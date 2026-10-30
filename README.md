---
language:
- vi
license: cc-by-4.0
task_categories:
- question-answering
- text-retrieval
pretty_name: ViCivil-TKG (Vietnamese Civil Law Temporal KG)
size_categories:
- 10K<n<100K
tags:
- vietnamese
- legal
- temporal-knowledge-graph
- retrieval
- benchmark
- question-answering
configs:
- config_name: corpus
  data_files: data/civil_chunks.jsonl
- config_name: benchmark
  data_files:
  - benchmark/law_bench_200c.json
  - benchmark/law_bench_v1.json
- config_name: index
  data_files:
  - index/vdb_chunks.json
  - index/vdb_entities.json
  - index/vdb_relationships.json
  - index/kv_store_text_chunks.json
  - index/kv_store_entity_chunks.json
  - index/kv_store_relation_chunks.json
- config_name: provenance
  data_files:
  - provenance/temporal_graph.json
  - provenance/cite_edges.json
  - provenance/lineage_candidates.json
  - provenance/amend_candidates.json
  - provenance/law_sources.json
  - provenance/law_audit.json
  - provenance/ablation_AB.json
  - provenance/significance.json
  - provenance/qa_faith.json
  - provenance/ranks_hybrid.json
  - provenance/law_index_stats.json
---

# ViCivil-TKG v1.7.0 — Vietnamese Civil Law Temporal Knowledge Graph

Article-granularity temporal KG of 17 Vietnamese civil-law texts (1996–2026,
BLDS 1995/2005/2015 included) with a 281-question situational benchmark,
three-round verified gold labels, and an 8-file ADGR-style retrieval index.
Legal lookup questions are temporal — *"which article was in force on date X"* —
and this is the dataset that answers them, with explicit succession edges mined
from official consolidation preambles.

## What is inside

| folder | content |
|---|---|
| `data/` | 11,267 chunk rows at `Dieu`/`Khoan`/`Diem` granularity; per-row source URL + type; law validity window inherited by every chunk; decontaminated extraction (zero CJK/PUA glyphs by automated gate) |
| `benchmark/` | 281 situational questions with gold chunk ids + `gold_tier` (245 verified / 32 regolded / 4 author-verified), per-question ranks, model-audit cascade (8B full pass 162/281 accepted; 14B deep pass on the 120 flagged: 97 confirmed / 23 reversed) + regold trail, as-of repair log (`as_of_fixes.json`), TCR experiment (`tcr_sgb_result.json`), 50-item expert review package, end-to-end LLM RAG run (`rag_inputs.json`, `llm_rag_result.json`, `llm_rag_significance.json`) |
| `index/` | dense 768-d matrices (`embeddinggemma-300m`, L2-normed) for 14,099 entities / 20,311 in-corpus relation rows (+ 439 cross-version successor edges, sim ≥ 0.90) + kv chunk maps |
| `provenance/` | temporal graph (33 law windows + 21 amendment/succession edges), 1,506 CITE edges, lineage candidates with similarity bands, source audit, ablation + significance + faithfulness artifacts |
| `sources_official/` | 5 signed gazette PDFs (BLDS 1995/2005/2015, HNGD 2000, TNBTCNN 2017) used to verify the corpus |
| `docs/` | RDF/Turtle + JSON-LD + GEXF exports, offline HTML graph explorer, 18-page NCKH report (TeX + PDF) |

## Data fields

`corpus` (one JSON line = one chunk, 11,267 rows):

| field | type | meaning |
|---|---|---|
| `chunk_id` | str | `Law\|Dieu[\|Khoan[\|Diem[\|Muc]]]` — unique key, also the benchmark gold label |
| `law_id` | str | corpus law id used by the temporal graph |
| `dieu` `khoan` `diem` `muc` | str | article/clause/point/item numbers |
| `tieu_de` | str | article heading |
| `content` | str | decontaminated chunk text |
| `chars` | int | len(content) |
| `source_url` | str | source page (gazette or TVPL mirror) |
| `source_type` | str | official / mirror / official-copy / semi |
| `fetched` | date | crawl date of the source page |
| `valid_from` `valid_to` | date | law validity window inherited by the chunk (joined from `provenance/temporal_graph.json`, present on every row) |
| `cleaned_v11` | bool | footer/header strip flag — present (true) on the 367 stripped rows, absent elsewhere |

