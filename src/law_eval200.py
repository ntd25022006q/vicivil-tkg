"""Full eval-200: v3 retriever (expansion + rerank-fusion) on clean benchmark.
Plus 3 abstain probes (dates with no valid law / missing 1995 content).
"""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
probes = [
    {"qid": "T1990", "as_of": "1990-01-01",
     "question": "Năm 1990 ly hôn cần điều kiện gì?", "gold_ids": ["ABSENT"]},
    {"qid": "T1995", "as_of": "2000-06-01",
     "question": "Bộ luật Dân sự 1995 quy định thế nào về quyền sở hữu?",
     "gold_ids": ["ABSENT"]},
]
h1 = h3 = h5 = n = 0
d5 = 0
by_law = {}
RANKF = "/home/devlab1/law_workspace/runs/law_eval_ranks.json"
try:
    saved = json.load(open(RANKF, encoding="utf-8"))
except Exception:
    saved = {}
for b in bench:
    if b["qid"] in saved:
        ids = saved[b["qid"]]
    else:
        ids = rt.retrieve(b["question"], b["as_of"], topk=10, rerank=True)
        saved[b["qid"]] = ids
        json.dump(saved, open(RANKF, "w", encoding="utf-8"), ensure_ascii=False)
    gold = b["gold_ids"][0]
    gdieu = "|".join(gold.split("|")[:2])
    r0 = ids.index(gold) + 1 if gold in ids else 99
    rd = next((i + 1 for i, x in enumerate(ids) if "|".join(x.split("|")[:2]) == gdieu), 99)
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    d5 += rd <= 5
    L = b.get("law_id", "?")
    by_law.setdefault(L, [0, 0])[0] += 1
    by_law[L][1] += r0 <= 5
    if n % 40 == 0:
        print(f"[{n}/{len(bench)}] Hit@5={h5 / n:.3f}", flush=True)
abst = 0
for b in probes:
    ids = rt.retrieve(b["question"], b["as_of"], topk=10, rerank=False)
    ok = len(ids) == 0 or True
    # abstain = no confident answer: here = empty pool (1990) or gold absent
    print(f'{b["qid"]} date={b["as_of"]} n_ret={len(ids)}', flush=True)
    abst += 1 if (b["qid"] == "T1990" and len(ids) == 0) else 0
print(f"EVAL200 n={n} Hit@1={h1 / n:.3f} Hit@3={h3 / n:.3f} Hit@5={h5 / n:.3f} "
      f"Dieu@5={d5 / n:.3f}", flush=True)
print("by_law Hit@5:", {k: f"{v[1]}/{v[0]}" for k, v in by_law.items()}, flush=True)
print("abstain_empty_pool:", abst, "(want 1: 1990 has no valid law)", flush=True)
