# BÁO CÁO — ViCivil-TKG
## Khung tri thức thời gian của luật dân sự Việt Nam

Phiên bản dữ liệu: **v1.5.2** · Ngày lập: 19/10/2026
Kho mã: `github.com/ntd25022006q/vicivil-tkg` · Gương phát hành: `huggingface.co/datasets/datbazuka2502/vicivil-tkg`

---

## 1. Đặt vấn đề và mục tiêu

Luật dân sự Việt Nam không tồn tại trong một bản duy nhất. Bộ luật Dân sự 1995 bị
thay bằng bản 2005, bản 2005 bị thay bằng bản 2015; các luật chuyên ngành hôn nhân
và gia đình, tố tụng, thừa tụng, doanh nghiệp tư nhân liên tục sửa đổi lẫn nhau. Khi
tra cứu một vấn đề pháp lý, câu hỏi đầu tiên không phải "điều khoản nào nói về
điều này" mà là **"vào thời điểm đó, điều khoản nào đang có hiệu lực"**.

Mục tiêu của công trình là dựng một bộ dữ liệu có thể trả lời đúng câu hỏi đó, gồm
bốn phần: kho chunk đã gán nhãn, đồ thị tri thức có chiều thời gian, bộ benchmark
để đo chất lượng truy hồi, và một trình xem để kiểm chứng bằng mắt.

| Chỉ số | Giá trị |
| --- | --- |
| Văn bản luật trong corpus | 17 (kèm 16 văn bản sửa đổi bên ngoài) |
| Chunk mở | 11.267 |
| Node đồ thị / cạnh | 33 / 21 |
| Câu hỏi vàng | 281 |
| Phụ thuộc phần mềm | 4 thư viện mở, không CDN, không build tool |

---

## 2. Quy trình thực hiện từ A đến Z

![Quy trình A đến Z](figures/fig01_pipeline.png)

Mỗi bước trong sơ đồ đều có **một file đầu ra kiểm chứng được** — không có con số nào
trong báo cáo này mà không mở được file tương ứng để đối chiếu.

**A. Thu thập nguồn.** Sáu tệp PDF chính thức từ công báo: Bộ luật Dân sự 1995, 2005,
2015; Luật Hôn nhân và Gia đình 2014; Luật Tố tụng 2017; Nghị định 152/2026. Mỗi tệp
lưu kèm URL nguồn, loại nguồn và ngày thu thập trong `provenance/law_sources.json`.

**B. Phân loại và số hóa.** Tách PDF có lớp chữ khỏi PDF scan; ảnh scan đưa vào hàng
chờ OCR thay vì đoán.

**C. Chia chunk theo cấu trúc pháp lý.** Tách theo Điều → Khoản → Điểm, gán ID phân
cấp ổn định (mục 3).

**D. Lọc phạm vi và kiểm tra chất lượng.** Chỉ giữ văn bản thuộc nhóm dân sự; audit
gate chặn chunk rỗng, chunk trùng ID, luật mồ côi về thời gian.

**E. Vector hoá.** Nhúng 768 chiều cho toàn bộ 11.267 chunk, khoá chính là `chunk_id`.

**F. Trích thực thể và quan hệ.** Chuẩn hoá tên thực thể rồi gộp thực thể cùng tên
giữa các văn bản; tạo cạnh dẫn chiếu giữa các chunk.

**G. Lớp thời gian.** Gán `[valid_from, valid_to)` cho từng luật, dựng chuỗi kế thừa.

**H. Benchmark và đánh giá.** 281 câu hỏi vàng, chấm Hit@k và MRR, tách theo tầng độ
tin cậy của đáp án (mục 8).

**I. Đồ thị và trình xem.** Xuất GEXF 1.3 cho Gephi; dựng trình xem bằng AntV G6 và
Vega-Lite (mục 7).

