"""Cross-encoder rerank with FUSION (never override): Qwen3-Reranker-0.6B.
GPU-first with CPU fallback per AGENTS discipline. Scores (question, doc) pairs.
Fused as 0.5*base_rank + 0.5*rerank_rank with the base RRF order.
"""
import os

CK = os.environ.get("QWEN_RERANKER_CK", "Qwen/Qwen3-Reranker-0.6B")
_tok = _model = None
_device = None


def _load():
    global _tok, _model, _device
    if _model is not None:
        return True
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        _tok = AutoTokenizer.from_pretrained(CK, padding_side="left")
        try:
            import subprocess
            free = int(subprocess.run(
                "nvidia-smi --query-gpu=memory.free --format=csv,nounits,noheader",
                shell=True, capture_output=True, text=True).stdout.strip().split("\n")[0])
        except Exception:
            free = 0
        if free > 4000:
            _device = "cuda"
            _model = AutoModelForCausalLM.from_pretrained(CK, dtype="auto").eval().to("cuda")
        else:
            raise RuntimeError("gpu-low")
    except Exception:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            _tok = AutoTokenizer.from_pretrained(CK, padding_side="left")
            _device = "cpu"
            _model = AutoModelForCausalLM.from_pretrained(CK, torch_dtype="float32").eval()
        except Exception as e:
            print("reranker unavailable:", repr(e)[:120], flush=True)
            return False
    print("reranker on", _device, flush=True)
    return True


def score_pairs(question, docs, batch=16):
    """Return list[float] aligned with docs; [] if unavailable."""
    if not _load():
        return []
    import torch
    out = []
    with torch.no_grad():
        for i in range(0, len(docs), batch):
            msgs = [[{"role": "user",
                       "content": f"Cau hoi: {question}\nDoan luat: {d[:1500]}"}]
                      for d in docs[i:i + batch]]
            txt = _tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            enc = _tok(txt, padding=True, truncation=True, max_length=2048, return_tensors="pt")
            enc = {k: v.to(_device) for k, v in enc.items()}
            logits = _model(**enc).logits[:, -1]
            yw, nw = _tok("yes").input_ids[-1], _tok("no").input_ids[-1]
            s = (logits[:, yw] - logits[:, nw]).float().cpu().tolist()
            out.extend(s if isinstance(s, list) else [s])
    return out
