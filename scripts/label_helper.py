#!/usr/bin/env python3
"""Công cụ gán nhãn data/labels.csv (không gọi model, không hiện rule_map hay kết quả hệ thống).

  python scripts/label_helper.py label --labeler Duc --split dev     # gán nhãn tương tác, lưu sau MỖI dòng
  python scripts/label_helper.py label --labeler Duc --row 12        # sửa/gán lại đúng dòng 12
  python scripts/label_helper.py rater2 --labeler Binh               # người thứ hai gán các dòng kappa (ghi ra file riêng)
  python scripts/label_helper.py kappa                               # gộp rater2, tính % trùng + Cohen's kappa
  python scripts/label_helper.py check --split dev                   # kiểm tra lỗi + tiến độ
  python scripts/label_helper.py show --split dev --n 3              # chỉ xem cảnh báo
  python scripts/label_helper.py sops                                # danh sách id SOP

Trong lúc nhập: s = bỏ qua dòng này, q = thoát (nhãn đã lưu vẫn giữ), ? = xem lại gợi ý.
Dòng đếm từ 1 (không tính tiêu đề), khớp với số in ra khi chạy `show`.
"""
import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "data" / "labels.csv"
RATER2 = ROOT / "data" / "labels_rater2.csv"
SEV = {"1": "1_thap", "2": "2_trung-thap", "3": "3_trung-binh", "4": "4_trung-cao", "5": "5_cao"}
TPV = {"y": "yes", "yes": "yes", "n": "no", "no": "no", "u": "unsure", "unsure": "unsure"}
ACT = {"1": "BLOCK_IP", "2": "ISOLATE_HOST", "3": "REVIEW_LOG", "4": "NO_ACTION"}
SEV_SET, TP_SET, ACT_SET = set(SEV.values()), set(TPV.values()), set(ACT.values())
FILL = ("assigned_severity_range", "is_true_positive", "expected_sop",
        "recommended_action_label", "labeler", "label_date")
R2_FIELDS = ("sev", "tp", "sop", "act")

HELP_SEV = ("1=thấp (lành tính/scanner/false-positive rõ)  2=trung-thấp (nghi ngờ nhẹ)  3=trung-bình (cần xác minh)\n"
            "     4=trung-cao (khả năng cao là tấn công thật, chưa thành công)  5=cao (tấn công thật, có dấu hiệu thành công/ảnh hưởng)")
HELP_TP = "y=yes (tấn công thật)  n=no (bình thường/quét tự động)  u=unsure"
HELP_ACT = "1=BLOCK_IP  2=ISOLATE_HOST  3=REVIEW_LOG  4=NO_ACTION"


class Quit(Exception):
    pass


class Skip(Exception):
    pass


