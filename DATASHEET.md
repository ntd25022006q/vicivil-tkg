# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG v1.0.0)

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*
- Expert review of 50 sampled items is pending (flagged in
  `review_package_50.md`); until then treat gold labels as LLM+author
  adjudicated, not expert-verified.

## Composition (v1.0.0)
- **Chunks:** 11.267 (law|dieu[|khoan|diem|muc] IDs) across 17 laws;
  sources: official 6.141 / mirror 4.476 / official-copy 266 / semi 391,
  each chunk carries source_url + source_type + (where applicable)
  `header_footer_cleaned=true` footer-strip flag. BLDS 1995 re-parsed to clause level
  from the signed PDF (1.896 chunks: Dieu or Dieu|Muc{0..k}).
- **Extraction:** 11.267 chunk rows with entities/relations/deterministic
  DAN-CHIEU refs extracted on the decontaminated text (qwen25-awq,
  temp 0, few-shot + validators). 97 chunks were later re-extracted with
  qwen3:14b via Ollama (9 stub-rescues, then 94 rows whose
  stored text or extraction contained residual corruption) — engine
  heterogeneity for those rows is recorded per-row (`engine` field);
  extraction covers 11.267/11.267 rows with zero failed chunks.
- **Index (8-file ADGR-style):** 14.099 entities (10 legal types) / 20.311
  relations incl. chunk-chunk DAN-CHIEU edges (+439 cross-version
  successor edges appended separately, totalling 20.750 relation rows)
  mined by embedding similarity (sim >= 0.90, 0.80-0.90 band retained for
  manual review only) / chunk + entity + relation dense matrices (768-d,
  embeddinggemma:300m, L2-normed). Index content mirrors chunk text with a
  disclosed [:3000] char cap for BM25/representation — full text stays in
  `civil_chunks.jsonl`.
- **Temporal:** 17 laws [valid_from, valid_to) + 16 external amending laws;
  21 edges (4 succession + 17 AMENDS) with dates; chunks inherit law
  validity; abstain tested (1990 empty-pool + missing-law probes).
- **Benchmark:** 281 situational Qs (271 dev+syn + 12 hand) + no gold
  weak/partial tiers left: 245 verified / 32 regolded (same-Q better-chunk
  with `regolded_from` provenance) / 4 author-verified stubs; 1 question
  dropped with written reason (`dropped_log.json`); model-audit cascade trail
  (8B full bench: 162/281 accepted; 14B re-audit of the 120 flagged:
  97 confirmed / 23 reversed) in `second_rater*.json`, `regold.json`,
  `fixall.json`; 50-Q expert review package still pending.

### Per-law size table (chunk counts, v1.0.0)

| law_id | chunks | law_id | chunks |
|---|---:|---|---:|
| van-ban-hop-nhat-so-21 (BLTTHS-VBHN, official PDF) | 1.979 | TNBTCNN-2017 (official mirror) | 505 |
| BLDS 1995 (clause-level, official PDF) | 1.890 | HNGD 2014 (Hôn nhân gia đình) | 393 |
| BLDS 2015 (official mirror) | 1.838 | HNGD-VBHN 2025 | 392 |
| BLDS 2005 (official mirror) | 780 | Hộ tịch 2014 (official copy) | 266 |
| THADS-VBHN (MOJ official file) | 758 | HNGD 2000 (mirror) | 239 |
| THA dân sự 2008 (mirror) | 721 | NCN 2010 (gov .doc) | 208 |
| ND 152/2026-ND-CP (official PDF) | 665 | HOAGIAI2026 (công báo PDF) | 175 |
| Luật số 15/2026/QH16 (công báo PDF) | 151 | Hộ tịch 2026 (công báo PDF) | 172 |
| TT liên tịch 07/2026 (công báo PDF) | 135 | | |

## Data fields (schema)

`data/civil_chunks.jsonl` — one JSON object per line, 11.267 rows:

| field | type | meaning |
|---|---|---|
| `chunk_id` | str | hierarchical ID `Law\|Dieu[\|Khoan[\|Diem[\|Muc]]]` (unique key) |
| `law_id` | str | corpus law identifier used by the temporal graph |
| `dieu` / `khoan` / `diem` / `muc` | str | article/clause/point/item part numbers |
| `tieu_de` | str | article heading as in the official text |
| `content` | str | decontaminated chunk text (full text, mirror includes same) |
| `chars` | int | len(content), schema-normalized |
| `source_url` | str | URL of the used source page (Cong-bao or TVPL mirror) |
| `source_type` | str | `official` / `mirror` / `official-copy` / `semi` |
| `fetched` | date | crawl date of the source page |
| `valid_from` / `valid_to` | date | law inheritance of `[from, to)` validity (joined from the temporal graph, present on every row) |
| `header_footer_cleaned` | bool | footer/header decontamination flag — present (true) on the 367 stripped rows, absent elsewhere |
| `muc` | str | item part for BLDS 1995 clause-level rows |

