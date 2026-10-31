"""Cham lai bo benchmark theo quy tac "nhieu dap an dung", va cong bo ca hai
cach cham de nguoi doc tu so sanh.

Nen:
  - dap an vang cua moi cau nam o benchmark/law_bench_main.json (truong gold_ids,
    co the nhieu dap an) va benchmark/law_bench_seed.json (nhom CIV*).
  - thu tu tra ve cua he thong nam o benchmark/law_eval_ranks_full.json (truong per_q).
  - noi dung chuan hoa cua tung chunk lay tu data/civil_chunks.jsonl.

Cach cham:
  (A) "chat tu ID"  - dung nhu cong bo hien tai: chi dung khi top-k co DUNG
      mot dap an vang.
  (B) "nhieu dap an" - dung khi top-k co bat ky dap an vang nao, HOAC co chunk
      khac ma noi dung chuan hoa giong het mot dap an vang (truong hop tra ve
      ngon dung tu ban luat khac).

Khong can GPU, khong can mo hinh: chi so sanh chuoi van ban da chuan hoa.
"""
import io, json, os, re, sys, unicodedata, collections

R = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root (src/ is one level down)
B = os.path.join(R, "benchmark")

def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r"[^\w\sđ]", "", s)
    return s

content = {}
with io.open(os.path.join(R, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        content[c["chunk_id"]] = norm(c.get("content", ""))

gold = {}
for fn in ("law_bench_main.json", "law_bench_seed.json"):
    for q in json.load(io.open(os.path.join(B, fn), encoding="utf-8")):
        g = q.get("gold_ids") or []
        if g:
            gold[q["qid"]] = g

ev = json.load(io.open(os.path.join(B, "law_eval_ranks_full.json"), encoding="utf-8"))
tops = {q["qid"]: q.get("top", []) for q in ev.get("per_q", [])}

ks = (1, 3, 5, 10)
A = collections.Counter()
Bcnt = collections.Counter()
recovered = []
n = 0

for qid, golds in gold.items():
    top = tops.get(qid)
    if not top:
        continue
    n += 1
    gnorms = {content[g] for g in golds if g in content and content[g]}
    for k in ks:
        strict = any(t in golds for t in top[:k])
        equiv = False
        if not strict:
            for t in top[:k]:
                cn = content.get(t, "")
                if cn and cn in gnorms:
                    equiv = True
                    break
        if strict:
            A[k] += 1
        if strict or equiv:
            Bcnt[k] += 1
            if equiv:
                if k == 10:
                    recovered.append(qid)

regold = json.load(io.open(os.path.join(B, "regold.json"), encoding="utf-8"))
# nhom cau bi danh dau "khong xac minh duoc": dap an vang bi dat null
no_valid_gold = {q for q, v in regold.items() if not v.get("new_gold")}

def r(c, k):
    return round(c[k] / n, 4) if n else 0.0

C = collections.Counter()
nC = 0
for qid, golds in gold.items():
    top = tops.get(qid)
    if not top or qid in no_valid_gold:
        continue
    nC += 1
    gnorms = {content[g] for g in golds if g in content and content[g]}
    for k in ks:
        strict = any(t in golds for t in top[:k])
        equiv = False
        if not strict:
            for t in top[:k]:
                cn = content.get(t, "")
                if cn and cn in gnorms:
                    equiv = True
                    break
        if strict or equiv:
            C[k] += 1

out = {
    "n_questions_scored": n,
    "rule_A_strict_id": "chi dung khi top-k chua DUNG mot ID dap an vang",
    "rule_B_multi_answer": "dung khi top-k co bat ky ID dap an vang, hoac co chunk "
                            "khac ma noi dung chuan hoa giong het dap an vang",
    "A_strict_id": {"hit@" + str(k): r(A, k) for k in ks},
    "B_multi_answer": {"hit@" + str(k): r(Bcnt, k) for k in ks},
    "questions_recovered_at_10": len(recovered),
    "recovered_examples": recovered[:12],
    "C_only_questions_with_a_verified_gold": {
        "n_questions": nC,
        "excluded_questions_without_verifiable_gold": n - nC,
        "hit@" + str(1): round(C[1] / nC, 4) if nC else 0.0,
        "hit@3": round(C[3] / nC, 4) if nC else 0.0,
        "hit@5": round(C[5] / nC, 4) if nC else 0.0,
        "note": "chi cham nhung cau co dap an vang xac minh duoc; nhom bi danh dau "
                "'khong xac minh duoc' duoc tach ra va cong bo rieng",
    },
}
p = os.path.join(B, "law_eval_matching_rules.json")
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))