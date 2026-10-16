"""Batch: downloaded civil PDFs -> text -> flow-chunk -> civil_chunks.jsonl.
Text-layer check (skip scans for OCR-later list). Dates parsed from preamble
('co hieu luc tu ngay...'); provisional + needs_review flag when absent.
Law ID from filename so_hieu. Appends; never rewrites existing chunks.
"""
import json, os, re, sys

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
OUT = f"{R}/civil_chunks.jsonl"
UP = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"

have = set()
for L in open(OUT, encoding="utf-8"):
    have.add(json.loads(L)["chunk_id"])
print("existing chunks:", len(have), flush=True)

from pypdf import PdfReader

DM = {"01": "01", "02": "02", "03": "03", "04": "04", "05": "05", "06": "06",
      "07": "07", "08": "08", "09": "09", "10": "10", "11": "11", "12": "12"}


def find_date(t, keys):
    for k in keys:
        m = re.search(k + r"[^\d]{0,40}?ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", t[:4000])
        if m:
            return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    return None


def flow_chunks(flow, law):
    dblocks = re.split(r"(?=Điều\s+\d+\.)", flow)
    recs = []
    for b in dblocks:
        m = re.match(r"Điều\s+(\d+)\.\s*(.*)$", b, re.S)
        if not m:
            continue
        d, rest = m.group(1), m.group(2)
        title = rest.split(".")[0][:120] if "." in rest else rest[:120]
        base = f"{law}|Dieu{d}"
        ks = re.split(r"(?<=\s)(\d{1,2})\.\s+(?=[%s])" % UP, rest)
        if len(ks) < 3:
            recs.append({"chunk_id": base, "law_id": law, "dieu": d, "khoan": "",
                         "diem": "", "tieu_de": title, "content": rest.strip()[:6000]})
            continue
        for i in range(1, len(ks) - 1, 2):
            kn, kt = ks[i], ks[i + 1]
            kid = f"{base}|Khoan{kn}"
            ds = re.split(r"(?<=\s)([a-zđ])\)\s+", kt)
            if len(ds) < 3:
                recs.append({"chunk_id": kid, "law_id": law, "dieu": d, "khoan": kn,
                             "diem": "", "tieu_de": title, "content": kt.strip()[:6000]})
            else:
                for j in range(1, len(ds) - 1, 2):
                    recs.append({"chunk_id": f"{kid}|Diem{ds[j]}", "law_id": law,
                                 "dieu": d, "khoan": kn, "diem": ds[j],
                                 "tieu_de": title,
                                 "content": (kt[:200] + " [...] " + ds[j + 1]).strip()[:6000]})
    return recs


pdfs = sorted(f for f in os.listdir(P) if f.lower().endswith(".pdf"))
print("pdfs:", len(pdfs), flush=True)
scans, added, laws = [], 0, set()
with open(OUT, "a", encoding="utf-8") as f:
    for fn in pdfs:
        law = re.sub(r"__.*$", "", fn).replace("_", "/")[:40] or "UNKN"
        try:
            rd = PdfReader(os.path.join(P, fn))
            tx = "\n".join([(pg.extract_text() or "") for pg in rd.pages])
            flow = re.sub(r"\s+", " ", tx).strip()
            if len(flow) < len(rd.pages) * 200:
                scans.append(fn)
                continue
            vf = find_date(flow, ["có hiệu lực", "hiệu lực thi hành"]) or "2000-01-01"
            recs = flow_chunks(flow, law)
            n0 = 0
            for r in recs:
                r["chars"] = len(r["content"])
                r["valid_from"] = vf
                if r["chars"] >= 20 and r["chunk_id"] not in have:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    have.add(r["chunk_id"])
                    n0 += 1
            laws.add(law)
            added += n0
            print(f"{fn[:50]}: +{n0} valid_from={vf}", flush=True)
        except Exception as e:
            print("ERR", fn[:50], repr(e)[:80], flush=True)
print(f"BATCH DONE added={added} laws={len(laws)} scans_skipped={len(scans)}", flush=True)
json.dump({"scans": scans}, open(f"{R}/law_scans.json", "w", encoding="utf-8"), ensure_ascii=False)
# auto-register new laws into temporal graph (provisional, flagged review)
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
have_laws = {L["law_id"] for L in G["laws"]}
vf_by_law = {}
for L in open(OUT, encoding="utf-8"):
    r = json.loads(L)
    if r["law_id"] not in have_laws:
        vf_by_law.setdefault(r["law_id"], r.get("valid_from", "2000-01-01"))
for lid, vf in sorted(vf_by_law.items()):
    G["laws"].append({"law_id": lid, "ten": lid, "so_hieu": lid,
                      "valid_from": vf, "valid_to": None, "status": "needs_review"})
    have_laws.add(lid)
json.dump(G, open(f"{R}/temporal_graph.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("temporal laws now:", len(G["laws"]), flush=True)
