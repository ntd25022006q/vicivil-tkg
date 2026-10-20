# Báo cáo NCKH — ViCivil-TKG

> Bản chính thức trình bày theo chuẩn báo cáo nghiên cứu là tệp PDF:
> **`docs/report/ViCivil-TKG_bao-cao.pdf`** (25 trang, dựng bằng XeLaTeX, mã nguồn
> `docs/report/report.tex`). Tệp Markdown này là bản rút gọn cùng nội dung để đọc nhanh.

Phiên bản dữ liệu **v1.5.5** · Ngày: 20/10/2026
Kho mã: `github.com/ntd25022006q/vicivil-tkg` · Gương: `huggingface.co/datasets/datbazuka2502/vicivil-tkg`

---

## Tóm tắt

Luật dân sự Việt Nam không tồn tại trong một bản duy nhất. Bộ luật Dân sự 1995 bị thay bằng bản 2005,
bản 2005 bị thay bằng bản 2015; các luật chuyên ngành liên tục sửa đổi lẫn nhau. Khi tra cứu, câu hỏi
đầu tiên không phải "điều khoản nào nói về điều này" mà là **"vào thời điểm đó, điều khoản nào còn
có hiệu lực"**.

Công trình này dựng một bộ dữ liệu mở trả lời được câu hỏi đó: từ sáu PDF công báo chính thức,
bộ luật được cắt thành **11.267 đoạn văn bản** theo cấu trúc pháp lý (Điều – Khoản – Điểm), mỗi đoạn
mang một mã ổn định. Trên nền đó dựng **đồ thị tri thức 33 văn bản, 21 quan hệ** có mốc thời gian;
xây **281 câu hỏi có đáp án** để đo chất lượng truy hồi; và dựng **trang xem một tệp HTML** chạy
được offline để kiểm chứng bằng mắt.

Kết quả đo trên 281 câu: Hit@1 = 0,452 · Hit@3 = 0,658 · Hit@5 = 0,726 · Hit@10 = 0,794 · MRR = 0,569.
Trên 245 câu đã được tác giả xác minh: Hit@1 = 0,502.

**Từ khóa:** luật dân sự; tri thức thời gian; dữ liệu mở; tra cứu pháp lý; truy hồi thông tin; mã hoá
văn bản; đồ thị tri thức.

---

## Chương 1 — Đặt vấn đề và mục tiêu

**Bối cảnh.** Mỗi văn bản chỉ có hiệu lực trong một khoảng thời gian; văn bản hợp nhất (VBHN) có
thể nhập gộp hàng chục văn bản đã hết hiệu lực. Dữ liệu luật trên mạng phần lớn ở dạng văn bản phẳng
theo từng văn bản, thiếu ba thứ: các đoạn văn bản nhỏ để trích dẫn chính xác, quan hệ giữa các văn
bản theo thời gian, và cơ chế đo chất lượng.

**Phương pháp.** Thu thập từ công báo chính thức (Python) → cắt chunk theo cấu trúc pháp lý và gán
mã phân cấp → mã hoá 768 chiều → trích thực thể và quan hệ → gán khoảng hiệu lực → làm bộ 281 câu
hỏi có đáp án và chấm điểm → dựng đồ thị và trình xem bằng **AntV G6 5.1.1** và **Vega-Lite 5.21.0**
(hai thư viện mở chuyên dụng, nhúng trực tiếp, không cần mạng).

**Đóng góp.** (i) bộ dữ liệu 11.267 chunk có mã ổn định, tái sử dụng được; (ii) đồ thị tri thức có
chiều thời gian, tự kiểm ở ba mốc; (iii) bộ 281 câu hỏi kèm cơ chế chia tầng độ tin cậy và kết quả
đo công khai; (iv) trình xem một tệp, xuất PNG và GEXF để mở bằng Gephi.

## Chương 2 — Dữ liệu và quy trình xây dựng

| Bước | Nội dung | Tệp đầu ra | Kết quả |
| --- | --- | --- | --- |
| A | Lấy PDF công báo, lưu nguồn và ngày lấy | `provenance/law_sources.json` | 6 tệp |
| B | Phân biệt PDF chữ và PDF ảnh | `sources_raw/` | ảnh vào hàng chờ OCR |
| C | Cắt nhỏ theo Điều – Khoản – Điểm, gán mã | `data/civil_chunks.jsonl` | 11.267 chunk |
| D | Lọc luật dân sự, chặn chunk rỗng/trùng mã | `provenance/law_audit.json` | 0 lỗi |
| E | Mã hoá mỗi chunk thành vectơ 768 chiều | `index/vdb_chunks.json` | 11.267 vectơ |
| F | Rút thực thể và quan hệ giữa các chunk | `index/kv_store_*.json` | 3 kho chỉ mục |
| G | Gán khoảng hiệu lực, dựng chuỗi kế thừa | `provenance/temporal_graph.json` | 33 luật |
| H | Làm câu hỏi có đáp án và chấm điểm | `benchmark/law_eval_v12.json` | 281 câu |
| I | Xuất đồ thị GEXF và dựng trang xem | `docs/graph/` | 1 trang xem |
| J | Băm SHA-256, đồng bộ hai gương | `SHA256SUMS` | 84 tệp |

