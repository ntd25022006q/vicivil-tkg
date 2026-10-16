"""Generic fetcher: vanban.chinhphu.vn docid -> attachment (.doc/.pdf) -> text -> chunks.
Usage: law_fetch_vanban.py <docid> <LAW_ID> <valid_from>
Finds attachment href on the doc page (same onDownload pattern as NCN2010).
"""
import json, os, re, sys, time, urllib.request

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64"}
DOCID, LAW, VF = sys.argv[1], sys.argv[2], sys.argv[3]


def get(url, binary=False, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read() if binary else r.read().decode("utf-8", "ignore")
        except Exception as e:
            print("retry", a, repr(e)[:70], flush=True)
            time.sleep(5)
    return None


h = get(f"https://vanban.chinhphu.vn/default.aspx?docid={DOCID}&pageid=27160")
assert h, "doc page failed"
cands = set(re.findall(r"(?:https?://datafiles[^\s\"']+?\.do[cx]?|[A-Za-z0-9_/.\-]*[0-9]{4,}_[a-z0-9]+\.do[cx]?)", h))
print("candidates:", list(cands)[:5], flush=True)
data, src = None, None
for c in cands:
    u = c if c.startswith("http") else "https://datafiles.chinhphu.vn/cpp/files/vbpq/" + c.lstrip("/")
    for uu in [u, u.replace("/vbpq/", "/vbpq/20" + DOCID[:2] + "/")]:
        data = get(uu, binary=True, tries=1)
        if data and len(data) > 20000:
            src = uu
            break
    if data:
        break
assert data, "no attachment downloaded"
print("got", len(data), "bytes from", src, flush=True)
fp = f"/tmp/{LAW}.doc"
open(fp, "wb").write(data)

import olefile
texts = []
try:
    ole = olefile.OleFileIO(fp)
    raw = ole.openstream("WordDocument").read().decode("utf-16-le", errors="ignore")
    texts = [p.strip() for p in re.split(r"[\r\n\x07]+", raw) if len(p.strip()) > 2]
    print("ole paras:", len(texts), flush=True)
except Exception as e:
    print("ole fail, fallback strings:", repr(e)[:80], flush=True)
    raw = open(fp, "rb").read().decode("utf-16-le", errors="ignore")
    texts = [p.strip() for p in re.split(r"[\r\n\x07]+", raw) if len(p.strip()) > 2]
t = "\n".join(texts)
open(f"/tmp/{LAW}.txt", "w", encoding="utf-8").write(t)
dies = list(dict.fromkeys(re.findall(r"Điều\s+(\d+)\.", t)))
print("dieu:", len(dies), dies[:3], dies[-3:], flush=True)
json.dump({"law": LAW, "docid": DOCID, "src": src, "dieu": len(dies), "vf": VF},
          open(f"/tmp/{LAW}.meta.json", "w", encoding="utf-8"), ensure_ascii=False)
