# -*- coding: utf-8 -*-
# notes/interview_prep/modes_demo/mode_2_react.py
"""工作模式 2 · ReAct（推理-行动-观察循环）最小示例。
脚本化 FakeLLM 按轮次返回「工具调用 → 工具调用 → 最终回答」，展示：
- Act：程序执行模型选择的工具
- Observe：结果回传进 messages
- 终止：模型不再给 tool_calls 即收敛（终止权在模型，资源权在代码）
对照真实实现：w6_hr_policy/app/agent_loop.py（此处为教学缩略版）。
运行：python mode_2_react.py —— 零依赖、零 API。"""
import json
from types import SimpleNamespace as NS

TOOLS = {
    "search_policy": lambda query: "【检索结果】试用期工资按正式工资总额的 80% 发放（章节 5.2）",
    "calc": lambda expr: "80% → 0.8 × 10000 = 8000 元",
}

class FakeReActLLM:
    """按调用轮次脚本化的模型：第 1/2 轮要求调工具，第 3 轮给出最终回答。"""
    def __init__(self):
        self.turn = 0
    def chat(self, messages):
        self.turn += 1
        if self.turn == 1:
            return NS(tool_calls=[NS(name="search_policy", args={"query": "试用期工资"})], content=None)
        if self.turn == 2:
            return NS(tool_calls=[NS(name="calc", args={"expr": "10000*0.8"})], content=None)
        return NS(tool_calls=[], content="试用期月薪 = 10000 × 80% = 8000 元（依据章节 5.2）")

def main():
    llm, messages, trace = FakeReActLLM(), [{"role": "user", "content": "试用期工资多少？"}], []
    for step in range(1, 9):                      # 资源闸：步数上限在代码手里
        resp = llm.chat(messages)
        if not resp.tool_calls:                   # 模型决定收敛
            trace.append({"step": step, "type": "final", "content": resp.content})
            break
        for call in resp.tool_calls:              # Act：程序执行，模型只表达意图
            result = TOOLS[call.name](**call.args)
            trace.append({"step": step, "tool": call.name, "result": result[:30]})
            messages.append({"role": "tool", "content": result})   # Observe：结果回传
    for t in trace:
        print(json.dumps(t, ensure_ascii=False)[:100])

    assert trace[-1]["type"] == "final" and "8000" in trace[-1]["content"], "循环应收敛到最终答案"
    assert sum(1 for t in trace if t.get("tool")) == 2, "应有两次工具行动"
    print("[PASS] 模式2：Think-Act-Observe 循环——每步动作由模型输出决定，收敛由「无 tool_calls」触发")

if __name__ == "__main__":
    main()
