"""Benchmark v2 eval: hybrid BM25+dense RRF over date-valid chunks.
CIV012 (1995 absent): empty valid set OR gold missing -> ABSTAIN-OK.
"""
import json, sys, urllib.request
import numpy as np

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_retrieve import BM25, rrf

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"


def emb(texts):
    out = []
    for i in range(0, len(texts), 16):
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/embed",
            data=json.dumps({"model": "embeddinggemma:300m",
                             "input": texts[i:i + 16]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            v = np.asarray(json.load(r)["embeddings"], dtype=np.float32)
        out.append(v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9))
    return np.vstack(out)


bench = json.load(open(f"{R}/law_bench_v1.json", encoding="utf-8"))
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
lawmap = {L["law_id"]: L for L in G["laws"]}
ch = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(__import__("base64").b64decode(ch["matrix"]), dtype=np.float32).reshape(-1, 768)
bm = BM25([c["content"] for c in ch["data"]])
Q = emb([b["question"] for b in bench])
h1 = h3 = h5 = n = abst = 0
for bi, b in enumerate(bench):
    keep = [(i, c) for i, c in enumerate(ch["data"])
            if (lambda L: L["valid_from"] <= b["as_of"] and
               (L["valid_to"] is None or b["as_of"] < L["valid_to"]))(lawmap[c["url"]])]
    if not keep:
        tag = "ABSTAIN-OK" if b["qid"] == "CIV012" else "NO-CANDIDATES"
        abst += (b["qid"] == "CIV012")
        print(f'{b["qid"]} {tag}', flush=True)
        continue
    M = mat[[i for i, _ in keep]]
    ds = (M @ Q[bi]).tolist()
    bs = bm.score(b["question"])
    bsk = [bs[i] for i, _ in keep]
    order_d = sorted(range(len(keep)), key=lambda r: -ds[r])[:50]
    order_b = sorted(range(len(keep)), key=lambda r: -bsk[r])[:50]
    fused = rrf([order_d, order_b])[:10]
    ids = [keep[r][1]["__id__"] for r in fused]
    gold = b["gold_ids"][0]
    r0 = ids.index(gold) + 1 if gold in ids else 99
    if b["qid"] == "CIV012":
        abst = 1 if r0 == 99 else 0
        print(f'{b["qid"]} rank={r0} ABSTAIN-{"OK" if r0 == 99 else "FAIL"}', flush=True)
        continue
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    print(f'{b["qid"]} rank={r0} {"HIT" if r0 <= 5 else "miss"}', flush=True)
print(f"HYBRID n={n} Hit@1={h1 / max(n, 1):.3f} Hit@3={h3 / max(n, 1):.3f} "
      f"Hit@5={h5 / max(n, 1):.3f} abstain={abst}", flush=True)
