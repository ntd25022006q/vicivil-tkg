"""Save per-Q ranks for A-dense (fast, ollama only) for significance testing."""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
qv = rt.embed([b["question"] for b in bench])
out = {}
for bi, b in enumerate(bench):
    vix = rt.valid_idx(b["as_of"])
    if not vix:
        continue
    dd = (rt.cmat[vix] @ qv[bi]).tolist()
    od = sorted(range(len(vix)), key=lambda r: -dd[r])[:10]
    out[b["qid"]] = [rt.chunks[vix[r]]["__id__"] for r in od]
    if (bi + 1) % 50 == 0:
        print(f"[{bi + 1}/{len(bench)}]", flush=True)
json.dump(out, open(f"{R}/ranks_dense.json", "w", encoding="utf-8"), ensure_ascii=False)
print("RANKS-A DONE n=", len(out), flush=True)
