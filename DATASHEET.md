# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG)

Version 1.1.0 (2026-11-01). This datasheet documents the released artifacts;
every number is machine-checkable against `benchmark/` and re-verified by
`src/verify_paper_numbers.py` and the paper's audit trail.

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*
- Expert review of a stratified 60-item kit (`docs/annotation/`, with
  Cohen/Fleiss κ scripts) is pending; until then treat gold labels as
  LLM+author adjudicated, not expert-verified.

## Composition
- **Chunks:** 13,151 (law|dieu[|khoan|diem|muc] IDs) across **20 laws**
  (1995–2026, including the 1996–2015 era additions: BLTTHS 2004,
  NĐ 158/2005 hộ tịch, NĐ 126/2014 HNGD guide); every chunk carries
  source_url + source_type + `fetched` + its law's `[valid_from, valid_to)`
  window. 2 chunks converted from a damaged government `.doc` produced binary
  mojibake and were dropped (logged in `dropped_log.json`; referenced by no
  question). BLDS 1995 is clause-level from the signed PDF.
- **Extraction:** the original 11,267 rows carry LLM entities/relations
  (qwen25-awq temp 0 + validators; 97 re-extracted with qwen3:14b, per-row
  `engine` field). The 1,884 round-2 rows stored in the release (1,886
  ingested; the two mojibake rows above were dropped) are stored as cleaned
  raw text and are NOT part of the entity/relation index yet (disclosed;
  retrieval uses their chunk vectors, which ARE in `index/vdb_chunks.json`).
- **Index (8-file ADGR-style):** 14,099 entities / 20,750 relation rows
  (incl. DAN-CHIEU edges) + chunk/entity/relation dense matrices (768-d,
  embeddinggemma:300m, L2-normed). The chunk matrix covers all 13,151 rows.
- **Temporal graph:** 37 law windows + 24 succession/amendment edges with
  dates; chunks inherit law validity; abstain probes retained
  (1990 empty-pool + missing-law cases).
- **Benchmark:** **451 published questions** in three cohorts:
  281 core (269 generated + 12 hand-written CIV001–CIV012), 106 round-1
  extension (101 verified + 5 regolded), 64 round-2 extension from the
  1996–2015 statutes (53 verified + 11 regolded). **226 quarantined
  questions** (136 + 90) are published verbatim with audit trails and count
  in no metric. Core gold tiers after the full adjudication chain:
  **229 verified / 22 regolded / 4 author-verified / 26 pass3-flagged**
  (flagged disclosed with reasons, excluded from headline metrics), and
  **0 unverifiable** questions remain. Dev/test split 140/141 (stratified).

### Adjudication chain (all trails in `benchmark/`)
1. Two-tier audit at generation time (8B judge → 14B deep re-audit with
   evidence) — failures quarantined.
2. Two-round re-anchoring: a replacement chunk is accepted only when both
   judge rounds confirm (38 core golds re-anchored this way, two-round
   agreement 0.888).
3. Pass-3 (qwen3:14b): 99 weak-gold suspects re-checked → verdicts 66 gold-ok
   / 29 flagged / 3 re-anchored (plus 1 proposal rejected by a guardrail —
   not in the stored candidate pool), each application guarded by
   (chunk exists · appears in stored candidates · inside the as_of validity
   window). The last 2 previously-unverifiable questions were both
   successfully re-anchored in this pass. (v1.0.1: the TOP27031 re-anchor is
   also persisted to the question files; before the fix it lived only in
   `gold_adjudicated.json`.) After the audit's human-overrule and persist
   steps, the final core tier structure is 229/22/4/26 as stated above.
4. Independent agreement audit on a fixed 60-question sample (seed 20261101):
   gold-set agreement 0.571, primary-chunk agreement 0.571 (56/60 parse OK;
   measured against the applied golds — 0.554 if the 24 recorded-but-
   never-applied gold sets are counted, see `gold_adjudicated.json`).
   This is a model-vs-model check and does NOT replace human review.
5. Round-2 cohort added a cross-cohort near-duplicate scan (cos > 0.95 vs all
   387 published questions): 1 near-duplicate (cos 0.9931) caught and
   quarantined (`extension2_dedup_audit.json`).

