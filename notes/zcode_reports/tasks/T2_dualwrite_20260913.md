# T2 · harness 双写点：汇聚器验证（对应 D6，已降级任务）· 2026-09-13

## ① 目标与结论

验证 `D:\WorkBuddyData\tools\consolidate_workspace_memory.py` 的四项能力并补缺口分析。**结论：脚本功能属实，已执行一次 `--apply`（汇聚 5 / 归档 5 / 失败 0），幂等验证通过，未改任何代码。**

## ② 逐条能力复核（代码行号对照）

| 声称能力 | 代码位置 | 实测 |
|---|---|---|
| 默认 dry-run | L49 `--apply` 开关 + L94-96 无开关即 return | ✅ 首跑未落盘 |
| 幂等（不重复追加） | L70 `already = body[:400] in l3txt` | ✅ 复跑 dry-run = 0 命中 |
| 归档到 `_archive/`（移动非删除） | L112-114 `shutil.move` → `_archive/workspace-memory-<ts>/` | ✅ 目录 `workspace-memory-20260913_033224` 已建，源文件已移出 |
| `--apply` / `--no-archive` 开关 | L49-50 | ✅（本次未用 no-archive） |

⚠️ 一处文档与实现的小出入：docstring 说归档目录 `workspace-memory-<date>`，实际用 `<stamp>`（`%Y%m%d_%H%M%S` 带时分秒）——无碍，反而防同日多次执行互相覆盖。

## ③ dry-run 与 apply 实测数据

**残留现状（apply 前）**：仅 **5 个文件 / 19,070 B / 2 个日期**——与登记的「42 目录 / 88 个 .md / ≈500 KB」**不同量级，原因是 9/12 已跑过汇聚**（MEMORY_ISSUES §三「用后即归档」），这 5 个是其后的新增残留。5 个路径全部为 `<workspace>\.workbuddy\memory\<date>.md` 形态，**无计划外目录**（最年轻 mtime 25.8 分钟前，无热文件）。

**apply 原始输出**：
```
执行完成：汇聚 5 ｜ 归档 5 ｜ 失败 0      （退出码 0）
L3_Daily/2026-09-12.md：508 行 → 527 行（+19）
L3_Daily/2026-09-13.md：147 行 → 353 行（+206）
```
行数只增不减，append-only 达标；复跑 dry-run 命中 0（幂等）；HOT_COUNT=0（源文件已清空）。

## ④ 缺口分析（本任务真正的增量）

**注入文案原文摘录**（`D:\WorkBuddyData\notify\session_bootstrap.py` `_residue_note()`）：
> `⚠️ 检测到 %d 个 workspace 日志副本近 24h 被写入（双写点仍在活动）→ 应并入 D:\Users\高斯\.workbuddy\L3_Daily 后归档`

**「允许两写 + 汇聚」是否足够？** 判断：**目前足够，暂不需改 harness**。依据：
1. 残留增速实测 ≈ 5 个 / 19 KB / 天（5 个会话），汇聚器一次即清零，量级可控；
2. `session_bootstrap.py` 已在每次会话注入「应并入 L3_Daily」的正确写点指引，残留来自仍按旧 harness 指令写的会话，属收敛中的尾部；
3. harness 侧（系统注入文案本身）改动属系统源码，**超出本清单授权**，且收益（省一次汇聚）远小于风险。

**建议（只建议，不执行）**：把「跑一次 `consolidate_workspace_memory.py --apply`」加进 `hy4_daily.md` §2 常驻任务，使汇聚至少每日一次；由迪莫裁决是否落地（该文件有另外两个写手，且 T20 受时间窗约束）。

**发现的脚本局限（记录，未改代码）**：幂等判据是「正文前 400 字符是否已在 L3」——若两个不同 workspace 同日副本以相同模板开头，第二个会被误判「已在 L3，仅归档」（数据不丢但未并入 L3）。建议后续改为「workspace 路径前缀 + 全文比对」。

## ⑤ 产出物清单

- 归档区：`C:\Users\高斯\.workbuddy\_archive\workspace-memory-20260913_033224\`（5 个文件，保留相对路径）
- L3 追加：`L3_Daily\2026-09-12.md` / `2026-09-13.md` 各一个「【汇聚】来源：」区块
- 本报告；辅助脚本 `tasks\_t2_list.py`（列残留+热度）

## ⑥ 验证证据

见 ③ 的行数对比与幂等复跑；`--apply` 退出码 0；归档目录实测存在。

## ⑦ 遗留 / 阻塞

- 无阻塞。归档为移动非删除，符合红线 #6。