`benchmark` (281 rows):

| field | type | meaning |
|---|---|---|
| `qid` | str | question id |
| `question` | str | situational question (no article numbers mentioned) |
| `as_of` | date | temporal anchor for retrieval filtering |
| `gold_ids` | list[str] | gold chunk ids in `corpus` |
| `gold_tier` | str | verified / regolded / author-verified |
| `regolded_from` `hint` `reviewed` | str | audit trail |

## Example records

```json
{"chunk_id": "BLDS2015|Dieu1", "law_id": "BLDS2015", "dieu": "1",
 "tieu_de": "Phạm vi điều chỉnh",
 "content": "Bộ luật này quy định địa vị pháp lý, chuẩn mực pháp lý về cách ứng xử ...",
 "source_type": "official", "valid_from": "2017-01-01", "valid_to": null}
{"qid": "CIV001", "as_of": "2024-06-01",
 "question": "Con đẻ muốn đổi từ họ cha sang họ mẹ cần điều kiện gì?",
 "gold_ids": ["BLDS2015|Dieu27|Khoan1|Diema"], "gold_tier": "regolded"}
```

## Metrics (three published scoring rounds; per-question artifacts for each)

Hybrid retriever (BM25 + dense 768-d, RRF fusion, temporal filter), n = 281.

**Frozen v1.2.3 overview** (equivalence-group matching, live query encoder):
**Hit@1 0.452 / Hit@3 0.658 / Hit@5 0.726 / Hit@10 0.794, MRR 0.569.**
Stratified: verified 245 → 0.502/0.678/0.731/0.796; regolded 32 →
0.062/0.531/0.719/0.812; author-verified 4 → 0.5/0.5/0.5/0.5.
**Strict exact-ID chain** (stored vectors; every TCR/SGB/LLM number below uses it):
baseline Hit@1 0.409 / Hit@5 0.729 / Hit@10 0.819, MRR 0.554; adding
`BAAI/bge-reranker-v2-m3` (30 candidates/question): Hit@1 0.445 / Hit@10 **0.868**,
MRR 0.591 (paired Wilcoxon over per-question MRR p = 0.034; ranks in
`benchmark/rerank_result.json`). Historical live-encoder rerank run: MRR 0.594
(from 0.550) — same protocol family, kept for cross-check.

**No-GPU reproduction** (`bash tools/reproduce.sh`, `benchmark/law_eval_repro.json`):
Hit@1 0.402 / Hit@5 0.730 / Hit@10 0.819, MRR 0.545 — Hit@5/Hit@10 identical to the
strict chain; Hit@1 sits 0.7 pp under the strict baseline (0.409) from stored-vector
precision and RRF tie order, and 5.0 pp under the frozen overview (0.452) additionally
because of the scoring rule (equivalence-groups vs exact-ID).

**Temporal-Constraint Reranking (TCR)** — dropping candidates whose law is not in force at the
question's `as_of` (the graph's validity windows acting on retrieval) lifts Hit@1 0.409 → 0.530
over the hybrid baseline and 0.445 → 0.609 over the reranked baseline (MRR 0.554 → 0.659 and
0.591 → 0.706; Wilcoxon p < 2·10⁻¹⁵ both). Raw numbers + ablations (recency bias hurts;
citation-graph boost neutral at 1,506 edges) in `benchmark/tcr_sgb_result.json`.

