# -*- coding: utf-8 -*-
"""
清理文档中的「版本迭代痕迹」标记。

背景：P0 执行清单历经 v1.1 -> v1.9 共 9 轮修订，正文中残留大量
「（v1.6 新增）」「（v1.4 修订）」这类元信息标记。它们对执行没有帮助，
反而打断阅读沉浸感（典型如「v1.6 升级为 MoSCoW 三层，原 ★/☆ 两档作废」）。

本脚本只删除「文档版本号 + 修订动作词」的组合，
不碰 W6 v1.5 / W6 v1.6 / W6 v1.7 这类「项目版本号」。

用法：python clean_version_marks.py <文件路径> [--apply]
默认 dry-run，打印将要发生的替换；加 --apply 才真正写盘。
"""

import re
import sys
from pathlib import Path

# (正则, 替换) —— 顺序敏感，先长后短
RULES = [
    # 括号内的版本号 + 动作词，整体删除或只留动作词之后的内容
    (r"（v1\.\d 新增 · ", "（"),
    (r"（v1\.\d 更新 · ", "（"),
    (r"（v1\.\d 新增 · ", "（"),
    (r"（v1\.\d 新增，", "（"),
    (r"（v1\.\d 新增）", ""),
    (r"（v1\.\d 修订）", ""),
    (r"（v1\.\d 修订：", "（"),
    (r"（v1\.\d 补）", ""),
    (r"（v1\.\d）", ""),
    (r"（v1\.\d 收缩，", "（"),
    (r"（v1\.\d 移出 P0）", "（已移出 P0）"),
    (r"（v1\.\d \*\*移出", "（**移出"),
    (r"（v1\.\d 降级为", "（"),
    # 括号外：动作词前的版本号直接去掉，保留动作本身
    (r"v1\.\d 已删除", "已删除"),
    (r"v1\.\d 已收缩", "已收缩"),
    (r"v1\.\d 维持", "维持"),
    (r"v1\.\d 整合方式", "整合方式"),
    (r"\*\*v1\.\d 处置\*\*", "**处置**"),
    (r"\*\*v1\.\d 处置（", "**处置（"),
    (r"v1\.\d 修订：", ""),
    # 分号/顿号连接的尾部标记
    (r"；v1\.\d 修订）", "）"),
    (r"；v1\.\d 补）", "）"),
    (r"；v1\.\d 新增）", "）"),
    (r" · v1\.\d 新增）", "）"),
    (r" · \*\*v1\.\d 新增\*\*）", "）"),
    (r"，v1\.\d 新增）", "）"),
    (r"，v1\.\d 起", "，"),
    (r"，v1\.\d 新增", "，"),
    (r" · v1\.\d 收缩）", " · 已收缩）"),
]


def clean(text: str):
    hits = []
    for pattern, repl in RULES:
        new_text, n = re.subn(pattern, repl, text)
        if n:
            hits.append((pattern, n))
            text = new_text
    return text, hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = Path(sys.argv[1])
    apply = "--apply" in sys.argv
    original = path.read_text(encoding="utf-8")
    cleaned, hits = clean(original)

    print(f"文件：{path.name}")
    print(f"命中规则 {len(hits)} 条，共 {sum(n for _, n in hits)} 处替换")
    for pattern, n in hits:
        print(f"  {n:>3} 处  {pattern}")
    print(f"行数：{original.count(chr(10))} -> {cleaned.count(chr(10))}")

    if apply:
        path.write_text(cleaned, encoding="utf-8")
        print("\n已写盘。")
    else:
        print("\n[dry-run] 未写盘，加 --apply 执行。")


if __name__ == "__main__":
    main()
