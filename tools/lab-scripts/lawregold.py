"""Re-gold rejected questions: hybrid top-10 candidates verified by 14b judge.
First CO verdict wins. Questions stay, labels get corrected (disclosed).
Output: runs/regold.json {qid: {new_gold, old_gold}}
"""
import json, sys, time, urllib.request

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
r14 = json.load(open(f"{R}/second_rater14.json", encoding="utf-8"))
qs = {}
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    for o in json.load(open(f"{R}/{fn}", encoding="utf-8")):
        qs[o["qid"]] = o
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
rej = [q for q, v in r14.items() if v == "KHONG" and q in qs]
print("rejoudge candidates:", len(rej), flush=True)
try:
    out = json.load(open(f"{R}/regold.json", encoding="utf-8"))
except Exception:
    out = {}
todo = [q for q in rej if q not in out]
print("todo:", len(todo), flush=True)
SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi TRUC TIEP cau hoi khong? "
       "Chi tra loi: CO / KHONG.")


def judge(question, content):
    body = {"model": "qwen3:14b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"CAU HOI: {question}\nDOAN LUAT:\n{content[:1200]}"}]}
    for _ in range(2):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                t = (json.load(r)["message"]["content"] or "").strip().upper()
            return "CO" if "CO" in t.replace(" ", "") and "KHONG" not in t.replace(" ", "") else "KHONG"
        except Exception:
            time.sleep(10)
    return "ERROR"


for qid in todo:
    o = qs[qid]
    ids = rt.retrieve(o["question"], o["as_of"], topk=10, rerank=False, mode="hybrid")
    found = None
    for cid in ids[:6]:
        if cid == (o.get("gold_ids") or ["?"])[0]:
            continue
        if judge(o["question"], chunks.get(cid, "")) == "CO":
            found = cid
            break
    out[qid] = {"old_gold": (o.get("gold_ids") or ["?"])[0], "new_gold": found}
    json.dump(out, open(f"{R}/regold.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{qid}: {out[qid]['old_gold'][-18:]} -> {str(found)[-18:]}", flush=True)
print("REGOLD DONE", flush=True)
