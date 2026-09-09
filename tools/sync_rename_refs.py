# -*- coding: utf-8 -*-
"""
引用同步器：把改名后的新文件名回填到引用了旧名的文件中
=========================================================
背景：tools/rename_zh.py 改了 96 个文档的文件名，导致引用这些名字的地方失效。
本脚本按同一张映射表，对指定目标文件做「basename 级」字符串替换。

目标文件（默认）
---------------
1. tools/kb_uploader.py      —— 57 条上传计划的 source 路径
2. 知识库上传清单.md          —— 上传计划 Markdown 版
3. 知识库文件夹映射表.md      —— 若引用了文档名
4. 其它被 grep 到的 .md      —— 文档内交叉引用

用法
----
    python tools/sync_rename_refs.py --dry-run
    python tools/sync_rename_refs.py --apply

安全
----
- 只替换「完整 basename」级匹配（含扩展名），不做模糊替换
- REPLACE 类的 4 个 target_file_name 是 KB 内既有名，**不在映射表内**，不会被误改
"""

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(r"D:\WorkBuddyData\projects\agent-learning")

# 从 rename_zh.py 复用同一张表，避免两处维护
import importlib.util
spec = importlib.util.spec_from_file_location("rename_zh", PROJECT_ROOT / "tools" / "rename_zh.py")
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

# (旧 basename, 新 basename)
PAIRS = [(Path(rel).name, new) for rel, new in rz.RENAMES]
# 长名优先，避免短名先替换导致错乱
PAIRS.sort(key=lambda x: -len(x[0]))

TARGETS = [
    "tools/kb_uploader.py",
    "知识库上传清单.md",
    "知识库文件夹映射表.md",
    "知识库分类方案_v2_20260908.md",
    "知识库分类方案_20260908.md",
    "资料盘点与上传清单_20260908.md",
]

# 额外：自动发现引用了旧名的其它 md（限项目内，排除 .git/venv）
def discover_extra() -> list[str]:
    extra = []
    for p in PROJECT_ROOT.rglob("*.md"):
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        if rel.startswith(".git/") or rel.startswith("venv/"):
            continue
        if rel in TARGETS:
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if any(old in t for old, _ in PAIRS):
            extra.append(rel)
    return extra


def sync_file(rel: str, dry: bool) -> int:
    p = PROJECT_ROOT / rel
    if not p.exists():
        print(f"  ⚠️ 跳过（不存在）: {rel}")
        return 0
    text = p.read_text(encoding="utf-8")
    n = 0
    for old, new in PAIRS:
        if old in text:
            c = text.count(old)
            n += c
            if not dry:
                text = text.replace(old, new)
    if n and not dry:
        p.write_text(text, encoding="utf-8")
    print(f"  {'[dry] ' if dry else '[sync]'} {rel}: {n} 处")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--with-extra", action="store_true",
                    help="一并扫描并同步其它引用了旧名的 md")
    a = ap.parse_args()
    dry = not a.apply

    files = list(TARGETS)
    if a.with_extra:
        ex = discover_extra()
        print(f"发现额外引用旧名的 md：{len(ex)} 个")
        files += ex

    total = 0
    for f in files:
        total += sync_file(f, dry)
    print(f"\n{'[dry-run] ' if dry else ''}共替换 {total} 处引用")
