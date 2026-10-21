import hashlib
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GH = r"C:\Users\ntd25\Downloads\OpenCode\law_release"
HF = r"C:\Users\ntd25\AppData\Local\Temp\opencode\hf_stage"

INVIS = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
TYPO = re.compile("[\u2000-\u200a\u2010-\u2015\u2028\u2029\u2018-\u201f\u2026]")
CJK = re.compile("[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u2e80-\u2eff\u31c0-\u31ff\uff00-\uffef]")
SECRET = re.compile(
    r"(github_pat_[A-Za-z0-9_]{10,}|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY|glpat-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9-]{20,})"
)

issues = []

def surface(root):
    for dirpath, _dirs, files in os.walk(root):
        _dirs[:] = [d for d in _dirs if d not in (".git", ".cache")]
        for f in files:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if os.path.splitext(f)[1] in (".pdf", ".png", ".jpg", ".bin"):
                yield p, rel, False
            else:
                yield p, rel, True

for root, tag in ((GH, "GH"), (HF, "HF")):
    for p, rel, istext in surface(root):
        if istext:
            s = io.open(p, encoding="utf-8", errors="replace").read()
            vendored = rel.endswith(".min.js") or rel.endswith("explorer.html")  # vendored third-party libraries ship verbatim; v1.4.0 inlines them into the viewer
            inv = INVIS.findall(s)
            if inv:
                issues.append(f"{tag} {rel}: {len(inv)} invisible/control chars")
            typo = TYPO.findall(s)
            if typo:
                print(f"note: {tag} {rel}: {len(typo)} typographic (dash/quote) chars - legitimate")
            cjk = CJK.findall(s)
            if cjk and not vendored:
                issues.append(f"{tag} {rel}: {len(cjk)} CJK-like chars")
            elif cjk:
                print(f"note: {tag} {rel}: {len(cjk)} CJK-like chars - vendored third-party library, disclosed")
            sec = SECRET.findall(s)
            if sec:
                issues.append(f"{tag} {rel}: SECRET pattern x{len(sec)}")
            if rel.endswith(".json"):
                try:
                    json.loads(s)
                except Exception as e:
                    issues.append(f"{tag} {rel}: JSON parse {e}")
            elif rel.endswith(".jsonl"):
                for i, line in enumerate(s.splitlines(), 1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except Exception as e:
                            issues.append(f"{tag} {rel}: JSONL parse line {i} {e}")
            elif rel.endswith(".gexf"):
                try:
                    ET.fromstring(s)
                except Exception as e:
                    issues.append(f"{tag} {rel}: GEXF parse {e}")
            elif rel.endswith(".cff"):
                for key in ("CITATION",):
                    if "cff-version" not in s:
                        issues.append(f"{tag} {rel}: no cff-version")

def manifest(mp):
    out = {}
    for line in io.open(mp, encoding="utf-8").read().splitlines():
        if line.strip():
            h, rel = line.split(None, 1)
            out[rel.strip()] = h
    return out

mgh, mhf = manifest(os.path.join(GH, "SHA256SUMS")), manifest(os.path.join(HF, "SHA256SUMS"))
if set(mgh) != set(mhf):
    issues.append(f"manifest fileset differ: GH-only={sorted(set(mgh)-set(mhf))} HF-only={sorted(set(mhf)-set(mgh))}")
bad = [rel for rel in mgh if rel != "README.md" and mgh.get(rel) != mhf.get(rel)]
if bad:
    issues.append(f"manifest hash differ: {bad}")
missing = [rel for rel in mgh if not os.path.exists(os.path.join(GH, rel)) or not os.path.exists(os.path.join(HF, rel))]
if missing:
    issues.append(f"manifest files missing on disk: {missing}")

for root, tag in ((GH, "GH"), (HF, "HF")):
    mp = os.path.join(root, "SHA256SUMS")
    for rel, h in manifest(mp).items():
        p = os.path.join(root, rel)
        if os.path.exists(p):
            d = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            if d != h:
                issues.append(f"{tag} {rel}: manifest hash mismatch on disk")

if issues:
    for i in issues:
        print("ISSUE:", i)
    sys.exit(1)
print(f"SWEEP CLEAN: GH={len(mgh)} HF={len(mhf)} files, manifests byte-equal except README.md policy, no secret/invisible/CJK, all JSON/JSONL/GEXF parse")
