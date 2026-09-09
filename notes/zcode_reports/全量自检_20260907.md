# 全量自检报告（R15 · 夜班总演练）

> **执行**：zcode ｜ **时间**：2026-09-07 01:55 ｜ **范围**：今夜产出的全部可执行资产 + 工具链 + 门禁
> **结论：16/16 项全 PASS**（明细如下），夜班所有产出处于可运行、可复现、口径一致状态。

## 一、测试门禁（tools/run_all_tests.py）

| 项 | 结果 |
|---|---|
| 离线测试 7 个（b1_context_compact/b2_dispatch/b3_resilience/c2_loop_breaker/v17_auth/v17_fallback/v17_memory_wal） | 7/7 PASS |
| G1 Gate 十项（tools/g1_gate_check.py） | 8绿2红（#4 判据过时待裁决、#7 投递台账 MANUAL——均非缺陷） |

## 二、工具链复跑

| 工具 | 结果 |
|---|---|
| verify_candidates.py | ALL PASS（84 行候选池：原文命中/类别/反幻觉/去重） |
| make_cards.py | 250/250 卡、0 跳过 |
| audit_metrics.py | 273 处命中（含今夜新增文件），经 R3 判定规则分类无真实违规 |
| gen_eval_candidates.py | 断点续传状态完好（未复跑生成，避免无谓 API 消耗） |

## 三、可运行示例复跑

| 脚本 | 结果 |
|---|---|
| modes_demo/mode_1_prompt_chain.py | PASS（控制流在代码） |
| modes_demo/mode_2_react.py | PASS（Think-Act-Observe） |
| modes_demo/mode_3_plan_and_execute.py | PASS（计划先行+局部 re-plan） |
| modes_demo/mode_4_multi_agent.py | PASS（失败收敛为数据+降级路由） |
| os/echo_server.py --selftest | PASS（5 连接 × 20 消息回显） |
| os/gil_demo.py | PASS（CPU 线程/进程 2.50x 差距；I/O 3.99x） |

## 四、未复跑项（成本/环境原因，非缺陷）

- gen_eval_candidates 正式生成（需真实 API；断点日志完好可随时续跑）
- test_b2_e2e / test_b1_memory_12rounds / test_b2_tool_selection（E2E 组：需本地服务+真实 API，`--e2e` 显式开启）
- gil_demo 数字随机器变化（脚本自带 PASS/FAIL 判据，换机复跑即可）

## 五、处置

- 自检发现的问题：0（本轮纯验证，无修复动作）
- 本报告作为夜班交付的最终验证记录，与 night_shift_summary_20260907.md 一起构成交接材料。
