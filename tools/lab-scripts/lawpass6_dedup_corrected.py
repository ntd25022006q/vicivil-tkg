"""Pass 6: correct near-dup collapse (same-sig + both-active-at-as_of only,
never across disjoint-version laws) -> full eval -> law_eval_dedupcollapse_corrected.json.
"""
import io, json, re, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
CM = {c["chunk_id"]: c for c in chunks}
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
VF = {L["law_id"]: [L.get("valid_from") or "0000", L.get("valid_to") or "2999-12-31"]
      for L in G["laws"]}


def norm(s):
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"^(Điều \d+[\.:]?|[\d\.]+-|[\wđ]+\) )", "", s[:400])
    return s


sig = {}
for c in CM.values():
    sig.setdefault(norm(c["content"][:400]), []).append(c["chunk_id"])
print("dup groups:", sum(1 for v in sig.values() if len(v) > 1), flush=True)


def active(law_id, d):
    lo, hi = VF.get(law_id, ["0000", "2999-12-31"])
    return (lo <= (d or "9999")) and not ((d or "9999-01-01") >= hi)


def vbhn(law_id):
    return law_id.startswith("van-ban-hop-nhat") or law_id.startswith("THADSVBHN")


sys.path.insert(0, f"{W}/src")
from law_adgr import LawRetriever
rt = LawRetriever()
_orig = rt.retrieve


def retrieve_dedup(q, as_of=None, topk=10, rerank=True, mode="hybrid"):
    res = _orig(q, as_of=as_of, topk=topk * 3, rerank=rerank, mode=mode)
    got = []
    seen_sig = set()
    for r in res:
        cid = r if isinstance(r, str) else (r.get("chunk_id") or r.get("__id__") or "")
        s = norm(CM[cid]["content"][:400])
        ch = CM[cid]
        if s in seen_sig and as_of and active(ch["law_id"], as_of):
            lead = sig[s][0] if len(sig[s]) > 1 else cid
            retain_peer = vbhn(lead) ^ vbhn(ch["law_id"])
            if not retain_peer:
                continue
            if vbhn(ch["law_id"]):
                continue
        if s in seen_sig and as_of and not active(ch["law_id"], as_of):
            continue
        seen_sig.add(s)
        got.append(cid)
        if len(got) >= topk:
            break
    return got


rt.retrieve = retrieve_dedup
qs = []
for fn in ["law_bench_main.json", "law_bench_seed.json"]:
    qs += json.load(open(f"{R}/{fn}", encoding="utf-8"))
h = {1: 0, 3: 0, 5: 0, 10: 0}
mrr, n = 0.0, 0
strat = {}
rowsout = []
t0 = time.time()
for o in qs:
    got = rt.retrieve(o["question"], as_of=o.get("as_of"), topk=10, rerank=True, mode="hybrid")
    gg = o["gold_ids"]
    rank = next((i + 1 for i, g in enumerate(got[:10]) if g in gg), None)
    for k in h:
        h[k] += int(rank is not None and rank <= k)
    mrr += (1.0 / rank) if rank else 0.0
    t = o.get("gold_tier", "?")
    st = strat.setdefault(t, {1: 0, 3: 0, 5: 0, 10: 0, "n": 0})
    st["n"] += 1
    if rank:
        for k in st:
            if k != "n":
                st[k] += int(rank <= k)
    rowsout.append({"qid": o["qid"], "rank": rank})
    n += 1
    if n % 80 == 0:
        print("eval", n, dict(h), flush=True)
out = {"n": n, "hit": {k: round(v / n, 3) for k, v in h.items()}, "mrr": round(mrr / n, 4),
       "strat": {t: dict(s) for t, s in strat.items()},
       "per_q": rowsout, "secs": round(time.time() - t0, 1)}
json.dump(out, open(f"{R}/law_eval_dedupcollapse_corrected.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("V14", json.dumps(out["hit"]), "MRR", out["mrr"], flush=True)
for t, s in out["strat"].items():
    print("STRAT", t, "n", s["n"], "h1", round(s[1] / s["n"], 3), "h3", round(s[3] / s["n"], 3),
          "h5", round(s[5] / s["n"], 3), "h10", round(s[10] / s["n"], 3), flush=True)
print("FIN6 DONE", flush=True)
