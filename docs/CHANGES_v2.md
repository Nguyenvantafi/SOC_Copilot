# Thay đổi so với SOC_Copilot_merged_final.zip
- `soc_copilot/sop_store.py`: embedding tính từ `title + category + mục "Điều kiện áp dụng"`; prompt vẫn nhận SOP đầy đủ;
  sync tự nhúng lại khi đổi chế độ (`index_v` trong metadata). `EMBED_TEXT_MODE="full"` trong config để quay lại cách cũ.
- `scripts/retrieval_check.py` (mới): hit@1, hit@3, bảng ngưỡng, cặp sai; mặc định chỉ tập dev; dùng `expected_sop` nếu đã gán nhãn.
- `scripts/label_helper.py` (mới): gán nhãn tương tác (lưu từng dòng, tự sao lưu `labels.csv.bak`), người thứ hai gán dòng kappa (`rater2`), tính % trùng + Cohen's kappa (`kappa`), kiểm tra lỗi gõ và tiến độ (`check`), xem cảnh báo (`show`). Không hiển thị rule_map hay kết quả model.
- `tests/test_sop_index.py` (mới): 5 test cho phần embed mới.
- `requirements.txt`: ghim `sentence-transformers==3.0.1`, `transformers==4.44.2`, `huggingface_hub<0.26` (đã chạy được: 100 test pass).
- `README.md`: thêm mục truy xuất, quy trình gán nhãn, ghi chú Mac Intel (torch 2.2.2 + numpy<2).
- Xoá `data/eval_runs/mock-*.jsonl` (dữ liệu giả, tránh lẫn vào kết quả thật; chạy lại `run_matrix.py ... --backend mock` nếu cần kiểm tra harness).
- `docs/KET_QUA_TRUY_XUAT_SO_BO.md` (mới): kết quả đo sơ bộ trước bản vá.
