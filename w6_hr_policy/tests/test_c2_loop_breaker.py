# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_c2_loop_breaker.py
"""C2 自测（v1.6 接线版）：工具执行已统一走 dispatch.run_calls，
故通过向 IMPL 注入必然失败的工具来构造死循环用例。
验收不变：死循环用例必须 ≤8 步停，trace 有 break reason，错误以 error 状态回传。"""
import sys, pathlib, asyncio, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import w6_hr_policy.app.tools as tools_mod

def boom(**kw):
    raise RuntimeError("上游 500")

tools_mod.IMPL["search_policy"] = boom   # 注入必然失败的工具（覆盖真实实现）

from w6_hr_policy.app.agent_loop import run_agent  # noqa: E402

class FakeLLM:
    """永远要求调用同一个必然失败的工具，用于验证终止三件套。
    注：args 必须符合 search_policy 的 Schema（query 字段）——v1.6 起执行前有
    白名单+Schema 双重校验，非法参数会被拦成 blocked（那也是终止，但走的是另一条路径）。"""
    def chat(self, messages, tools=None, timeout=None):
        call = type("T", (), {"name": "search_policy", "args": {"query": "年假"}})()
        return type("R", (), {"tool_calls": [call], "content": None})()

def main():
    ans, trace = asyncio.run(run_agent("年假怎么算", FakeLLM(), dict(tools_mod.IMPL)))
    print("答复:", ans)
    print("轨迹步数:", len(trace))
    print("最后一步:", json.dumps(trace[-1], ensure_ascii=False))

    errors = [t for t in trace if t.get("status") == "error"]
    breaks = [t for t in trace if t.get("type") == "break"]

    assert len(trace) <= 8, f"轨迹步数 {len(trace)} > 8，终止三件套失效"
    assert breaks and "repeated_action" in breaks[-1]["reason"], "缺少 repeated_action 中断原因"
    assert errors, "工具异常未以 error 状态记录（异常被吞）"
    assert "已中断" in ans, "中断原因未拼进答复（静默失败）"
    print("\n[PASS] C2 终止三件套（v1.6 接线）：死循环用例 %d 步停止，reason=%r，错误已回传记录" %
          (len(trace), breaks[-1]["reason"]))

def test_max_steps_boundary():
    """off-by-one 回归（Z12）：第 max_steps 步应可执行，step > max_steps 才中断。"""
    from w6_hr_policy.app.agent_loop import LoopBreaker
    b = LoopBreaker(max_steps=3)
    assert not b.check(1)[0], "第 1 步不应中断"
    assert not b.check(2)[0], "第 2 步不应中断"
    assert not b.check(3)[0], "第 max_steps(3) 步应允许执行（off-by-one 已修复）"
    brk, reason = b.check(4)
    assert brk and "max_steps" in reason, "超过 max_steps 后必须中断"
    print("[PASS] max_steps 边界：第 3 步可执行、第 4 步才中断（实际可执行步数 = MAX_STEPS）")

if __name__ == "__main__":
    main()
    test_max_steps_boundary()
