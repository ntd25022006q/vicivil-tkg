"""Final D: 1) sync vdb/kv content to [:3000] policy; 2) retry 9 failed3x serially;
3) retrieval-time near-dup collapse + full re-eval; save law_eval_v13.json.
"""
import base64, io, json, re, sys, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
CM = {c["chunk_id"]: c for c in chunks}
vdb = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
kvt = json.load(open(f"{D}/kv_store_text_chunks.json", encoding="utf-8"))
n = 0
for c in vdb["data"]:
    want = CM[c["__id__"]]["content"][:3000]
    if c["content"] != want:
        c["content"] = want
        n += 1
json.dump(vdb, open(f"{D}/vdb_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
k = 0
for cid in kvt:
    want = CM[cid]["content"][:3000]
    if kvt[cid].get("content") != want:
        kvt[cid]["content"] = want
        k += 1
json.dump(kvt, open(f"{D}/kv_store_text_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("synced vdb:", n, "kv:", k, flush=True)
mm = sum(1 for c in vdb["data"] if c["content"] != CM[c["__id__"]]["content"][:3000])
print("post-sync vdb mismatches ([:3000] policy):", mm, flush=True)

VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
TYPES = ["Quyen", "NghiaVu", "CheTai", "DieuKien", "CoQuan", "DoiTuong",
         "ThoiHan", "CheDinh", "HanhVi", "TaiSan"]
SYS = """Ban trich xuat thuc the phap ly. Tuan thu DINH DANG tuyet doi.
LOAI duoc phep: Quyen, NghiaVu, CheTai, DieuKien, CoQuan, DoiTuong, ThoiHan, CheDinh, HanhVi, TaiSan.
Dong entity (dung 4 truong, cach nhau boi <|#|>):
entity<|#|>TEN CU THE<|#|>LOAI<|#|>MO TA 1 CAU
Dong relation (dung 5 truong; NGUON va DICH phai la TEN da liet ke, KHONG duoc la LOAI):
relation<|#|>TEN NGUON<|#|>TEN DICH<|#|>TU KHOA NGAN<|#|>MO TA 1 CAU
QUY TAC: TEN phai cu the (>=2 tu, khong chung chung nhu "quyền", "pháp luật"). Khong co gi cu the thi chi in: NONE"""
REF_RE = re.compile(r"điểm\s+([a-zđ])\s+khoản\s+(\d+)\s+Điều\s+(\d+)|"
                    r"khoản\s+(\d+)\s+Điều\s+(\d+)|Điều\s+(\d+)", re.IGNORECASE)
ex = json.load(open(f"{R}/civil_extract.json", encoding="utf-8"))
todo = [CM[k] for k in CM if ex.get(k, {}).get("error")]
print("retry-failed3x:", len(todo), flush=True)
if todo:
    r = todo[0] if len(todo) == 1 else todo
    for r in todo:
        body = {"model": MODEL,
                "messages": [{"role": "system", "content": SYS},
                             {"role": "user", "content": "DOAN CAN TRICH:\n" + r["content"][:2800]}],
                "temperature": 0, "max_tokens": 1500}
        got = None
        for _ in range(2):
            try:
                req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=600) as rp:
                    o = json.load(rp)["choices"][0]["message"]["content"] or ""
                ents = [L for L in o.split("\n") if L.startswith("entity<|#|>")
                        and len(L.split("<|#|>")) == 4 and len(L.split("<|#|>")[1].split()) >= 2
                        and L.split("<|#|>")[2].strip() in set(TYPES)]
                names = [e.split("<|#|>")[1] for e in ents]
                nl = [x.lower() for x in names]
                rels = [L for L in o.split("\n") if L.startswith("relation<|#|>")
                        and len(L.split("<|#|>")) == 5
                        and L.split("<|#|>")[2].strip().lower() not in [x.lower() for x in TYPES]
                        and any(L.split("<|#|>")[1].strip().lower() in nn or nn in L.split("<|#|>")[1].strip().lower() for nn in nl)
                        and any(L.split("<|#|>")[2].strip().lower() in nn or nn in L.split("<|#|>")[2].strip().lower() for nn in nl)]
                refs, seen = [], set()
                for m in REF_RE.finditer(r["content"]):
                    x = (f"{r['law_id']}|Dieu{m.group(3)}|Khoan{m.group(2)}|Diem{m.group(1)}" if m.group(3)
                         else f"{r['law_id']}|Dieu{m.group(5)}|Khoan{m.group(4)}" if m.group(5)
                         else f"{r['law_id']}|Dieu{m.group(6)}")
                    if x not in seen:
                        seen.add(x)
                        refs.append(x)
                got = {"ents": ents, "rels": rels, "refs": refs, "done": True}
                break
            except Exception as e:
                print("  retry fail", r["chunk_id"], str(e)[:40], flush=True)
                time.sleep(6)
        if got is None:
            got = {"error": "failed3x", "refs": [], "ents": [], "rels": [], "done": True}
        ex[r["chunk_id"]] = got
        print("  ", r["chunk_id"], "ents", len(got.get("ents", [])), "errs", got.get("error", "-"), flush=True)
    json.dump(ex, open(f"{R}/civil_extract.json", "w", encoding="utf-8"), ensure_ascii=False)
print("extract failed3x now:", sum(1 for v in ex.values() if v.get("error")), flush=True)

G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
VF = {L["law_id"]: [L.get("valid_from"), L.get("valid_to", "2999-12-31")] for L in G["laws"]}
sig_mp = {}


def norm(s):
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"^(Điều \d+[\.:]?|[\d\.]+-|[\wđ]+\) )", "", s[:400])
    return s


sig = {}
for c in CM.values():
    h = norm(c["content"][:400])
    sig.setdefault(h, []).append(c["chunk_id"])


def canon(ids):
    def kf(x):
        law = CM[x]["law_id"]
        vf = VF.get(law, [None]
                    if False else [None])
        return (vf[0] or "0000", law)
    return sorted(ids, key=kf)[0]


canon_of = {}
for h, v in sig.items():
    if len(v) > 1:
        for x in v[1:]:
            canon_of[x] = canon(v)

sys.path.insert(0, f"{W}/src")
from law_adgr import LawRetriever
rt = LawRetriever()
_orig = rt.retrieve


def retrieve_dedup(q, as_of=None, topk=10, rerank=True, mode="hybrid"):
    res = _orig(q, as_of=as_of, topk=topk * 3, rerank=rerank, mode=mode)
    out = []
    for r in res:
        cid = r if isinstance(r, str) else (r.get("chunk_id") or r.get("__id__") or "")
        rep = canon_of.get(cid, cid)
        if rep not in out:
            out.append(rep)
        if len(out) >= topk:
            break
    return out


rt.retrieve = retrieve_dedup
qs = []
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    qs += json.load(open(f"{R}/{fn}", encoding="utf-8"))
print("as_of present:", sum(1 for o in qs if o.get("as_of")), "of", len(qs), flush=True)
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
out = {"n": n, "hit": {k: round(v / n, 3) for k, v in h.items()}, "mrr": round(mrr / n, 4),
       "strat": {t: {kk: (round(v / s["n"], 3) if kk != "n" else s["n"]) for kk, v in s.items()}
                 for t, s in strat.items()},
       "per_q": rowsout, "dedup_groups": int(sum(1 for v in sig.values() if len(v) > 1)),
       "secs": round(time.time() - t0, 1)}
json.dump(out, open(f"{R}/law_eval_v13_dedup.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("V13-DEDUP", json.dumps(out["hit"]), "MRR", out["mrr"], flush=True)
for t, s in out["strat"].items():
    print(t, s["n"], json.dumps(s["hit"]), "n-only", s["hit"].get("n"), flush=True)
print("FIN5 DONE", flush=True)
