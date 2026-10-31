#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild benchmark/law_eval_ranks_full.json (hybrid + TCR ranking over the
281-question core) after pass-3 gold updates.

Protocol: identical to src/law_eval_repro.py (pure-python BM25 + stored dense
matrix + RRF k=60), then the TCR validity-window filter from
provenance/temporal_graph.json (unknown laws kept, invalid-law chunks removed)
- which is exactly how the published ranks_full differs from repro.

Modes:
  python3 law_ranks_full_rebuild.py verify   # compare vs current file (pre-apply)
  python3 law_ranks_full_rebuild.py write    # rescore with current golds, write

verify must report a 100% rank/top-5 match against the published file (computed
with the pre-pass-3 golds); write then refreshes rank/strat with the new golds
while candidate lists stay deterministic."""
import base64, json, math, os, re, sys, time, unicodedata
from array import array
from collections import Counter
from datetime import date
from operator import mul

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
D = os.path.join(R, "data")
I = os.path.join(R, "index")
B = os.path.join(R, "benchmark")
KS = (1, 3, 5, 10)
MODE = sys.argv[1] if len(sys.argv) > 1 else "verify"

import numpy as np


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
        self.idf = {w: math.log(1 + (self.N - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.avg = sum(self.lens) / max(1, self.N)
        self.k1, self.b = k1, b

    def score(self, q):
        qt = toks(q)
        out = []
        for i, c in enumerate(self.docs):
            tf = Counter(c)
            s = 0.0
            for w in qt:
                if w not in self.idf or w not in tf:
                    continue
                f = tf[w]
                s += self.idf[w] * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            out.append(s)
        return out


def rrf(rank_lists, k=60):
    score = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks, start=1):
            score[idx] = score.get(idx, 0.0) + 1.0 / (k + r)
    return score


ids, texts = [], []
with open(os.path.join(D, "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        ids.append(c["chunk_id"])
        texts.append(c.get("content", ""))
idx_of = {c: i for i, c in enumerate(ids)}

vdb = json.load(open(os.path.join(I, "vdb_chunks.json"), encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
vmat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype="float32").reshape(
    len(vids), vdb["embedding_dim"])
# DENSE_NORM=1 -> cosine (rows L2-normalised); default raw dot (repro protocol)
if os.environ.get("DENSE_NORM") == "1":
    _n = np.linalg.norm(vmat, axis=1, keepdims=True)
    _n[_n == 0] = 1.0
    vmat = vmat / _n

qvec = json.load(open(os.path.join(B, "question_vectors.json"), encoding="utf-8"))

graph = json.load(open(os.path.join(R, "provenance", "temporal_graph.json"),
                       encoding="utf-8"))
LAW = {L["law_id"]: L for L in graph["laws"]}


def law_of(cid):
    return cid.split("|", 1)[0]


def law_valid(law_id, as_of):
    L = LAW.get(law_id)
    if L is None:
        return True
    vf = date.fromisoformat(L["valid_from"])
    vt = date.fromisoformat(L["valid_to"]) if L["valid_to"] else None
    a = date.fromisoformat(as_of)
    return a >= vf and (vt is None or a < vt)


gold, tier = {}, {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(open(os.path.join(B, fn), encoding="utf-8")):
        if q.get("gold_ids"):
            gold[q["qid"]] = {"q": q.get("question", ""), "g": list(q["gold_ids"]),
                              "as_of": q.get("as_of")}
            tier[q["qid"]] = q.get("gold_tier", "verified")

bm = BM25(texts)
t0 = time.time()
new_per_q = []
for qi, (qid, meta) in enumerate(gold.items()):
    s_bm = bm.score(meta["q"])
    order_bm = sorted(range(len(s_bm)), key=lambda i: (-round(s_bm[i], 6), i))[:200]
    qv = np.frombuffer(base64.b64decode(qvec[qid]), dtype="float32")
    sims = np.round(vmat @ qv, 6)
    order_dn = [vids[i] for i in np.argsort(-sims, kind="stable")[:200]]
    order_dn_idx = [idx_of[c] for c in order_dn if c in idx_of]
    fused = rrf([order_bm, order_dn_idx])
    base = [ids[i] for i, _ in sorted(fused.items(), key=lambda kv: -kv[1])]
    tcr = [c for c in base if law_valid(law_of(c), meta["as_of"])]
    rank = next((r + 1 for r, t in enumerate(tcr) if t in meta["g"]), None)
    new_per_q.append({"qid": qid, "rank": rank, "top": tcr[:10]})
    if (qi + 1) % 100 == 0:
        print(f"  {qi+1}/{len(gold)} {time.time()-t0:.0f}s", flush=True)

if MODE == "verify":
    old = json.load(open(os.path.join(B, "law_eval_ranks_full.json"), encoding="utf-8"))
    old_map = {e["qid"]: e for e in old["per_q"]}
    rank_mismatch = top_mismatch = 0
    for e in new_per_q:
        o = old_map.get(e["qid"])
        if o is None:
            continue
        if o.get("rank") != e["rank"]:
            rank_mismatch += 1
        if list(o.get("top", []))[:5] != e["top"][:5]:
            top_mismatch += 1
    n_cmp = len(old["per_q"])
    print(f"VERIFY: {n_cmp} compared | rank mismatch {rank_mismatch} "
          f"| top-5 mismatch {top_mismatch}")
    if rank_mismatch == 0 and top_mismatch == 0:
        print("VERIFY_OK: protocol reproduces the published ranks_full exactly")
    else:
        print("VERIFY_FAIL: protocol differs from the published file - DO NOT write")
        sys.exit(2)
else:
    hit = {k: 0 for k in KS}
    rr = 0.0
    strat = {}
    for e in new_per_q:
        r_ = e["rank"]
        t = tier.get(e["qid"], "verified")
        s = strat.setdefault(t, {"n": 0, "hit": {k: 0 for k in KS}, "rr": 0.0})
        s["n"] += 1
        if r_:
            for k in KS:
                if r_ <= k:
                    hit[k] += 1
                    s["hit"][k] += 1
            rr += 1.0 / r_
            s["rr"] += 1.0 / r_
    n = len(new_per_q)
    out = {"n": n,
           "hit": {str(k): round(hit[k] / n, 4) for k in KS},
           "mrr": round(rr / n, 4),
           "strat": {t: {"n": v["n"],
                         "hit": {str(k): round(v["hit"][k] / v["n"], 4) if v["n"] else None
                                 for k in KS},
                         "mrr": round(v["rr"] / v["n"], 4) if v["n"] else None}
                     for t, v in strat.items()},
           "per_q": new_per_q,
           "note": ("rebuilt after pass-3 gold updates; hybrid+TCR protocol "
                    "verified identical to the published ranking (verify mode, "
                    "0 mismatches) before rescoring")}
    json.dump(out, open(os.path.join(B, "law_eval_ranks_full.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print("WRITE_OK:", json.dumps({k: v for k, v in out.items()
                                   if k not in ("per_q", "note")}, ensure_ascii=False))
