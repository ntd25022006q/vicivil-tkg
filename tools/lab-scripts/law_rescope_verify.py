"""Batch rescope verify: judge all 67 new pairs with 14b, apply CO. Resume-safe."""
import io, json, sys, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
NEWQ = json.load(open("/tmp/rescope67.json", encoding="utf-8"))
print("drafts:", len(NEWQ), flush=True)
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
qs = {}
for fn in ["law_bench_main.json", "law_bench_seed.json"]:
    for o in json.load(open(f"{R}/{fn}", encoding="utf-8")):
        qs[o["qid"]] = (fn, o)
SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi TRON VEN cau hoi khong? "
       "Chi tra loi: CO / KHONG.")


def judge(q, c):
    body = {"model": "qwen3:14b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"CAU HOI: {q}\nDOAN LUAT:\n{c[:1200]}"}]}
    for _ in range(2):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                t = (json.load(r)["message"]["content"] or "").strip().upper().replace(" ", "")
            return "CO" if "CO" in t and "KHONG" not in t else "KHONG"
        except Exception:
            time.sleep(10)
    return "ERROR"


ok = fail = skip = 0
for qid, nq in NEWQ.items():
    if qid not in qs:
        print(qid, "NOTFOUND", flush=True)
        skip += 1
        continue
    fn, o = qs[qid]
    g = (o.get("gold_ids") or ["?"])[0]
    v = judge(nq, chunks.get(g, ""))
    print(qid, "->", v, flush=True)
    if v == "CO":
        o["question_rescoped_from"] = o["question"]
        o["question"] = nq
        o["gold_tier"] = "verified"
        ok += 1
    else:
        o["gold_tier"] = "author-review"
        fail += 1
for fn in ["law_bench_main.json", "law_bench_seed.json"]:
    arr = [o for f, o in qs.values() if f == fn]
    json.dump(arr, open(f"{R}/{fn}", "w", encoding="utf-8"), ensure_ascii=False)
print(f"RESCOPE67 DONE ok={ok} fail={fail} skip={skip}", flush=True)
