# w6_hr_policy/app/llm.py
"""LLM 适配层：统一返回属性风格响应对象（.content + .tool_calls，元素含 .name/.args）。
DeepSeek 兼容 OpenAI 协议；模型名/base_url/超时全部走 .env（第零步 0.3），代码不硬编码
（v1.5 修订：base_url 由硬编码改为 DEEPSEEK_BASE_URL 环境变量，缺省回退官方地址——
本机 .env 只读待孟轩补行，回退默认值保证服务可用）。
P0 教学规模下 chat 内同步调用可接受；全链路 async 化属 P2 范畴。"""
import json, os
from openai import OpenAI
from .config import API_TIMEOUT
from .resilience import call_with_retry

def make_llm():
    _client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                     base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                     timeout=API_TIMEOUT)

    class _Resp:
        def __init__(self, content, tool_calls, raw=None):
            self.content = content
            self.tool_calls = tool_calls
            self.raw = raw   # OpenAI 原始 assistant 消息（含 tool_calls）：
                             # 回传 tool 结果前必须先把它入栈，否则协议 400

    class _LLM:
        def __init__(self):
            # B3 接线（Z3）：client 挂到实例上，便于离线测试注入 FakeClient；
            # 每次调用 chat 时用 call_with_retry 包住底层请求——超时/连接错误/5xx/429
            # 指数退避重试，4xx 协议错误直接抛。_Resp 返回结构不变，agent_loop 零改动。
            self._client = _client

        def chat(self, messages, tools=None, timeout=None):
            # 兼容两种传入：可执行工具映射（{name: fn}，schema 取 tools.py 的 TOOLS）
            # 或 OpenAI schema 列表（直接使用）
            if tools and isinstance(tools, dict):
                from .tools import TOOLS
                schemas = TOOLS
            else:
                schemas = tools or None
            trace = []
            r = call_with_retry(
                self._client.chat.completions.create,
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=messages, tools=schemas, trace=trace)
            m = r.choices[0].message
            tcs = [type("TC", (), {"id": t.id,
                                   "name": t.function.name,
                                   "args": json.loads(t.function.arguments or "{}")})()
                   for t in (m.tool_calls or [])]
            resp = _Resp(m.content, tcs, raw=m)
            resp.resilience_trace = trace   # 每轮尝试记录（P2 归因接线点）
            return resp

    return _LLM()
