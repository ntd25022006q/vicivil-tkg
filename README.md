# ViCivil-TKG — Vietnamese Civil Law Temporal Knowledge Graph

**📄 Báo cáo tuần (VI): [REPORT_WEEKLY_VI.md](REPORT_WEEKLY_VI.md) | Datasheet: [DATASHEET.md](DATASHEET.md)**

Kho tri thức đồ thị có thời gian cho luật dân sự Việt Nam ở mức
Điều/Khoản/Điểm: chunk ID phân cấp, entity/relation type luật, khoảng hiệu lực,
cạnh kế thừa, benchmark câu hỏi có ngày, abstain test.

## Số liệu (đo thật, truy được file gốc)

- **10.212 chunk / 17 luật**: BLDS 1995/2005/2015, HN&GĐ 2000/2014/VBHN-2025,
  Hộ tịch 2014/2026, Nuôi con nuôi 2010, Hòa giải 2026, Tố tụng + Thi hành án
  + Bồi thường + văn bản hướng dẫn (`data/civil_chunks.jsonl`).
- **~32k entity + ~18k relation + ~4,3k cạnh dẫn chiếu** (`data/civil_extract.json`).
- **Retrieval** (lai BM25+dense+fusion+expansion+rerank, lọc thời gian):
  Hit@1 0,180 • Hit@3 0,351 • Hit@5 0,474 • Điều@5 0,592 (n=211); abstain 2/2.
- **Provenance**: chunk nào cũng có `source_url + source_type`
  (official-line/mirror); audit trùng/rỗng/mồ côi/gold = 0 (`data/law_audit.json`).

## Cấu trúc

```
├── DATASHEET.md / REPORT_WEEKLY_VI.md
├── data/          # chunks, extraction, temporal graph, benchmark, audit, sources
└── src/           # pipeline: crawl, chunk, extract, temporal, retrieve, eval
```

Index vector 8 file + PDFs gốc tái tạo được bằng `src/` (xem DATASHEET mục
Reproduce). Văn bản luật là public domain (Luật 104/2016/QH13); phần curation
(schema, ID, benchmark) CC-BY-4.0. **Không phải tư vấn pháp lý.**
