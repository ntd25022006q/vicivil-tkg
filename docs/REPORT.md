# Báo cáo: trang xem luật dân sự ViCivil-TKG

Phiên bản v1.5.2 · Ngày làm: tháng 10 năm 2026  
Kho mã: github.com/ntd25022006q/vicivil-tkg  
Gương phát hành: huggingface.co/datasets/datbazuka2502/vicivil-tkg  
Tất cả hình ảnh trong báo cáo đều là ảnh chụp từ trang đang chạy, hoặc sơ đồ vẽ bằng công cụ mở Mermaid, hoặc chụp nguyên từ tệp gốc trong kho. Không có hình nào được vẽ tay hoặc bịa số liệu.

---

## 1. Giới thiệu

Luật dân sự Việt Nam không có một bản duy nhất. Bộ luật 1995 bị thay bằng bản 2005, bản 2005 bị thay bằng bản 2015; luật hôn nhân gia đình, luật tố tụng… liên tục sửa đổi. Khi tra cứu một vấn đề pháp lý, câu hỏi đầu tiên không phải "điều khoản nào nói về điều này" mà là **"vào thời điểm đó, điều khoản nào còn có hiệu lực"**?

Trang xem này giúp trả lời câu hỏi đó. Nó gồm bốn phần:

- kho chứa các đoạn văn bản đã cắt nhỏ và gán mã;
- đồ thị tri thức liên hệ các luật với nhau;
- bộ 281 câu hỏi để kiểm tra xem hệ thống có tìm đúng hay không;
- trang xem để ai cũng có thể mở, xem, kéo thời gian.

Số liệu chung:

| Chỉ số | Giá trị |
| --- | --- |
| Văn bản luật trong kho | 17 văn bản |
| Đoạn văn bản cắt nhỏ (chunk) | 11.267 đoạn |
| Văn bản trong đồ thị | 33 |
| Quan hệ giữa các văn bản | 21 |
| Câu hỏi kiểm tra | 281 câu |
| Phần mềm dùng | 4 thư viện mở, không cần mạng, không cần cài đặt để chạy |

---

## 2. Quy trình làm từ A đến Z

Mỗi bước trong sơ đồ sau đều có một tệp đầu ra, và mọi con số trong báo cáo đều mở được file đó để kiểm chứng.

![Sơ đồ quy trình từ A đến Z](figures/fig01_quy-trinh.png)
*_Hình 1. Quy trình A → Z, vẽ bằng công cụ Mermaid. Nguồn: docs/report/diagrams/pipeline.mmd_*

Các bước:

**A. Lấy 6 tệp PDF chính thức từ công báo** — Bộ luật Dân sự 1995, 2005, 2015; Luật Hôn nhân và Gia đình 2014; Luật Tố tụng 2017; Nghị định 152/2026. Mỗi tệp lưu kèm đường dẫn và ngày lấy.

**B. Kiểm tra PDF có chữ hay là ảnh.** Ảnh đưa vào hàng chờ đọc lại (OCR) thay vì đoán.

**C. Cắt nhỏ văn bản thành đoạn (chunk).** Tách theo Điều → Khoản → Điểm. Mỗi đoạn có mã riêng, ví dụ `BLDS2015|Dieu27|Khoan1|Diema`. Tổng cộng 11.267 đoạn.

**D. Lọc ra luật dân sự, kiểm tra chất lượng.** Chặn đoạn rỗng, đoạn trùng mã, luật mồ côi về thời gian.

**E. Mã hoá từng đoạn thành 768 con số** (để máy hiểu được nghĩa chung của đoạn).

**F. Rút tên thực thể và quan hệ giữa các đoạn.**

**G. Gán thời gian cho từng văn bản** — từ ngày nào đến ngày nào có hiệu lực.

**H. Làm 281 câu hỏi có đáp án** và chấm xem hệ thống tìm đúng bao nhiêu.

