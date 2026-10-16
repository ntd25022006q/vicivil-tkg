"""Mine amendment lists from Preamble chunks (+VBHN-21 PDF) into verified AMENDS edges.
Pattern: 'Luật số X/... ngày DD tháng MM năm YYYY ... có hiệu lực kể từ ngày DD/MM/YYYY'.
Output: runs/amend_candidates.json for review (NOT auto-merged).
"""
import json, os, re

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
texts = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    if r["chunk_id"].endswith("|Preamble"):
        texts[r["law_id"]] = r["content"]
# VBHN-21 preamble from its PDF
for fn in os.listdir(P):
    if "468974" in fn and fn.endswith(".pdf"):
        from pypdf import PdfReader
        rd = PdfReader(os.path.join(P, fn))
        tx = "\n".join([(pg.extract_text() or "") for pg in rd.pages[:6]])
        m = re.search(r"Điều\s+1\.", tx)
        texts["van-ban-hop-nhat-so-21-vbhn-vpqh-468974"] = re.sub(
            r"\s+", " ", tx[:m.start()] if m else tx[:4000])
        break
print("preambles:", list(texts), flush=True)
pat = re.compile(
    r"(Luật|Nghị định|Nghị quyết|Pháp lệnh|Thông tư)[^.]{0,60}?số\s+([0-9/\-A-ZĐNQHTTLVBhnpq]+).*?"
    r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.S)
eff = re.compile(r"có hiệu lực(?: kể từ ngày)?\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})|"
                    r"có hiệu lực kể từ ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})")
out = []
BASE = {"HNGDVBHN2025": "52/2014/QH13", "THADSVBHN": "26/2008/QH12",
        "van-ban-hop-nhat-so-21-vbhn-vpqh-468974": "92/2015/QH13"}
for law, t in texts.items():
    for m in pat.finditer(t):
        num = re.sub(r"\s+", "", m.group(2))[:30]
        if num == BASE.get(law):
            continue
        seg = t[m.start():m.start() + 500]
        e = eff.search(seg)
        if e:
            g = [x for x in e.groups() if x is not None]
            ed = f"{g[2]}-{g[1].zfill(2)}-{g[0].zfill(2)}" if len(g) == 3 else None
        else:
            ed = None
        key = (num, law)
        if not any(o["amender"].endswith(num) and o["target_law"] == law for o in out):
            out.append({"target_law": law, "amender": f"{m.group(1)} số {num}",
                        "issued": f"{m.group(5)}-{m.group(4).zfill(2)}-{m.group(3).zfill(2)}",
                        "effective": ed})
json.dump(out, open(f"{R}/amend_candidates.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("candidates:", len(out), flush=True)
for o in out:
    print(f'{o["amender"]} ({o["issued"]}, eff {o["effective"]}) -> {o["target_law"]}', flush=True)
