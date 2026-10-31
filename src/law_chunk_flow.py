"""Civil chunker (flow mode): for PDFs whose text comes word-per-line.
Joins everything to one flow, then regex-splits Dieu -> Khoan -> Diem.
Usage: law_chunk_flow.py <txt> <LAW_ID>   (appends to civil_chunks.jsonl)
"""
import json, os, re, sys

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
TXT, LAW = sys.argv[1], sys.argv[2]
OUT = f"{R}/civil_chunks.jsonl"

flow = re.sub(r"\s+", " ", open(TXT, encoding="utf-8").read()).strip()
print("flow chars:", len(flow), flush=True)

UP = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
dblocks = re.split(r"(?=Điều\s+\d+\.)", flow)
print("dieu blocks:", len(dblocks), flush=True)

recs = []
for b in dblocks:
    m = re.match(r"Điều\s+(\d+)\.\s*(.*)$", b, re.S)
    if not m:
        continue
    d, rest = m.group(1), m.group(2)
    title = rest.split(".")[0][:120] if "." in rest else rest[:120]
    base = f"{LAW}|Dieu{d}"
    ks = re.split(r"(?<=\s)(\d{1,2})\.\s+(?=[%s])" % UP, rest)
    if len(ks) < 3:
        recs.append({"chunk_id": base, "law_id": LAW, "dieu": d, "khoan": "",
                     "diem": "", "tieu_de": title, "content": rest.strip()[:6000]})
        continue
    head, tail = ks[0], ks[1:]
    for i in range(0, len(tail) - 1, 2):
        kn, kt = tail[i], tail[i + 1]
        kid = f"{base}|Khoan{kn}"
        ds = re.split(r"(?<=\s)([a-zđ])\)\s+", kt)
        if len(ds) < 3:
            recs.append({"chunk_id": kid, "law_id": LAW, "dieu": d, "khoan": kn,
                         "diem": "", "tieu_de": title, "content": kt.strip()[:6000]})
        else:
            for j in range(1, len(ds) - 1, 2):
                recs.append({"chunk_id": f"{kid}|Diem{ds[j]}", "law_id": LAW,
                             "dieu": d, "khoan": kn, "diem": ds[j],
                             "tieu_de": title,
                             "content": (kt[:200] + " [...] " + ds[j + 1]).strip()[:6000]})

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
print(f"kept={n1 - n0} total={n1} skipped={bad}", flush=True)