**I. Xuất đồ thị ra định dạng GEXF 1.3** (mở được bằng Gephi) và dựng trang xem.

**J. Băm mã SHA-256 cho mọi tệp**, đồng bộ hai nơi, đóng thẻ phiên bản.

---

## 3. Dữ liệu dùng: 11.267 đoạn văn bản

![Một đoạn văn bản đã gán mã](figures/fig03_chunk_sample.png)
*_Hình 2. 14 chunk đầu tiên của tệp data/civil_chunks.jsonl (mỗi dòng là một chunk). Chụp nguyên văn từ tệp gốc._*

Mỗi đoạn là một đoạn văn bản thuần khiết, gắn kèm:

| Trường | Ý nghĩa |
| --- | --- |
| chunk_id | Mã riêng, ví dụ `BLDS2015|Dieu1` |
| law_id | Mã luật, ví dụ `BLDS2015` |
| dieu | Số Điều |
| khoan | Số Khoản |
| diem | Số Điểm |
| tieu_de | Tiêu đề đoạn |
| content | Nội dung đoạn |
| source_url | Đường dẫn gốc |

Mã này không đổi sau mỗi lần chạy lại — nên mọi tính toán đã làm trước vẫn còn đúng.

---

## 4. Ba nơi lưu trữ trên cùng một bộ dữ liệu

Cùng 11.267 đoạn văn bản, lưu theo ba cách để tra cứu khác nhau:

![Ba tầng lưu trữ](figures/fig04_ba-tang-luu-tru.png)
*_Hình 3. Sơ đồ vẽ bằng Mermaid. Nguồn: docs/report/diagrams/index-layers.mmd_*

| Tầng | Lưu gì | Dùng để làm gì |
| --- | --- | --- |
| Tầng 1 | Tra theo mã đoạn (11.267 mục), tên thực thể (14.538 mục), quan hệ (20.311 mục) | Tra chính xác: đoạn nào, tên gì |
| Tầng 2 | Mã hoá 768 con số cho từng đoạn | Tra nghĩa: câu hỏi → đoạn gần nhất về ý nghĩa |
| Tầng 3 | Đồ thị 33 văn bản, 21 quan hệ | Tra theo quan hệ: luật nào thay luật nào, tại thời điểm nào còn hiệu lực |

---

## 5. Đồ thị tri thức

Đồ thị này chỉ chứa các **văn bản luật** (33 nút) và **quan hệ giữa các luật** (21 cạnh):

| Quan hệ | Số lượng | Nghĩa |
| --- | --- | --- |
| Thay thế (REPLACES) | 3 | Luật mới thay luật cũ |
| Sửa đổi (AMENDS) | 17 | Sửa điều khoản cụ thể |
| Hợp nhất (CONSOLIDATES) | 1 | Hợp nhất |

Quan hệ sửa đổi chỉ được nhận khi đọc được từ lời nói đầu của văn bản hợp nhất — không tin vào đoạn trích từ tìm kiếm. Có lần tin đoạn tìm kiếm đã tạo ra 142 cạnh sai, sau đó đã sửa.

Mỗi nút trên đồ thị còn mang số đoạn văn bản và số lần được dẫn chiếu — từ đó nhảy xuống được tận đoạn văn bản gốc.

---

## 6. Cập nhật theo thời gian

Đồ thị này có chiều thời gian. Mỗi nút có `[từ ngày, đến ngày]`. Kéo thanh thời gian xem trạng thái tại từng năm:

![Đồ thị năm 2026](figures/fig05_graph_2026.png)
*_Hình 4. Trạng thái năm 2026: 14 văn bản còn hiệu lực, các luật cũ làm mờ._*

![Đồ thị năm 2012](figures/fig06_graph_2012.png)
*_Hình 5. Trạng thái năm 2012: chỉ 4 văn bản còn hiệu lực._*

| Năm | Số văn bản còn hiệu lực |
| --- | --- |
| 2026 | 14 |
| 2012 | 4 |

