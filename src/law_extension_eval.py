#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retrieval evaluation on the extension cohort, mirroring src/law_eval_repro.py
protocol exactly: BM25 (pure python) + stored dense chunk matrix (768d, b64) +
RRF k=60; scoring = strict gold-chunk-id matching. Two variants measured in the
same run: base hybrid, and base + TCR (validity-window filter from
provenance/temporal_graph.json; laws missing from the graph are kept).
Significance: paired Wilcoxon on reciprocal rank of the first gold hit.
Output: benchmark/extension_eval_ranks.json  (also stores top-30 candidate ids
per question per variant so the rerank step can reuse them)."""
import base64, json, os, re, sys, unicodedata
from array import array
from collections import Counter
from operator import mul

import numpy as np
from scipy.stats import wilcoxon

R = "/home/devlab1/law_workspace/hf_release"
B = f"{R}/benchmark"
# Cohort selection via argv (defaults keep the published round-1 behaviour):
#   argv[1] question file, argv[2] question-vector file, argv[3] output file
QFILE = sys.argv[1] if len(sys.argv) > 1 else f"{B}/law_bench_extension.json"
VFILE = sys.argv[2] if len(sys.argv) > 2 else f"{B}/extension_question_vectors.json"
OFILE = sys.argv[3] if len(sys.argv) > 3 else f"{B}/extension_eval_ranks.json"
KS = (1, 3, 5, 10)
log = lambda *a: print(*a, flush=True)


def toks(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.findall(r"[a-zà-ỹđ0-9]+", s)


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.docs = [toks(d) for d in docs]
        self.N = len(self.docs)
        df = Counter()
        self.lens = []
        for t in self.docs:
            self.lens.append(len(t))
            for w in set(t):
                df[w] += 1
        self.idf = {w: math_log1p((self.N - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.avg = sum(self.lens) / max(1, self.N)
        self.k1, self.b = k1, b

    def rank(self, q, n=30):
        qt = toks(q)
        scored = []
        for i, c in enumerate(self.docs):
            s = 0.0
            tf = None
            for w in qt:
                if w not in self.idf:
                    continue
                if tf is None:
                    tf = Counter(c)
                f = tf.get(w, 0)
                if not f:
                    continue
                s += self.idf[w] * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            scored.append((s, i))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [i for _, i in scored[:n]]


def math_log1p(x):
    import math
    return math.log1p(x)


def rrf(rank_lists, k=60):
    score = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks, start=1):
            score[idx] = score.get(idx, 0.0) + 1.0 / (k + r)
    return score


log("load chunks...")
ids, texts = [], []
with open(f"{R}/data/civil_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        ids.append(c["chunk_id"])
        texts.append(c.get("content", ""))
idx_of = {c: i for i, c in enumerate(ids)}

log("load dense matrix...")
vdb = json.load(open(f"{R}/index/vdb_chunks.json", encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
vmat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype="float32").reshape(len(vids), 768)
vidx_of = {c: i for i, c in enumerate(vids)}
qnrm = np.linalg.norm(vmat, axis=1)
qnrm[qnrm == 0] = 1.0

log("load graph validity...")
graph = json.load(open(f"{R}/provenance/temporal_graph.json", encoding="utf-8"))
LAW = {L["law_id"]: L for L in graph["laws"]}

import datetime as dt


def law_valid(law_id, as_of):
    L = LAW.get(law_id)
    if L is None:
        return True                      # unknown law -> keep (main TCR behavior)
    vf = dt.date.fromisoformat(L["valid_from"])
    vt = dt.date.fromisoformat(L["valid_to"]) if L["valid_to"] else None
    a = dt.date.fromisoformat(as_of)
    return a >= vf and (vt is None or a < vt)


def law_of(chunk_id):
    return chunk_id.split("|", 1)[0]


log("load questions + gold + qvecs...")
qs = json.load(open(QFILE, encoding="utf-8"))
qv = json.load(open(VFILE, encoding="utf-8"))

log("BM25 index...")
bm25 = BM25(texts)

def decode_vec(b64):
    a = array("f")
    a.frombytes(base64.b64decode(b64))
    return np.asarray(a, dtype="float32")


def metrics(ranked, gold_set):
    first = None
    for r, cid in enumerate(ranked, start=1):
        if cid in gold_set:
            first = r
            break
    hit = {k: int(first is not None and first <= k) for k in KS}
    mrr = (1.0 / first) if first else 0.0
    return hit, mrr, first


per_q = {}
res = {"base": {"h": Counter(), "mrr": 0.0, "rr": []},
       "tcr": {"h": Counter(), "mrr": 0.0, "rr": []}}
for g in qs:
    qid, as_of = g["qid"], g["as_of"]
    gold = set(g["gold_ids"])
    qvec = decode_vec(qv[qid])
    sims = (vmat @ qvec) / (qnrm * (np.linalg.norm(qvec) + 1e-9))
    dense = [vids[i] for i in np.argsort(-sims, kind="stable")[:200]]
    bm = [ids[i] for i in bm25.rank(g["question"], n=200)]
    fused = sorted(rrf([dense, bm]).items(), key=lambda t: (-t[1], t[0]))
    base_rank = [c for c, _ in fused]

    kept = [c for c in base_rank if law_valid(law_of(c), as_of)]
    unknown = [c for c in base_rank if law_of(c) not in LAW]
    tcr_rank = kept + [c for c in unknown if c not in kept]

    bhit, bmrr, bfirst = metrics(base_rank, gold)
    thit, tmrr, tfirst = metrics(tcr_rank, gold)
    for k in KS:
        res["base"]["h"][k] += bhit[k]
        res["tcr"]["h"][k] += thit[k]
    res["base"]["mrr"] += bmrr
    res["tcr"]["mrr"] += tmrr
    res["base"]["rr"].append(bmrr)
    res["tcr"]["rr"].append(tmrr)
    per_q[qid] = {"as_of": as_of, "gold_tier": g["gold_tier"],
                  "base_top30": base_rank[:30], "tcr_top30": tcr_rank[:30],
                  "first_base": bfirst, "first_tcr": tfirst}

n = len(qs)
out = {"n": n, "protocol": "strict gold-chunk-id matching, BM25+dense(768d stored)+RRF k=60",
       "embedder": "embeddinggemma:300m via ollama (same engine as the 281 originals)"}
for variant in ("base", "tcr"):
    out[variant] = {
        "hit_at_k": {str(k): round(res[variant]["h"][k] / n, 4) for k in KS},
        "mrr": round(res[variant]["mrr"] / n, 4),
    }
    log(variant, out[variant])

st = {t: {"n": 0, "hit_at_k": Counter(), "mrr": 0.0} for t in ("verified", "regolded", "flagged")}
for g in qs:
    qid = g["qid"]
    t = g["gold_tier"]
    f = per_q[qid]["first_tcr"]
    st[t]["n"] += 1
    if f:
        for k in KS:
            st[t]["hit_at_k"][k] += int(f <= k)
        st[t]["mrr"] += 1.0 / f
out["tcr_stratified"] = {t: {"n": v["n"],
                             "hit_at_k": {str(k): round(v["hit_at_k"][k] / v["n"], 4) if v["n"] else None for k in KS},
                             "mrr": round(v["mrr"] / v["n"], 4) if v["n"] else None}
                         for t, v in st.items()}
log("tcr stratified:", json.dumps(out["tcr_stratified"]))

rrb = np.asarray(res["base"]["rr"], dtype="float64")
rrt = np.asarray(res["tcr"]["rr"], dtype="float64")
d = rrt - rrb
if np.any(d != 0):
    stat, p = wilcoxon(rrt, rrb, zero_method="wilcox")
else:
    stat, p = 0.0, 1.0
out["wilcoxon_tcr_vs_base"] = {"stat": float(stat), "p": float(p), "n_pairs": int((d != 0).sum())}
log("wilcoxon:", out["wilcoxon_tcr_vs_base"])

out["per_q"] = per_q
json.dump(out, open(OFILE, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("EVAL DONE ->", OFILE)

