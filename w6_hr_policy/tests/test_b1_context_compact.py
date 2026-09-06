# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b1_context_compact.py
"""B1 自测 A（离线，零 API）：compact 触发判据与摘要保真。
调用契约（与 main.py 一致）：build_context 只接收 user/assistant 历史（load 产物），
system 原始指令由 run_agent 外层拼接、不进 compact——对应清单踩坑笔记第 1 条。
验证三判据：超窗口预算 70% 才触发 compact；摘要保留「用户目标/已试工具/结论/未决问题」；
最近 SUMMARY_KEEP_LAST 轮原文保留。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from w6_hr_policy.app.context import build_context, token_estimate

class FakeLLM:
    """返回固定摘要（真实实现为 LLM 生成；离线测试只验证机制）"""
    def chat(self, messages, tools=None, timeout=None):
        class R: content = "【摘要】用户工龄 12 年，目标：确认年假天数；已聊 BM25 与算术；未决问题：年假能休几天。"
        return R()

def long_text(seed):
    return f"第{seed}轮背景补充。" + "企业年假管理涉及工龄认定、折算规则与跨年安排等细节。" * 20

def main():
    fake = FakeLLM()
    msgs = []  # 模拟 main.py 的 load()：仅 user/assistant，不含 system
    msgs.append({"role": "user", "content": "我工龄 12 年，先记一下。"})
    msgs.append({"role": "assistant", "content": "好的，已记住您工龄 12 年。"})
    for i in range(2, 12):
        msgs.append({"role": "user", "content": long_text(i)})
        msgs.append({"role": "assistant", "content": long_text(i) + "（答复）"})

    before = len(msgs)
    out = build_context(list(msgs), fake, budget_tokens=6000)
    after = len(out)

    assert token_estimate(msgs) > 6000 * 0.7, "测试前置不成立：消息体未超 70% 预算"
    assert after < before, f"compact 未触发（{before}→{after}）"
    assert len(out) == 5, f"compact 输出应为 1 摘要 + 4 保留轮，实际 {after} 条"
    assert out[0]["role"] == "system" and "【历史摘要】" in out[0]["content"], "摘要未保留/位置错误"
    assert "工龄 12 年" in out[0]["content"], "摘要丢失用户目标（工龄 12 年）"
    assert "未决问题" in out[0]["content"], "摘要丢失未决问题"
    assert out[-4:] == msgs[-4:], "最近 4 条原文未保留"
    print(f"[PASS] compact 机制：{before} 条 → {after} 条（1 摘要 + 4 原文）；"
          f"摘要含用户目标与未决问题；原始 system 由 run_agent 外层拼接、未被压缩")

if __name__ == "__main__":
    main()
