#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCR constraint-hardness sensitivity sweep (CPU only, stored vectors).

Interpolates the temporal-constraint filter between OFF and HARD:
  alpha = 0.0 : expired-law candidates keep their full base RRF score  (= baseline)
  alpha = 1.0 : expired-law candidates sink to score 0                  (≈ TCR-hard)
  in between  : expired candidates are down-weighted by (1 - alpha)
Valid candidates are untouched. Mirrors the BM25 (k1=1.2, b=0.75) + stored
dense vectors + RRF(k=60) baseline of src/law_eval_repro.py exactly.

Output: benchmark/tcr_weight_sensitivity.json
"""
import base64, json, math, os, re, time, unicodedata
from array import array
from collections import Counter

R = os.environ.get("VICIVIL_ROOT",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D, I, B, P = f"{R}/data", f"{R}/index", f"{R}/benchmark", f"{R}/provenance"
OUT = f"{B}/tcr_weight_sensitivity.json"
KS = (1, 3, 5, 10)
ALPHAS = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]

import numpy as np
from scipy.stats import wilcoxon

t00 = time.time()


def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)


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
        self._tf = [None] * self.N

    def score(self, q):
        qt = toks(q)
        out = []
        for i, t in enumerate(self.docs):
            if self._tf[i] is None:
                self._tf[i] = Counter(t)
            tf = self._tf[i]
            s = 0.0
            for w in qt:
                if w not in self.idf or w not in tf:
                    continue
                f = tf[w]
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            out.append(s)
        return out


def rrf(rank_lists, k=60):
    score = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks, start=1):
            score[idx] = score.get(idx, 0.0) + 1.0 / (k + r)
    return score


def top_dense(qvec, vmat, vids, n=200):
    sims = np.round(vmat @ qvec, 6)
    idx = np.argsort(-sims, kind="stable")[:n]
    return [vids[i] for i in idx]


log("load chunks...")
ids, texts = [], []
with open(f"{D}/civil_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        ids.append(c["chunk_id"])
        texts.append(c.get("content", ""))
idx_of = {cid: i for i, cid in enumerate(ids)}

log("load vectors...")
vdb = json.load(open(f"{I}/vdb_chunks.json", encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
dim = vdb["embedding_dim"]
raw = vdb["matrix"]
flat = array("f")
if isinstance(raw, str):
    flat.frombytes(base64.b64decode(raw))
else:
    for r in raw:
        if isinstance(r, str):
            flat.frombytes(base64.b64decode(r))
        else:
            flat.extend(r)
vmat = np.frombuffer(flat, dtype="float32").reshape(len(vids), dim)
qvec = json.load(open(f"{B}/question_vectors.json", encoding="utf-8"))

log("load benchmark (canonical names)...")
gold, qmeta = {}, {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(open(f"{B}/{fn}", encoding="utf-8")):
        if q.get("gold_ids"):
            gold[q["qid"]] = q["gold_ids"]
            qmeta[q["qid"]] = q
unverified = set()
for q, v in json.load(open(f"{B}/regold.json", encoding="utf-8")).items():
    if not v.get("new_gold"):
        unverified.add(q)
split = json.load(open(f"{B}/bench_split.json", encoding="utf-8"))
all_q = [q for q in gold if q in qvec]
test_q = [q for q in split.get("test", []) if q in gold and q in qvec]
ver_q = [q for q in all_q if q not in unverified]
log("  gold=%d all=%d test=%d verified=%d" % (len(gold), len(all_q), len(test_q), len(ver_q)))

log("load temporal graph...")
tg = json.load(open(f"{P}/temporal_graph.json", encoding="utf-8"))
laws = {L["law_id"]: L for L in tg["laws"]}


def law_valid(lid, as_of):
    L = laws.get(lid)
    if L is None:
        return True
    vf, vt = L.get("valid_from"), L.get("valid_to")
    if vf and as_of < vf:
        return False
    if vt and as_of >= vt:
        return False
    return True


log("hybrid BM25+dense+RRF baseline (verbatim mirror)...")
bm = BM25(texts)
base_rank = {}
for qi, qid in enumerate(all_q):
    if qi % 100 == 0:
        log("  query %d/%d" % (qi, len(all_q)))
    q = qmeta[qid].get("question", "")
    s_bm = bm.score(q)
    order_bm = sorted(range(len(s_bm)), key=lambda i: (-round(s_bm[i], 6), i))[:200]
    qv = np.frombuffer(base64.b64decode(qvec[qid]), dtype="float32")
    order_dn = top_dense(qv, vmat, vids, 200)
    order_dn_idx = [idx_of[c] for c in order_dn if c in idx_of]
    fused = rrf([order_bm, order_dn_idx])
    base_rank[qid] = [ids[i] for i, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))]
log("baseline ready")


def metrics(rank_of, qids):
    hit = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    rrs = []
    for qid in qids:
        g = gold[qid]
        rk = rank_of(qid)
        rank = next((r + 1 for r, t in enumerate(rk) if t in g), None)
        n += 1
        for k in KS:
            if rank and rank <= k:
                hit[k] += 1
        rr = (1.0 / rank) if rank else 0.0
        mrr += rr
        rrs.append(rr)
    return {"n": n, "hit": {str(k): round(hit[k] / n, 4) for k in KS},
            "mrr": round(mrr / n, 4)}, rrs


def soft_tcr(qid, alpha):
    """Expired-law candidates down-weighted by (1-alpha); valid untouched."""
    as_of = qmeta[qid].get("as_of") or ""
    base = base_rank[qid]
    scored = []
    for r, c in enumerate(base):
        s = 1.0 / (60.0 + r + 1)
        lid = c.split("|")[0]
        if lid in laws and not law_valid(lid, as_of):
            s *= (1.0 - alpha)
        scored.append((c, s, r))
    return [c for c, _s, _r in sorted(scored, key=lambda t: (-t[1], t[2]))]


_, rrs_base_full = metrics(lambda q: base_rank[q], all_q)
_, rrs_base_test = metrics(lambda q: base_rank[q], test_q)

res = {
    "description": ("Temporal-constraint hardness sensitivity: expired-law candidates "
                    "down-weighted by (1 - alpha); alpha=0 equals the unfiltered hybrid "
                    "baseline, alpha=1 sinks them below every in-force candidate. "
                    "Engine: pure-Python BM25 (k1=1.2, b=0.75) + stored 768-d dense "
                    "vectors + RRF(k=60), identical to the published no-GPU mirror. "
                    "CPU only, no model, no network."),
    "alphas": ALPHAS,
    "sweep": {},
}
log("alpha sweep on full %d questions..." % len(all_q))
for a in ALPHAS:
    m_full, rrs_f = metrics(lambda q, a=a: soft_tcr(q, a), all_q)
    m_test, rrs_t = metrics(lambda q, a=a: soft_tcr(q, a), test_q)
    m_ver, _ = metrics(lambda q, a=a: soft_tcr(q, a), ver_q)
    entry = {"alpha": a, "full": m_full, "test": m_test, "verified": m_ver}
    try:
        _p = float(
            wilcoxon(rrs_f, rrs_base_full, zero_method="wilcox").pvalue)
        if _p != _p:  # NaN - alpha=0.0 is the identical baseline
            _p = None
            res["note_alpha_zero"] = (
                "alpha=0.0 is the identical-by-construction baseline; "
                "its paired p-value is null (not estimable, both rank "
                "vectors are equal).")
        entry["wilcoxon_full_p_vs_base"] = _p
    except Exception as ex:
        entry["wilcoxon_err"] = str(ex)
    res["sweep"][str(a)] = entry
    log("  alpha=%.2f full Hit@1=%.3f Hit@10=%.3f MRR=%.3f" %
        (a, m_full["hit"]["1"], m_full["hit"]["10"], m_full["mrr"]))

# cross-check: exact hard filter (drop expired entirely) for reference
def hard_tcr(qid):
    as_of = qmeta[qid].get("as_of") or ""
    return [c for c in base_rank[qid]
            if not (c.split("|")[0] in laws and not law_valid(c.split("|")[0], as_of))]


m_hard, rrs_hard = metrics(hard_tcr, all_q)
res["hard_filter_reference"] = m_hard
log("hard-filter reference: Hit@1=%.3f MRR=%.3f" % (m_hard["hit"]["1"], m_hard["mrr"]))

res["runtime_sec"] = round(time.time() - t00, 1)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log("saved -> %s" % OUT)
log("DONE")
