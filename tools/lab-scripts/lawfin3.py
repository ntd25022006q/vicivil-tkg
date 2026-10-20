"""Final C: strip TVPL truncation stubs (CÔNG BÁO/Số N/Ng [...]) from 9 chunks,
re-embed them, re-extract them. Log: runs/lawfin3.log
"""
import base64, io, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
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
STUB = re.compile(r"CÔNG BÁO\s*/\s*Số\s*(?:\d+\s*/\s*Ng(?:ày)?[^ ,;.:()\n]{0,6})?\s*\[\.{3}\]\s*")
rows = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
patched = []
for r in rows:
    c = r.get("content") or ""
    c2 = STUB.sub("", c)
    if c2 != c:
        r["content"] = re.sub(r"\n{2,}", "\n", re.sub(r"[ \t]{2,}", " ", c2)).strip()
        r["chars"] = str(len(r["content"]))
        patched.append(r)
print("patched:", len(patched), sorted(r["chunk_id"] for r in patched), flush=True)
left = sum(1 for r in rows if re.search(r"CÔNG BÁO\s*/\s*Số", r.get("content") or ""))
print("residual Công BÁO pattern anywhere:", left, flush=True)
assert left == 0, "residual != 0, aborting without write"
with open(f"{R}/civil_chunks.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
kv = json.load(open(f"{D}/kv_store_text_chunks.json", encoding="utf-8"))
for r in patched:
    kv[r["chunk_id"]] = {"law_id": r["law_id"], "content": r["content"]}
json.dump(kv, open(f"{D}/kv_store_text_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)


def embed_batch(texts):
    body = {"model": "embeddinggemma:300m", "input": texts}
    for _ in range(3):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/embed",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return np.asarray(json.load(r)["embeddings"], dtype=np.float32)
        except Exception as e:
            print("embed retry", str(e)[:50], flush=True)
            time.sleep(15)
    raise RuntimeError("embed failed")


txt = {r["chunk_id"]: r["content"] for r in patched}
V = []
for i in range(0, len(txt), 8):
    v = embed_batch([txt[c] for c in list(txt)[i:i + 8]])
    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    V.append(v)
V = np.vstack(V)
vdb = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype=np.float32).reshape(-1, 768).copy()
posmap = {c["__id__"]: i for i, c in enumerate(vdb["data"])}
for j, cid in enumerate(txt):
    mat[posmap[cid]] = V[j]
json.dump(vdb, open(f"{D}/vdb_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("vdb re-embedded:", len(txt), flush=True)
ex = json.load(open(f"{R}/civil_extract.json", encoding="utf-8"))


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
                o = json.load(rp)["choices"][0]["message"]["content"] or ""
            ents = [L for L in o.split("\n") if L.startswith("entity<|#|>")
                    and len(L.split("<|#|>")) == 4 and len(L.split("<|#|>")[1].split()) >= 2
                    and L.split("<|#|>")[2].strip() in set(TYPES)]
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


with ThreadPoolExecutor(max_workers=4) as exn:
    for cid, val in exn.map(one, patched):
        ex[cid] = val
json.dump(ex, open(f"{R}/civil_extract.json", "w", encoding="utf-8"), ensure_ascii=False)
print("FIN3 DONE", len(ex), flush=True)
