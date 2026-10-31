# Lab scripts (đồng bộ từ máy A30)

Các script làm việc được đồng bộ từ máy tính toán A30
(`/home/devlab1/law_workspace/src`) về đây để người đọc có thể xem lại
toàn bộ quá trình, không chỉ phần đã được chọn lọc trong `src/`.

| Nhóm | Script | Vai trò |
| --- | --- | --- |
| Trích xuất | `law_extract.py`, `lawreext.py`, `lawblds1995_mucsplit.py` | Lấy văn bản từ nguồn, bóc tách nội dung theo cấu trúc luật |
| Làm sạch dữ liệu | `lawapply.py`, `lawfixall.py` | Chuẩn hoá và sửa các lỗi đã phát hiện trong dữ liệu |
| Sinh câu hỏi | `law_second.py`, `law_second_14b.py`, `law_qafaith.py`, `law_rescope_verify.py` | Sinh câu hỏi có đáp án và kiểm tra độ trung thành của câu trả lời |
| Chấm điểm | `lawpass1_dedup_clean.py`, `lawpass2_fulleval.py`, `lawpass3_stubfix_reembed.py`, `lawpass5_dedup_collapse.py`, `lawpass6_dedup_corrected.py`, `lawpass7_rescue_crowdstat.py` | Các vòng đánh giá truy hồi, lưu log từng vòng |
| Ván thời gian | `lawq_time.py` | Truy vấn theo mốc thời gian |
| Ván đánh giá | `lawregold.py`, `lawreviewpkg.py` | Ván lại nhóm câu hỏi và dựng gói review cho người đọc |
| Vá chunk đã làm sạch | `lawpatch_reembed_cleaned.py` | Nhúng lại 1.203 chunk đã làm sạch vào chỉ mục vector |

Lưu ý: các script này được giữ **để đối chiếu và tái lập**, không phải
để chạy trực tiếp. Đường dẫn trong chúng trỏ tới thư mục làm việc trên máy A30
(`/home/devlab1/law_workspace`), nên khi chạy lại cần chỉnh đường dẫn cho
phù hợp. Phần được phát hành và dùng để dựng lại toàn bộ artifact nằm ở
`src/` (36 script, giống hệt bản trên máy) cùng `tools/`.

Các script trong `src/` của kho đã được kiểm tra bằng cách so mã băm: **36/36
trùng khớp tuyệt đối** với bản trên máy A30, nên không có sai lệch nào giữa
hai nơi.
