# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG v1.2.7)

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*
- Expert review of 50 sampled items is pending (flagged in
  `review_package_50.md`); until then treat gold labels as LLM+author
  adjudicated, not expert-verified.

## Composition (v1.2.7)
- **Chunks:** 11.267 (law|dieu[|khoan|diem|muc] IDs) across 17 laws;
  sources: official 6.141 / mirror 4.476 / official-copy 266 / semi 391,
  each chunk carries source_url + source_type + (where applicable)
  `cleaned_v11=true` footer-strip flag. BLDS 1995 re-parsed to clause level
  from the signed PDF (1.896 chunks: Dieu or Dieu|Muc{0..k}).
- **Extraction:** 11.267 chunk rows with entities/relations/deterministic
  DAN-CHIEU refs extracted on the decontaminated text (qwen25-awq,
  temp 0, few-shot + validators). 97 chunks were later re-extracted with
  qwen3:14b via Ollama (9 stub-rescues in v1.2.2, then 94 rows whose
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
  dropped with written reason (`dropped_log.json`); double-rater trail
  (8B full bench + 14B doubtfuls) in `second_rater*.json`, `regold.json`,
  `fixall.json`; 50-Q expert review package still pending.

### Per-law size table (chunk counts, v1.2.7)

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
| `valid_from` / `valid_to` | date | law inheritance of `[from, to)` validity |
| `cleaned_v11` | bool | footer/header decontamination flag |
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

## Metrics (measured on the v1.2.3 index; numbers carried to v1.2.4 —
  hygiene-only strip of 12 invisible codepoints, no content change)
- Full bench n=281: Hit@1 0.452 / Hit@3 0.658 / Hit@5 0.726 / Hit@10 0.794
  / MRR 0.568. Re-evaluated on the sanitized v1.2.3 index and confirmed
  unchanged vs v1.2 (same numbers whenever rounded to 3 decimals).
- Stratified by gold_tier: verified 245 -> 0.502/0.678/0.731/0.796;
  regolded 32 -> 0.062/0.531/0.719/0.812 (deliberately hard restatements:
  answer lives in a target chunk not reachable by surface wording, but
  rank-10 recall 0.812 shows the index finds it — good for paper);
  author-verified 4 -> 0.500/0.500/0.500/0.500.
- Per-question ranks saved (`law_eval_v12.json`); ablation + significance
  still those of v1.0 (`ablation_AB.json`, `significance.json`) and will be
  re-run for the paper on this frozen v1.2.3 snapshot.
- v1.1 metrics for comparison: Hit@1 0.41 / Hit@3 0.60 / Hit@5 0.67 /
  Hit@10 0.75 (n=283 incl. 41 weak + 48 partial tiers now resolved).

## Collection & preprocessing
- **Sources:** signed Cong-bao PDFs (5 core laws re-verified numerically
  perfect: 838/838, 110/110, 777/777, 78/78, 689/689 Điều) + TVPL official
  HTML for 24/24 sampled chunks; mirror pages remain for laws without
  official equivalents and stay `mirror`-flagged.
- **Decontamination (three rounds):** v1.1 stripped boilerplate footers
  ("so hieu:", "ngay cong bao:" ...) from 1.203 chunks (residual 0);
  v1.2 stripped in-body Cong-bao page headers from 409 chunks and removed
  3 duplicate chunk IDs; v1.2.3 (1) rebuilt 2 chunks of NCN2010 whose
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
- Public HF mirror (v1.2.3): https://huggingface.co/datasets/datbazuka2502/vicivil-tkg
- `data/civil_chunks.jsonl` (11.267 rows), `civil_chunks_v10.jsonl`
  (frozen v1.0 backup), `civil_extract.json` (clean extraction), 6 index
  files (`vdb_chunks / vdb_entities / vdb_relationships` +
  3 kv stores), `temporal_graph.json`.
- `benchmark/law_bench_200c.json`, `law_bench_v1.json` (281 Qs, gold_tier +
  rescoped question provenance), `law_eval_v12.json` (per-Q ranks),
  rater/regold/drop trail: `second_rater.json`, `second_rater14.json`,
  `regold.json`, `fixall.json`, `dropped_log.json`, `bench_split.json`.
