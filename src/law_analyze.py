"""Eval-200 analysis: hand vs synthetic, by law, miss patterns. Run after eval.
Reads law_eval200.log ranks + bench files. No GPU needed.
"""
import json, re

LOG = "/home/devlab1/law_workspace/runs/law_eval200.log"
R = "/home/devlab1/law_workspace/runs"
hand = {o["qid"] for o in json.load(open(f"{R}/law_bench_v1.json", encoding="utf-8"))}
syn = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
by_q = {o["qid"]: o for o in syn}
recs = []
for L in open(LOG, encoding="utf-8", errors="replace"):
    m = re.match(r"(GEN\d+|CIV\d+)\s+rank=(\d+)", L)
    if m:
        recs.append((m.group(1), int(m.group(2))))


def hit(rs, k):
    return sum(1 for _, r in rs if r <= k) / max(1, len(rs))


hh = [(q, r) for q, r in recs if q in hand]
ss = [(q, r) for q, r in recs if q not in hand]
print(f"ALL n={len(recs)} Hit@1={hit(recs, 1):.3f} Hit@3={hit(recs, 3):.3f} Hit@5={hit(recs, 5):.3f}")
print(f"HAND n={len(hh)} Hit@1={hit(hh, 1):.3f} Hit@3={hit(hh, 3):.3f} Hit@5={hit(hh, 5):.3f}")
print(f"SYN  n={len(ss)} Hit@1={hit(ss, 1):.3f} Hit@3={hit(ss, 3):.3f} Hit@5={hit(ss, 5):.3f}")
from collections import Counter
laws = Counter()
for q, r in ss:
    o = by_q.get(q, {})
    laws[o.get("law_id", "?")] += 1
print("syn by law:", dict(laws))
miss = [q for q, r in recs if r > 5]
print(f"miss sample ({len(miss)}):", miss[:10])
