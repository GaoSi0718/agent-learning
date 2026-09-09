# 夜班交接文档（晨报 v3）· 2026-09-07 —— zcode → 迪莫 / 孟轩

> **本文件定位**：夜班（2026-09-06 23:07 → 09-07 02:00）**全部工作的唯一交接入口**。v3 为完整版（覆盖主队列 Z1–Z8 与续班迭代 R1–R18，替代此前 v1/v2 的部分段落）。通读约 10 分钟；逐任务细节见「附 A 报告索引」对应的报告文件。
> **值班**：zcode ｜ **门禁终态**：离线测试 **7/7 PASS** ｜ G1 Gate **8绿2红** ｜ 全量自检 **16/16 PASS** ｜ **28 commits** 已全部推送远端 ｜ API 成本 **≈$0.04**
> **纪律执行**：全程按路径精确 add（迪莫属主文件零接触、迪莫未提交改动零触碰）；每项任务四件套（产出/验证/commit/报告）齐备；数字一律对齐 metrics_log（D12）。

---

## 0. 30 秒摘要

Z1–Z8 全部完成（venv 重建/鉴权限流/可靠性骨架/84 条评测候选池/250 题库/面试笔记×3/32 家投递清单/一键自检脚本），另完成 18 轮自主迭代（C4 21 题逐题展开、简历双轨 v0.9、D1–D5 追问链、四模式可运行示例、记忆卡 250 张、bug 故事集、行业情报、3 个代码修复、WAL 升级、fallback 接线、4 个可复用工具、全量自检）。**唯一硬红仍是投递台账 0 行（只能孟轩执行）**；4 项裁决待迪莫；28 commits 已推送 `7bb7c63..fbf5b61`。

---

## 一、任务完成总台账

### 1.1 主队列 Z1–Z8（CONTEXT §10 指定）

| 任务 | 产出文件（相对项目根） | 验证结果 | commit |
|---|---|---|---|
| **Z1** venv 重建+锁版本 | `requirements.lock.txt`（54 包）；venv 原地重建（不入库） | 两离线测试 PASS；**venv 自报 3.13.14（目录名 3.13.12 名不符实，裁决①）** | 186424a/811a831 |
| **Z2** 鉴权+限流 | `w6_hr_policy/app/auth.py`、`app/rate_limit.py`、`app/main.py`（接线）；`tests/test_v17_auth.py` | 无Key/错Key 401、对Key 200 出流、61 连发第 61→429；**起真实服务跑通 b2_e2e+12 轮记忆联调** | 47734c8 |
| **Z3** B3 可靠性三件套 | `app/resilience.py`、`app/llm.py`（接线）、`tests/test_b3_resilience.py` | 重试（超时/连接/5xx/429）/降级 5 断言；最小真实调用验证 | 2e39781 |
| **Z4** 评测候选池流水线 | `tools/gen_eval_candidates.py`、`tools/verify_candidates.py`、`notes/eval_expansion/`（candidates_80.csv **84 行**+README+断点日志+校验报告） | ALL PASS；抽检 10/10；成本 ≈$0.023 | 04734ed |
| **Z5** L0 题库 | `notes/l0_bank/`：network/os/mysql/redis/python_50.md（**250 题**，四段式含来源） | 计网随 Z4 入库；其余 06e8f85；**未单独出报告（台账补记，见附 A）** | 04734ed/06e8f85 |
| **Z6** 面试考点笔记×3 | `notes/interview_prep/C1/C3/C4*.md` | 行号级代码证据；0.674 口径；400 bug 复盘按「评测设计教训」定位 | b195923 |
| **Z7** 投递清单 | `job_hunt/targets_2026.csv`（32 家，首批 5） | AI 轨 65.6%/后端 34.4%；URL 实测+官方信源；中兴 2027 届 8/31 已启动 | 612b23c |
| **Z8** 一键自检脚本 | `tools/run_all_tests.py`、`tools/g1_gate_check.py` | 门禁口径+E2E 显式隔离；G1 十项自动判定 | 62eb140 |

### 1.2 续班迭代 R1–R18（应孟轩「迭代勿闲置」+「拓展创新」指令）