- `provenance/`: `cite_edges.json`, `lineage_candidates.json`,
  `amend_candidates.json`, `law_audit.json`, `law_sources.json`,
  `ablation_AB.json`, `significance.json`, `qa_faith.json`,
  `ranks_hybrid.json`, `law_index_stats.json`, `SHA256SUMS` (regenerated
  for v1.2.3 and verified on upload).
- Data and benchmark trees (`data/`, `benchmark/`, `index/`,
  `provenance/`) are identical between the GitHub release engine and the
  HF dataset card (byte-level verified).

## Known gaps (disclosed)
- ~500 item-level chunks have empty LLM extractions (mostly short BLDS
  1995 numbered items; validators reject generic 1-word names) — refs kept;
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
- Remaining article-numbering gaps (final v1.2.3 measurement in
  `law_audit.json`): HNGD2000 3/110, THADS-VBHN 5/190, VBHN-21 Dieu 497,
  Law 15/2026 44 items (gazette law still awaiting consolidated text);
  BLDS 1995 has zero gaps left since its v1.2 clause-level rebuild.
- Graph-mode retrieval still trails hybrid on strict Hit (known from v1.0
  ablation); 32 regolded questions are hard restatements — stratified
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
- **v1.2.7:** interaction-and-axis polish release, zero content change
  (no data/index/benchmark edits; retrieval metrics above remain the
  frozen v1.2 measurement). Hovering any law now focuses its succession
  neighborhood and dims everything else, restored cleanly on mouse-out;
  amending (EXT) laws are now reachable for tooltips and the provenance
  drawer exactly like ordinary laws (previously EXT nodes were inert on
  hover/tap); the year guides gain top cap ticks and faint per-lane
  band stems for structural reading; amendment edges render as gentle
  arcs while succession lines stay straight through the time columns;
  the top-left lane-title/older-label overlap is removed. Manifest
  unchanged at **42 entries**; 12-statute sweep green on both mirrors.
- **v1.2.6:** visual-refresh release, zero content change (no data/index/
  benchmark edits; retrieval metrics above remain the frozen v1.2
  measurement). The viewer's interface is rebuilt to publication-grade
  typography: Google-Fonts **Be Vietnam Pro** (body) + **IBM Plex Mono**
  (figures), flat "consultation ledger" palette, a slim masthead with a
  vector brand mark, an inverse-contrast year seal, a single transport
  bar (slider / play / 1x-2x speed), edge-type toggles and family chips
  regrouped on the lane bar, and library names removed from the tab
  captions ("Mạng kế thừa" / "Phổ thời gian"). Inside the canvas, the
  offline label packing is upgraded to a near-full Cartesian lattice
  with vertical-priority ordering (resolving rare pixel-exact
  collisions between 2024-2025 amending-law labels), edge-of-canvas
  guard nodes protect border labels from clipping, vertical time guides
  are drawn behind the nodes, and the Vega-Lite timeline is re-themed
  to the same palette. Manifest unchanged at **42 entries**; a
  12-statute glyph/secret/JSON sweep runs green across both mirrors.
- **v1.2.5:** visualization release, zero content change (no data/index/
  benchmark edits; retrieval metrics above remain the frozen v1.2
  measurement). The interactive release viewer is rebuilt on dedicated
  open-source graph tooling in place of the general-purpose chart
  library: the temporal successor network
  (`docs/graph/explorer.html`) now runs on **Cytoscape.js 3.30.2** with
  (a) lane-grouped layout (10 law families along a vertical axis) using a
  collision-free pixel-packing pass computed offline in the generator,
  (b) a time-travel slider (1996→2026) that hides future laws, dims
  replaced ones and recounts "in force" live, (c) short statutory labels
  on external amending laws (just the number/year, e.g. "59/2020"), and
  (d) a provenance drawer per node (validity, chunk/citation counts,
  succession chip, citation list). The timeline tab
  (`docs/graph/law_timeline.vl.json`) is an explicit **Vega-Lite 5.21.0**
  spec (temporal Gantt with successor edges and an "today" marker,
  palette-matched to the network). Both plus the open GEXF 1.3 export
  are covered by the manifest, which grows from 41 to **42 entries**.
  "Sync/pull" wording along the whole pipeline was audited: every step
  is a full checkout or full upload plus manifest verification — no
  remote-side partial merge is ever relied on. A 12-statute glyph/
  secret/JSON sweep runs green across both mirrors.
