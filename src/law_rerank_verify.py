"""Tinh lai chi so truy hoi tu ket qua RERANK da luu trong kho.

Tep benchmark/rerank_result.json chua xep hang sau khi xep lai bang mo hinh
(BAAI/bge-reranker-v2-m3). Script nay tinh lai chi so truc tiep tu tep do:
KHONG can GPU, KHONG can model, KHONG can mang.

Chay:  python src/law_rerank_verify.py
"""
import json, os

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
KS = (1, 3, 5, 10)

rr = json.load(open(os.path.join(B, "rerank_result.json"), encoding="utf-8"))
gold = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = q["gold_ids"]

hit = {k: 0 for k in KS}
mrr = 0.0
n = 0
for row in rr["per_q"]:
    g = gold.get(row["qid"])
    if not g:
        continue
    n += 1
    rank = next((r + 1 for r, t in enumerate(row["rerank_top"]) if t in g), None)
    for k in KS:
        if rank and rank <= k:
            hit[k] += 1
    if rank:
        mrr += 1.0 / rank

out = {
    "source": "benchmark/rerank_result.json",
    "model_used_for_rerank": rr.get("model"),
    "n_questions": n,
    "hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS},
    "mrr": round(mrr / n, 4),
    "note": "tinh lai truc tiep tu xep hang da luu; khong can GPU, khong can mo hinh",
}
json.dump(out, open(os.path.join(B, "rerank_verify.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))