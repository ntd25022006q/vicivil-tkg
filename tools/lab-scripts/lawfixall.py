"""Fix-all: wide-search (hybrid30+graph30) + 14b judge for 41 weak + 48 partial.
First CO wins -> new gold. Else logged unfixable with evidence for author triage.
Resume-safe via runs/fixall.json. Output: runs/lawfixall.log
"""
import json, sys, time, urllib.request

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
rt = LawRetriever()
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
qs = {}
for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    for o in json.load(open(f"{R}/{fn}", encoding="utf-8")):
        qs[o["qid"]] = o
todo = [o for o in qs.values() if o.get("gold_tier") in ("weak", "partial")]
print("fix candidates:", len(todo), flush=True)
try:
    out = json.load(open(f"{R}/fixall.json", encoding="utf-8"))
except Exception:
    out = {}
todo = [o for o in todo if o["qid"] not in out]
print("todo:", len(todo), flush=True)
SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi TRON VEN cau hoi khong "
       "(khong thieu y, khong suy dien xa)? Chi tra loi: CO / KHONG.")


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
                t = (json.load(r)["message"]["content"] or "").strip().upper().replace(" ", "")
            return "CO" if "CO" in t and "KHONG" not in t else "KHONG"
        except Exception:
            time.sleep(10)
    return "ERROR"


for o in todo:
    qid = o["qid"]
    old = (o.get("gold_ids") or ["?"])[0]
    pool = []
    for mode in ("hybrid", "graph"):
        try:
            pool += rt.retrieve(o["question"], o["as_of"], topk=30, rerank=False, mode=mode)
        except Exception as e:
            print(qid, "retr-err", str(e)[:60], flush=True)
    seen, cands = set(), []
    for c in pool:
        if c != old and c not in seen:
            seen.add(c)
            cands.append(c)
    found, tried = None, 0
    for cid in cands[:10]:
        tried += 1
        if judge(o["question"], chunks.get(cid, "")) == "CO":
            found = cid
            break
    out[qid] = {"old_gold": old, "new_gold": found, "tried": tried, "pool": len(cands)}
    json.dump(out, open(f"{R}/fixall.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{qid} [{o.get('gold_tier')}] tried={tried} -> {str(found)[-22:] if found else 'UNFIXABLE'}",
          flush=True)
print("FIXALL DONE", flush=True)
