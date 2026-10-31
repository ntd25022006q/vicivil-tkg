"""Temporal graph layer: law lifecycle skeleton + point-in-time queries.
Laws carry [valid_from, valid_to); succession edges chain generations.
Chunks/entities inherit validity from their law; cross-generation entity links
(same normalized name) become SUPERSEDED_BY when full extraction lands.
Usage: python -u law_temporal.py   -> runs/temporal_graph.json + self-test
"""
import json, os, unicodedata, re

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
OUT = f"{R}/temporal_graph.json"
CHUNKS = f"{R}/civil_chunks.jsonl"

LAWS = [
    {"law_id": "BLDS1995", "ten": "Bo luat Dan su 1995", "so_hieu": "44-L/CTN",
     "valid_from": "1996-07-01", "valid_to": "2006-01-01", "status": "het_hieu_luc"},
    {"law_id": "BLDS2005", "ten": "Bo luat Dan su 2005", "so_hieu": "33/2005/QH11",
     "valid_from": "2006-01-01", "valid_to": "2017-01-01", "status": "het_hieu_luc"},
    {"law_id": "BLDS2015", "ten": "Bo luat Dan su 2015", "so_hieu": "91/2015/QH13",
     "valid_from": "2017-01-01", "valid_to": None, "status": "con_hieu_luc"},
    {"law_id": "HNGD2014", "ten": "Luat Hon nhan va Gia dinh 2014", "so_hieu": "52/2014/QH13",
     "valid_from": "2015-01-01", "valid_to": None, "status": "con_hieu_luc"},
]
SUCCESSION = [
    {"src": "BLDS2005", "tgt": "BLDS1995", "relation": "REPLACES",
     "at": "2006-01-01", "note": "BLDS 2005 thay the BLDS 1995"},
    {"src": "BLDS2015", "tgt": "BLDS2005", "relation": "REPLACES",
     "at": "2017-01-01", "note": "BLDS 2015 thay the BLDS 2005"},
]


def fold(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in unicodedata.category(c) != "Mn" for c in [c])
    return re.sub(r"\s+", " ", s.strip().lower())


def law_as_of(laws, date):
    return [L["law_id"] for L in laws
            if L["valid_from"] <= date and (L["valid_to"] is None or date < L["valid_to"])]


def chunk_valid(lawmap, chunk, date):
    L = lawmap.get(chunk["law_id"])
    if not L:
        return False
    return L["valid_from"] <= date and (L["valid_to"] is None or date < L["valid_to"])


lawmap = {L["law_id"]: L for L in LAWS}
chunks = [json.loads(L) for L in open(CHUNKS, encoding="utf-8")] if os.path.exists(CHUNKS) else []
by_law = {}
for c in chunks:
    by_law[c["law_id"]] = by_law.get(c["law_id"], 0) + 1

g = {"laws": LAWS, "succession": SUCCESSION,
     "chunk_counts": by_law,
     "tests": {
         "2010-06-01": law_as_of(LAWS, "2010-06-01"),
         "2020-06-01": law_as_of(LAWS, "2020-06-01"),
         "2000-01-01": law_as_of(LAWS, "2000-01-01"),
     }}
json.dump(g, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("laws:", len(LAWS), "edges:", len(SUCCESSION), "chunks:", len(chunks), flush=True)
assert g["tests"]["2010-06-01"] == ["BLDS2005"], g["tests"]["2010-06-01"]
assert set(g["tests"]["2020-06-01"]) == {"BLDS2015", "HNGD2014"}
assert g["tests"]["2000-01-01"] == ["BLDS1995"]
print("SELF-TEST PASS: 2010->BLDS2005, 2020->BLDS2015+HNGD2014, 2000->BLDS1995", flush=True)
print("wrote", OUT, flush=True)
