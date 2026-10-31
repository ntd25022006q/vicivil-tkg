"""Export 50-Q human review package (hand 12 + 38 random, Q + gold text + tick columns)."""
import json, random

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
bench = json.load(open(f"{R}/law_bench_main.json", encoding="utf-8"))
hand = json.load(open(f"{R}/law_bench_seed.json", encoding="utf-8"))
chunks = {}
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    r = json.loads(L)
    chunks[r["chunk_id"]] = r["content"]
random.seed(99)
syn = random.sample(bench, 38)
out = ["# GOI DUYET CHUYEN GIA - 50 cau (gold co tra loi dung cau hoi khong?)",
       "# Cach tick: DUNG / SAI / MOT-PHAN + ghi chu neu SAI", ""]
for i, o in enumerate(hand + syn, 1):
    g = (o.get("gold_ids") or ["?"])[0]
    out += [f"## C{i:02d} [{o['qid']}]", f"Q: {o['question']}",
            f"GOLD: {g}", f"A: {chunks.get(g, '?')[:400]}",
            "Tick: [ ] DUNG  [ ] SAI  [ ] MOT-PHAN", "Ghi chu:", ""]
open(f"{R}/review_package_50.md", "w", encoding="utf-8").write("\n".join(out))
print("wrote review_package_50.md", len(hand) + 38, "items", flush=True)
