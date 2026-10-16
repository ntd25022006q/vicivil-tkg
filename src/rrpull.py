"""Background pull of Qwen3-Reranker-0.6B weights into HF cache."""
import os

os.environ.setdefault("HF_HUB_VERBOSITY", "error")
try:
    from huggingface_hub import snapshot_download
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "huggingface_hub"], check=True)
    from huggingface_hub import snapshot_download
p = snapshot_download("Qwen/Qwen3-Reranker-0.6B")
print("RERANKER READY:", p, flush=True)