**J. Đóng gói và phát hành.** Băm SHA-256 toàn bộ 47 tệp, quét ký tự ẩn/khoá bí mật,
đồng bộ hai gương, đóng thẻ phiên bản.

---

## 3. Chia chunk và gán nhãn

![Mẫu chunk đã gán nhãn](figures/fig03_chunk_sample.png)

Chunk là đơn vị trích dẫn nhỏ nhất mà luật dân sự dùng để quy định nghĩa vụ: **Điều →
Khoản → Điểm**. ID sinh theo cấu trúc đó, ví dụ `BLDS2015|Dieu27|Khoan1|Diema`.

Ba lý do ID phải bám theo cấu trúc pháp lý:

1. **Ổn định.** Nếu ID đổi sau mỗi lần chạy lại, toàn bộ 11.267 vector và mọi cạnh
   dẫn chiếu đã xây phải làm lại.
2. **Trích dẫn chính xác.** Giữ nguyên ranh giới Điểm a/b/c giúp trích đủ ý, không
   thiếu không thừa.
3. **Chia sẻ được.** Người khác dùng chung `chunk_id` này để nối vào tập dữ liệu của
   họ mà không phải chia lại dữ liệu.

![Số chunk mở theo văn bản](figures/fig11_chunk_distribution.png)

Phân bố rất không đều: 4 văn bản chiếm hơn một nửa corpus, trong khi các luật chuyên
ngành chỉ vài trăm chunk. Đây chính là lý do không thể dùng một ngưỡng cắt chunk cố
định cho toàn bộ corpus.

---

## 4. Lưu trữ thành cơ sở dữ liệu các chunk có nhãn

![Ba tầng chỉ mục](figures/fig04_index_layers.png)

Cùng một tập 11.267 chunk được lập chỉ mục theo ba cách tra cứu khác nhau, mỗi tầng
phục vụ một dạng câu hỏi:

| Tầng | Cấu trúc | Dùng để trả lời |
| --- | --- | --- |
| T1 | 3 khoá–giá trị: chunk (11.267 mục), thực thể (14.538), quan hệ (20.311) | tra chính xác theo `chunk_id` hoặc tên thực thể đã chuẩn hoá |
| T2 | kho vectơ 768 chiều cho chunk, thực thể, quan hệ | tra ngữ nghĩa: câu hỏi → vector → top-k chunk gần nhất |
| T3 | đồ thị tri thức 33 node, 21 cạnh, có chiều thời gian | tra theo quan hệ: luật nào thay luật nào, tại thời điểm T văn bản nào còn hiệu lực |

Điểm cần nói thẳng: đây là **JSON + kho vectơ phẳng**, chưa phải cơ sở dữ liệu quan hệ
đầy đủ (mục 10, đề xuất 1).

---

## 5. Chia sẻ chunk và node cho người khác

![GEXF 1.3](figures/fig12_gexf.png)

Đồ thị được xuất ra **GEXF 1.3 ở chế độ `dynamic`**, nên khi mở bằng Gephi, Gephi-Lite
hay bất kỳ bộ đọc GEXF nào, người nhận đều có được đồ thị kèm chiều thời gian và mọi
thuộc tính (số hiệu, số chunk, số dẫn chiếu).

Phần chưa làm và nên làm tiếp: chưa xuất RDF/JSON-LD để nạp vào kho tri thức chuẩn,
chưa cấp DOI cho từng phiên bản.

---

## 6. Xây dựng đồ thị tri thức

![Đồ thị kế thừa năm 2026](figures/fig05_graph_2026.png)

Node là văn bản luật, mỗi node mang `[valid_from, valid_to)`. Cạnh có nhãn và mốc thời
gian:

| Quan hệ | Số cạnh | Nghĩa |
| --- | --- | --- |
| `REPLACES` | 3 | luật mới thay thế luật cũ |
| `AMENDS` | 17 | sửa đổi điều khoản cụ thể |
| `CONSOLIDATES` | 1 | hợp nhất |

