# 13 · Structured Output 如何控制模型输出

> 来源：冲刺版 §5.1 第三梯队-13

## 题面
Structured Output 如何控制模型输出。

## 30 秒答
四层控制，逐层收紧：①Prompt 约束（格式指令+few-shot）——最弱；②Schema 声明（OpenAI function calling 的 parameters / JSON Schema，枚举+required）——约束输出分布；③解析校验——jsonschema 程序化验证，失败回传让模型自改；④约束解码——服务端按 grammar 生成（部分 API 支持），最强但依赖平台。W6 用②+③组合。

## 2 分钟深答（行号证据）
- **Schema 层**：tools.py 的 TOOLS——enum 枚举（category 六选一）、required 必填、description 写明格式期望（「检索关键词，尽量简短（2-6 个字）」）；
- **校验层**：dispatch.py validate_call 用 jsonschema.validate——类型/枚举/必填全查；失败拼人类可读的错误消息回传（「参数校验失败：'火星' is not one of [...]」），模型看到具体违规点才能自改；
- **解析韧性**：模型可能把 JSON 包在 markdown 代码块里——Z4 流水线的 parse_json 先剥 ```json 围栏再正则取 {…}/[…]，两种形态都兜住（这是 84 条候选生成中真实处理过的问题）；
- **失败策略**：校验失败不无限重试——「最多重试一次」纪律在调用方（dispatch docstring），重试无意义时（4xx 类协议错）直接失败降级。

## 追问预案
- 「约束解码为什么不常用？」→ 需要平台侧 grammar 支持（llama.cpp/vLLM 有，托管 API 未必开）；且过度约束会让模型「填不出合法值时硬凑」——合法但错误，比格式错更难发现。
- 「嵌套 JSON 校验失败怎么定位？」→ jsonschema 的 error message 自带 JSON path 与违规字段——工具化输出错误是可解析的。

## 素材
tools.py TOOLS、dispatch.py:15-24、tools/gen_eval_candidates.py parse_json
