# -*- coding: utf-8 -*-
# tools/audit_metrics.py
"""Z10：全库口径一致性扫描——D12（数字唯一权威=docs/metrics_log.md）的常态化防御工具。
用法（cwd 任意）：
  venv\\Scripts\\python.exe tools\\audit_metrics.py                # 扫全库，stdout 出 Markdown 表
  venv\\Scripts\\python.exe tools\\audit_metrics.py --out <path>   # 同时落盘
扫描口径：
  0.474 / 0.6607 / 0.674 / 0.66（裸写，可能是截断引用，需人工判定）+ 违规短语
  「准确率 67 / 75」（W6 指标禁用「准确率」一词）与「千条级 / 生产级」（D9 禁词）。
范围：项目根全部文本文件，剔除 .git/venv/__pycache__/数据大文件。零 API 成本。
输出列：文件:行号 | 命中类型 | 行摘录（每处截 90 字）。判定列由人工（zcode/迪莫）在报告中补。"""
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules", "data"}
SKIP_SUFFIX = {".jsonl", ".png", ".pdf", ".docx", ".db", ".lock", ".csv"}
SKIP_FILES = {"policy_context.txt", "w6_sample_policy.txt"}   # 语料原文与数字无关
MAX_EXCERPT = 90

PATTERNS = [
    ("0.474", "对齐前口径(36题)"),
    ("0.6607", "对齐基线(40题)"),
    ("0.674", "最终基线(score2)"),
    ("0.66", "裸写0.66(疑似截断)"),
    ("准确率 67", "违禁短语"),
    ("准确率67", "违禁短语"),
    ("准确率 75", "违禁短语"),
    ("准确率75", "违禁短语"),
    ("千条级", "D9禁词"),
    ("生产级", "D9禁词"),
]

def iter_files():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in SKIP_SUFFIX or p.name in SKIP_FILES:
            continue
        if p.name.startswith("_audit_raw"):   # 审计原始表自身，防递归自指
            continue
        if p.name == Path(__file__).name:
            continue
        yield p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="同时写入指定文件")
    args = ap.parse_args()
    lines_out = ["| 文件:行号 | 命中类型 | 行摘录 |", "|---|---|---|"]
    total = 0
    for p in sorted(iter_files()):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[warn] 无法读取 {p}：{e}", file=sys.stderr)
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat, label in PATTERNS:
                if pat in line:
                    # 0.66 裸写只在「不是 0.6607/0.674 的一部分」时才独立报（避免重复噪声）
                    if pat == "0.66" and ("0.6607" in line or "0.674" in line or "0.660" in line):
                        continue
                    excerpt = line.strip().replace("|", "\\|")
                    if len(excerpt) > MAX_EXCERPT:
                        excerpt = excerpt[:MAX_EXCERPT] + "…"
                    rel = p.relative_to(ROOT)
                    lines_out.append(f"| {rel.as_posix()}:{i} | {label}（{pat}） | {excerpt} |")
                    total += 1
    table = "\n".join(lines_out) + f"\n\n> 共 {total} 处命中。判定规则：三口径数字均须带口径全称；裸 0.66 与违禁短语一律需勘误或改写。\n"
    print(table)
    if args.out:
        Path(args.out).write_text(table, encoding="utf-8")
        print(f"[audit] 已写入 {args.out}", file=sys.stderr)

if __name__ == "__main__":
    main()
