"""Download PDFs for civil-law docs from the broad index (CPU/network only).
Filter: civil keywords in title/url + all VBHN (consolidated) docs.
Checkpointed per doc, polite 1s, skip >60MB. -> pdfs/ + runs/law_dl.json
"""
import json, os, time, urllib.request

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
os.makedirs(P, exist_ok=True)
OUT = f"{R}/law_dl.json"
UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64 (academic research; rate-limited)"}
KEYS = ["dan-su", "dan su", "hon-nhan", "gia-dinh", "thua-ke", "hop-dong",
        "so-huu", "boi-thuong", "cap-duong", "con-nuoi", "thua-ke", "vbhn",
        "hon nhan", "thừa kế", "dân sự", "hợp đồng", "sở hữu", "bồi thường",
        "cấp dưỡng", "con nuôi"]

idx = json.load(open(f"{R}/law_index.json", encoding="utf-8"))
try:
    dl = json.load(open(OUT, encoding="utf-8"))
except Exception:
    dl = {}
cands = []
for u, d in idx.get("docs", {}).items():
    t = ((d.get("title") or "") + " " + u).lower()
    if any(k in t for k in KEYS) and d.get("pdfs"):
        cands.append((u, d))
print("civil candidates:", len(cands), flush=True)
n_new = n_skip = n_fail = 0
for u, d in cands:
    if u in dl and dl[u].get("done"):
        n_skip += 1
        continue
    saved = []
    for purl in d["pdfs"][:2]:
        try:
            fn = "".join(c if c.isalnum() or c in "-_." else "_" for c in purl.split("/")[-1].split("?")[0])[:80]
            if not fn.lower().endswith(".pdf"):
                fn += ".pdf"
            fp = os.path.join(P, (d.get("so_hieu") or "nod").replace("/", "_")[:40] + "__" + fn)
            if os.path.exists(fp) and os.path.getsize(fp) > 10000:
                saved.append(fp)
                continue
            req = urllib.request.Request(purl, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                if int(r.headers.get("Content-Length", "0")) > 60 * 1024 * 1024:
                    continue
                data = r.read()
            if len(data) < 10000:
                continue
            open(fp, "wb").write(data)
            saved.append(fp)
            time.sleep(1)
        except Exception as e:
            print("  fail", purl[:60], repr(e)[:60], flush=True)
    dl[u] = {"so_hieu": d.get("so_hieu"), "files": saved, "done": True}
    if saved:
        n_new += 1
    else:
        n_fail += 1
    json.dump(dl, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    if (n_new + n_fail) % 20 == 0:
        print(f"progress new={n_new} fail={n_fail} skip={n_skip}", flush=True)
    time.sleep(1)
print(f"DL DONE new={n_new} fail={n_fail} skip={n_skip}", flush=True)
