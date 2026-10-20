"""Re-judge doubtful golds (KHONG/MOTPHAN from 8b) with stronger qwen3:14b.
Improved prompt allows inference. Output: runs/second_rater14.json
"""
import json, time, urllib.request

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
OUT = f"{R}/second_rater14.json"
SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi TRUC TIEP hoac SUY RA "
       "duoc cau tra loi cho CAU HOI khong (duoc phep suy luan 1 buoc don gian)? "
       "Chi tra loi dung 1 tu: CO / KHONG / MOTPHAN.")
prev = json.load(open(f"{R}/second_rater.json", encoding="utf-8"))
qs = {}
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    for o in json.load(open(f"{R}/{fn}", encoding="utf-8")):
        qs[o["qid"]] = o
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
todo = [q for q, v in prev.items() if v in ("KHONG", "MOTPHAN")]
print("rejoudge n:", len(todo), flush=True)
try:
    out = json.load(open(OUT, encoding="utf-8"))
except Exception:
    out = {}
todo = [q for q in todo if q not in out]
print("todo:", len(todo), flush=True)


def judge(qid):
    o = qs[qid]
    c = chunks.get((o.get("gold_ids") or ["?"])[0], "")
    body = {"model": "qwen3:14b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"CAU HOI: {o['question']}\nDOAN LUAT:\n{c[:1200]}"}]}
    for _ in range(2):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                t = (json.load(r)["message"]["content"] or "").strip().upper()
            for v in ["MOTPHAN", "KHONG", "CO"]:
                if v in t.replace(" ", ""):
                    return v
            return "UNCLEAR"
        except Exception:
            time.sleep(10)
    return "ERROR"


for qid in todo:
    out[qid] = judge(qid)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    if len(out) % 15 == 0:
        print(f"[{len(out)}/{len(todo)}]", flush=True)
from collections import Counter
print(Counter(out.values()), flush=True)
