"""So sanh vector chunk hien tai (noi dung tran) voi vector moi (kem ngu canh).
Dung cung phép cham: BM25 + dense + RRF. Khong can GPU.
"""
import base64, json, math, os, re, sys, unicodedata
from array import array
from collections import Counter
from operator import mul

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
I = os.path.join(R, "index")
KS = (1, 3, 5, 10)
try:
    import numpy as np
except Exception:
    np = None


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
    score = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks, start=1):
            score[idx] = score.get(idx, 0.0) + 1.0 / (k + r)
    return score


def load_vec(path):
    d = json.load(open(path, encoding="utf-8"))
    vids = [x["__id__"] for x in d["data"]]
    dim = d["embedding_dim"]
    flat = array("f")
    flat.frombytes(base64.b64decode(d["matrix"]))
    m = np.frombuffer(flat, dtype="float32").reshape(len(vids), dim) if np is not None else flat
    return vids, m


ids, texts = [], []
with open(os.path.join(R, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        ids.append(c["chunk_id"])
        texts.append(c.get("content", ""))
idx_of = {c: i for i, c in enumerate(ids)}

qvec = json.load(open(os.path.join(B, "question_vectors.json"), encoding="utf-8"))
gold = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = {"q": q.get("question", ""), "g": q["gold_ids"]}

bm = BM25(texts)
# BM25 chạy 1 lần cho mọi biến thể vector
bm_scores = {qid: bm.score(meta["q"]) for qid, meta in gold.items()}
bm_orders = {qid: sorted(range(len(s)), key=lambda i: (-round(s[i], 6), i))[:200] for qid, s in bm_scores.items()}

results = {}
for name, path in (("A. vector hien tai (noi dung tran)", os.path.join(I, "vdb_chunks.json")),
                   ("B. vector moi (kem ngu canh)", sys.argv[1] if len(sys.argv) > 1 else None)):
    if path is None or not os.path.exists(path):
        continue
    vids, vmat = load_vec(path)
    vrow = {c: i for i, c in enumerate(vids)}
    hit = {k: 0 for k in KS}
    rr = 0.0
    n = 0
    for qid, meta in gold.items():
        if qid not in qvec:
            continue
        n += 1
        if np is not None:
            qv = np.frombuffer(base64.b64decode(qvec[qid]), dtype="float32")
            sims = np.round(vmat @ qv, 6)
            order_dn = list(np.argsort(-sims, kind="stable")[:200])
        else:
            qv = array("f"); qv.frombytes(base64.b64decode(qvec[qid]))
            step = len(qv); sc = []
            for i, cid in enumerate(vids):
                r = vrow[cid] * step
                sc.append((round(sum(map(mul, qv, vmat[r:r + step])), 6), i))
            sc.sort(key=lambda t: (-t[0], t[1]))
            order_dn = [i for _, i in sc[:200]]
        fused = rrf([bm_orders[qid], order_dn])
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:10]
        top_ids = [ids[i] for i, _ in top if i < len(ids)]
        rank = next((r + 1 for r, t in enumerate(top_ids) if t in meta["g"]), None)
        for k in KS:
            if rank and rank <= k:
                hit[k] += 1
        if rank:
            rr += 1.0 / rank
    results[name] = {"hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS}, "mrr": round(rr / n, 4)}
    print(name, json.dumps(results[name], ensure_ascii=False), flush=True)

out = {"question": "ma hoa lai doan van ban kem ngu canh co giup truy hoi tot hon khong?",
       "note": "cung phiep cham BM25 + dense + RRF; khong can GPU de cham",
       "variants": results}
json.dump(out, open(os.path.join(B, "embedding_context_experiment.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("da ghi:", os.path.join(B, "embedding_context_experiment.json"))
