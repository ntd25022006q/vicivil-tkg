"""End-to-end QA faithfulness sample (30 Qs): retrieve top-5 (hybrid) -> vLLM
answer with citations -> qwen3 judge (supported? CO/KHONG/MOTPHAN).
Honest small-scale extrinsic eval. Checkpointed.
Usage: law_qafaith.py
"""
import json, random, sys, time, urllib.request

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
OUT = f"{R}/qa_faith.json"
GEN_SYS = ("Tra loi cau hoi CHI DUA TREN cac doan luat duoc cho. Moi y tra loi "
           "ghi ro nguon (Dieu/Khoan). Khong co thong tin thi noi KHONG TIM THAY.")


def vllm(messages, tok=300):
    body = {"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": tok}
    for _ in range(2):
        try:
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)["choices"][0]["message"]["content"] or ""
        except Exception:
            time.sleep(10)
    return ""


def judge(question, ctx, ans):
    body = {"model": "qwen3:8b", "stream": False,
            "messages": [{"role": "system", "content": (
                "Cho CAU HOI, NGUON (doan luat) va TRA LOI. Mọi ý trong TRA LOI "
                "có được NGUON suy ra không? Chi tra loi: CO / KHONG / MOTPHAN.")},
             {"role": "user", "content": f"CAU HOI: {question}\nNGUON:\n{ctx[:2500]}\nTRA LOI:\n{ans[:1500]}"}]}
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
            return "UNCLEAR"
        except Exception:
            time.sleep(5)
    return "ERROR"


rt = LawRetriever()
bench = json.load(open(f"{R}/law_bench_200c.json", encoding="utf-8"))
hand = json.load(open(f"{R}/law_bench_v1.json", encoding="utf-8"))
random.seed(5)
samp = hand[:12] + random.sample(bench, 18)
try:
    out = json.load(open(OUT, encoding="utf-8"))
except Exception:
    out = {}
print(f"sample={len(samp)} todo={sum(1 for o in samp if o['qid'] not in out)}", flush=True)
for o in samp:
    if o["qid"] in out:
        continue
    ids = rt.retrieve(o["question"], o["as_of"], topk=5)
    byid = {}
    for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
        r = json.loads(L)
        byid[r["chunk_id"]] = r["content"]
    ctx = "\n---\n".join(f"[{i}] {byid.get(i, '')[:800]}" for i in ids if i in byid)
    ans = vllm([{"role": "system", "content": GEN_SYS},
                {"role": "user", "content": f"Cau hoi: {o['question']}\nDoan luat:\n{ctx[:3000]}"}])
    v = judge(o["question"], ctx, ans) if ans else "NO-ANS"
    out[o["qid"]] = {"answer": ans[:1000], "verdict": v, "n_ctx": len(ids)}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f'{o["qid"]} -> {v}', flush=True)
from collections import Counter
print(Counter(v["verdict"] for v in out.values()), flush=True)
