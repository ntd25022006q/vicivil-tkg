"""Benchmark top-up for NEW laws (low concurrency: 3 workers, eval-safe).
Target ~4 Qs/law for laws lacking questions. Strict prompt + CJK retry.
Appends to law_bench_main.json with reviewed=pending.
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
SYS = ("Viet 1 cau hoi ngan (1-2 dong) cua NGUOI DAN gap tinh huong phap ly, "
       "dua vao DOAN LUAT. BAT BUOC: 100% tieng Viet, CAM tuyet doi chu Trung Quoc "
       "va tieng Anh, dung cau doi thuong, khong chep cau luat. Chi in cau hoi.")
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
MID = {}
for L in G["laws"]:
    vf = L["valid_from"]
    vt = L["valid_to"] or "2026-06-01"
    MID[L["law_id"]] = vf[:4] + "-06-01" if vf[:4] < (vt[:4] if vt else "9999") else vt

HAVE_LAWS = set()
for L in open(CHUNKS, encoding="utf-8"):
    HAVE_LAWS.add(json.loads(L)["law_id"])
old = json.load(open(OUT, encoding="utf-8"))
have_q = {o["law_id"] for o in old}
need = [l for l in HAVE_LAWS if sum(1 for o in old if o.get("law_id") == l) < 3]
print("laws needing Qs:", need, flush=True)
rows = [json.loads(L) for L in open(CHUNKS, encoding="utf-8")]
todo = []
random.seed(11)
for law in need:
    pool = [r for r in rows if r["law_id"] == law and r["khoan"] and r["chars"] >= 120]
    random.shuffle(pool)
    todo += pool[:5]
print("todo:", len(todo), flush=True)


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
    for _ in range(4):
        try:
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as rp:
                d = json.load(rp)
            q = clean((d["choices"][0]["message"]["content"] or ""))
            if q:
                return {"qid": f"NEW{abs(hash(r['chunk_id'] + q)) % 90000 + 10000}",
                        "as_of": MID.get(r["law_id"], "2024-06-01"), "question": q,
                        "gold_ids": [r["chunk_id"]], "hint": "synthetic (weak gold)",
                        "law_id": r["law_id"], "reviewed": "pending"}
        except Exception:
            time.sleep(5)
    return None


for b in range(0, len(todo), 8):
    with ThreadPoolExecutor(max_workers=3) as ex:
        for o in ex.map(one, todo[b:b + 8]):
            if o:
                old.append(o)
    json.dump(old, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{b + 8}/{len(todo)}] n={len(old)}", flush=True)
print("TOPUP DONE n=", len(old), flush=True)
