# -*- coding: utf-8 -*-
"""hy4_daily.md 补丁包（T20/D10 守卫 + F1A 建议①③④）· 自带时间窗守卫 · v2（R-003⑤ 回写版）

历史：v1（2026-09-13 03:48）的 P1/P2/P4 为「锚点后追加」式编辑（new 包含 old），与
mem_edit 旧版回读断言「old 不得残留」冲突 → 恒 rc=5（迪莫 15:4x 实测发现，FB-04）。
处置：① mem_edit 已改为「逐字节一致」断言（12/12 PASS，追加式回归用例⑨通过）；
② 迪莫已用跨边界锚点版 _apply_hy4_patches_fixed_20260913.py 于 15:48 落地四处补丁；
③ 本脚本改为**幂等**：检测到四处守卫已存在 → 直接报 ALREADY_APPLIED（rc=0），不再重复编辑。

⛔ 只允许在 23:05–08:00 窗口【之外】运行（夜间批次会读本文件，窗口内改动可能被读半截）。
用法：<受管 python> _apply_hy4_patches.py
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, r"D:\WorkBuddyData\tools")
import mem_edit  # noqa: E402

TARGET = r"D:\WorkBuddyData\projects\agent-learning\nightshift\hy4_daily.md"
BACKUP_ROOT = r"D:\WorkBuddyData\backup\zcode-20260913\T7_T20_hy4patch"

# 四处守卫的「已存在」判据（与迪莫落地版正文一致）
MARKERS = [
    ("T20/D10 mtime 守卫（§1 第 11 条）", "写入前 mtime 校验（2026-09-13 T20 补"),
    ("F1A① 并发窗口声明（§1 第 12 条）", "并发窗口声明（F1A 建议①"),
    ("F1A③ 快照起点行（F1 命令块）", 'date "+%Y-%m-%d %H:%M:%S 快照起点"'),
    ("F1A④ 漂移声明（F1 产出模板 ④）", "执行期间检测到 N 个文件被外部写入"),
]


def in_window():
    h = datetime.now().hour + datetime.now().minute / 60.0
    return h >= 23.083 or h < 8.0  # 23:05 起


def main():
    if in_window() and "--force" not in sys.argv:
        print("REFUSED: 当前处于 23:05–08:00 夜间批次窗口，禁止改动 hy4_daily.md。请在 08:00 后运行。")
        return 3
    text = open(TARGET, encoding="utf-8").read()
    missing = [name for name, marker in MARKERS if marker not in text]
    if not missing:
        print("ALREADY_APPLIED: 四处守卫已全部存在（迪莫 15:48 版已落地），无需重复编辑（rc=0）")
        return 0
    print("MISSING: %s → 需要执行补丁" % "; ".join(missing))

    patches = []
    a10 = "10. **断点续跑**：任何一项因额度/超时中断，都要在报告里写明「已完成 / 未完成 / 顺延去向」，**不得静默跳过**。"
    b10 = a10 + ("\n11. **写入前 mtime 校验（2026-09-13 T20 补，对应 D10）**：任何写 `CURRENT_STATUS.md` 的动作，"
                 "须先记录 mtime + sha256，写入前再核对；不一致则放弃写入并记入报告。"
                 "推荐直接用 `D:\\WorkBuddyData\\tools\\mem_edit.py`（自带指纹守卫与原子写）。"
                 "\n12. **并发窗口声明（F1A 建议①，2026-09-13 T7 落地）**：夜间批次**默认工作区处于并发编辑态**；"
                 "所有读数须在报告首行标注「快照时点 HH:MM」，且**不得使用「当前/最新」等绝对表述**。")
    if "写入前 mtime 校验" not in text:
        patches.append(("P1P2_§1条11条12", a10, b10))
    a3 = "cd /d/WorkBuddyData/projects/agent-learning\n\n# ⚠️ 未推送 commit"
    b3 = ("cd /d/WorkBuddyData/projects/agent-learning\n"
          'date "+%Y-%m-%d %H:%M:%S 快照起点"   # F1A 建议③：所有读数须带时点，写进产出文件首行\n\n# ⚠️ 未推送 commit')
    if "快照起点" not in text:
        patches.append(("P3_F1快照起点行", a3, b3))
    a4 = "**产出** `F1_env_check_<日期>.md`：① 逐项「实测值 vs CURRENT_STATUS 记录值 vs 是否漂移」三列表；" \
         "② 漂移项标严重度（P0/P1/P2）+ 建议改法；③ 大文件清单（如有）。"
    b4 = a4 + "；④ 报告首行须有「⚠️ 本表为 HH:MM 快照；执行期间检测到 N 个文件被外部写入，数值可能已漂移」。"
    if "执行期间检测到 N 个文件被外部写入" not in text:
        patches.append(("P4_F1模板④漂移声明", a4, b4))
    if not patches:
        print("ALREADY_APPLIED: 缺失项经二次核对均已存在（可能被并发会话补齐），不编辑")
        return 0

    for name, old, new in patches:
        n = text.count(old)
        if n != 1:
            print("ABORT %s：锚点命中 %d 处（需 1），不做任何改动" % (name, n))
            return 2
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    rc_all = 0
    for name, old, new in patches:
        rc, msg = mem_edit.edit_file(TARGET, old, new, occurrence="1", caller="zcode-T7T20-v2",
                                     backup_root=BACKUP_ROOT)
        print("%s: rc=%d %s" % (name, rc, msg))
        if rc != 0:
            rc_all = rc
            break
    print("PATCH_DONE" if rc_all == 0 else "PATCH_INCOMPLETE")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
