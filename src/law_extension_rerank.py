#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rerank stage for the extension cohort, mirroring the published protocol:
BAAI/bge-reranker-v2-m3 over the top-30 base-hybrid candidates, then the
TCR validity filter applied to the reranked list. Writes:
  benchmark/extension_rerank_result.json  (metrics + per-q top-30 lists)
  benchmark/extension_rag_inputs.json     (top-5 context per variant, for the
                                           end-to-end LLM QA step)
"""
import json, sys, time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
# Cohort selection via argv (defaults keep the published round-1 behaviour):
#   argv[1] eval-ranks file, argv[2] question file, argv[3] output file,
#   argv[4] rag-inputs output file
EFILE = sys.argv[1] if len(sys.argv) > 1 else f"{B}/extension_eval_ranks.json"
QFILE = sys.argv[2] if len(sys.argv) > 2 else f"{B}/law_bench_extension.json"
OFILE = sys.argv[3] if len(sys.argv) > 3 else f"{B}/extension_rerank_result.json"
RIFILE = sys.argv[4] if len(sys.argv) > 4 else f"{B}/extension_rag_inputs.json"
t00 = time.time()
log = lambda *a: print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

ev = json.load(open(EFILE, encoding="utf-8"))
qs = {g["qid"]: g for g in json.load(open(QFILE, encoding="utf-8"))}
graph = json.load(open(f"{R}/provenance/temporal_graph.json", encoding="utf-8"))
LAW = {L["law_id"]: L for L in graph["laws"]}

import datetime as dt


def law_valid(law_id, as_of):
    L = LAW.get(law_id)
    if L is None:
        return True
    vf = dt.date.fromisoformat(L["valid_from"])
    vt = dt.date.fromisoformat(L["valid_to"]) if L["valid_to"] else None
    a = dt.date.fromisoformat(as_of)
    return a >= vf and (vt is None or a < vt)


def law_of(chunk_id):
    return chunk_id.split("|", 1)[0]


chunks = {}
with open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        chunks[c["chunk_id"]] = c.get("content", "")

MODEL = "BAAI/bge-reranker-v2-m3"
log("load reranker...")
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL, dtype=torch.float16, attn_implementation="sdpa", device_map="cuda")
model.eval()

KS = (1, 3, 5, 10)


def metrics(ranked, gold):
    first = next((r for r, c in enumerate(ranked, 1) if c in gold), None)
    return {k: int(first is not None and first <= k) for k in KS}, (1.0 / first if first else 0.0), first


BATCH = 64
per_q = {}
res = {"model": MODEL, "params": {"candidates": 30, "batch": BATCH, "dtype": "float16"},
       "rerank": {"h": {}, "mrr": 0.0, "rr": []}, "rerank_tcr": {"h": {}, "mrr": 0.0, "rr": []}}
pairs, meta = [], []
for qid, g in qs.items():
    for cid in ev["per_q"][qid]["base_top30"]:
        pairs.append((g["question"], chunks.get(cid, "")[:1500]))
        meta.append((qid, cid))
log(f"{len(pairs)} pairs to score")

scores = []
with torch.inference_mode():
    for i in range(0, len(pairs), BATCH):
        b = pairs[i:i + BATCH]
        enc = tok([b[0] for b in b], [b[1] for b in b], padding=True, truncation=True,
                  max_length=1024, return_tensors="pt").to("cuda")
        s = model(**enc).logits.view(-1).float().cpu().tolist()
        scores.extend(s)
        if (i // BATCH) % 10 == 0:
            log(f"  {i + len(b)}/{len(pairs)}")

by_q = {}
for (qid, cid), s in zip(meta, scores):
    by_q.setdefault(qid, []).append((s, cid))

for qid, lst in by_q.items():
    lst.sort(key=lambda t: (-t[0], t[1]))
    rr = [c for _, c in lst]
    gold = set(qs[qid]["gold_ids"])
    as_of = qs[qid]["as_of"]
    rt = [c for c in rr if law_valid(law_of(c), as_of)]
    rt += [c for c in rr if c not in rt]
    bh, bm, bf = metrics(rr, gold)
    th, tm, tf = metrics(rt, gold)
    for k in KS:
        res["rerank"]["h"][k] = res["rerank"]["h"].get(k, 0) + bh[k]
        res["rerank_tcr"]["h"][k] = res["rerank_tcr"]["h"].get(k, 0) + th[k]
    res["rerank"]["mrr"] += bm
    res["rerank_tcr"]["mrr"] += tm
    res["rerank"]["rr"].append(bm)
    res["rerank_tcr"]["rr"].append(tm)
    per_q[qid] = {"rerank_top30": rr[:30], "rerank_tcr_top30": rt[:30],
                  "first_rerank": bf, "first_rerank_tcr": tf}

n = len(by_q)
for v in ("rerank", "rerank_tcr"):
    res[v]["hit_at_k"] = {str(k): round(res[v]["h"][k] / n, 4) for k in KS}
    res[v]["mrr"] = round(res[v]["mrr"] / n, 4)
    del res[v]["h"]
    log(v, res[v]["hit_at_k"], "mrr", res[v]["mrr"])

from scipy.stats import wilcoxon
import numpy as np
rrr = np.asarray(res["rerank"]["rr"], dtype="float64")
rrt = np.asarray(res["rerank_tcr"]["rr"], dtype="float64")
base_rr, tcr_rr = [], []
for qid in per_q:
    base_rr.append(1.0 / ev["per_q"][qid]["first_base"] if ev["per_q"][qid]["first_base"] else 0.0)
    tcr_rr.append(1.0 / ev["per_q"][qid]["first_tcr"] if ev["per_q"][qid]["first_tcr"] else 0.0)
base_rr = np.asarray(base_rr)
tcr_rr = np.asarray(tcr_rr)
res["wilcoxon"] = {
    "rerank_vs_base": {k: float(v) for k, v in zip(("stat", "p"), wilcoxon(rrr, base_rr, zero_method="wilcox"))},
    "rerank_tcr_vs_tcr": {k: float(v) for k, v in zip(("stat", "p"), wilcoxon(rrt, tcr_rr, zero_method="wilcox"))},
}
log("wilcoxon:", json.dumps(res["wilcoxon"]))

res["per_q"] = per_q
json.dump(res, open(OFILE, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- rag inputs for the LLM QA step (top-5 per variant) ----
ri = {}
for qid, g in qs.items():
    ri[qid] = {
        "question": g["question"],
        "gold_ids": g["gold_ids"],
        "as_of": g["as_of"],
        "base_top5": ev["per_q"][qid]["base_top30"][:5],
        "tcr_top5": ev["per_q"][qid]["tcr_top30"][:5],
        "rr_tcr_top5": per_q[qid]["rerank_tcr_top30"][:5],
    }
json.dump(ri, open(RIFILE, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("RERANK DONE ->", OFILE, "+", RIFILE)

