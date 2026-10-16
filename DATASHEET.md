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
- **Temporal:** 17 laws with [valid_from, valid_to); 5+ succession edges
  (REPLACES/CONSOLIDATES); every chunk inherits law validity.
- **Benchmark:** 211 câu tình huống (12 tay + 199 sinh, đã lọc rác + duyệt 38 ca
  nghi) + abstain tests (1990 rỗng pool, nội dung 1995 thiếu) + tem reviewed.
  Eval cuối (n=211): Hit@1 0,512 • Hit@3 0,682 • Hit@5 0,711 (mặc định lai; ablation đầy đủ trong README);
  abstain 2/2.
- **Versions:** civil_chunks.jsonl, civil_extract.json, law_data/ (8-file
  index), temporal_graph.json, law_audit.json. Snapshots per release;
  amendment deltas between releases (planned).

## Collection & preprocessing
- **Sources:** signed Công báo PDFs + VBHN consolidations (official),
  ministry portals, static mirrors (each chunk carries source_url +
  source_type: official-line 45% / mirror 55%).
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
- **Metrics v1:** hybrid retrieval Hit@5 0.636 (11 hand) / 0.554 (166 mixed);
  Dieu@5 0.909; abstain 2/2. Baselines: dense-only 0.000 (fails on
  colloquial queries — the motivating result for hybrid+graph).

