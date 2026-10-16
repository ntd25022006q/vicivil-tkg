"""Quality filter for generated benchmark: drop CJK/meta/long/short questions."""
import json, re

b = json.load(open("/home/devlab1/law_workspace/runs/law_bench_200.json", encoding="utf-8"))
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
META = ["đoạn văn", "đoạn luật", "câu hỏi trên", "văn bản trên", "tình huống trên"]
keep, drop = [], 0
for o in b:
    q = o["question"]
    if CJK.search(q) or len(q) < 15 or len(q) > 250 or any(m in q.lower() for m in META):
        drop += 1
        continue
    keep.append(o)
json.dump(keep, open("/home/devlab1/law_workspace/runs/law_bench_200c.json", "w",
                     encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"kept={len(keep)} dropped={drop}", flush=True)
