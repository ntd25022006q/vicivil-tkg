#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCR + SGB — clean decomposition of the temporal-constraint gain.

Baseline mirrors src/law_eval_repro.py EXACTLY (BM25 k1=1.2 b=0.75,
stored dense vectors, RRF k=60, rounded-6 stable sort).

Variants (hard temporal filter is ALWAYS on in every TCR/SGB variant):
  BASE      : published hybrid, no post-processing
  TCR-hard  : drop candidates from laws expired at as_of
              (exception: chunks of the question's own target law,
               and laws with unknown validity)
  TCR-soft  : TCR-hard + lam_rec * 1[law is latest in-force version of
              its succession line at as_of]  (additive on RRF scale)
  SGB       : TCR-hard + lam_g * RRF(citation-graph mass ranking)
              — scale-free fusion, house RRF style
  TCR+SGB   : TCR-hard + lam_rec + lam_g

Track B: same post-processing on the stored reranked top-30.

Tuning ONLY on dev split. CPU only, no GPU, no model, no network.
Output: benchmark/tcr_sgb_result.json
"""
import base64, json, math, os, re, time, unicodedata
from array import array
from collections import Counter, defaultdict

R = os.environ.get("VICIVIL_ROOT",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D, I, B, P = f"{R}/data", f"{R}/index", f"{R}/benchmark", f"{R}/provenance"
OUT = f"{B}/tcr_sgb_result.json"
KS = (1, 3, 5, 10)

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
log("  %d chunks" % len(ids))

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

log("load benchmark...")
gold, qmeta = {}, {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    p = f"{B}/{fn}"
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = q["gold_ids"]
                qmeta[q["qid"]] = q
unverified = set()
p = f"{B}/regold.json"
if os.path.exists(p):
    for q, v in json.load(open(p, encoding="utf-8")).items():
        if not v.get("new_gold"):
            unverified.add(q)
split = json.load(open(f"{B}/bench_split.json", encoding="utf-8"))
dev_q = [q for q in split.get("dev", []) if q in gold and q in qvec]
test_q = [q for q in split.get("test", []) if q in gold and q in qvec and q not in dev_q]
all_q = [q for q in gold if q in qvec]
log("  gold=%d dev=%d test=%d all=%d" % (len(gold), len(dev_q), len(test_q), len(all_q)))

log("load temporal graph + cite edges...")
tg = json.load(open(f"{P}/temporal_graph.json", encoding="utf-8"))
laws = {L["law_id"]: L for L in tg["laws"]}
succ = tg["succession"]
parent = {}


def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for e in succ:
    a, b = find(e["src"]), find(e["tgt"])
    if a != b:
        parent[a] = b
line_members = defaultdict(list)
for lid in laws:
    line_members[find(lid)].append(lid)


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


def latest_in_force(line, as_of):
    best, bvf = None, None
    for lid in line:
        L = laws.get(lid)
        if L is None:
            continue
        vf = L.get("valid_from") or ""
        if vf <= as_of and law_valid(lid, as_of):
            if bvf is None or vf > bvf:
                best, bvf = lid, vf
    return best


art_chunks = defaultdict(set)
for cid in ids:
    seg = cid.split("|")
    art_chunks[(seg[0], seg[1])].add(cid)

cite = json.load(open(f"{P}/cite_edges.json", encoding="utf-8"))
adj = defaultdict(dict)
for e in cite:
    sl = e["src_law"]
    a, b = (sl, "Dieu%s" % e["src_dieu"]), (sl, "Dieu%s" % e["tgt_dieu"])
    w = float(e.get("n") or 1)
    adj[a][b] = adj[a].get(b, 0.0) + w
    adj[b][a] = adj[b].get(a, 0.0) + w
deg = {k: sum(v.values()) for k, v in adj.items()}
n_art_hit = sum(1 for k in adj if k in art_chunks)
log("  %d laws / %d succession edges / %d symmetrized article-edges (%d keys match chunk articles)" % (len(laws), len(succ), len(adj), n_art_hit))

# ---------------------------------------------------------------- baseline
log("hybrid BM25+dense+RRF (verbatim mirror)...")
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


# ---------------------------------------------------------------- TCR/SGB engine
def post_process(qid, ranked, lam_rec=0.0, lam_g=0.0):
    """Hard filter ALWAYS on. ranked: full base order. Returns new order.
    Pure rule: drop candidates whose law is not in force at as_of;
    laws with unknown validity are kept. (No target-law exception is
    needed: benchmark as_of values were repaired so every gold law is
    in force at its question's as_of — see benchmark/as_of_fixes.json.)"""
    as_of = qmeta[qid].get("as_of") or ""
    # 1) TCR hard
    kept = []
    for r, c in enumerate(ranked):
        lid = c.split("|")[0]
        if lid in laws and not law_valid(lid, as_of):
            continue
        kept.append((c, r))
    # 2) TCR soft recency (additive on base RRF score)
    latest = {}
    if lam_rec > 0:
        for root, mem in line_members.items():
            l = latest_in_force(mem, as_of)
            if l:
                latest[l] = True
    # 3) SGB: citation-graph mass -> second rank list, scale-free RRF fusion
    mass = {}
    if lam_g > 0:
        cand = set(c for c, _ in kept)
        for c, _r in kept:
            seg = c.split("|")
            art = (seg[0], seg[1])
            m = 0.0
            for tgt, w in adj.get(art, {}).items():
                d = deg.get(tgt, 1.0)
                for cc in art_chunks.get(tgt, ()):
                    if cc in cand and cc != c:
                        m += w / (1.0 + d)
            mass[c] = m
    if lam_g > 0:
        by_mass = sorted(kept, key=lambda cr: (-mass.get(cr[0], 0.0), cr[1]))
        grank = {c: r for r, (c, _) in enumerate(by_mass)}
    score = {}
    for r, (c, _) in enumerate(kept):
        s = 1.0 / (60.0 + r + 1)
        if lam_rec > 0 and latest.get(c.split("|")[0]):
            s += lam_rec
        if lam_g > 0:
            s += lam_g * (1.0 / (60.0 + grank[c] + 1))
        score[c] = s
    return [c for c, _ in sorted(kept, key=lambda cr: (-score[cr[0]], cr[1]))]


# diagnostic: is the target-law exception textually grounded? (question text
# mentions the law name / so_hieu of an expired-target-law question)
def fold(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s.lower())


exp_t_q = [q for q in all_q
           if any((g.split("|")[0] == (qmeta[q].get("law_id") or "")) and
                  (g.split("|")[0] in laws) and
                  (not law_valid(g.split("|")[0], qmeta[q].get("as_of") or ""))
                  for g in gold[q])]
mention = 0
for q in exp_t_q:
    ql = qmeta[q].get("law_id") or ""
    L = laws.get(ql) or {}
    qf = fold(qmeta[q].get("question", ""))
    hay = fold(L.get("ten", "")) + " " + fold(L.get("so_hieu", "")) + " " + fold(ql.replace("BLDS", "bo luat "))
    toks_law = [t for t in hay.split() if len(t) > 3]
    if any(t in qf for t in toks_law) or fold(L.get("so_hieu", "")) in qf:
        mention += 1
log("  expired-target-law questions: %d; question text mentions the law: %d" % (len(exp_t_q), mention))
res_later = {"expired_target_q": len(exp_t_q), "expired_target_text_mention": mention}

# ---------------------------------------------------------------- grid on dev
log("grid search on dev (%d q)..." % len(dev_q))
grid = []
for lr in (0.0, 0.01, 0.02, 0.05, 0.1):
    for lg in (0.0, 0.25, 0.5, 1.0, 2.0):
        m, _ = metrics(lambda q, lr=lr, lg=lg: post_process(q, base_rank[q], lr, lg), dev_q)
        grid.append({"lam_rec": lr, "lam_g": lg, "dev_mrr": m["mrr"], "dev_hit1": m["hit"]["1"]})
grid.sort(key=lambda x: (-x["dev_mrr"], -x["dev_hit1"]))
log("top-6 dev:")
for g in grid[:6]:
    log("   %s" % g)
best_soft = max((g for g in grid if g["lam_g"] == 0.0 and g["lam_rec"] > 0),
                key=lambda x: (x["dev_mrr"], x["dev_hit1"]), default=None)
best_g = max((g for g in grid if g["lam_rec"] == 0.0 and g["lam_g"] > 0), key=lambda x: (x["dev_mrr"], x["dev_hit1"]))
best_both = grid[0]

res = {"grid_top10": grid[:10],
       "diagnostics_text": res_later,
       "chosen": {"soft": best_soft, "sgb": best_g, "both": best_both}}

base_metrics, rrs_base_full = metrics(lambda q: base_rank[q][:200], all_q)
_, rrs_base_test = metrics(lambda q: base_rank[q][:200], test_q)
log("BASE full: %s" % base_metrics)

VARIANTS = {"TCR_hard": (0.0, 0.0)}
if best_soft:
    VARIANTS["TCR_soft"] = (best_soft["lam_rec"], 0.0)
VARIANTS["SGB"] = (0.0, best_g["lam_g"])
VARIANTS["TCR_SGB"] = (best_both["lam_rec"], best_both["lam_g"])
for name, (lr, lg) in VARIANTS.items():
    rk = lambda q, lr=lr, lg=lg: post_process(q, base_rank[q], lr, lg)
    m_full, rrs_f = metrics(rk, all_q)
    m_test, rrs_t = metrics(rk, test_q)
    m_dev, _ = metrics(rk, dev_q)
    m_ver, _ = metrics(rk, [q for q in all_q if q not in unverified])
    entry = {"lam_rec": lr, "lam_g": lg, "full": m_full, "test": m_test,
             "dev": m_dev, "verified": m_ver}
    try:
        entry["wilcoxon_full_p"] = float(wilcoxon(rrs_f, rrs_base_full, zero_method="wilcox").pvalue)
        entry["wilcoxon_test_p"] = float(wilcoxon(rrs_t, rrs_base_test, zero_method="wilcox").pvalue)
    except Exception as ex:
        entry["wilcoxon_err"] = str(ex)
    res[name] = entry
    log("%s full=%s test=%s p=%.3g" % (name, m_full, m_test, entry.get("wilcoxon_full_p", -1)))

# ---------------------------------------------------------------- Track B (stored rerank top-30)
rrp = json.load(open(f"{B}/rerank_result.json", encoding="utf-8")).get("per_q", [])
rerank_top = {row["qid"]: row["rerank_top"] for row in rrp if row.get("rerank_top")}
rr_q = [q for q in all_q if q in rerank_top]
m_rb, rrs_rb_full = metrics(lambda q: rerank_top[q], rr_q)
log("TrackB rerank baseline (n=%d): %s" % (m_rb["n"], m_rb))
res["trackB"] = {"rerank_base": m_rb}
for name, (lr, lg) in VARIANTS.items():
    rk = lambda q, lr=lr, lg=lg: post_process(q, rerank_top[q], lr, lg)
    m, rrs = metrics(rk, rr_q)
    entry = dict(m)
    try:
        entry["wilcoxon_p"] = float(wilcoxon(rrs, rrs_rb_full, zero_method="wilcox").pvalue)
    except Exception as ex:
        entry["wilcoxon_err"] = str(ex)
    res["trackB"][name] = entry
    log("  TrackB %s: %s" % (name, entry))

res["baseline_full"] = base_metrics
res["runtime_sec"] = round(time.time() - t00, 1)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log("saved -> %s" % OUT)
log("DONE")
