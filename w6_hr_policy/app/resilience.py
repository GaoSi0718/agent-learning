# -*- coding: utf-8 -*-
# w6_hr_policy/app/resilience.py
"""B3 可靠性三件套骨架：重试 / 超时 / 降级（全离线可测，GLM Key 到位后只改 .env，本文件不动）。
- 超时：由 OpenAI client 的 timeout（config.API_TIMEOUT）承担，本层只负责识别其异常形态；
- 重试：call_with_retry 仅对「超时 / 连接错误 / 5xx / 429 限流」重试，其余 4xx（400/401/404
  等协议错误，重试必然复现）不重试直接抛；指数退避默认 (0.5, 1, 2)s；每轮尝试记入 trace。
  429 纳入重试的理由：清单 §11 明确「免费档 429 → B3 的重试逻辑正好能验证」——它是瞬态
  节流而非协议错误，与 400/401 性质不同；
- 降级：LLM 全灭时 fallback_answer() 直连 BM25 检索 top3，拼条款原文 + [source] 出处
  （与 tools.search_policy 的 [source] text 格式一致），绝不静默失败；
- 超时预算闸门：3 次尝试 × 单次 30s(API_TIMEOUT) + 退避 0.5+1=1.5s ≈ 91.5s
  < agent_loop LoopBreaker.total_timeout=120s 总闸，重试不会击穿总闸。
"""
import time

# 可重试判定：openai 原生异常 + 鸭子类型兜底（让离线 FakeLLM 不必构造 openai 异常对象）
def is_retryable(exc) -> bool:
    """超时/连接错误/5xx/429 → True；其余（含 4xx 协议错误）→ False。"""
    # openai 原生异常族
    try:
        import openai
        if isinstance(exc, openai.APITimeoutError):
            return True
        if isinstance(exc, openai.APIConnectionError):
            return True
        if isinstance(exc, openai.RateLimitError):
            return True
        if isinstance(exc, openai.APIStatusError) and getattr(exc, "status_code", 0) >= 500:
            return True
    except ImportError:
        pass
    # 鸭子类型兜底：类名带 Timeout/Connection，或异常自带 status_code
    name = type(exc).__name__.lower()
    if "timeout" in name or "connection" in name:
        return True
    sc = getattr(exc, "status_code", None)
    if isinstance(sc, int) and (sc >= 500 or sc == 429):
        return True
    return False

def call_with_retry(fn, *args, max_attempts=3, backoff=(0.5, 1, 2),
                    trace=None, retry_on=is_retryable, **kwargs):
    """同步重试包装（P0 口径 chat 为同步调用）。
    trace：可选 list，每轮尝试追加一条 {"attempt","ok","error","waited_s"}；
    成功返回 fn 结果；不可重试异常立即抛；重试耗尽抛最后一次异常。"""
    trace = trace if trace is not None else []
    last = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.perf_counter()
        try:
            r = fn(*args, **kwargs)
            trace.append({"attempt": attempt, "ok": True, "error": None,
                          "waited_s": 0.0,
                          "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
            return r
        except Exception as e:
            waited = backoff[attempt - 1] if attempt - 1 < len(backoff) else backoff[-1] if backoff else 0
            ok_retry = attempt < max_attempts and retry_on(e)
            trace.append({"attempt": attempt, "ok": False,
                          "error": f"{type(e).__name__}: {e}",
                          "waited_s": waited if ok_retry else 0.0,
                          "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
            if not ok_retry:
                raise
            last = e
            if waited > 0:
                time.sleep(waited)
    raise last  # 理论不可达（耗尽时上面已 raise），保险起见

FALLBACK_NOTICE = "智能回答暂不可用，以下为检索到的原始条款："

async def fallback_answer(query: str, top_k: int = 3) -> str:
    """降级路径：LLM 不可用时直连检索，返回与主链路一致的 [source] 条款原文。
    检索本身也挂了也要如实说明——绝不静默失败、绝不编造。"""
    from .rag import retrieve          # 惰性导入：不拖累不需要检索的测试
    try:
        hits = await retrieve(query, top_k=top_k)
    except Exception as e:
        return (f"{FALLBACK_NOTICE}\n"
                f"（检索服务同样不可用：{type(e).__name__}: {e}。请稍后重试。）")
    if not hits:
        return f"{FALLBACK_NOTICE}\n（检索无结果。请稍后重试，或改用更短的关键词。）"
    return (FALLBACK_NOTICE + "\n" +
            "\n---\n".join(f"[{h['source']}] {h['text']}" for h in hits))
