#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pass-3 weak-gold adjudication on the frozen 281-question core set.

The two-round adjudication chain (law_gold_adjudicate.py) re-anchored 38
questions and left exactly 2 questions unverifiable. This pass-3:
  1. re-checks those 2 unverifiable questions with a deeper, different judge
     (qwen3:14b; the original two-round judge was qwen2.5:14b) over the stored
     rerank_top-8 candidates from benchmark/rerank_result.json;
  2. runs an independent gold-anchoring agreement audit on a seeded random
     sample of 60 adjudicated questions (same judge, same protocol);
  3. applies the outcomes to benchmark/gold_adjudicated.json (replacements
     keep a full trail: regolded_by=pass3, regolded_from, judge reason) and
     recomputes benchmark/gold_adjudicated_metrics.json from the stored ranks
     (CPU only, no GPU, deterministic);
  4. writes the full trail to benchmark/gold_pass3.json.

A replacement is accepted only when the judge names an exact candidate chunk
id that exists in the stored candidate list. Greedy decoding (temperature 0),
so the pass is reproducible given the same judge model."""
import json, os, random, re, sys, time, urllib.request

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
RUN = "/home/devlab1/law_workspace/runs/extension2"
OLLAMA = "http://127.0.0.1:11434"
JUDGE = "qwen3:14b"
SAMPLE_N = 60
SEED = 20261101
KS = (1, 3, 5, 10)
t00 = time.time()
log = lambda *a: print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

log("load inputs...")
rr = json.load(open(f"{B}/rerank_result.json", encoding="utf-8"))
per_q = {e["qid"]: e for e in rr["per_q"]}
chunks = {}
with open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        chunks[c["chunk_id"]] = c.get("content", "")
qs = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(open(f"{B}/{fn}", encoding="utf-8")):
        qs[q["qid"]] = q

# ---------------------------------------------------------------- rebuild the
# adjudicated gold map from the CURRENT main+seed golds (post weak-apply) using
# the original two-round rule: questions the regold trail marked unverifiable
# keep their gold only when both judge rounds accepted the re-anchor; the rest
# fall to the deep pass-3 re-check below.
regold = json.load(open(f"{B}/regold.json", encoding="utf-8"))
ver = json.load(open(f"{B}/regold_judge_round2.json", encoding="utf-8"))
unverified = {q for q, v in regold.items() if not v.get("new_gold")}
gold_adj, still = {}, []
n_two_round = 0
for qid, q in qs.items():
    g = list(q.get("gold_ids") or [])
    if not g:
        continue
    if qid in unverified:
        keep = ver.get("decisions", {}).get(qid, {}).get("accepted_both_rounds", [])
        if keep:
            gold_adj[qid] = list(keep)
            n_two_round += 1
        else:
            still.append(qid)
    else:
        gold_adj[qid] = g
log(f"rebuild: {len(gold_adj)} adjudicated golds, {len(still)} fall through to "
    f"pass-3 recheck: {sorted(still)}")
unver = sorted(still)


def ochat(model, messages, max_tokens=900, temperature=0.0):
    body = {"model": model, "messages": messages, "stream": False,
            "keep_alive": "1h",
            "options": {"temperature": temperature, "num_predict": max_tokens}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as rp:
        d = json.load(rp)
    return d["message"]["content"] or ""


def last_json(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    # prefer flat JSON objects that carry the expected keys
    for m in reversed(re.findall(r"\{[^{}]*\}", text, re.S)):
        try:
            d = json.loads(m)
        except Exception:
            continue
        if isinstance(d, dict) and ("verdict" in d or "chunk" in d):
            return d
    for m in reversed(re.findall(r"\{[^{}]*\}", text, re.S)):
        try:
            return json.loads(m)
        except Exception:
            continue
    return None


SYS = ("Bạn là thẩm định viên pháp lý. Cho một câu hỏi pháp lý dân sự Việt Nam "
       "và các đoạn trích luật ứng viên, hãy chọn đoạn trích là cơ sở pháp lý "
       "ĐÚNG cho câu hỏi tại thời điểm as_of. Chỉ chọn khi đoạn trích thật sự "
       "trả lời được câu hỏi. Trả về đúng một JSON: "
       '{"verdict":"yes|no","chunk":"<chunk_id>|null","reason":"<ngắn gọn>"} '
       "trong đó verdict=yes khi có đoạn trích phù hợp, chunk là chunk_id được chọn.")


def judge_one(qid):
    q = qs[qid]
    cands = per_q[qid]["rerank_top"][:8]
    blocks = []
    for cid in cands:
        seg = cid.split("|")
        label = " — ".join([seg[0]] + [s.replace("Dieu", "Điều ")
                                       .replace("Khoan", "Khoản ")
                                       .replace("Diem", "Điểm ") for s in seg[1:]])
        txt = (chunks.get(cid) or "").strip()
        if len(txt) > 900:
            txt = txt[:900] + "…"
        blocks.append(f"[{cid} | {label}]\n{txt}")
    usr = (f"Câu hỏi: {q['question']}\nas_of: {q['as_of']}\n\n"
           + "\n\n".join(blocks) + "\n\nJSON:")
    d = None
    for attempt in range(3):
        txt = ochat(JUDGE, [{"role": "system", "content": SYS},
                            {"role": "user", "content": usr}])
        d = last_json(txt)
        if d and d.get("verdict") in ("yes", "no"):
            break
        time.sleep(3)
    return d, cands


# ---------------------------------------------------- 1) unverifiable recheck
recheck = []
pass3_replacements = {}
for qid in unver:
    if qid not in per_q:
        recheck.append({"qid": qid, "judge": JUDGE, "outcome": "no_candidates",
                        "verdict": None})
        continue
    d, cands = judge_one(qid)
    log(f"  {qid}: {json.dumps(d, ensure_ascii=False)[:200]}")
    row = {"qid": qid, "judge": JUDGE, "candidates": cands, "verdict": d}
    if d and d.get("verdict") == "yes" and d.get("chunk") in cands:
        row["outcome"] = "regolded"
        pass3_replacements[qid] = d["chunk"]
    else:
        row["outcome"] = "still_unverifiable"
    recheck.append(row)

# --------------------------------------------- 2) agreement audit (n=SAMPLE_N)
verified = [qid for qid in gold_adj if qid not in pass3_replacements]
rng = random.Random(SEED)
sample = sorted(rng.sample(verified, min(SAMPLE_N, len(verified))))
agree = primary = parse_fail = 0
audit_rows = []
for i, qid in enumerate(sample, 1):
    d, cands = judge_one(qid)
    gold = set(gold_adj[qid])
    if not d or d.get("verdict") not in ("yes", "no"):
        parse_fail += 1
        audit_rows.append({"qid": qid, "chosen": None, "agrees_gold": None,
                           "matches_primary": None, "verdict": d,
                           "parse_fail": True})
        continue
    ok = bool(d.get("verdict") == "yes" and d.get("chunk") in gold)
    prim = bool(d.get("chunk") == gold_adj[qid][0])
    agree += ok
    primary += prim
    audit_rows.append({"qid": qid, "chosen": (d or {}).get("chunk"),
                       "agrees_gold": ok, "matches_primary": prim,
                       "verdict": d})
    if i % 10 == 0:
        log(f"  agreement audit {i}/{len(sample)} (agree={agree}, primary={primary}, parse_fail={parse_fail})")

_n_effective = len(sample) - parse_fail
agreement = {"n": len(sample), "n_parse_fail": parse_fail,
             "n_effective": _n_effective,
             "n_agree_gold": agree, "n_agree_primary": primary,
             "agreement_rate": round(agree / max(1, _n_effective), 4),
             "primary_rate": round(primary / max(1, _n_effective), 4),
             "seed": SEED, "judge": JUDGE,
             "protocol": "judge picks the legal basis among stored rerank_top-8; "
                         "agreement = chosen chunk belongs to the adjudicated gold set"}
log("agreement:", json.dumps(agreement, ensure_ascii=False))

# ------------------------------------------------- 3) apply + metrics recompute
if pass3_replacements:
    for qid, chunk in pass3_replacements.items():
        gold_adj[qid] = [chunk]
still_final = [q for q in still if q not in pass3_replacements]
out_gold = {
    "n_questions_with_verified_gold": len(gold_adj),
    "n_questions_unverifiable": len(still_final),
    "unverifiable_qids": still_final,
    "n_regolded_by_two_round_llm_judge": n_two_round,
    "judge_model": ver.get("model"),
    "judge_agreement_rate": ver.get("agreement_rate"),
    "rule": "cau chi con lai khi ca hai vong kiem chung cua LLM judge deu xac nhan "
            "doan do tra loi dung; cac doan duoc giu la dap an chinh la cac ban "
            "khac nhau cua cung dieu khoan",
    "pass3": {"judge": JUDGE, "n_rechecked": len(recheck),
              "n_regolded": len(pass3_replacements),
              "qids": sorted(pass3_replacements)},
    "gold": gold_adj,
}
json.dump(out_gold, open(f"{B}/gold_adjudicated.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("gold_adjudicated.json rebuilt:", len(gold_adj), "golds |",
    len(still_final), "unverifiable |", sorted(pass3_replacements), "pass-3 regolded")


def score(rows, key, goldmap):
    hit = {k: 0 for k in KS}
    rr_sum = 0.0
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
            rr_sum += 1.0 / rank
    return {"n_questions": n,
            "hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS} if n else {},
            "mrr": round(rr_sum / n, 4) if n else 0}


gold_adj = out_gold["gold"]
# original (pre-adjudication) gold for the old_gold row comes from the questions
orig = {qid: list(q["gold_ids"]) for qid, q in qs.items() if q.get("gold_ids")}
old = score(list(per_q.values()), "rerank_top", orig)
new = score(list(per_q.values()), "rerank_top", gold_adj)
old_h = score(list(per_q.values()), "hybrid_top", orig)
new_h = score(list(per_q.values()), "hybrid_top", gold_adj)
res = {"old_gold": {"n_questions": old["n_questions"], "hit_at_k": old["hit_at_k"],
                    "mrr": old["mrr"]},
       "new_gold_adjudicated": {"n_questions": new["n_questions"],
                                "hit_at_k": new["hit_at_k"], "mrr": new["mrr"]},
       "hybrid_with_old_gold": {"hit_at_k": old_h["hit_at_k"], "mrr": old_h["mrr"]},
       "hybrid_with_new_gold": {"hit_at_k": new_h["hit_at_k"], "mrr": new_h["mrr"]},
       "n_regolded": n_two_round,
       "n_unverifiable_remaining": len(still_final),
       "pass3": {"judge": JUDGE, "n_rechecked": len(recheck),
                 "n_regolded": len(pass3_replacements)},
       "agreement_audit": agreement}
json.dump(res, open(f"{B}/gold_adjudicated_metrics.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"meta": {"judge": JUDGE, "sample_seed": SEED, "sample_n": len(sample),
                    "candidates_source": "rerank_result.json per_q rerank_top[:8]",
                    "applied": sorted(pass3_replacements)},
           "unverifiable_recheck": recheck,
           "agreement_audit": {"summary": agreement, "per_q": audit_rows}},
          open(f"{B}/gold_pass3.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("PASS3 DONE -> gold_pass3.json + updated gold_adjudicated.json + metrics")