**End-to-end LLM RAG validation** — feeding each question through a small local LLM (Qwen2.5-3B-Instruct, greedy decode, deterministic) shows the TCR retrieval gain transfers to answers: article-citation accuracy 0.488 → 0.594 when the RAG context is temporally filtered (+10.7 pts, McNemar p = 1.3·10⁻⁴; Span-F1 +2.3 pts, Wilcoxon p = 9.4·10⁻⁵), while closed-book cites correctly only 0.4% of the time and abstains 55% of it. Context Hit@5 values reproduce the published retrieval numbers exactly (0.729 / 0.811 / 0.846). The rerank+TCR condition covers 280/281 questions: for NEW90253 the stored Track-B rerank pool is empty after strict temporal filtering (no candidate in force at its as_of), so it is skipped by protocol. Per-question answers in `benchmark/llm_rag_result.json`, paired tests in `benchmark/llm_rag_significance.json`, exact RAG contexts in `benchmark/rag_inputs.json`. Data-quality note: answers are stored verbatim and occasionally contain CJK code-switching from the 3B model — 11/281 (3.9%) closed-book, 3/281 (1.1%) RAG, 5/281 (1.8%) RAG+TCR, 2/280 (0.7%) rerank+TCR — a Vietnamese RAG context cuts code-switching roughly 4x; nothing was edited post-hoc.

**`as_of` repair (transparent):** 28/281 questions carried a date before their gold law took
effect (23 × 2026-era statutes with a default 2024 date; 5 × stale HNGD 2000 gold). Dates were
moved into the gold law's validity era — full audit trail in `benchmark/as_of_fixes.json`.
After repair, 100% of golds are in force at their `as_of`. Recompute everything with
`bash tools/reproduce.sh` (GitHub repo) — pure Python 3.9+, no GPU.

## How gold labels were made (protocol)

1. Chunk-level generation with an 8B open model + junk filters (production prompts; no target-law content leaked).
2. Two-rater hostility audit: 8B model on the full bench, 14B model on the 120 doubtfuls; 57 rejects → 16 gold re-anchors with provenance (`regolded_from`).
3. Author adjudication for weak/partial labels → rescoped questions, 4 verified stubs, 1 documented drop (`dropped_log.json`). No gold without an audit trail.

## Known limitations (disclosed, not hidden)

- 36/281 answers (32 regolded + 4 author-verified) not yet independently expert-reviewed;
  `benchmark/review_package_50.md` is ready for external raters.
- 0 empty-content chunks; 424 item-level chunks carry short extraction text (`law_audit.json`: `empty`=0, `short_n`=424); remaining numbering gaps measured in `provenance/law_audit.json`.
- 603 near-duplicate chunk groups across law versions (identical statutory wording); measured top-5 collision impact: 10/281 questions.
- Vietnamese source frame only; English mirror planned. Not legal advice.

## How to load

```python
from datasets import load_dataset
corpus = load_dataset("datbazuka2502/vicivil-tkg", "corpus")["train"]
bench  = load_dataset("datbazuka2502/vicivil-tkg", "benchmark")["train"]

# index + provenance as raw JSON
from huggingface_hub import snapshot_download
p = snapshot_download("datbazuka2502/vicivil-tkg", repo_type="dataset")
import json
chunks = [json.loads(l) for l in open(f"{p}/data/civil_chunks.jsonl")]
```

Index files need `law_adgr.py` (ADGR-style LawRetriever) — shipped in the
[GitHub repo](https://github.com/ntd25022006q/vicivil-tkg), which also runs the
verification CI on every push and serves the offline graph explorer via GitHub Pages.
All released files passed a 12-section audit (manifest completeness, JSON parse-all,
matrix shapes, gold chain, extraction coverage, secret scan, schema fields, duplicate
accounting, law-window sanity, kv refs, weird-character gate, id-set equality) and
carry SHA-256 checksums (`SHA256SUMS`).

## Contact

- GitHub issues: https://github.com/ntd25022006q/vicivil-tkg/issues
- Dataset: HF "Community" tab on this page

## License & attribution

- Legal texts: public domain (Luật 104/2016/QH13; Luật 64/2025/QH15).
- Curation (schema, IDs, benchmark): CC-BY-4.0 — cite as:

```bibtex
@misc{viciviltkg2026,
  title  = {ViCivil-TKG: A Temporal Knowledge Graph and Benchmark for
            Vietnamese Civil Law Retrieval},
  author = {ntd25022006q},
  year   = {2026},
  url    = {https://huggingface.co/datasets/datbazuka2502/vicivil-tkg}
}
```
