# Guideline thẩm định đáp án vàng — ViCivil-TKG

**Mục tiêu:** đánh giá độc lập việc đáp án vàng (gold) của mỗi câu hỏi có *trả lời đúng câu hỏi* hay không, tại mốc thời điểm áp dụng (`as_of`) của câu hỏi.

## Thang chấm (3 nhãn)

| Nhãn | Định nghĩa |
|---|---|
| `DUNG` | Câu/văn bản gold nêu đúng quy phạm trả lời câu hỏi, tại đúng thời điểm áp dụng. |
| `MOTPHAN` | Gold đúng *phần* nội dung nhưng thiếu ý bắt buộc, hoặc trúng đúng điều nhưng sai khoản/điểm, hoặc đúng điều luật nhưng không khớp mốc `as_of` cho toàn bộ nội dung. |
| `SAI` | Gold trỏ sai điều/khoản/văn bản, hoặc nội dung không trả lời câu hỏi, hoặc trái quy phạm tại `as_of`. |

## Quy tắc làm việc

1. Chấm **độc lập**: không thảo luận, không xem chấm của người khác.
2. Chỉ dựa trên *nội dung gold cho sẵn* trong bảng; không tra cứu thêm tài liệu ngoài.
3. Câu hỏi có cặp so sánh thời gian (cùng hỏi, khác `as_of`): chấm từng dòng theo mốc riêng của dòng đó.
4. Ghi `notes` ngắn (≤ 20 từ) cho mọi dòng không phải `DUNG`.
5. Tốc độ tham chiếu: 2–4 phút/câu; ghi chú nếu vượt.
6. Không bỏ trống dòng nào; nếu thật sự không thể kết luận, chọn `MOTPHAN` và ghi `notes` "không xác định được".

## Đối tượng & mẫu

- `review_sheet_60.csv`: **60 câu = 50 câu lõi** (12 viết tay + 38 sinh, phủ 3 tầng vàng) **+ 10 câu mở rộng** (6 vòng 1, 4 vòng 2 — gồm tầng `regolded`).
- Cột `rater_A`, `rater_B`, `rater_C`: điền `DUNG` / `SAI` / `MOTPHAN`.

## Tính thỏa thuận

Chạy `python3 compute_iaa.py review_sheet_60.csv` sau khi đủ ≥ 2 người chấm:

- κ Cohen từng cặp người chấm + κ Fleiss toàn bảng.
- **Mục tiêu κ ≥ 0,75** (thỏa thuận tốt). Nếu κ < 0,60: họp làm rõ rubric, sau đó chấm lại *các dòng tranh chấp* (script in sẵn danh sách).
- Kết quả (κ, số người chấm, ngày) được chèn vào `DATASHEET.md` và phần Thẩm định của paper trước khi nộp bài.

## Sau khi chấm xong

1. Lưu file CSV đã điền thành `benchmark/iaa_kappa.json` (script xuất kèm số liệu tổng hợp).
2. Cập nhật một dòng kết quả vào `DATASHEET.md` (mục Validation).
3. Re-run `sha256sum` + push theo quy trình sync hiện hành.
