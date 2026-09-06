# -*- coding: utf-8 -*-
# notes/interview_prep/modes_demo/mode_4_multi_agent.py
"""工作模式 4 · 多 Agent（supervisor / worker）最小示例。
核心性质（脚本自证）：
- 通信 = 显式结构化交接单（任务/上下文/预算），不共享父 Agent 全部历史；
- 异常 = 子 Agent 失败收敛为数据（status/result），失败不炸整批；
- 预算 = 每个子 Agent 独立计步（继承终止纪律）。
对照真实设计：w6_hr_policy/app/dispatch.py 的「调用即数据」收敛结构。
运行：python mode_4_multi_agent.py —— 零依赖、零 API。"""
import json

class WorkerAgent:
    """最小子 Agent：给定任务在自己的工具箱里循环，最多 max_steps 步。"""
    def __init__(self, name, tools, max_steps=4):
        self.name, self.tools, self.max_steps = name, tools, max_steps

    def run(self, task: dict) -> dict:
        """task=交接单；返回统一形态的结果数据（成功或失败都是数据不是异常）。"""
        for step in range(1, self.max_steps + 1):
            for tool_name, arg in self.tools:
                if tool_name == task["need"] and arg != "bad":
                    return {"agent": self.name, "status": "ok",
                            "result": f"{tool_name}({arg}) → 完成：{task['need']}"}
            # 模拟「工具失败」（bad 参数）：下一轮换路（此处直接收敛为失败数据）
        return {"agent": self.name, "status": "error", "result": "无法完成任务（步数耗尽）"}

def main():
    researcher = WorkerAgent("researcher", [("search_policy", "试用期工资")])
    auditor_bad = WorkerAgent("auditor", [("verify", "bad")], max_steps=2)   # 必然失败
    fallback = WorkerAgent("fallback_auditor", [("verify", "重算校验通过")])

    # supervisor：拆解 → 派发 → 收敛结果（交接单显式、预算独立）
    plan = [{"need": "search_policy", "context": "年假问题需先查条款"},
            {"need": "verify", "context": "对结论做事实核查"}]
    workers = [researcher, auditor_bad, fallback]
    answers = []
    for task in plan:
        for w in workers:
            r = w.run({**task, "budget_steps": w.max_steps})
            print(json.dumps(r, ensure_ascii=False)[:90])
            if r["status"] == "ok":
                answers.append(r)
                break
            print("  ↳ 失败收敛为数据，supervisor 换下一个 worker")

    assert len(answers) == 2, "两个任务都应有 worker 成功完成"
    assert any(r["agent"] == "fallback_auditor" for r in answers), "verify 任务应降级到备用 worker 完成"
    print("[PASS] 模式4：显式交接单 + 失败收敛为数据 + 失败不炸整批（supervisor 完成降级路由）")

if __name__ == "__main__":
    main()
