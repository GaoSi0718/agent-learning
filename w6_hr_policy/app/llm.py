# w6_hr_policy/app/llm.py
"""LLM 适配层：统一返回属性风格响应对象（.content + .tool_calls，元素含 .name/.args）。
DeepSeek 兼容 OpenAI 协议；模型名/base_url/超时全部走 .env（第零步 0.3），代码不硬编码
（v1.5 修订：base_url 由硬编码改为 DEEPSEEK_BASE_URL 环境变量，缺省回退官方地址——
本机 .env 只读待孟轩补行，回退默认值保证服务可用）。
P0 教学规模下 chat 内同步调用可接受；全链路 async 化属 P2 范畴。"""
import json, os
from openai import OpenAI
from .config import API_TIMEOUT

def make_llm():
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                    timeout=API_TIMEOUT)

    class _Resp:
        def __init__(self, content, tool_calls, raw=None):
            self.content = content
            self.tool_calls = tool_calls
            self.raw = raw   # OpenAI 原始 assistant 消息（含 tool_calls）：
                             # 回传 tool 结果前必须先把它入栈，否则协议 400

    class _LLM:
        def chat(self, messages, tools=None, timeout=None):
            # 兼容两种传入：可执行工具映射（{name: fn}，schema 取 tools.py 的 TOOLS）
            # 或 OpenAI schema 列表（直接使用）
            if tools and isinstance(tools, dict):
                from .tools import TOOLS
                schemas = TOOLS
            else:
                schemas = tools or None
            r = client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=messages, tools=schemas)
            m = r.choices[0].message
            tcs = [type("TC", (), {"id": t.id,
                                   "name": t.function.name,
                                   "args": json.loads(t.function.arguments or "{}")})()
                   for t in (m.tool_calls or [])]
            return _Resp(m.content, tcs, raw=m)

    return _LLM()