Cách dựng quan hệ đáng nói: quan hệ `AMENDS` **chỉ được chấp nhận khi đọc được từ văn
bản gốc** (phần "lời nói đầu" của văn bản hợp nhất), không tin vào đoạn trích tìm
kiếm. Casebook đã ghi lại một lỗi cụ thể: tin đoạn snippet đã tạo ra 142 cạnh sai.

Mỗi node còn mang số chunk và số dẫn chiếu nội bộ, nối thẳng về tầng T1/T2 — tức là
từ đồ thị có thể nhảy xuống tận đoạn văn bản gốc.

---

## 7. Cập nhật theo đồ thị động và cập nhật thời gian

Cùng một đồ thị, hai thời điểm:

![Đồ thị năm 2026](figures/fig05_graph_2026.png)
![Đồ thị năm 2012](figures/fig06_graph_2012.png)

| Năm | Số văn bản đang hiệu lực | Trạng thái hiển thị |
| --- | --- | --- |
| 2026 | 14 | toàn bộ luật đã qua hiệu lực được làm mờ, tương lai ẩn |
| 2012 | **4** | luật chưa tới hạn bị tẩn, chỉ 4 luật sáng |

Kéo slider là toàn bộ đồ thị tính lại trạng thái; đây không phải hai bản vẽ khác nhau
mà là một đồ thị có chiều thời gian.

![Phổ thời gian](figures/fig07_timeline_tab.png)

Tab phổ thời gian dựng bằng Vega-Lite từ một spec công khai
(`law_timeline.vl.json`) — người khác muốn vẽ lại thì dùng đúng spec đó.

![Thẻ tin khi rê chuột](figures/fig08_tooltip.png)

![Khung chi tiết văn bản](figures/fig09_drawer.png)

Rê chuột vào một luật sẽ sáng đúng chuỗi kế thừa của luật đó; bấm vào mở khung chi tiết
với số hiệu, thời gian hiệu lực, số chunk, số dẫn chiếu và danh sách quan hệ.

---

## 8. Đánh giá chất lượng truy hồi

![Kết quả truy hồi](figures/fig10_eval.png)

Bộ benchmark gồm 281 câu hỏi vàng; ngày hỏi phải nằm trong khoảng hiệu lực của văn bản
chứa đáp án.

| Chỉ số | Toàn bộ 281 câu | 245 câu đã tác giả xác minh |
| --- | --- | --- |
| Hit@1 | 0,452 | 0,502 |
| Hit@3 | 0,658 | 0,678 |
| Hit@5 | 0,726 | 0,731 |
| Hit@10 | 0,794 | 0,796 |
| MRR | 0,569 | — |

Điểm đáng nói và đáng nói thẳng: **32 câu thuộc nhóm "đáp án đúng nhưng nguồn khác" chỉ
đạt Hit@1 = 0,062**, kéo toàn bộ số trung bình xuống. Đây là hạn chế của **thang đo**,
chưa chắc là hạn chế của hệ thống — cần tách hai thứ này khi báo cáo (mục 10).

---

## 9. Khó khăn gặp phải

| Khó khăn | Biểu hiện | Đã xử lý thế nào |
| --- | --- | --- |
| Quan hệ sửa đổi bị sai khi tin nguồn không chính thức | 142 cạnh `AMENDS` sai | chỉ nhận quan hệ từ lời nói đầu văn bản hợp nhất |
| Ngày hỏi lệch khỏi hiệu lực văn bản | 48 câu benchmark không dùng được | validate ngày hỏi nằm trong khoảng hiệu lực trước khi nhận câu |
| Ghi đè checkpoint làm mất ~2.900 dòng | mất dữ liệu đã trích | bắt buộc resume-filter + sao lưu `.bak` |
| Truy hồi trả về nguồn khác với đáp án đúng | Hit@1 nhóm regolded chỉ 0,062 | công bố đúng số thay vì bóp chấm (mục 10) |
| PDF scan không có lớp chữ | không tách được chunk | tách riêng hàng chờ OCR, không đoán |
| Thư viện đồ thị chạy sai trên một số trình duyệt | trang trắng, không báo lỗi | chuyển sang dùng đúng hợp đồng API của thư viện + kiểm trên Chrome/Edge thật trước khi phát hành |

