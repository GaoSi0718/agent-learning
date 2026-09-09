# C1 · Function Calling 深挖（基于 W6 v1.6 真实代码）

> **用途**：面试深挖题的弹药库。每个考点 = 代码证据（文件+行号）+ 一层原理 + 追问预案。
> **数字口径**：与 `docs/metrics_log.md` 一致——最终基线 **score2=0.674**（0.6×bigram 召回+0.4×数字召回，31 题对齐集，k=6），**关键词口径 0.75**；对齐基线 0.6607 仅内部参照。**禁止说「准确率 67%」**（D12）。
> **生成**：zcode 2026-09-07（Z6 任务）。

---

## 0. 四步流程（必须脱口而出）

1. 定义工具 schema（JSON Schema）——`w6_hr_policy/app/tools.py:8-54` 的 `TOOLS` 列表；
2. LLM 输出**结构化调用指令**（JSON 文本，**不是执行**）——`llm.py` 把 `m.tool_calls` 包装为 `.name/.args` 对象；
3. 程序解析、双重校验后**真正执行**——`dispatch.py:26-48` `run_calls`；
4. 把结果作为 tool message 回传（必须带 `tool_call_id`）——`agent_loop.py:90-95`。

**关键认知（一句话层）**：
- 「LLM 自己不执行函数」——它只产出「想调什么」的结构化意图；
- 「工具 schema 是给 LLM 看的 prompt，不是给编译器的接口」——description 的信息密度决定调用质量；
- 「执行权永远在代码手里」——这是白名单与最小权限能落地的技术前提。

---

## 1. schema 设计三原则（对着自己的代码讲）

### 原则一：描述即契约（何时用 + 何时不用）

**代码证据** `tools.py:13`（search_policy 的 description）：

```python
"description": "检索公司 HR 政策文档。仅当问题涉及年假/报销/考勤/社保/公积金等制度时使用；闲聊或计算类问题不要用。",
```

正面写「何时用」、负面写「何时不用」，两半缺一不可。反例是清单点名的坑：「description 只写一句话 = 工具被乱调」——模型无法从一句话里推断边界，会把「137×8」也拿去检索。

**追问预案**：为什么不用 fine-tune 教模型选工具？→ 调用边界变化时 prompt 层改一行即可生效，fine-tune 要重训；且 selection 错误可以靠「失败回传」自愈，不必用权重承担。

### 原则二：参数最小化 + 枚举约束

**代码证据** `tools.py:17-21`：

```python
"query":   {"type": "string", "description": "检索关键词，尽量简短（2-6 个字）"},
"category": {"type": "string", "enum": ["年假", "报销", "考勤", "社保", "公积金", "其他"], ...},
...
"required": ["query"]
```

能枚举就枚举（enum 是结构化约束，LLM 的输出分布被直接截断到合法集合）；能可选就可选（category 不确定时填「其他」，description 里写明默认策略）。参数越少，幻觉面越小。

**追问预案**：枚举值将来要动态扩展怎么办？→ schema 由配置生成（代码里已是 `TOOLS` 列表驱动），扩展枚举=改配置不改执行逻辑。

### 原则三：单一职责

**代码证据** `tools.py:29`（calc_annual_leave 的 description）：

```python
"description": "根据入职日期计算司龄与国家法定年假档位。公司手册条款不在本工具职责内——回答公司口径前请先用 search_policy 检索'年假'核实。仅在需要具体数字时使用。",
```

三个工具各管一件事：检索（search_policy）、计算（calc_annual_leave）、日历（workday_lookup）。工具描述里显式写「不在本工具职责内」的负面边界，把「算数字 vs 查条款」两个职责切开——这正是后来发现「双源混淆」问题（公司口径 vs 国家口径）时，工具层已经预留了对策的原因。

---

## 2. 双重校验：为什么分层？（这是「安全架构」级别的答案）

**代码证据** `dispatch.py:15-24` `validate_call`：

```python
def validate_call(name, args):
    if name not in SCHEMA_MAP:
        return False, f"未知工具：{name}"          # ① 白名单
    if name in BLOCKED:
        return False, f"高危工具已禁用：{name}"     # ② 权限拦截
    try:
        validate(instance=args, schema=SCHEMA_MAP[name])
    except ValidationError as e:
        return False, f"参数校验失败：{e.message}"   # ③ 结构校验
    return True, ""
```

**为什么不能只靠一道？**

| 层 | 防什么 | 为什么另一层防不了 |
|---|---|---|
| ① 白名单（`name not in SCHEMA_MAP`，dispatch.py:16-17） | 模型幻觉出「不存在的工具名」 | schema 校验的前提是「工具存在」，这一层管的是存在性 |
| ② 高危拦截（`BLOCKED = {"delete_policy", "modify_salary"}`，dispatch.py:13,18-19） | 越权/破坏性操作 | 即便模型「正确地」调用了危险工具，也不该放行——这是**独立于 LLM 意图**的权限层 |
| ③ JSON Schema 结构校验（dispatch.py:20-23） | 参数类型/枚举/必填项错误 | 前两层不校验参数内容；错误参数会导致工具运行期崩溃或语义错乱 |

**三层的一句话总结**：①管「有没有这个工具」，②管「该不该执行」，③管「参数对不对」——存在性、权限、结构，正交的三个关注点，谁也替代不了谁。

**为什么不重试**（dispatch.py docstring 2-5 行）：校验失败**不擅自重试**——错误信息原样回传 LLM，由它决定改参数还是换工具；「最多重试一次」的纪律在调用方（agent_loop）。无限重试 = 烧钱死循环（清单点名的坑）。

