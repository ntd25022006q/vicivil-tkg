#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paired significance tests for LLM RAG: hybrid vs hybrid_tcr (and vs rerank_tcr)."""
import json, os

from scipy.stats import wilcoxon

B = os.path.join(os.environ.get(
    "VICIVIL_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "benchmark")
res = json.load(open(f"{B}/llm_rag_result.json"))
conds = res["conditions"]

out = {}
pairs = [("rag_hybrid", "rag_hybrid_tcr"), ("rag_hybrid", "rag_rerank_tcr"),
         ("norag", "rag_hybrid"), ("rag_hybrid_tcr", "rag_rerank_tcr")]
for a, b in pairs:
    pa, pb = conds[a]["per_q"], conds[b]["per_q"]
    common = sorted(set(pa) & set(pb))
    f1a = [pa[q]["span_f1"] for q in common]
    f1b = [pb[q]["span_f1"] for q in common]
    ca = [1 if pa[q]["cite_ok"] else 0 for q in common]
    cb = [1 if pb[q]["cite_ok"] else 0 for q in common]
    # McNemar
    b01 = sum(1 for x, y in zip(ca, cb) if x == 0 and y == 1)
    b10 = sum(1 for x, y in zip(ca, cb) if x == 1 and y == 0)
    try:
        from scipy.stats import binomtest
        mcnemar_p = binomtest(b01, b01 + b10, 0.5).pvalue if (b01 + b10) > 0 else 1.0
    except Exception:
        mcnemar_p = None
    try:
        wf1 = float(wilcoxon(f1b, f1a, zero_method="wilcox").pvalue)
    except Exception as e:
        wf1 = None
    key = f"{a}_vs_{b}"
    out[key] = {
        "n_common": len(common),
        "mcnemar_cite_b01": b01, "mcnemar_cite_b10": b10,
        "mcnemar_cite_p": mcnemar_p,
        "wilcoxon_span_f1_p": wf1,
        "delta_cite_acc": round(sum(cb) / len(cb) - sum(ca) / len(ca), 4),
        "delta_span_f1": round(sum(f1b) / len(f1b) - sum(f1a) / len(f1a), 4),
    }
    print(key, json.dumps(out[key]))

json.dump(out, open(f"{B}/llm_rag_significance.json", "w"), ensure_ascii=False, indent=1)
print("saved llm_rag_significance.json")
