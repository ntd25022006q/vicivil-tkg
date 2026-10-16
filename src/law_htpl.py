"""Per-article crawl from hethongphapluat (static, polite).
Usage: law_htpl.py <slug> <LAW_ID> <max_n>   e.g. luat-thi-hanh-an-dan-su-2008 THADS2008 200
Output: /tmp/<LAW_ID>_htpl.txt (assembled full text) + checkpoint json.
"""
import json, os, re, sys, time, html as ihtml, urllib.request

SLUG, LAW, MAXN = sys.argv[1], sys.argv[2], int(sys.argv[3])
UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64"}
CK = f"/tmp/htpl_{LAW}.json"
OUT = f"/tmp/{LAW}_htpl.txt"
try:
    done = json.load(open(CK, encoding="utf-8"))
except Exception:
    done = {}


def get(url):
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print("retry", url[-20:], repr(e)[:60], flush=True)
            time.sleep(5)
    return None


def body_of(h, n):
    t = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<header.*?</header>", " ", t, flags=re.S)
    t = re.sub(r"<footer.*?</footer>", " ", t, flags=re.S)
    t = re.sub(r"<nav.*?</nav>", " ", t, flags=re.S)
    # main article block: heading Dieu N followed by content before TOC/footer
    m = re.search(r"(Điều\s+%d\..{0,12000})" % n, t, re.S)
    if not m:
        return None
    seg = m.group(1)
    seg = re.sub(r"<[^>]+>", "\n", seg)
    seg = ihtml.unescape(seg)
    lines = [L.strip() for L in seg.split("\n") if len(L.strip()) > 2]
    # cut at TOC tail (lines starting with 'Điều ' that are titles only)
    out = []
    for L in lines:
        out.append(L)
        if len("\n".join(out)) > 6000:
            break
    return "\n".join(out)


got, miss = 0, 0
for n in range(1, MAXN + 1):
    k = str(n)
    if k in done:
        got += 1
        continue
    h = get(f"https://hethongphapluat.com/{SLUG}/dieu-{n}")
    if not h:
        miss += 1
        if miss > 5:
            break
        continue
    b = body_of(h, n)
    if b and f"Điều {n}." in b:
        done[k] = b
        got += 1
    else:
        miss += 1
        if miss > 5:
            break
    json.dump(done, open(CK, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(1)
    if n % 30 == 0:
        print(f"{LAW} {n}/{MAXN} got={got}", flush=True)
full = []
for k in sorted(done, key=int):
    full.append(done[k])
open(OUT, "w", encoding="utf-8").write("\n\n".join(full))
print(f"DONE {LAW}: {len(done)} articles -> {OUT}", flush=True)
