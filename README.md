# ViCivil-TKG — Vietnamese Civil Law Temporal Knowledge Graph

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0-blue.svg)](https://github.com/ntd25022006q/vicivil-tkg/releases/tag/v1.0)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](src/)

A versioned, article-level knowledge graph of Vietnamese civil law with
**validity-time tracking**: every chunk carries a hierarchical ID
(`Law|Article|Clause|Point`), every law carries a validity interval, and
amendments are explicit edges mined from consolidation preambles — so the
graph answers *"what did the law say on date X?"*, which flat vector stores
cannot.

## Data at a glance

| Item | v1.0 |
|---|---|
| Law chunks (Điều/Khoản/Điểm) | 10,212 across 17 laws |
| Entities / relations / citation edges | ~32k / ~18k / ~4.3k |
| Laws with validity intervals | 17 (+16 external amending laws) |
| Amendment edges (verified from VBHN preambles) | 17 |
| Benchmark questions (temporal + abstain tests) | 211 + 12 hand-written |
| Retrieval (hybrid BM25+dense, default) | Hit@1 0.512 · Hit@5 0.711 · nDCG@10 0.637 |

Laws: Civil Codes 1995/2005/2015, Marriage & Family 2000/2014/2025-consolidation,
Civil Status 2014/2026, Adoption 2010, Grassroots Mediation 2026, Civil/Criminal
Procedure + Enforcement (+ consolidated versions), State Compensation + 2026 amendment.

## Quickstart

```python
import json
chunks = [json.loads(l) for l in open("data/civil_chunks.jsonl", encoding="utf-8")]
print(len(chunks))  # 10212

# Which laws were in force on a date?
G = json.load(open("data/temporal_graph.json", encoding="utf-8"))
def in_force(law_id, date):
    L = {x["law_id"]: x for x in G["laws"]}[law_id]
    return L["valid_from"] <= date and (L["valid_to"] is None or date < L["valid_to"])
print([L["law_id"] for L in G["laws"] if L.get("status") != "external-ref" and in_force(L["law_id"], "2010-06-01")])
# -> ['BLDS2005', 'THADS2008', 'HNGD2000'] (2015+ laws did not exist yet)
```

See [`src/`](src/) for the full pipeline (crawl → chunk → extract → temporal →
retrieve → evaluate) and [`data/`](data/) for the release files with SHA256SUMS.

## Benchmark

211 situational questions with weak golds (disclosed) + 12 hand-written temporal
probes + abstain tests, stratified dev/test split (`data/bench_split.json`),
per-config ranks stored (`data/ranks_hybrid.json`), significance tested
(McNemar + Wilcoxon, all p<0.03). Key ablation on the same index: dense-only
0.673 → hybrid 0.711 → +graph layers 0.526 @Hit@5.
Gold review: author-adjudicated 38 flagged cases (keep/fix/drop with reasons) +
independent qwen3 second-rater over all golds (65% agree, 83% on verified hand
golds → ~18% truly weak, fixed). End-to-end QA faithfulness (n=30, cited
answers): 20 supported / 10 partial / **0 hallucinated**.

## Docs

- [`DATASHEET.md`](DATASHEET.md) — motivation, composition, collection,
  known gaps, license, update protocol.
- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — operating rules: audit gates,
  release checklist, incident casebook.
- [`docs/weekly-report-vi.md`](docs/weekly-report-vi.md) — weekly log (Vietnamese).

## Citation

See [`CITATION.cff`](CITATION.cff). If you use this dataset, please cite the
repository and note the version tag.

## License & disclaimer

Curation (schema, IDs, benchmark): **CC-BY-4.0** ([LICENSE](LICENSE)).
Legal texts are public domain under Vietnam's Law on Access to Information
(No. 104/2016/QH13). **Not legal advice** — verify against official sources
before any real-world use.

## Tóm tắt tiếng Việt

Kho tri thức đồ thị có thời gian cho luật dân sự Việt Nam (10.212 chunk mức
Điều/Khoản/Điểm, 17 luật, khoảng hiệu lực + cạnh sửa đổi verify từ VBHN),
kèm benchmark 211 câu hỏi có ngày + test từ chối trả lời. Chi tiết xem
[`docs/weekly-report-vi.md`](docs/weekly-report-vi.md).
