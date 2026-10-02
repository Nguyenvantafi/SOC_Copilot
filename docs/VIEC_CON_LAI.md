# Việc còn lại trước khi đóng băng (freeze-v1)

Các mục dưới đây cần người hoặc máy thật, không thể làm trong bản merge này.

## Bắt buộc
- [ ] Xác nhận IP thật của lab và sửa `data/config/protected_ips.txt`. Hai IP hiện tại (`192.168.26.30`, `192.168.26.50`) là suy đoán từ ca adversarial 12/13.
- [ ] Gán nhãn `data/labels.csv` (87 dòng đang trống, thiếu `expected_sop`). Chưa có nhãn thì hit@k, accuracy, kappa đều không tính được.
- [ ] Chạy `python -m pytest -q` trên máy nhóm (kỳ vọng 100 pass).
- [ ] Chạy thử 1 ca `eval/run_eval.py --backend copilot` với Ollama + qwen2.5 thật; kiểm tra schema, độ trễ, model embedding tải được offline.
- [ ] Gắn tag `freeze-v1`, sau đó mới chạy đánh giá chính thức.

## Đề cương chưa khớp với sản phẩm (cần sửa đề cương HOẶC đổi code)
- Đề cương ghi **FastAPI + React/Next.js** (mục 2 và mục 1.5.5 ReactJS), **LangChain/LlamaIndex**, **ChromaDB/FAISS**. Code thực tế dùng **Streamlit**, Python thuần và ChromaDB; không có FastAPI, React, LangChain hay FAISS. Cần thống nhất với GVHD: sửa đề cương cho đúng công nghệ đã làm, hoặc ghi rõ lý do thay đổi.
- Tab "Hàng đợi" (D8) và con số "15055 alert → 37 nhóm, giảm 99.8%" chưa nối vào UI và chưa được tái tính; không viết như tính năng đã hoàn thành.
- `data/eval_runs/mock-*.jsonl`, `eval/REPORT.md` và `docs/figures/` đang sinh từ backend `mock` (dữ liệu giả); phải sinh lại sau khi có nhãn và kết quả thật.

## Lưu ý đóng gói
Chạy `pytest` sẽ tạo lại `soc_copilot.db` ở thư mục gốc (đã nằm trong `.gitignore`); xoá trước khi nén bản giao.
