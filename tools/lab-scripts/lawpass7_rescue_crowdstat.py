"""Pass 7: rescue 9 failed3x via Ollama (qwen3:14b, same format/validators);
+ near-dup crowdstat on saved full-eval ranks; write runs/law_crowdstat.json.
"""
import io, json, re, sys, time, urllib.request
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
CM = {c["chunk_id"]: c for c in [json.loads(L) for L in
      open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]}
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
ex = json.load(open(f"{R}/civil_extract.json", encoding="utf-8"))
fails = [k for k, v in ex.items() if v.get("error")]
print("rescue targets:", len(fails), flush=True)
for cid in fails:
    r = CM[cid]
    body = {"model": "qwen3:14b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": "DOAN CAN TRICH:\n" + r["content"][:2800]}],
            "temperature": 0, "options": {"num_predict": 1200}}
    t0 = time.time()
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as rp:
            o = (json.load(rp)["message"]["content"] or "").strip()
        ents = [L for L in o.split("\n") if L.startswith("entity<|#|>")
                and len(L.split("<|#|>")) == 4 and len(L.split("<|#|>")[1].split()) >= 2
                and L.split("<|#|>")[2].strip() in set(TYPES)]
        names = [e.split("<|#|>")[1] for e in ents]
        nl = [x.lower() for x in names]
        rels = [L for L in o.split("\n") if L.startswith("relation<|#|>")
                and len(L.split("<|#|>")) == 5
                and L.split("<|#|>")[2].strip().lower() not in [x.lower() for x in TYPES]
                and any(L.split("<|#|>")[1].strip().lower() in nn or nn in L.split("<|#|>")[1].strip().lower() for nn in nl)
                and any(L.split("<|#|>")[2].strip().lower() in nn or nn in L.split("<|#|>")[2].strip().lower() for nn in nl)]
        refs, seen = [], set()
        for m in REF_RE.finditer(r["content"]):
            x = (f"{r['law_id']}|Dieu{m.group(3)}|Khoan{m.group(2)}|Diem{m.group(1)}" if m.group(3)
                 else f"{r['law_id']}|Dieu{m.group(5)}|Khoan{m.group(4)}" if m.group(5)
                 else f"{r['law_id']}|Dieu{m.group(6)}")
            if x not in seen:
                seen.add(x)
                refs.append(x)
        ex[cid] = {"ents": ents, "rels": rels, "refs": refs, "done": True,
                   "engine": "qwen3:14b-ollama"}
        print("  OK", cid[:44], "ents", len(ents), "rels", len(rels),
              round(time.time() - t0, 1), "s", flush=True)
    except Exception as e:
        print("  FAIL", cid[:44], str(e)[:50], flush=True)
json.dump(ex, open(f"{R}/civil_extract.json", "w", encoding="utf-8"), ensure_ascii=False)
print("rescued:", sum(1 for v in ex.values() if not v.get("error") and v.get("done")),
      "still-fail:", sum(1 for v in ex.values() if v.get("error")), flush=True)


def norm(s):
    s = re.sub(r"\s+", " ", s.strip())
    return re.sub(r"^(Điều \d+[\.:]?|[\d\.]+-|[\wđ]+\) )", "", s[:400])


sig = {}
for c in CM.values():
    sig.setdefault(norm(c["content"][:400]), []).append(c["chunk_id"])
gr = sum(1 for v in sig.values() if len(v) > 1)
ev = json.load(open(f"{R}/law_eval_ranks_full.json", encoding="utf-8"))
col = missing = rank_low = 0
for p in ev["per_q"]:
    tops = p["top"]
    if any(x not in CM for x in tops):
        missing += 1
        continue
    cnt = Counter(norm(CM[x]["content"][:400]) for x in tops)
    if any(n > 1 for n in cnt.values()):
        col += 1
        if p.get("rank") in (None, 5) or (p.get("rank") or 99) > 5:
            rank_low += 1
out = {"dup_groups": gr, "top5_collision_questions": col,
       "collisions_with_rank_gt5_or_miss": rank_low, "missing_top_ids": missing}
json.dump(out, open(f"{R}/law_crowdstat.json", "w", encoding="utf-8"), ensure_ascii=False)
print("CROWDSTAT", json.dumps(out), flush=True)
print("FIN7 DONE", flush=True)