# ---------- đọc/ghi CSV (ghi nguyên tử, giữ thứ tự cột, UTF-8, xuống dòng LF) ----------
def read_all():
    with open(LABELS, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        return rows, rd.fieldnames


def read_rows():
    return read_all()[0]


def write_all(rows, fields):
    tmp = LABELS.with_name(LABELS.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(LABELS)


def sop_ids():
    out = {}
    for p in sorted((ROOT / "data" / "sops").glob("*.md")):
        title = ""
        for line in p.read_text(encoding="utf-8").splitlines()[:15]:
            m = re.match(r"title:\s*(.+)", line)
            if m:
                title = m.group(1).strip().strip('"\'')
        out[p.stem] = title
    return out


def g(d, path, default=""):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def cut(s, n):
    s = str(s).replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + " …[cắt]"


def show_alert(i, row):
    a = json.load(open(ROOT / row["alert_ref"], encoding="utf-8-sig"))
    a = a.get("_source", a)
    print("=" * 78)
    print(f"DÒNG {i}  |  {row['alert_ref']}  |  split={row['split']}  |  kappa={row['is_kappa_check_sample']}")
    print("-" * 78)
    print(f"Thời gian : {a.get('timestamp', '')}")
    print(f"Rule      : {g(a, 'rule.id')} (level {g(a, 'rule.level')})  {g(a, 'rule.description')}")
    print(f"Nhóm      : {g(a, 'rule.groups')}   MITRE: {g(a, 'rule.mitre.id')} {g(a, 'rule.mitre.technique')}")
    print(f"Tần suất  : frequency={g(a, 'rule.frequency')}  firedtimes={g(a, 'rule.firedtimes')}")
    print(f"Agent     : {g(a, 'agent.name')}   Nguồn log: {a.get('location', '')}")
    data = a.get("data", {})
    if data:
        print(f"Data      : {cut(json.dumps(data, ensure_ascii=False), 500)}")
    print(f"full_log  : {cut(a.get('full_log', ''), 700)}")
    if a.get("previous_output"):
        print(f"previous  : {cut(a['previous_output'], 500)}")
    print()


# ---------- nhập liệu tương tác ----------
def ask(prompt, mapping, optional=False):
    while True:
        s = input(prompt).strip()
        low = s.lower()
        if low in ("q", "quit"):
            raise Quit
        if low in ("s", "skip"):
            raise Skip
        if low == "" and optional:
            return ""
        if low in mapping:
            return mapping[low]
        if s in mapping:
            return mapping[s]
        print("   Không hợp lệ. Gõ lại (s=bỏ qua, q=thoát).")


def sop_menu(sops):
    keys = list(sops)
    print("  Chọn SOP đúng nhất (gõ số hoặc id):")
    for n, k in enumerate(keys, 1):
        print(f"   {n:2}. {k:26} {sops[k]}")
    mapping = {str(n): k for n, k in enumerate(keys, 1)}
    mapping.update({k: k for k in keys})
    return mapping


def collect(sops, with_notes):
    """Hỏi 4 quyết định. Trả về dict hoặc ném Skip/Quit."""
    sop_map = sop_menu(sops)
    print(f"  Mức nghiêm trọng: {HELP_SEV}")
    sev = ask("  [1-5] > ", SEV)
    print(f"  Có phải tấn công thật?  {HELP_TP}")
    tp = ask("  [y/n/u] > ", TPV)
    sop = ask("  SOP [số/id] > ", sop_map)
    print(f"  Hành động khuyến nghị:  {HELP_ACT}")
    act = ask("  [1-4] > ", ACT)
    notes = ""
    if with_notes:
        notes = input("  Ghi chú (Enter = bỏ qua) > ").strip()
    return {"sev": sev, "tp": tp, "sop": sop, "act": act, "notes": notes}


def confirm(d):
    print(f"\n  → mức={d['sev']} | thật={d['tp']} | SOP={d['sop']} | hành động={d['act']}"
          + (f" | ghi chú={d['notes']}" if d.get("notes") else ""))
    while True:
        s = input("  Enter = lưu, r = nhập lại, s = bỏ qua, q = thoát > ").strip().lower()
        if s == "":
            return True
        if s == "r":
            return False
        if s == "s":
            raise Skip
        if s == "q":
            raise Quit


def cmd_label(args):
    if not args.labeler:
        sys.exit("Thiếu --labeler (ví dụ --labeler Duc)")
    rows, fields = read_all()
    bak = LABELS.with_name(LABELS.name + ".bak")
    if not bak.exists():
        shutil.copy(LABELS, bak)
        print(f"(đã sao lưu bản gốc: {bak.name})")
    sops = sop_ids()
    if args.row:
        todo = [args.row]
    else:
        todo = [i for i, r in enumerate(rows, 1)
                if (args.split == "all" or r["split"] == args.split)
                and not all((r.get(k) or "").strip() for k in FILL[:4])]
    total = len(todo)
    print(f"Còn {total} dòng cần gán. Gõ q để dừng bất cứ lúc nào (nhãn đã lưu vẫn giữ).\n")
    saved = 0
    try:
        for pos, i in enumerate(todo, 1):
            row = rows[i - 1]
            while True:
                print(f"\n[{pos}/{total}]")
                show_alert(i, row)
                try:
                    d = collect(sops, with_notes=True)
                    if not confirm(d):
                        continue
                except Skip:
                    print("  (bỏ qua dòng này)")
                    break
                row["assigned_severity_range"] = d["sev"]
                row["is_true_positive"] = d["tp"]
                row["expected_sop"] = d["sop"]
                row["recommended_action_label"] = d["act"]
                row["labeler"] = args.labeler
                row["label_date"] = date.today().isoformat()
                if d["notes"]:
                    row["notes"] = d["notes"]
                write_all(rows, fields)
                saved += 1
                print("  ✔ đã lưu")
                break
    except (Quit, EOFError, KeyboardInterrupt):
        print("\nĐã dừng.")
    print(f"Đã lưu {saved} dòng trong phiên này. Chạy: python scripts/label_helper.py check --split {args.split}")


def read_rater2():
    if not RATER2.exists():
        return {}
    with open(RATER2, encoding="utf-8-sig", newline="") as f:
        return {r["alert_ref"]: r for r in csv.DictReader(f)}


def write_rater2(d):
    fields = ["alert_ref", "row", "labeler2", "label_date"] + list(R2_FIELDS)
    tmp = RATER2.with_name(RATER2.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(d.values())
    tmp.replace(RATER2)


def cmd_rater2(args):
    if not args.labeler:
        sys.exit("Thiếu --labeler (tên người thứ hai)")
    rows = read_rows()
    done = read_rater2()
    sops = sop_ids()
    todo = [i for i, r in enumerate(rows, 1)
            if r["is_kappa_check_sample"] == "True" and r["alert_ref"] not in done
            and (args.split == "all" or r["split"] == args.split)]
    print(f"Người thứ hai: còn {len(todo)} dòng kappa. Kết quả ghi vào {RATER2.relative_to(ROOT)} "
          "(không đụng nhãn người thứ nhất, và công cụ không hiển thị nhãn đó).\n")
    saved = 0
    try:
        for pos, i in enumerate(todo, 1):
            row = rows[i - 1]
            while True:
                print(f"\n[{pos}/{len(todo)}]")
                show_alert(i, row)
                try:
                    d = collect(sops, with_notes=False)
                    if not confirm(d):
                        continue
                except Skip:
                    print("  (bỏ qua dòng này)")
                    break
                done[row["alert_ref"]] = {"alert_ref": row["alert_ref"], "row": i, "labeler2": args.labeler,
                                          "label_date": date.today().isoformat(),
                                          **{k: d[k] for k in R2_FIELDS}}
                write_rater2(done)
                saved += 1
                print("  ✔ đã lưu")
                break
    except (Quit, EOFError, KeyboardInterrupt):
        print("\nĐã dừng.")
    print(f"Đã lưu {saved} dòng. Gửi file {RATER2.name} cho người thứ nhất rồi chạy: label_helper.py kappa")


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)


def cmd_kappa(_):
    rows, fields = read_all()
    r2 = read_rater2()
    if not r2:
        sys.exit(f"Chưa có {RATER2.name}. Người thứ hai chạy: label_helper.py rater2 --labeler Ten")
    col = {"sev": "assigned_severity_range", "tp": "is_true_positive",
           "sop": "expected_sop", "act": "recommended_action_label"}
    pairs = {k: ([], []) for k in R2_FIELDS}
    mism, n_both, n_all_match = [], 0, 0
    for i, r in enumerate(rows, 1):
        x = r2.get(r["alert_ref"])
        if not x or not (r.get(col["sev"]) or "").strip():
            continue
        n_both += 1
        diffs = []
        for k in R2_FIELDS:
            v1, v2 = (r[col[k]] or "").strip().lower(), (x[k] or "").strip().lower()
            pairs[k][0].append(v1)
            pairs[k][1].append(v2)
            if v1 != v2:
                diffs.append(f"{k}: {v1} vs {v2}")
        r["rater2_label"] = ";".join(f"{k}={x[k]}" for k in R2_FIELDS)
        r["agreement_flag"] = "match" if not diffs else "mismatch"
        n_all_match += not diffs
        if diffs:
            mism.append((i, r["alert_ref"], diffs))
    write_all(rows, fields)
    print(f"Số dòng có đủ 2 người gán: {n_both}; trùng hoàn toàn cả 4 trường: {n_all_match}/{n_both}")
    names = {"sev": "mức nghiêm trọng", "tp": "tấn công thật", "sop": "SOP", "act": "hành động"}
    for k in R2_FIELDS:
        a, b = pairs[k]
        if not a:
            continue
        po = sum(x == y for x, y in zip(a, b))
        kp = cohen_kappa(a, b)
        print(f"  {names[k]:18} trùng {po}/{len(a)} ({po / len(a):.0%})  Cohen's kappa = "
              f"{'n/a (một loại duy nhất)' if kp is None else f'{kp:.2f}'}")
    if mism:
        print("\nCác dòng lệch cần họp thống nhất (sửa thẳng vào cột nhãn của labels.csv bằng `label --row N`):")
        for i, ref, diffs in mism:
            print(f"  dòng {i} {ref}: " + "; ".join(diffs))
    print("\nĐã ghi rater2_label và agreement_flag vào labels.csv.")


# ---------- xem, kiểm tra ----------
def cmd_show(args):
    rows = read_rows()
    if args.row:
        show_alert(args.row, rows[args.row - 1])
        return
    shown = 0
    for i, r in enumerate(rows, 1):
        if args.split != "all" and r["split"] != args.split:
            continue
        if (r.get("expected_sop") or "").strip():
            continue
        show_alert(i, r)
        shown += 1
        if shown >= args.n:
            break
    if not shown:
        print("Không còn dòng nào chưa gán expected_sop trong split này.")


def cmd_check(args):
    rows = read_rows()
    ids = set(sop_ids())
    errs, done = [], 0
    sel = [(i, r) for i, r in enumerate(rows, 1) if args.split == "all" or r["split"] == args.split]
    for i, r in sel:
        vals = {k: (r.get(k) or "").strip() for k in FILL}
        if not any(vals.values()):
            continue
        before = len(errs)
        miss = [k for k, v in vals.items() if not v]
        if miss:
            errs.append(f"dòng {i}: thiếu {', '.join(miss)}")
        else:
            if vals["assigned_severity_range"] not in SEV_SET:
                errs.append(f"dòng {i}: assigned_severity_range='{vals['assigned_severity_range']}' (hợp lệ: {sorted(SEV_SET)})")
            if vals["is_true_positive"].lower() not in TP_SET:
                errs.append(f"dòng {i}: is_true_positive='{vals['is_true_positive']}' (yes/no/unsure)")
            if vals["expected_sop"] not in ids:
                errs.append(f"dòng {i}: expected_sop='{vals['expected_sop']}' không có trong data/sops/")
            if vals["recommended_action_label"] not in ACT_SET:
                errs.append(f"dòng {i}: recommended_action_label='{vals['recommended_action_label']}' (hợp lệ: {sorted(ACT_SET)})")
        if len(errs) == before:
            done += 1
    print(f"Split '{args.split}': đã gán đủ & hợp lệ {done}/{len(sel)} dòng.")
    kap = [r for _, r in sel if r["is_kappa_check_sample"] == "True"]
    if kap:
        r2 = read_rater2()
        n2 = sum(1 for r in kap if (r.get("rater2_label") or "").strip() or r["alert_ref"] in r2)
        print(f"Dòng kappa: {len(kap)} (người thứ hai đã gán {n2}).")
    if errs:
        print(f"\n{len(errs)} lỗi cần sửa:")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("Không có lỗi định dạng.")


def cmd_sops(_):
    for k, t in sop_ids().items():
        print(f"{k:28} {t}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, split=True, **kw):
        p = sp.add_parser(name)
        if split:
            p.add_argument("--split", default=kw.get("default_split", "dev"), choices=["dev", "test", "all"])
        p.set_defaults(fn=fn)
        return p

    p = add("label", cmd_label)
    p.add_argument("--labeler")
    p.add_argument("--row", type=int)
    p = add("rater2", cmd_rater2, default_split="all")
    p.add_argument("--labeler")
    add("kappa", cmd_kappa, split=False)
    p = add("show", cmd_show)
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--row", type=int)
    add("check", cmd_check)
    add("sops", cmd_sops, split=False)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
