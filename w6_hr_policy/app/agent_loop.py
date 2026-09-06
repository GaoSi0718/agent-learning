# w6_hr_policy/app/agent_loop.py
"""Agent Loop（终止三件套 + v1.6 多工具接线）。
v1.6 变更：工具执行统一走 dispatch.run_calls（并发 + 白名单/Schema 双重校验 + 失败回传），
替换 W1 的「直接调工具」两行；tools 参数仅用于向 LLM 提供 schema（{name: fn} 映射形态）。
终止三件套语义不变：先过检查再执行——注定中断的批次不浪费执行。"""
import json, time, hashlib
from collections import deque
from .config import MAX_STEPS, API_TIMEOUT
from .dispatch import run_calls

class LoopBreaker:
    """终止条件三件套"""
    def __init__(self, max_steps=MAX_STEPS, repeat_limit=3,
                 step_timeout=API_TIMEOUT, total_timeout=120):
        self.max_steps = max_steps
        self.repeat_limit = repeat_limit
        self.step_timeout = step_timeout
        self.total_timeout = total_timeout
        self.history = deque(maxlen=repeat_limit)
        self.start = time.time()

    def _sig(self, tool_name, args):
        """动作指纹：工具名 + 规范化后的参数"""
        return hashlib.md5(
            f"{tool_name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}".encode()
        ).hexdigest()

    def check(self, step, tool_name=None, args=None):
        """返回 (should_break, reason)。reason 会被写进日志——这是可复盘的关键。"""
        if step >= self.max_steps:
            return True, f"max_steps({self.max_steps}) reached"
        if time.time() - self.start > self.total_timeout:
            return True, f"total_timeout({self.total_timeout}s) exceeded"
        if tool_name is not None:
            sig = self._sig(tool_name, args or {})
            self.history.append(sig)
            if len(self.history) == self.repeat_limit and len(set(self.history)) == 1:
                return True, f"repeated_action({tool_name}) x{self.repeat_limit}"
        return False, ""

async def run_agent(user_query, llm, tools, breaker=None, history=None):
    """history：调用方从记忆库 load 出的消息列表（W1 main.py 接入）；
    多轮上下文由调用方传入，Agent 内部不直接碰 DB。"""
    breaker = breaker or LoopBreaker()
    messages = [{"role": "system", "content": "你是 HR 政策问答助手：依据检索到的政策条款回答，结论需带出处；检索不到就如实说，不要编造。"},
                *(history or []),
                {"role": "user", "content": user_query}]
    trace = []                       # ← 完整轨迹，P1 评测与 P2 归因都靠它
    for step in range(1, breaker.max_steps + 1):
        resp = llm.chat(messages, tools=tools, timeout=breaker.step_timeout)
        if not resp.tool_calls:
            trace.append({"step": step, "type": "final", "content": resp.content})
            return resp.content, trace

        # 先过终止三件套再执行：同一批次内第 3 次重复动作直接中断，不浪费执行
        doomed = None
        for call in resp.tool_calls:
            name = call["name"] if isinstance(call, dict) else call.name
            args = call["args"] if isinstance(call, dict) else call.args
            brk, reason = breaker.check(step, name, args)
            if brk:
                doomed = reason
                break
        if doomed:
            trace.append({"step": step, "type": "break", "reason": doomed})
            # ⚠️ 中断也要给用户一个交代，不能静默失败
            return f"（已中断：{doomed}）根据已有信息：{resp.content or '暂无结论'}", trace

        # OpenAI 协议：回传 tool 结果前，必须先把「发起调用的 assistant 消息」入栈，
        # 且每条 tool 消息带 tool_call_id——否则 DeepSeek 400。这是清单源码的潜在 bug
        # （W1 自测走 FakeLLM 不发真实请求，从未暴露），2026-09-06 由 B2 端到端实测发现并修复。
        raw = getattr(resp, "raw", None)
        if raw is not None:
            messages.append(raw)
        else:
            messages.append({"role": "assistant", "content": resp.content,
                             "tool_calls": [{"id": getattr(c, "id", None), "type": "function",
                                             "function": {"name": c.name,
                                                          "arguments": json.dumps(c.args, ensure_ascii=False)}}
                                            for c in resp.tool_calls]})

        results = await run_calls(resp.tool_calls)
        for call, r in zip(resp.tool_calls, results):
            if isinstance(r, BaseException):   # gather 兜底（one() 已就地收敛，正常不会走到）
                r = {"name": "?", "status": "error", "result": str(r), "latency_ms": 0}
            name = call["name"] if isinstance(call, dict) else call.name
            args = call["args"] if isinstance(call, dict) else call.args
            trace.append({"step": step, "tool": name, "args": args,
                          "status": r["status"], "latency_ms": r.get("latency_ms", 0)})
            # 关键：把结果/错误回传给 LLM，让它自己决定换工具还是改参数
            cid = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
            msg = {"role": "tool", "name": name, "content": str(r["result"])}
            if cid:
                msg["tool_call_id"] = cid
            messages.append(msg)
    return "（达到最大步数，未得出最终结论）", trace
