"""Generate SHA256SUMS manifest for a release tree (HF or GH style).

Usage: python lawmanifest.py <tree_root> <out_file> <mode>
mode=hf  : data/, benchmark/, index/, provenance/ (excl SHA), sources_official/,
           docs/graph/, DATASHEET.md, README.md, CITATION.cff, LICENSE
mode=gh  : same universe but with the GH-tree root paths (identical layout)
"""
import hashlib
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

root, out, _ = sys.argv[1], sys.argv[2], sys.argv[3]
targets = {
    "data/civil_chunks.jsonl": None,
    "sources_official/BLDS1995_official.pdf": None,
    "sources_official/BLDS2005_official.pdf": None,
    "sources_official/BLDS2015_official.pdf": None,
    "sources_official/HNGD2000_official.pdf": None,
    "sources_official/TNBTCNN2017_official.pdf": None,
}
UNIV = "benchmark index provenance src docs/graph docs/report/figures tools tools/lab-scripts".split()
SKIP = {"SHA256SUMS"}
for d in UNIV:
    dp = os.path.join(root, d)
    if not os.path.isdir(dp):
        continue
    for fn in sorted(os.listdir(dp)):
        full = os.path.join(dp, fn)
        if os.path.isdir(full):
            continue
        rel = f"{d}/{fn}"
        if fn.startswith("SHA256SUMS"):
            continue
        targets.setdefault(rel, None)
# markdown directly under docs/ (PROTOCOL.md, REPORT.md) + the LaTeX report sources
for fn in sorted(os.listdir(os.path.join(root, "docs"))):
    if fn.endswith(".md"):
        targets.setdefault(f"docs/{fn}", None)
for fn in sorted(os.listdir(os.path.join(root, "docs", "report"))):
    if fn == "ViCivil-TKG_bao-cao.pdf" or fn.endswith(".tex"):
        targets.setdefault(f"docs/report/{fn}", None)
targets.setdefault("DATASHEET.md", None)
targets.setdefault("README.md", None)
targets.setdefault("CITATION.cff", None)
targets.setdefault("LICENSE", None)
targets.setdefault("THIRD-PARTY-NOTICES.md", None)
targets.setdefault("requirements.txt", None)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


lines = []
miss = []
for rel in sorted(targets):
    p = os.path.join(root, rel)
    if os.path.exists(p):
        lines.append(f"{sha(p)}  ./{rel}")
    else:
        miss.append(rel)
_d = os.path.dirname(os.path.abspath(out))
if _d:
    os.makedirs(_d, exist_ok=True)
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("entries:", len(lines), "missing:", miss)

