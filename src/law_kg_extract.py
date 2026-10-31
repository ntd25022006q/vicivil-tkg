"""Civil KG extraction pilot: few-shot prompt, strict formats, grounded relations.
Usage: python -u law_kg_extract.py [--pilot | --full]  (deletes old pilot output on --pilot)
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"
OUT = f"{R}/civil_extract.json"
CHUNKS = f"{R}/civil_chunks.jsonl"

TYPES = ["Quyen", "NghiaVu", "CheTai", "DieuKien", "CoQuan", "DoiTuong",
         "ThoiHan", "CheDinh", "HanhVi", "TaiSan"]
SYS = """Ban trich xuat thuc the phap ly. Tuan thu DINH DANG tuyet doi.
LOAI duoc phep: Quyen, NghiaVu, CheTai, DieuKien, CoQuan, DoiTuong, ThoiHan, CheDinh, HanhVi, TaiSan.
Dong entity (dung 4 truong, cach nhau boi <|#|>):
entity<|#|>TEN CU THE<|#|>LOAI<|#|>MO TA 1 CAU
Dong relation (dung 5 truong; NGUON va DICH phai la TEN da liet ke, KHONG duoc la LOAI):
relation<|#|>TEN NGUON<|#|>TEN DICH<|#|>TU KHOA NGAN<|#|>MO TA 1 CAU
VI DU:
entity<|#|>quyền thay đổi họ<|#|>Quyen<|#|>cá nhân được yêu cầu thay đổi họ trong các trường hợp luật định
entity<|#|>UBND cấp xã<|#|>CoQuan<|#|>cơ quan đăng ký hộ tịch thay đổi họ
relation<|#|>cá nhân<|#|>quyền thay đổi họ<|#|>thay đổi họ, hộ tịch<|#|>cá nhân thực hiện quyền thay đổi họ qua UBND cấp xã
QUY TAC: TEN phai cu the (>=2 tu, khong chung chung nhu "quyền", "pháp luật"). Khong co gi cu the thi chi in: NONE"""
REF_RE = re.compile(r"điểm\s+([a-zđ])\s+khoản\s+(\d+)\s+Điều\s+(\d+)|"
                    r"khoản\s+(\d+)\s+Điều\s+(\d+)|Điều\s+(\d+)",
                    re.IGNORECASE)
TYPESET = set(TYPES)


def refs_of(content, law):
    out = []
    for m in REF_RE.finditer(content):
        if m.group(3):
            out.append(f"{law}|Dieu{m.group(3)}|Khoan{m.group(2)}|Diem{m.group(1)}")
        elif m.group(5):
            out.append(f"{law}|Dieu{m.group(5)}|Khoan{m.group(4)}")
        elif m.group(6):
            out.append(f"{law}|Dieu{m.group(6)}")
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def valid_ent(line):
    p = line.split("<|#|>")
    return len(p) == 4 and len(p[1].split()) >= 2 and p[2].strip() in TYPESET


def valid_rel(line, names):
    p = line.split("<|#|>")
    if len(p) != 5:
        return False
    s, t = p[1].strip().lower(), p[2].strip().lower()
    if t in [x.lower() for x in TYPESET]:
        return False
    nl = [n.lower() for n in names]
    return any(s in n or n in s for n in nl) and any(t in n or n in t for n in nl)


rows = [json.loads(L) for L in open(CHUNKS, encoding="utf-8")]
if "--full" not in sys.argv:
    rows = rows[:30]
    if os.path.exists(OUT):
        os.remove(OUT)
    out = {}
    print("resume: 0 (fresh pilot)", flush=True)
else:
    try:
        out = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        out = {}
    print("resume:", len(out), flush=True)


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
            ents = [L for L in o.split("\n") if L.startswith("entity<|#|>") and valid_ent(L)]
            names = [e.split("<|#|>")[1] for e in ents]
            rels = [L for L in o.split("\n") if L.startswith("relation<|#|>") and valid_rel(L, names)]
            return r["chunk_id"], {
                "ents": ents, "rels": rels,
                "refs": refs_of(r["content"], r["law_id"]), "done": True}
        except Exception:
            time.sleep(8)
    return r["chunk_id"], {"error": "failed3x", "refs": refs_of(r["content"], r["law_id"]), "done": True}


todo = [r for r in rows if r["chunk_id"] not in out or not out[r["chunk_id"]].get("done")]
print("todo:", len(todo), flush=True)
import signal


def _wd(signum, frame):
    print("WATCHDOG: batch stuck >10min, vLLM likely hung. EXIT LOUD.", flush=True)
    raise SystemExit(42)


t0 = time.time()
for b in range(0, len(todo), 16):
    signal.alarm(0)
    try:
        signal.signal(signal.SIGALRM, _wd)
        signal.alarm(600)
        with ThreadPoolExecutor(max_workers=8) as ex:
            for cid, row in ex.map(one, todo[b:b + 16]):
                out[cid] = row
    finally:
        signal.alarm(0)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[{b + 16}/{len(todo)}] {(time.time() - t0) / 60:.1f}min", flush=True)
ne = sum(len(v.get("ents", [])) for v in out.values() if isinstance(v, dict))
nr = sum(len(v.get("rels", [])) for v in out.values() if isinstance(v, dict))
nrf = sum(len(v.get("refs", [])) for v in out.values() if isinstance(v, dict))
n0 = sum(1 for v in out.values() if isinstance(v, dict) and not v.get("ents"))
print(f"DONE rows={len(out)} ents={ne} rels={nr} refs={nrf} empty={n0}", flush=True)
