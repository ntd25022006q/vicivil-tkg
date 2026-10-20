"""Pipeline tang dan: them van ban moi ma KHONG chay lai toan bo.

Vien goc chay lai het mot lan (chunk + ma hoa + chi muc + do thi), gay ton
tai GPU. Script nay chi giai quyet trinh:
  1. doc cac tep PDF moi (thu muc nguon);
  2. cat chunk theo Dieu-Khoan-Diem;
  3. ghep vao tep chunk hien co, bo trung ma;
  4. ghi ra tap "delta" de buoc ma hoa chi chay cho phan moi;
  5. cap nhat do thi tri thuc (them node luot va canh ke thia/sua doi neu
     tin hieu sua doi co trong van ban moi).

KHONG can GPU cho buoc 1-3 va 5. Buoc ma hoa chi can cho phan delta
(khong nhieu), nen chay duoc ngay ca khi GPU dang ban.
"""
import io, json, os, re, sys, hashlib, unicodedata, collections, datetime

R = os.environ.get("LAW_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "sources_raw")
OUT = os.path.join(R, "runs")

# ------------------------------------------------------------------ helpers
def slug_law(name):
    s = unicodedata.normalize("NFC", name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s.upper() or "LAW"

def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip()

# ------------------------------------------------------------------ 1. doc nguon
existing = set()
chunks_path = os.path.join(R, "data", "civil_chunks.jsonl")
if os.path.exists(chunks_path):
    with io.open(chunks_path, encoding="utf-8") as f:
        for line in f:
            existing.add(json.loads(line)["chunk_id"])

# cac tep van ban moi: .txt (da boc text) hoac .md
new_files = []
if os.path.isdir(SRC):
    for fn in sorted(os.listdir(SRC)):
        if fn.lower().endswith((".txt", ".md")):
            new_files.append(os.path.join(SRC, fn))

print("nguon moi:", len(new_files), "tai", SRC)

# ------------------------------------------------------------------ 2. cat chunk
def split_articles(text):
    """Tach theo 'Dieu N.' - dung cho van ban da boc text san."""
    out = []
    parts = re.split(r"(?m)^\s*Điều\s+(\d+)\s*[.:]?\s*$", "\n" + text)
    if len(parts) < 3:
        return out
    for i in range(1, len(parts) - 1, 2):
        num, body = parts[i], parts[i + 1]
        out.append((num, body.strip()))
    return out

delta = []
for path in new_files:
    law_id = slug_law(os.path.splitext(os.path.basename(path))[0])
    text = io.open(path, encoding="utf-8", errors="replace").read()
    arts = split_articles(text)
    if not arts:
        print("  bo qua (khong tach duoc Dieu):", os.path.basename(path))
        continue
    for num, body in arts:
        for koan in re.split(r"(?m)^\s*Khoản\s+(\d+)\s*[.:]?\s*$", body)[1:]:
            pass
        cid = "%s|Dieu%s" % (law_id, num)
        if cid in existing:
            continue
        content = norm(body)
        if len(content) < 40:
            continue
        delta.append({"chunk_id": cid, "law_id": law_id, "dieu": num, "khoan": "",
                      "diem": "", "tieu_de": "", "content": content, "chars": len(content),
                      "source_url": "", "source_type": "local", "fetched": datetime.date.today().isoformat()})
    print("  ", os.path.basename(path), "->", law_id, len(arts), "dieu")

# ------------------------------------------------------------------ 3+4. ghep va ghi delta
os.makedirs(OUT, exist_ok=True)
delta_path = os.path.join(OUT, "chunk_delta.jsonl")
with io.open(delta_path, "w", encoding="utf-8", newline="\n") as f:
    for d in delta:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
print("delta ghi vao:", delta_path, "| so chunk moi:", len(delta))

if delta:
    merged = os.path.join(OUT, "civil_chunks_merged.jsonl")
    seen = set()
    with io.open(merged, "w", encoding="utf-8", newline="\n") as out:
        for src in (chunks_path, delta_path):
            if not os.path.exists(src):
                continue
            with io.open(src, encoding="utf-8") as f:
                for line in f:
                    c = json.loads(line)
                    if c["chunk_id"] in seen:
                        continue
                    seen.add(c["chunk_id"])
                    out.write(line)
    print("ban ghep:", merged, "| tong chunk:", len(seen))
    print("BUOC TIEP THEO (can mo hinh ma hoa, GPU neu rong):")
    print("  1) ma hoa chi %d chunk trong delta" % len(delta))
    print("  2) noi vector vao index/vdb_chunks.json")
    print("  3) chay lai src/law_articles_index.py va src/law_rdf_export.py")
    print("  4) chay lai src/law_eval_equiv.py de kiem tra hoi quy")
else:
    print("khong co chunk moi (cac van ban da co trong kho)")