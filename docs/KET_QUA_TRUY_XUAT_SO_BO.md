# Kết quả truy xuất SOP sơ bộ (TRƯỚC bản vá embed `title + category + Điều kiện áp dụng`)

Đo ngày 02/10/2026 trên 87 mẫu (cả dev lẫn test), backend embedding `all-MiniLM-L6-v2`, THRESHOLD=0.45,
embed `title + toàn bộ nội dung`. Đáp án đối chiếu là `data/rule_map.yaml` (baseline do người soạn SOP viết,
KHÔNG phải nhãn chuẩn) nên chỉ là chỉ báo thô. Cần đo lại bằng nhãn thật: `python scripts/retrieval_check.py`.

- Chỉ 5/87 mẫu có khoảng cách ≤ 0.45, tức ~94% cảnh báo rơi vào SOP dự phòng `sop_general`.
- SOP gần nhất khớp rule_map ở 48/70 mẫu có rule trong rule_map (~69%).
- Khoảng cách của nhóm đúng (TB ~0.59) và nhóm sai (TB ~0.65) chồng lấn, nên nâng ngưỡng làm tăng số SOP sai lọt qua
  (ngưỡng 0.60: 43/87 qua, trong 70 mẫu có đáp án có 7 mẫu qua nhưng sai; ngưỡng 0.70: 72/87 qua, 18 sai).
- Lỗi có quy luật: cảnh báo lành tính (5402, 5403, 5501, 5502, 5715, 591) bị gán SOP tấn công (10 mẫu);
  rule 40112 (thành công sau nhiều lần thất bại) bị gán SOP brute force thường; SQLi (31103) không ra `sop_sqli`;
  rule 31106 bị gán nhóm dò quét.
- Một mẫu chạy đầy đủ (rule 5712, qwen2.5:3b, CPU Intel): t_llm ≈ 16.6 s, t_total ≈ 23.2 s.

Hạn chế: số liệu này lấy trên cả hai split và chưa có nhãn thật; đừng dùng để chỉnh tham số, chỉ dùng tập dev.

## So sánh hai cách embed trên tập dev (37/45 mẫu có đáp án từ rule_map; chưa có nhãn thật)
Đo ngày 02/10/2026, `all-MiniLM-L6-v2`, THRESHOLD hiện tại 0.45, cùng 37 mẫu.

| | `full` (title + toàn bộ nội dung) | `conditions` (title + category + Điều kiện áp dụng) |
|---|---|---|
| hit@1 | 28/37 (76%) | 32/37 (86%) |
| hit@3 | 36/37 (97%) | 37/37 (100%) |
| Khoảng cách TB: đúng / sai | 0.590 / 0.656 | 0.537 / 0.627 |
| Mẫu qua ngưỡng 0.45 | 0 | 7 |
| Qua ngưỡng 0.60 (đúng / sai) | 21 (18 / 3) | 24 (23 / 1) |
| Số mẫu chọn sai SOP | 9 | 5 |

Đối chiếu từng mẫu: `conditions` sửa đúng 5 mẫu (rule 31103, 5501, 5502, 554 và một mẫu 31106), làm sai thêm 1 mẫu (5503).
Lỗi còn lại ở cả hai cách: rule 40112 (thành công sau nhiều lần thất bại) bị gán SOP brute force thường; 5402 và 591 (lành tính) bị gán SOP tấn công.
Hạn chế: mẫu nhỏ (khoảng tin cậy Wilson 95% của hit@1 cách mới xấp xỉ 72–94%); đáp án là rule_map, không phải nhãn thật;
cần đo lại bằng nhãn thật trước khi chốt THRESHOLD. Cách `conditions` là mặc định từ bản này.
