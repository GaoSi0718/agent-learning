# w6_hr_policy/app/dispatch.py
"""双重校验 + 并发执行（v1.6）。
校验两道：① 白名单 + 高危禁用（独立于 LLM 存在——LLM 只决定调什么，执行权在代码手里）
② JSON Schema 结构校验。校验失败不擅自重试：错误信息回传 LLM，「最多重试一次」的
纪律由调用方执行；单调用异常就地收敛为 status=error（等价 gather 的异常隔离）。"""
import asyncio
from jsonschema import validate, ValidationError
from .tools import TOOLS, IMPL

SCHEMA_MAP = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}

# 业务校验：白名单 + 危险操作拦截（P2 会升级为"确定性校验门"）
BLOCKED = {"delete_policy", "modify_salary"}

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

async def run_calls(tool_calls):
    """并发执行互不依赖的调用；每条附 latency_ms（trace/P2 归因用）。"""
    loop = asyncio.get_event_loop()

    async def one(call):
        t0 = loop.time()
        # 兼容两种形态：dict（本文件自测用例）与属性对象（W1 llm.py 返回的 tool_calls）
        name = call["name"] if isinstance(call, dict) else call.name
        args = call["args"] if isinstance(call, dict) else call.args
        ok, err = validate_call(name, args)
        if not ok:
            return {"name": name, "status": "blocked", "result": err, "latency_ms": 0}
        try:
            result = await IMPL[name](**args)
            return {"name": name, "status": "ok", "result": result,
                    "latency_ms": int((loop.time() - t0) * 1000)}
        except Exception as e:
            # 错误回传，让 LLM 自己决定重试还是换工具
            return {"name": name, "status": "error",
                    "result": f"{type(e).__name__}: {e}",
                    "latency_ms": int((loop.time() - t0) * 1000)}

    return await asyncio.gather(*[one(c) for c in tool_calls], return_exceptions=True)
