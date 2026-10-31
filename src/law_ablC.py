"""Ablation C: anchors+edges+keywords, NO expansion, NO rerank.
Isolates whether expansion/rerank are the poison vs graph layers.
"""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
rt.expand = lambda q: q
bench = json.load(open(f"{R}/law_bench_main.json", encoding="utf-8"))
h1 = h3 = h5 = n = 0
for b in bench:
    ids = rt.retrieve(b["question"], b["as_of"], topk=10, rerank=False)
    gold = b["gold_ids"][0]
    r0 = ids.index(gold) + 1 if gold in ids else 99
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    if n % 50 == 0:
        print(f"[{n}/{len(bench)}] Hit@5={h5 / n:.3f}", flush=True)
print(f"C-graph-noexp-norr n={n} Hit@1={h1 / n:.3f} Hit@3={h3 / n:.3f} Hit@5={h5 / n:.3f}", flush=True)
