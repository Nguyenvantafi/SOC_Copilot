# Bao cao metric (D4/D6 so bo)

**CANH BAO BAT BUOC** (checklist D4): vi co mau nho, moi con so duoi day duoc bao cao dang `k/n` kem khoang tin cay Wilson 95%, KHONG duoc doc/trich dan nhu ty le phan tram chinh xac tuyet doi (vd khong noi 'model dat 93,4% chinh xac'). KET QUA CHI PHAN ANH DU LIEU CUA 1 LAB NAY, KHONG duoc khai quat ra ngoai pham vi du lieu da thu thap.

## Tong quan tat ca ket qua da nap

- Tong so dong ket qua (moi to hop model/mode/run): 127
- Loi hoac khong parse duoc JSON: 1
- Khop duoc voi it nhat 1 nhan that trong labels.csv: 0

## Ket qua theo tung to hop (model, mode)

| model | mode | recommended_action | is_true_positive | severity (khop dung) | severity (lech <=1 bac) |
|---|---|---|---|---|---|
| qwen2.5:3b | full_context | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |
| qwen2.5:3b | rag | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |
| qwen2.5:3b | rule_map | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |

## Truy xuat SOP va guard (chi co voi backend `copilot`; can cot `expected_sop` trong labels.csv)

| model | mode | hit@1 | hit@3 | dung fallback | fallback dung | guard doi hanh dong | co nghi injection |
|---|---|---|---|---|---|---|---|
| qwen2.5:3b | full_context | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |
| qwen2.5:3b | rag | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |
| qwen2.5:3b | rule_map | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) | 0/0 (khong co du lieu) |

## Do tre (giay) - DA LOAI BO lan goi dau tien/cold-start cho tung (model, mode)

| model | mode | n (loai cold-start) | n (goc, gom cold-start) | mean | median | p95 |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5:3b | full_context | 41 | 42 | 40.002s | 44.114s | 46.702s |
| qwen2.5:3b | rag | 41 | 42 | 18.099s | 17.181s | 30.805s |
| qwen2.5:3b | rule_map | 41 | 42 | 14.732s | 13.563s | 26.945s |

## Ca sai (mismatches) - de D6 phan tich 10 ca sai nang nhat

- Tong so ca sai (tren tat ca truong/to hop): 0
- Chi tiet tung ca nam trong `docs/figures/metrics_report.json` (khoa `mismatches` trong tung to hop model/mode) - dung file JSON de loc/sap xep khi viet D6.

---
_Sinh boi `eval/metrics.py`. Ket qua am tinh (vd mode nao do KHONG tot hon mode khac) van la ket qua hop le va PHAI duoc bao cao trung thuc, khong chi bao cao ket qua co loi._