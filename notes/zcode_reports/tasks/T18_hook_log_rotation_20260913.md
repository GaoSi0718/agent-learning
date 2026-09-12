# T18 · hook_run.log 按月轮转（对应 D13）· 2026-09-13

## ① 目标与结论

**结论：已完成并首轮执行。** `D:\WorkBuddyData\tools\rotate_hook_log.py` 交付（原子改名轮转 + mem_append 带锁合并 + 保留最近 3 个月、超龄移入 `_archive/hook-logs/` 只移不删）；首轮实测：**121 行 / 5,388 B 完整迁入 `hook_run-202609.log`**，`hook_run.log` 由下次 hook 执行自动重建。

## ② 实际执行（原始输出）

```
$ python rotate_hook_log.py
OK 轮转 → D:\WorkBuddyData\notify\hook_run-202609.log（121 行，直接落位）
当前月度文件: hook_run-202609.log     （退出码 0）
复核：hook_run-202609.log = 121 行 / 5,388 B ✓（与轮转前逐字节一致）
```

## ③ 设计要点

- **rename 而非复制+清空**：`os.replace` 原子改名，正在写日志的句柄不受影响；写手下次 open("a") 自动重建 `hook_run.log`——不存在"复制与清空之间丢行"的窗口。
- 若文件被占用（PermissionError）→ 本次放弃返回 4（不硬来）。
- 同月二次轮转 → mem_append 原子合并（复用 T6 的锁机制），原始片段移 `_archive/hook-logs/`。
- **保留 3 个月**：更老月度文件移入 `_archive/hook-logs/`（**不删除**，红线 #6 合规）。

## ④ 产出物

- `tools/rotate_hook_log.py`；`hook_run-202609.log`（121 行）；MEMORY_ISSUES D13 → 🟡（例行化待排期）。

## ⑤ 遗留

- **例行化**：建议迪莫把「每月 1 日跑一次 `rotate_hook_log.py`」加入自动化/hy4 批次（当前 hy4_daily.md 处于时间窗管制，本轮未追加；补丁包亦未含此项，需单独裁决）。
- 有效期与复测：下次轮转前 `hook_run.log` 会从 0 行重新累积——**属预期**，不是日志丢失。
