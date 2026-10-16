"""Broad sweep of congbao.chinhphu.vn: listing pages -> issues -> doc metadata + PDFs.
Pilot:  pages 1-2, 3 issues, 5 docs.  Full: everything, checkpointed, polite.
Usage: python -u law_crawl.py [--pilot | --full]
Outputs: runs/law_index.json (issues+docs+pdf urls), pdfs/ (downloaded files).
"""
import json, os, re, sys, time, urllib.request, urllib.parse

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
P = f"{W}/pdfs"
for d in (W, R, P):
    os.makedirs(d, exist_ok=True)

BASE = "https://congbao.chinhphu.vn"
UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64 (academic research; rate-limited contact: research)"}
DELAY = 1.2
IDX = f"{R}/law_index.json"

try:
    idx = json.load(open(IDX, encoding="utf-8"))
except Exception:
    idx = {"pages_done": [], "issues": {}, "docs": {}}


def get(url, binary=False, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read() if binary else r.read().decode("utf-8", "ignore")
        except Exception as e:
            print("  retry", a, url[:70], repr(e)[:80], flush=True)
            time.sleep(5 + a * 5)
    return None


def save():
    json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False)


def pilot():
    return "--full" not in sys.argv


def main():
    pl = pilot()
    print("mode:", "PILOT" if pl else "FULL", flush=True)
    # ---- 1. listing pages ----
    NPG = 542
    pages = range(1, 3) if pl else range(1, NPG + 1)
    for pg in pages:
        if str(pg) in idx["pages_done"]:
            continue
        h = get(f"{BASE}/cong-bao/trang-{pg}.htm")
        if not h:
            print("page FAIL", pg, flush=True)
            continue
        for m in set(re.findall(r"/cong-bao/(cong-bao-so-\d+-ngay-\d+-\d+-\d+-\d+)\.htm", h)):
            u = f"/cong-bao/{m}.htm"
            if u not in idx["issues"]:
                idx["issues"][u] = {}
        idx["pages_done"].append(str(pg))
        save()
        print(f"page {pg}: issues={len(idx['issues'])}", flush=True)
        time.sleep(DELAY)
    # ---- 2. issues ----
    issues = sorted(idx["issues"])
    if pl:
        issues = issues[:3]
    for iu in issues:
        it = idx["issues"][iu]
        if it.get("done"):
            continue
        h = get(BASE + iu)
        if not h:
            print("issue FAIL", iu, flush=True)
            continue
        m = re.search(r'hdFileUrl" value="([^"]+\.pdf[^"]*)"', h)
        it["issue_pdf"] = m.group(1) if m else None
        n = re.search(r"cong-bao-so-(\d+)-ngay-(\d+)-(\d+)-(\d+)", iu)
        it["so"], it["ngay"] = (n.group(1), f"{n.group(4)}-{n.group(3)}-{n.group(2)}") if n else (None, None)
        it["docs"] = sorted(set(re.findall(r"(/van-ban/[a-z0-9\-]+/\d+\.htm)", h)))
        for d in it["docs"]:
            idx["docs"].setdefault(d, {})
        it["done"] = True
        save()
        print(f"issue {it.get('so')}: pdf={'Y' if it['issue_pdf'] else 'N'} docs={len(it['docs'])}", flush=True)
        time.sleep(DELAY)
    # ---- 3. doc detail pages ----
    docs = sorted(idx["docs"])
    if pl:
        docs = docs[:5]
    for du in docs:
        d = idx["docs"][du]
        if d.get("done"):
            continue
        h = get(BASE + du)
        if not h:
            print("doc FAIL", du, flush=True)
            continue
        txt = re.sub(r"<[^>]+>", " ", h)
        txt = re.sub(r"\s+", " ", txt)
        d["title"] = (re.search(r"<title>([^<]{5,200})</title>", h).group(1).strip()
                      if re.search(r"<title>([^<]{5,200})</title>", h) else du)
        pdfs = sorted(set(re.findall(r"https?://[^\"' ]+\.pdf[^\"' ]*", h)))
        pdfs += sorted(set("https://congbao.chinhphu.vn" + u if u.startswith("/") else u
                           for u in re.findall(r"/api/download/stream\?Url=[A-Za-z0-9_\-]+", h)))
        d["pdfs"] = pdfs
        m = re.search(r"(Luật số|Bộ luật số|Nghị định số|Nghị quyết số|Thông tư số|Quyết định số)\s*([0-9/\-A-ZĐNQHTT]+)", txt)
        d["so_hieu"] = (m.group(1) + " " + m.group(2)) if m else None
        d["done"] = True
        save()
        print(f"doc {d.get('so_hieu') or du[-30:]}: pdfs={len(pdfs)}", flush=True)
        time.sleep(DELAY)
    print("INDEX DONE issues=%d docs=%d" % (len(idx["issues"]), len(idx["docs"])), flush=True)


main()
