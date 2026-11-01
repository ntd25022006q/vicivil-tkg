#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-score the published core LLM RAG metrics against the APPLIED golds.

This is the v1.0.1 (F6) replacement for the original rescore script, which
kept the run-time ctx_hit5 values recorded BEFORE the gold adjudication chain
(audit bug B5). Differences from the superseded version:

  * ctx_hit5 is RECOMPUTED from benchmark/rag_inputs.json stored contexts
    (base_top5 / tcr_top5 / rr_tcr_top5) intersected with the applied golds;
  * reproduce-then-patch: before writing anything, the recomputation is
    asserted against the summaries currently stored in the artifact; a
    mismatch aborts with exit 1 and nothing is modified;
  * per-question rows are updated in place and the note field records the
    v1.0.1 semantics.

Run on the A30 build host:  python3 src/law_llm_rag_rescore.py [--check]
"""
import json, re, sys, unicodedata
from collections import Counter

from scipy.stats import wilcoxon, binomtest

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
log = lambda *a: print(*a, flush=True)
CHECK_ONLY = "--check" in sys.argv

CTX_KEY = {"rag_hybrid": "base_top5", "rag_hybrid_tcr": "tcr_top5",
           "rag_rerank_tcr": "rr_tcr_top5", "norag": None}


def toks(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.findall(r"[a-zà-ỹđ0-9]+", s)


def token_f1(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return 0.0
    common = sum((Counter(ta) & Counter(tb)).values())
    if common == 0:
        return 0.0
    p, r = common / len(ta), common / len(tb)
    return 2 * p * r / (p + r)


CITE_RE = re.compile(r"điều\s+(\d+[a-z]?)", re.IGNORECASE)


def cited_articles(ans):
    return set(m.lower() for m in CITE_RE.findall(ans or ""))


def gold_articles(gids):
    out = set()
    for g in gids:
        m = re.match(r"[^|]+\|[Dd]ieu(\d+[a-z]?)", g)
        if m:
            out.add(m.group(1).lower())
    return out


goldmap = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(open(f"{B}/{fn}", encoding="utf-8")):
        goldmap[q["qid"]] = q["gold_ids"]

rag = json.load(open(f"{B}/rag_inputs.json", encoding="utf-8"))
chunks = {}
for line in open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8"):
    c = json.loads(line)
    chunks[c["chunk_id"]] = c.get("content", "")

res = json.load(open(f"{B}/llm_rag_result.json", encoding="utf-8"))


def recompute():
    out = {}
    for cond, c in res["conditions"].items():
        n = cite = abst = ctx = 0
        f1s, lens = [], []
        for qid, row in c["per_q"].items():
            g = goldmap.get(qid)
            if g is None:
                continue
            n += 1
            ok = bool(cited_articles(row["answer"]) & gold_articles(g))
            cite += ok
            gt = " ".join(chunks.get(x, "") for x in g)
            f1s.append(round(token_f1(row["answer"], gt), 4))
            abst += row["abstain"]
            key = CTX_KEY[cond]
            lst = (rag.get(qid, {}).get(key) if key else None) or []
            ctx += bool(set(lst) & set(g))
            lens.append(len(toks(row["answer"])))
        out[cond] = {"n": n, "cite_acc": round(cite / n, 4),
                     "span_f1": round(sum(f1s) / n, 4),
                     "abstain_rate": round(abst / n, 4),
                     "ctx_hit5": round(ctx / n, 4),
                     "mean_ans_tokens": round(sum(lens) / n, 1)}
    return out


post = recompute()
mismatch = []
for cond, s in post.items():
    cur = res["conditions"][cond]["summary"]
    for k in ("n", "cite_acc", "span_f1", "abstain_rate", "ctx_hit5"):
        if s[k] != cur.get(k):
            mismatch.append(f"{cond}.{k}: stored={cur.get(k)} recomputed={s[k]}")
            log(f"  DIFF {cond}.{k}: stored={cur.get(k)} recomputed={s[k]}")

if mismatch:
    if CHECK_ONLY:
        log("CHECK FAILED — stored artifact disagrees with recomputation")
        sys.exit(1)
    log(f"{len(mismatch)} cells differ -> patching (reproduce-then-patch)")
else:
    log("recomputation matches the stored artifact exactly; nothing to patch")

if CHECK_ONLY:
    log("CHECK OK")
    sys.exit(0)

for cond, c in res["conditions"].items():
    for qid, row in c["per_q"].items():
        g = goldmap.get(qid)
        if g is None:
            continue
        row["cite_ok"] = bool(cited_articles(row["answer"]) & gold_articles(g))
        row["span_f1"] = round(token_f1(
            row["answer"], " ".join(chunks.get(x, "") for x in g)), 4)
        key = CTX_KEY[cond]
        lst = (rag.get(qid, {}).get(key) if key else None) or []
        row["ctx_hit5"] = bool(set(lst) & set(g))
    c["summary"] = post[cond]

res["rescore_note"] = ("v1.0.1: cite_acc, span_f1 and ctx_hit5 recomputed from "
                       "stored greedy answers/contexts against the APPLIED "
                       "adjudicated golds (the v1.0.0 rescore kept run-time "
                       "ctx_hit5, which predated the gold chain); abstain "
                       "unchanged (answer-dependent).")
tmp = f"{B}/llm_rag_result.json.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
import os
os.replace(tmp, f"{B}/llm_rag_result.json")
log("llm_rag_result.json rescored")

# ---- significance rebuild ----
c = {k: v["per_q"] for k, v in res["conditions"].items()}
sig = {}


def mcnemar(a_keys, b_keys, tag):
    common = sorted(set(c[a_keys]) & set(c[b_keys]))
    b01 = b10 = 0
    f1a, f1b = [], []
    for q in common:
        if c[a_keys][q]["cite_ok"] and not c[b_keys][q]["cite_ok"]:
            b10 += 1
        if c[b_keys][q]["cite_ok"] and not c[a_keys][q]["cite_ok"]:
            b01 += 1
        f1a.append(c[a_keys][q]["span_f1"])
        f1b.append(c[b_keys][q]["span_f1"])
    p = binomtest(b10, b01 + b10, 0.5).pvalue if b01 + b10 else 1.0
    st, wp = ((0.0, 1.0) if not any(x != y for x, y in zip(f1a, f1b))
              else wilcoxon(f1b, f1a, zero_method="wilcox"))
    sig[tag] = {"n_common": len(common), "mcnemar_cite_b01": b01,
                "mcnemar_cite_b10": b10, "mcnemar_cite_p": float(p),
                "wilcoxon_span_f1_p": float(wp),
                "delta_cite_acc": round(
                    sum(c[b_keys][q]["cite_ok"] for q in common) / len(common)
                    - sum(c[a_keys][q]["cite_ok"] for q in common) / len(common), 4),
                "delta_span_f1": round(
                    sum(c[b_keys][q]["span_f1"] for q in common) / len(common)
                    - sum(c[a_keys][q]["span_f1"] for q in common) / len(common), 4)}


mcnemar("rag_hybrid", "rag_hybrid_tcr", "rag_hybrid_vs_rag_hybrid_tcr")
mcnemar("rag_hybrid", "rag_rerank_tcr", "rag_hybrid_vs_rag_rerank_tcr")
mcnemar("norag", "rag_hybrid", "norag_vs_rag_hybrid")
mcnemar("norag", "rag_hybrid_tcr", "norag_vs_rag_hybrid_tcr")
sig["note"] = ("rebuilt from stored per_q answers against the APPLIED golds "
               "(McNemar exact on cite_ok; Wilcoxon wilcox on span_f1)")
tmp = f"{B}/llm_rag_significance.json.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(sig, f, ensure_ascii=False, indent=1)
os.replace(tmp, f"{B}/llm_rag_significance.json")
log("significance rebuilt:", json.dumps(
    {k: v.get("mcnemar_cite_p") for k, v in sig.items() if isinstance(v, dict)}))
log("RESCORE_DONE")
