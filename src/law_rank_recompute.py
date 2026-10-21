"""Kiem tra: chi so da cong bo (Hit@1 = 0,452) co tai lap duoc tu tep
provenance/ranks_hybrid.json trong kho khong? File nay luu XEP HANH DAY DU
(cau nao -> danh sach chunk theo thu tu), khong phai chi 5 ket qua dau.

Neu khop, thi phan "khong tai lap duoc" cua bao cao la do phan ghi tep ket qua,
khong phai do thieu du lieu.
"""
import json, os

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
P = os.path.join(R, "provenance")
KS = (1, 3, 5, 10)

gold = {}
for fn in ("law_bench_200c.json", "law_bench_v1.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = q["gold_ids"]

rh = json.load(open(os.path.join(P, "ranks_hybrid.json"), encoding="utf-8"))
print("ranks_hybrid phu %d cau | co dap an vang: %d" % (len(rh), len(gold)))

hit = {k: 0 for k in KS}
rr = 0.0
n = 0
missing = []
for qid, golds in gold.items():
    rank_list = rh.get(qid)
    if not rank_list:
        missing.append(qid)
        continue
    n += 1
    rank = next((r + 1 for r, t in enumerate(rank_list) if t in golds), None)
    for k in KS:
        if rank and rank <= k:
            hit[k] += 1
    if rank:
        rr += 1.0 / rank

out = {
    "source": "provenance/ranks_hybrid.json",
    "n_questions_covered": n,
    "n_questions_not_covered": len(missing),
    "hit_at_k": {str(k): round(hit[k] / n, 4) if n else 0 for k in KS},
    "mrr": round(rr / n, 4) if n else 0,
    "note": "tinh lai truc tiep tu xep hang da luu trong kho; khong can GPU, khong can mo hinh",
}
json.dump(out, open(os.path.join(B, "rank_recompute_from_repo.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))