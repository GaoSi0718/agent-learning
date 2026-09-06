# w6_hr_policy/app/main.py
import json, os, sqlite3, time
from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from .agent_loop import run_agent
from .context import compact, summarize_tool_result, build_context
from .llm import make_llm
from .auth import require_api_key
from .rate_limit import rate_limit
from .resilience import fallback_answer

app = FastAPI(title="W6 HR 政策问答")

def make_tools():
    """W1 v1.5 阶段暂无注册工具（纯检索问答）；W2 v1.6 起返回 tools.IMPL"""
    try:
        from .tools import IMPL
        return dict(IMPL)
    except ImportError:
        return {}
DB = "w6_hr_policy/data/memory.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS memory (
        session_id TEXT, ts REAL, role TEXT, content TEXT)""")
    con.commit(); con.close()

@app.on_event("startup")
def _():
    init_db()
    if not (os.getenv("W6_API_KEY") or "").strip():
        print("[W6][启动检查] W6_API_KEY 未配置：业务路由将按 fail-closed 全部拒绝(401)。"
              "公网部署前请在 .env 配置 W6_API_KEY（.env 不入库）。")

def save(session_id, role, content):
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO memory VALUES (?,?,?,?)",
                (session_id, time.time(), role, content))
    con.commit(); con.close()

def load(session_id, limit=40):
    """v1.5 修订：默认 20→40 行。原 limit=20（10 轮）会让 12 轮跨距测试的第 1 轮
    在第 12 轮前必然滑出窗口（每轮 user+assistant 共 2 行），跨距记忆无从谈起；
    长会话的体量控制仍由 build_context 的 70% token 预算闸门 + compact 负责。"""
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT role, content FROM memory WHERE session_id=? ORDER BY ts DESC LIMIT ?",
        (session_id, limit)).fetchall()
    con.close()
    return [{"role": r, "content": c} for r, c in reversed(rows)]

@app.get("/health")
async def health():
    """健康检查（W5 部署验收与 W11 p0_gate.sh 都会打这个接口）"""
    return {"status": "ok"}

@app.get("/chat/stream", dependencies=[Depends(rate_limit), Depends(require_api_key)])
async def chat_stream(q: str, session_id: str = "default"):
    """SSE 流式。P0 口径：Agent 跑完后把最终答复分片吐出（先把流式管道打通）；
    真·逐 token 增量（LLM stream=True）属 P1 优化项，不影响本阶段验收。
    v1.7 前置：限流+鉴权作为路由级依赖，在 EventSourceResponse 产生之前完成——
    即鉴权失败/超限时流根本不会开始，不会先烧一次 LLM 调用再拒绝。"""
    async def gen():
        llm = make_llm()
        history = build_context(load(session_id), llm)   # 记忆压缩接线（W1 D3 context.py）：超窗口预算 70% 才 compact
        try:
            ans, trace = await run_agent(q, llm, make_tools(), history=history)
        except Exception as e:
            # B3 降级（R6 接线）：LLM 链路全灭（重试耗尽/网络不可达）→ 检索直答，
            # 绝不静默失败或断流；降级答复同样入记忆，会话上下文不丢
            print(f"[W6][降级] run_agent 失败，转检索直答：{type(e).__name__}: {e}")
            ans = await fallback_answer(q)
        for i in range(0, len(ans), 8):            # 每 8 字符一片，模拟逐段输出
            yield {"event": "message", "data": json.dumps(
                {"delta": ans[i:i+8]}, ensure_ascii=False)}
        save(session_id, "user", q)
        save(session_id, "assistant", ans)         # 问答双方都存，否则记忆只有一半
    return EventSourceResponse(gen())

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
async def index():
    """演示页：不直接烧 LLM，但会暴露服务用法，故挂鉴权不挂限流（真正的成本在 /chat/stream）。"""
    return """
<div id="out" style="white-space:pre-wrap;font-family:system-ui"></div>
<script>
const es = new EventSource('/chat/stream?q=' + encodeURIComponent('年假怎么算'));
es.addEventListener('message', e => {
  document.getElementById('out').textContent += JSON.parse(e.data).delta;
});
es.onerror = () => es.close();
</script>
"""
