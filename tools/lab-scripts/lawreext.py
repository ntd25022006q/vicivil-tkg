"""Targeted re-extract: prune stale keys (cleaned + old-1995) then extract todo only.
Writes checkpoints every 100. Log: runs/lawreext.log
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") \
    if False else sys.stdout
import io as _io
sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
OUT = f"{R}/civil_extract.json"
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
TYPESET = set(TYPES)
rows = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
byid = {r["chunk_id"]: r for r in rows}
out = json.load(open(OUT, encoding="utf-8"))
print("extract keys before:", len(out), flush=True)
pruned = 0
for cid in list(out):
    r = byid.get(cid)
    if r is None or r.get("cleaned_v11") or r.get("source_type") == "official":
        out.pop(cid, None)
        pruned += 1
print("pruned stale keys:", pruned, flush=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)


def refs_of(content, law):
    res, seen = [], set()
    for m in REF_RE.finditer(content or ""):
        x = (f"{law}|Dieu{m.group(3)}|Khoan{m.group(2)}|Diem{m.group(1)}" if m.group(3)
             else f"{law}|Dieu{m.group(5)}|Khoan{m.group(4)}" if m.group(5)
             else f"{law}|Dieu{m.group(6)}")
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def one(r):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": "DOAN CAN TRICH:\n" + r["content"][:2800]}],
            "temperature": 0, "max_tokens": 1500}
    for _ in range(3):
        try:
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as rp:
                d = json.load(rp)
            o = d["choices"][0]["message"]["content"] or ""
            ents = [L for L in o.split("\n") if L.startswith("entity<|#|>")
                    and len(L.split("<|#|>")) == 4 and len(L.split("<|#|>")[1].split()) >= 2
                    and L.split("<|#|>")[2].strip() in TYPESET]
            names = [e.split("<|#|>")[1] for e in ents]
            nl = [n.lower() for n in names]
            rels = [L for L in o.split("\n") if L.startswith("relation<|#|>")
                    and len(L.split("<|#|>")) == 5
                    and L.split("<|#|>")[2].strip().lower() not in [x.lower() for x in TYPES]
                    and any(L.split("<|#|>")[1].strip().lower() in n or n in L.split("<|#|>")[1].strip().lower() for n in nl)
                    and any(L.split("<|#|>")[2].strip().lower() in n or n in L.split("<|#|>")[2].strip().lower() for n in nl)]
            return r["chunk_id"], {"ents": ents, "rels": rels,
                                   "refs": refs_of(r["content"], r["law_id"]), "done": True}
        except Exception:
            time.sleep(8)
    return r["chunk_id"], {"error": "failed3x", "refs": refs_of(r["content"], r["law_id"]), "done": True}


todo = [byid[c] for c in byid if c not in out or not out[c].get("done")]
print("todo:", len(todo), flush=True)
done_n = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for cid, val in ex.map(one, todo):
        out[cid] = val
        done_n += 1
        if done_n % 100 == 0:
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"extracted {done_n}/{len(todo)}", flush=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("REEXTRACT DONE", len(out), flush=True)