| 轮 | 任务 | 产出文件 | 验证结果 | commit |
|---|---|---|---|---|
| R1 | **Z12** 代码修复 | `app/agent_loop.py`（off-by-one）、`app/tools.py`（司龄口径）、`tests/test_c2_loop_breaker.py`（+边界） | 修复后全测试 PASS | a79dda7 |
| R2 | **Z9** 简历双轨 v0.9 | `job_hunt/resumes/draft_ai_track.md`、`draft_backend_track.md`（DRAFT，占位不编造） | 五作品顺序+口径对齐 | 2e2967e |
| R3 | **Z10** 口径审计 | `tools/audit_metrics.py`、`notes/zcode_reports/audit_metrics_20260907.md`（+_audit_raw） | 全库 0 真实违规；2 处历史文档建议项 | 0c8dfd9 |
| R4 | **D2 配套**实测脚本 | `notes/os/gil_demo.py`、`notes/os/echo_server.py`；实测数字回填题库 | CPU 4 线程 2.39s vs 4 进程 0.96s；I/O 3.99x；echo 100 消息回显 | 242f025 |
| R5 | **Z11** 行业情报 | `notes/industry_watch_20260907.md` | 每条带来源；薪资类标未核实 | f533c97 |
| R6 | fallback 接线（B3 闭环） | `app/main.py`（try/except→fallback_answer）、`tests/test_v17_fallback.py` | LLM 全灭 SSE 不断流、降级入记忆；6 断言 | 0a9dc82 |
| R7 | 投递清单 v1.1 | `tools/check_targets.py`、`job_hunt/targets_2026.csv`（32 条全量核验） | 25 直达/7 人工修正——**信锐官方域 sundray.com.cn（原表有误已改）**、字节 /campus、海康 campushr、同花顺 10jqka、米哈游迁 jobs.mihoyo.com 等 | 59cd183 |
| R8 | **C4 正式交付** | `notes/interview_qa/01…21` + `reverse_questions.md`（22 文件，五段式） | 21 题全覆盖（冲刺版 §5 题面） | f664f6f |
| R9 | 简历追问压力测试 | `notes/interview_prep/w6_grill.md`（10 项×三层追问） | — | e370541 |
| R10 | 记忆卡生成器 | `tools/make_cards.py`、`notes/l0_bank/cards/*_cards.csv` ×5 | **250/250 卡**零跳过 | 647a729 |
| R11 | 四模式可运行示例（C3 顺延项） | `notes/interview_prep/modes_demo/mode_1…4.py` | 4/4 断言 PASS | 3b0f887 |
| R12 | 五段式 bug 故事集 | `notes/interview_prep/bug_stories.md`（5 个真实故事） | 全部有代码/commit 佐证 | 785c4cd |
| R13 | 面试准备总控 | `notes/interview_prep/README.md`（文件地图+节奏） | — | b736a21 |
| R14 | 记忆库 WAL 升级 | `app/main.py`（_connect/WAL/busy_timeout）、`tests/test_v17_memory_wal.py` | journal_mode=wal；并发写 100 次零异常 | 9fb5bce |
| R15 | 全量自检总演练 | `notes/zcode_reports/full_selfcheck_20260907.md` | **16/16 PASS** | 2151c59 |
| R16 | 面试自测 CLI | `tools/mock_interview.py`（--list/--n，先答后看） | 21/21 加载 | 2151c59/e523c61 |
| R17 | **D1–D5 追问链**×5 | `notes/network|os|mysql|cache|python/追问链.md` + `cache/cache_problems_demo.py` + `python/classic_pitfalls.py`（照搬 P0 清单原文） | cache 穿透实测 100→1；5 坑断言全过 | e523c61 |
| R18 | 内容自审 | interview_qa 13 文件补「题面」小节 | 21/21 格式统一 | 7d71b42 |

---

## 二、生产代码变更清单（**迪莫审查重点**——均为 zcode 属主文件）

