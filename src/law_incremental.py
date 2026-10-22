"""Pipeline tang dan: them van ban moi ma KHONG chay lai toan bo.

Van de da phat hien va sua: ban dau script nay dung bo tach rieng, yeu hon bo
tach goc trong tools/law_extract_pilot.py, nen khong tach duoc "Dieu" trong
mot so van ban. Ban nay dung DUNG bo tach cua nguon goc:
  - "Dieu N."   : bat dau mot dieu, phan con lai cua dong la tieu de
  - "K."        : dong bat dau bang so 1-2 chu so -> mot khoan
  - phan con lai cua dieu -> noi dung dieu (khi khong co khoan nao)
Dung chung ID: {LAW}|Dieu{d}[|Khoan{k}[|Diem{p}]]

Usage:
  python src/law_incremental.py [thu_muc_nguon] [tieu_de_va_ban]
"""
import io, json, os, re, sys, datetime

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "sources_raw")
CORPUS = os.path.join(R, "data", "civil_chunks.jsonl")
OUT = os.path.join(R, "runs", "chunk_delta.jsonl")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

DIEU_RE = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
KHOAN_RE = re.compile(r"^(\d+)\.\s+(.*)$")


def read_text(path):
    if path.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            print("  bo qua (thieu pypdf):", os.path.basename(path))
            return None
        rd = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in rd.pages)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def split_articles(text, law_id):
    """Cung logic tach voi tools/law_extract_pilot.py."""
    lines = [ln.strip() for ln in text.split("\n")]
    recs, cur = [], None

    def push():
        nonlocal cur
        if cur and cur["content"].strip():
            cur["content"] = cur["content"].strip()
            cur["chars"] = len(cur["content"])
            recs.append(cur)
        cur = None

    for ln in lines:
        if not ln:
            continue
        m = DIEU_RE.match(ln)
        if m:
            push()
            cur = {"chunk_id": "%s|Dieu%s" % (law_id, m.group(1)), "law_id": law_id,
                   "dieu": m.group(1), "khoan": "", "diem": "",
                   "tieu_de": m.group(2).strip(), "content": ""}
            continue
        if cur is None:
            continue
        k = KHOAN_RE.match(ln)
        if k and len(k.group(1)) <= 2:
            sub = dict(cur)
            sub["khoan"] = k.group(1)
            sub["chunk_id"] = "%s|Khoan%s" % (cur["chunk_id"], k.group(1))
            sub["content"] = k.group(2)
            cur.setdefault("_subs", []).append([sub, []])
            continue
        if cur.get("_subs"):
            cur["_subs"][-1][1].append(ln)
        else:
            cur["content"] += ("\n" if cur["content"] else "") + ln
    push()

    flat = []
    for r in recs:
        subs = r.pop("_subs", [])
        if subs:
            r["content"] = ""
            r["chars"] = 0
            flat.append(r)
            for s, tail in subs:
                if tail:
                    s["content"] += "\n" + "\n".join(tail)
                s["content"] = s["content"].strip()
                s["chars"] = len(s["content"])
                flat.append(s)
        else:
            flat.append(r)
    return flat


def law_id_from(path):
    base = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[^0-9a-zA-Z]+", "-", base).strip("-").upper() or "LAW"


existing = set()
if os.path.exists(CORPUS):
    with io.open(CORPUS, encoding="utf-8") as f:
        for line in f:
            existing.add(json.loads(line)["chunk_id"])

files = []
if os.path.isdir(SRC):
    for fn in sorted(os.listdir(SRC)):
        if fn.lower().endswith((".txt", ".pdf")):
            files.append(os.path.join(SRC, fn))
print("nguon:", len(files), "tai", SRC)

today = datetime.date.today().isoformat()
delta, seen_new = [], set()
for path in files:
    text = read_text(path)
    if not text:
        continue
    law = law_id_from(path)
    recs = split_articles(text, law)
    kept = 0
    for r in recs:
        if not r.get("chars"):
            continue
        if r["chunk_id"] in existing or r["chunk_id"] in seen_new:
            continue
        seen_new.add(r["chunk_id"])
        r["source_url"] = ""
        r["source_type"] = "local"
        r["fetched"] = today
        delta.append(r)
        kept += 1
    print("  %-42s -> %-28s %5d chunk moi" % (os.path.basename(path)[:42], law, kept))

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for d in delta:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
print("delta ghi vao:", OUT, "| so chunk moi:", len(delta))

if delta:
    merged = os.path.join(R, "runs", "civil_chunks_merged.jsonl")
    with io.open(merged, "w", encoding="utf-8", newline="\n") as out:
        for src in (CORPUS, OUT):
            if not os.path.exists(src):
                continue
            with io.open(src, encoding="utf-8") as f:
                for line in f:
                    out.write(line)
    print("ban ghep:", merged)
    print("BUOC TIEP THEO (can mo hinh ma hoa, GPU neu ranh):")
    print("  1) ma hoa chi %d chunk trong delta" % len(delta))
    print("  2) noi vector vao index/vdb_chunks.json")
    print("  3) chay lai src/law_articles_index.py, src/law_rdf_export.py")
    print("  4) chay lai src/law_eval_repro.py va src/law_rerank.py de kiem tra hoi quy")
else:
    print("khong co chunk moi (cac van ban da co trong kho)")