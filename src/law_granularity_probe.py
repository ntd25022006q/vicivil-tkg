"""Kiem tra gia thuyet: 24 cau 'cung van ban nhung khac doan' co duoc sua bang cach
gop cac doan o cap Khoan khong? Do bang cach: doan 'anh em' (cung Dieu+Khoan) cua dap
an vang co xuat hien trong top-10 khong.

Khong can GPU: chi doc ket qua da cham.
"""
import json, os

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(R, "benchmark")
D = os.path.join(R, "data")

corpus = {}
with open(os.path.join(D, "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        corpus[c["chunk_id"]] = {"law": c.get("law_id", ""), "dieu": str(c.get("dieu", "")),
                                "khoan": str(c.get("khoan", ""))}


def sibling(cid):
    m = corpus[cid]
    return (m["law"], m["dieu"], m["khoan"])


gold = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    p = os.path.join(B, fn)
    if os.path.exists(p):
        for q in json.load(open(p, encoding="utf-8")):
            if q.get("gold_ids"):
                gold[q["qid"]] = q["gold_ids"]

ev = json.load(open(os.path.join(B, "law_eval_repro.json"), encoding="utf-8"))

n_miss = 0
n_sib_in_top = 0
n_sib_same_law_in_top = 0
n_sib_in_top_but_other_law = 0
det = []
for row in ev["per_q"]:
    if row["rank"]:
        continue
    g = [x for x in gold.get(row["qid"], []) if x in corpus]
    if not g:
        continue
    n_miss += 1
    gs = set(sibling(x) for x in g)
    glaw = set(corpus[x]["law"] for x in g)
    top = row["top"]
    hit_sib = None
    for t in top:
        if sibling(t) in gs:
            hit_sib = t
            break
    if hit_sib:
        n_sib_in_top += 1
        if corpus[hit_sib]["law"] in glaw:
            n_sib_same_law_in_top += 1
        else:
            n_sib_in_top_but_other_law += 1
        det.append({"qid": row["qid"], "sibling_found": hit_sib,
                    "same_law": corpus[hit_sib]["law"] in glaw,
                    "gold_law": sorted(glaw), "sibling_law": corpus[hit_sib]["law"]})

out = {
    "n_miss_at_10": n_miss,
    "n_sibling_in_top10": n_sib_in_top,
    "n_sibling_same_law": n_sib_same_law_in_top,
    "n_sibling_other_law": n_sib_in_top_but_other_law,
    "conclusion": (
        "Neu phan lon so cau bi truot co 'anh em' (cung Dieu-Khoan) cua dap an vang xuat "
        "hien trong top-10, thi gop cac doan o cap Khoan se sua duoc nhung cau do ma KHONG "
        "can GPU (chi can ma hoa lai mot lan bang ollama khi may ranh)."
    ),
    "examples": det[:15],
}
json.dump(out, open(os.path.join(B, "granularity_probe.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "examples"}, ensure_ascii=False, indent=1))