## Data fields (schema)

`data/civil_chunks.jsonl` — one JSON object per line, 13,151 rows:

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
  `law_ranks_full_rebuild.py verify` reproduced the published ranking with
  0 mismatches before the v1.0.1 gold fix): full n=281 → Hit@1 0.541 /
  Hit@3 0.740 / Hit@5 0.811 / Hit@10 0.879 / MRR 0.662 (full-list MRR).
  Stratified: verified (229) 0.585/0.760/0.821/0.895 MRR 0.693; regolded (22)
  0.273/0.773/0.864/0.909; author-verified (4) 0.250/0.500/0.750/0.750;
  pass3-flagged (26) 0.423/0.577/0.692/0.731 (excluded from headline
  averages).
- **No-TCR hybrid repro** (`law_eval_repro.json`, no GPU, no network):
  Hit@1 0.399 / Hit@5 0.733 / Hit@10 0.815 / MRR 0.540 (MRR@10 window) —
  the TCR gap is the temporal-filtering contribution.
- **Gold-adjudication effect** (same stored 30-candidate rerank/hybrid
  lists, applied gold before vs after persisting the TOP27031 pass-3
  re-anchor): rerank Hit@5 0.794→0.797, MRR 0.5957→0.5964; hybrid Hit@1
  0.406→0.409, Hit@5 0.737→0.740, MRR 0.548→0.552. Sensitivity row kept for
  continuity: scoring against the 24 recorded-but-never-applied gold sets
  gives rerank Hit@1 0.484 / MRR 0.621 (`gold_adjudicated_metrics.json:
  recorded_sets_*`).
- **Core LLM RAG** (Qwen2.5-3B-Instruct, greedy, rescored from stored answers
  after gold updates): cite_acc No-RAG 0.004 → hybrid 0.488 → hybrid+TCR
  **0.601** (McNemar p = 5.8e-05) → rerank+TCR 0.604 (ctx_hit5 0.850,
  recomputed against the applied golds in v1.0.1); No-RAG vs hybrid+TCR
  p = 5.3e-51.
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
  1,506 intra-law CITES edges (as DAN-CHIEU relations) unchanged from the
  v1.0.0 corpus build.

## Artifacts in this release
- `data/civil_chunks.jsonl` (13,151 rows), 6 index files + 3 kv stores,
  `provenance/temporal_graph.json` (37 windows, 24 edges), `law_sources.json`.
- Core benchmark + full trail (`regold*.json`, `fixall.json`, `as_of_fixes.json`,
  `gold_adjudicated.json`, `gold_pass3.json`, `weak_gold_reanchor.json`,
  `dropped_log.json`, `bench_split.json`).
- Extension round 1: questions + vectors + audit trail + eval artifacts
  (`law_bench_extension.json`, `extension_flagged.json`, ...).
- Extension round 2: `law_bench_extension2.json` + `extension2_*` audit,
  dedup, vectors, ranks, rerank and LLM-QA artifacts.
- Paper: `docs/report/ViCivil-TKG_paper_v1.1.0_en.pdf` (English edition,
  IMRaD, LaTeX source `docs/report/paper_en.tex`); the Vietnamese v1.0.1
  edition remains archived in `docs/report/`.
- `SHA256SUMS` regenerated over the full release tree; the integrity-audit
  record (`AUDIT_2026-11-01.md`, `CHANGES.json`) documents every v1.0.1
  data fix with before/after values.

## Known gaps (disclosed)
- Single domain (civil + civil-procedure law), Vietnamese only.
- 26 core questions pass3-flagged; the regolded strata are systematically
  harder (low Hit@1, high Hit@5) — always read stratified numbers.
- Independent judge agreement on the 60-question sample is 0.571 — gold
  anchoring in this domain is genuinely ambiguous; human expert review
  (60-item kit, `docs/annotation/`) is the top-priority next step.
- The 1,884 released round-2 chunk rows are not yet mined for
  entities/relations (retrieval-ready, KG-pending).
