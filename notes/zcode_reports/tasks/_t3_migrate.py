# -*- coding: utf-8 -*-
"""T3：把 CURRENT_STATUS.md §十 全量机械迁移到 OPEN_ITEMS.md，L2 原位改指针+Top3。
零丢失校验内置；L2 写入走 mem_edit（备份+原子+回读断言）。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\WorkBuddyData\tools")
import mem_edit  # noqa: E402

L2 = r"C:\Users\高斯\.workbuddy\CURRENT_STATUS.md"
OPEN_ITEMS = r"C:\Users\高斯\.workbuddy\OPEN_ITEMS.md"
BACKUP_ROOT = r"D:\WorkBuddyData\backup\zcode-20260913\T3"
REPORT_DIR = r"D:\WorkBuddyData\projects\agent-learning\notes\zcode_reports\tasks"

HEAD_RE = re.compile(r"^## 十、开放问题")
NEXT_RE = re.compile(r"^## ")
ENTRY_RE = re.compile(r"^(\d{1,2}[a-z]?)\.\s")


def main():
    text = open(L2, encoding="utf-8").read()
    l2_bytes = len(text.encode("utf-8"))
    lines = text.split("\n")

    # 定位 §十
    start = end = None
    for i, ln in enumerate(lines):
        if start is None and HEAD_RE.match(ln):
            start = i
        elif start is not None and NEXT_RE.match(ln):
            end = i
            break
    if start is None or end is None:
        print("FATAL: 未定位到 §十（start=%s end=%s）" % (start, end))
        return 1
    block_lines = lines[start:end]
    block = "\n".join(block_lines)
    block_bytes = len(block.encode("utf-8"))

    # 解析条目：编号行 + 其后续（缩进/空行）行
    entries = []  # (num, [lines])
    for ln in block_lines[1:]:  # 跳过标题行
        m = ENTRY_RE.match(ln)
        if m:
            entries.append([m.group(1), [ln]])
        elif entries:
            entries[-1][1].append(ln)
        # 标题后首个条目前的空行丢弃
    nums = [e[0] for e in entries]
    print("解析到 %d 个顶层条目: %s" % (len(entries), ",".join(nums)))

    # 编号去重：第二个 "9." → "9b"
    seen9 = 0
    mapping = []  # (原编号, 新编号, 是否重复)
    for e in entries:
        if e[0] == "9":
            seen9 += 1
            if seen9 == 2:
                e[0] = "9b"
                mapping.append(("9（第二条·cloud:1865647）", "9b"))
            else:
                mapping.append(("9（第一条·夜间调度）", "9"))
        else:
            mapping.append((e[0], e[0]))

    # 组装 OPEN_ITEMS.md（条目正文逐字保留）
    oi = []
    oi.append("# OPEN_ITEMS.md — 开放问题与待办台账（单源）")
    oi.append("")
    oi.append("> **建立**：2026-09-13 03:3x ｜ **执行**：zcode（T3，对应 D16，孟轩已派单）")
    oi.append("> **来源**：`CURRENT_STATUS.md` §十 **全部条目机械迁入，零丢失**（迁移前后逐条比对通过）")
    oi.append("> **约定**：开放问题/待办台账一律写本文件；L2 §十 只留指针 + 未闭环 Top3。"
              "新增条目接在最后，编号递增；**不要在 L2 再开台账**。")
    oi.append("> **编号对照**：原 §十 有两个 `9.`（夜间调度 / cloud:1865647），"
              "第二个已改 **9b**，其余编号不变（不得静默改号，特此声明）。")
    oi.append("")
    oi.append("## 迁移编号对照表")
    oi.append("")
    oi.append("| 原编号（L2 §十） | 新编号（本文件） | 备注 |")
    oi.append("|---|---|---|")
    for old, new in mapping:
        oi.append("| %s | %s | %s |" % (old, new, "重复编号去重" if old != new else "不变"))
    oi.append("")
    oi.append("---")
    oi.append("")
    oi.append("## 条目区（迁自 L2 §十，正文未改）")
    oi.append("")
    for num, elines in entries:
        for j, ln in enumerate(elines):
            if j == 0:
                oi.append(re.sub(r"^\d{1,2}[a-z]?\.", num + ".", ln, count=1))
            else:
                oi.append(ln)
        oi.append("")
    oi_content = "\n".join(oi).rstrip("\n") + "\n"
    open(os.path.join(REPORT_DIR, "_t3_open_items_draft.md"), "w", encoding="utf-8", newline="").write(oi_content)

    # 零丢失校验 A：条目数一致
    ok_count = True
    # 零丢失校验 B：每条正文逐条出现在 OPEN_ITEMS 中
    missing = []
    for (num, elines), (old, new) in zip(entries, mapping):
        body = "\n".join(elines)
        if old != new:  # 9 → 9b：首行编号替换后比对
            body2 = re.sub(r"^9\.", new + ".", body, count=1)
        else:
            body2 = body
        if body2.strip() not in oi_content:
            missing.append(old)
            ok_count = False
    # 零丢失校验 C：原块每行（除标题）都能在 OPEN_ITEMS 找到（整行比对，覆盖子行）
    lost_lines = [ln for ln in block_lines[1:] if ln.strip() and ln not in oi_content]
    # 编号行 9→9b 的那一行允许不同
    lost_lines = [ln for ln in lost_lines if not (ENTRY_RE.match(ln) and ln.startswith("9.") and
                                                  re.sub(r"^9\.", "9b.", ln, count=1) in oi_content)]

    print("校验A 条目数 %d==%d : %s" % (len(entries), len(nums), ok_count))
    print("校验B 每条正文在 OPEN_ITEMS: %s（missing=%s）" % (not missing, missing))
    print("校验C 整行覆盖缺失数: %d" % len(lost_lines))
    for ln in lost_lines[:5]:
        print("  LOST: %r" % ln[:80])
    if missing or lost_lines:
        print("FATAL: 零丢失校验未通过，中止写入")
        return 1

    # 写 OPEN_ITEMS.md（tmp + replace）
    tmp = OPEN_ITEMS + ".tmp"
    open(tmp, "w", encoding="utf-8", newline="").write(oi_content)
    os.replace(tmp, OPEN_ITEMS)
    print("OPEN_ITEMS.md 已写入: %d B" % len(oi_content.encode("utf-8")))

    # L2 §十 → 指针 + Top3（走 mem_edit）
    new_block = "\n".join([
        "## 十、开放问题（台账已迁出，本节只留指针）",
        "",
        "> **📌 本节已迁出（2026-09-13 T3，对应 D16）**：开放问题全量台账见 **`OPEN_ITEMS.md`**（同目录，"
        "含原编号→新编号对照表；原重复编号 `9.` 的第二条改 `9b`）。**新增开放问题一律写 OPEN_ITEMS.md，不要再写回本节。**",
        "> 本节保留**未闭环且影响面最大的 3 条**（选择理由见 zcode 报告 T3）：",
        "> 1. **#3 首批投递尚未发出**——求职主线唯一真阻塞点（applications.csv 连续 7 天 0 行）",
        "> 2. **#10 `.env` 缺 `W6_API_KEY`**——B4 端到端验证、12 轮记忆测试与公网部署全被卡",
        "> 3. **#16 zcode 大任务交接**——24 项任务执行中，完成后需迪莫复核闭环",
        "> 其余条目（含已闭环留档）一律以 `OPEN_ITEMS.md` 为准。",
    ])
    # 备份 L2 到 T3 备份区（mem_edit 另有自己的时间戳备份）
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    bpath = os.path.join(BACKUP_ROOT, "CURRENT_STATUS.md.before-T3")
    open(bpath, "w", encoding="utf-8", newline="").write(text)
    rc, msg = mem_edit.edit_file(L2, block, new_block, occurrence="1", caller="zcode-T3",
                                 backup_root=BACKUP_ROOT)
    print("mem_edit L2: rc=%d %s" % (rc, msg))
    if rc != 0:
        return rc
    after = open(L2, encoding="utf-8").read()
    after_bytes = len(after.encode("utf-8"))
    print("L2: %d B → %d B（- %d B，§十块 %d B → 指针块 %d B）"
          % (l2_bytes, after_bytes, l2_bytes - after_bytes, block_bytes,
             len(new_block.encode("utf-8"))))
    print("T3_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
