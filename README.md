---
language:
- vi
license: cc-by-4.0
task_categories:
- question-answering
- text-retrieval
pretty_name: ViCivil-TKG (Vietnamese Civil Law Temporal KG & QA Benchmark)
size_categories:
- 10K<n<100K
tags:
- vietnamese
- legal
- temporal-knowledge-graph
- retrieval
- benchmark
- question-answering
- as-of-qa
- rag
configs:
- config_name: corpus
  data_files: data/civil_chunks.jsonl
- config_name: benchmark
  data_files:
  - benchmark/law_bench_main.json
  - benchmark/law_bench_seed.json
- config_name: benchmark-extension
  data_files: benchmark/law_bench_extension.json
- config_name: benchmark-extension2
  data_files: benchmark/law_bench_extension2.json
- config_name: index
  data_files:
  - index/vdb_chunks.json
  - index/vdb_entities.json
  - index/vdb_relationships.json
---

# ViCivil-TKG — Vietnamese Civil Law Temporal KG & QA Benchmark

![release](https://img.shields.io/badge/release-v1.1.0-black) ![license](https://img.shields.io/badge/license-CC--BY--4.0-blue) ![tasks](https://img.shields.io/badge/tasks-QA%20%2B%20retrieval-4c8) ![language](https://img.shields.io/badge/language-ti%E1%BA%BFng%20Vi%E1%BB%87t-red) ![repro](https://img.shields.io/badge/repro-GPU--free-success)

**ViCivil-TKG** is an open benchmark and temporal knowledge graph for Vietnamese civil-law question answering, built around two challenges most legal QA sets ignore:

1. **Temporal validity (`as_of` QA).** The same question has different answers under different applicability windows of a statute. Every question carries an `as_of` date and is scored against the law that was in force *at that date* — the retrieval protocol (TCR) filters candidates by validity windows built from a manually verified 37-node / 24-edge statute timeline graph.
2. **Gold-label reliability.** Automatically generated questions usually ship unverified gold answers. Here every gold passes a four-stage adjudication chain (two-tier generation audit → two-round re-anchoring → pass-3 sweep with guardrails → independent agreement audit) with full public trails, and rejected questions are **publicly quarantined** — they count in no metric.

> Tiếng Việt: Bộ dữ liệu mở cho hỏi–đáp pháp luật dân sự Việt Nam với kiểm định thời hiệu (`as_of`) và chuỗi thẩm định đáp án vàng đa vòng; câu không đạt được công khai ở nhóm cách ly, không tính vào chỉ số.

## Key facts

| | |
|---|---|
| Published questions | **451** = 281 core (12 hand-written + 269 generated) + 106 round-1 + 64 round-2 (1996–2015 era) |
| Quarantined questions | **226** (136 + 90), published verbatim with trails, never scored |
| Core gold tiers | 229 verified · 22 regolded · 4 author-verified · 26 flagged (excluded from headline metrics) · 0 unverifiable |
| Corpus | 20 legal documents, **13,151** article/clause/point chunks, per-chunk provenance + validity windows |
| Split | stratified dev/test 140/141 (core) |
| Baselines | BM25+dense+RRF retrieval, TCR temporal filtering, BGE-reranker-v2-m3, Qwen2.5-3B RAG (greedy) |
| Reproduction | `bash tools/reproduce.sh` — **no GPU, no network** required |

## Headline results (v1.0.1 frozen snapshot)

All numbers are computed from released artifacts; the paper's every figure is machine-verified (`src/verify_paper_numbers.py`).

| Metric | No TCR | + TCR | + Rerank & TCR |
|---|---|---|---|
| Core retrieval (281 q) | Hit@5 0.733 (MRR@10 0.540) | **Hit@5 0.811, MRR 0.662** | — |
| Round-2 1996–2015 (64 q) | Hit@5 0.703 | Hit@5 0.781 (p = 4.0e-05) | **Hit@1 0.703, Hit@5 0.828** |
| Core LLM cite_acc (Qwen2.5-3B) | 0.004 (no context) | hybrid 0.488 → **0.601** (McNemar p = 5.8e-05) | 0.604, ctx_hit5 0.850 |
| Round-2 LLM cite_acc | 0.000 | **0.531** (p = 1.2e-10) | 0.531 (span_F1 0.497) |

Disclosed hard slice: the round-2 `regolded` stratum (11 q) reaches only Hit@1 0.091 — old-statute anchoring is genuinely hard, and 4 of those 11 anchors are temporally out of scope at their `as_of` (disclosed in the paper and datasheet).

## Quickstart

```python
from datasets import load_dataset

chunks = load_dataset("datbazuka2502/vicivil-tkg", "corpus")["train"]
bench  = load_dataset("datbazuka2502/vicivil-tkg", "benchmark")["train"]

q = next(x for x in bench if x["qid"] == "CIV001")
print(q["qid"], q["as_of"], q["gold_ids"], q["gold_tier"])
# CIV001 2024-06-01 ['BLDS2015|Dieu27|Khoan1|Diema'] regolded
```

Every `gold_ids` entry resolves to a `chunk_id` in `data/civil_chunks.jsonl`, which carries `source_url`, `source_type`, `fetched` and the validity window. Score with strict `chunk_id` matching after filtering candidates by validity at the question's `as_of` (that protocol is TCR; `tools/reproduce.sh` re-derives all published ranks offline).

GPU-free reproduction of every published metric:

```bash
git clone https://github.com/ntd25022006q/vicivil-tkg.git
cd vicivil-tkg && pip install -r requirements.txt
bash tools/reproduce.sh
```

## Repository layout

```
data/civil_chunks.jsonl        13,151 chunks, provenance + validity windows
benchmark/                     451 questions (3 cohorts) + 226 quarantined + full trails
index/                         dense matrices + kv stores (768-d, embeddinggemma:300m)
provenance/                    temporal graph (37 windows/24 edges), law sources, quality
docs/annotation/               60-question human IAA kit + Cohen/Fleiss kappa script
docs/graph/                    RDF/JSON-LD exports + offline graph explorer
docs/report/                   paper (EN v1.1.0 + archived VI v1.0.1), LaTeX sources
src/                           all scoring/eval/rescore scripts (paths resolved at runtime)
tools/reproduce.sh             one-command, GPU-free verification of every metric
AUDIT_2026-11-01.md            data-integrity audit: reproduce-then-patch, 30 logged changes
SHA256SUMS                     hashes over the whole release tree
```

## The gold adjudication chain

```
controlled generation (qwen2.5:14b, as_of inside validity window, vector dedup)
  └─ two-tier audit: 8B judge → 14B judge + evidence   ──fail──▶ public quarantine
      └─ two-round re-anchoring (both rounds must confirm; 38 core golds, agreement 0.888)
          └─ pass-3 sweep (qwen3:14b) over 99 suspects, 3 guardrails
               66 gold-ok · 29 flagged · 3 re-anchored (+1 proposal blocked)
               last 2 "unverifiable" questions re-anchored in a separate recheck
          └─ independent agreement audit (60-q sample, seed 20261101): 0.571 / 0.571
```

Quarantined questions are **published, not hidden**: 136 round-1 + 90 round-2 (89 two-tier failures + 1 near-duplicate at cosine 0.9931), each with its rejection trail (`benchmark/extension2_flagged.json` and friends).

## Data integrity audit (v1.0.1)

The release passed a reproduce-then-patch audit: every metric was recomputed independently from per-question artifacts and only matching values were patched forward. Three real defects were found and fixed with full logs (`AUDIT_2026-11-01.md`, `CHANGES.json` — 30 changes): an adjudicated re-anchor that never reached the question file (TOP27031: gold at rank 31 instead of rank 1), an adjudication map that mixed recorded-but-never-applied gold sets into the applied set, and a stale `ctx_hit5` in the LLM rescore. After the patch: core Hit@5 0.808→0.811, MRR 0.659→0.662; extension metrics unchanged. We argue this kind of audit should be standard for public benchmarks.

## Known limitations (disclosed)

- Narrow domain: civil + civil-procedure law, Vietnamese only.
- 26 core questions are flagged and excluded from headline metrics; regolded strata are systematically harder — always read stratified numbers.
- The 60-question agreement audit is model-vs-model (0.571); the human IAA kit is released but expert review is still pending.
- 4 of 11 round-2 regolded anchors are temporally out of scope at their `as_of` (adjudicated legal bases, wrong validity window; disclosed, not silently re-anchored).
- Three MRR semantics (full-list / @10 / @30) are annotated per table; unification is planned.

## License & citation

Legal texts are public domain (Luật 104/2016/QH13, Luật 64/2025/QH15); curation (schema, IDs, benchmark) is **CC-BY-4.0**. Not legal advice.

```bibtex
@misc{viciviltkg2026,
  title     = {ViCivil-TKG: A Temporally Anchored Benchmark for Vietnamese Civil-Law
               Question Answering with Multi-Round Gold-Answer Adjudication},
  author    = {Nguyễn Tiến Đạt},
  year      = {2026},
  version   = {v1.1.0},
  url       = {https://huggingface.co/datasets/datbazuka2502/vicivil-tkg}
}
```

See `CITATION.cff` for the canonical machine-readable citation and `DATASHEET.md` for the full datasheet and changelog.
