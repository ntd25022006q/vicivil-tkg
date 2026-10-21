"""Phan tich loi truy hoi: 168 cau khong tim thay dap an o top-10 - vi sao?

Phan loai nguyen nhan (de biet nen sua cai gi):
  1. dap an vang khong co trong corpus        -> loi du lieu mo rong
  2. dap an vang co nhung khong vao top-10  -> loi truy hoi that
  3. top-1 cung van ban voi dap an vang      -> ranh gioi doan sai
  4. top-1 khac van ban nhung noi dung tuong duong -> thang do khong chap nhan nhieu dap an
"""
import base64, json, os, re, unicodedata
from collections import Counter

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
D = os.path.join(R, "data")


def norm(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"[^a-zà-ỹđ0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s):
    return norm(s).split()


corpus = {}
with open(os.path.join(D, "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        corpus[c["chunk_id"]] = {"text": c.get("content", ""), "law": c.get("law_id", ""),
                                "dieu": c.get("dieu", "")}

ev = json.load(open(os.path.join(B, "law_eval_repro.json"), encoding="utf-8"))
gold = {}
for fn in ("law_bench_200c.json", "law_bench_v1.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = {"q": q.get("question", ""), "g": q["gold_ids"],
                                  "as_of": q.get("as_of", ""), "law_id": q.get("law_id", "")}

cat = Counter()
examples = {k: [] for k in range(1, 5)}
found_rank_hist = Counter()

for row in ev["per_q"]:
    qid = row["qid"]
    meta = gold.get(qid)
    if not meta:
        continue
    g = meta["g"]
    present = [x for x in g if x in corpus]
    rank = row["rank"]
    if rank:
        found_rank_hist[rank] += 1
        continue
    # khong tim thay o top-10
    if not present:
        cat["1. dap an vang khong co trong corpus"] += 1
        examples[1].append(qid)
        continue
    top = row["top"]
    if not top:
        cat["2. khong co ket qua tra ve"] += 1
        continue
    t1 = top[0]
    g0 = present[0]
    same_law = corpus[t1]["law"] == corpus[g0]["law"]
    gnorm = norm(corpus[g0]["text"])
    tnorm = norm(corpus[t1]["text"])
    if same_law:
        cat["3. cung van ban, khac doan"] += 1
        examples[3].append(qid)
    elif tnorm and gnorm and (tnorm in gnorm or gnorm in tnorm or
                               len(set(toks(tnorm)) & set(toks(gnorm))) / max(1, len(set(toks(gnorm)))) > 0.85):
        cat["4. khac van ban nhung noi dung tuong duong"] += 1
        examples[4].append(qid)
    else:
        cat["2. dap an co nhung khong vao top-10"] += 1
        examples[2].append(qid)

out = {
    "n_questions": len(ev["per_q"]),
    "n_hit_at_10": sum(1 for r in ev["per_q"] if r["rank"]),
    "n_miss_at_10": sum(1 for r in ev["per_q"] if not r["rank"]),
    "rank_histogram": {str(k): v for k, v in sorted(found_rank_hist.items())},
    "miss_reasons": dict(cat),
    "example_qids": {str(k): v[:12] for k, v in examples.items()},
    "note": "phan loai cac cau khong co dap an trong top-10 cua phép cham tai lap (khong GPU)",
}
json.dump(out, open(os.path.join(B, "error_analysis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "example_qids"}, ensure_ascii=False, indent=1))