"""Final A: dedup junk fragments, strip CONG BAO page headers, re-embed + re-extract affected.
Log: runs/lawfin1.log
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
CB_RE = re.compile(r"CÔNG BÁO\s*/\s*Số\s*\d+\s*/\s*Ngày\s*[\d-]+\s*\d*\s*")
chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
BY = {}
seen = {}
junk = set()
for r in chunks:
    cid = r["chunk_id"]
    if cid in seen:
        old = seen[cid]
        up = lambda x: max("".join((x["content"].split("\n"))[1:]).split())
        both = [old, r]
        real = max(both, key=lambda x: len(re.sub(r"[^a-zà-ỹđ]", "", " ".join(x["content"].split("\n")[1:]), flags=re.I)))
        junk.add((min(both, key=lambda x: len(x["content"])))["chunk_id"])
        BY[cid] = real
    else:
        seen[cid] = r
        BY[cid] = r
print("junk dup rows:", sorted(junk), flush=True)
rows = [r for r in chunks if (r["chunk_id"] not in junk) and (r is BY.get(r["chunk_id"])) ]
rows = list({r["chunk_id"]: r for r in rows}.values())
print("chunks after dedup:", len(rows), flush=True)
patched = []
for r in rows:
    c = r.get("content") or ""
    c2 = CB_RE.sub("", c)
    if c2 != c:
        r["content"] = re.sub(r"\n{2,}", "\n", c2).strip()
        r["chars"] = str(len(r["content"]))
        patched.append(r)
print("congbao patched:", len(patched), flush=True)
with open(f"{R}/civil_chunks.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
shutil_ok = True
kv = json.load(open(f"{D}/kv_store_text_chunks.json", encoding="utf-8"))
kv = {k: v for k, v in kv.items() if k not in junk and k in {r["chunk_id"] for r in rows}}
for r in patched:
    kv[r["chunk_id"]] = {"law_id": r["law_id"], "content": r["content"]}
json.dump(kv, open(f"{D}/kv_store_text_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("kv size:", len(kv), flush=True)


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


vdb = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype=np.float32).reshape(-1, 768).copy()
keep_idx, keep_data, bad = [], [], []
for i, c in enumerate(vdb["data"]):
    cid = c["__id__"]
    if cid in junk or cid not in {r["chunk_id"] for r in rows}:
        continue
    keep_idx.append(i)
    keep_data.append(c)
print("vdb keep:", len(keep_data), "of", len(vdb["data"]), flush=True)
ids_p = [r["chunk_id"] for r in patched]
missing = [r["chunk_id"] for r in rows if r["chunk_id"] not in {c["__id__"] for c in keep_data}]
print("missing ids to embed:", len(missing), flush=True)
vecs = []
B = 16
for s in range(0, len(ids_p) + len(missing), B):
    pass
todo_embed = ids_p + missing
todo_map = {r["chunk_id"]: r for r in patched}
for m in missing:
    todo_map[m] = next(r for r in rows if r["chunk_id"] == m)
Vn = []
for s in range(0, len(todo_embed), B):
    b = todo_embed[s:s + B]
    v = embed_batch([todo_map[x]["content"] for x in b])
    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    Vn.append(v)
    if (s // B) % 8 == 0:
        print(f"embed {s + len(b)}/{len(todo_embed)}", flush=True)
VN = np.vstack(Vn)
kept_new = [c for c in keep_data if c["__id__"] not in set(ids_p)]
mat2 = np.vstack([mat[keep_idx[:len(kept_new)]], VN]) if False else None
pos = {c["__id__"]: i for i, c in enumerate(keep_data)}
mat_new = np.vstack([mat[keep_idx], VN]) if len(keep_idx) == len(keep_data) else None
final_rows = [c for c in keep_data if c["__id__"] not in set(ids_p)] + [
    {"__id__": cid, "content": todo_map[cid]["content"], "url": "patched"} for cid in ids_p]
cols = [mat[i] for i, c in zip(keep_idx, keep_data) if c["__id__"] not in set(ids_p)]
matF = np.vstack(cols + [VN])
vdb["data"] = final_rows
vdb["matrix"] = base64.b64encode(np.ascontiguousarray(matF, dtype=np.float32).tobytes()).decode()
json.dump(vdb, open(f"{D}/vdb_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("vdb final rows:", matF.shape, flush=True)
ex = json.load(open(f"{R}/civil_extract.json", encoding="utf-8"))
for j in junk:
    ex.pop(j, None)
for cid in list(ex):
    if cid not in {r["chunk_id"] for r in rows}:
        ex.pop(cid, None)
json.dump(ex, open(f"{R}/civil_extract.json", "w", encoding="utf-8"), ensure_ascii=False)
print("extract keys:", len(ex), flush=True)


def refs_of(content, law):
    res, seenr = [], set()
    for m in REF_RE.finditer(content or ""):
        x = (f"{law}|Dieu{m.group(3)}|Khoan{m.group(2)}|Diem{m.group(1)}" if m.group(3)
             else f"{law}|Dieu{m.group(5)}|Khoan{m.group(4)}" if m.group(5)
             else f"{law}|Dieu{m.group(6)}")
        if x not in seenr:
            seenr.add(x)
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


todo_x = [r for r in patched]
print("re-extract todo:", len(todo_x), flush=True)
with ThreadPoolExecutor(max_workers=6) as ex2:
    for cid, val in ex2.map(one, todo_x):
        ex[cid] = val
json.dump(ex, open(f"{R}/civil_extract.json", "w", encoding="utf-8"), ensure_ascii=False)
print("FIN1 DONE", len(ex), flush=True)