- **v1.2.4:** hygiene release, zero content change. (a) The last 12
  invisible left-to-right-mark (U+200E) control characters — previously
  recorded as a pending post-release sync item — are now stripped at the
  source of both mirrors from all four affected files
  (data/civil_chunks.jsonl, data/civil_chunks_v10.jsonl,
  index/kv_store_text_chunks.json, index/vdb_chunks.json); all four parses
  re-verified; (b) one typographic slip in "Collection & preprocessing"
  ("Dien)" → "Điều)"); (c) explorer label-overlap fix (ECharts
  labelLayout.hideOverlap) and regenerated docs/graph/explorer.html;
  (d) both mirrors regenerated; retrieval metrics not re-run (the strip
  touches 12 invisible codepoints only; v1.2.3 numbers reported above
  remain the reference measurement).
- **v1.2.3:** root-cause sanitization pass. (a) Rebuilt 2 NCN2010 chunks
  from the official government .doc via a full piece-table parser (the
  source file itself carries damaged piece records that had leaked binary
  debris into the corpus); (b) replaced 1 source emoji with "[!] "; (c)
  re-extracted 94 rows whose output contained stray CJK/PUA glyphs (the
  extraction engine occasionally emitted isolated Chinese tokens) with
  qwen3:14b/Ollama — per-row engine field kept; (d) one header-only stub
  chunk (VBHN-21 Dieu 151, 17 chars) removed from every store and 2.307
  rows had a non-integer `chars` field normalized to int; index rebuilt
  (14.099 ent / 20.311 rel + 439 lineage = 20.750 rows) with same-gold
  anchor sets; re-eval unchanged (0.452/0.658/0.726/0.794, MRR 0.568);
  (e) 12-section pre-release audit green: zero weird-character groups
  across all released files, zero id-set drift across the 4 stores, gold
  281/0 broken, extraction 11.267/11.267 done, zero secret patterns;
  (f) one residual split roman numeral ("Chương XXX VII" from a scraped
  page boundary) normalized to "Chương XXXVII" corpus-wide and its index
  row re-embedded; (g) HF + GitHub trees regenerated and revisioned
  together with a 41-entry signed manifest covering data, benchmark, index,
  provenance, the interactive temporal graph explorer
  (`docs/graph/explorer.html` + open GEXF `docs/graph/law_graph.gexf`),
  and the five official source PDFs.
- **v1.2.2:** full-scale cross-artifact audit (zero id-set drift across
  chunk/extract/vdb/kv files; matrix rows == data rows everywhere; gold
  0 broken; 439 cross edges all resolvable). 9 failed3x chunk extractions
  rescued (engine noted per-row) and the 8-file index rebuilt from the
  complete extraction — re-eval reproduced v1.2 metrics exactly
  (0.452/0.658/0.726/0.794, MRR 0.569). Duplicate-crowding measured
  (10/281 top-5 collisions) — retrieval-time dedup rejected as
  rank-distorting; index content [:3000] cap disclosed.
- **v1.2:** BLDS 1995 rebuilt at clause level from signed PDF; second
  decontamination round (409 Cong-bao page headers, 3 dup IDs, 1 Muc-remap
  fix in lineage injection); full re-extraction on clean text (11.268 rows
  as shipped at v1.2)
  + index rebuild (14.066 ent / 20.271 rel + 439 lineage edges); gold
  archive finalized — no weak/partial tiers: 245 verified + 32 regolded +
  4 author-verified + 1 documented drop; eval frozen at Hit@1 0.452 /
  MRR 0.569 (n=281).
- **v1.1:** official-PDF verification of 5 core laws; footer decontamination
  (1.203 chunks); double-rater gold audit; 16 regolds; tag + release.
- **v1.0:** first full benchmark + 8-file index + hybrid/graph ablations,
  abstain probes, faithfulness n=30 (20/10/0 hallucinated).
