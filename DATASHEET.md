# DATASHEET — Vietnamese Civil Law Temporal Knowledge Graph (ViCivil-TKG v1.0)

## Motivation
- *Why built:* no public Vietnamese legal KG exists at article–clause–point
  granularity with validity-time tracking. Document-level graphs (170k docs)
  know "Law A amends Law B" but not which article, effective when.
  Competition demos (3 tax docs) prove the idea, not the resource.
- *Intended uses:* temporal legal QA ("what did the law say on date X?"),
  GraphRAG research, amendment tracking. *Not legal advice.*

## Composition
- **Instances:** ~10.2k chunks (law|dieu|khoan|diem IDs), ~17k entities
  (10 legal types), ~9k relations + deterministic cross-reference edges.
- **Temporal:** 17 laws with [valid_from, valid_to) + 16 external amending laws;
  21 edges (4 succession + 17 AMENDS mined from VBHN preambles with dates);
  every chunk inherits law validity; `law_as_of(date)` tested.
- **Benchmark:** 211 situational questions (12 hand + 199 generated, junk-filtered,
  38 flagged cases adjudicated) + abstain tests (1990 empty pool + missing-law
  probes) + review stamps. Final (n=211): Hit@1 0.512 / Hit@3 0.682 /
  Hit@5 0.711 / MRR 0.599 / nDCG@10 0.637; abstain 2/2; second-rater agreement
  65% (83% on verified hand); end-to-end QA faithfulness n=30: 20 supported /
  10 partial / 0 hallucinated.
- **Versions:** civil_chunks.jsonl, civil_extract.json, law_data/ (8-file
  index), temporal_graph.json, law_audit.json. Snapshots per release;
  amendment deltas between releases (planned).

## Collection & preprocessing
- **Sources:** signed Công báo PDFs + VBHN consolidations (official),
  ministry portals, static mirrors (each chunk carries source_url +
source_type: official-line 45% / mirror 55%. Mirror verification: **43/43
  sampled chunks match independent sources** (4 excerpt checks + 15/15 vs TVPL
  full-text PDF OCR + 24/24 vs TVPL full HTML across BLDS 2015/2005,
  HN&GĐ 2000, Nuôi con nuôi 2010; diacritic-stripped fuzzy spans,
  OCR/noise-tolerant). Residual: laws without official cross-check stay
  flagged `mirror`.
- **Pipeline:** crawl → text-layer check (scans quarantined) → hierarchy
  parse (flow + line modes) → TOC-dedup (longest) → civil title filter
  (hand-reviewed allowlist) → LLM extraction (few-shot + validators) →
  deterministic ref resolver → audit gates (dup 0, empty 0, orphans 0).
- **Known gaps (disclosed, not hidden):** BLDS 1995 missing 2/838 articles;
  HNGD2000 missing 3/110; THADS-VBHN 5/190; VBHN-21 missing Điều 497;
  amendment-law chunks sparse by nature; BLDS1995 chunks Dieu-level only
  (khoan inline); 35 empty extractions; mirror sources need official
  re-verification for courtroom use.

## Uses, distribution, maintenance
- **License:** legal texts public domain (Luật 104/2016/QH13, Luật 64/2025/QH15);
  curation (schema, IDs, benchmark) CC-BY-4.0.
- **Update protocol:** monthly gazette sweep appends new issues; amended
  articles close valid_to + open new edges (never rewrite history).
- **Metrics v1 (final):** hybrid default Hit@5 0.711 (MRR 0.599); ablation
  dense 0.673 → hybrid 0.711 → +graph 0.526 (graph harms strict-Hit, p≈0);
  Dieu@5 ~0.6-0.9; dense-only 0.000 on colloquial queries (the motivating
  result for hybrid+graph).

## v1.1 changelog (official-PDF upgrade)
- **Source upgrade:** 5 core laws re-verified against official signed PDFs
  (BLDS 1995 838/838, HNGD 2000 110/110, BLDS 2005 777/777, TNBTCNN 2017 78/78,
  BLDS 2015 689/689 Điều) + TVPL full HTML; sampled diff 75/75 chunks match.
- **Decontamination:** stripped site-boilerplate footers from 1203 chunks
  (4 laws; residual 0; backup `civil_chunks_v10.jsonl`); chunk dense vectors
  re-embedded; v1.0 frozen + tagged.
- **Gold audit:** 282 Qs double-rated (8B full + 14B on 120 doubtful);
  16 regolds accepted (same-Q, better-chunk; 14 in dev + 2 in hand);
  41 weak golds kept + flagged `gold_tier=weak` (stratified reporting,
  no deletions).
- **Metrics v1.1:** hybrid full-bench (n=283: 271 dev+syn + 12 hand):
  Hit@1 0.41 / Hit@3 0.60 / Hit@5 0.67 / Hit@10 0.75 (hand: 0.50/0.75/0.75/
  0.83); stratified by gold_tier (168 verified + 16 regolded + 48 partial +
  41 weak, no deletions). Cleaning shifted scores slightly vs v1.0
  (boilerplate had inflated BM25 idf); temporal + abstain behavior unchanged.

