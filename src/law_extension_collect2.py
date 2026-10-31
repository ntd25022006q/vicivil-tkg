#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect extension round-2 stages into release-ready benchmark artifacts,
mirroring src/law_extension_collect.py (round 1) plus a cross-cohort
near-duplicate audit that round 1 did not have. Run AFTER law_bench_extend2.py
finishes (EXTEND2_STAGES_DONE in runs/extension2/extension2_run.log).

Writes (nothing else in the release tree is touched):
  benchmark/law_bench_extension2.json        - validated questions + gold_tier
  benchmark/extension2_question_vectors.json - qid -> b64 float32 (768d)
  benchmark/extension2_audit1.json           - first-round judge results
  benchmark/extension2_audit14.json          - deep-round judge results
  benchmark/extension2_regold.json           - re-anchoring trail
  benchmark/extension2_asof.json             - as_of validation trail
  benchmark/extension2_flagged.json          - quarantined failed questions
  benchmark/extension2_dedup_audit.json      - cross-cohort near-duplicate audit

Validation rule (identical to round 1): a question enters the benchmark only
with gold_tier "verified" (deep judge usable=yes) or "regolded" (re-anchored to
a confirmed chunk). Everything else is quarantined with the full audit trail
and NEVER part of any benchmark metric. Additional quarantine trigger here:
cosine similarity > 0.95 against any question already published in the
benchmark (281-question core or the round-1 extension cohort)."""
import base64, json
from array import array

import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/hf_release"
RUN = f"{W}/runs/extension2"
B = f"{R}/benchmark"

load = lambda n: json.load(open(f"{RUN}/{n}.json", encoding="utf-8"))
G, V, A1, A2, RG, AS = load("G"), load("V"), load("A1"), load("A2"), load("R"), load("O")
log = lambda *a: print(*a, flush=True)
assert len(V) >= len(G), f"vectors incomplete: {len(V)}/{len(G)}"

DUPLICATE_COS = 0.95


def decode_vec(b64):
    a = array("f")
    a.frombytes(base64.b64decode(b64))
    return np.asarray(a, dtype="float32")


# ------------------------------------------------------------------ tier rule
def tier_of(qid):
    deep = A2.get(qid, {}).get("usable")
    r1 = A1.get(qid, {}).get("usable")
    if RG.get(qid, {}).get("regolded_to"):
        return "regolded"
    if deep == "yes" or (deep is None and r1 == "yes"):
        return "verified"
    return "flagged"


# ------------------------------------------------- cross-cohort near-dup scan
# Reference pool = PUBLISHED benchmark questions only (core 281 + round-1
# validated 106). Round-1 quarantined vectors are kept in a side pool: a match
# there is recorded in the audit but does not quarantine (nothing published to
# duplicate).
log("cross-cohort duplicate scan vs published benchmark...")
pub_qids = set()
pub_qids.update(q["qid"] for q in json.load(
    open(f"{B}/law_bench_extension.json", encoding="utf-8")))
ref_vecs, side_vecs = {}, {}
for src, fn in (("core281", "question_vectors.json"),
                ("ext1", "extension_question_vectors.json")):
    for k, v in json.load(open(f"{B}/{fn}", encoding="utf-8")).items():
        tag = f"{src}:{k}"
        if src == "core281" or k in pub_qids:
            ref_vecs[tag] = v
        else:
            side_vecs[tag] = v
ref_mat = np.stack([decode_vec(v) for v in ref_vecs.values()])
ref_nrm = ref_mat / (np.linalg.norm(ref_mat, axis=1, keepdims=True) + 1e-9)
side_mat = np.stack([decode_vec(v) for v in side_vecs.values()])
side_nrm = side_mat / (np.linalg.norm(side_mat, axis=1, keepdims=True) + 1e-9)
log(f"  published pool: {len(ref_vecs)} | r1-quarantine pool: {len(side_vecs)}")

dedup_hits, side_hits = {}, {}
for g in G:
    q = decode_vec(V[g["qid"]])
    q = q / (np.linalg.norm(q) + 1e-9)
    sims = ref_nrm @ q
    top = int(np.argmax(sims))
    if sims[top] > DUPLICATE_COS:
        dedup_hits[g["qid"]] = {"match": list(ref_vecs.keys())[top],
                                "cosine": round(float(sims[top]), 4)}
        continue
    if side_vecs:
        ssims = side_nrm @ q
        stop = int(np.argmax(ssims))
        if ssims[stop] > DUPLICATE_COS:
            side_hits[g["qid"]] = {"match_quarantined": list(side_vecs.keys())[stop],
                                   "cosine": round(float(ssims[stop]), 4)}
log(f"  near-duplicates vs published (cos>{DUPLICATE_COS}): {len(dedup_hits)}"
    f" | vs r1-quarantine: {len(side_hits)}")

# --------------------------------------------------------------- split cohorts
validated, flagged = [], []
for g in G:
    qid = g["qid"]
    t = tier_of(qid)
    row = {"qid": qid, "as_of": g["as_of"], "question": g["question"],
           "gold_ids": g["gold_ids"], "hint": g["hint"], "law_id": g["law_id"],
           "gold_tier": t}
    if RG.get(qid, {}).get("regolded_to"):
        row["gold_ids"] = [RG[qid]["regolded_to"]]
        row["regolded_from"] = g["gold_ids"][0]
        row["hint"] = ("extension cohort round 2, 1996-2015 statutes "
                       "(weak gold, disclosed; re-anchored)")
    entry = {"qid": qid, "as_of": g["as_of"], "question": g["question"],
             "gold_ids": g["gold_ids"], "law_id": g["law_id"],
             "gen_model": g.get("gen_model"), "status": "flagged",
             "excluded_from_benchmark": True,
             "audit1": A1.get(qid), "audit14": A2.get(qid),
             "regold_attempt": RG.get(qid)}
    if qid in side_hits:
        entry["duplicate_of_quarantined"] = side_hits[qid]
    if qid in dedup_hits:
        entry["duplicate_of"] = dedup_hits[qid]["match"]
        entry["duplicate_cosine"] = dedup_hits[qid]["cosine"]
        entry["status"] = "flagged-duplicate"
        flagged.append(entry)
    elif t == "flagged":
        flagged.append(entry)
    else:
        validated.append(row)

import collections
cnt_v = collections.Counter(r["gold_tier"] for r in validated)
cnt_f = collections.Counter(e["status"] for e in flagged)
log("validated:", dict(cnt_v), "| quarantined:", dict(cnt_f),
    "| total generated:", len(G))

meta = {"note": ("Questions generated by the extension round-2 pipeline "
                 "(1996-2015 statutes: BLTTDS2004, ND158_2005, ND126_2014) "
                 "whose gold failed the two-tier audit or duplicated an "
                 "already-published question. Published for full transparency "
                 "and scrutiny; NEVER part of any benchmark metric. The "
                 "validated cohort is law_bench_extension2.json."),
        "generated": len(G),
        "validated": len(validated),
        "flagged": len(flagged),
        "duplicate_cos_threshold": DUPLICATE_COS,
        "audit_files": ["extension2_audit1.json", "extension2_audit14.json",
                        "extension2_regold.json", "extension2_dedup_audit.json"]}

json.dump(validated, open(f"{B}/law_bench_extension2.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(V, open(f"{B}/extension2_question_vectors.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(A1, open(f"{B}/extension2_audit1.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(A2, open(f"{B}/extension2_audit14.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(RG, open(f"{B}/extension2_regold.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(AS, open(f"{B}/extension2_asof.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"meta": meta, "questions": flagged},
          open(f"{B}/extension2_flagged.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"meta": {"threshold": DUPLICATE_COS,
                    "published_reference_files": ["question_vectors.json",
                                                  "law_bench_extension.json",
                                                  "extension_question_vectors.json"],
                    "n_published_vectors": len(ref_vecs),
                    "n_quarantine_vectors": len(side_vecs),
                    "n_generated": len(G),
                    "rule": "cos>0.95 vs a PUBLISHED question quarantines the "
                            "generated question; matches against round-1 "
                            "quarantined questions are recorded only"},
           "hits_vs_published": dedup_hits,
           "hits_vs_quarantined": side_hits},
          open(f"{B}/extension2_dedup_audit.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("COLLECT2 DONE:", len(validated), "validated ->",
    "benchmark/law_bench_extension2.json |", len(flagged), "quarantined")
