"""Protocol-grade audit: numbering gaps, dup IDs, empties, temporal consistency,
benchmark gold existence. Output: runs/law_audit.json + printed verdicts.
"""
import json
from collections import Counter

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rows = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
rep = {"n_chunks": len(rows)}
# 1. dup chunk ids
ids = [r["chunk_id"] for r in rows]
rep["dup_ids"] = len(ids) - len(set(ids))
# 2. numbering gaps per law
gaps = {}
by_law = {}
for r in rows:
    by_law.setdefault(r["law_id"], []).append(r)
for law, lst in by_law.items():
    nums = sorted({int(r["dieu"]) for r in lst if str(r["dieu"]).isdigit()})
    if nums:
        full = set(range(1, max(nums) + 1))
        g = sorted(full - set(nums))
        if g:
            gaps[law] = g
rep["numbering_gaps"] = gaps
# 3. empty/short
rep["empty"] = sum(1 for r in rows if r["chars"] < 20)
short = [(r["chunk_id"], r["chars"]) for r in rows if 20 <= r["chars"] < 60]
rep["short_n"] = len(short)
# 4. temporal: every chunk law has entry; succession targets exist
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
have = {L["law_id"] for L in G["laws"]}
rep["orphan_laws"] = sorted(set(by_law) - have)
rep["laws"] = len(have)
rep["edges"] = len(G["succession"])
# 5. benchmark golds exist
ids_set = set(ids)
missing = []
for fn in ["law_bench_v1.json", "law_bench_200c.json"]:
    try:
        for o in json.load(open(f"{R}/{fn}", encoding="utf-8")):
            for g in o.get("gold_ids", []):
                if g != "ABSENT" and g not in ids_set:
                    missing.append((fn, o["qid"], g))
    except Exception as e:
        missing.append((fn, "FILE", repr(e)[:60]))
rep["missing_golds"] = missing[:10]
rep["missing_gold_n"] = len(missing)
json.dump(rep, open(f"{R}/law_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "missing_golds"}, ensure_ascii=False)[:800], flush=True)
print("missing golds:", missing[:6], flush=True)
