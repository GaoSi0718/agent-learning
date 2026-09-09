# 01 · LLM 和 Agent 的区别

> 来源：冲刺版 §5.1 第一梯队-1（字节剪映 Agent 岗真实面经）｜ 数字口径：metrics_log（score2=0.674）

## 题面
四模块（LLM 大脑/规划/记忆/工具）+ Think-Act-Observe 循环。

## 30 秒答
LLM 是「一次输入→一次输出」的文本映射，没有状态也不会行动；Agent = LLM 大脑 + 规划 + 记忆 + 工具四个模块，在 Think-Act-Observe 循环里**根据行动结果决定下一步**。一句话：LLM 只能「说」，Agent 能「做完一件事」。

## 2 分钟深答（用 W6 落地证据）
- **LLM 大脑**：W6 的 deepseek-chat 负责「决定调什么工具 + 何时收敛」（agent_loop.py 的 llm.chat 循环）；
- **规划**：不是前置 plan，而是 ReAct 式逐步规划——每轮拿到 tool 结果后重新决策（agent_loop.py:49-53：无 tool_calls 即收敛）；
- **记忆**：跨轮次靠 SQLite 会话记忆（main.py save/load，12 轮跨距实测：第 1 轮说工龄 12 年，第 12 轮能答对年假档位）+ 上下文压缩（context.py 超 70% 预算 compact）；
- **工具**：3 个工具（检索/计算/日历）经双重校验执行（dispatch.py）。
- **循环**：Think（LLM 输出意图）→ Act（代码执行工具，0.51s 并发）→ Observe（结果回传 messages）。
- **关键边界**：Agent 的「自主」只在策略层——执行权、终止权在代码手里（终止三件套 + 白名单），这是可控性的来源。

## 追问预案
- 「Agent 一定比直接调 LLM 好吗？」→ 不是。单轮可完成的任务（翻译/摘要）直接调 LLM 更便宜可控；需要多源信息或行动的任务才值得引入循环（W6 的年假问题需要检索+计算+核对三步）。
- 「四模块里哪个最难做？」→ 记忆——因为要同时管「相关性与预算」；我们踩过的坑：load limit=20 行会让 12 轮跨距测试必然丢首轮（B1 修订记录）。

## 素材
notes/interview_prep/C1_function_calling_deep_dive.md §0、C4_working_modes.md 模式 2、w6_hr_policy/app/agent_loop.py
