"""Temporal civil QA benchmark v1 (weak supervision: keyword-anchored golds).
Each item: {qid, question, as_of, gold_ids[], answer_hint}. Dates make it temporal:
same question at different dates -> different golds. Expert review = v2.
"""
import json

Q = [
 ("CIV001", "2024-06-01", "Con đẻ muốn đổi từ họ cha sang họ mẹ cần điều kiện gì?",
  ["BLDS2015|Dieu27|Khoan2"], "thay đổi họ cho con đẻ"),
 ("CIV002", "2010-06-01", "Con đẻ muốn đổi từ họ cha sang họ mẹ cần điều kiện gì?",
  ["BLDS2005|Dieu27|Khoan1"], "cùng câu CIV001 nhưng đáp theo BLDS 2005 (temporal)"),
 ("CIV003", "2024-06-01", "Nam nữ kết hôn phải đủ bao nhiêu tuổi?",
  ["HNGD2014|Dieu8|Khoan1|Diema"], "nam đủ 20, nữ đủ 18"),
 ("CIV004", "2024-06-01", "Những ai thuộc hàng thừa kế thứ nhất?",
  ["BLDS2015|Dieu651|Khoan1|Diema"], "vợ chồng cha mẹ con"),
 ("CIV005", "2024-06-01", "Nguyên tắc bồi thường thiệt hại ngoài hợp đồng là gì?",
  ["BLDS2015|Dieu584|Khoan1"], "thiệt hại thực tế, lỗi, nhân quả"),
 ("CIV006", "2024-06-01", "Ai phải cấp dưỡng cho con chưa thành niên sau ly hôn?",
  ["HNGD2014|Dieu81|Khoan1"], "cha mẹ không trực tiếp nuôi con"),
 ("CIV007", "2024-06-01", "Xúc phạm danh dự người khác bị xử lý thế nào về dân sự?",
  ["BLDS2015|Dieu34|Khoan2"], "cải chính, xin lỗi, bồi thường"),
 ("CIV008", "2016-06-01", "Vợ chồng cùng muốn ly hôn thì làm sao?",
  ["HNGD2014|Dieu55"], "thuận tình ly hôn"),
 ("CIV009", "2024-06-01", "Tài sản chung vợ chồng gồm những gì?",
  ["HNGD2014|Dieu33|Khoan1"], "tài sản do vợ chồng tạo ra trong thời kỳ hôn nhân"),
 ("CIV010", "2024-06-01", "Di chúc miệng khi nào có hiệu lực?",
  ["BLDS2015|Dieu629|Khoan1"], "nguy kịch, 2 người làm chứng"),
 ("CIV011", "2024-06-01", "Người chưa thành niên gây thiệt hại ai bồi thường?",
  ["BLDS2015|Dieu586|Khoan1"], "cha mẹ/người giám hộ"),
 ("CIV012", "2000-06-01", "Năm 2000, con nuôi có được thừa kế như con đẻ không?",
  ["BLDS1995|Dieu678|Khoan1"], "temporal ngoài corpus (BLDS1995 thiếu) -> kỳ vọng KHÔNG đáp được"),
]
items = [{"qid": q, "as_of": d, "question": t, "gold_ids": g, "hint": h}
         for q, d, t, g, h in Q]
open("/home/devlab1/law_workspace/runs/law_bench_v1.json", "w", encoding="utf-8").write(
    json.dumps(items, ensure_ascii=False, indent=1))
print("wrote", len(items), "questions", flush=True)
print("temporal probes: CIV002 (2005 law), CIV008 (2010), CIV012 (1995 missing -> abstain expected)", flush=True)
