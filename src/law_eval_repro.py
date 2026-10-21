"""Cham lai bo benchmark tu cac tep trong kho - KHONG can GPU, KHONG can model.

Nguyen tac: phan vector (dense) da duoc tinh truoc va luu trong kho:
  - vector chunk      : index/vdb_chunks.json         (11.267 x 768)
  - vector cau hoi   : benchmark/question_vectors.json (281 x 768)
Phan tu vung (BM25) tinh lai bang Python thuan tu data/civil_chunks.jsonl.
Hai phan gop bang RRF - cung cach voi law_retrieve.py.

Chay:  python src/law_eval_repro.py
Chi can Python 3.9+; numpy duoc dung neu co (nhanh hon), khong co van chay duoc.
"""
import base64, json, math, os, re, time, unicodedata
from array import array
from collections import Counter
from operator import mul

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
D = os.path.join(R, "data")
I = os.path.join(R, "index")
B = os.path.join(R, "benchmark")
OUT = os.path.join(B, "law_eval_repro.json")
KS = (1, 3, 5, 10)

try:
    import numpy as np
except Exception:
    np = None


# ------------------------------------------------------------------ tokens
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
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            out.append(s)
        return out


def rrf(rank_lists, k=60):
    """Reciprocal Rank Fusion - cung cach voi law_retrieve.py."""
    score = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks, start=1):
            score[idx] = score.get(idx, 0.0) + 1.0 / (k + r)
    return score


def top_dense(qvec, vmat, vids, n=200):
    """Tra ve n chunk_id giong nhat theo cosin. numpy neu co, nguoc lai Python thuan.

    Diem lam tron 6 chu so thap phan thuoc truoc khi xep hang: vay ket qua
    giong het nhau giua co numpy va khong co (thu tu cong don bien tang).
    """
    if np is not None and isinstance(vmat, np.ndarray):
        sims = np.round(vmat @ qvec, 6)
        idx = np.argsort(-sims, kind="stable")[:n]
        return [vids[i] for i in idx]
    # Python thuan: vector 768 so, 11.267 hang
    out = []
    step = len(qvec)
    nrow = len(vmat) // step
    for r in range(nrow):
        row = vmat[r * step:(r + 1) * step]
        out.append((round(sum(map(mul, qvec, row)), 6), r))
    out.sort(key=lambda t: (-t[0], t[1]))
    return [vids[r] for _, r in out[:n]]


# ------------------------------------------------------------------ load
t0 = time.time()
print("doc chunk...", flush=True)
ids, texts = [], []
with open(os.path.join(D, "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        ids.append(c["chunk_id"])
        texts.append(c.get("content", ""))
print("  %d chunk" % len(ids), flush=True)

print("doc vector chunk...", flush=True)
vdb = json.load(open(os.path.join(I, "vdb_chunks.json"), encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
dim = vdb["embedding_dim"]
raw = vdb["matrix"]
if isinstance(raw, str):
    flat = array("f")
    flat.frombytes(base64.b64decode(raw))
    vmat = flat
else:
    vmat = array("f")
    for r in raw:
        vmat.frombytes(base64.b64decode(r)) if isinstance(r, str) else vmat.extend(r)
if np is not None:
    vmat = np.frombuffer(vmat, dtype="float32").reshape(len(vids), dim)
print("  %d vector (%s)" % (len(vids), "numpy" if np is not None else "python thuan"), flush=True)

qvec = json.load(open(os.path.join(B, "question_vectors.json"), encoding="utf-8"))
print("  %d vector cau hoi" % len(qvec), flush=True)

# ------------------------------------------------------------------ gold
gold = {}
for fn in ("law_bench_200c.json", "law_bench_v1.json"):
    p = os.path.join(B, fn)
    if not os.path.exists(p):
        continue
    for q in json.load(open(p, encoding="utf-8")):
        g = q.get("gold_ids") or []
        if g:
            gold[q["qid"]] = {"q": q.get("question", ""), "g": g}

# nhom "khong xac minh duoc": dap an cu bi danh dau null trong regold.json
unverified = set()
p = os.path.join(B, "regold.json")
if os.path.exists(p):
    for q, v in json.load(open(p, encoding="utf-8")).items():
        if not v.get("new_gold"):
            unverified.add(q)

# ------------------------------------------------------------------ cham
print("cham BM25 + dense + RRF...", flush=True)
bm = BM25(texts)
per_q = []
hit = {k: 0 for k in KS}
hit_v = {k: 0 for k in KS}
rr = 0.0
rr_v = 0.0
n = 0
n_v = 0
idx_of = {cid: i for i, cid in enumerate(ids)}

for qi, (qid, meta) in enumerate(gold.items()):
    if qid not in qvec:
        continue
    n += 1
    s_bm = bm.score(meta["q"])
    order_bm = sorted(range(len(s_bm)), key=lambda i: (-round(s_bm[i], 6), i))[:200]

    if np is not None:
        qv = np.frombuffer(base64.b64decode(qvec[qid]), dtype="float32")
    else:
        qv = array("f")
        qv.frombytes(base64.b64decode(qvec[qid]))
    order_dn = top_dense(qv, vmat, vids, 200)
    order_dn_idx = [idx_of[c] for c in order_dn if c in idx_of]

    fused = rrf([order_bm, order_dn_idx])
    top = sorted(fused.items(), key=lambda kv: -kv[1])[:10]
    top_ids = [ids[i] for i, _ in top]

    rank = next((r + 1 for r, t in enumerate(top_ids) if t in meta["g"]), None)
    per_q.append({"qid": qid, "rank": rank, "top": top_ids,
                  "scores": [round(s, 6) for _, s in top]})
    for k in KS:
        if rank and rank <= k:
            hit[k] += 1
    if rank:
        rr += 1.0 / rank
    if qid not in unverified:
        n_v += 1
        for k in KS:
            if rank and rank <= k:
                hit_v[k] += 1
        if rank:
            rr_v += 1.0 / rank
    if (qi + 1) % 50 == 0:
        print("  %d/%d  %.0fs" % (qi + 1, len(gold), time.time() - t0), flush=True)

out = {
    "note": "cham lai tu cac tep trong kho: BM25 (Python thuan) + dense (vector da luu) + RRF. "
            "Khong can GPU, khong can mo hinh, khong can mang.",
    "engine": "numpy" if np is not None else "python-thuan",
    "n_questions": n,
    "n_questions_with_verified_gold": n_v,
    "hit_at_k_all": {str(k): round(hit[k] / n, 4) if n else 0 for k in KS},
    "mrr_all": round(rr / n, 4) if n else 0,
    "hit_at_k_verified_only": {str(k): round(hit_v[k] / n_v, 4) if n_v else 0 for k in KS},
    "mrr_verified_only": round(rr_v / n_v, 4) if n_v else 0,
    "unverified_question_count": len(unverified),
    "per_q": per_q,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "per_q"}, ensure_ascii=False, indent=1))
print("da ghi:", OUT, os.path.getsize(OUT), "bytes | %.0fs" % (time.time() - t0))