`benchmark/law_bench_*.json` — 281 question objects in two files:

| field | type | meaning |
|---|---|---|
| `qid` | str | question id (CIV-prefix) |
| `question` | str | situational natural-language question |
| `as_of` | date | the "what did law say then" date used for temporal filtering |
| `gold_ids` | list[str] | gold chunk ids referencing `civil_chunks.jsonl` |
| `gold_tier` | str | `verified` / `regolded` / `author-verified` |
| `regolded_from` | list[str] | original gold before re-anchoring (when tier=regolded) |
| `hint`, `reviewed` | str | adjudication trail (rater notes, reviewer pass) |

`index/` — dense matrices store `embedding_dim: 768`, a base64 `matrix`
(float32, row-major, L2-normed) and a parallel `data` list of
`{__id__, content[, src_id, tgt_id, ...]}` rows; the three `kv_store_*.json`
map object ids to their referenced `chunk_ids`.

## Metrics (measured on the frozen retrieval index; unchanged by the
  final hygiene pass, which stripped 12 invisible codepoints with no
  content change)
- Full bench n=281: Hit@1 0.452 / Hit@3 0.658 / Hit@5 0.726 / Hit@10 0.794
  / MRR 0.569. Re-evaluated on the sanitized frozen index and confirmed
  parseable. The no-GPU re-run (`law_eval_repro.json`, strict exact-ID + stored
  vectors) reproduces the chain at Hit@1 0.402 / Hit@5 0.730 / Hit@10 0.819 /
  MRR 0.545 — Hit@5/Hit@10 identical to the strict TCR chain; Hit@1 sits 0.7 pp
  under the strict baseline (0.409) from vector precision and RRF tie order, and
  5.0 pp under this frozen overview (0.452) additionally from the scoring rule
  (equivalence-groups vs exact-ID). Per-question artifacts ship for all rounds.
- Stratified by gold_tier: verified 245 -> 0.502/0.678/0.731/0.796;
  regolded 32 -> 0.062/0.531/0.719/0.812 (deliberately hard restatements:
  answer lives in a target chunk not reachable by surface wording, but
  rank-10 recall 0.812 shows the index finds it — good for paper);
  author-verified 4 -> 0.500/0.500/0.500/0.500.
- Per-question ranks saved (`law_eval_ranks_full.json`, historical engine; strict chain in
  `tcr_sgb_result.json`, no-GPU repro in `law_eval_repro.json`); ablation + significance
  still those of the initial ablation (`ablation_AB.json`, `significance.json`) and will be
  re-run for the paper on this frozen release snapshot.
- Temporal-constraint hardness sweep (`tcr_weight_sensitivity.json`): expired-law
  candidates down-weighted by (1−α); Hit@1 reaches the hard-filter value 0.530 already
  at α=0.1 and all metrics coincide with the hard filter from α=0.5 (every α>0:
  Wilcoxon p<10⁻¹⁹, n=281, no-GPU stored-vector engine).
- Early-benchmark metrics for comparison: Hit@1 0.41 / Hit@3 0.60 / Hit@5 0.67 /
  Hit@10 0.75 (n=283 incl. 41 weak + 48 partial tiers now resolved).

## Collection & preprocessing
- **Sources:** signed Cong-bao PDFs (5 core laws re-verified numerically
  perfect: 838/838, 110/110, 777/777, 78/78, 689/689 Điều) + TVPL official
  HTML for 24/24 sampled chunks; mirror pages remain for laws without
  official equivalents and stay `mirror`-flagged.
- **Decontamination (three rounds):** round 1 stripped boilerplate footers
  ("so hieu:", "ngay cong bao:" ...) from 1.203 chunks (residual 0);
  round 2 stripped in-body Cong-bao page headers from 409 chunks and removed
  3 duplicate chunk IDs; round 3 (1) rebuilt 2 chunks of NCN2010 whose
  official government .doc source carried broken piece-table bytes
  (text re-derived from the same official file with a complete
  piece-table parser, source_url/source_type kept "official"), (2) replaced
  a source-page warning emoji with a plain "[!] " marker in BLDS2005
  Dieu 777, and (3) re-ran 94 LLM extractions whose stored output contained
  stray non-Vietnamese glyphs (the earlier engine occasionally emitted
  isolated CJK tokens). A byte-level gate over every released file now
  counts non-Vietnamese-script / private-use artifacts as zero.
  The extraction and index in this release therefore match chunk text 1:1.
- **Lineage:** per-Dieu mean-vector cosine across BLDS 1995->2005->2015;
  sim >= 0.90 accepted as "phien ban khac" relations (439 unique after
  Muc-remap for the 1995 clause split), 0.80-0.90 band kept in
  `lineage_candidates.json` for audit, not injected.
- **CITES:** 1.506 intra-law cross-reference edges from the ref regex —
  these are already regenerated as DAN-CHIEU relations inside the index
  build, so `cite_edges.json` doubles as ground truth for them.
