"""Dung bo dap an vang da trong tham (adjudicated gold) va tinh lai chi so.

- 240 cau co dap an vang da duoc xac minh: giu nguyen.
- 41 cau chua xac minh: dua vao ket qua LLM judge 2 vong (chi nhan khi ca hai
  vong deu xac nhan). Cau nao khong con doan nao duoc xac nhan -> van la
  khong xac minh duoc va bi tach ra khoi chi so.
- Chi so duoc tinh lai tu xep hang da luu (khong can GPU, khong can model).
"""
import io, json, os

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
KS = (1, 3, 5, 10)

gold = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = {"q": q.get("question", ""), "g": list(q["gold_ids"])}

regold = json.load(open(os.path.join(B, "regold.json"), encoding="utf-8"))
unverified = {q for q, v in regold.items() if not v.get("new_gold")}
ver = json.load(open(os.path.join(B, "regold_judge_round2.json"), encoding="utf-8"))
rr = json.load(open(os.path.join(B, "rerank_result.json"), encoding="utf-8"))
ev = json.load(open(os.path.join(B, "law_eval_repro.json"), encoding="utf-8"))

gold_adj = {}
regolded = 0
still = []
for qid, meta in gold.items():
    g = list(meta["g"])
    if qid in unverified:
        keep = ver["decisions"].get(qid, {}).get("accepted_both_rounds", [])
        if keep:
            g = keep
            regolded += 1
        else:
            still.append(qid)
            continue
    gold_adj[qid] = g

out_gold = {
    "n_questions_with_verified_gold": len(gold_adj),
    "n_questions_unverifiable": len(still),
    "unverifiable_qids": still,
    "n_regolded_by_two_round_llm_judge": regolded,
    "judge_model": ver.get("model"),
    "judge_agreement_rate": ver.get("agreement_rate"),
    "rule": "cau chi con lai khi ca hai vong kiem chung cua LLM judge deu xac nhan "
            "doan do tra loi dung; cac doan duoc giu la dap an chinh la cac ban "
            "khac nhau cua cung dieu khoan",
    "gold": gold_adj,
}
json.dump(out_gold, open(os.path.join(B, "gold_adjudicated.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)


def score(rows, key, goldmap):
    hit = {k: 0 for k in KS}
    rr = 0.0
    n = 0
    for r in rows:
        g = goldmap.get(r["qid"])
        if not g:
            continue
        n += 1
        rank = next((i + 1 for i, t in enumerate(r[key]) if t in g), None)
        for k in KS:
            if rank and rank <= k:
                hit[k] += 1
        if rank:
            rr += 1.0 / rank
    return {"n_questions": n,
            "hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS} if n else {},
            "mrr": round(rr / n, 4) if n else 0}


old = score(rr["per_q"], "rerank_top", {q: m["g"] for q, m in gold.items()})
new = score(rr["per_q"], "rerank_top", gold_adj)
old_h = score(rr["per_q"], "hybrid_top", {q: m["g"] for q, m in gold.items()})
new_h = score(rr["per_q"], "hybrid_top", gold_adj)

res = {
    "old_gold": {"n_questions": old["n_questions"], "hit_at_k": old["hit_at_k"], "mrr": old["mrr"]},
    "new_gold_adjudicated": {"n_questions": new["n_questions"], "hit_at_k": new["hit_at_k"], "mrr": new["mrr"]},
    "hybrid_with_old_gold": {"hit_at_k": old_h["hit_at_k"], "mrr": old_h["mrr"]},
    "hybrid_with_new_gold": {"hit_at_k": new_h["hit_at_k"], "mrr": new_h["mrr"]},
    "n_regolded": regolded,
    "n_unverifiable_remaining": len(still),
}
json.dump(res, open(os.path.join(B, "gold_adjudicated_metrics.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))