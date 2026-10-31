"""Civil-law chunker: signed PDF -> text -> Dieu/Khoan/Diem records with IDs.
ID scheme: {LAW}|Dieu{d}|Khoan{k}|Diem{p}  (Khoan/Diem empty when absent).
Output (JSONL, one record per line = crash-safe):
  runs/civil_chunks.jsonl : {chunk_id, law_id, dieu, khoan, diem, tieu_de, content, chars}
Usage: python -u law_extract.py <pdf_path> <LAW_ID>
"""
import json, os, re, sys

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
os.makedirs(R, exist_ok=True)

PDF, LAW = sys.argv[1], sys.argv[2]
OUT = f"{R}/civil_chunks.jsonl"

from pypdf import PdfReader

rd = PdfReader(PDF)
raw = []
for i, pg in enumerate(rd.pages):
    try:
        raw.append(pg.extract_text() or "")
    except Exception:
        raw.append("")
text = "\n".join(raw)
print("pages:", len(rd.pages), "chars:", len(text), flush=True)

# cut signature/appendix tail: keep up to last Dieu block
lines = [ln.strip() for ln in text.split("\n")]
recs, cur = [], None

dieu_re = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
khoan_re = re.compile(r"^(\d+)\.\s+(.*)$")


def push():
    global cur
    if cur and cur["content"].strip():
        cur["content"] = cur["content"].strip()
        cur["chars"] = len(cur["content"])
        recs.append(cur)
    cur = None


for ln in lines:
    if not ln:
        continue
    m = dieu_re.match(ln)
    if m:
        push()
        cur = {"chunk_id": "", "law_id": LAW, "dieu": m.group(1), "khoan": "",
               "diem": "", "tieu_de": m.group(2).strip(), "content": ""}
        cur["chunk_id"] = f"{LAW}|Dieu{m.group(1)}"
        continue
    if cur is None:
        continue
    k = khoan_re.match(ln)
    if k and len(k.group(1)) <= 2:
        push_sub = dict(cur)
        push_sub["khoan"] = k.group(1)
        push_sub["chunk_id"] = f"{cur['chunk_id']}|Khoan{k.group(1)}"
        push_sub["content"] = k.group(2)
        cur["_subs"] = cur.get("_subs", []) + [(push_sub, [])]
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

mode = "a" if os.path.exists(OUT) else "w"
n0 = sum(1 for _ in open(OUT, encoding="utf-8")) if mode == "a" else 0
with open(OUT, mode, encoding="utf-8") as f:
    for r in flat:
        if r["chars"] > 0:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
n1 = sum(1 for _ in open(OUT, encoding="utf-8"))
print(f"wrote {n1 - n0} records (total {n1}) -> {OUT}", flush=True)
print("sample:", json.dumps(flat[1] if len(flat) > 1 else {}, ensure_ascii=False)[:300])
