# -*- coding: utf-8 -*-
# notes/interview_prep/modes_demo/mode_3_plan_and_execute.py
"""工作模式 3 · Plan-and-Execute（先规划后执行）最小示例。
核心性质（脚本自证）：先产出完整计划，执行阶段严格按计划顺序进行、
不再产生新决策；并演示「计划步骤失败 → 局部 re-plan」的兜底。
运行：python mode_3_plan_and_execute.py —— 零依赖、零 API。"""
import json

def fake_planner(task: str) -> list[dict]:
    """规划调用：一次性返回完整计划（真实场景 = 一次结构化 LLM 调用）。"""
    return [
        {"step": 1, "action": "检索条款", "arg": "试用期工资"},
        {"step": 2, "action": "提取比例", "arg": "从检索结果中提取 80%"},
        {"step": 3, "action": "计算月薪", "arg": "10000 × 比例"},   # 将失败：无比例上下文
    ]

def executor(action: str, arg: str) -> str:
    """执行调用：只做计划交给它的事，不做任何新决策。"""
    env = {"检索条款": "试用期工资按正式工资 80% 发放（章节 5.2）",
           "提取比例": "0.8"}
    if action == "计算月薪":
        return f"{arg} = 8000 元"
    return env.get(arg, env.get(action, f"执行 {action}: {arg}"))

def replan(failed_step: dict) -> list[dict]:
    """局部重规划：失败步骤替换为「先补上下文再执行」。"""
    return [{"step": failed_step["step"], "action": "提取比例", "arg": "从检索结果中提取 80%"},
            {"step": failed_step["step"] + 1, "action": "计算月薪", "arg": "10000 × 0.8"}]

def main():
    plan = fake_planner("试用期工资多少？")
    print("计划（执行前产出，可人工审核）：", json.dumps(plan, ensure_ascii=False))

    results, i, executed_order = [], 0, []
    while i < len(plan):
        step = plan[i]
        try:
            if step["action"] == "计算月薪" and "比例" in step["arg"]:
                raise ValueError("执行器拿不到比例值（模拟计划缺陷）")
            out = executor(step["action"], step["arg"])
            results.append((step["step"], out))
            executed_order.append(step["action"])
        except ValueError as e:
            print(f"  [re-plan] 步骤 {step['step']} 失败：{e}")
            plan[i:i+1] = replan(step)          # 原地替换失败步骤
            print("  [re-plan] 新计划：", json.dumps(plan, ensure_ascii=False))
        i += 1

    for s, out in results:
        print(f"  step{s}: {out}")

    assert executed_order[:2] == ["检索条款", "提取比例"], "执行顺序必须严格按计划"
    assert any("8000" in out for _, out in results), "re-plan 后应完成月薪计算"
    print("[PASS] 模式3：计划先行 + 执行期不再决策 + 失败步骤局部重规划（非整体重来）")

if __name__ == "__main__":
    main()