**Chunk và mã.** Chunk là đơn vị trích dẫn nhỏ nhất mà luật dân sự dùng (Điều – Khoản – Điểm), mã
ổn định dạng `BLDS2015|Dieu27|Khoan1|Diema`. Mã bám theo cấu trúc pháp lý vì: (i) ổn định – nếu mã đổi
sau mỗi lần chạy lại thì 11.267 vectơ và mọi cạnh dẫn chiếu phải làm lại; (ii) trích dẫn chính xác –
giữ ranh giới Điểm a/b/c để trích đủ ý; (iii) chia sẻ được – người khác dùng chung mã này được.

**Ba tầng lưu trữ.** (1) Tra theo mã: chunk 11.267 mục, thực thể 14.538 mục, quan hệ 20.311 mục.
(2) Tra theo nghĩa: 11.267 vectơ 768 chiều. (3) Tra theo quan hệ và thời điểm: đồ thị 33 luật,
21 quan hệ.

**Phân bố dữ liệu.** Bốn văn bản chiếm hơn một nửa số chunk → không thể dùng một ngưỡng cắt chunk
duy nhất cho toàn bộ kho.

![Số chunk mở theo văn bản](figures/fig11_phan-bo-chunk.png)
*_Hình 1. Số chunk mở theo từng văn bản. Biểu đồ vẽ bằng Vega-Lite từ tệp
`data/civil_chunks.jsonl` trong kho._*

## Chương 3 — Đồ thị tri thức và chiều thời gian

![Đồ thị năm 2026](figures/fig05_graph_2026.png)
*_Hình 2. Trạng thái đồ thị tại năm 2026: 14 văn bản còn hiệu lực, các luật đã hết hiệu lực làm mờ._*

| Quan hệ | Số cạnh | Nghĩa |
| --- | --- | --- |
| REPLACES | 3 | Luật mới thay thế luật cũ |
| AMENDS | 17 | Sửa đổi điều khoản cụ thể |
| CONSOLIDATES | 1 | Hợp nhất |

Quan hệ sửa đổi chỉ được nhận khi đọc được từ lời nói đầu của văn bản hợp nhất, không tin đoạn trích
từ công cụ tìm kiếm. Có một lần tin đoạn tìm kiếm đã tạo ra 142 cạnh sai; sau đó dựng lại từ văn bản gốc.

![Đồ thị năm 2012](figures/fig06_graph_2012.png)
*_Hình 3. Cùng đồ thị, tại thời điểm năm 2012: chỉ 4 văn bản còn hiệu lực._*

| Mốc thời gian | Số luật còn hiệu lực | Kiểm tra tự động trong dữ liệu |
| --- | --- | --- |
| 2000-01-01 | 1 | Chỉ Bộ luật Dân sự 1995 |
| 2010-06-01 | 1 | Chỉ Bộ luật Dân sự 2005 |
| 2020-06-01 | 2 | Bộ luật Dân sự 2015 và Luật Hôn nhân và Gia đình 2014 |
| 2026 | 14 | Trạng thái hiện tại của trang xem |

## Chương 4 — Trình xem

![Phổ thời gian](figures/fig07_timeline_tab.png)
*_Hình 4. Phổ thời gian, dựng bằng Vega-Lite từ tệp spec công khai `law_timeline.vl.json`._*

![Thẻ tin khi rê chuột](figures/fig08_tooltip.png)
*_Hình 5. Rê chuột vào một luật: số hiệu, khoảng hiệu lực, số chunk, số lần dẫn chiếu; chuỗi kế thừa
của luật đó được làm sáng._*

![Khung chi tiết](figures/fig09_drawer.png)
*_Hình 6. Khung chi tiết: Bộ luật Dân sự 2015 – số hiệu 91/2015/QH13, hiệu lực từ 01/01/2017 đến nay,
1.838 chunk, 145 lần dẫn chiếu, quan hệ thay thế với Bộ luật Dân sự 2005._*

| Vai trò | Thành phần |
| --- | --- |
| Vẽ đồ thị | AntV G6 5.1.1 (MIT) – kéo/zoom/phóng to khi rê chuột, plugin minimap, tooltip, lưới nền |
| Vẽ biểu đồ | Vega-Lite 5.21.0 (BSD-3) |
| Nhúng biểu đồ | vega-embed 6.26.0 (BSD-3) |
| Trao đổi đồ thị | GEXF 1.3 (mở bằng Gephi, Gephi-Lite) |

