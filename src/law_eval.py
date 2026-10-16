"""Benchmark v1 eval: Hit@1/3/5 over date-valid chunks (dense only).
Abstain test CIV012 expects MISS (1995 absent) -> counted separately.
"""
import json, urllib.request
import numpy as np

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
Q = emb([b["question"] for b in bench])
h1 = h3 = h5 = n = abstain_ok = 0
for bi, b in enumerate(bench):
    keep = [(i, c) for i, c in enumerate(ch["data"])
            if (lambda L: L["valid_from"] <= b["as_of"] and
               (L["valid_to"] is None or b["as_of"] < L["valid_to"]))(lawmap[c["url"]])]
    if not keep:
        continue
    s = mat[[i for i, _ in keep]] @ Q[bi]
    order = np.argsort(-s)
    ranks = [r + 1 for r in order if keep[r][1]["__id__"] in b["gold_ids"][:1]]
    r0 = ranks[0] if ranks else 99
    tag = "ABSTAIN-OK" if (b["qid"] == "CIV012" and r0 == 99) else ("HIT" if r0 <= 5 else "miss")
    if b["qid"] == "CIV012":
        abstain_ok = 1 if r0 == 99 else 0
        print(f'{b["qid"]} date={b["as_of"]} rank={r0} {tag}', flush=True)
        continue
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    print(f'{b["qid"]} date={b["as_of"]} rank={r0} {tag}', flush=True)
print(f"BENCH n={n} Hit@1={h1 / n:.3f} Hit@3={h3 / n:.3f} Hit@5={h5 / n:.3f} abstain_test={abstain_ok}", flush=True)
