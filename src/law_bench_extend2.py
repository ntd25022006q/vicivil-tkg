#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benchmark extension round 2: questions from the newly ingested 1996-2015 era
documents (BLTTDS2004, ND158_2005, ND126_2014), same verification discipline as
round 1 and the frozen 281 core set. Run on the A30 host under flock (single
instance - the round-1 concurrent race is documented and must not repeat).

Stages (checkpointed in runs/extension2/):  G -> A1 -> A2 -> R -> O -> V
Nothing is written into the release tree here; collect step does that."""
import base64, json, os, re, sys, time, urllib.request
from array import array
from datetime import date
from concurrent.futures import ThreadPoolExecutor

W = "/home/devlab1/law_workspace"
R = f"{W}/hf_release"
RUN = f"{W}/runs/extension2"
os.makedirs(RUN, exist_ok=True)
OLLAMA = "http://127.0.0.1:11434"
GEN_MODEL = "qwen2.5:14b"
DEEP_MODEL = "qwen3:14b"
EMB_MODEL = "embeddinggemma:300m"
N_TARGET = 160
LAW_IDS = {"BLTTDS2004", "ND158_2005", "ND126_2014"}
LOG = open(f"{RUN}/extension2_run.log", "a", encoding="utf-8")

def log(*a):
    print(*a, file=sys.stdout, flush=True)
    print(*a, file=LOG, flush=True)

def stage(name):
    p = f"{RUN}/{name}.json"
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8")), True
        except Exception:
            pass
    return {} if name in ("A1", "A2", "R") else [], False

def save(name, obj):
    json.dump(obj, open(f"{RUN}/{name}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

def ochat(model, messages, max_tokens=220, temperature=0.0):
    body = {"model": model, "messages": messages, "stream": False,
            "keep_alive": "3h",
            "options": {"temperature": temperature, "num_predict": max_tokens}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as rp:
        d = json.load(rp)
    return d["message"]["content"] or ""

def oembed(text):
    body = {"model": EMB_MODEL, "input": text}
    req = urllib.request.Request(f"{OLLAMA}/api/embed",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as rp:
        d = json.load(rp)
    return d["embeddings"][0]

def last_json(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    for m in reversed(re.findall(r"\{[^{}]*\}", text, re.S)):
        try:
            return json.loads(m)
        except Exception:
            continue
    return None

# ---------------------------------------------------------------- graph + pool
graph = json.load(open(f"{R}/provenance/temporal_graph.json", encoding="utf-8"))
LAWS = {L["law_id"]: L for L in graph["laws"] if L["law_id"] in LAW_IDS}
assert len(LAWS) == 3, f"r2 laws not registered yet: {sorted(LAWS)}"

def mid_as_of(law):
    vf = date.fromisoformat(law["valid_from"])
    cap = date(2026, 6, 30)
    if law["valid_to"]:
        vt = date.fromisoformat(law["valid_to"])
        if vt <= vf:
            vt = date.fromordinal(vf.toordinal() + 365)
        span = (vt - vf).days
        mid = date.fromordinal(vf.toordinal() + int(span * 0.6))
        mid = min(mid, date.fromordinal(vt.toordinal() - 1))
    else:
        if vf.year >= 2026:
            mid = date.fromordinal(vf.toordinal() + 45)
        else:
            mid = date(vf.year + 1, vf.month, vf.day)
        mid = min(mid, cap)
    mid = max(mid, date.fromordinal(vf.toordinal() + 1))
    return mid.isoformat()

AS_OF = {lid: mid_as_of(L) for lid, L in LAWS.items()}
log("r2 as_of windows:", AS_OF)

rows = [json.loads(L) for L in open(f"{W}/runs/civil_chunks.jsonl", encoding="utf-8")]
main_q = json.load(open(f"{R}/benchmark/law_bench_main.json", encoding="utf-8"))
seed_q = json.load(open(f"{R}/benchmark/law_bench_seed.json", encoding="utf-8"))
ext1 = json.load(open(f"{R}/benchmark/law_bench_extension.json", encoding="utf-8"))
ext1_G = json.load(open(f"{W}/runs/extension/G.json", encoding="utf-8"))
used = set()
for q in main_q + seed_q + ext1 + ext1_G:
    for cid in q.get("gold_ids", []):
        used.add(cid)
pool = [r for r in rows if r["chunk_id"] not in used and r.get("khoan")
        and r["chars"] >= 120 and r["law_id"] in LAW_IDS]
by_law = {}
for r in pool:
    by_law.setdefault(r["law_id"], []).append(r)
log("pool:", {k: len(v) for k, v in by_law.items()})
share = {k: len(v) for k, v in by_law.items()}
tot = sum(share.values())
quota = {k: min(120, max(3, round(N_TARGET * s / tot))) for k, s in share.items()}
over = sum(quota.values()) - N_TARGET
if over > 0:
    for k in sorted(quota, key=lambda k: -quota[k]):
        if over <= 0:
            break
        dec = min(over, max(0, quota[k] - 3))
        quota[k] -= dec
        over -= dec
elif over < 0:
    for k in sorted(quota, key=lambda k: -quota[k]):
        if over >= 0:
            break
        room = min(120 - quota[k], len(by_law[k]) - quota[k])
        add = min(room, -over)
        quota[k] += add
        over += add
log("quotas:", quota, "| sum:", sum(quota.values()))

import random
rng = random.Random(42)
samp = []
for k, n in quota.items():
    lst = by_law[k][:]
    rng.shuffle(lst)
    samp += lst[:n]

# ---------------------------------------------------------------- G: generate
SYS = ("Viet 1 cau hoi ngan (1-2 dong) cua NGUOI DAN gap tinh huong phap ly, "
       "dua vao DOAN LUAT. BAT BUOC: 100% tieng Viet, CAM tuyet doi chu Trung Quoc "
       "va tieng Anh, dung cau doi thuong, khong chep cau luat. "
       "CAU HOI PHAI DUOC TRA LOI TRUC TIEP VA DU BOI CHINH DOAN LUAT: khong hoi ly do "
       "hay co che ma doan khong ne, khong gia dinh tinh huong trai nguoc quy dinh "
       "trong doan. Chi in cau hoi.")
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
META = ["đoạn văn", "đoạn luật", "câu hỏi trên", "văn bản trên", "tình huống trên"]

def clean(q):
    q = (q or "").strip().split("\n")[0][:250]
    if CJK.search(q) or len(q) < 15 or any(m in q.lower() for m in META):
        return None
    return q

gen, done = stage("G")
if not done:
    gen = []
have_chunks = {g["gold_ids"][0] for g in gen}
todo = [r for r in samp if r["chunk_id"] not in have_chunks]
log("G: todo", len(todo))

def gen_one(i_r):
    i, r = i_r
    for _ in range(3):
        try:
            t = ochat(GEN_MODEL,
                      [{"role": "system", "content": SYS},
                       {"role": "user", "content": "DOAN LUAT:\n" + r["content"][:1500]}],
                      max_tokens=100, temperature=0.3)
            q = clean(t)
            if q:
                return {"qid": f"EXT{20001 + i}", "as_of": AS_OF[r["law_id"]],
                        "question": q, "gold_ids": [r["chunk_id"]],
                        "hint": "extension cohort r2 (weak gold, disclosed; ND/TT/2004-2015 era)",
                        "law_id": r["law_id"], "gen_model": GEN_MODEL}
        except Exception as ex:
            log("  gen retry:", str(ex)[:80])
            time.sleep(5)
    return None

for b in range(0, len(todo), 8):
    with ThreadPoolExecutor(max_workers=4) as ex:
        for o in ex.map(gen_one, list(enumerate(todo[b:b + 8], start=len(gen)))):
            if o:
                o["qid"] = "EXT%d" % (20001 + len(gen))
                gen.append(o)
    save("G", gen)
    log(f"G: [{min(b + 8, len(todo))}/{len(todo)}] n={len(gen)}")
log("G DONE n=", len(gen))

# ---------------------------------------------------------------- A1: audit 1
SYSA = ("Ban la chu cham benchmark phap ly. Cho CAU HOI cua nguoi dan va DOAN LUAT "
        "gold. Chi tra loi DUNG MOT DONG JSON: "
        "{\"usable\": \"yes|partial|no\", \"reason\": \"ngan gon\"}. "
        "Tieu chi: (1) la cau hoi tinh huong thuc te, khong chep cau chu luat; "
        "(2) DOAN LUAT tra loi duoc truc tiep cau hoi; "
        "(3) cau hoi tu conten, khong can thong tin ngoai DOAN LUAT. "
        "usable=yes chi khi dat ca 3 tieu chi.")

a1, _ = stage("A1")
chunk_by_id = {r["chunk_id"]: r for r in rows}

def audit1(g):
    if g["qid"] in a1:
        return None
    ch = chunk_by_id[g["gold_ids"][0]]
    for _ in range(3):
        try:
            t = ochat(GEN_MODEL,
                      [{"role": "system", "content": SYSA},
                       {"role": "user", "content": "CAU HOI: " + g["question"] +
                        "\n\nDOAN LUAT:\n" + ch["content"][:1500]}],
                      max_tokens=140)
            j = last_json(t)
            if j and j.get("usable") in ("yes", "partial", "no"):
                return g["qid"], {"usable": j["usable"],
                                  "reason": str(j.get("reason", ""))[:200]}
        except Exception as ex:
            log("  a1 retry:", str(ex)[:80])
            time.sleep(5)
    return g["qid"], {"usable": "parse-fail", "reason": "unparseable judge output"}

todo1 = [g for g in gen if g["qid"] not in a1]
log("A1: todo", len(todo1))
for b in range(0, len(todo1), 8):
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(audit1, todo1[b:b + 8]):
            if r:
                a1[r[0]] = r[1]
    save("A1", a1)
    log(f"A1: [{min(b + 8, len(todo1))}/{len(todo1)}]")
log("A1 DONE")

# ---------------------------------------------------------------- A2: deep audit
SYSD = ("Ban la chuyen gia phap ly dang tham dinh cau hoi cho benchmark. Hay suy "
        "nghi ky (toi da 5 dong) roi ket luan bang DUNG MOT DONG JSON cuoi cung: "
        "{\"usable\": \"yes|partial|no\", \"evidence\": \"trich doan cua DOAN LUAT tra loi cau hoi\", \"reason\": \"ngan gon\"}. "
        "Tieu chi: (1) cau hoi tinh huong thuc te khong chep luat; (2) DOAN LUAT chua "
        "du thong tin tra loi; (3) khong can thong tin ngoai DOAN LUAT. "
        "yes chi khi dat ca 3; partial khi dat (2) nhung thieu (1)/(3); no neu DOAN LUAT khong tra loi duoc.")

a2, _ = stage("A2")
flagged = [g for g in gen if a1.get(g["qid"], {}).get("usable") != "yes"]
todo2 = [g for g in flagged if g["qid"] not in a2]
log("A2: flagged", len(flagged), "todo", len(todo2))

def audit2(g):
    ch = chunk_by_id[g["gold_ids"][0]]
    for _ in range(3):
        try:
            t = ochat(DEEP_MODEL,
                      [{"role": "system", "content": SYSD},
                       {"role": "user", "content": "CAU HOI: " + g["question"] +
                        "\n\nDOAN LUAT:\n" + ch["content"][:1500]}],
                      max_tokens=600, temperature=0.0)
            j = last_json(t)
            if j and j.get("usable") in ("yes", "partial", "no"):
                return g["qid"], {"usable": j["usable"],
                                  "reason": str(j.get("reason", ""))[:200],
                                  "evidence": str(j.get("evidence", ""))[:300]}
        except Exception as ex:
            log("  a2 retry:", str(ex)[:80])
            time.sleep(5)
    return g["qid"], {"usable": "parse-fail", "reason": "unparseable"}

for b in range(0, len(todo2), 8):
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(audit2, todo2[b:b + 8]):
            if r:
                a2[r[0]] = r[1]
    save("A2", a2)
    log(f"A2: [{min(b + 8, len(todo2))}/{len(todo2)}]")
log("A2 DONE")

# ---------------------------------------------------------------- R: regold
regold, _ = stage("R")
rejected = [g for g in gen
            if a2.get(g["qid"], {}).get("usable") in ("no", "parse-fail")
            or (a2.get(g["qid"], {}).get("usable") == "partial"
                and a1.get(g["qid"], {}).get("usable") == "no")]
todoR = [g for g in rejected if g["qid"] not in regold]
log("R: rejected", len(rejected), "todo", len(todoR))

import numpy as np
vdb = json.load(open(f"{R}/index/vdb_chunks.json", encoding="utf-8"))
vids = [d["__id__"] for d in vdb["data"]]
vmat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype="float32").reshape(len(vids), 768)
nrm = np.linalg.norm(vmat, axis=1)
nrm[nrm == 0] = 1.0

SYSR = ("Cho CAU HOI va DOAN LUAT ung cuien. Chi tra loi MOT DONG JSON: "
        "{\"usable\": \"yes|no\", \"reason\": \"ngan gon\"}. yes neu DOAN LUAT tra loi duoc cau hoi.")

def regold_one(g):
    try:
        qv = np.asarray(oembed(g["question"]), dtype="float32")
        sims = (vmat @ qv) / (nrm * (np.linalg.norm(qv) + 1e-9))
        cand = [vids[i] for i in np.argsort(-sims, kind="stable")[:5]
                if vids[i] != g["gold_ids"][0]]
        for cid in cand:
            ch = chunk_by_id[cid]
            t = ochat(DEEP_MODEL,
                      [{"role": "system", "content": SYSR},
                       {"role": "user", "content": "CAU HOI: " + g["question"] +
                        "\n\nDOAN LUAT:\n" + ch["content"][:1500]}],
                      max_tokens=200)
            j = last_json(t) or {}
            if j.get("usable") == "yes":
                return g["qid"], {"regolded_to": cid, "confirmed_by": DEEP_MODEL,
                                  "reason": str(j.get("reason", ""))[:160]}
        return g["qid"], {"regolded_to": None,
                          "reason": "no candidate confirmed"}
    except Exception as ex:
        log("  regold retry:", str(ex)[:80])
        return g["qid"], {"regolded_to": None, "reason": "error " + str(ex)[:80]}

for b in range(0, len(todoR), 8):
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(regold_one, todoR[b:b + 8]):
            if r:
                regold[r[0]] = r[1]
    save("R", regold)
    log(f"R: [{min(b + 8, len(todoR))}/{len(todoR)}]")
log("R DONE")

# ---------------------------------------------------------------- O: as_of check
asof, _ = stage("O")
if not asof:
    asof = []
changed = 0
for g in gen:
    law = LAWS[g["law_id"]]
    vf = date.fromisoformat(law["valid_from"])
    vt = date.fromisoformat(law["valid_to"]) if law["valid_to"] else None
    ao = date.fromisoformat(g["as_of"])
    ok = ao >= vf and (vt is None or ao < vt)
    if not ok:
        changed += 1
        asof.append({"qid": g["qid"], "old": g["as_of"], "new": AS_OF[g["law_id"]],
                     "reason": f"as_of outside validity {law['valid_from']}..{law['valid_to']}"})
        g["as_of"] = AS_OF[g["law_id"]]
save("O", asof)
log("O DONE: fixed", changed)
save("G", gen)

# ---------------------------------------------------------------- V: vectors
vec, donev = stage("V")
if not donev or len(vec) < len(gen):
    vec = {k: v for k, v in vec.items()} if isinstance(vec, dict) else {}
    for i, g in enumerate(gen):
        if g["qid"] in vec:
            continue
        v = oembed(g["question"])
        vec[g["qid"]] = base64.b64encode(array("f", v).tobytes()).decode()
        if i % 20 == 0:
            log(f"V: {i}/{len(gen)}")
    save("V", vec)
log("V DONE", len(vec))

tiers = {}
for g in gen:
    q = g["qid"]
    d = a2.get(q, a1.get(q, {})).get("usable")
    if q in regold and regold[q].get("regolded_to"):
        tiers[q] = "regolded"
    elif d == "yes":
        tiers[q] = "verified"
    else:
        tiers[q] = "flagged"
import collections
log("SUMMARY tiers:", dict(collections.Counter(tiers.values())))
log("EXTEND2_STAGES_DONE")
