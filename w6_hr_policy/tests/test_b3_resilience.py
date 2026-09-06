# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b3_resilience.py
"""B3/Z3 验收（全离线，API 成本 $0）：
① FakeLLM 连续失败 2 次第 3 次成功 → 最终成功且 trace 记录 2 次重试；
② 持续失败 → 重试耗尽后抛出，降级答复非空且含检索 top3 条目出处；
③ 4xx 协议错误不重试（1 次即抛）；④ llm.py 接线后 chat 走 retry，_Resp 结构不变；
⑤ 429 限流判定为可重试（清单 §11 免费档场景）。
运行：venv\\Scripts\\python.exe w6_hr_policy\\tests\\test_b3_resilience.py"""
import asyncio, os, re, sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)   # 语料/数据路径按既有约定从项目根解析

from w6_hr_policy.app.resilience import (call_with_retry, fallback_answer,
                                         FALLBACK_NOTICE, is_retryable)

class FakeTimeout(Exception):
    """类名含 Timeout → is_retryable 鸭子类型判可重试"""

class FakeBadRequest(Exception):
    status_code = 400

class FakeRateLimit(Exception):
    status_code = 429

def test_retry_then_success():
    calls, trace = {"n": 0}, []
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeTimeout("fake timeout")
        return "OK"
    r = call_with_retry(flaky, max_attempts=3, backoff=(0, 0, 0), trace=trace)
    retries = [e for e in trace if not e["ok"]]
    assert r == "OK" and calls["n"] == 3 and len(retries) == 2, (r, calls, trace)
    assert all("FakeTimeout" in e["error"] for e in retries)
    print("[PASS] ① 失败 2 次第 3 次成功：最终成功，trace 记录 2 次重试")

def test_exhausted_then_fallback():
    trace = []
    def always_fail():
        raise FakeTimeout("fake timeout")
    try:
        call_with_retry(always_fail, max_attempts=3, backoff=(0, 0, 0), trace=trace)
        raise AssertionError("重试耗尽后应当抛出")
    except FakeTimeout:
        pass
    assert len([e for e in trace if not e["ok"]]) == 3
    # 降级：真实 BM25 检索（本地语料，零 API 成本）
    ans = asyncio.run(fallback_answer("年假", top_k=3))
    assert ans and FALLBACK_NOTICE in ans, ans[:120]
    sources = re.findall(r"\[([^\]]+)\] ", ans)
    assert len(sources) >= 3, f"出处条目不足 3：{ans[:200]}"
    print("[PASS] ② 持续失败→重试耗尽抛出→降级答复非空且含 top3 出处")

def test_4xx_no_retry():
    calls = {"n": 0}
    def bad():
        calls["n"] += 1
        raise FakeBadRequest("protocol error")
    try:
        call_with_retry(bad, max_attempts=3, backoff=(0, 0, 0))
        raise AssertionError("4xx 应当立即抛出")
    except FakeBadRequest:
        pass
    assert calls["n"] == 1, f"4xx 被重试了 {calls['n']} 次（应只调 1 次）"
    print("[PASS] ③ 4xx 协议错误 1 次即抛（重试无意义）")

def test_llm_wiring():
    from w6_hr_policy.app.llm import make_llm
    llm = make_llm()
    calls = {"n": 0}
    class FakeCompletions:
        def create(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise FakeTimeout("fake timeout")
            return NS(choices=[NS(message=NS(content="重试后成功", tool_calls=None))])
    llm._client = NS(chat=NS(completions=FakeCompletions()))
    resp = llm.chat([{"role": "user", "content": "hi"}])
    assert resp.content == "重试后成功" and resp.tool_calls == []
    assert calls["n"] == 3 and len([e for e in resp.resilience_trace if not e["ok"]]) == 2
    print("[PASS] ④ llm.py 接线：chat 经 retry 2 次重试后成功，_Resp 返回结构不变")

def test_429_retryable():
    assert is_retryable(FakeRateLimit()) is True
    assert is_retryable(FakeBadRequest()) is False
    print("[PASS] ⑤ 429 判可重试 / 400 判不可重试（口径与清单 §11 一致）")

if __name__ == "__main__":
    test_retry_then_success()
    test_exhausted_then_fallback()
    test_4xx_no_retry()
    test_llm_wiring()
    test_429_retryable()
    print("[PASS] B3 可靠性三件套（骨架）5 项断言全过（离线，API 成本 $0）")