| 文件 | 变更 | 审查要点 |
|---|---|---|
| `app/main.py` | 鉴权限流接线；fallback 降级（R6）；WAL+_connect（R14） | 降级分支是否可接受「降级文本也入记忆」；WAL 对部署的影响（-wal/-shm 文件） |
| `app/auth.py`、`app/rate_limit.py` | 新增：fail-closed 鉴权、滑动窗口限流 | 429/401 语义；多实例需迁 Redis 的边界 |
| `app/llm.py` | call_with_retry 接线；client 挂实例；`resilience_trace` 属性 | retry 口径（429 可重试=裁决③） |
| `app/agent_loop.py` | off-by-one（step>max_steps）；循环耗尽补 break 记录 | 耗尽答复文案变更（「已中断：max_steps…」） |
| `app/tools.py` | calc_annual_leave 司龄口径显式化 | 返回文本扩展是否影响下游断言（test_b2_dispatch 已过） |
| `tests/` | 新增 4（auth/fallback/wal/b3_resilience）、修改 3（c2 边界/e2e/memory 的 Key 头） | test_b2_tool_selection 归入 E2E 的分类修正 |

---

## 三、工具与文档资产索引（全部已入库）

**工具 8 个（tools/）**：gen_eval_candidates / verify_candidates / run_all_tests / g1_gate_check / make_cards / check_targets / audit_metrics / mock_interview
**面试弹药（notes/interview_prep/ + interview_qa/）**：C1/C3/C4 深挖 ×3、21 题逐题展开 + 反问、w6_grill 压力测试、bug_stories ×5、modes_demo ×4、总控 README
**题库与追问链（notes/）**：l0_bank 五科 250 题 + 250 记忆卡；network/os/mysql/cache/python 追问链 ×5；gil_demo/echo_server/cache_problems_demo/classic_pitfalls 可演示脚本 ×4
**求职物料（job_hunt/）**：targets_2026.csv v1.1（32 家）、draft_ai_track/draft_backend_track（DRAFT v0.9）
**数据（notes/eval_expansion/）**：candidates_80.csv（84 行候选池，**待迪莫复核转正**）
**情报（notes/industry_watch_20260907.md）**：校招启动表 + 6 家 JD 实证

---

## 四、G1 Gate 与 metrics_log 状态

