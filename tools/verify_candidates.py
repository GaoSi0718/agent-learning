# -*- coding: utf-8 -*-
# tools/verify_candidates.py
"""Z4 校验脚本：逐行检查 candidates_80.csv 的硬约束，输出报告。
检查项：
  A. 7 列齐全且无空值；
  B. source_excerpt 能在 policy_context.txt 语料中【原文连续】找到（防拼接/改写）；
  C. category ∈ 5 类，且每类 ≥10 题；总行数 ≥80；
  D. reference_answer 中一切数字都能在语料中找到（反幻觉复核）；
  E. question 无重复（近似去重：去空白后全等）。
用法：venv\\Scripts\\python.exe tools\\verify_candidates.py
退出码：全部通过 0；任一 FAIL 1。报告同时落盘 notes/eval_expansion/verify_report.txt
"""
import csv, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "notes" / "eval_expansion" / "candidates_80.csv"
CORPUS = ROOT / "policy_context.txt"
CATEGORIES = ["加班", "试用期", "年休假", "考勤与请假", "薪酬与社保"]

def main():
    lines = []
    def say(s=""):
        print(s)
        lines.append(s)

    corpus = CORPUS.read_text(encoding="utf-8")
    say(f"语料：{CORPUS.name} {len(corpus)} 字")

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    say(f"CSV 数据行：{len(rows)}")

    fails = []
    def check(cond, msg):
        say(("  [OK] " if cond else "  [FAIL] ") + msg)
        if not cond:
            fails.append(msg)

    # A. 列完整
    need_cols = ["q_id", "question", "reference_answer", "source_chunk_id",
                 "source_excerpt", "category", "proposed_by"]
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    check(header == need_cols, f"表头 7 列且顺序一致：{header == need_cols}")
    empty = [r["q_id"] for r in rows if any(not (r.get(c) or "").strip() for c in need_cols)]
    check(not empty, f"无空值单元格（空值行：{empty[:5]}）")

    # B. excerpt 原文命中
    miss = [r["q_id"] for r in rows if r["source_excerpt"] not in corpus]
    check(not miss, f"source_excerpt 全部原文命中语料（未命中 {len(miss)} 条：{miss[:5]}）")

    # C. 类别分布与总量
    dist = Counter(r["category"] for r in rows)
    for cat in CATEGORIES:
        check(dist.get(cat, 0) >= 10, f"类别「{cat}」≥10 题（实际 {dist.get(cat, 0)}）")
    extra = set(dist) - set(CATEGORIES)
    check(not extra, f"无超出 5 类的杂项类别（{extra or '无'}）")
    check(len(rows) >= 80, f"总行数 ≥80（实际 {len(rows)}）")

    # D. 反幻觉复核
    bad_num = []
    for r in rows:
        for x in re.findall(r"\d+(?:\.\d+)?", r["reference_answer"]):
            if x not in corpus:
                bad_num.append((r["q_id"], x))
    check(not bad_num, f"答案中数字全部见于语料（违例：{bad_num[:5]}）")

    # E. 去重
    qs = [re.sub(r"\s+", "", r["question"]) for r in rows]
    dup = [q for q, n in Counter(qs).items() if n > 1]
    check(not dup, f"问题无重复（重复：{dup[:5]}）")

    say("\n===== 类别分布明细 =====")
    for cat in CATEGORIES + sorted(extra):
        say(f"  {cat}: {dist.get(cat, 0)}")
    verdict = "ALL PASS" if not fails else f"FAIL x{len(fails)}"
    say(f"\n结论：{verdict}")
    (ROOT / "notes" / "eval_expansion" / "verify_report.txt").write_text(
        "\n".join(lines), encoding="utf-8")
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    main()
