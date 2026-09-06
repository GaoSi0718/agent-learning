# 12 · 多 Agent 通信链路与异常处理 + 不要过早引入 Multi-Agent

> 来源：冲刺版 §5.1 第二梯队-12｜ 配套：C4_working_modes.md 模式 4

## 30 秒答
通信=显式结构化消息（交接单：任务、上下文、预算、验收），不用隐式共享记忆；异常=每个子 Agent 的失败**收敛为数据**回传调度者（status/error/latency），失败不炸整批。第三句话最重要：**不要过早引入 Multi-Agent**——我们单 Agent+3 工具就够时，不为了简历好看上多智能体。

## 2 分钟深答
- **架构预留（如实说没做）**：W6 是单 Agent。但 dispatch.run_calls 的设计天然可扩展：工具调用被收敛为 `{"name","status","result","latency_ms"}` 数据对象（dispatch.py:37-46）——把 one() 里的 `IMPL[name](**args)` 换成子 Agent 的 run_agent，就是 supervisor/worker 的雏形。**架构上留了门，工程上没过度建设**；
- **通信链路要点**：①上下文交接显式化（子 Agent 拿到的是任务描述+必要事实，不是父 Agent 全部历史——省 token 且防上下文污染）；②预算归属明确（子 Agent 死循环烧的是谁的配额——每个子 Agent 继承父的终止三件套，步数/超时单独计）；③错误语义统一（失败是数据不是异常，父 Agent 决定重试/换路/降级）；
- **异常处理铁律**：单子 Agent 失败 ≠ 整体失败——return_exceptions 语义（dispatch.py:48）在多 Agent 场景同样适用；
- **「不要过早」的论据**：多 Agent 引入的调试面/成本面/评测面都指数级变难（哪个 Agent 贡献了答案？失败归因给谁？）——先用单 Agent+好工具把评测做扎实，是负责任的路径。

## 追问预案
- 「什么信号出现时你会真的拆多 Agent？」→ 单 Agent 的工具数膨胀导致 system prompt 过载、或需要互斥的专业人格（如「检索员」与「审计员」互相校验）时。
- 「A2A 和 MCP 的区别？」→ MCP 管「Agent↔工具」，A2A 管「Agent↔Agent」互操作——层级不同，可能并存。

## 素材
dispatch.py、C4_working_modes.md 模式 4、冲刺版 §5.1-12
