# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG v1.2)

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*
- Expert review of 50 sampled items is pending (flagged in
  `review_package_50.md`); until then treat gold labels as LLM+author
  adjudicated, not expert-verified.

## Composition (v1.2)
- **Chunks:** 11.268 (law|dieu[|khoan|diem| muc] IDs) across 17 laws;
  sources: official 6.141 / mirror 4.476 / official-copy 266 / semi 391,
  each chunk carries source_url + source_type + (where applicable)
  `cleaned_v11=true` footer-strip flag. BLDS 1995 re-parsed to clause level
  from the signed PDF (1.896 chunks: Dieu or Dieus|M u{0..k}).
- **Extraction:** 11.268 chunk rows with entities/relations/deterministic
  DIEN-DACHIEU refs extracted on the decontaminated text (qwen25-awq,
  temp 0, few-shot + validators). 9 previously-failed chunks (stub-carrying
  paragraphs) were rescued with qwen3:14b via Ollama — engine heterogeneity
  for those 9 rows is recorded on the row (`engine` field); extraction now
  covers 11.268/11.268 rows with zero failed chunks (0% vs the 4% disclosed
  in v1.2).
- **Index (8-file ADGR-style):** 14.068 entities (10 legal types) / 20.275
  relations incl. chunk-chunk DIEN-DACHIEU edges (+439 cross-version
  successor edges appended separately, totalling 20.714 relation rows)
  mined by embedding similarity (sim ≥ 0.90, p 0.80-0.90 band retained for
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

## Metrics (v1.2, hybrid retriever + rerank, temporal-filtered)
- Full bench n=281: Hit@1 0.452 / Hit@3 0.658 / Hit@5 0.726 / Hit@10 0.794
  / MRR 0.569.
- Stratified by gold_tier: verified 245 → 0.502/0.678/0.731/0.796;
  regolded 32 → 0.062/0.531/0.719/0.812 (deliberately hard restatements:
  answer lives in a target chunk not reachable by surface wording, but
  rank-10 recall 0.812 shows the index finds it — good for paper);
  author-verified 4 → 0.500/0.500/0.500/0.500.
- Per-question ranks saved (`law_eval_v12.json`); ablation + significance
  still those of v1.0 (`ablation_AB.json`, `significance.json`) and will be
  re-run for the paper on this frozen v1.2 snapshot.
- v1.1 metrics for comparison: Hit@1 0.41 / Hit@3 0.60 / Hit@5 0.67 /
  Hit@10 0.75 (n=283 incl. 41 weak + 48 partial tiers now resolved).

## Collection & preprocessing
- **Sources:** signed Cong-bao PDFs (5 core laws re-verified numerically
  perfect: 838/838, 110/110, 777/777, 78/78, 689/689 Dien) + TVPL official
  HTML for 24/24 sampled chunks; mirror pages remain for laws without
  official equivalents and stay `mirror`-flagged.
- **Decontamination (two rounds):** v1.1 stripped boilerplate footers
  ("số hiệu:", "ngày công báo:" ...) from 1.203 chunks (residual 0);
  v1.2 additionally stripped in-body Công-bao page headers
  ("CÔNG BÁO/Số N/...") from 409 chunks (6 laws 2026/VBHN), removed 3
  duplicate chunk IDs (BLDS 1995 re-parse artifacts), re-embedded and
  re-extracted all affected — the extraction and index in this release
  therefore match chunk text 1:1.
- **Lineage:** per-Dieu mean-vector cosine across BLDS 1995→2005→2015;
  sim ≥ 0.90 accepted as `phiên bản khác` relations (439 unique after
  M u-remap for 1995 clause split), 0.80-0.90 band kept in
  `lineage_candidates.json` for audit, not injected.
- **CITES:** 1.506 intra-law cross-reference edges from the ref regex —
  these are already regenerated as DIEN-DACHIEU relations inside the index
  build, so `cite_edges.json` doubles as ground truth for them.

## Artifacts in this release
- `data/civil_chunks.jsonl` (11.268 rows), `civil_chunks_v10.jsonl`
  (frozen v1.0 backup), `civil_extract.json` (clean extraction), 6 index
  files (`vdb_chunks / vdb_entities / vdb_relationships` +
  3 kv stores), `temporal_graph.json`.
- `data/law_bench_200c.json`, `law_bench_v1.json` (281 Qs, gold_tier +
  rescoped question provenance), `law_eval_v12.json` (per-Q ranks),
  rater/regold/drop trail: `second_rater.json`, `second_rater14.json`,
  `regold.json`, `fixall.json`, `dropped_log.json`.
- Provenance/mining: `cite_edges.json`, `lineage_candidates.json`,
  `amend_candidates.json`, `law_audit.json`, `law_sources.json`.
- `SHA256SUMS` regenerated for v1.2.

## Known gaps (disclosed)
- ~500 item-level chunks have empty LLM extractions (mostly short BLDS
  1995 numbered items; validators reject generic 1-word names) — refs kept;
  disclosed per-law histogram in `law_audit.json` (computed, reproducible).
- Near-duplicate copies across laws (557 groups, 1.164 chunks — e.g. the
  same article text preserved verbatim by a 2005 successor, or VBHN
  consolidations): measured impact is small — only 10/281 benchmark
  questions show a top-5 duplicate collision, and temporal filtering
  already prevents most crowding. A retrieval-time duplicate-collapse
  experiment was REJECTED: the retriever's internal ordering depends on
  the requested top-k, so extending-and-truncating outside the retriever
  distorts ranks (Hit@1 fell to 0.0 in probe). Numbers below therefore use
  the unmodified hybrid retriever.
- Missing articles as in v1.0 (BLDS 1995 2/838 pre-PDF-era gaps, HNGD2000
  3/110, THADS-VBHN 5/190, VBHN-21 Điều 497) — measured and documented.
- Graph-mode retrieval still trails hybrid on strict Hit (known from v1.0
  ablation); 32 regolded questions are hard restatements — stratified
  numbers are reported so no one average hides them.
- Expert review (50 Qs) and HuggingFace mirror still pending; GitHub PAT
  rotation pending (outreach-level risk accepted by owner).
- Bench has 1 duplicated question text across two qids (CIV001/CIV002,
  both verified) — counted in all averages, disclosed here to avoid
  hidden double weighting.

## Uses, distribution, maintenance
- **License:** legal texts public domain (Luật 104/2016/QH13, Luật
  64/2025/QH15); curation (schema, IDs, benchmark) CC-BY-4.0.
- **Update protocol:** monthly gazette sweep; amended articles close
  valid_to + open new edges (never rewrite history).

## Changelog
- **v1.2.2:** full-scale cross-artifact audit (zero id-set drift across
  chunk/extract/vdb/kv files; matrix rows == data rows everywhere; gold
  0 broken; 439 cross edges all resolvable). 9 failed3x chunk extractions
  rescued (engine noted per-row) and the 8-file index rebuilt from the
  complete extraction — re-eval reproduced v1.2 metrics exactly
  (0.452/0.658/0.726/0.794, MRR 0.569). Duplicate-crowding measured
  (10/281 top-5 collisions) — retrieval-time dedup rejected as
  rank-distorting; index content [:3000] cap disclosed.
- **v1.2:** BLDS 1995 rebuilt at clause level from signed PDF; second
  decontamination round (409 Công-bao page headers, 3 dup IDs, 1 M u-remap
  fix in lineage injection); full re-extraction on clean text (11.268 rows)
  + index rebuild (14.066 ent / 20.271 rel + 439 lineage edges); gold
  archive finalized — no weak/partial tiers: 245 verified + 32 regolded +
  4 author-verified + 1 documented drop; eval frozen at Hit@1 0.452 /
  MRR 0.569 (n=281).
- **v1.1:** official-PDF verification of 5 core laws; footer decontamination
  (1.203 chunks); double-rater gold audit; 16 regolds; tag + release.
- **v1.0:** first full benchmark + 8-file index + hybrid/graph ablations,
  abstain probes, faithfulness n=30 (20/10/0 hallucinated).
