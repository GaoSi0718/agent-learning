# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_c2_loop_breaker.py
"""C2 自测：死循环用例必须 ≤8 步停，且 trace 有 break reason。"""
import sys, pathlib, asyncio, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from w6_hr_policy.app.agent_loop import run_agent, LoopBreaker

class FakeLLM:
    """永远要求调用同一个必然失败的工具，用于验证终止三件套"""
    def chat(self, messages, tools=None, timeout=None):
        call = type("T", (), {"name": "search_policy", "args": {"q": "年假"}})()
        return type("R", (), {"tool_calls": [call], "content": None})()

def boom(**kw):
    raise RuntimeError("上游 500")

def main():
    ans, trace = asyncio.run(run_agent("年假怎么算", FakeLLM(), {"search_policy": boom}))
    print("答复:", ans)
    print("轨迹步数:", len(trace))
    print("最后一步:", json.dumps(trace[-1], ensure_ascii=False))

    errors = [t for t in trace if t.get("status") == "error"]
    breaks = [t for t in trace if t.get("type") == "break"]

    assert len(trace) <= 8, f"轨迹步数 {len(trace)} > 8，终止三件套失效"
    assert breaks and "repeated_action" in breaks[-1]["reason"], "缺少 repeated_action 中断原因"
    assert errors, "工具异常未以 error 状态记录（异常被吞）"
    assert "已中断" in ans, "中断原因未拼进答复（静默失败）"
    print("\n[PASS] C2 终止三件套：死循环用例 %d 步停止，reason=%r，错误已回传记录" %
          (len(trace), breaks[-1]["reason"]))

if __name__ == "__main__":
    main()
