# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_v17_auth.py
"""Z2 验收测试（离线，API 成本 $0）：
① 无 Key → 401；② 错 Key → 401；③ 对 Key → 200（SSE 出流）；④ 同 IP 第 61 发 → 429。
全部走 FastAPI TestClient（不发起真实网络请求），LLM 用桩替换。
运行：venv\\Scripts\\python.exe w6_hr_policy\\tests\\test_v17_auth.py（cwd=项目根）"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)   # main.py 的 memory.db 是 cwd 相对路径，与既有约定一致：从项目根解析
os.environ.setdefault("W6_API_KEY", "test-key-z2")   # 测试专用 Key；真实部署由 .env 提供

os.makedirs(ROOT / "w6_hr_policy" / "data", exist_ok=True)   # memory.db 相对路径兜底

from fastapi.testclient import TestClient
import w6_hr_policy.app.main as main_mod
from w6_hr_policy.app.rate_limit import limiter

# ── LLM 桩：鉴权/限流测试绝不触碰真实模型 ─────────────────────────────
async def fake_run_agent(q, llm, tools, breaker=None, history=None):
    return "测试回答（桩）：年假按司龄档位计算", []

main_mod.run_agent = fake_run_agent
main_mod.make_llm = lambda: type("FakeLLM", (), {"chat": lambda self, *a, **k: None})()

failures = []
def expect(name, cond, extra=""):
    print(("[PASS] " if cond else "[FAIL] ") + name + (f" | {extra}" if extra and not cond else ""))
    if not cond:
        failures.append(name)

with TestClient(main_mod.app) as client:
    # ① 无 Key → 401
    r = client.get("/chat/stream", params={"q": "年假怎么算"})
    expect("① 无 Key 请求 → 401", r.status_code == 401, f"got {r.status_code}")

    # ② 错 Key → 401
    r = client.get("/chat/stream", params={"q": "年假怎么算"},
                   headers={"X-API-Key": "wrong-key"})
    expect("② 错 Key 请求 → 401", r.status_code == 401, f"got {r.status_code}")

    # ③ 对 Key → 200，且 SSE 流正常产出 delta 分片（LLM 已打桩）
    limiter.reset()
    r = client.get("/chat/stream", params={"q": "年假怎么算", "session_id": "t-z2-auth"},
                   headers={"X-API-Key": "test-key-z2"})
    expect("③ 对 Key 请求 → 200（SSE 出流）", r.status_code == 200 and "delta" in r.text,
           f"got {r.status_code}")

    # ④ 同 IP 61 连发（对 Key）：前 60 全 200，第 61 个 → 429
    limiter.reset()
    codes = [client.get("/chat/stream", params={"q": "压测"},
                        headers={"X-API-Key": "test-key-z2"}).status_code
             for _ in range(61)]
    expect("④ 61 连发：第 61 个 → 429",
           all(c == 200 for c in codes[:60]) and codes[60] == 429,
           f"codes[:8]={codes[:8]} last3={codes[-3:]}")

    # 附加：/health 保持公开（fail-closed 不影响部署 Gate 与监控探活）
    r = client.get("/health")
    expect("⑤ /health 公开探活 → 200", r.status_code == 200, f"got {r.status_code}")

if failures:
    raise SystemExit(f"Z2 验收未通过：{failures}")
print("[PASS] Z2 鉴权+限流 5 项断言全过（离线，API 成本 $0）")
