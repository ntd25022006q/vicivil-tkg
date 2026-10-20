"""Final B: wait INDEX OK -> append cross-law lineage edges (sim>=0.90, Muc-remap)
-> clean full eval (Hit@1/3/5/10 + MRR + stratified) -> runs/law_eval_v12.json.
Log: runs/lawfin2.log
"""
import base64, hashlib, io, json, os, sys, time, urllib.request
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
for _ in range(200):
    ok = False
    try:
        ok = "INDEX OK" in open(f"{R}/lawkbuild.log", encoding="utf-8").read()[-4000:]
    except Exception:
        pass
    if ok:
        break
    time.sleep(20)
print("kgbuild OK", open(f"{R}/law_index_stats.json").read(), flush=True)

chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
ids = {c["chunk_id"] for c in chunks}
dieu_children = {}
for c in chunks:
    if c["law_id"] == "BLDS1995":
        n = c["dieu"]
        dieu_children.setdefault(n, []).append(c["chunk_id"])


def remap95(cid):
    if cid in ids:
        return [cid]
    if cid.startswith("BLDS1995|Dieu"):
        n = cid.split("|Dieu")[1]
        ch = dieu_children.get(n, [])
        if ch:
            pref = [x for x in ch if x.endswith("|Muc0")]
            return pref[:1] or ch[:1]
    return []


lin = json.load(open(f"{R}/lineage_candidates.json", encoding="utf-8"))
pairs = []
for band in lin.values():
    for e in band:
        if e["sim"] < 0.90:
            continue
        for a in remap95(e["from"]):
            if e["to"] in ids and a != e["to"]:
                pairs.append((a, e["to"], round(e["sim"], 3)))
seen, EP = set(), []
for a, b, s in pairs:
    if (a, b) not in seen:
        seen.add((a, b))
        EP.append((a, b, s))
print("lineage edges:", len(EP), flush=True)


def embed_batch(texts):
    body = {"model": "embeddinggemma:300m", "input": texts}
    for _ in range(3):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/embed",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return np.asarray(json.load(r)["embeddings"], dtype=np.float32)
        except Exception as e:
            print("embed retry", str(e)[:50], flush=True)
            time.sleep(15)
    raise RuntimeError("embed failed")


rel = json.load(open(f"{D}/vdb_relationships.json", encoding="utf-8"))
mat = np.frombuffer(base64.b64decode(rel["matrix"]), dtype=np.float32).reshape(-1, 768)
have = {r["__id__"] for r in rel["data"]}
kv_e = json.load(open(f"{D}/kv_store_entity_chunks.json", encoding="utf-8"))
new_data, new_txt = [], []
for a, b, s in EP:
    eid = "rel-x" + hashlib.md5((a + b).encode()).hexdigest()
    if eid in have:
        continue
    body = f"phiên bản khác\t{a}\n{b}\nĐiều tương ứng giữa các phiên bản luật (sim {s})"
    new_data.append({"__id__": eid, "src_id": a, "tgt_id": b, "content": body,
                     "source_id": a, "law_id": "CROSS"})
    new_txt.append(body)
    kv_e[eid] = {"chunk_ids": [a, b]}
print("new edges to embed:", len(new_data), flush=True)
if new_data:
    V = []
    for i in range(0, len(new_txt), 16):
        v = embed_batch(new_txt[i:i + 16])
        v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        V.append(v)
    V = np.vstack(V)
    m2 = np.vstack([mat, V])
    rel["data"] = rel["data"] + new_data
    rel["matrix"] = base64.b64encode(np.ascontiguousarray(m2, dtype=np.float32).tobytes()).decode()
    json.dump(rel, open(f"{D}/vdb_relationships.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(kv_e, open(f"{D}/kv_store_entity_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("rel rows now:", len(rel["data"]), flush=True)

sys.path.insert(0, f"{W}/src")
from law_adgr import LawRetriever
rt = LawRetriever()
qs = []
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    qs += json.load(open(f"{R}/{fn}", encoding="utf-8"))
h = {1: 0, 3: 0, 5: 0, 10: 0}
mrr, n = 0.0, 0
strat = {}
rowsout = []
for o in qs:
    q = o["question"]
    try:
        res = rt.retrieve(q, as_of=o.get("as_of"), topk=10, rerank=True, mode="hybrid")
    except Exception as e:
        print("ERR", o["qid"], str(e)[:60], flush=True)
        res = []
    got = [r if isinstance(r, str) else (r.get("chunk_id") or r.get("__id__") or "")
           for r in res[:10]]
    gold = o["gold_ids"]
    rank = next((i + 1 for i, g in enumerate(got) if g in gold), None)
    for k in h:
        h[k] += int(rank is not None and rank <= k)
    mrr += (1.0 / rank) if rank else 0.0
    t = o.get("gold_tier", "?")
    s = strat.setdefault(t, {1: 0, 3: 0, 5: 0, 10: 0, "n": 0})
    s["n"] += 1
    if rank:
        for k in s:
            if k != "n":
                s[k] += int(rank <= k)
    n += 1
    rowsout.append({"qid": o["qid"], "rank": rank, "top": got[:5]})
    if n % 60 == 0:
        print("eval", n, dict(h), flush=True)
out = {"n": n, "hit": {k: round(v / n, 3) for k, v in h.items()},
       "mrr": round(mrr / n, 4),
       "strat": {t: {"n": s["n"], "hit": {k: (round(v / s["n"], 3) if k != "n" else s["n"]) for k, v in s.items()}} for t, s in strat.items()},
       "per_q": rowsout}
json.dump(out, open(f"{R}/law_eval_v12.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("V12 EVAL", json.dumps(out["hit"]), "MRR", out["mrr"], flush=True)
for t, s in out["strat"].items():
    print(t, s["n"], json.dumps(s["hit"]), "n-only", s["hit"].get("n"), flush=True)
print("FIN2 EVAL DONE", flush=True)
