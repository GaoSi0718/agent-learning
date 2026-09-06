# 面试准备 · 总控索引（interview_prep/）

> **维护**：zcode ｜ **更新**：2026-09-07 ｜ **上游口径**：docs/metrics_log.md（D12）
> **本目录是面试弹药的唯一总控入口**——所有材料围绕「W6 主项目」组织，其他作品（W4/W3/W5/W7）素材见 `job_hunt/resumes/w6_evidence.md` 与 `draft_*_track.md`。

## 文件地图

| 文件/目录 | 内容 | 什么时候用 |
|---|---|---|
| `interview_qa/01…21`（21 文件） | 冲刺版 §5 全部 21 题逐题展开：题面→30 秒答→2 分钟深答→追问预案→素材 | W2 起每日 2-3 题过一轮；面试前只看 30 秒答 |
| `interview_qa/reverse_questions.md` | 反问环节问题库（技术/HR 两套） | 每场面试挑 2 个 |
| `C1_function_calling_deep_dive.md` | FC 深挖：schema 三原则/三层校验/400 bug 复盘 | Function Calling 相关追问的主弹药 |
| `C3_termination_talk.md` | 终止三件套 30s/2min/5min 三档话术 | 「防死循环」必考题 |
| `C4_working_modes.md` | 四工作模式理论 + 21 题对接索引 | 模式类考题（Agent vs Workflow 等） |
| `modes_demo/mode_1…4.py` | 四模式**可运行**最小示例（自包含零 API，带性质断言） | 现场演示/自己跑一遍加深理解 |
| `bug_stories.md` | 五段式 bug 故事 ×5（全部真实、有代码佐证） | 「讲一个你解决的 bug」类问题 |
| `w6_grill.md` | 简历数字三层追问压力测试（10 项） | 简历定稿前自测 + 面试前夜过一遍 |

## 使用节奏（建议，交孟轩/迪莫裁剪）

- **每日**：Anki 刷卡 20 张（`notes/l0_bank/cards/*_cards.csv`，由 `tools/make_cards.py` 生成）+ interview_qa 过 2 题（只背 30 秒版）；
- **每周**：挑 1 题「2 分钟深答」对着镜子/录音讲一遍；用 `tools/audit_metrics.py` 复扫口径一次；
- **面试前夜**：w6_grill 全表过一遍 + 目标公司 JD 对照 16 题（路由限流）/04 题（RAG）找结合点；
- **面试后**：24h 内把「答不上的追问」补回对应文件的「追问预案」小节——弹药库只增不减。

## 素材链条（一图流）

```
简历数字 ──追问──▶ w6_grill.md ──答法──▶ interview_qa 21 题 ──深挖──▶ C1/C3/C4 ──证据──▶ 代码行号
                                                    ▲                        │
                              l0_bank 250 题/250 卡 ─┘                  bug_stories.md（五段式）
```

## 红线提醒

1. 所有数字五问（测试集/公式/样本量/显著性/复算），答不出就删数字（D12）；
2. 「准确率」一词禁用；规模如实（D9）；CVE 编号引用前再核实；
3. 讲故事必打开代码佐证——「代码在手，故事落地」。
