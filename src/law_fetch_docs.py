"""Targeted fetch: doc detail pages -> PDFs -> chunks. For 2026 laws + guides.
Usage: law_fetch_docs.py   (URL list inside; checkpointed via law_dl.json)
"""
import json, os, re, time, urllib.request

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64 (academic research)"}
TARGETS = [
    ("/van-ban/luat-so-16-2026-qh16-470451/68490.htm", "HOAGIAI2026", "2026-07-01"),
    ("/van-ban/luat-so-03-2026-qh16-469530/64878.htm", "HOTICH2026", "2026-07-01"),
    ("/van-ban/luat-so-60-2014-qh13-5264/10513.htm", "HOTICH2014_ALT", None),
    ("/van-ban/nghi-dinh-so-123-2015-nd-cp-18108/12709.htm", "ND123_2015", "2015-01-01"),
]


def get(url, binary=False, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read() if binary else r.read().decode("utf-8", "ignore")
        except Exception as e:
            print("retry", url[-40:], repr(e)[:60], flush=True)
            time.sleep(5)
    return None


for path, law, vf in TARGETS:
    h = get("https://congbao.chinhphu.vn" + path)
    if not h:
        print("FAIL page", law, flush=True)
        continue
    pdfs = sorted(set(re.findall(r"https?://[^\"' ]+\.pdf[^\"' ]*", h)))
    pdfs += sorted(set("https://congbao.chinhphu.vn" + u if u.startswith("/") else u
                       for u in re.findall(r"/api/download/stream\?Url=[A-Za-z0-9_\-]+", h)))
    print(law, "pdfs:", len(pdfs), flush=True)
    for purl in pdfs[:2]:
        fn = re.sub(r"[^A-Za-z0-9\-.]", "_", purl.split("/")[-1].split("?")[0])[:70] or "doc.pdf"
        if not fn.lower().endswith(".pdf"):
            fn += ".pdf"
        fp = os.path.join(P, law + "__" + fn)
        if os.path.exists(fp) and os.path.getsize(fp) > 10000:
            print("  have", fn[:40], flush=True)
            continue
        d = get(purl, binary=True)
        if d and len(d) > 10000:
            open(fp, "wb").write(d)
            print("  saved", fn[:40], len(d), flush=True)
        time.sleep(1)
    time.sleep(1)
print("FETCH DONE", flush=True)
