"""Ablation A/B: dense-only vs +BM25 (no vLLM, no rerank). Fast. Saves ranks."""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
qv = rt.embed([b["question"] for b in bench])
res = {}
for mode in ["A-dense", "B-hybrid"]:
    h1 = h3 = h5 = n = 0
    for bi, b in enumerate(bench):
        vix = rt.valid_idx(b["as_of"])
        if not vix:
            continue
        dd = (rt.cmat[vix] @ qv[bi]).tolist()
        od = sorted(range(len(vix)), key=lambda r: -dd[r])[:10]
        ids = [rt.chunks[vix[r]]["__id__"] for r in od]
        if mode == "B-hybrid":
            bs = rt.bm_c.scores(b["question"])
            ob = sorted(range(len(vix)), key=lambda r: -bs[vix[r]])[:10]
            ob = [vix[r] for r in ob]
            f = {}
            for r, gi in enumerate([vix[r] for r in od] + ob):
                f[gi] = f.get(gi, 0) + 1.0 / (60 + r + 1)
            ids = [rt.chunks[i]["__id__"] for i in sorted(f, key=f.get, reverse=True)[:10]]
        gold = b["gold_ids"][0]
        r0 = ids.index(gold) + 1 if gold in ids else 99
        n += 1
        h1 += r0 <= 1
        h3 += r0 <= 3
        h5 += r0 <= 5
    res[mode] = (round(h1 / n, 3), round(h3 / n, 3), round(h5 / n, 3), n)
    print(f"{mode} n={n} Hit@1/3/5={res[mode][0]}/{res[mode][1]}/{res[mode][2]}", flush=True)
json.dump(res, open(f"{R}/ablation_AB.json", "w", encoding="utf-8"))
