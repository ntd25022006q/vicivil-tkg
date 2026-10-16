"""Eval law ADGR-fixed retrieval on benchmark v1: Hit@1/3/5 + abstain."""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_v1.json", encoding="utf-8"))
h1 = h3 = h5 = n = abst = 0
d1 = d5 = 0
for b in bench:
    ids = rt.retrieve(b["question"], b["as_of"], topk=10)
    gold = b["gold_ids"][0]
    gdieu = "|".join(gold.split("|")[:2])
    r0 = ids.index(gold) + 1 if gold in ids else 99
    rd = next((i + 1 for i, x in enumerate(ids) if "|".join(x.split("|")[:2]) == gdieu), 99)
    if b["qid"] == "CIV012":
        abst = 1 if r0 == 99 else 0
        print(f'{b["qid"]} rank={r0} ABSTAIN-{"OK" if r0 == 99 else "FAIL"}', flush=True)
        continue
    n += 1
    h1 += r0 <= 1
    h3 += r0 <= 3
    h5 += r0 <= 5
    d1 += rd <= 1
    d5 += rd <= 5
    print(f'{b["qid"]} rank={r0} dieu_rank={rd} {"HIT" if r0 <= 5 else ("DIEU-HIT" if rd <= 5 else "miss")}', flush=True)
print(f"ADGR-V2 n={n} Hit@1={h1 / max(n, 1):.3f} Hit@3={h3 / max(n, 1):.3f} "
      f"Hit@5={h5 / max(n, 1):.3f} Dieu@1={d1 / max(n, 1):.3f} Dieu@5={d5 / max(n, 1):.3f} abstain={abst}", flush=True)