---

## 7. Trang xem

Trang xem có hai phần:

**Mạng kế thừa** — vẽ bằng thư viện AntV G6. Có thanh thời gian, kéo lại toàn bộ đồ thị tính lại trạng thái; rê chuột vào một luật sẽ sáng đúng chuỗi kế thừa của nó; bấm vào mở khung chi tiết.

![Phổ thời gian](figures/fig07_timeline_tab.png)
*_Hình 6. Tab phổ thời gian, dựng bằng thư viện Vega-Lite từ một spec công khai._*

![Thẻ tin khi rê chuột](figures/fig08_tooltip.png)
*_Hình 7. Rê chuột vào một luật: số hiệu, thời gian hiệu lực, số đoạn, số lần dẫn chiếu._*

![Khung chi tiết văn bản](figures/fig09_drawer.png)
*_Hình 8. Khung chi tiết: ví dụ Bộ luật Dân sự 2015, số hiệu 91/2015/QH13, có hiệu lực từ 01/01/2017 đến nay, 1.838 đoạn, 145 lần dẫn chiếu._*

**Phổ thời gian** — vẽ bằng Vega-Lite, mo spec công khai, ai cũng có thể dùng lại.

**Xuất PNG** — nút trên trang lưu hình ảnh của đồ thị hiện tại.

---

## 8. Thử nghiệm

![Kết quả truy hồi](figures/fig10_eval.png)
*_Hình 9. Kết quả trên 281 câu hỏi có đáp án._*

Bộ kiểm tra gồm 281 câu hỏi; ngày hỏi phải nằm trong khoảng hiệu lực của văn bản chứa đáp án:

| Chỉ số | Toàn bộ 281 câu | 245 câu đã được tác giả xác minh |
| --- | --- | --- |
| Tìm đúng ở lần 1 (Hit@1) | 0,452 | 0,502 |
| Tìm đúng trong 3 lần (Hit@3) | 0,658 | 0,678 |
| Tìm đúng trong 5 lần (Hit@5) | 0,726 | 0,731 |
| Tìm đúng trong 10 lần (Hit@10) | 0,794 | 0,796 |
| Độ tin cậy tổng hợp (MRR) | 0,569 | — |

**Điểm đáng nói thẳng:** 32 câu thuộc nhóm "đáp án đúng nhưng trả về nguồn khác" chỉ đạt 0,062. Đây là vấn đề của thang đo, chưa chắc là vấn đề của hệ thống — nên báo cáo con số trên tập đã xác minh làm con số chính.

---

## 9. Phân bố đoạn văn bản

![Phân bố đoạn theo văn bản](figures/fig11_chunk_distribution.png)
*_Hình 10. Vẽ từ dữ liệu thật của tệp data/civil_chunks.jsonl._*

4 văn bản chiếm hơn một nửa số đoạn. Do đó không thể cắt đoạn theo một quy tắc duy nhất cho tất cả.

---

## 10. Chia sẻ cho người khác

![Trích từ tệp GEXF](figures/fig12_gexf.png)
*_Hình 11. 40 dòng đầu của tệp docs/graph/law_graph.gexf (tệp có 696 dòng). Chụp nguyên văn từ tệp gốc._*

Đồ thị được xuất ra định dạng GEXF 1.3, mở được bằng Gephi và Gephi-Lite. Mọi thuộc tính thời gian và số đoạn đều đi kèm. Phần chưa làm: chưa xuất định dạng RDF/JSON-LD, chưa cấp mã DOI cho từng phiên bản.

---

## 11. Gặp khó khăn gì và đề xuất cải tiến

