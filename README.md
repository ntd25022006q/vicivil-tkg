---
language:
- vi
license: cc-by-4.0
task_categories:
- question-answering
- text-retrieval
pretty_name: ViCivil-TKG (Vietnamese Civil Law Temporal KG)
size_categories:
- 10K<n<100K
tags:
- vietnamese
- legal
- temporal-knowledge-graph
- retrieval
- benchmark
- question-answering
configs:
- config_name: corpus
  data_files: data/civil_chunks.jsonl
- config_name: benchmark
  data_files:
  - benchmark/law_bench_main.json
  - benchmark/law_bench_seed.json
- config_name: benchmark-extension
  data_files: benchmark/law_bench_extension.json
- config_name: benchmark-extension2
  data_files: benchmark/law_bench_extension2.json
- config_name: index
  data_files:
  - index/vdb_chunks.json
  - index/vdb_entities.json
  - index/vdb_relationships.json
---

# ViCivil-TKG — Vietnamese Civil Law Temporal KG & Benchmark

![license](https://img.shields.io/badge/license-CC--BY--4.0-blue) ![tasks](https://img.shields.io/badge/tasks-QA%20%2B%20retrieval-4c8) ![language](https://img.shields.io/badge/language-ti%E1%BA%BFng%20Vi%E1%BB%87t-red)

**ViCivil-TKG** là bộ dữ liệu mở cho hỏi–đáp pháp luật dân sự Việt Nam, tập trung vào hai yếu tố thường bị bỏ qua: **thời hiệu văn bản** (cùng câu hỏi — đáp án khác nhau theo mốc thời gian áp dụng) và **độ tin cậy của đáp án vàng** (mọi câu hỏi đều có dấu vết thẩm định đa vòng, không câu nào "không xác minh được").

| | |
|---|---|
| Văn bản pháp luật | **20** (1995–2026) |
| Đoạn văn bản (Điều–Khoản–Điểm) | **13.151**, mỗi đoạn có `source_url`, `source_type`, `fetched`, cửa sổ hiệu lực |
| Câu hỏi benchmark đã công bố | **451** = 281 lõi (269 sinh + 12 viết tay) + 106 mở rộng vòng 1 + 64 mở rộng vòng 2 (văn bản 1996–2015) |
| Câu hỏi cách ly công khai | **226** (không bao giờ tính vào chỉ số) |
| Trạng thái vàng | 281/281 câu lõi đã xác minh (0 unverifiable); 21 regolded · 4 author-verified · 27 flagged disclosed |
| Tách dev/test (lõi) | 140 / 141 (stratified) |
| Đồ thị thời gian | 37 văn bản · 24 cạnh nối tiếp–sửa đổi |

## Cấu trúc benchmark

```
benchmark/
  law_bench_main.json          269 câu sinh (GEN/NEW/TOP*) — tier + weak_review disclosure
  law_bench_seed.json          12 câu viết tay (CIV001–CIV012, có câu test abstain)
  law_bench_extension.json     106 câu vòng 1 (101 verified + 5 regolded)
  law_bench_extension2.json    64 câu vòng 2 — văn bản 1996–2015 (53 verified + 11 regolded)
  extension_flagged.json       136 câu vòng 1 bị cách ly + full audit trail
  extension2_flagged.json      90 câu vòng 2 bị cách ly (89 audit-fail + 1 trùng lặp cos 0.9931)
  extension2_dedup_audit.json  audit trùng lặp chéo cohort (cos > 0.95 vs 387 câu công bố)
  gold_adjudicated.json        vàng sau thẩm định: 281/281 gold đã xác minh
  gold_pass3.json              pass-3: 99 nghi vấn → 66 ok / 29 flag / 4 reanchor + agreement audit
  weak_gold_reanchor.json      dấu vết áp dụng pass-3 (guardrail: tồn tại · trong ứng viên · đúng cửa sổ thời hiệu)
  as_of_fixes.json · regold.json · regold_judge_round2.json   trail các vòng trước
```

## Chuỗi thẩm định đáp án vàng

1. **Hai tầng khi sinh** — judge 8B chấm `usable`, câu không đạt được judge sâu 14B chấm lại kèm bằng chứng; fail → cách ly công khai.
2. **Neo lại hai vòng** — đề xuất đoạn thay thế chỉ được chấp nhận khi **cả hai vòng** LLM judge xác nhận (38 câu lõi, agreement judge 0.8875).
3. **Pass-3 (qwen3:14b)** — rà 99 câu nghi vấn vàng yếu: 66 gold-ok · 29 flag · 4 reanchor (1 bị guardrail chặn vì ngoài cửa sổ thời hiệu); 2 câu "không xác minh được" cuối cùng đều được neo lại thành công. Trên 60 câu mẫu (seed cố định): **gold-set agreement 0.554, primary 0.571** (56/60 parse OK) — kiểm tra giữa hai mô hình, **không thay thế** đánh giá con người (gói 50 câu cho human IAA kèm sẵn trong repo).

## Kết quả chính (chi tiết trong `docs/report/ViCivil-TKG_paper.pdf`)

**Truy hồi trên lõi 281 câu** (BM25 + dense 768d + RRF k=60, lọc thời hiệu TCR):

| Nhóm | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|---|---|
| Toàn bộ | 281 | 0.537 | 0.737 | 0.808 | 0.875 |
| verified | 229 | 0.585 | 0.760 | 0.821 | 0.895 |
| regolded | 21 | 0.238 | 0.762 | 0.857 | 0.905 |

**Sinh có trích dẫn** (Qwen2.5-3B-Instruct, greedy): No-RAG cite_acc **0.004** → RAG hybrid **0.488** → **+TCR 0.601** (McNemar p = 5.8e-05) → rerank+TCR 0.600 (ctx_hit5 0.846). No-RAG vs TCR: p = 5.3e-51.

**Cohort 1996–2015 (64 câu)** — khó hơn rõ rệt: retrieval Hit@5 0.703 → **0.781 với TCR** (p = 4.0e-05) → **0.828 với rerank+TCR** (Hit@1 0.703, p = 1.4e-03); LLM cite_acc 0.000 → 0.531 với TCR (McNemar p = 1.2e-10). Stratified theo tier công bố đầy đủ trong paper.

## Tái lập không cần GPU

```bash
bash tools/reproduce.sh   # chấm lại toàn bộ retrieval từ artifact đã lưu
python src/law_eval_repro.py              # core hybrid (không TCR)
python src/law_ranks_full_rebuild.py verify   # hybrid+TCR, tự đối chiếu file công bố
python src/law_llm_rag_rescore.py         # rescore LLM RAG từ câu trả lời đã lưu
python src/law_extension_eval.py benchmark/law_bench_extension2.json \
    benchmark/extension2_question_vectors.json benchmark/extension2_eval_ranks.json
```

Mọi bước sinh/đánh giá cần GPU (gen, adjudicate, rerank, LLM QA) đều có script trong `src/` với checkpoint đầy đủ trong trail files.

## Bảng giấy phép & trích dẫn

- Kho văn bản: theo nguồn gốc từng văn bản (xem `provenance/law_sources.json`); nội dung pháp luật là công khai theo pháp luật Việt Nam.
- Benchmark + metadata: **CC-BY-4.0**.
- Code: xem repo GitHub kèm theo.

```bibtex
@dataset{vicivil_tkg_2026,
  title     = {ViCivil-TKG: Vietnamese Civil Law Temporal Knowledge Graph and Benchmark},
  author    = {Nguy{\^e}n Ti{\'e}n {\DJ}{\d{a}}t},
  year      = {2026},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/datbazuka2502/vicivil-tkg}
}
```

## Liên quan

- Paper: `docs/report/ViCivil-TKG_paper.pdf` (IMRaD, đầy đủ bảng + hình + thống kê).
- DATASHEET: `DATASHEET.md` — motivation, composition, maintenance, limitations.
- Kit thẩm định của con người: `docs/annotation/` — guideline chấm, bảng 60 câu (50 lõi + 10 mở rộng, phân tầng) và script tính κ Cohen/Fleiss.
- Contact: mở issue trên GitHub repo.
