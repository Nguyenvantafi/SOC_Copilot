# Huong dan dien data/labels.csv (D3)

**Truoc khi Duc/Binh gan nhan**: SOP + prompt + nguong PHAI da freeze (tag `freeze-v1`). Nguoi gan nhan CHI duoc nhin file alert goc trong `alert_ref`, KHONG duoc nhin dau ra cua model.

- Tong so dong: se hien thi khi chay script (xem log chay).
- Cot da dien san (tham chieu, KHONG sua): alert_ref, alert_id_raw, rule_id, rule_level, rule_description, source, split, is_kappa_check_sample, rater2_label, agreement_flag
- Cot Duc/Binh can dien: assigned_severity_range, is_true_positive, expected_sop, recommended_action_label, labeler, label_date, notes

## assigned_severity_range - chon 1 trong cac khoang sau (co the dieu chinh neu Phu luc D quy dinh khac)

- `1_thap (benign / scanner / false-positive ro rang)`
- `2_trung-thap (nghi ngo nhe, can theo doi)`
- `3_trung-binh (can xac minh chu dong, chua chac tan cong)`
- `4_trung-cao (kha nang cao la tan cong that, chua thanh cong ro rang)`
- `5_cao (tan cong that, co dau hieu thanh cong / anh huong he thong)`

## recommended_action_label - chon 1 trong (co the dieu chinh theo SOP that)

- `BLOCK_IP`
- `ISOLATE_HOST`
- `REVIEW_LOG`
- `NO_ACTION`

(Bon gia tri nay TRUNG voi `Action` trong `soc_copilot/models.py`; dung gia tri khac thi metric hanh dong khong so khop duoc voi he thong that.)

## is_true_positive

- `yes` / `no` / `unsure`. LUU Y dac biet: theo docs/data_provenance.md, phan lon alert rule 31101/31151 (~85% pool) mang dau hieu la traffic quet Nikto tu dong, KHONG phai tan cong thu cong. Neu gap alert loai nay, hay xem xet gan `no` (hoac `unsure` neu khong chac) thay vi mac dinh `yes` chi vi rule co ten 'attack'.

## expected_sop (moi)

- id SOP dung cho alert nay, lay tu ten file trong `data/sops/` (vd `sop_ssh_bruteforce`, `sop_benign_activity`, hoac `sop_general` neu khong SOP nao phu hop). Gan nhin alert, KHONG nhin `data/rule_map.yaml` de tranh tu tham chieu vong tron voi baseline rule_map. Dung de tinh hit@1/hit@3 cua truy xuat.

## is_kappa_check_sample

- Neu `True`: Binh PHAI gan nhan DOC LAP (khong xem nhan cua Duc truoc), dien vao `rater2_label` (dung cung dinh dang voi `assigned_severity_range` hoac `recommended_action_label` tuy quy uoc nhom chon). Sau khi ca hai co nhan, tinh % trung / Cohen's kappa va dien `agreement_flag`, roi hop thong nhat cac ca bat dong.

## Sau khi gan nhan xong: gan tag `freeze-v1` cho SOP/prompt/nguong + labels.csv nay, khong sua nguong/prompt tren tap `test` nua tu thoi diem do.