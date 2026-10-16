"""Smoke: hybrid (default) vs graph mode on 2 questions."""
import json, sys

sys.path.insert(0, "/home/devlab1/law_workspace/src")
from law_adgr import LawRetriever

rt = LawRetriever()
tests = [
    ("Con đẻ muốn đổi từ họ cha sang họ mẹ cần điều kiện gì?", "2024-06-01",
     "BLDS2015|Dieu27|Khoan2"),
    ("Nam nữ kết hôn phải đủ bao nhiêu tuổi?", "2024-06-01",
     "HNGD2014|Dieu8|Khoan1|Diema"),
]
for q, d, g in tests:
    h = rt.retrieve(q, d, topk=5)
    gr = rt.retrieve(q, d, topk=5, mode="graph")
    rh = h.index(g) + 1 if g in h else 99
    rg = gr.index(g) + 1 if g in gr else 99
    print(f"Q: {q[:45]}", flush=True)
    print(f"  hybrid rank={rh} graph rank={rg}", flush=True)
print("SMOKE DONE", flush=True)
