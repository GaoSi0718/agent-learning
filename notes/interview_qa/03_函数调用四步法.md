# 03 · Function Call 底层实现（四步）

> 来源：冲刺版 §5.1 第一梯队-3｜ 深挖版：C1_function_calling_deep_dive.md（必读，含 400 bug 故事）

## 题面
四步流程：定义工具 schema → LLM 输出结构化调用指令 → 程序执行 → 结果回传。关键认知：**LLM 自己不执行函数**。

## 30 秒答
①用 JSON Schema 定义工具（名称/参数/何时用）；②模型输出的是**结构化调用意图**（JSON 文本），不是执行结果；③程序解析意图、校验后真正调用函数；④把结果作为 tool 消息回传，模型基于结果继续。核心认知一句话：**LLM 自己不执行函数，执行权永远在代码手里**。

## 2 分钟深答（全部有行号证据）
- **schema 即 prompt**：description 写「何时用+何时不用」（tools.py:13 检索工具的负面边界）+ 参数枚举（tools.py:18 category 枚举）——模型输出质量由 schema 信息密度决定；
- **执行前双重校验**：白名单/高危拦截/JSON Schema 三层（dispatch.py:15-24）——存在性、权限、结构三个正交关注点；校验失败**不擅自重试**，错误回传让模型自己改；
- **回传协议**：assistant 原始消息先入栈 + 每条 tool 消息带 tool_call_id，否则 DeepSeek 400（agent_loop.py:69-80）——这是 FakeLLM 自测永远暴露不了、端到端才打穿的协议 bug，已固化为 test_b2_e2e.py；
- **并发执行**：asyncio.gather + return_exceptions=True（dispatch.py:48），一批工具互不拖累，3 个 0.5s 任务实测墙钟 0.51s。

## 追问预案
- 「校验失败为什么要回传而不是代码自动重试？」→ 自动重试=用代码猜测模型意图，错误参数重试大概率再错，白烧钱；回传后模型有完整上下文，能换参数甚至换工具——策略归模型，纪律归代码（「最多重试一次」在调用方控制）。
- 「怎么防止模型调危险工具？」→ 权限层独立于模型意图：BLOCKED 集合硬拦截（dispatch.py:13），模型「想调」也到不了执行层。

## 素材
C1 §0-§4、tools.py、dispatch.py、agent_loop.py
