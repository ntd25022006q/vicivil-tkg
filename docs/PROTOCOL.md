# PROTOCOL — Vận hành dataset ViCivil-TKG (chuẩn protocol)

Mọi quy tắc dưới đây tồn tại vì vi phạm nó từng gây mất dữ liệu hoặc số sai.
Đọc trước khi chạm vào `data/` hoặc chạy pipeline.

## 1. Nguyên tắc bất di bất dịch

1. **Mọi con số truy được file gốc.** Số nào trong docs cũng phải có file đo
   tương ứng trong `data/` hoặc log chạy. Không số miệng, không làm tròn đẹp.
2. **Không giấu số xấu.** Hố, miss, fail, giới hạn — công bố kèm nguyên nhân
   đã đo. Gian lận chỉ số (bóp cách chấm cho đẹp) là cấm tuyệt đối.
3. **Thay thế phải công bố + đo ảnh hưởng.** Model khác, proxy khác, thang đo
   khác — ghi rõ thay gì, vì sao, lệch bao nhiêu.
4. **Lịch sử không viết lại.** Luật sửa đổi thì đóng/mở hiệu lực, không xóa
   cạnh cũ. Checkpoint ghi đè thì backup `.bak` trước.

## 2. Cập nhật hàng tháng (đồ thị luôn mới)

1. Quét số Công báo mới từ `law_index.json` (checkpoint sẵn, chạy tiếp).
2. Tải PDF → `law_route.py` phân loại (text/scan) → scan vào quarantine.
3. Chunk theo ID phân cấp → lọc dân sự (allowlist khóa tay) → audit gate.
4. Trích delta (resume) → rebuild index → eval hồi quy (số không được tụt
   quá ngưỡng gate).
5. VBHN mới → moi preamble lấy danh sách sửa đổi → cạnh AMENDS verify tay.
6. Đóng bản quý theo semantic version (ví dụ v1.1.0): snapshot + delta + CHANGELOG + tag.

## 3. Audit gate (không đạt là dừng, không đẩy)

| Gate | Ngưỡng | File kiểm |
|---|---|---|
| Trùng chunk ID | = 0 | `law_audit.json` |
| Chunk rỗng (<20 ký tự) | = 0 | idem |
| Luật mồ côi temporal | = 0 | idem |
| Gold benchmark thiếu | = 0 | idem |
| Đủ Điều/luật lõi | khớp số luật định | idem (`numbering_gaps` chỉ nhận gap đã giải trình) |
| Benchmark mới | gold tồn tại + ngày trong hiệu lực | `gold_review.json` |
| Eval hồi quy | Hit@5 không tụt > 0,03 so với bản trước | log eval |

## 4. Chuẩn benchmark (không phải "chấm cho có")

- Gold = chunk tồn tại thật, ngày hỏi nằm trong hiệu lực luật chứa gold.
- Câu sinh bằng LLM phải qua lọc (CJK/meta/ngắn/dài) + duyệt mẫu thủ công;
  tỉ lệ lọc công bố.
- Split dev/test công khai, cố định seed; test gold được giữ kín, chỉ công bố gold của dev.
- Metric tối thiểu: Hit@1/3/5/10 + MRR + nDCG@10 + Điều@5 + abstain.
- Khác biệt giữa các hệ phải qua kiểm định (McNemar + Wilcoxon) mới được
  gọi là "hơn".

## 5. Release checklist (đủ tick mới tag version)

- [ ] Audit gate xanh hết
- [ ] Eval hồi quy đạt + kiểm định cập nhật
- [ ] Datasheet điền số cuối (không số tạm)
- [ ] SHA256SUMS cho mọi file data
- [ ] Quét keys/secret 0 phát hiện
- [ ] CHANGELOG ghi thay đổi so với bản trước
- [ ] Git tag `vX.Y` + push + verify remote đủ file

## 6. Quy tắc GPU/A30 (chia sẻ, không phá nhau)

- 1 GPU 1 việc nặng tại 1 thời điểm; kiểm `ps` trước khi launch (không bao
  giờ 2 tiến trình ghi cùng checkpoint).
- Kill theo PID cụ thể, không `pkill python/ollama`; không đụng job người khác.
- vLLM treo (health trống >10 phút): kill đúng PID → reboot profile cũ →
  health 200 mới chạy tiếp. Client giữ ≤8 luồng + watchdog tự sát ầm ĩ
  (exit 42) thay vì chết ngầm.
- Ổ đĩa >90%: dừng việc mới, báo cả lab (phần lớn là data người khác —
  không tự ý xóa).

## 7. Xử lý sự cố đã gặp (casebook)

- Checkpoint ghi đè mất ~2.900 dòng: do relaunch thiếu resume-filter và
  không backup → từ nay backup `.bak` + resume-filter bắt buộc.
- Cạnh AMENDS sai (142/2025): do tin snippet tìm kiếm → chỉ nhận quan hệ
  từ văn bản gốc (lời nói đầu VBHN), snippet chỉ để định hướng.
- Benchmark date-mismatch hệ thống (48 câu): do công thức ngày ẩu → ngày hỏi
  phải validate trong khoảng hiệu lực trước khi nhận câu.
- Tool cắt lệnh có ký tự `|`: mọi script đi file base64, không lệnh inline
  phức tạp; số quan trọng verify 2 cách độc lập.
