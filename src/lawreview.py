"""Gold review triage: auto-flag suspicious Q-gold pairs for manual review.
Flags: low keyword overlap, gold too short/long, law/date mismatch.
Output: runs/gold_review.json {qid: {flags, question, gold_text}}
"""
import json, re, unicodedata

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"


def toks(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    return set(re.findall(r"[a-zà-ỹđ0-9]{3,}", s))


STOP = {"những", "các", "của", "và", "với", "trong", "không", "được", "này",
        "qua", "theo", "quy", "định", "luật", "điều", "khoản", "người", "việc"}
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
lawmap = {L["law_id"]: L for L in G["laws"]}
items = []
for fn in ["law_bench_seed.json", "law_bench_main.json"]:
    try:
        items += json.load(open(f"{R}/{fn}", encoding="utf-8"))
    except Exception:
        pass
seen, out = set(), []
for o in items:
    if o["qid"] in seen:
        continue
    seen.add(o["qid"])
    g = (o.get("gold_ids") or ["ABSENT"])[0]
    c = chunks.get(g)
    flags = []
    if g == "ABSENT" or not c:
        flags.append("gold-missing")
    else:
        qw = toks(o["question"]) - STOP
        cw = toks(c["content"]) - STOP
        ov = len(qw & cw) / max(1, len(qw))
        if ov < 0.25:
            flags.append(f"low-overlap-{ov:.2f}")
        if c["chars"] < 60:
            flags.append("gold-short")
        L = lawmap.get(c.get("law_id", ""), {})
        if not (L.get("valid_from", "9") <= o.get("as_of", "") and
                (L.get("valid_to") is None or o.get("as_of", "") < L["valid_to"])):
            flags.append("date-mismatch")
    out.append({"qid": o["qid"], "flags": flags, "question": o["question"],
                "gold": g, "gold_text": (c["content"][:300] if c else None)})
json.dump(out, open(f"{R}/gold_review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
fl = [o for o in out if o["flags"]]
print(f"total={len(out)} flagged={len(fl)}", flush=True)
for o in fl[:20]:
    print(f'{o["qid"]} {o["flags"]} | {o["question"][:70]}', flush=True)
