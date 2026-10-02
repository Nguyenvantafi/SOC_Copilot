#!/usr/bin/env python3
"""Kiểm tra chất lượng truy xuất SOP (chỉ bước truy xuất, KHÔNG gọi LLM nên chạy nhanh).

Mặc định chỉ xét tập dev (data/labels.csv, cột split) để chỉnh ngưỡng/SOP/embedding mà không
"nhìn trộm" tập test. Đáp án đối chiếu:
  - cột expected_sop trong labels.csv nếu đã điền (nhãn thật), nếu không
  - data/rule_map.yaml (CHỈ là chỉ báo thô: do người soạn SOP viết, không phải nhãn chuẩn).

Dùng:  python scripts/retrieval_check.py            # tập dev
       python scripts/retrieval_check.py --verbose  # in từng mẫu
       python scripts/retrieval_check.py --split all  # chỉ để xem sơ bộ, KHÔNG dùng để chỉnh tham số
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from soc_copilot import config                                   # noqa: E402
from soc_copilot.features import build_query, normalize_alert    # noqa: E402
from soc_copilot.retrieval import load_rule_map                  # noqa: E402
from soc_copilot.sop_store import SopStore, embed_text_mode      # noqa: E402

THRESHOLDS = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.split != "dev":
        print(f"!! Đang xét split='{args.split}': chỉ xem sơ bộ, đừng dùng kết quả này để chỉnh tham số.\n")

    rows = list(csv.DictReader(open(ROOT / "data" / "labels.csv", encoding="utf-8-sig")))
    if args.split != "all":
        rows = [r for r in rows if r["split"] == args.split]
    rule_map = load_rule_map()
    store = SopStore()
    store.sync()
    print(f"embed_model={config.EMBED_MODEL} | embed_text_mode={embed_text_mode()} | "
          f"THRESHOLD hiện tại={config.THRESHOLD} | số mẫu={len(rows)}\n")

    res = []
    for r in rows:
        try:
            a = normalize_alert(json.load(open(ROOT / r["alert_ref"], encoding="utf-8-sig")))
        except Exception as e:
            print("LỖI đọc", r["alert_ref"], e)
            continue
        hits = store.query(build_query(a), n_results=3)
        top, dist = hits[0]["id"], hits[0]["distance"]
        margin = hits[1]["distance"] - dist if len(hits) > 1 else 0.0
        exp = (r.get("expected_sop") or "").strip()
        src = "nhãn"
        if not exp:
            exp, src = rule_map.get(str(r["rule_id"]), ""), "rule_map"
        res.append({"ref": Path(r["alert_ref"]).name, "rule": str(r["rule_id"]), "top": top,
                    "dist": dist, "margin": margin, "exp": exp, "src": src,
                    "top3": [h["id"] for h in hits]})
        if args.verbose:
            ok = "" if not exp else ("OK " if exp == top else "SAI")
            print(f"{res[-1]['ref']:26} {res[-1]['rule']:7} {top:26} {dist:6.3f} {margin:6.3f} "
                  f"{ok} (đáp án: {exp or '-'} [{src}])")

    known = [x for x in res if x["exp"]]
    n_lab = sum(1 for x in known if x["src"] == "nhãn")
    print(f"\nCó đáp án: {len(known)}/{len(res)} mẫu (từ nhãn: {n_lab}, từ rule_map: {len(known) - n_lab})")
    if not known:
        return
    h1 = sum(x["exp"] == x["top"] for x in known)
    h3 = sum(x["exp"] in x["top3"] for x in known)
    print(f"hit@1 = {h1}/{len(known)} ({h1 / len(known):.0%}) | hit@3 = {h3}/{len(known)} ({h3 / len(known):.0%})")
    ok_d = [x["dist"] for x in known if x["exp"] == x["top"]]
    bad_d = [x["dist"] for x in known if x["exp"] != x["top"]]
    if ok_d and bad_d:
        print(f"Khoảng cách trung bình: đúng {sum(ok_d) / len(ok_d):.3f} | sai {sum(bad_d) / len(bad_d):.3f} "
              "(càng tách xa nhau thì ngưỡng càng có ích)")

    print("\nNgưỡng | qua ngưỡng | trong đó SOP đúng | trong đó SOP sai")
    for t in THRESHOLDS:
        p = [x for x in known if x["dist"] <= t]
        good = sum(x["exp"] == x["top"] for x in p)
        print(f"{t:6.2f} | {len(p):4}/{len(known):<4}  | {good:4}              | {len(p) - good:4}")

    miss = Counter((x["rule"], x["exp"], x["top"]) for x in known if x["exp"] != x["top"])
    if miss:
        print("\nCác cặp sai (rule, đáp án -> SOP được chọn): số mẫu")
        for (rule, exp, top), c in miss.most_common():
            print(f"  {rule:7} {exp} -> {top}: {c}")


if __name__ == "__main__":
    main()
