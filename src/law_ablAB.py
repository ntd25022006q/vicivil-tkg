"""Ablation A/B: dense-only vs +BM25 (no vLLM, no rerank). Fast. Saves ranks."""
import json, sys, math

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
split = json.load(open(f"{R}/bench_split.json", encoding="utf-8"))
qv = rt.embed([b["question"] for b in bench])
res = {}
ranks_B = {}
for mode in ["A-dense", "B-hybrid"]:
    h = {1: 0, 3: 0, 5: 0, 10: 0}
    rr = ndcg = n = 0
    dh = {1: 0, 3: 0, 5: 0, 10: 0}
    dn = 0
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
        for k in h:
            h[k] += r0 <= k
        if r0 <= 10:
            rr += 1.0 / r0
            ndcg += 1.0 / math.log2(r0 + 1)
        if b["qid"] in split["test"]:
            dn += 1
            for k in dh:
                dh[k] += r0 <= k
        if mode == "B-hybrid":
            ranks_B[b["qid"]] = ids
    res[mode] = {"n": n, **{f"Hit@{k}": round(h[k] / n, 3) for k in [1, 3, 5, 10]},
                 "MRR": round(rr / n, 3), "nDCG@10": round(ndcg / n, 3),
                 **{f"test_Hit@{k}": round(dh[k] / max(dn, 1), 3) for k in [1, 3, 5, 10]},
                 "test_n": dn}
    print(f"{mode} n={n} " + " ".join(f"Hit@{k}={res[mode][f'Hit@{k}']} " for k in [1, 3, 5, 10]) +
          f"MRR={res[mode]['MRR']} nDCG={res[mode]['nDCG@10']} test_Hit@5={res[mode]['test_Hit@5']}", flush=True)
json.dump(res, open(f"{R}/ablation_AB.json", "w", encoding="utf-8"))
if ranks_B:
    json.dump(ranks_B, open(f"{R}/ranks_hybrid.json", "w", encoding="utf-8"), ensure_ascii=False)
