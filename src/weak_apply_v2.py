#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply pass-3 weak-gold recheck verdicts to benchmark/law_bench_main.json,
with STRICTER guardrails than the interrupted session's version:
  reanchor accepted only when better_gold (a) exists in the corpus,
  (b) appears in the question's stored retrieval candidates, and
  (c) is inside the law's validity window at the question's as_of (TCR rule).
  Otherwise the reanchor is REJECTED and recorded (gold unchanged).
  flag     -> gold_tier := flagged, weak_review := pass3-flagged
  gold-ok  -> weak_review := pass3-ok (tier kept)
Backup of main.json goes to runs/main_backup_pass3.json (first run only)."""
import json, shutil, collections, datetime

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
RUN = "/home/devlab1/law_workspace/runs"
log = lambda *a: print(*a, flush=True)

chk = json.load(open(f"{RUN}/weak_recheck.json", encoding="utf-8"))
main = json.load(open(f"{B}/law_bench_main.json", encoding="utf-8"))
byq = {m["qid"]: m for m in main}
chunks = set()
for line in open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8"):
    chunks.add(json.loads(line)["chunk_id"])
ranks = json.load(open(f"{B}/rerank_result.json", encoding="utf-8"))
cands = {e["qid"]: set(e["rerank_top"]) for e in ranks["per_q"]}
graph = json.load(open(f"{R}/provenance/temporal_graph.json", encoding="utf-8"))
LAW = {L["law_id"]: L for L in graph["laws"]}


def law_of(cid):
    return cid.split("|", 1)[0]


def law_valid(law_id, as_of):
    L = LAW.get(law_id)
    if L is None:
        return True
    vf = datetime.date.fromisoformat(L["valid_from"])
    vt = (datetime.date.fromisoformat(L["valid_to"]) if L["valid_to"] else None)
    a = datetime.date.fromisoformat(as_of)
    return a >= vf and (vt is None or a < vt)


import os
if not os.path.exists(f"{RUN}/main_backup_pass3.json"):
    shutil.copy(f"{B}/law_bench_main.json", f"{RUN}/main_backup_pass3.json")
    log("backup saved -> runs/main_backup_pass3.json")

trail, n_re, n_rej, n_fl, n_ok = [], 0, 0, 0, 0
for qid, v in chk.items():
    m = byq.get(qid)
    if m is None:
        continue
    if v["verdict"] == "reanchor":
        bg = v.get("better_gold")
        if (bg in chunks and bg in cands.get(qid, set())
                and law_valid(law_of(bg), m["as_of"])):
            trail.append({"qid": qid, "from": m["gold_ids"], "to": [bg],
                          "evidence": v.get("evidence", ""),
                          "reason": v.get("reason", ""),
                          "judge": "qwen3:14b-pass3"})
            m["gold_ids"] = [bg]
            m["gold_tier"] = "regolded"
            m["weak_review"] = "pass3-reanchored"
            n_re += 1
        else:
            why = ("chunk-missing" if bg not in chunks else
                   "not-in-candidates" if bg not in cands.get(qid, set()) else
                   "outside-validity-window")
            m["weak_review"] = "pass3-reanchor-rejected"
            m["weak_review_reason"] = f"{why}: {str(v.get('reason', ''))[:160]}"
            n_rej += 1
    elif v["verdict"] == "flag":
        m["gold_tier"] = "flagged"
        m["weak_review"] = "pass3-flagged"
        m["weak_review_reason"] = str(v.get("reason", ""))[:200]
        n_fl += 1
    else:
        m["weak_review"] = "pass3-ok"
        n_ok += 1

json.dump(main, open(f"{B}/law_bench_main.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"meta": {"judge": "qwen3:14b-pass3", "n_verdicts": len(chk),
                    "n_reanchored": n_re, "n_reanchor_rejected": n_rej,
                    "n_flagged": n_fl, "n_confirmed_ok": n_ok,
                    "guardrails": ["chunk-exists", "in-stored-candidates",
                                   "validity-window"]},
           "reanchors": trail},
          open(f"{B}/weak_gold_reanchor.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log(f"reanchored: {n_re} | rejected: {n_rej} | flagged: {n_fl} | ok: {n_ok}")
log("main tiers:", dict(collections.Counter(m["gold_tier"] for m in main)))
log("WEAK_APPLY_V2_DONE")
