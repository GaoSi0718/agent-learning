# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_v17_fallback.py
"""R6 验收：LLM 链路全灭（重试耗尽后仍抛异常）时，/chat/stream 不断流、不 500，
而是降级输出 FALLBACK_NOTICE + 检索条款原文（[source] 格式），且降级答复入 SQLite 记忆。
全离线：FakeLLM 注入 + 本地 BM25 语料，API 成本 $0。
运行：venv\\Scripts\\python.exe w6_hr_policy\\tests\\test_v17_fallback.py（cwd 任意）"""
import os, sqlite3, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)                      # main.py 的 memory.db 是 cwd 相对路径
os.environ.setdefault("W6_API_KEY", "test-key-fb")
os.makedirs(ROOT / "w6_hr_policy" / "data", exist_ok=True)

from fastapi.testclient import TestClient
import w6_hr_policy.app.main as main_mod
from w6_hr_policy.app.rate_limit import limiter
from w6_hr_policy.app.resilience import FALLBACK_NOTICE

class DeadLLM:
    """chat 永远抛类名含 Timeout 的异常——llm.py 的重试耗尽后异常上抛，触发降级。"""
    class FakeTimeout(Exception):
        pass
    def chat(self, messages, tools=None, timeout=None):
        raise DeadLLM.FakeTimeout("上游持续超时（重试已耗尽）")

failures = []
def expect(name, cond, extra=""):
    print(("[PASS] " if cond else "[FAIL] ") + name + (f" | {extra}" if extra and not cond else ""))
    if not cond:
        failures.append(name)

SID = f"t-r6-fallback-{int(time.time())}"   # memory.db 持久化跨运行，用唯一会话保证幂等
with TestClient(main_mod.app) as client:
    limiter.reset()
    # 让 gen() 拿到 DeadLLM：make_llm 被替换，但 run_agent 走真实 dispatch（工具不会被用到——
    # LLM 第一步 chat 就抛，走不到工具调用）
    main_mod.make_llm = lambda: DeadLLM()

    r = client.get("/chat/stream", params={"q": "年假怎么算", "session_id": SID},
                   headers={"X-API-Key": "test-key-fb"})
    expect("① LLM 全灭时 /chat/stream 仍 200（不 5xx、不断流）", r.status_code == 200,
           f"got {r.status_code}")
    # 降级文本按 8 字符分片下发——先拼回 delta 再断言（与 e2e 测试同法）
    import json as _json
    deltas = [_json.loads(l[6:])["delta"] for l in r.text.splitlines()
              if l.startswith("data: ")]
    ans = "".join(deltas)
    expect("② 降级答复含固定说明", FALLBACK_NOTICE in ans, ans[:120])
    expect("③ 降级答复含检索条款出处（[章节/第X条/无章节号] 格式）",
           ("[章节" in ans) or ("[第" in ans) or ("[无章节号]" in ans))

    con = sqlite3.connect(str(ROOT / "w6_hr_policy" / "data" / "memory.db"))
    n = con.execute("SELECT COUNT(*) FROM memory WHERE session_id=?", (SID,)).fetchone()[0]
    last = con.execute("SELECT content FROM memory WHERE session_id=? AND role='assistant' "
                       "ORDER BY ts DESC LIMIT 1", (SID,)).fetchone()
    con.close()
    expect("④ 降级答复已入记忆（user+assistant 共 2 行）", n == 2, f"rows={n}")
    expect("⑤ 记忆中的助手内容是降级文本（非异常字符串）",
           bool(last) and FALLBACK_NOTICE in last[0])

    # 正常链路不受影响：恢复桩后对 Key 请求仍走 Agent 路径（摘要输出含 delta）
    async def fake_run_agent(q, llm, tools, breaker=None, history=None):
        return "正常回答（桩）", []
    main_mod.run_agent = fake_run_agent
    limiter.reset()
    r2 = client.get("/chat/stream", params={"q": "年假", "session_id": "t-r6-normal"},
                    headers={"X-API-Key": "test-key-fb"})
    expect("⑥ 正常链路回归：Agent 路径仍 200 出流", r2.status_code == 200 and "delta" in r2.text,
           f"got {r2.status_code}")

if failures:
    raise SystemExit(f"R6 降级接线验收未通过：{failures}")
print("[PASS] R6 降级接线 6 项断言全过（离线，API 成本 $0）")
