"""Benchmark refill to 200 clean: strict Vietnamese-only prompt + CJK retry loop.
Keeps existing 90 clean, generates ~120 new from unused chunks. Weak golds, disclosed.
"""
import json, os, random, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
OUT = f"{R}/law_bench_main.json"
CHUNKS = f"{R}/civil_chunks.jsonl"
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
META = ["đoạn văn", "đoạn luật", "câu hỏi trên", "văn bản trên", "tình huống trên"]
MID = {"BLDS2015": "2024-06-01", "BLDS2005": "2010-06-01", "HNGD2014": "2024-06-01"}
SYS = ("Viet 1 cau hoi ngan (1-2 dong) cua NGUOI DAN gap tinh huong phap ly, "
       "dua vao DOAN LUAT. BAT BUOC: 100% tieng Viet, CAM tuyet doi chu Trung Quoc "
       "va tieng Anh, dung cau doi thuong, khong chep cau luat. Chi in cau hoi.")

out = json.load(open(OUT, encoding="utf-8"))
have = {o["gold_ids"][0] for o in out}
rows = [json.loads(L) for L in open(CHUNKS, encoding="utf-8")]
pool = [r for r in rows if r["khoan"] and r["chars"] >= 120 and r["chunk_id"] not in have]
random.seed(7)
random.shuffle(pool)
todo = pool[:130]
print("kept:", len(out), "todo:", len(todo), flush=True)


def clean(q):
    q = q.strip().split("\n")[0][:250]
    if CJK.search(q) or len(q) < 15 or any(m in q.lower() for m in META):
        return None
    return q


def one(r):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": "DOAN LUAT:\n" + r["content"][:1500]}],
            "temperature": 0.3, "max_tokens": 100}
    for _ in range(5):
        try:
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as rp:
                d = json.load(rp)
            q = clean((d["choices"][0]["message"]["content"] or ""))
            if q:
                return {"qid": f"GEN{abs(hash(r['chunk_id'] + q)) % 90000 + 10000}",
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
print("BENCH CLEAN DONE n=", len(out), flush=True)
