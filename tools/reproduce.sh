#!/usr/bin/env bash
# Tai lap va kiem chung bo du lieu ViCivil-TKG - KHONG can GPU, KHONG can model.
#
#   bash tools/reproduce.sh
#
# Yeu cau: Python 3.9+ va numpy/scipy (pip install -r requirements.txt)
# v1.0.1: sua loi buoc 7 (go rong bi goi voi chuoi rong); them buoc kiem
# chung rescore; doi ten buoc cho dung thu tu.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n=== %s ===\n' "$1"; }
PY="${PYTHON:-python3}"

say "1/7 Cham lai ket qua truy hoi (BM25 + vector da luu + RRF)"
"$PY" src/law_eval_repro.py

say "2/7 Tinh lai chi so sau khi xep lai (tu xep hang da luu, khong can GPU)"
"$PY" src/law_rerank_verify.py

say "3/7 Do chat luong du lieu chunk"
"$PY" src/law_quality.py

say "4/7 Xuat va kiem chung do thi tri thuc (RDF / JSON-LD)"
"$PY" src/law_rdf_export.py
"$PY" src/law_rdf_verify.py

say "5/7 Lap chi muc dieu khoan"
"$PY" src/law_articles_index.py

say "6/7 Kiem dinh thong ke cap doi (LLM RAG: McNemar + Wilcoxon)"
"$PY" src/law_rag_signif.py

say "7/7 Cham lai cohort mo rong + xac minh xep hang loi + rescore LLM"
"$PY" src/law_extension_eval.py
"$PY" src/law_extension_eval.py benchmark/law_bench_extension2.json benchmark/extension2_question_vectors.json benchmark/extension2_eval_ranks.json
"$PY" src/law_extension_eval.py benchmark/law_bench_extension3.json benchmark/extension3_question_vectors.json benchmark/extension3_eval_ranks.json
"$PY" src/law_extension_eval.py benchmark/law_bench_extension4.json benchmark/extension4_question_vectors.json benchmark/extension4_eval_ranks.json
"$PY" src/law_ranks_full_rebuild.py verify
"$PY" src/law_llm_rag_rescore.py --check

say "Ket qua:"
ls -l benchmark/law_eval_repro.json benchmark/rerank_verify.json \
      benchmark/extension_eval_ranks.json benchmark/extension2_eval_ranks.json \
      benchmark/extension3_eval_ranks.json benchmark/extension3_rerank_result.json \
      benchmark/extension4_eval_ranks.json benchmark/extension4_rerank_result.json \
      provenance/chunk_quality.json provenance/rdf_verify.json \
      docs/graph/law_graph.ttl docs/graph/law_graph.jsonld
