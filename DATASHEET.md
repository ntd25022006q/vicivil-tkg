# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG)

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*
- Expert review of 50 sampled items is pending (flagged in
  `review_package_50.md`); until then treat gold labels as LLM+author
  adjudicated, not expert-verified.

## Composition
- **Chunks:** 13.151 (law|dieu[|khoan|diem|muc] IDs) across **20 laws**
  (1995–2026, including the 1996–2015 era additions: BLTTHS 2004,
  NĐ 158/2005 hộ tịch, NĐ 126/2014 HNGD guide); every chunk carries
  source_url + source_type + `fetched` + its law's `[valid_from, valid_to)`
  window. 2 chunks converted from a damaged government `.doc` produced binary
  mojibake and were dropped (logged in `dropped_log.json`; referenced by no
  question). BLDS 1995 is clause-level from the signed PDF.
- **Extraction:** the original 11.267 rows carry LLM entities/relations
  (qwen25-awq temp 0 + validators; 97 re-extracted with qwen3:14b, per-row
  `engine` field). The 1.886 round-2 rows are stored as cleaned raw text and
  are NOT part of the entity/relation index yet (disclosed; retrieval uses
  their chunk vectors, which ARE in `index/vdb_chunks.json`).
- **Index (8-file ADGR-style):** 14.099 entities / 20.750 relation rows
  (incl. DAN-CHIEU edges) + chunk/entity/relation dense matrices (768-d,
  embeddinggemma:300m, L2-normed). The chunk matrix covers all 13.151 rows.
- **Temporal graph:** 37 law windows + 24 succession/amendment edges with
  dates; chunks inherit law validity; abstain probes retained
  (1990 empty-pool + missing-law cases).
- **Benchmark:** **451 published questions** in three cohorts:
  281 core (269 generated + 12 hand-written CIV001–CIV012), 106 round-1
  extension (101 verified + 5 regolded), 64 round-2 extension from the
  1996–2015 statutes (53 verified + 11 regolded). **226 quarantined
  questions** (136 + 90) are published verbatim with audit trails and count
  in no metric. Core gold tiers after the full adjudication chain:
  **229 verified / 21 regolded / 4 author-verified / 27 pass3-flagged**
  (flagged disclosed with reasons, excluded from headline metrics), and
  **0 unverifiable** questions remain. Dev/test split 140/141 (stratified).

### Adjudication chain (all trails in `benchmark/`)
1. Two-tier audit at generation time (8B judge → 14B deep re-audit with
   evidence) — failures quarantined.
2. Two-round re-anchoring: a replacement chunk is accepted only when both
   judge rounds confirm (38 core golds re-anchored this way).
3. Pass-3 (qwen3:14b): 99 weak-gold suspects re-checked → 66 gold-ok /
   29 flagged / 4 re-anchored, with guardrails (chunk exists · appears in
   stored candidates · inside the as_of validity window; 1 proposal
   rejected by the guardrails). The last 2 previously-unverifiable questions
   were both successfully re-anchored in this pass.
4. Independent agreement audit on a fixed 60-question sample (seed 20261101):
   gold-set agreement 0.554, primary-chunk agreement 0.571 (56/60 parse OK).
   This is a model-vs-model check and does NOT replace human review.
5. Round-2 cohort added a cross-cohort near-duplicate scan (cos > 0.95 vs all
   387 published questions): 1 near-duplicate (cos 0.9931) caught and
   quarantined (`extension2_dedup_audit.json`).

## Data fields (schema)

`data/civil_chunks.jsonl` — one JSON object per line, 13.151 rows:

| field | type | meaning |
|---|---|---|
| `chunk_id` | str | hierarchical ID `Law\|Dieu[\|Khoan[\|Diem[\|Muc]]]` (unique key) |
| `law_id` | str | corpus law identifier used by the temporal graph |
| `dieu` / `khoan` / `diem` / `muc` | str | article/clause/point/item part numbers |
| `tieu_de` | str | article heading as in the official text |
| `content` | str | decontaminated chunk text |
| `chars` | int | len(content) |
| `source_url` | str | URL of the used source page (Cong-bao or TVPL mirror) |
| `source_type` | str | `official` / `mirror` / `official-copy` / `semi` |
| `fetched` | date | crawl date of the source page |
| `valid_from` / `valid_to` | date | law validity `[from, to)` (present on every row) |
| `header_footer_cleaned` | bool | decontamination flag (367 stripped rows) |

`benchmark/law_bench_*.json` — question objects:

| field | type | meaning |
|---|---|---|
| `qid` | str | question id (CIV/GEN/NEW/TOP/EXT prefix by cohort) |
| `question` | str | situational natural-language question |
| `as_of` | date | the "what did law say then" date used for temporal filtering |
| `gold_ids` | list[str] | gold chunk ids referencing `civil_chunks.jsonl` |
| `gold_tier` | str | `verified` / `regolded` / `author-verified` / `flagged` |
| `regolded_from` | list[str] | original gold before re-anchoring (tier=regolded) |
| `hint`, `reviewed`, `weak_review` | str | adjudication trail fields |

