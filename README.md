# ViCivil-TKG - Vietnamese Civil Law Temporal Knowledge Graph

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
![Release](https://img.shields.io/badge/release-v1.5.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
[![HuggingFace Dataset](https://img.shields.io/badge/HF-dataset-yellow.svg)](https://huggingface.co/datasets/datbazuka2502/vicivil-tkg)

A versioned, article-level knowledge graph of Vietnamese civil law with
**validity-time tracking**: every chunk carries a hierarchical ID
(`Law|Article|Clause|Point`), every law carries a validity interval, and
amendments are explicit edges mined from consolidation preambles - so the
graph answers *"what did the law say on date X?"*, which flat vector stores
cannot.

## Interactive artifacts

- **Temporal graph explorer** - single-file, no build step:
  [`docs/graph/explorer.html`](docs/graph/explorer.html), served live at
  <https://ntd25022006q.github.io/vicivil-tkg/graph/explorer.html>
  (AntV G6 5.1.1; lane-grouped layout, as-of time slider 1996-2026,
  replaced laws dimmed, future laws hidden, gold `REPLACES` succession
  spine, dashed amendment edges, per-law provenance drawer).
  The same law-level graph ships as an **open GEXF 1.3 dynamic file** -
  [`docs/graph/law_graph.gexf`](docs/graph/law_graph.gexf) - which opens
  directly in Gephi or Gephi-Lite for any other analysis workflow, and as
  an explicit **Vega-Lite 5.21.0 timeline**
  ([`docs/graph/law_timeline.vl.json`](docs/graph/law_timeline.vl.json))
  rendered by Vega/vega-embed in the same page.

## Repository layout

| folder | content |
|---|---|
| `data/` | 11,267 chunk rows at article/clause/point granularity (17 laws, 1996-2026), each with `source_url` + `source_type` + decontamination flags; frozen v1.0 backup; LLM extraction covering all 11,267 rows |
| `benchmark/` | 281 situational questions with gold chunk IDs and `gold_tier` (245 verified / 32 regolded / 4 author-verified; 1 documented drop), per-question rank file, double-rater and regold trail, 50-question expert review package |
| `index/` | 8-file ADGR-style retrieval index: dense 768-d matrices (embeddinggemma:300m) for 14,099 entities and 20,750 relation rows (20,311 in-corpus incl. deterministic DAN-CHIEU edges + 439 cross-version successor edges at similarity >= 0.90), plus entity/relation-to-chunk kv maps |
| `provenance/` | temporal graph (17 law validity windows + 21 amendment/succession edges), 1,506 intra-law cross-reference edges, lineage candidates (0.80-0.90 similarity band retained for audit only), source audit, ablation + significance + faithfulness artifacts, authoritative index stats, SHA256SUMS |

A byte-level mirror of the four data folders is published on HuggingFace:
<https://huggingface.co/datasets/datbazuka2502/vicivil-tkg> (dataset card
with configs + loading snippets). `CITATION.cff` and the BibTeX block in
the HF card cover attribution.

## Quality gates in v1.2.5/v1.5.1

- Official-source fidelity: 5 signed Cong-bao PDFs re-verified digit-by-digit
  (838/838, 110/110, 777/777, 78/78, 689/689 articles); the corrupted
  NCN2010 government `.doc` piece-table was re-parsed and the 2 affected
  chunks rebuilt from the same official file.
- Extraction: 11,267/11,267 rows done, zero failed chunks; 94 rows whose
  stored output contained stray non-Vietnamese glyphs were re-extracted
  (per-row `engine` field records the model used).
- Character hygiene gate: zero CJK/Hangul/PUA glyphs across every released
  file (12-section audit).
- Index/text coherence: kv mirrors and dense-matrix token content equal
  chunk text 1:1 (with the disclosed 3,000-character representation cap).
- Gold audit trail: two-rater passes (8B full bench + 14B on 120
  doubtfuls), 16 re-anchors with `regolded_from` provenance, author
  adjudication for the remaining tiers.
- Reproduced metrics on the sanitized index, n=281: Hit@1 0.452 /
  Hit@3 0.658 / Hit@5 0.726 / Hit@10 0.794 / MRR 0.568 - identical to the
  v1.2.2 release numbers, so all published comparisons stay valid.
- v1.3.0 engine migration: the succession network now runs on AntV G6
  5.1.1 (built-in dark theme, hover-activate, grid backdrop, minimap,
  tooltips); a fix for a pre-existing v1.2.5-1.2.7 bug is disclosed - the
  time-travel slider now genuinely hides future laws as promised (the
  2012 probe shows exactly the 4 then-active laws bright with all later
  laws ghosted out, while the readout counts are unchanged because they
  never depended on the broken visibility).
- v1.3.1 packaging hardening: all 4 viewer JavaScript engines
  (AntV G6, Vega, Vega-Lite, vega-embed) are vendored beside the
  viewer so the artifact needs no CDN; a field report of a blank tab
  behind CDNs reproducible only in restricted networks is closed.
- v1.3.2 diagnosability: any init failure now paints an immediate red
  banner (message + position + last init step) and a dismissible
  corner pill reports the self-test state (G6/vega loaded, graph
  initialized) - no silent blank pages remain.
- v1.5.1 tooltip fix: the statute-to-G6 mapper read fields off the
  wrapper instead of the wrapped record, so statute hover cards rendered
  `undefined`; the mapping now reads the record. Footer library
  branding removed.
- v1.5.0 libraries-only UI: the custom loading mask, status pill and
  error banner are gone; the viewer drives G6/Vega through their
  documented APIs (`graph.render()` promise, `toDataURL()`,
  `vegaEmbed()`). Browser verification moved into the pre-release gate,
  which runs the artifact in bundled Chromium plus the real Chrome and
  Edge binaries. `THIRD-PARTY-NOTICES.md` lists every dependency, version
  and license.
- v1.4.2 Chrome compatibility: the app script's top-level `const chrome`
  collided with Google Chrome's built-in `window.chrome`, an early
  `SyntaxError` that prevented the whole viewer from running. All
  top-level bindings are now audited against browser globals, and a
  regression probe emulates a non-configurable `window.chrome`.
- v1.4.1 blocking-font fix: the optional Google-Fonts stylesheet no
  longer blocks document parsing (non-blocking `media="print"` pattern),
  and init follows G6's documented `render()` promise contract with an
  error watcher installed before the vendored libraries - the viewer
  renders with 0 JS errors even when the font request never answers.
- v1.4.0 single-artifact + first-frame correctness: the viewer inlines
  all four libraries so it cannot lose dependencies; the opening state
  application now waits for the library's ready signal, fixing a latent
  race that silently dropped every initial element-state update (the
  reported blank-canvas-in-the-wild class of failures).
- v1.2.7 interaction polish: every released law - including the
  amending (EXT) acts - responds to hover focus, tooltip and the
  provenance drawer; a synthetic hover probe verifies 88 of 90 canvas
  elements dim around the hovered law and fully restore on mouse-out,
  with zero JS errors on the build-time placeholder guard.
- v1.2.6 visual refresh: publication typography (Be Vietnam Pro + IBM
  Plex Mono), flat ledger palette and condensed single-bar controls; the
  offline label packing is upgraded to a near-full Cartesian lattice with
  vertical-priority ordering - build-time check reports zero pixel-exact
  collisions and zero temporal drift beyond the time columns, and the
  generator's placeholder guard runs clean before each release.

## Metrics context

| tier | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|---|---|
| all | 281 | 0.452 | 0.658 | 0.726 | 0.794 |
| verified | 245 | 0.502 | 0.678 | 0.731 | 0.796 |
| regolded (hard restatements) | 32 | 0.062 | 0.531 | 0.719 | 0.812 |
| author-verified | 4 | 0.500 | 0.500 | 0.500 | 0.500 |

## License

Legal texts are public domain under Vietnamese law (Luat 104/2016/QH13,
Luat 64/2025/QH15). Curation artifacts (schema, IDs, benchmark, provenance)
are CC-BY-4.0 - see `LICENSE` and `CITATION.cff`.