Trang xem viết thành **một tệp HTML duy nhất**, nhúng sẵn cả bốn thư viện, nên chạy được khi mất mạng
và mở trực tiếp từ ổ đĩa. Trước khi phát hành, trang được kiểm tra trên Chromium, trên đúng Google
Chrome và trên Microsoft Edge, yêu cầu không lỗi JavaScript nào.

## Chương 5 — Thử nghiệm và đánh giá

![Kết quả truy hồi](figures/fig10_ket-qua-truy-hoi.png)
*_Hình 7. Kết quả truy hồi trên 281 câu hỏi có đáp án. Biểu đồ vẽ bằng Vega-Lite từ tệp
`benchmark/law_eval_v12.json` trong kho._*

| Chỉ số | Toàn bộ 281 câu | 245 câu đã tác giả xác minh |
| --- | --- | --- |
| Tìm đúng ở lần 1 (Hit@1) | 0,452 | 0,502 |
| Tìm đúng trong 3 lần (Hit@3) | 0,658 | 0,678 |
| Tìm đúng trong 5 lần (Hit@5) | 0,726 | 0,731 |
| Tìm đúng trong 10 lần (Hit@10) | 0,794 | 0,796 |
| Độ tin cậy tổng hợp (MRR) | 0,569 | — |

**Phân tích.** 32 câu thuộc nhóm "đáp án đúng nhưng hệ thống trả về nguồn khác" chỉ đạt Hit@1 = 0,062,
kéo số trung bình toàn bộ xuống. Đây là hạn chế của **thang đo**, chưa chắc là hạn chế của hệ thống – vì
vậy báo cáo lấy số trên tập 245 câu đã xác minh làm con số chính. So sánh giữa các hệ khác nhau cần
kiểm định thống kê (McNemar, Wilcoxon) trước khi khẳng định hệ này tốt hơn hệ kia.

## Chương 6 — Khó khăn gặp phải và hướng phát triển

| Khó khăn | Biểu hiện | Đã xử lý thế nào |
| --- | --- | --- |
| Tin đoạn trích tìm kiếm làm nhiễu quan hệ | 142 cạnh sửa đổi sai | Chỉ nhận quan hệ từ lời nói đầu văn bản hợp nhất |
| Ngày hỏi nằm ngoài thời gian hiệu lực | 48 câu hỏi không dùng được | Kiểm tra ngày hỏi trước khi nhận câu |
| Ghi đè làm mất dữ liệu đã trích | mất ~2.900 dòng | Bắt buộc sao lưu trước khi ghi đè |
| Hệ thống trả nguồn khác với đáp án đúng | 32 câu chỉ đạt 0,062 | Công bố đúng số thay vì làm đẹp con số |
| PDF ảnh không có lớp chữ | không tách được chunk | Tách riêng hàng chờ đọc lại, không đoán |
| Thư viện vẽ chạy sai trên một số trình duyệt | trang trắng, không báo lỗi | Chạy thử trên Chrome và Edge thật trước khi phát hành |

**Hướng phát triển:** (1) xuất RDF/JSON-LD để nạp vào kho tri thức chuẩn; (2) đưa đoạn văn bản lên
đồ thị (nút cấp Điều/Khoản); (3) sửa thang đo để chấp nhận nhiều đáp án tương đương và dùng mô hình
ngôn ngữ lớn làm người chấm; (4) pipeline tăng dần khi có văn bản mới; (5) bổ sung văn bản chưa số hoá.

## Chương 7 — Kết luận

Đã dựng được một bộ dữ liệu mở có chiều thời gian: 11.267 chunk có mã, đồ thị 33 văn bản với 21
quan hệ có nhãn, 281 câu hỏi có đáp án kèm kết quả đo, và một trình xem chạy offline. Chất lượng
truy hồi đạt Hit@5 = 0,726 (toàn bộ tập) và 0,731 (tập đã xác minh). Phần còn thiếu đã được nêu rõ:
chưa xuất RDF/JSON-LD, chưa có DOI, đồ thị mới ở cấp văn bản, và phần chênh lệch điểm số còn lớn
do thang đo. Ưu tiên ngắn hạn: xuất RDF/JSON-LD và đưa đoạn văn bản lên đồ thị.

## Phụ lục

- **Bản đáp án yêu cầu** (xem Bảng A.1 trong PDF).
- **Nguồn từng hình**: Hình 1, 7 vẽ bằng Vega-Lite từ tệp dữ liệu trong kho; Hình 2–6 là ảnh chụp
  trực tiếp từ trang xem đang chạy.
- **Kiểm tra trước khi phát hành**: SHA-256 84/84 tệp khớp; quét chữ ẩn/khoá bí mật: không phát
  hiện; mọi tệp JSON/JSONL/GEXF mở được; 0 lỗi JavaScript trên Chromium, Chrome và Edge; trang
  chạy được khi mất mạng; truy vấn thời gian đúng ở ba mốc 2000, 2010, 2020.
