# bugs_found · 2026-09-06（zcode 接管首夜）

| # | 级别 | 状态 | 对象 | 描述 |
|---|---|---|---|---|
| 1 | 🔴 | **已修复** | P0 清单 §W1 源码（agent_loop.py / llm.py） | **tool 结果回传协议缺陷**：llm.py 丢弃 `tool_call.id` 且 agent_loop 未把「发起调用的 assistant 消息」入栈、tool 消息缺 `tool_call_id` → 真实 DeepSeek API 必报 400 `missing field tool_call_id`。W1 自测全走 FakeLLM 不发真实请求，故从未暴露；2026-09-06 由 B2 端到端实测发现。修复：llm.py 透传 `id`+`raw`，agent_loop 先入栈 assistant 消息、tool 消息带 `tool_call_id`（按「影响任务继续才可修」纪律执行，已注释标注） |
| 2 | 🔴 | **已修复** | zcode 自有代码 tools.py | **calc_annual_leave 法定档位错误**：嵌套三元只覆盖 3 档，司龄 12 年被算成 15 天（应为 10 天）。由 B2 dispatch 自测拦截；修复为显式 4 档（<1 年 0 / 1–10 年 5 / 10–20 年 10 / ≥20 年 15）并补 4 组边界用例全对 |
| 3 | 🟡 | 设计勘误（未修） | P0 清单 §W2 D3–D4 源码 | 清单版 `_leave` 的「<1年:5天；1-10年:10天；≥10年:15天」是旧假设语料的档位口径，与国家法定（514 号令）四档不一致；zcode 版按国家法定实现，公司口径一律交由 search_policy 检索（避免硬编码「唯一真相」造成双源混淆） |
| 4 | 🟡 | 按设计生效（非 bug） | dispatch.py Schema 校验 | 清单 C2 自测的 FakeLLM 参数 `{"q": "年假"}` 不符合 search_policy Schema，v1.6 起会被拦成 `blocked`——这是校验按设计工作；C2 测试已改用合法参数 `{"query": …}` 走「执行失败→error 回传」路径 |

## 修复涉及文件
- w6_hr_policy/app/llm.py（TC 透传 id、_Resp.raw）
- w6_hr_policy/app/agent_loop.py（assistant 消息入栈 + tool_call_id）
- w6_hr_policy/app/tools.py（法定四档）
- w6_hr_policy/tests/test_b2_dispatch.py（四档边界用例）、test_c2_loop_breaker.py（合法参数）
