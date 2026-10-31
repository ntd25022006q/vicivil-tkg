#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect extension stages into release-ready benchmark artifacts.
Run AFTER law_bench_extend.py finishes. Writes:
  benchmark/law_bench_extension.json        - questions + gold_tier (+ regolded_from)
  benchmark/extension_question_vectors.json - qid -> b64 float32 (768d)
  benchmark/extension_audit1.json           - round-1 judge results
  benchmark/extension_audit14.json          - deep round results
  benchmark/extension_regold.json           - re-anchoring trail
  benchmark/extension_asof.json             - as_of validation fixes
Nothing else in the release tree is touched.
"""
import json, os

W = "/home/devlab1/law_workspace"
R = f"{W}/hf_release"
RUN = f"{W}/runs/extension"
B = f"{R}/benchmark"

load = lambda n: json.load(open(f"{RUN}/{n}.json", encoding="utf-8"))
G = load("G")
V = load("V")
if len(V) < len(G):
    print(f"V incomplete: {len(V)}/{len(G)} — rerun after the generator finishes")
    raise SystemExit(2)
A1 = load("A1")
A2 = load("A2")
RG = load("R")
AS = load("O")
log = lambda *a: print(*a, flush=True)

def tier_of(qid):
    deep = A2.get(qid, {}).get("usable")
    r1 = A1.get(qid, {}).get("usable")
    if RG.get(qid, {}).get("regolded_to"):
        return "regolded"
    if deep == "yes" or (deep is None and r1 == "yes"):
        return "verified"
    return "flagged"

out = []
for g in G:
    qid = g["qid"]
    t = tier_of(qid)
    row = {"qid": qid, "as_of": g["as_of"], "question": g["question"],
           "gold_ids": g["gold_ids"], "hint": g["hint"], "law_id": g["law_id"],
           "gold_tier": t}
    if RG.get(qid, {}).get("regolded_to"):
        row["gold_ids"] = [RG[qid]["regolded_to"]]
        row["regolded_from"] = g["gold_ids"][0]
        row["hint"] = "extension cohort (weak gold, disclosed; re-anchored)"
    out.append(row)

import collections
cnt = collections.Counter(r["gold_tier"] for r in out)
log("tiers:", dict(cnt), "| total:", len(out))

json.dump(out, open(f"{B}/law_bench_extension.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(V, open(f"{B}/extension_question_vectors.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(A1, open(f"{B}/extension_audit1.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(A2, open(f"{B}/extension_audit14.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(RG, open(f"{B}/extension_regold.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(AS, open(f"{B}/extension_asof.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("COLLECT DONE:", len(out), "questions -> benchmark/law_bench_extension.json")