- **Temporal scope of 4 round-2 anchors (v1.1.0 disclosure):** EXT20028,
  EXT20039, EXT20113 and EXT20123 (4 of the 11 round-2 `regolded` anchors)
  are out of scope at the question's `as_of`: three (EXT20028, EXT20039,
  EXT20113) point to consolidated texts whose validity window starts
  *after* `as_of`, while EXT20123 points to a BLDS 1995 passage whose
  validity window ended on 2006-01-01, six years before its 2012 `as_of`.
  Each anchor was accepted by the adjudication chain as the legal basis of
  the underlying question, but all four fall outside the validity windows
  at the stated dates, so TCR filtering excludes them by construction;
  they contribute to the low regolded-stratum Hit@1 (0.091). We disclose
  rather than silently re-anchor a second time.
- Three MRR semantics coexist (full-list / MRR@10 / MRR@30) and are
  annotated per table; unifying them is a planned technical task.
- GitHub PAT rotation still pending (owner accepted the residual risk);
  no secret is stored in any released file (pattern-scanned).

## Uses, distribution, maintenance
- **License:** legal texts public domain (Luật 104/2016/QH13, Luật
  64/2025/QH15); curation (schema, IDs, benchmark) CC-BY-4.0.
- **Update protocol:** monthly gazette sweep; amended articles close
  valid_to + open new edges (never rewrite history).

## Changelog

- **2026-11-01 (v1.1.0, paper + release hardening):** English conference-style
  paper (v1.1.0) replaces the Vietnamese v1.0.1 as the reference paper
  (measurements unchanged, decimal-point notation; new disclosure of the 4
  round-2 anchor-window cases above); professional README rewritten for HF
  and GitHub; the v1.0.1 patched benchmark artifacts (previously shipped only
  as a side-by-side patch directory) are now THE canonical files in
  `benchmark/`; CITATION.cff bumped to 1.1.0 with the English preferred
  citation; `tools/reproduce.sh` step 7 fixed (an empty-string command made
  the published GPU-free reproduction abort); the four-anchor disclosure
  corrected (EXT20123 is an expired BLDS-1995 window, not a not-yet-effective
  consolidation) and the round-2 stored-row count corrected to 1,884 released
  of 1,886 ingested; `src/law_llm_rag_rescore.py`
  replaced by the v1.0.1 F6 logic (recomputes ctx_hit5 from
  `rag_inputs.json` — re-running the old chain step would have regressed the
  published 0.740/0.815/0.850); release verifiers now exit non-zero on
  failure (previously several printed "OK" unconditionally).
- **2026-11-01 (v1.0.1 integrity audit):** persisted the TOP27031 pass-3
  re-anchor to the question files (tier flagged→regolded; 27/21 flagged/
  regolded became 26/22); rescored core retrieval/repro/LLM metrics against
  the applied golds and recomputed stale run-time `ctx_hit5`; moved the 24
  recorded-but-never-applied gold sets in `gold_adjudicated.json` to
  `proposals_not_applied`; rebuilt the human IAA kit (`docs/annotation/`)
  with complete `as_of` fields and gold synced to the applied golds. No
  question text, corpus row or cohort size changed. *Erratum (v1.1.0):*
  the `CHANGES.json` B4 record states the review-sheet fix as "rows with
  gold != applied gold: old 8 -> new 7"; direct measurement gives a pre-fix
  count of **7** and a shipped kit with **0** such rows (the recorded "8"
  and intermediate "7" are stale counts from during the fix — the shipped
  files are correct, only that log line is off).
- **2026-10-31 (data update within v1.0.0):** corpus 11,267→13,151 chunks,
  17→20 laws (1996–2015 era statutes added); benchmark 281→451 published
  questions (+226 quarantined with trails); pass-3 adjudication completed
  (0 unverifiable golds left); cross-cohort dedup audit added; documented
  hybrid+TCR retrieval protocol with 0-mismatch verification; all metrics
  recomputed; NCKH paper (IMRaD) replaces the previous technical report.
- **v1.0.0:** first public release (corpus, temporal KG, index, 281-question
  benchmark with full verification trail, retrieval + LLM RAG baselines,
  offline graph explorer). All numbers reproducible from the repository
  alone, without GPU or network.
