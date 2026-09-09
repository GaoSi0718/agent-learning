# -*- coding: utf-8 -*-
"""
zcode_reports 编号文件补命名（2026-09-08）
==========================================
背景：rename_zh.py 第一版跳过了 zcode_reports 里 17 个「纯编号+日期」文件，
理由是文件名无英文描述词、不知道主题。现读取各文件「任务名称」字段后补上中文主题。

规则：编号 + 中文主题 + 日期后缀；技术词（venv / API / Agent / Gate / SSE）保留。

用法：
    python tools/rename_zcode.py --dry-run
    python tools/rename_zcode.py --apply
    python tools/rename_zcode.py --rollback
"""

import argparse
from pathlib import Path

ROOT = Path(r"D:\WorkBuddyData\projects\agent-learning\notes\zcode_reports")

RENAMES = [
    ("A1_20260906.md",  "A1_W1周复盘_20260906.md"),
    ("A2_20260906.md",  "A2_G1基线验收_20260906.md"),
    ("A3_20260906.md",  "A3_W6评估转简历素材_20260906.md"),
    ("B1_20260906.md",  "B1_W6的SSE与记忆系统_20260906.md"),
    ("B2_20260906.md",  "B2_W6多工具Agent化_20260906.md"),
    ("C2_20260906.md",  "C2_Agent终止三件套_20260906.md"),
    ("Z1_20260907.md",  "Z1_venv重建与依赖锁定_20260907.md"),
    ("Z2_20260907.md",  "Z2_API鉴权与限流_20260907.md"),
    ("Z3_20260907.md",  "Z3_超时重试降级骨架_20260907.md"),
    ("Z4_20260907.md",  "Z4_评测集候选池流水线_20260907.md"),
    ("Z5_20260907.md",  "Z5_交接补记_20260907.md"),
    ("Z6_20260907.md",  "Z6_C类面试考点笔记_20260907.md"),
    ("Z7_20260907.md",  "Z7_投递清单30家_20260907.md"),
    ("Z8_20260907.md",  "Z8_一键自测与Gate脚本_20260907.md"),
    ("Z9_20260907.md",  "Z9_简历双轨草稿_20260907.md"),
    ("Z11_20260907.md", "Z11_九月AI岗位情报速报_20260907.md"),
    ("Z12_20260907.md", "Z12_年假口径与循环越界修复_20260907.md"),
]


def run(dry: bool, rollback: bool = False):
    ok = fail = 0
    items = reversed(RENAMES) if rollback else RENAMES
    for old_n, new_n in items:
        src, dst = (ROOT / new_n, ROOT / old_n) if rollback else (ROOT / old_n, ROOT / new_n)
        if not src.exists():
            print(f"  ⚠️ 跳过（不存在）: {src.name}")
            fail += 1
            continue
        if dst.exists():
            print(f"  ⚠️ 跳过（目标已存在）: {dst.name}")
            fail += 1
            continue
        if dry:
            print(f"  [dry] {src.name}  →  {dst.name}")
        else:
            src.rename(dst)
            print(f"  [{'undo' if rollback else 'mv'}] {src.name}  →  {dst.name}")
        ok += 1
    print(f"\n{'[dry-run] ' if dry else ''}成功 {ok} / 失败 {fail}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    a = ap.parse_args()
    run(dry=not a.apply, rollback=a.rollback)