---

## 10. Đề xuất cải tiến

1. **Xuất RDF/JSON-LD.** Cấu trúc quan hệ đã sẵn có; xuất ra RDF sẽ nạp được vào
   Neo4j/rdf4j và các kho tri thức khác. Đây là việc có giá trị cao nhất nếu reviewer
   hỏi về tính chuẩn hoá.
2. **Đưa chunk lên đồ thị.** Thêm node cấp Điều/Khoản (`BLDS2015|Dieu455`) nối vào
   luật, dùng sẵn hành vi phóng to theo rê của G6. Trả lời trực tiếp câu hỏi kiểu
   "điều nào bị sửa, sửa những gì".
3. **Sửa thang đo benchmark.** Chấp nhận nhiều đáp án tương đương về mặt pháp lý và
   dùng đánh giá LLM-as-judge cho nhóm câu có nguồn khác; báo cáo Hit@1 trên tập đã
   xác minh làm con số chính, nhóm kia để riêng.
4. **Pipeline tăng dần.** Tách bước xây chỉ mục để khi có văn bản mới chỉ chunk và embed
   phần mới, nối cạnh kế thừa tự động, thay vì chạy lại toàn bộ.
5. **Bổ sung văn bản còn thiếu.** 4 câu hỏi author-verified chỉ đạt 0,5 cho thấy một phần
   đáp án nằm ở văn bản chưa số hóa; mở rộng tập nguồn là hướng cải thiện trực tiếp.

---

## 11. Tái lập và kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Manifest SHA-256 | 47/47 file khớp, hai gương giống nhau (trừ README vì chính sách khác nhau) |
| Quét chất lượng văn bản | 0 ký tự ẩn, 0 mẫu khoá bí mật, mọi JSON/JSONL/GEXF đều parse được |
| Trình duyệt | 0 lỗi JavaScript trên Chromium, Chrome thật và Edge thật |
| Tính đúng đắn thời gian | truy vấn điểm-thời-điểm tự kiểm ở 3 mốc: 2000 → BLDS1995; 2010 → BLDS2005; 2020 → BLDS2015, HNGD2014 |

Trang trình xem chạy hoàn toàn offline sau khi tải: không CDN, không build step, không
phụ thuộc mạng. Toàn bộ số liệu trong báo cáo này đều lấy từ file trong kho, có thể mở
kiểm tra trực tiếp.

---

## Phụ lục — Bản đồ yêu cầu

| Yêu cầu | Mục | Kết quả |
| --- | --- | --- |
| Chia file bộ luật thành chunk | §3 | 11.267 chunk theo Điều/Khoản/Điểm |
| Lưu thành CSDL các chunk có nhãn | §4 | 3 tầng chỉ mục: khoá–giá trị, vectơ 768 chiều, đồ thị |
| Chia sẻ chunk/node | §5 | GEXF 1.3 mở bằng Gephi, ID ổn định — **còn thiếu RDF/DOI** |
| Xây đồ thị tri thức theo cách người ta làm | §6 | 33 node, 21 cạnh có nhãn + mốc thời gian — **node chỉ ở cấp luật** |
| Cập nhật theo đồ thị động | §7 | slider thời gian, 2012 → 4 luật, 2026 → 14 luật |
| Cập nhật thời gian | §7, §11 | `[valid_from, valid_to)` + tự kiểm 3 mốc thời gian |
| Nêu khó khăn và đề xuất | §9, §10 | 6 khó khăn, 5 đề xuất cải tiến |