| Khó khăn | Đã xử lý thế nào |
| --- | --- |
| Tin đoạn tìm kiếm tạo ra 142 cạnh sai | Chỉ nhận quan hệ từ lời nói đầu văn bản hợp nhất |
| Ngày hỏi nằm ngoài thời gian hiệu lực | Kiểm tra ngày hỏi trước khi nhận câu |
| Ghi đè làm mất dữ liệu | Bắt buộc sao lưu trước khi ghi đè |
| Truy hồi trả về nguồn khác với đáp án đúng | Công bố đúng số thay vì làm đẹp con số |
| PDF ảnh không có chữ | Tách riêng hàng chờ đọc lại, không đoán |
| Trang bị trắng trên một số trình duyệt | Chạy thử trên Chrome và Edge thật trước khi phát hành |

**Đề xuất làm tiếp:**

1. Xuất định dạng RDF/JSON-LD để nạp vào kho tri thức chuẩn (Neo4j, rdf4j…).
2. Đưa đoạn văn bản lên đồ thị (nút cấp Điều/Khoản nối vào luật).
3. Sửa thang đo: chấp nhận nhiều đáp án đúng về mặt pháp lý.
4. Khi có văn bản mới, chỉ tính toán phần mới thay vì chạy lại toàn bộ.
5. Thêm văn bản chưa số hóa — 4 câu hỏi chưa đạt trọn vẹn có liên quan đến vấn đề này.

---

## 12. Kiểm tra lại trước khi phát hành

| Kiểm tra | Kết quả |
| --- | --- |
| Mã SHA-256 của mọi tệp | 60/60 khớp, hai gương giống nhau |
| Quét chữ ẩn, khoá bí mật | Không phát hiện |
| Mọi tệp JSON/JSONL/GEXF mở được | Có |
| Chạy trên Chrome thật | Không có lỗi JavaScript |
| Chạy trên Edge thật | Không có lỗi JavaScript |
| Trang xem chạy khi mất mạng | Có (không cần CDN) |

---

## Phụ lục: cách làm mỗi hình ảnh

| Hình | Có gì | Làm bằng công cụ gì | Nguồn |
| --- | --- | --- | --- |
| 1. Quy trình A→Z | Sơ đồ 10 bước | Mermaid 12.2.0 | docs/report/diagrams/pipeline.mmd |
| 2. Mẫu đoạn văn bản | Chụp nguyên từ tệp data/civil_chunks.jsonl | Chụp từ trình duyệt | data/civil_chunks.jsonl (dòng 1–14) |
| 3. Ba tầng lưu trữ | Sơ đồ 3 tầng | Mermaid 12.2.0 | docs/report/diagrams/index-layers.mmd |
| 4. Đồ thị 2026 | Ảnh chụp trang đang chạy | agent-browser + Chrome thật | docs/graph/explorer.html |
| 5. Đồ thị 2012 | Ảnh chụp trang đang chạy | agent-browser + Chrome thật | docs/graph/explorer.html |
| 6. Phổ thời gian | Ảnh chụp trang đang chạy | agent-browser + Chrome thật | docs/graph/explorer.html |
| 7. Tooltip | Ảnh chụp trang đang chạy | agent-browser + Chrome thật | docs/graph/explorer.html |
| 8. Khung chi tiết | Ảnh chụp trang đang chạy | agent-browser + Chrome thật | docs/graph/explorer.html |
| 9. Biểu đồ đánh giá | Vẽ từ dữ liệu thật | Vega-Lite | benchmark/law_eval_v12.json |
| 10. Phân bố đoạn | Vẽ từ dữ liệu thật | Vega-Lite | data/civil_chunks.jsonl |
| 11. GEXF | Trích nguyên từ tệp thực tế | Chụp từ trình duyệt | docs/graph/law_graph.gexf |

Mọi con số trong báo cáo đều lấy từ file trong kho, có thể mở kiểm tra trực tiếp. Trang xem chạy hoàn toàn khi mất mạng (không cần CDN, không cần cài đặt).

---
*Báo cáo này đi kèm với bản Word tương tự (ViCivil-TKG_BAO-CAO.docx) cùng nội dung và hình ảnh.*
