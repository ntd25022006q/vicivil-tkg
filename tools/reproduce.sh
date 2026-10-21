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

say "1/4 Cham lai ket qua truy hoi (BM25 + vector da luu + RRF)"
"$PY" src/law_eval_repro.py

say "2/4 Do chat luong du lieu chunk"
"$PY" src/law_quality.py

say "3/4 Xuat do thi tri thuc ra RDF / JSON-LD"
"$PY" src/law_rdf_export.py

say "4/4 Lap chi muc dieu khoan"
"$PY" src/law_articles_index.py

say "Hoan tat. Ket qua:"
ls -l benchmark/law_eval_repro.json provenance/chunk_quality.json \
      docs/graph/law_graph.ttl docs/graph/law_graph.jsonld \
      docs/graph/law_articles.json
