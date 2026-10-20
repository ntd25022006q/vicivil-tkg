# Lab scripts (đồng bộ từ máy A30)

Các script làm việc được đồng bộ từ máy tính toán A30
(`/home/devlab1/law_workspace/src`) về đây để người đọc có thể xem lại
toàn bộ quá trình, không chỉ phần đã được chọn lọc trong `src/`.

| Nhóm | Script | Vai trò |
| --- | --- | --- |
| Trích xuất | `law_extract.py`, `lawreext.py`, `law95do.py` | Lấy văn bản từ nguồn, bóc tách nội dung theo cấu trúc luật |
| Làm sạch dữ liệu | `lawapply.py`, `lawfixall.py` | Chuẩn hoá và sửa các lỗi đã phát hiện trong dữ liệu |
| Sinh câu hỏi | `law_second.py`, `law_second14.py`, `law_qafaith.py`, `lawrs67.py` | Sinh câu hỏi có đáp án và kiểm tra độ trung thành của câu trả lời |
| Chấm điểm | `lawfin1.py`, `lawfin2.py`, `lawfin3.py`, `lawfin5.py`, `lawfin6.py`, `lawfin7.py` | Các vòng đánh giá truy hồi, lưu log từng vòng |
| Ván thời gian | `lawq_time.py` | Truy vấn theo mốc thời gian |
| Ván đánh giá | `lawregold.py`, `lawreviewpkg.py` | Ván lại nhóm câu hỏi và dựng gói review cho người đọc |
| Vá dữ liệu v11 | `lawv11patch.py` | Mã hoá lại 1.203 chunk đã làm sạch trong bước v1.1 |

Lưu ý: các script này được giữ **để đối chiếu và tái lập**, không phải
để chạy trực tiếp. Đường dẫn trong chúng trỏ tới thư mục làm việc trên máy A30
(`/home/devlab1/law_workspace`), nên khi chạy lại cần chỉnh đường dẫn cho
phù hợp. Phần được phát hành và dùng để dựng lại toàn bộ artifact nằm ở
`src/` (36 script, giống hệt bản trên máy) cùng `tools/`.

Các script trong `src/` của kho đã được kiểm tra bằng cách so mã băm: **36/36
trùng khớp tuyệt đối** với bản trên máy A30, nên không có sai lệch nào giữa
hai nơi.
