#!/usr/bin/env bash
# Tai lap va kiem chung bo du lieu ViCivil-TKG - KHONG can GPU, KHONG can model.
#
#   bash tools/reproduce.sh
#
# Yeu cau: Python 3.9+ va numpy (pip install -r requirements.txt)
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n=== %s ===\n' "$1"; }
PY="${PYTHON:-python3}"

say "1/5 Cham lai ket qua truy hoi (BM25 + vector da luu + RRF)"
"$PY" src/law_eval_repro.py

say "2/5 Tinh lai chi so sau khi xep lai (tu xep hang da luu, khong can GPU)"
"$PY" src/law_rerank_verify.py

say "3/5 Do chat luong du lieu chunk"
"$PY" src/law_quality.py

say "4/5 Xuat va kiem chung do thi tri thuc (RDF / JSON-LD)"
"$PY" src/law_rdf_export.py
"$PY" src/law_rdf_verify.py

say "5/5 Lap chi muc dieu khoan"
"$PY" src/law_articles_index.py

say "Ket qua:"
ls -l benchmark/law_eval_repro.json benchmark/rerank_verify.json \
      provenance/chunk_quality.json provenance/rdf_verify.json \
      docs/graph/law_graph.ttl docs/graph/law_graph.jsonld \
      docs/graph/law_articles.json
