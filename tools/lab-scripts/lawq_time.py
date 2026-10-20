"""Realtime demo: hoi luat tai thoi diem X -> chi chunk con hieu luc.
Usage: lawq_time.py <YYYY-MM-DD> [keyword]
"""
import json, sys

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
lawmap = {L["law_id"]: L for L in G["laws"]}
DATE = sys.argv[1]
KW = sys.argv[2] if len(sys.argv) > 2 else ""


def valid(law_id):
    L = lawmap[law_id]
    return L["valid_from"] <= DATE and (L["valid_to"] is None or DATE < L["valid_to"])


n_all = n_ok = 0
hits = []
for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8"):
    c = json.loads(L)
    n_all += 1
    if valid(c["law_id"]):
        n_ok += 1
        if KW and KW in c["content"] and len(hits) < 3:
            hits.append(c)
print(f"tai {DATE}: luat hieu luc = "
      f"{[L['law_id'] for L in G['laws'] if valid(L['law_id'])]}", flush=True)
print(f"chunk hop le: {n_ok}/{n_all}", flush=True)
for h in hits:
    print(" -", h["chunk_id"], "|", h["content"][:160].replace("\n", " "), flush=True)