- **Index stats file:** `provenance/law_index_stats.json` carries the
  authoritative entity/relation/chunk counts used by every audit script.

## Artifacts in this release
- Public HF mirror (v1.0.0): https://huggingface.co/datasets/datbazuka2502/vicivil-tkg
- `data/civil_chunks.jsonl` (11.267 rows; superseded intermediates
  `civil_chunks_v10.jsonl` / `civil_extract.json` removed from both mirrors, regenerable via `src/law_kg_extract.py`), 6 index
  files (`vdb_chunks / vdb_entities / vdb_relationships` +
  3 kv stores), `temporal_graph.json`.
- `benchmark/law_bench_main.json`, `law_bench_seed.json` (281 Qs, gold_tier +
  rescoped question provenance), `law_eval_ranks_full.json` (per-Q ranks),
  rater/regold/drop trail: `second_rater.json`, `second_rater14.json`,
  `regold.json`, `regold_judge_round1.json`, `regold_judge_round2.json`, `fixall.json`, `dropped_log.json`, `bench_split.json`.
- `provenance/`: `cite_edges.json`, `lineage_candidates.json`,
  `amend_candidates.json`, `law_audit.json`, `law_sources.json`,
  `ablation_AB.json`, `significance.json`, `qa_faith.json`,
  `ranks_hybrid.json`, `law_index_stats.json`, `SHA256SUMS` (regenerated
  for v1.0.0 and verified on upload).
- Data and benchmark trees (`data/`, `benchmark/`, `index/`,
  `provenance/`) are identical between the GitHub release engine and the
  HF dataset card (byte-level verified).

## Known gaps (disclosed)
- 0 empty-content chunks (`law_audit.json`: `empty`=0); 424 item-level chunks
  carry short LLM extractions (mostly short BLDS 1995 numbered items) — refs kept;
  disclosed per-law histogram in `law_audit.json` (computed, reproducible).
- Near-duplicate copies across laws (603 total groups; 557 of them span
  more than one law — e.g. the same article text preserved verbatim by a
  2005 successor, or VBHN consolidations): measured impact is small —
  only 10/281 benchmark questions show a top-5 duplicate collision, and
  temporal filtering already prevents most crowding. A retrieval-time
  duplicate-collapse experiment was REJECTED: the retriever's internal
  ordering depends on the requested top-k, so extending-and-truncating
  outside the retriever distorts ranks (Hit@1 fell to 0.0 in probe).
  Numbers below therefore use the unmodified hybrid retriever.
- Two NCN2010 article-bodies could not be byte-preserved from the
  government .doc (its own piece-table is damaged); they were rebuilt from
  the same official file's clean piece-table run and the cleaned text was
  verified against the surrounding articles before release.
- Remaining article-numbering gaps (final release measurement in
  `law_audit.json`): HNGD2000 3/110, THADS-VBHN 5/190, VBHN-21 Dieu 497,
  Law 15/2026 44 items (gazette law still awaiting consolidated text);
  BLDS 1995 has zero gaps left since its clause-level rebuild.
- Graph-mode retrieval still trails hybrid on strict Hit (known from the ablation study); 32 regolded questions are hard restatements — stratified
  numbers are reported so no one average hides them.
- Expert review (50 Qs) pending; GitHub PAT rotation pending (owner has
  accepted the outreach-level risk in the meantime).
- The first HF token was exposed in a chat log during upload and has been
  revoked; a new token is used thereafter with no secret stored in any
  released file (verified by secret-pattern scan).
- Bench has 1 duplicated question text across two qids (CIV001/CIV002,
  both verified) — counted in all averages, disclosed here to avoid
  hidden double weighting.

## Uses, distribution, maintenance
- **License:** legal texts public domain (Luật 104/2016/QH13, Luật
  64/2025/QH15); curation (schema, IDs, benchmark) CC-BY-4.0.
- **Update protocol:** monthly gazette sweep; amended articles close
  valid_to + open new edges (never rewrite history).

## Changelog

- **v1.0.0:** first public release. Corpus of 11,267 hierarchical chunks across
  17 Vietnamese civil-law statutes (1996-2026) with per-chunk validity windows;
  temporal knowledge graph (33 statutes, 21 replaces/amends edges) exported as
  RDF/Turtle, JSON-LD and GEXF; three-tier retrieval index (14,099 entities,
  20,311 relation rows, 768-d vectors); 281-question situational benchmark with
  the complete gold-verification trail (8B/14B cascade audit, re-anchoring
  logs, author review tiers, one documented drop); retrieval metrics (hybrid,
  TCR temporal filtering, cross-encoder rerank) with paired significance
  tests; an end-to-end LLM RAG baseline (Qwen2.5-3B-Instruct, four
  conditions); and a single-file offline graph explorer. All numbers are
  reproducible from the repository alone, without GPU or network.
