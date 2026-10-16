"""Benchmark expansion to 200: LLM writes 1 situational question per sampled chunk.
Gold = source chunk (weak supervision, disclosed). as_of = mid-validity of the law.
Stratified: all 3 laws, Khoan-level preferred, chars>=120. Checkpointed.
Usage: law_bench_gen.py [--n 200]
"""
import json, os, random, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
OUT = f"{R}/law_bench_200.json"
CHUNKS = f"{R}/civil_chunks.jsonl"
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 200

MID = {"BLDS2015": "2024-06-01", "BLDS2005": "2010-06-01", "HNGD2014": "2024-06-01"}
SYS = ("Ban la nguoi dan gap tinh huong phap ly. Doc DOAN LUAT sau, viet 1 cau hoi "
       "ngan gon (1-2 dong) cua nguoi dan ve dung tinh huong do, KHONG chep lai cau chu luat. "
       "Chi in cau hoi, khong giai thich.")

rows = [json.loads(L) for L in open(CHUNKS, encoding="utf-8")]
pool = [r for r in rows if r["khoan"] and r["chars"] >= 120]
random.seed(42)
by_law = {}
for r in pool:
    by_law.setdefault(r["law_id"], []).append(r)
per = max(1, N // max(1, len(by_law)))
samp = []
for law, lst in by_law.items():
    random.shuffle(lst)
    samp += lst[:per]
samp = samp[:N]
print("sampled:", len(samp), {k: sum(1 for s in samp if s["law_id"] == k) for k in by_law}, flush=True)
try:
    out = json.load(open(OUT, encoding="utf-8"))
except Exception:
    out = []
have = {o["gold_ids"][0] for o in out}
todo = [r for r in samp if r["chunk_id"] not in have]
print("todo:", len(todo), flush=True)


def one(r):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": "DOAN LUAT:\n" + r["content"][:1500]}],
            "temperature": 0.7, "max_tokens": 120}
    for _ in range(3):
        try:
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as rp:
                d = json.load(rp)
            q = (d["choices"][0]["message"]["content"] or "").strip().split("\n")[0][:300]
            if len(q) >= 15:
                return {"qid": f"GEN{abs(hash(r['chunk_id'])) % 90000 + 10000}",
                        "as_of": MID[r["law_id"]], "question": q,
                        "gold_ids": [r["chunk_id"]], "hint": "synthetic situational (weak gold)",
                        "law_id": r["law_id"]}
        except Exception:
            time.sleep(5)
    return None


for b in range(0, len(todo), 16):
    with ThreadPoolExecutor(max_workers=8) as ex:
        for o in ex.map(one, todo[b:b + 16]):
            if o:
                out.append(o)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{b + 16}/{len(todo)}] n={len(out)}", flush=True)
print("BENCH200 DONE n=", len(out), flush=True)