**追问预案**：这套校验和「确定性校验门」（P2 升级项）什么关系？→ 现在 BLOCKED 是硬编码集合，P2 会把权限层配置化（角色×工具矩阵），但分层结构不变——好的分层让演进局部化。

---

## 3. 最佳面试故事：tool 回传协议 400 bug 的完整复盘

> 这是「评测设计」的最佳论据——**如实讲，不吹成「我预见了」**。

### 事故现象

B2 端到端实测（真实调用 DeepSeek）时，Agent 第一步 search_policy 成功，**第二步把工具结果回传后直接 HTTP 400**——进程内 FakeLLM 自测全绿，一上真实 API 就崩。

### 根因（OpenAI 协议要求）

**代码证据** `agent_loop.py:69-80`（修复代码+注释）：

```python
# OpenAI 协议：回传 tool 结果前，必须先把「发起调用的 assistant 消息」入栈，
# 且每条 tool 消息带 tool_call_id——否则 DeepSeek 400。这是清单源码的潜在 bug
# （W1 自测走 FakeLLM 不发真实请求，从未暴露），2026-09-06 由 B2 端到端实测发现并修复。
raw = getattr(resp, "raw", None)
if raw is not None:
    messages.append(raw)
```

两个协议要求缺一即 400：
1. **发起调用的 assistant 原始消息要先入栈**——tool 消息必须「挂」在它后面（`agent_loop.py:72-74`）；
2. **每条 tool 消息带 `tool_call_id`**——一批多个 tool_call 时靠 id 配对（`agent_loop.py:90-94`：`msg["tool_call_id"] = cid`）。

配套改动在 `llm.py:50`：`_Resp` 增加 `.raw` 字段（保留 OpenAI 原始 assistant 消息），而 schema/args 早已解析——**协议完整性和结构化解析是两件事，字段都要留**。

### 为什么自测没抓住（这是故事的价值核心）

- W1 阶段的自测走 **FakeLLM**：桩不校验 OpenAI 协议，直接返回编造的 tool_calls——**测试替身的保真度决定了它能暴露哪一类 bug**；
- FakeLLM 自测验证的是「Agent 逻辑」（循环/终止/分发），永远验证不了「协议合规性」；
- 端到端真实调用才把「逻辑对、协议错」的盲区打穿。

### 修复后的防线

① `.raw` 字段保留原始消息（llm.py）；② 回传顺序+id 配对（agent_loop.py）；③ 端到端测试固化成 `tests/test_b2_e2e.py`（进程内 + HTTP 两段，HTTP 段走真实服务）——**同一类 bug 不再依赖「人记得」来防**。

### 面试叙述模板（60 秒版）

> "我们有一类 bug 是单元自测永远抓不到的：W6 的 FakeLLM 桩不校验 OpenAI 协议，Agent 逻辑全绿，一上真实 DeepSeek 就 400——因为回传工具结果前必须先入栈发起调用的 assistant 原始消息、每条 tool 消息带 tool_call_id。这件事教会我两点：测试替身的保真度决定它能暴露哪类 bug；端到端测试不是可选项，它是协议层的唯一验收手段。修复固化后我们把它变成了 tests/test_b2_e2e.py 的常驻用例。"

---

## 4. 并发执行与失败回传（第三、四件套）

### 并发调度

**代码证据** `dispatch.py:26-48`：

- `asyncio.gather(*[one(c) for c in tool_calls], return_exceptions=True)`（dispatch.py:48）——`return_exceptions=True` 保证**异常不连坐**：一个工具崩不影响同批其他工具（清单点名的坑）；
- 每条调用就地收敛为 `{"status": "ok"/"error"/"blocked", "result": ..., "latency_ms": ...}`（dispatch.py:37,40-46）——错误变成**数据**而不是异常，让上层能统一处理；
- 实测：3 个 0.5s 工具并发墙钟 **0.51s**（串行约 1.5s）——`tests/test_b2_dispatch.py` 用例 3，数字来自离线测试可直接引用。

### 失败回传与 LLM 自主决策

**代码证据** `agent_loop.py:83-95`：

```python
results = await run_calls(resp.tool_calls)
for call, r in zip(resp.tool_calls, results):
    ...
    # 关键：把结果/错误回传给 LLM，让它自己决定换工具还是改参数
    msg = {"role": "tool", "name": name, "content": str(r["result"])}
```

错误回传 ≠ 重试控制权移交：**谁执行、谁改策略**的分工是——代码管校验与执行，LLM 管策略调整；代码只负责把「世界发生了什么」如实喂回去。

**追问预案**：trace 里记录了什么、给谁用？→ `agent_loop.py:88-89` 每步记录 `{step, tool, args, status, latency_ms}`——P1 评测归因、P2 可观测都吃这份 trace；Z3 之后每次 LLM 调用的重试轨迹也挂在 `_Resp.resilience_trace`（llm.py:50）。

---

## 5. 自测清单（面试前过一遍）

- [ ] 四步流程 30 秒讲完（不低头看稿）
- [ ] 三原则各配一个自己代码的行号
- [ ] 双重校验为什么三层：存在性/权限/结构 三个词
- [ ] 400 bug：现象→根因（两条协议要求）→为什么自测没抓到→怎么固化防线
- [ ] 并发数字：0.51s（3×0.5s 工具）；评估口径：score2=0.674（复合指标全称），不说「准确率」
