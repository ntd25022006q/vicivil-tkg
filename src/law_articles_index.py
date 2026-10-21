import io, json, os, collections

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ---- chunk theo dieu/khoan
arts = collections.defaultdict(lambda: {"chunks": [], "chars": 0, "in": 0, "out": 0})
with io.open(os.path.join(R, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        key = (c["law_id"], str(c.get("dieu", "")), str(c.get("khoan", "")), str(c.get("diem", "")))
        a = arts[key]
        a["chunks"].append(c["chunk_id"])
        a["chars"] += c.get("chars", 0) or len(c.get("content", ""))

# ---- quan he danh chiieu cap dieu (provenance/cite_edges.json)
ce = json.load(io.open(os.path.join(R, "provenance", "cite_edges.json"), encoding="utf-8"))
law_arts = collections.defaultdict(set)
for (law, d, k, dm) in arts:
    if d:
        law_arts[law].add(d)
for e in ce:
    sl, sd, td = e.get("src_law"), str(e.get("src_dieu", "")), str(e.get("tgt_dieu", ""))
    n = e.get("n", 1) or 1
    for key in arts:
        if key[0] == sl and key[1] == sd:
            arts[key]["out"] += n
    for key in arts:
        if key[0] == sl and key[1] == td:
            arts[key]["in"] += n

# ---- gom theo dieu (bo qua khoan/diem khi dem) + giu chi tiet theo dieu
out = {}
for (law, dieu, khoan, diem), a in arts.items():
    e = out.setdefault(law, {})
    key = "Dieu%s" % (dieu or "?")
    if khoan:
        key += "|Khoan%s" % khoan
    if diem:
        key += "|Diem%s" % diem
    d = e.setdefault(key, {"dieu": dieu, "khoan": khoan, "diem": diem, "n": 0,
                           "chars": 0, "in": 0, "out": 0, "ids": []})
    d["n"] += len(a["chunks"])
    d["chars"] += a["chars"]
    d["in"] += a["in"]
    d["out"] += a["out"]
    d["ids"].extend(a["chunks"])

p = os.path.join(R, "docs", "graph", "law_articles.json")
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
n = sum(len(v) for v in out.values())
print("don vi dieu/khoan:", n, "| so luat:", len(out), "| bytes:", os.path.getsize(p))
top = sorted(((v["out"], v["in"], k) for k, v in out.get("BLDS2015", {}).items()), reverse=True)[:5]
print("BLDS2015 dieu duoc tro nhieu nhat (ra | va):", top)