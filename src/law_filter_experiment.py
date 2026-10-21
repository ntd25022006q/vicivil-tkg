"""Thu nghiem: loc bo cac doan chat luong thap (rat ngan / trung noi dung) co lam
diem truy hoi tot hon khong? Chay lai cung phep cham, khong can GPU.

So sanh 3 phien ban:
  A. goc            : moi 11.267 doan
  B. bo doan < 120 ky tu
  C. bo doan trung (chuoi da chuan hoa) va doan < 120 ky tu
"""
import base64, json, math, os, re, time, unicodedata
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


def norm_text(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"[^a-zà-ỹđ0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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


# ---------------- du lieu
all_ids, all_texts = [], []
with open(os.path.join(R, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        all_ids.append(c["chunk_id"])
        all_texts.append(c.get("content", ""))

vdb = json.load(open(os.path.join(I, "vdb_chunks.json"), encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
dim = vdb["embedding_dim"]
flat = array("f")
flat.frombytes(base64.b64decode(vdb["matrix"]))
vmat = np.frombuffer(flat, dtype="float32").reshape(len(vids), dim) if np is not None else flat
vrow = {cid: i for i, cid in enumerate(vids)}

qvec = json.load(open(os.path.join(B, "question_vectors.json"), encoding="utf-8"))
gold = {}
for fn in ("law_bench_200c.json", "law_bench_v1.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = {"q": q.get("question", ""), "g": q["gold_ids"]}
unverified = set()
p = os.path.join(B, "regold.json")
if os.path.exists(p):
    unverified = {q for q, v in json.load(open(p, encoding="utf-8")).items() if not v.get("new_gold")}

# ---------------- bo bien tap
seen = set()
short_ids, dup_ids = set(), set()
for cid, txt in zip(all_ids, all_texts):
    t = norm_text(txt)
    if len(txt.strip()) < 120:
        short_ids.add(cid)
    if t in seen:
        dup_ids.add(cid)
    else:
        seen.add(t)

VARIANTS = {
    "A. goc (11.267 doan)": set(),
    "B. bo doan < 120 ky tu": short_ids,
    "C. bo doan trung + < 120 ky tu": short_ids | dup_ids,
}

results = {}
for name, drop in VARIANTS.items():
    keep = [i for i, cid in enumerate(all_ids) if cid not in drop]
    ids = [all_ids[i] for i in keep]
    texts = [all_texts[i] for i in keep]
    bm = BM25(texts)
    hit = {k: 0 for k in KS}
    hit_v = {k: 0 for k in KS}
    rr = 0.0
    n = n_v = 0
    t0 = time.time()
    for qid, meta in gold.items():
        if qid not in qvec:
            continue
        n += 1
        s_bm = bm.score(meta["q"])
        order_bm = sorted(range(len(s_bm)), key=lambda i: (-round(s_bm[i], 6), i))[:200]
        if np is not None:
            qv = np.frombuffer(base64.b64decode(qvec[qid]), dtype="float32")
            sims = np.round(vmat[[vrow[all_ids[i]] for i in keep]] @ qv, 6)
            order_dn = list(np.argsort(-sims, kind="stable")[:200])
        else:
            qv = array("f"); qv.frombytes(base64.b64decode(qvec[qid]))
            step = len(qv)
            sc = []
            for j, i in enumerate(keep):
                row = vmat[vrow[all_ids[i]] * step:(vrow[all_ids[i]] + 1) * step]
                sc.append((round(sum(map(mul, qv, row)), 6), j))
            sc.sort(key=lambda t: (-t[0], t[1]))
            order_dn = [j for _, j in sc[:200]]
        fused = rrf([order_bm, order_dn])
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:10]
        top_ids = [ids[i] for i, _ in top]
        rank = next((r + 1 for r, t in enumerate(top_ids) if t in meta["g"]), None)
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
    results[name] = {
        "n_chunks": len(ids),
        "hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS},
        "mrr": round(rr / n, 4),
        "hit_at_k_verified_only": {str(k): round(hit_v[k] / n_v, 4) for k in KS},
        "seconds": round(time.time() - t0, 1),
    }
    print(name, json.dumps(results[name], ensure_ascii=False), flush=True)

out = {
    "question": "loc bo doan chat luong thap co lam diem truy hoi tot hon khong?",
    "short_chunks_under_120_chars": len(short_ids),
    "duplicate_chunks": len(dup_ids),
    "variants": results,
    "note": "cung phep cham voi law_eval_repro.py (BM25 + vector da luu + RRF), khong can GPU",
}
json.dump(out, open(os.path.join(B, "chunk_filter_experiment.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("da ghi:", os.path.join(B, "chunk_filter_experiment.json"))