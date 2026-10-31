#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end LLM RAG evaluation: does the TCR retrieval gain transfer to
downstream QA?

Conditions (all 281 questions, greedy decode, deterministic):
  norag          : closed-book LLM
  rag_hybrid     : top-5 published hybrid (BM25+dense+RRF)
  rag_hybrid_tcr : top-5 after TCR-hard temporal filter
  rag_rerank_tcr : top-5 stored rerank + TCR-hard (Track B best)

Metrics (deterministic, no LLM judge):
  cite_acc : answer cites an article number that matches a gold article
  span_f1  : token-F1(answer, concatenated gold chunk contents)
  abstain  : 'không đủ thông tin' present
  ctx_hit5 : gold chunk present in the fed context (sanity vs published)

Output: benchmark/llm_rag_result.json
"""
import json, os, re, time, unicodedata

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

R = os.environ.get("VICIVIL_ROOT",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B, D = f"{R}/benchmark", f"{R}/data"
OUT = f"{B}/llm_rag_result.json"
MODEL = "Qwen/Qwen2.5-3B-Instruct"
BATCH = 6
MAX_NEW = 180

t00 = time.time()


def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)


def toks(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.findall(r"[a-zà-ỹđ0-9]+", s)


def token_f1(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return 0.0
    common = sum((__import__("collections").Counter(ta) & __import__("collections").Counter(tb)).values())
    if common == 0:
        return 0.0
    p = common / len(ta)
    r = common / len(tb)
    return 2 * p * r / (p + r)


CITE_RE = re.compile(r"điều\s+(\d+[a-z]?)", re.IGNORECASE)


def cited_articles(ans):
    return set(m.lower() for m in CITE_RE.findall(ans or ""))


log("load inputs...")
ri = json.load(open(f"{B}/rag_inputs.json", encoding="utf-8"))
chunks = {}
with open(f"{D}/civil_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        chunks[c["chunk_id"]] = c


def fmt_chunk(cid):
    c = chunks.get(cid)
    if c is None:
        return None
    seg = cid.split("|")
    parts = [seg[0]]
    if len(seg) > 1 and seg[1]:
        parts.append(seg[1].replace("Dieu", "Điều "))
    if len(seg) > 2 and seg[2]:
        parts.append(seg[2].replace("Khoan", "Khoản "))
    if len(seg) > 3 and seg[3]:
        parts.append(seg[3].replace("Diem", "Điểm ").replace("Diemc", "Điểm c"))
    label = " — ".join(parts)
    content = (c.get("content") or "").strip()
    if len(content) > 900:
        content = content[:900] + "…"
    return f"[{label}]\n{content}"


def gold_articles(qid):
    out = set()
    for g in ri[qid]["gold_ids"]:
        m = re.match(r"[^|]+\|Dieu(\d+[a-z]?)", g)
        if m:
            out.add(m.group(1).lower())
    return out


def gold_text(qid):
    return " ".join((chunks.get(g, {}).get("content") or "") for g in ri[qid]["gold_ids"])


COND = {
    "norag": None,
    "rag_hybrid": "base_top5",
    "rag_hybrid_tcr": "tcr_top5",
    "rag_rerank_tcr": "rr_tcr_top5",
}

qids = sorted(ri.keys())


def build_prompt(qid, cond):
    q = ri[qid]["question"]
    key = COND[cond]
    seen = set()
    if key is None:
        sys = ("Bạn là trợ lý pháp lý Việt Nam. Hãy trả lời ngắn gọn, chính xác; "
               "nêu rõ số điều luật nếu bạn biết. Nếu không chắc, hãy nói 'Không đủ thông tin'.")
        usr = f"Câu hỏi: {q}\nTrả lời:"
    else:
        ctx, seen = [], set()
        for cid in ri[qid][key]:
            s = fmt_chunk(cid)
            if s:
                ctx.append(s)
                seen.add(cid)
        sys = ("Bạn là trợ lý pháp lý Việt Nam. Dựa CHỈ trên các trích dẫn luật dưới đây, "
               "trả lời ngắn gọn, chính xác và nêu rõ điều khoản (ví dụ: Điều 455). "
               "Nếu trích dẫn không đủ để trả lời, hãy nói 'Không đủ thông tin'.")
        usr = "Các trích dẫn luật:\n\n" + "\n\n".join(ctx) + f"\n\nCâu hỏi: {q}\nTrả lời:"
    return sys, usr, seen


log("load model...")
tok = AutoTokenizer.from_pretrained(MODEL)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(
    MODEL, dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda"
)
model.eval()
log("  model ready on cuda")

res = {"model": MODEL, "params": {"batch": BATCH, "max_new_tokens": MAX_NEW,
       "decode": "greedy", "transformers": __import__("transformers").__version__,
       "torch": torch.__version__}, "conditions": {}}

for cond in COND:
    log(f"=== condition {cond}")
    answers, prompts, seens = {}, {}, {}
    for qid in qids:
        if COND[cond] == "rr_tcr_top5" and not ri[qid].get("rr_tcr_top5"):
            continue
        sys, usr, seen = build_prompt(qid, cond)
        msgs = [{"role": "system", "content": sys}, {"role": "user", "content": usr}]
        prompts[qid] = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        seens[qid] = seen
    order = sorted(prompts.keys(), key=lambda q: len(prompts[q]))
    log(f"  {len(order)} prompts")
    n_done = 0
    t0c = time.time()
    for i in range(0, len(order), BATCH):
        batch = order[i:i + BATCH]
        enc = tok([prompts[q] for q in batch], return_tensors="pt", padding=True,
                  truncation=True, max_length=6144).to("cuda")
        with torch.inference_mode():
            gen = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for j, q in enumerate(batch):
            out_ids = gen[j][enc["input_ids"].shape[1]:]
            answers[q] = tok.decode(out_ids, skip_special_tokens=True).strip()
        n_done += len(batch)
        if n_done % (BATCH * 10) == 0:
            log(f"  {n_done}/{len(order)} ({time.time()-t0c:.0f}s)")
    # metrics
    n = 0
    cite_ok = 0
    f1s = []
    abst = 0
    ctx_hit = 0
    lens = []
    per_q = {}
    for q, a in answers.items():
        n += 1
        ga = gold_articles(q)
        ca = cited_articles(a)
        ok = bool(ca & ga)
        cite_ok += ok
        f1 = token_f1(a, gold_text(q))
        f1s.append(f1)
        ab = "không đủ thông tin" in a.lower()
        abst += ab
        ch = bool(seens[q] & set(ri[q]["gold_ids"]))
        ctx_hit += ch
        lens.append(len(toks(a)))
        per_q[q] = {"answer": a, "cite_ok": ok, "span_f1": round(f1, 4),
                    "abstain": ab, "ctx_hit5": ch}
    summary = {
        "n": n,
        "cite_acc": round(cite_ok / n, 4),
        "span_f1": round(sum(f1s) / n, 4),
        "abstain_rate": round(abst / n, 4),
        "ctx_hit5": round(ctx_hit / n, 4),
        "mean_ans_tokens": round(sum(lens) / n, 1),
    }
    res["conditions"][cond] = {"summary": summary, "per_q": per_q}
    log(f"  SUMMARY {cond}: {summary}")
    # incremental save (crash-safe)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

res["runtime_sec"] = round(time.time() - t00, 1)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log(f"saved -> {OUT}")
log("DONE")
