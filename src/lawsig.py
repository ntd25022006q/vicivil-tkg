"""Significance: McNemar (Hit@1/Hit@5, B vs A and B vs C-proxy) + Wilcoxon on RR.
Ranks files: ranks_dense.json (A), ranks_hybrid.json (B). C from law_eval_ranks
(graph+expansion+rerank, older index -> compare with disclosed caveat).
"""
import json, math
from collections import defaultdict

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
bench = {o["qid"]: o for o in json.load(open(f"{R}/law_bench_main.json", encoding="utf-8"))}
for o in json.load(open(f"{R}/law_bench_seed.json", encoding="utf-8")):
    bench.setdefault(o["qid"], o)
A = json.load(open(f"{R}/ranks_dense.json", encoding="utf-8"))
B = json.load(open(f"{R}/ranks_hybrid.json", encoding="utf-8"))
try:
    C = json.load(open(f"{R}/law_eval_ranks.json", encoding="utf-8"))
except Exception:
    C = {}


def rr(ids, gold):
    return 1.0 / (ids.index(gold) + 1) if gold in ids else 0.0


def hit(ids, gold, k):
    return 1 if gold in ids[:k] else 0


def mcnemar(b, c):
    n01 = sum(1 for q in b if b[q] == 0 and c[q] == 1)
    n10 = sum(1 for q in b if b[q] == 1 and c[q] == 0)
    n = n01 + n10
    if n == 0:
        return 1.0, (0, 0)
    chi = (abs(n01 - n10) - 1) ** 2 / n
    p = math.erfc(math.sqrt(chi / 2))
    return p, (n01, n10)


def wilcoxon(d):
    d = [x for x in d if x != 0]
    n = len(d)
    if n < 10:
        return 1.0
    ranks = sorted(range(n), key=lambda i: abs(d[i]))
    W = sum((r + 1) * (1 if d[i] > 0 else -1) for r, i in enumerate(ranks))
    var = n * (n + 1) * (2 * n + 1) / 6
    z = W / math.sqrt(var)
    return math.erfc(abs(z) / math.sqrt(2))


qs = sorted(set(A) & set(B) & set(bench))
print("common n:", len(qs), flush=True)
out = {}
for tag, RA, RB in [("BvsA", B, A), ("BvsC", B, C)]:
    row = {}
    for k in [1, 5]:
        hb = {q: hit(RA.get(q, []), bench[q]["gold_ids"][0], k) for q in qs if q in RA}
        hc = {q: hit(RB.get(q, []), bench[q]["gold_ids"][0], k) for q in qs if q in RB}
        qq = sorted(set(hb) & set(hc))
        p, (n01, n10) = mcnemar({q: hb[q] for q in qq}, {q: hc[q] for q in qq})
        row[f"Hit@{k}_p"] = round(p, 4)
        row[f"Hit@{k}_n01n10"] = [n01, n10]
    d = []
    for q in qs:
        if q in RA and q in RB:
            d.append(rr(RA[q], bench[q]["gold_ids"][0]) - rr(RB[q], bench[q]["gold_ids"][0]))
    row["RR_Wilcoxon_p"] = round(wilcoxon(d), 4)
    row["n"] = len(qs)
    out[tag] = row
    print(tag, row, flush=True)
json.dump(out, open(f"{R}/significance.json", "w", encoding="utf-8"), indent=2)
