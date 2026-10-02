# Merge notes

## Nguồn
| Thành phần | Lấy từ |
|---|---|
| `soc_copilot/` (lõi pipeline) | `soc_copilot_binh` |
| `app.py`, `ui/`, `soc_copilot/storage.py`, `data/sops/`, `data/rule_map.yaml` | `SOC_Copilot_Tai_package` |
| `eval/`, `data/samples/`, `data/adversarial/`, `data/lab/`, `data/labels.csv`, `soc_copilot/triage.py` | `soc_eval_D1_D9_full` |

SOP runtime là bộ của Tài (đầy đủ hơn bộ 3 file của Bình). `sop_ddos` và `sop_ransomware` (trước ở `sops_optional/`) đã chuyển vào `data/sops/`
để làm SOP gây nhiễu. `data/sop/full_sop.md` và `data/sop/rule_map.json` của bộ eval cố ý **không** đưa vào, tránh nguồn sự thật thứ hai.
Chroma/database không commit; tạo lại bằng `SopStore.sync()`. Thư mục `data/samples_curated_original/` (các mẫu `mauN` cũ, tên lệch rule) không đưa vào; `data/samples/extraction_report.md` ghi ánh xạ sang tên mới.

## Lỗi tích hợp đã sửa sau khi gộp
1. **UI không hiển thị đủ kết quả thật.** UI đọc `rule_severity`, `action_target_ip`, `sop_alternatives`, `timings{}`, `meta{}`, `alert_summary{}`...
   còn `AnalysisResult` của lõi dùng tên khác (`rule_bucket`, `block_target`, `alternatives`, `t_*`...). Thiếu khoá thì UI không báo lỗi, chỉ ẩn mục đó.
   Thêm `ui/backend.to_contract()` (có test `tests/test_ui_contract.py`). `attack_type`, `summary` lấy từ tiêu đề SOP và lập luận của mô hình;
   `report_md` nếu lõi chưa sinh thì ghép từ lập luận và các mục "Cách xác minh", "Ngăn chặn" của SOP (đã ghi rõ trong báo cáo).
2. **Bộ eval không đo hệ thống thật.** `eval/` có prompt, enum hành động (`MONITOR`, `ESCALATE`...), retrieval TF-IDF riêng và không có guard.
   Thêm backend `copilot` (gọi `soc_copilot.core.analyze_alert`), metric hit@1/hit@3, tỉ lệ fallback, guard đổi hành động, cờ injection.
   `retrieval.py` và `AnalysisResult` lưu thêm `top_hits`/`retrieved_top` (top-k thô trước khi áp ngưỡng) để tính hit@k.
3. **Enum nhãn hành động** trong hướng dẫn gán nhãn khác enum của hệ thống → đổi thành `BLOCK_IP, ISOLATE_HOST, REVIEW_LOG, NO_ACTION`. Thêm cột `expected_sop` (để trống).
4. **`eval_context` chế độ `rule_map`** chỉ đưa tên SOP vào prompt, không đưa nội dung → đã sửa.
5. **`PROTECTED_IPS` không khớp ca adversarial 12/13** → guard đọc `data/config/protected_ips.txt` (có hai IP lab giả định, nhóm xác nhận lại).
6. **Test UI** phải ép backend giả (`SOC_COPILOT_UI_MOCK=1`); nếu không, trên máy đủ thư viện test sẽ gọi Ollama/Chroma thật.
7. **Thiếu cấu hình riêng tư (T9):** `.streamlit/config.toml` thêm `gatherUsageStats = false`.
8. Khôi phục: `pytest.ini`, CI GitHub Actions, `docs/GIAO_DIEN_VOI_BINH.md`, `eval/README.md`, `triage.py`, `data/raw/README.txt`, `docs/data_provenance_stats.json`.
9. Dọn: `.venv/`, `__pycache__/`, `__MACOSX/`, `*.pyc` không đưa vào bản giao.

## Chưa làm được (cần người/máy thật)
- Chưa chạy được với Ollama thật. Đã chạy `pytest` ngoài môi trường tạo bản merge (Python 3.12, pydantic 2, chromadb 0.4.24): 100 pass, 30 subtests pass (đã sửa lỗi docstring `LLMOutput` làm hỏng `test_llm::test_ok`).
- `labels.csv` chưa có nhãn; chưa gắn `freeze-v1`; chưa có ảnh chụp B9; chưa sinh báo cáo tiếng Việt bằng lời gọi LLM riêng (B5 P1).
- Tab "Hàng đợi" (D8) chưa nối vào UI; nếu không làm thì phải hạ nhẹ động lực alert fatigue trong đề cương.
