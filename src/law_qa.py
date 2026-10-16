"""End-to-end civil QA v1: embed question -> dense top-K over date-valid chunks.
Usage: law_qa.py <qid>   (reads law_bench_v1.json)
"""
import json, sys, urllib.request
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"


def emb(texts):
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/embed",
        data=json.dumps({"model": "embeddinggemma:300m", "input": texts}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        v = np.asarray(json.load(r)["embeddings"], dtype=np.float32)
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)


QID = sys.argv[1]
b = [x for x in json.load(open(f"{R}/law_bench_v1.json", encoding="utf-8")) if x["qid"] == QID][0]
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
lawmap = {L["law_id"]: L for L in G["laws"]}


def valid(law_id):
    L = lawmap[law_id]
    return L["valid_from"] <= b["as_of"] and (L["valid_to"] is None or b["as_of"] < L["valid_to"])


ch = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(__import__("base64").b64decode(ch["matrix"]), dtype=np.float32).reshape(-1, 768)
keep = [(i, c) for i, c in enumerate(ch["data"]) if valid(c["url"])]
M = mat[[i for i, _ in keep]]
q = emb([b["question"]])[0]
s = M @ q
order = np.argsort(-s)[:3]
print(f"Q {QID} [{b['as_of']}]: {b['question']}", flush=True)
print(f"valid laws: {[L['law_id'] for L in G['laws'] if valid(L['law_id'])]}", flush=True)
hit = False
for r in order:
    c = keep[r][1]
    mark = "GOLD" if c["__id__"] in b["gold_ids"] else "...."
    if mark == "GOLD":
        hit = True
    print(f"  [{mark} {s[r]:.3f}] {c['__id__']}: {c['content'][:130]}", flush=True)
print("HIT" if hit else "MISS", flush=True)
