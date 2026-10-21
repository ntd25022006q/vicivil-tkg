"""Thu nghiem 1 (khong can GPU): them ngu canh vao văn bản khi tra cuu.

Vector chunk hien tai duoc tao tu NOI DUNG TRAN (khong ten luat, khong so dieu, khong tieu de).
Mot cau hoi nhac " Dieu 27 Bai Luat Dan su 2015 " thi tu vung do khong ton tai trong doan,
nen ca BM25 lan vector deu that bai khop.

Thu nghiem: them ngu canh vao DOAN DUNG trong tra cuu va do lai Hit@k.
"""
import json, math, os, re, unicodedata
from collections import Counter

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
D = os.path.join(R, "data")
KS = (1, 3, 5, 10)


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


# ten luat co dau: lay tu payload cua trang xem
built = open(os.path.join(R, "docs", "graph", "explorer.html"), encoding="utf-8").read()
i = built.find('{"nodes"')
payload = json.loads(built[i:].split("\n", 1)[0].rsplit(";", 1)[0].split("const D=", 1)[-1])
NAME = {n["id"]: n.get("name", n["id"]) for n in payload["nodes"] if n.get("cat")}
SYM = {n["id"]: (n.get("sym") or "") for n in payload["nodes"] if n.get("cat")}

chunks = []
with open(os.path.join(D, "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))


def ctx(c):
    law = c.get("law_id", "")
    head = NAME.get(law, law)
    sym = SYM.get(law, "")
    loc = "Điều %s" % (c.get("dieu") or "?")
    if c.get("khoan"):
        loc += ", Khoản %s" % c["khoan"]
    if c.get("diem"):
        loc += ", Điểm %s" % c["diem"]
    title = (c.get("tieu_de") or "").strip()
    return "%s%s\n%s%s\n%s" % (head, (" (%s)" % sym) if sym else "", loc, (": " + title) if title else "",
                              c.get("content", ""))


gold = {}
for fn in ("law_bench_200c.json", "law_bench_v1.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = {"q": q.get("question", ""), "g": q["gold_ids"]}

variants = {
    "A. noi dung tran (hien tai)": [c.get("content", "") for c in chunks],
    "B. co ngu canh (ten luat + dieu/khoan + tieu de)": [ctx(c) for c in chunks],
}
ids = [c["chunk_id"] for c in chunks]

res = {}
for name, texts in variants.items():
    bm = BM25(texts)
    hit = {k: 0 for k in KS}
    rr = 0.0
    n = 0
    for qid, meta in gold.items():
        n += 1
        s = bm.score(meta["q"])
        order = sorted(range(len(s)), key=lambda i: (-round(s[i], 6), i))[:10]
        rank = next((r + 1 for r, i in enumerate(order) if ids[i] in meta["g"]), None)
        for k in KS:
            if rank and rank <= k:
                hit[k] += 1
        if rank:
            rr += 1.0 / rank
    res[name] = {"hit_at_k": {str(k): round(hit[k] / n, 4) for k in KS}, "mrr": round(rr / n, 4)}
    print(name, json.dumps(res[name], ensure_ascii=False), flush=True)

out = {"question": "them ngu canh (ten luat, so dieu/khoan, tieu de) vao doan khi tra cuu co giup khong?",
       "chi BM25, khong can GPU": res,
       "vi du doan co ngu canh": ctx(chunks[0])[:220]}
json.dump(out, open(os.path.join(B, "context_experiment.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("da ghi:", os.path.join(B, "context_experiment.json"))