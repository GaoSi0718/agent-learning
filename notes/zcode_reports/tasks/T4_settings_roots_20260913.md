# T4 · settings.json 双根分叉定性（对应 D1）· 2026-09-13（只读任务，未改任何文件）

## ① 目标与结论

判定两个根的 `settings.json` 哪份生效、差异性质。**结论：非功能冲突的分叉——共用键值完全一致，D 根独有 claw 通道运行态 / 插件清单 / sandbox 扩展；「唯一生效源」无法单源判定，倾向「C 根=主配置、D 根=Claw 通道实时状态落点」（置信度中等，附反证条件）。不建议合并覆盖。**

## ② 逐键差异表（共用且相等的键已过滤；敏感值脱敏）

| 键 | C 根（2,523 B，09-12 19:02） | D 根（5,747 B，09-12 00:59） | 性质 |
|---|---|---|---|
| `sandbox.extraAllowWrite` | 11 项 | 12 项（多 `~/AppData/Local/AgentConnectors/`） | 值异（D 为超集） |
| `enabledPlugins`（document-skills / finance-data / playwright-cli / weixinpay=false 等） | 缺失 | 有 | 仅 D |
| `claw.users.<uid>.channels.qq.*`（含 appId/appSecret） | 缺失 | 有 | 仅 D（含敏感 token） |
| `claw.users.<uid>.channels.weixinClawBot.*`（含 botToken） | 缺失 | 有 | 仅 D（含敏感 token） |
| `claw…conversationBindings / requestDeliveries`（投递状态、cwd） | 缺失 | 有，时间戳 9/11 晚 | 仅 D（运行态） |
| `autoLaunchDesired` | 缺失 | true | 仅 D |
| hooks 段及其他共用键 | 一致 | 一致 | 无冲突 |

原始逐键输出：`tasks\_t4t5_evidence.py` 运行日志（本报告存档版已脱敏）。

## ③ 判定方法与证据（任务书 2/3/4 法）

1. **引用关系统计**：原始计数 C 根 108 处 vs D 根 55 处，但**两边都混入大量报告/manifest 文档性提及**；真正的运行时引用极少（`notify\session_check.py` 引 C 根；`tools\memory-audit\*.py` 维护脚本引 D 根）→ **不具判定力**。
2. **mtime 活跃度**：C 根 09-12 19:02，D 根 09-12 00:59（hooks 同步脚本所为）→ 都不"陈旧"，**弱证据**。
3. **hooks 段线索**：两根 hooks 一致（9/12 审计脚本同步）→ 证明 D 根被人为维护过，但不代表应用读它。
4. **🔑 补强证据（本任务新发现）**：D 根独有的 `claw.requestDeliveries/conversationBindings` 是**应用运行态**（QQ/微信机器人投递记录，时间戳 9/11 晚）→ 说明 **Claw 通道确实在读写 D 根**；而 C 根无任何 claw 段。同时，9/12 已定案的废弃指针 `D:\WorkBuddyData\MEMORY.md` 写明「记忆/约定类文档一律以 C 根为准」→ 记忆体系以 C 根为既定权威。

## ④ 判定结论

- **差异性质**：两根不是"同一配置的两份冲突版本"，更像 **C 根=应用主配置（hooks/sandbox/基础项），D 根=Claw IM 通道的独立配置+运行态存储**。所有共用键值一致，**不存在会引发 EBUSY 回归的实质冲突**（D1 描述的 `weixinpay` 差异实为 D 根插件清单显式 `false`、C 根缺省）。
- **哪份"生效"**：**无法单源判定**。倾向：C 根为主配置源、D 根为 Claw 专属源（置信度 ~60%）。**反证条件**：若在 C 根加一条 D 根没有的 hooks/插件项且重启后生效，则 C 根单源生效；若改 D 根 sandbox 后行为立即变化（不重启），则 D 根才是主源。
- **建议实验（需孟轩，本任务不做）**：改一处可观察项 + 重启应用验证（任务书法 1，最可靠）。
- **🔴 安全提醒**：D 根 settings.json 含**明文 appSecret/botToken**（微信/QQ 机器人凭据）——与风险登记册 #3（敏感信息落地）同类，建议迪莫评估是否收敛权限或迁移存储（只提醒，未动）。

## ⑤ 遗留 / 阻塞

- 本任务零写入（含 settings 两文件、MEMORY_ISSUES 状态行另行走 mem_edit）。
- D1 定性后处置建议：**保持双根现状**（合并覆盖有中断应用风险，且两根各有活跃读写方），将 D1 状态改「已定性：非冲突分叉，暂不合并」交迪莫复核。
