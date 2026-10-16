"""Civil chunker v1b (text input): BLDS full text -> Dieu/Khoan(/Diem) JSONL.
Dedup: TOC repeats each Dieu -> keep LONGEST block per Dieu number.
ID: {LAW}|Dieu{d}[|Khoan{k}[|Diem{p}]]   Usage: law_chunk_text.py <txt> <LAW_ID>
"""
import json, os, re, sys

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
os.makedirs(R, exist_ok=True)
TXT, LAW = sys.argv[1], sys.argv[2]
OUT = f"{R}/civil_chunks.jsonl"

text = open(TXT, encoding="utf-8").read()
lines = [ln.strip() for ln in text.split("\n")]

dieu_re = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
khoan_re = re.compile(r"^(\d{1,2})\.\s+(.{15,})$")
diem_re = re.compile(r"^([a-zđ])\)\s+(.{5,})$")

blocks, cur = [], None


def push():
    global cur
    if cur and cur["content"].strip():
        cur["content"] = cur["content"].strip()
        blocks.append(cur)
    cur = None


for ln in lines:
    if not ln:
        continue
    m = dieu_re.match(ln)
    if m:
        push()
        cur = {"dieu": m.group(1), "tieu_de": m.group(2).strip(), "content": ""}
        continue
    if cur is None:
        continue
    cur["content"] += ("\n" if cur["content"] else "") + ln
push()

by_dieu = {}
for b in blocks:
    k = b["dieu"]
    if k not in by_dieu or len(b["content"]) > len(by_dieu[k]["content"]):
        by_dieu[k] = b
print(f"raw blocks={len(blocks)} unique dieu={len(by_dieu)}", flush=True)

recs = []
for d in sorted(by_dieu, key=int):
    b = by_dieu[d]
    base = f"{LAW}|Dieu{d}"
    parts, curk = [], None
    for ln in b["content"].split("\n"):
        km = khoan_re.match(ln)
        if km:
            if curk:
                parts.append(curk)
            curk = {"khoan": km.group(1), "content": km.group(2), "subs": []}
            continue
        dm = diem_re.match(ln)
        if dm and curk is not None:
            curk["subs"].append((dm.group(1), dm.group(2)))
            continue
        if curk is not None:
            if curk["subs"]:
                p, tx = curk["subs"][-1]
                curk["subs"][-1] = (p, tx + " " + ln)
            else:
                curk["content"] += " " + ln
    if curk:
        parts.append(curk)
    if not parts:
        recs.append({"chunk_id": base, "law_id": LAW, "dieu": d, "khoan": "",
                     "diem": "", "tieu_de": b["tieu_de"],
                     "content": b["content"][:6000]})
    else:
        for p in parts:
            kid = f"{base}|Khoan{p['khoan']}"
            if not p["subs"]:
                recs.append({"chunk_id": kid, "law_id": LAW, "dieu": d,
                             "khoan": p["khoan"], "diem": "",
                             "tieu_de": b["tieu_de"], "content": p["content"][:6000]})
            else:
                for dp, dtx in p["subs"]:
                    recs.append({"chunk_id": f"{kid}|Diem{dp}", "law_id": LAW,
                                 "dieu": d, "khoan": p["khoan"], "diem": dp,
                                 "tieu_de": b["tieu_de"],
                                 "content": (p["content"] + " " + dtx).strip()[:6000]})

mode = "a" if os.path.exists(OUT) else "w"
n0 = sum(1 for _ in open(OUT, encoding="utf-8")) if mode == "a" else 0
bad = 0
with open(OUT, mode, encoding="utf-8") as f:
    for r in recs:
        r["chars"] = len(r["content"])
        if r["chars"] < 20:
            bad += 1
            continue
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
n1 = sum(1 for _ in open(OUT, encoding="utf-8"))
print(f"kept={n1 - n0} total={n1} skipped_short={bad}", flush=True)
ks = {}
for r in recs:
    ks[r["chunk_id"].count("|")] = ks.get(r["chunk_id"].count("|"), 0) + 1
print("by level (1=Dieu,2=Khoan,3=Diem):", ks, flush=True)