- **9/6 深夜人工判定 8绿2红** = {#1 venv 3.13.4, #7 台账 0 行}；**今晨脚本判定 8绿2红** = {#4 .env 六变量（§A2 字面判据）, #7 台账 0 行}——构成变化因果：#1 转绿=Z1 成果；#4 转红=脚本揪出判据过时（GLM_MODEL 预期缺失等 §11；FALLBACK_PROVIDER 已被 B3 降级设计取代），已核实 .env 实际 6 键，**非脚本 bug**。
- **唯一硬红仍是 #7 投递台账 0 行（只能孟轩执行）**。
- metrics_log 已同步：venv 更新（Z1）、成本更新（Z2/Z4）——迪莫属主数字未改动，仅追加 zcode 标记行。

## 五、待裁决事项（4 项，均不阻塞运行）

1. **#1 venv 判据**：建议改「由受管解释器创建（≥3.13.12）」——二进制自报 3.13.14，字面「3.13.12」永不可达（脚本默认按建议，`--strict-venv` 保留字面）；
2. **#4 §A2 判据修订**：建议改「LLM_PROVIDER/DEEPSEEK_MODEL/DEEPSEEK_BASE_URL/API_TIMEOUT/MAX_STEPS（GLM_MODEL 待 §11 后补）」——采纳后 G1 即 9绿1红；
3. **429 重试口径**（Z3）：按 §11 实现为可重试；若裁定 429 不重试，改 `is_retryable` 一行；
4. **test_b2_tool_selection 分类**：走 10 次真实 API，已移入 E2E 集（原 Z8 误归离线门禁）——请确认此口径。

## 六、API 成本台账（估算，以账单为准）

| 项 | 用量 | 估算 |
|---|---|---|
| Z2 联调测试（计划外但必要） | 约 15 次调用 | ≈$0.02 |
| Z4 候选池生成 | in=30963 / out=13086 tokens | ≈$0.023 |
| **合计** | — | **≈$0.04**（全局预算 $0.05 内） |

## 七、给孟轩的下一步（按优先级）

1. **简历占位补齐 → 定稿 → 首批 5 家投递 → 当天记台账**（`draft_ai_track.md` 头注释列了步骤；中兴 8/31 已启动排第一）——修复 G1 唯一硬红；
2. **GLM Key 开通**（CONTEXT §11，10 分钟）→ zcode 接线 B3 真模型实测；
3. 顺手：targets CSV 标「浏览器确认」的入口打开即知；GitHub 公开作品集仓库决策。

## 八、给迪莫的复核清单（建议顺序）

1. **裁决 4 项**（第五节）——采纳任一项只需改一行判据/代码；
2. **生产代码审查**（第二节表）——重点：fallback 降级入记忆、WAL、off-by-one 三处行为变更；
3. **Z4 候选池复核转正**（`notes/eval_expansion/README.md` §6 流程；84 行素材池未经复核不入正式评测集）；
4. **简历双轨数字复核**（w6_grill.md 即追问对照表）；
5. **interview_qa 21 题**与冲刺版 §5 题面一致性抽查；
6. CONTEXT.md 我未触碰（你工作区有未提交改动）——本文件 + 附 A 报告即为状态刷新依据。

## 九、遗留问题与风险

- E2E 三测试默认不进门禁（需服务+API）：下次联调 `run_all_tests.py --e2e`（先 `set W6_API_KEY=<key>` 起服务）；
- memory.db 相对路径：部署必须以项目根为 WorkingDirectory（P2 建议锚定包目录）；
- 限流器单进程内存版：多 worker 迁 Redis（redis_50 题 40 有方案）；
- gil_demo 数字随机器变化（脚本自带判据，换机复跑）；
- W6 v1.7 公网部署（B4）待服务器采购；OTel/安全/成本工程已按 v1.8 移出 P0（P1/P2 执行）。

## 十、commit 全列表（28 个，`7bb7c63..fbf5b61`，均已推送）

```
fbf5b61 晨报v2: 追加续班战报R6-R18
7d71b42 R18: interview_qa 13文件补齐题面小节
e523c61 R16/R17: mock_interview自测CLI + D1-D5追问链笔记 + cache/python可演示脚本
2151c59 R15/R16: 全量自检16项PASS报告 + mock_interview(初版)
9fb5bce R14: 记忆库WAL模式+busy_timeout
b736a21 R13: 面试准备总控README+迭代留痕R6-R13
785c4cd R12: 五段式bug故事集x5
3b0f887 R11: 四工作模式最小可运行示例x4
647a729 R10: 记忆卡生成器make_cards
e370541 R9: 简历追问压力测试集w6_grill
f664f6f R8/C4正式交付: interview_qa 21题+反问环节
59cd183 R7: 投递清单v1.1(32条URL全量核验)
0a9dc82 R6: fallback_answer接线SSE链路
3381a34 晨报v1: Z1-Z8全完成+5轮迭代
f533c97 Z11: 9月AI应用岗情报速报
242f025 D2配套: gil_demo+echo_server实测脚本
0c8dfd9 Z10: 全库口径一致性审计
2e2967e Z9: 简历双轨v0.9草稿
a79dda7 Z12: off-by-one修复+年假司龄口径显式化
62eb140 Z8: 一键离线测试门禁+G1 Gate十项自动检查
612b23c Z7: 32家目标公司投递清单
b195923 Z6: C类面试考点笔记x3
06e8f85 Z5: L0题库五科各50题
04734ed Z4: 80条评测候选池流水线
2e39781 Z3: B3可靠性三件套骨架
47734c8 Z2: API Key鉴权+每IP滑动窗口限流
811a831 Z1: 反馈报告(venv版本偏差如实记录)
186424a Z1: venv重建至受管解释器+requirements.lock
```

## 附 A · 反馈报告索引（notes/zcode_reports/）

| 报告 | 覆盖 |
|---|---|
| Z1/Z2/Z3/Z4/Z6/Z7/Z8/Z9/Z11/Z12_20260907.md | 对应任务详情（产出物/执行记录/坑/自评） |
| D2_scripts_20260907.md | D2 配套脚本实测 |
| iteration_log_20260907.md | R6–R18 每轮「目标→动作→结论」（R14–R18 由本台账补记） |
| audit_metrics_20260907.md（+_audit_raw） | Z10 口径审计 |
| full_selfcheck_20260907.md | R15 全量自检 16/16 |
| night_shift_summary_20260907.md | **本文件**（唯一交接入口） |
| 注：Z5 无独立报告——文件即产出，本台账 §1.1 补记其产出物与验证 |

---

**交接完成** ｜ zcode ｜ 2026-09-07 02:00 ｜ 下一班建议入口：先读本文件 §0/§五/§八，再按需下钻附 A 报告。
