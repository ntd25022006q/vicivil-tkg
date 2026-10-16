"""RTF -> text (Unicode escapes + control strip), then chunk like others."""
import json, re, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 Windows NT 10.0 Win64 x64"}
URL, LAW, VF = sys.argv[1], sys.argv[2], sys.argv[3]
req = urllib.request.Request(URL, headers=UA)
with urllib.request.urlopen(req, timeout=120) as r:
    raw = r.read()
print("bytes:", len(raw), flush=True)
t = raw.decode("utf-8", errors="ignore")


def rtf2text(s):
    s = re.sub(r"\\u(-?\d+)(\\\S{0,4}|\s?)",
               lambda m: chr(int(m.group(1)) % 65536) + "", s)
    s = re.sub(r"\\'[0-9a-fA-F]{2}",
               lambda m: bytes([int(m.group(0)[2:], 16)]).decode("cp1258", "ignore"), s)
    s = re.sub(r"\\par[d]?", "\n", s)
    s = re.sub(r"\{[^{}]*\}", " ", s)
    s = re.sub(r"\\[a-z]+\d*\s?", " ", s)
    s = re.sub(r"[{}]", " ", s)
    return s


tx = rtf2text(t)
tx = re.sub(r"[ \t\xa0]+", " ", tx)
tx = re.sub(r"\n\s*\n+", "\n", tx)
open(f"/tmp/{LAW}.txt", "w", encoding="utf-8").write(tx)
print("chars:", len(tx), flush=True)
dies = list(dict.fromkeys(re.findall(r"Điều\s+(\d+)\.", tx)))
print("dieu:", len(dies), dies[:3], dies[-3:], flush=True)
