# w6_hr_policy/app/context.py
import json

MAX_HISTORY_TURNS = 10      # 超过这个轮数触发 compact
SUMMARY_KEEP_LAST = 4       # compact 后保留最近几轮原文

def summarize_tool_result(result: str, max_chars: int = 500) -> str:
    """工具返回摘要：长结果截断 + 标记，避免整篇塞回上下文"""
    if len(result) <= max_chars:
        return result
    return result[:max_chars] + f"\n…（已截断，原文 {len(result)} 字）"

def compact(messages, llm):
    """把早期对话压成一段摘要，保留最近若干轮原文"""
    if sum(1 for m in messages if m["role"] in ("user", "assistant")) <= MAX_HISTORY_TURNS:
        return messages
    head = messages[:-SUMMARY_KEEP_LAST]
    tail = messages[-SUMMARY_KEEP_LAST:]
    digest = llm.chat(head + [{
        "role": "user",
        "content": "把以上对话压缩成 150 字以内的要点摘要，保留：用户目标、已尝试的工具、已得出的结论、未解决的问题。"
    }]).content
    return [{"role": "system", "content": f"【历史摘要】{digest}"}] + tail

def token_estimate(messages):
    """中文粗估：约 2 字符 ≈ 1 token（精确计数用 tiktoken，P0 不引入）"""
    return sum(len(m.get("content", "")) for m in messages) // 2

def build_context(messages, llm, budget_tokens=6000):
    """组装上下文：超预算 70% 触发 compact，并打 token 日志（12 轮跨距测试用）"""
    n = token_estimate(messages)
    print(f"[context] tokens≈{n} / budget={budget_tokens}")
    if n > budget_tokens * 0.7:
        messages = compact(messages, llm)
    return messages
