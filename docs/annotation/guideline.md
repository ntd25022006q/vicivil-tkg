# Guideline thẩm định đáp án vàng — ViCivil-TKG (v1.0.1)

**Mục tiêu:** đánh giá độc lập việc đáp án vàng (gold) của mỗi câu hỏi có *trả lời đúng câu hỏi* hay không, tại mốc thời điểm áp dụng (`as_of`) của câu hỏi.

## Thang chấm (3 nhãn)

| Nhãn | Định nghĩa |
|---|---|
| `DUNG` | Câu/văn bản gold nêu đúng quy phạm trả lời câu hỏi, tại đúng thời điểm áp dụng. |
| `MOTPHAN` | Gold đúng *phần* nội dung nhưng thiếu ý bắt buộc, hoặc trúng đúng điều nhưng sai khoản/điểm, hoặc đúng điều luật nhưng không khớp mốc `as_of` cho toàn bộ nội dung. |
| `SAI` | Gold trỏ sai điều/khoản/văn bản, hoặc nội dung không trả lời câu hỏi, hoặc trái quy phạm tại `as_of`. |

## Quy tắc làm việc

1. Chấm **độc lập**: không thảo luận, không xem chấm của người khác.
2. Chỉ dựa trên *nội dung gold cho sẵn* trong bảng (cột `answer`); không tra cứu thêm tài liệu ngoài.
3. **Luôn đối chiếu mốc `as_of`** (cột 3) với nội dung gold: văn bản đã hết hạn tại `as_of` → không thể là `DUNG`.
4. Cột `gold` là định danh đoạn vàng (`Law|Điều|Khoản|…`) chỉ để tra vết; **không dùng để đoán nhãn**.
5. Cột `gold_note` do hệ thống ghi (ví dụ "text khoi phuc tu N chunk con…") — chỉ mang tính thông tin, không ảnh hưởng nhãn.
6. Ghi `notes` ngắn (≤ 20 từ) cho mọi dòng không phải `DUNG`.
7. Tốc độ tham chiếu: 2–4 phút/câu; ghi chú nếu vượt.
8. Không bỏ trống dòng nào; nếu thật sự không thể kết luận, chọn `MOTPHAN` và ghi `notes` "không xác định được".

## Đối tượng & mẫu

- `review_sheet_60.csv`: **60 câu = 50 câu lõi** (12 viết tay + 38 sinh, phủ 3 tầng vàng) **+ 10 câu mở rộng** (6 vòng 1, 4 vòng 2 — gồm tầng `regolded`).
- Toàn bộ 60 dòng có `as_of` đầy đủ và gold đã đồng bộ với bộ vàng *đã áp dụng* trong `benchmark/law_bench_*.json` (bản v1.0.1).
- Cột `rater_A`, `rater_B`, `rater_C`: điền `DUNG` / `SAI` / `MOTPHAN`.

## Tính thỏa thuận

Chạy `python3 compute_iaa.py review_sheet_60.csv` sau khi đủ ≥ 2 người chấm (script nằm cùng thư mục, chạy tại đây):

- κ Cohen từng cặp người chấm + κ Fleiss toàn bảng (các dòng đủ người chấm).
- **Mục tiêu κ ≥ 0,75** (thống nhất tốt). Nếu κ < 0,60: họp làm rõ rubric, sau đó chấm lại *các dòng tranh chấp* (script in sẵn danh sách).
- Kết quả xuất ra `iaa_kappa.json` ngay trong thư mục hiện hành — copy về `benchmark/iaa_kappa.json` khi chốt.

## Sau khi chấm xong

1. Copy `iaa_kappa.json` vào `benchmark/iaa_kappa.json`.
2. Cập nhật một dòng kết quả vào `DATASHEET.md` (mục *Known gaps / expert review*).
3. Chạy lại `sha256sum` cho các file thay đổi + push theo quy trình sync hiện hành.
