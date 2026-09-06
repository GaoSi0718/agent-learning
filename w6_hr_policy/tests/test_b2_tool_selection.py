# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b2_tool_selection.py
"""B2 自测 2：工具选型准确率（清单判据 ≥9/10）。
10 条真实问句（5 该调 / 5 不该调）走真实 DeepSeek tool_calls 判定。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from w6_hr_policy.app.llm import make_llm
from w6_hr_policy.app.tools import IMPL

SYSTEM = "你是 HR 政策问答助手：依据检索到的政策条款回答，结论需带出处；检索不到就如实说，不要编造。"

CASES = [
    # (问句, 期望：应调用工具的名单 / "NONE" 表示不应调用)
    ("我们公司的年假是怎么规定的？", {"search_policy"}),
    ("报销流程和标准是什么？", {"search_policy"}),
    ("迟到早退会怎么处理？", {"search_policy"}),
    ("社保和公积金按什么基数缴？", {"search_policy"}),
    ("2026-09-10 那天是工作日吗？", {"workday_lookup"}),
    ("你好，很高兴认识你", "NONE"),
    ("1 加 1 等于几？", "NONE"),
    ("帮我用 Python 写一个快速排序", "NONE"),
    ("什么是 TCP 三次握手？", "NONE"),
    ("今天天气真不错啊", "NONE"),
]

def main():
    llm = make_llm()
    correct = 0
    for q, expect in CASES:
        resp = llm.chat([{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": q}],
                        tools=dict(IMPL))
        names = sorted({t.name for t in (resp.tool_calls or [])})
        if expect == "NONE":
            ok = not names
        else:
            ok = any(n in expect for n in names)
        correct += ok
        tag = "✅" if ok else "❌"
        print(f"{tag} {q} → 调用: {names or '无'}（期望 {expect}）")
    print(f"\n选型准确率: {correct}/10（判据 ≥9）")
    assert correct >= 9, f"工具选型准确率 {correct}/10 低于判据 9"
    print("[PASS] B2 工具选型准确率达标")

if __name__ == "__main__":
    main()
