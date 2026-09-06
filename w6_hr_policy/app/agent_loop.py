# w6_hr_policy/app/agent_loop.py
import inspect, json, time, hashlib
from collections import deque
from .config import MAX_STEPS, API_TIMEOUT

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

        for call in resp.tool_calls:
            brk, reason = breaker.check(step, call.name, call.args)
            if brk:
                trace.append({"step": step, "type": "break", "reason": reason})
                # ⚠️ 中断也要给用户一个交代，不能静默失败
                return f"（已中断：{reason}）根据已有信息：{resp.content or '暂无结论'}", trace

            t0 = time.time()
            try:
                result = tools[call.name](**call.args)
                if inspect.iscoroutine(result):   # 兼容 W2 起的 async 工具（tools.py IMPL）
                    result = await result
                status = "ok"
            except Exception as e:
                # 关键：把错误回传给 LLM，让它自己决定换工具还是改参数
                result = f"工具执行失败：{type(e).__name__}: {e}"
                status = "error"
            trace.append({"step": step, "tool": call.name,
                          "args": call.args, "status": status,
                          "latency_ms": int((time.time() - t0) * 1000)})
            messages.append({"role": "tool", "name": call.name, "content": str(result)})
    return "（达到最大步数，未得出最终结论）", trace
