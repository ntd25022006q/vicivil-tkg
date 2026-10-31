#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-score the published core LLM RAG metrics after pass-3 gold updates.
Stored greedy-decoded answers are unchanged (they never depended on gold);
only cite_acc and span_f1 depend on gold, so both are recomputed from the
stored per-question answers against the updated gold_ids, for every condition.
Also rebuilds benchmark/llm_rag_significance.json from the updated per_q."""
import json, re, unicodedata
from collections import Counter

from scipy.stats import wilcoxon, binomtest

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
log = lambda *a: print(*a, flush=True)


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


goldmap, qtext = {}, {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(open(f"{B}/{fn}", encoding="utf-8")):
        goldmap[q["qid"]] = q["gold_ids"]

chunks = {}
for line in open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8"):
    c = json.loads(line)
    chunks[c["chunk_id"]] = c.get("content", "")

res = json.load(open(f"{B}/llm_rag_result.json", encoding="utf-8"))
changed = 0
for cond, c in res["conditions"].items():
    n = cite_ok = abst = ctx = 0
    f1s, lens = [], []
    for qid, row in c["per_q"].items():
        g = goldmap.get(qid)
        if g is None:
            continue
        n += 1
        ok = bool(cited_articles(row["answer"]) & gold_articles(g))
        if ok != row["cite_ok"]:
            changed += 1
        row["cite_ok"] = ok
        f1 = token_f1(row["answer"],
                      " ".join((chunks.get(x, {}).get("content")
                                if isinstance(chunks.get(x), dict) else chunks.get(x, ""))
                               for x in g))
        if abs(f1 - row["span_f1"]) > 1e-9:
            changed += 1
        row["span_f1"] = round(f1, 4)
        cite_ok += ok
        abst += row["abstain"]
        ctx += row["ctx_hit5"]
        f1s.append(row["span_f1"])
        lens.append(len(toks(row["answer"])))
    c["summary"] = {"n": n, "cite_acc": round(cite_ok / n, 4),
                    "span_f1": round(sum(f1s) / n, 4),
                    "abstain_rate": round(abst / n, 4),
                    "ctx_hit5": round(ctx / n, 4),
                    "mean_ans_tokens": round(sum(lens) / n, 1)}
    log(cond, c["summary"])
res["rescore_note"] = ("cite_acc and span_f1 recomputed from stored greedy "
                       "answers after pass-3 gold updates; abstain and "
                       "ctx_hit5 unchanged (answer/context dependent)")
json.dump(res, open(f"{B}/llm_rag_result.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("cells changed:", changed)

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
sig["note"] = ("rebuilt from stored per_q answers after pass-3 gold updates "
               "(McNemar exact on cite_ok; Wilcoxon wilcox on span_f1)")
json.dump(sig, open(f"{B}/llm_rag_significance.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("significance rebuilt:", json.dumps(
    {k: v.get("mcnemar_cite_p") for k, v in sig.items() if isinstance(v, dict)}))
log("RESCORE_DONE")
