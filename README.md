# ViCivil-TKG — Vietnamese Civil Law Temporal Knowledge Graph

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
![Release](https://img.shields.io/badge/release-v1.6.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Benchmark](https://img.shields.io/badge/benchmark-281_QA-green.svg)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-dataset-yellow.svg)](https://huggingface.co/datasets/datbazuka2502/vicivil-tkg)

A versioned, article-level temporal knowledge graph of Vietnamese civil law.
Every chunk carries a hierarchical ID (`Law|Dieu|Khoan|Diem`), every law carries
a validity interval, and succession/amendment relations are explicit edges mined
from official consolidation preambles — so the graph answers *"what did the law
say on date X?"*, which flat per-document corpora cannot.

## Key numbers (v1.6.0, all measured and released)

| Artifact | Size |
|---|---|
| Corpus chunks (Điều/Khoản/Điểm, 17 statutes 1996–2026) | **11,267** |
| Temporal graph (nodes / succession + amendment edges) | **33 laws / 21 edges** |
| Article-level units (`law_articles.json`) | **10,215** |
| Retrieval index (entities / in-corpus relation rows, 768-d vectors) | **14,099 / 20,311** |
| Benchmark (situational QA with gold chunk IDs) | **281** = 245 verified + 32 regolded + 4 author-verified |

Retrieval (hybrid BM25 + dense, RRF fusion, temporal filter, frozen `v1.2.3` scoring):
**Hit@1 0.452 · Hit@3 0.658 · Hit@5 0.726 · Hit@10 0.794 · MRR 0.569** (Hit@1 0.502 on the
245 verified questions). Adding `BAAI/bge-reranker-v2-m3` over 30 candidates lifts
**Hit@10 to 0.868** (MRR 0.594); all deltas significant (Wilcoxon *p* < 0.001, `provenance/significance.json`).

**Temporal-Constraint Reranking (TCR)** — the graph's validity windows participate directly in
retrieval: candidates whose law is not in force at the question's `as_of` are dropped before
ranking. On the repaired benchmark this lifts **Hit@1 0.409 → 0.530** over the hybrid baseline
and **0.445 → 0.609** over the reranked baseline (MRR 0.554 → 0.659 and 0.591 → 0.706; Wilcoxon
*p* < 2·10⁻¹⁵ both; raw numbers + ablations in `benchmark/tcr_sgb_result.json`). Disclosed
ablations: a recency bias toward the newest law version *hurts* (questions deliberately target
older in-force versions); citation-graph boosting is neutral at 1,506 edges.

`as_of` repair (transparent): 28/281 questions carried a date before their gold law took effect
(23 × 2026-era statutes with a default 2024 date; 5 × stale HNGD 2000 gold). Dates were moved
into the gold law's validity era — full audit trail in `benchmark/as_of_fixes.json`; after
repair **100% of golds are in force at their `as_of`**.

## Interactive artifacts

- **Temporal graph explorer** — single self-contained file, no build step, works offline:
  [`docs/graph/explorer.html`](docs/graph/explorer.html), live at
  <https://ntd25022006q.github.io/vicivil-tkg/graph/explorer.html>
  (AntV G6 5.1.1; as-of time slider 1996–2026, REPLACES succession spine, dashed
  amendment edges, per-law provenance drawer; timeline tab driven by
  [`docs/graph/law_timeline.vl.json`](docs/graph/law_timeline.vl.json), Vega-Lite 5.21).
- **Report** (Vietnamese, LaTeX, 16 pp.): [`docs/report/ViCivil-TKG_bao-cao.pdf`](docs/report/ViCivil-TKG_bao-cao.pdf), source [`docs/report/report.tex`](docs/report/report.tex).
- **CI**: `.github/workflows/verify.yml` re-runs the evaluation, re-measures the corpus,
  exports and validates the RDF graph, and rebuilds the viewer on every push — no GPU, no secrets.

## Reproduce without a GPU

```bash
git clone https://github.com/ntd25022006q/vicivil-tkg
cd vicivil-tkg
bash tools/reproduce.sh   # recomputes the benchmark from released files (BM25 in pure Python + stored vectors + RRF)
```

Same numbers as the table above; numpy optional. Verify integrity with `sha256sum -c SHA256SUMS`.

## Load the data

```python
from datasets import load_dataset
corpus = load_dataset("datbazuka2502/vicivil-tkg", "corpus")["train"]      # 11,267 rows
bench  = load_dataset("datbazuka2502/vicivil-tkg", "benchmark")["train"]   # 281 rows
```

## Repository layout

| folder | content |
|---|---|
| `data/` | 11,267 chunk rows at article/clause/point granularity (`chunk_id`, `law_id`, validity window, source URL/type, cleaned flags); frozen v10 backup; decontaminated LLM extraction |
| `benchmark/` | 281 situational questions with gold chunk IDs + `gold_tier`, per-question ranks, two-rater + regold audit trail, as-of repair log (`as_of_fixes.json`), TCR experiment (`tcr_sgb_result.json`), 50-item expert review package |
| `index/` | dense 768-d matrices (`embeddinggemma-300m`, L2-normed) for entities/relations + kv chunk maps (ADGR-style LawRetriever format) |
| `provenance/` | temporal graph (33 law windows, 21 edges), 1,506 CITE edges, lineage candidates with similarity bands, source audit, ablation + significance + faithfulness artifacts |
| `sources_official/` | 5 signed gazette PDFs (BLDS 1995/2005/2015, HNGD 2000, TNBTCNN 2017) used to verify the corpus |
| `src/`, `tools/` | full pipeline source (crawl → chunk → KG → index → eval → export) + reproducibility scripts |
| `docs/` | explorer, RDF/JSON-LD/GEXF exports, NCKH report (TeX + PDF) |

## Known limitations (disclosed, not hidden)

- 36/281 gold answers (32 regolded + 4 author-verified) not yet independently expert-reviewed;
  a ready-made 50-item review package ships in `benchmark/review_package_50.md`.
- ~500 item-level chunks have empty extraction text (numbered-item granularity); remaining
  article-numbering gaps are measured in `provenance/law_audit.json`.
- 603 near-duplicate chunk groups (identical statutory wording across law versions); measured
  top-5 collision impact on 10/281 questions; retrieval-time dedup rejected as rank-distorting.
- Vietnamese source frame only (English mirror planned). Not legal advice.

## Citation

Legal texts are public domain (Luật 104/2016/QH13; Luật 64/2025/QH15); the curation
(schema, IDs, benchmark) is CC-BY-4.0. See [`CITATION.cff`](CITATION.cff):

```bibtex
@misc{viciviltkg2026,
  title  = {ViCivil-TKG: A Temporal Knowledge Graph and Benchmark for Vietnamese Civil Law Retrieval},
  author = {ntd25022006q},
  year   = {2026},
  url    = {https://github.com/ntd25022006q/vicivil-tkg}
}
```

Issues: <https://github.com/ntd25022006q/vicivil-tkg/issues> · Dataset discussions:
<https://huggingface.co/datasets/datbazuka2502/vicivil-tkg/discussions>
