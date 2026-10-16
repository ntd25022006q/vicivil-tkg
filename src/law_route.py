"""Layout router (proposal P2 implemented): given a file, decide parser or quarantine.
Rules: text chars/page >=200 -> line/flow parser (flow if avg words/line <4);
else -> quarantine (scan/OCR-later). Emits routing report JSON.
Usage: law_route.py <file-or-dir>...
"""
import json, os, re, sys

from pypdf import PdfReader

REP = []


def route_pdf(fp):
    try:
        rd = PdfReader(fp)
        n = len(rd.pages)
        tx = "\n".join([(pg.extract_text() or "") for pg in rd.pages[:5]])
        cpline = len(tx) / max(1, tx.count("\n"))
        wpl = len(tx.split()) / max(1, tx.count("\n"))
        if len(tx) < n * 40 and n > 0:
            return {"file": fp, "route": "quarantine_scan", "reason": "no text layer"}
        if wpl < 4:
            return {"file": fp, "route": "flow_parser", "reason": f"word-per-line ({wpl:.1f} wpl)"}
        return {"file": fp, "route": "line_parser", "reason": f"normal ({wpl:.1f} wpl)"}
    except Exception as e:
        return {"file": fp, "route": "quarantine_error", "reason": repr(e)[:80]}


def route_doc(fp):
    return {"file": fp, "route": "ole_parser", "reason": "legacy .doc via olefile"}


for a in sys.argv[1:]:
    paths = [os.path.join(a, f) for f in os.listdir(a)] if os.path.isdir(a) else [a]
    for p in paths:
        if p.lower().endswith(".pdf"):
            REP.append(route_pdf(p))
        elif p.lower().endswith(".doc"):
            REP.append(route_doc(p))
print(json.dumps(REP, ensure_ascii=False, indent=1)[:2000], flush=True)
q = [r for r in REP if r["route"].startswith("quarantine")]
print(f"routed={len(REP)} quarantine={len(q)}", flush=True)
