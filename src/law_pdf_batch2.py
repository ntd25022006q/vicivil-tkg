"""Cleanup bad 'nod' chunks + fixed batch v2 (law_id from index URL slug).
Step 1: drop law_id=='nod' chunks; drop 'nod' law from temporal graph.
Step 2: reprocess pdfs with file->doc map from law_dl.json.
"""
import json, os, re

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
UP = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"

# --- step 1: cleanup ---
rows = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
keep = [r for r in rows if r["law_id"] != "nod"]
print(f"cleanup chunks: {len(rows)} -> {len(keep)} (drop {len(rows) - len(keep)})", flush=True)
with open(f"{R}/civil_chunks.jsonl", "w", encoding="utf-8") as f:
    for r in keep:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
G["laws"] = [L for L in G["laws"] if L["law_id"] != "nod"]
json.dump(G, open(f"{R}/temporal_graph.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("temporal laws:", len(G["laws"]), flush=True)

# --- step 2: file -> doc map ---
dl = json.load(open(f"{R}/law_dl.json", encoding="utf-8"))
idx = json.load(open(f"{R}/law_index.json", encoding="utf-8"))
f2doc = {}
for u, d in dl.items():
    for fp in d.get("files", []):
        f2doc[os.path.basename(fp)] = u


def law_id_of(fn, u):
    slug = u.strip("/").split("/")[-2] if "/van-ban/" in u else u.strip("/")[-40:]
    slug = re.sub(r"[^a-z0-9\-]", "", slug.lower())[:60] or "unk"
    return slug


from pypdf import PdfReader


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


have = set()
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    have.add(json.loads(L)["chunk_id"])
pdfs = sorted(f for f in os.listdir(P) if f.lower().endswith(".pdf"))
print("pdfs:", len(pdfs), flush=True)
added, laws, scans, orphan = 0, set(), [], 0
with open(f"{R}/civil_chunks.jsonl", "a", encoding="utf-8") as f:
    for fn in pdfs:
        u = None
        for docu, lst in dl.items():
            if fn in [os.path.basename(x) for x in lst.get("files", [])]:
                u = docu
                break
        if not u:
            orphan += 1
            continue
        law = law_id_of(fn, u)
        try:
            rd = PdfReader(os.path.join(P, fn))
            tx = "\n".join([(pg.extract_text() or "") for pg in rd.pages])
            flow = re.sub(r"\s+", " ", tx).strip()
            if len(flow) < len(rd.pages) * 200:
                scans.append(fn)
                continue
            vf = find_date(flow, ["có hiệu lực", "hiệu lực thi hành"]) or "2000-01-01"
            n0 = 0
            for r in flow_chunks(flow, law):
                r["chars"] = len(r["content"])
                r["valid_from"] = vf
                if r["chars"] >= 20 and r["chunk_id"] not in have:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    have.add(r["chunk_id"])
                    n0 += 1
            laws.add(law)
            added += n0
            print(f"{law[:45]}: +{n0} vf={vf}", flush=True)
        except Exception as e:
            print("ERR", fn[:45], repr(e)[:70], flush=True)
print(f"V2 DONE added={added} laws={len(laws)} orphan={orphan} scans={len(scans)}", flush=True)
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
have_laws = {L["law_id"] for L in G["laws"]}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    if r["law_id"] not in have_laws:
        G["laws"].append({"law_id": r["law_id"], "ten": r["law_id"], "so_hieu": r["law_id"],
                          "valid_from": r.get("valid_from", "2000-01-01"), "valid_to": None,
                          "status": "needs_review"})
        have_laws.add(r["law_id"])
json.dump(G, open(f"{R}/temporal_graph.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("temporal laws now:", len(G["laws"]), flush=True)
