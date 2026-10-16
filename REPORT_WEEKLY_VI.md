# BÁO CÁO TUẦN — Dataset đồ thị tri thức thời gian luật dân sự Việt Nam (ViCivil-TKG)

## 1. Mục tiêu tuần
Dựng kho dữ liệu luật dân sự có gán nhãn ID chunk, đồ thị tri thức (KG) theo
cách paper ADGR, cập nhật theo hướng đồ thị động + thời gian hiệu lực; khó
khăn gặp phải và đề xuất cải tiến. Mọi số liệu chạy thật trên GPU, truy được
file gốc, không mock.

## 2. Quy trình thực hiện (8 bước, mỗi bước có chốt kiểm tra)
1. **Crawl Công báo** (542 trang → 937 số → 3.253 văn bản, checkpoint từng
   trang, lịch sự 1,2s/request).
2. **Tải + lọc nguồn** (thử 7 nguồn: PDF hợp nhất/VBHN/MOJ/CDN > mirror tĩnh >
   DOC công vụ > per-article crawl; bỏ nguồn chặn bot, PDF scan, trang đòi
   login; file <10KB loại + ghi danh sách).
3. **Chunk phân cấp** (regex Điều→Khoản→Điểm, ID `Luật|Điều|Khoản|Điểm`;
   3 parser cho 3 kiểu text; khử trùng Mục lục giữ khối dài nhất; đếm Điều đối
   chiếu luật định).
4. **Lọc dân sự 3 vòng** (regex → duyệt tay 120 tiêu đề → allowlist khóa tay;
   backup trước mỗi lần xóa).
5. **Trích KG** (prompt few-shot + validator format/tên cụ thể/relation nối
   entity; giải dẫn chiếu tất định bằng regex, không qua LLM).
6. **Đồ thị thời gian** (luật mang khoảng hiệu lực + cạnh kế thừa REPLACES/
   CONSOLIDATES; hàm `law_as_of(date)` tự kiểm tra).
7. **Benchmark + eval** (câu tay temporal + câu sinh từ chunk thật có lọc rác;
   gold verify tồn tại; retriever lai BM25+dense+fusion+expansion+rerank;
   test abstain).
8. **Audit + provenance** (trùng/rỗng/mồ côi/gold = 0; chunk nào cũng có
   nguồn + loại nguồn; gap sót ghi hết vào datasheet).

## 3. Kết quả số cuối (đo thật, n=211)
- Kho: **10.212 chunk / 17 luật** (BLDS 1995/2005/2015, HN&GĐ 2000/2014/VBHN-2025,
  Hộ tịch 2014/2026, Nuôi con nuôi 2010, Hòa giải 2026, Tố tụng + Thi hành án
  + Bồi thường + văn bản hướng dẫn).
- KG: 10.125 dòng trích → **~32k entity + ~18k relation + ~4,3k cạnh dẫn chiếu**.
- Retrieval cuối: **Hit@1 0,180 • Hit@3 0,351 • Hit@5 0,474 • Điều@5 0,592**;
  abstain đúng 2/2; dense thuần 0,000.
- Provenance: official-line/mirror + source từng chunk; audit trùng/rỗng/mồ côi/gold = 0.
- Provenance: 45% official-line / 55% mirror (lọc official-only được).

## 4. Sáu khó khăn và đề xuất (nội dung chính)
1. **Nguồn chặn bot/login** → ma trận 7 nguồn theo độ ưu tiên + ghi source_type;
   không phụ thuộc 1 nguồn.
2. **Mỗi PDF một kiểu text** (dòng/rải từ/scan/DOC/RTF-VNI) → 3 parser + router
   tự chọn (đo từ/dòng) + cách ly scan chờ OCR + bảng VNI đợt 2 (cơ chế 2 font
   đã chẩn đoán xong).
3. **Khoản dính dòng, trùng Mục lục** → dedup giữ khối dài nhất + drop số Điều
   dẫn chiếu + audit gate.
4. **Dẫn chiếu chéo** → resolver regex tất định 100%, tách việc chắc (regex)
   khỏi việc đoán (LLM).
5. **Luật sửa đổi** → khoảng hiệu lực + superseded_by + version quý + delta;
   cập nhật hàng tháng.
6. **Dense thuần chết** → lai + fusion thay rerank-đè (đo được chỗ tụt) +
   pipeline thích ứng (dễ đi tắt, khó bung đồ thị).

## 5. Hạn chế còn lại (trung thực) và hướng tuần sau
- 3 luật gốc thiếu (THADS-2008 bản gốc, TNBTCNN-2017 bản gốc đã có qua hethongphapluat,
  còn lại VBHN cover) — có VBHN thay thế 95% nội dung hiệu lực.
- Gold máy sinh (đã duyệt tay 38 ca nghi) — cần duyệt chuyên gia (luật sư).
- Mirror 55% — cần đối chiếu gốc khi dùng ra tòa (đã ghi source_type để lọc).
- Tuần sau: benchmark lên 200+ câu luật mới → đo baseline đầy đủ → datasheet +
  đẩy GitHub/HuggingFace (cần acc HF) → viết paper dataset.

## 6. File kết quả (trên GPU A30, /home/devlab1/law_workspace/)
- `runs/civil_chunks.jsonl` (kho chunk), `civil_extract.json` (trích),
  `law_data/` (index 8 file), `temporal_graph.json`, `law_bench_*.json`,
  `law_audit.json`, `law_sources.json`, `src/*.py` (toàn bộ pipeline).
