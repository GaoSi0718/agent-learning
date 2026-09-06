# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b2_e2e.py
"""B2 自测 3：端到端「我工龄 12 年，年假怎么算？」
① 进程内 run_agent：验证 trace 中真实发生 search_policy（+可能 calc_annual_leave）且 status=ok，
   最终答复为引用式（含条款/条例/手册出处字样 + 数字）；
② HTTP /chat/stream（需服务已启动）：验证用户可见链路同样得到带出处的答复。"""
import os, sys, pathlib, asyncio, json, urllib.request, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from w6_hr_policy.app.llm import make_llm
from w6_hr_policy.app.agent_loop import run_agent
from w6_hr_policy.app.tools import IMPL

# v1.7 鉴权适配（Z2）：服务按 fail-closed 校验 X-API-Key，联调请求必须带同一把 Key
BASE = os.getenv("W6_TEST_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("W6_API_KEY", "")

Q = "我工龄 12 年，年假怎么算？"
CITE_MARKS = ("条例", "手册", "章节", "第", "依据", "规定", "出处")

def is_cited(ans: str) -> bool:
    return any(m in ans for m in CITE_MARKS) and any(ch.isdigit() for ch in ans)

def in_process():
    ans, trace = asyncio.run(run_agent(Q, make_llm(), dict(IMPL)))
    print("--- 进程内 trace ---")
    for t in trace:
        print(json.dumps(t, ensure_ascii=False)[:180])
    print("--- 最终答复（前 200 字）---")
    print(ans[:200])
    tool_ok = [t for t in trace if t.get("status") == "ok" and t.get("tool")]
    assert tool_ok, "trace 中没有任何成功工具调用——Agent 未走检索链路"
    assert any(t["tool"] == "search_policy" for t in tool_ok), "未见 search_policy 调用"
    assert is_cited(ans), f"答复缺引用式要素（出处字样+数字）：{ans[:80]}"
    print("[PASS] 进程内端到端：工具链路生效且答复带出处")

def via_http():
    url = BASE + "/chat/stream?" + urllib.parse.urlencode(
        {"q": Q, "session_id": "b2e2e"})
    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8")
    deltas = [json.loads(l[6:])["delta"] for l in raw.splitlines()
              if l.startswith("data: ")]
    ans = "".join(deltas)
    print("--- HTTP 答复（前 200 字）---")
    print(ans[:200])
    assert len(ans) > 30, "HTTP 答复过短"
    assert is_cited(ans), f"HTTP 答复缺引用式要素：{ans[:80]}"
    print("[PASS] HTTP 端到端：/chat/stream 返回引用式回答")

if __name__ == "__main__":
    in_process()
    via_http()
    print("\n[PASS] B2 端到端验收全部通过")
