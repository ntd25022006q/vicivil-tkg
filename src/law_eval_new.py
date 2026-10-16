"""Delta eval: NEW* questions only (old 163 already measured).
Writes ranks into law_eval_ranks.json (compatible with cached full eval).
"""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
oldq = {o["qid"] for o in json.load(open(f"{R}/law_bench_200.json", encoding="utf-8"))}
newq = [b for b in bench if b["qid"] not in oldq]
print("delta n:", len(newq), flush=True)
try:
    saved = json.load(open(f"{R}/law_eval_ranks.json", encoding="utf-8"))
except Exception:
    saved = {}
h1 = h3 = h5 = n = 0
d5 = 0
for b in newq:
    ids = rt.retrieve(b["question"], b["as_of"], topk=10, rerank=True)
    saved[b["qid"]] = ids
    json.dump(saved, open(f"{R}/law_eval_ranks.json", "w", encoding="utf-8"), ensure_ascii=False)
    gold = b["gold_ids"][0]
    gdieu = "|".join(gold.split("|")[:2])
    r0 = ids.index(gold) + 1 if gold in ids else 99
    rd = next((i + 1 for i, x in enumerate(ids) if "|".join(x.split("|")[:2]) == gdieu), 99)
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    d5 += rd <= 5
    print(f'{b["qid"]} rank={r0} dieu={rd} {"HIT" if r0 <= 5 else ("DIEU" if rd <= 5 else "miss")}', flush=True)
print(f"DELTA n={n} Hit@1={h1 / max(n, 1):.3f} Hit@3={h3 / max(n, 1):.3f} "
      f"Hit@5={h5 / max(n, 1):.3f} Dieu@5={d5 / max(n, 1):.3f}", flush=True)
