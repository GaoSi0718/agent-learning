# -*- coding: utf-8 -*-
# notes/interview_prep/modes_demo/mode_1_prompt_chain.py
"""工作模式 1 · Prompt 链（Prompt Chaining / Workflow）最小示例。
核心性质（脚本自证）：控制流 100% 在代码里——步骤顺序、分支、终止都是写死的，
LLM（此处为脚本化 FakeLLM）只是流水线上的一个转换函数。
对照：mode_2_react.py 里「下一步做什么」由模型的 tool_calls 决定。
运行：python mode_1_prompt_chain.py —— 零依赖、零 API。"""
from types import SimpleNamespace as NS

def fake_llm_call(prompt: str) -> str:
    """脚本化「模型」：按 prompt 里的指令标记返回 canned 转换结果。
    真实场景即一次 chat.completions 调用；此处离线化。"""
    if "[STEP:提取要点]" in prompt:
        return "要点：员工试用期工资按正式工资 80% 发放"
    if "[STEP:改写为口语]" in prompt:
        return "试用期的工资是转正工资的八成哦～"
    raise ValueError("未知步骤")

def main():
    source = "公司手册 5.2 条：被录用员工试用期工资按所定正式工资总额的 80% 发放。"
    # ── 控制流全部在代码里：步骤顺序固定，没有任何「模型决定下一步」的逻辑 ──
    step1 = fake_llm_call(f"[STEP:提取要点]\n{source}")
    step2 = fake_llm_call(f"[STEP:改写为口语]\n{step1}")

    print("流水线：原文 → 提取要点 → 改写口语")
    print("  step1:", step1)
    print("  step2:", step2)

    # 自证核心性质：步骤数与顺序是代码常量，与「模型」输出无关
    steps = [fake_llm_call(f"[STEP:{s}]\n{source}") for s in ("提取要点", "改写为口语")]
    assert steps == [step1, step2], "输出顺序应严格等于代码定义的步骤顺序"
    print("[PASS] 模式1：控制流 100% 在代码（步骤顺序固定、无模型决策点）——这就是 Workflow")

if __name__ == "__main__":
    main()
