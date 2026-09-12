# T16 · 写入点收敛 + 僵尸 MEMORY.md 副本清理（对应 S1/S3/D3/S2）· 2026-09-13

## ① 目标与结论

按任务书判定标准枚举并处置僵尸副本。**结论：当前已无满足移动标准的僵尸副本——9/12 汇聚轮与本轮 T2 已把真实写入点清空；剩余 2 份同名副本均位于 8 月底的 `_backup_/_inspect_` 目录（本就是存档形态），不满足「位于 `<workspace>\.workbuddy\memory\` 写入点」标准 → 归档 0 份、待人工判定 2 份，宁可漏归档不误伤。** 另产出「写入点地图 v1」供收敛参照。

## ② 枚举与分类对照表（每条附判定依据）

| 文件 | 大小 / mtime | 分类 | 判定依据 |
|---|---|---|---|
| `~\.workbuddy\MEMORY.md` | 38,941 B / 09-13 04:05 | **权威真身（L1）** | 白名单定案；T15 刚瘦身 |
| `2026-08-26-16-25-58\outputs\_backup_identity_max_123747\MEMORY.md` | 727 B / 08-27 | **待人工判定（不动）** | 位于显式命名的 `_backup_` 目录（已是备份形态），且**不在** `.workbuddy\memory\` 写入点，不满足移动标准 |
| `2026-08-26-16-25-58\outputs\_inspect_identity\WorkBuddy用户记忆导出_MAX迁移\memory\MEMORY.md` | 6,829 B / 08-28 | **待人工判定（不动）** | `_inspect_identity` 检查快照；路径虽含 `memory\` 但非 `<workspace>\.workbuddy\memory\` 写入点 |
| 同目录 `9bf805ae-…_memory.md` + `.bak` | 20.9 KB ×2 / 15.6 天前 | **待人工判定（不动）** | L0 云端画像本地缓存副本（L1 白名单「第三类记忆文件，勿动」的同类），属 8/28 身份审计的检查产物 |
| 工作区 `.workbuddy\memory\<date>.md` 日志副本 | — | **无残留** | T2 实测：汇聚+归档后全库 0 命中（`_t2_list.py` HOT_COUNT=0 且枚举为空） |
| `D:\WorkBuddyData\MEMORY.md` | 749 B | **指针（已处置）** | 9/12 已废弃指针化 |

> 任务书所记「6 份僵尸副本」与当前实测不符：其中日期型日志副本已被 9/12 汇聚轮处理，其余为上述检查/备份产物。**以实测为准（9.3 纪律），不做凑数归档。**

## ③ 写入点地图 v1（S1/S3 收敛的目标态，供迪莫复核）

| 层 | 唯一写入点 | 说明 |
|---|---|---|
| L1 稳定约定 | `~\.workbuddy\MEMORY.md` | T15 后 38 KB；历史细节 → `MEMORY_ARCHIVE_20260913.md`（只读） |
| L2 易变状态 | `~\.workbuddy\CURRENT_STATUS.md` | §十 台账已拆出（T3） |
| 待办台账 | `~\.workbuddy\OPEN_ITEMS.md` | 新建（T3），新增开放问题不再写 L2 |
| L3 日志 | `~\.workbuddy\L3_Daily\<date>.md` | append-only，并发追加走 `tools\mem_append.py`（T6） |
| 缺陷登记 | `~\.workbuddy\MEMORY_ISSUES.md` | 唯一登记处（已立） |
| workspace 双写 | `<workspace>\.workbuddy\memory\<date>.md` | 允许两写 + 每日汇聚归档（D6 机制，T2 已验证） |
| 人格/身份 | `SOUL/IDENTITY/USER.md`（D 根真身） | T5 方案待拍板 |

收敛建议（不执行，交迪莫）：把本表写进《记忆协作执行向导》头部（见 T17 改法清单），并让 `session_bootstrap.py` 注入文案与向导引用同一份表，消除"7 个指法"。

## ④ 产出物

- `tasks\_t16_enum.py`（枚举脚本）+ 本报告；**零文件移动**（无符合标准对象）。

## ⑤ 遗留

- 待人工判定 2 项（§② 标注）——若孟轩/迪莫确认归档，一行命令可移入 `_archive\workspace-memory-20260913\`。