## Metrics (current frozen snapshot; every number reproducible from artifacts)
- **Core retrieval, hybrid BM25+dense+RRF with TCR** (documented protocol,
  `law_ranks_full_rebuild.py verify` reproduces the published ranking with
  0 mismatches): full n=281 → Hit@1 0.537 / Hit@3 0.737 / Hit@5 0.808 /
  Hit@10 0.875 / MRR 0.659. Stratified: verified (229) 0.585/0.760/0.821/0.895
  MRR 0.693; regolded (21) 0.238/0.762/0.857/0.905; author-verified (4)
  0.250/0.500/0.750/0.750; pass3-flagged (27) 0.407/0.556/0.667/0.704
  (excluded from headline averages).
- **No-TCR hybrid repro** (`law_eval_repro.json`, no GPU, no network):
  Hit@1 0.395 / Hit@5 0.730 / Hit@10 0.811 / MRR 0.536 — the TCR gap is the
  temporal-filtering contribution.
- **Gold-adjudication effect** (same stored rerank/hybrid candidate lists,
  old vs adjudicated gold): rerank Hit@1 0.448→0.484, Hit@5 0.794→0.808,
  MRR 0.596→0.621; hybrid Hit@1 0.406→0.441, MRR 0.548→0.571.
- **Core LLM RAG** (Qwen2.5-3B-Instruct, greedy, rescored from stored answers
  after gold updates): cite_acc No-RAG 0.004 → hybrid 0.488 → hybrid+TCR
  **0.601** (McNemar p = 5.8e-05) → rerank+TCR 0.600 (ctx_hit5 0.846);
  No-RAG vs hybrid+TCR p = 5.3e-51.
- **Round-1 extension** (n=106): retrieval Hit@5 0.906 → 0.925 with TCR
  (Wilcoxon p = 2.1e-05).
- **Round-2 extension, 1996–2015 (n=64):** retrieval Hit@5 0.703 → 0.781 with
  TCR (p = 4.0e-05) → 0.828 with rerank+TCR (Hit@1 0.703, p = 1.4e-03);
  LLM cite_acc 0.000 → 0.531 with TCR (McNemar p = 1.2e-10). Stratified
  tiers published; the regolded stratum (11 Qs) is the hardest slice of the
  whole benchmark (Hit@1 0.091).

## Collection & preprocessing
- **Sources:** signed Cong-bao PDFs + official government .doc + TVPL
  official pages; mirrors only where no official equivalent exists
  (`provenance/law_sources.json` records source_url/type/fetched per law).
- **Decontamination:** three documented rounds on the original corpus
  (footer/header strip, duplicate-id removal, .doc piece-table rebuilds,
  stray-glyph re-extraction). Round-2 ingestion applied the same gates; two
  mojibake chunks were dropped instead of repaired (unreferenced).
- **Lineage & cross-refs:** per-Dieu cosine lineage BLDS 1995→2005→2015 and
  1.506 intra-law CITES edges (as DAN-CHIEU relations) unchanged from the
  v1.0.0 corpus build.

## Artifacts in this release
- `data/civil_chunks.jsonl` (13.151 rows), 6 index files + 3 kv stores,
  `provenance/temporal_graph.json` (37 windows, 24 edges), `law_sources.json`.
- Core benchmark + full trail (`regold*.json`, `fixall.json`, `as_of_fixes.json`,
  `gold_adjudicated.json`, `gold_pass3.json`, `weak_gold_reanchor.json`,
  `dropped_log.json`, `bench_split.json`).
- Extension round 1: questions + vectors + audit trail + eval artifacts
  (`law_bench_extension.json`, `extension_flagged.json`, ...).
- Extension round 2: `law_bench_extension2.json` + `extension2_*` audit,
  dedup, vectors, ranks, rerank and LLM-QA artifacts.
- Paper: `docs/report/ViCivil-TKG_paper.pdf` (IMRaD, LaTeX source in
  `docs/report/paper.tex`).
- `SHA256SUMS` regenerated over the full release tree; `audit_release.py`
  verifies structure, counts, hashes and placeholder/secret scans.

## Known gaps (disclosed)
- Single domain (civil + civil-procedure law), Vietnamese only.
- 27 core questions pass3-flagged; the regolded strata are systematically
  harder (low Hit@1, high Hit@5) — always read stratified numbers.
- Independent judge agreement on the 60-question sample is 0.554 — gold
  anchoring in this domain is genuinely ambiguous; human expert review
  (50-question package) is the top-priority next step.
- The 1.886 round-2 chunk rows are not yet mined for entities/relations
  (retrieval-ready, KG-pending).
- GitHub PAT rotation still pending (owner accepted the residual risk);
  no secret is stored in any released file (pattern-scanned).

## Uses, distribution, maintenance
- **License:** legal texts public domain (Luật 104/2016/QH13, Luật
  64/2025/QH15); curation (schema, IDs, benchmark) CC-BY-4.0.
- **Update protocol:** monthly gazette sweep; amended articles close
  valid_to + open new edges (never rewrite history).

## Changelog

- **2026-10-31 (data update within v1.0.0):** corpus 11.267→13.151 chunks,
  17→20 laws (1996–2015 era statutes added); benchmark 281→451 published
  questions (+226 quarantined with trails); pass-3 adjudication completed
  (0 unverifiable golds left); cross-cohort dedup audit added; documented
  hybrid+TCR retrieval protocol with 0-mismatch verification; all metrics
  recomputed; NCKH paper (IMRaD) replaces the previous technical report.
- **v1.0.0:** first public release (corpus, temporal KG, index, 281-question
  benchmark with full verification trail, retrieval + LLM RAG baselines,
  offline graph explorer). All numbers reproducible from the repository
  alone, without GPU or network.
