"""Second-rater agreement: independent model (qwen3:8b via ollama) judges whether
each gold chunk answers its question. Verdicts: CO / KHONG / MOTPHAN.
Output: runs/second_rater.json + agreement stats. Disclosed as model-model agreement.
"""
import json, time, urllib.request

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
OUT = f"{R}/second_rater.json"
SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi CAU HOI khong? "
       "Chi tra loi dung 1 tu: CO / KHONG / MOTPHAN.")
items = []
for fn in ["law_bench_main.json", "law_bench_seed.json"]:
    try:
        items += json.load(open(f"{R}/{fn}", encoding="utf-8"))
    except Exception:
        pass
seen, Q = set(), []
for o in items:
    if o["qid"] not in seen:
        seen.add(o["qid"])
        Q.append(o)
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
try:
    out = json.load(open(OUT, encoding="utf-8"))
except Exception:
    out = {}
todo = [o for o in Q if o["qid"] not in out]
print(f"total={len(Q)} todo={len(todo)}", flush=True)


def judge(o):
    c = chunks.get((o.get("gold_ids") or ["?"])[0], "")
    body = {"model": "qwen3:8b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"CAU HOI: {o['question']}\nDOAN LUAT:\n{c[:1200]}"}]}
    for _ in range(2):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                t = (json.load(r)["message"]["content"] or "").strip().upper()
            for v in ["MOTPHAN", "KHONG", "CO"]:
                if v in t.replace(" ", ""):
                    return v
            return "UNCLEAR:" + t[:60]
        except Exception:
            time.sleep(5)
    return "ERROR"


for o in todo:
    out[o["qid"]] = judge(o)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    if len(out) % 20 == 0:
        print(f"[{len(out)}/{len(Q)}]", flush=True)
from collections import Counter
print(Counter(out.values()), flush=True)
