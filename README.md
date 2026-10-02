# SOC Analyst Copilot

Trợ lý phân tích cảnh báo Wazuh chạy hoàn toàn nội bộ: **SOP (Markdown) → ChromaDB → Ollama → guard kiểm tra hành động → dashboard Streamlit**.
Đề tài chuyên đề cơ sở, Học viện Kỹ thuật Mật mã. Hệ thống chỉ **đề xuất**; không lệnh nào được thực thi thật, người phân tích là người quyết định cuối cùng.

## Yêu cầu
- Python 3.10–3.12
- [Ollama](https://ollama.com) phiên bản **>= 0.5** (cần cho JSON schema); kiểm tra: `ollama --version`

## Cài đặt
```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt     # hoặc: bash scripts/setup.sh | .\scripts\setup.ps1
ollama pull qwen2.5:7b              # đổi theo soc_copilot/config.py: DEFAULT_MODEL
```

## Chạy lần đầu (cần mạng để tải model embedding từ HuggingFace)
```bash
python -m soc_copilot.cli sync      # nạp data/sops/*.md vào Chroma (chroma_data/, không commit)
python -m soc_copilot.cli health    # kiểm tra Ollama và danh sách model
python -m soc_copilot.cli analyze data/samples/5712_1.json --mode rag
streamlit run app.py                # dashboard
```
Tuỳ chọn của `analyze`: `--model`, `--mode rag|rule_map|full_context`, `--threshold`.

## Chạy offline (các lần sau)
```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1      # PowerShell: $env:HF_HUB_OFFLINE="1"
```

## Cấu trúc
```text
app.py, ui/            Dashboard (Tài). ui/backend.py nối UI với lõi và chuyển kết quả sang khoá UI đọc
soc_copilot/           Lõi (Bình): config, features, sop_store, retrieval, prompts, llm, guard, core, cli, netguard
                       storage.py (Tài, SQLite); triage.py (Đức, D8, tuỳ chọn, chưa nối vào UI)
data/sops/             Nguồn sự thật DUY NHẤT của SOP (15 file; sop_ddos/ransomware/malware/port_scan/privilege_escalation
                       cố ý không có rule trong dữ liệu, dùng làm SOP gây nhiễu truy xuất)
data/rule_map.yaml     Baseline tra theo rule.id (Tài)
data/config/protected_ips.txt   IP không bao giờ được đề xuất chặn (guard đọc; cần nhóm xác nhận trước freeze)
data/samples/, data/adversarial/, data/labels.csv, data/lab/    Dữ liệu và nhãn (Đức)
eval/                  Bộ đánh giá (Đức), xem eval/README.md
tests/  docs/  scripts/
```

## Kiểm tra chất lượng truy xuất SOP (nhanh, không gọi LLM)
```bash
python scripts/retrieval_check.py --verbose      # mặc định chỉ tập dev
```
In hit@1, hit@3, bảng ngưỡng và các cặp SOP bị chọn sai. Đáp án lấy từ cột `expected_sop` của `data/labels.csv` nếu đã gán nhãn, nếu không thì dùng `data/rule_map.yaml` (chỉ là chỉ báo thô). Chỉ chỉnh ngưỡng/SOP/embedding dựa trên tập dev; tập test để dành cho đánh giá cuối.
Chỉ mục embedding mặc định dùng `title + category + mục "Điều kiện áp dụng"` (prompt vẫn nhận SOP đầy đủ). Muốn quay lại cách cũ: thêm `EMBED_TEXT_MODE = "full"` vào `soc_copilot/config.py`, rồi `python -m soc_copilot.cli sync` (tự nhúng lại).

Ghi chú môi trường (Mac Intel): `torch` bản mới không hỗ trợ Mac Intel; cài `pip install "torch==2.2.2" "numpy<2"` trước `pip install -r requirements.txt`.

## Quy trình gán nhãn (khuyến nghị)
Dev trước, chỉnh trên dev, đóng băng, rồi mới gán test (giữ tập test sạch). Công cụ gán nhãn tương tác tự ghi đúng cột và lưu sau MỖI dòng:
```bash
python scripts/label_helper.py label --labeler Duc --split dev   # gán tương tác (s=bỏ qua, q=thoát, r=nhập lại)
python scripts/label_helper.py label --labeler Duc --row 12      # sửa/gán lại đúng dòng 12
python scripts/label_helper.py check --split dev                 # kiểm tra lỗi gõ + tiến độ
python scripts/label_helper.py rater2 --labeler Binh             # người thứ hai gán các dòng kappa -> data/labels_rater2.csv
python scripts/label_helper.py kappa                             # gộp rater2, tính % trùng + Cohen's kappa, điền agreement_flag
python scripts/label_helper.py show --split dev --n 3            # chỉ xem cảnh báo (không hiện rule_map/kết quả model)
```
Mỗi cảnh báo trả lời 4 câu: mức nghiêm trọng 1–5, có phải tấn công thật (y/n/u), SOP đúng nhất, hành động (BLOCK_IP/ISOLATE_HOST/REVIEW_LOG/NO_ACTION). Không mở `data/rule_map.yaml` khi gán nhãn.
Người thứ hai nên chạy `rater2` trên bản dự án CHƯA có nhãn người thứ nhất; file `labels_rater2.csv` gửi lại cho người thứ nhất bỏ vào `data/` rồi chạy `kappa`.
Sau khi chốt cấu hình: `git tag freeze-v1`, rồi gán tập test (`--split test`). Ghi rõ trong báo cáo rằng nhãn dev được gán trước freeze.
CẢNH BÁO: đã bắt đầu gán nhãn thì KHÔNG giải nén lại toàn bộ zip đè lên thư mục dự án (sẽ ghi đè `data/labels.csv`).

## Chạy test (không cần Ollama, không cần tải model)
```bash
python -m pytest -q
```

## Chạy đánh giá (số liệu cho báo cáo)
Dùng backend **`copilot`**: chạy qua đúng pipeline thật (`soc_copilot.core.analyze_alert`: truy xuất → LLM → guard).
```bash
python eval/run_eval.py --model qwen2.5:3b --mode rag --split test --backend copilot \
    --out data/eval_runs/qwen2.5-3b_rag_test.jsonl
python eval/metrics.py --results "data/eval_runs/qwen*.jsonl"
```
Backend `mock` chỉ để kiểm tra harness; các file `data/eval_runs/mock-*.jsonl` là dữ liệu **giả**, không được dùng trong báo cáo.
Trước khi gán nhãn và chạy đánh giá chính thức: chốt SOP, rule_map, prompt, ngưỡng, `protected_ips.txt` rồi gắn tag `freeze-v1`.
Cột `expected_sop` trong `data/labels.csv` đang để trống, Đức điền sau freeze.

## Kiểm chứng dữ liệu không rời hạ tầng (B9)
```bash
python scripts/egress_check.py              # lần 1
python scripts/egress_check.py --offline    # lần 2
```
Xem `docs/B9_egress_checklist.md` (Wireshark, Streamlit `gatherUsageStats = false` đã đặt trong `.streamlit/config.toml`).

Lưu ý: ngưỡng của guard và `LEVEL_BUCKETS` là chính sách của nhóm, không phải chuẩn Wazuh.
