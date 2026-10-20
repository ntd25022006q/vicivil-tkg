"""Apply accepted regolds to bench files, re-run hybrid eval, report deltas."""
import json

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
import sys
sys.path.insert(0, f"{W}/src")
from law_adgr import LawRetriever

reg = json.load(open(f"{R}/regold.json", encoding="utf-8"))
fixed = {q: v["new_gold"] for q, v in reg.items() if v.get("new_gold")}
print("accepted regolds:", len(fixed), flush=True)
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    qs = json.load(open(f"{R}/{fn}", encoding="utf-8"))
    n = 0
    for o in qs:
        if o["qid"] in fixed:
            o["gold_ids"] = [fixed[o["qid"]]]
            o["regolded_from"] = reg[o["qid"]]["old_gold"]
            n += 1
    json.dump(qs, open(f"{R}/{fn}", "w", encoding="utf-8"), ensure_ascii=False)
    print(fn, "updated:", n, flush=True)
rt = LawRetriever()
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    qs = json.load(open(f"{R}/{fn}", encoding="utf-8"))
    h = {k: 0 for k in (1, 3, 5, 10)}
    for o in qs:
        ids = rt.retrieve(o["question"], o["as_of"], topk=10, rerank=False, mode="hybrid")
        g = set(o["gold_ids"])
        for k in (1, 3, 5, 10):
            if any(i in g for i in ids[:k]):
                h[k] += 1
    n = len(qs)
    print(fn, f"n={n}", " ".join(f"H@{k}={h[k]/n:.3f}" for k in (1, 3, 5, 10)), flush=True)
print("APPLY DONE", flush=True)
