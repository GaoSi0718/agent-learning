# -*- coding: utf-8 -*-
"""
存量文档中文化 · 批量重命名器
=============================
命名规则
--------
1. 描述性词汇 → 全部中文化
2. 技术专名（RAG / Agent / LLM / MCP / API / MySQL / Redis / TCP / OS / Python / ReAct）保留国际通用写法
3. 版本号（v1.1）、日期后缀（_20260830_...）、序号（01_）、报告编号（A1/Z12）保留原样
4. 目录名不改（notes / docs / job_hunt 等是工程路径，改动会破坏所有引用）

用法
----
    python tools/rename_zh.py --dry-run     # 只打印，不改名
    python tools/rename_zh.py --apply       # 执行改名 + 生成映射表
    python tools/rename_zh.py --rollback    # 反向恢复（读 存量中文化映射表.md）

风险说明
--------
- 已确认：项目内 .py 代码只引用 .txt/.json/.csv，**不引用任何 .md**（实测 grep）
- 唯一例外：w4_price_quality.py 里有一处输出字符串含 "w4_price_quality_result.md"，
  仅影响打印文案，不影响运行
- 改名后必须同步：知识库上传清单.md / kb_uploader.py 的 source 路径
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\WorkBuddyData\projects\agent-learning")
MAP_OUT = PROJECT_ROOT / "存量中文化映射表_20260908.md"

# (相对路径原名, 新文件名) —— 目录保持不变，只改文件名
RENAMES: list[tuple[str, str]] = [
    # ===== 根目录 =====
    ("CONTEXT.md", "项目上下文.md"),
    ("README.md", "项目说明.md"),
    ("SESSION_HANDOFF_20260908.md", "会话交接文档_20260908.md"),
    ("P0_execution_checklist_v1.1_20260905.md", "P0_执行清单_v1.1_20260905.md"),
    ("P0_execution_checklist_v1.2_20260905.md", "P0_执行清单_v1.2_20260905.md"),
    ("P0_execution_checklist_v1.3_20260905.md", "P0_执行清单_v1.3_20260905.md"),
    ("P0_execution_checklist_v1.4_20260905.md", "P0_执行清单_v1.4_20260905.md"),
    ("P0_execution_checklist_v1.5_20260905.md", "P0_执行清单_v1.5_20260905.md"),
    ("P0_execution_checklist_v1.6_20260905.md", "P0_执行清单_v1.6_20260905.md"),
    ("P0_execution_checklist_v1.7_20260905.md", "P0_执行清单_v1.7_20260905.md"),
    ("agent-route-kb-revision-v8.1_20260830151400.md",
     "Agent学习路线_知识库修订总纲_v8.1_20260830151400.md"),
    ("ai-agent-learning-roadmap-20260830_20260830165500.md",
     "AI应用与Agent开发_学习路线_20260830_20260830165500.md"),
    ("ai-agent-roadmap-review-20260831_20260831193000.md",
     "AI学习路线_严格评审_20260831_20260831193000.md"),
    ("ai-job-market-overview-20260830_20260830203000.md",
     "AI岗位市场_行业调研_v1_20260830_20260830203000.md"),
    ("ai-job-market-overview-v2-20260830_20260830210000.md",
     "AI岗位市场_行业调研_v2_20260830_20260830210000.md"),
    ("ai-job-market-overview-v3-20260830_20260830211500.md",
     "AI岗位市场_行业调研_v3_20260830_20260830211500.md"),
    ("ai-job-market-overview-v4-final-20260831_20260831190000.md",
     "AI岗位市场_行业调研_v4终版_20260831_20260831190000.md"),
    ("ai-job-market-systematic-research-20260830_20260830160000.md",
     "AI应用与Agent开发岗_校招系统性调研_20260830_20260830160000.md"),
    ("api_gateway_deploy_guide.md", "API网关_部署指南.md"),
    ("api_gateway_deploy_template.md", "API网关_部署模板.md"),
    ("city-research-ai-jobs-20260830_20260830153500.md",
     "AI岗位_城市调研_20260830_20260830153500.md"),
    ("framework_model_selection.md", "框架与模型选型.md"),
    ("progress-snapshot-2026-08-30_20260830153000.md",
     "AI学习进度快照_20260830_20260830153000.md"),
    ("rag_hr_qa_README.md", "RAG_HR问答项目_说明.md"),
    ("report-improvement-review-20260831_20260831190500.md",
     "报告改进对照表与复评记录_20260831_20260831190500.md"),
    ("report-quality-audit-20260830_20260830204500.md",
     "质量审计报告_20260830_20260830204500.md"),
    ("route_resource_evaluation.html", "路线资源评估.html"),
    ("stage1_review.md", "阶段一_复盘.md"),
    ("stage2_mldl_resource_pack.md", "阶段二_机器学习与深度学习_资源包.md"),
    ("v1_limits.md", "v1版本_能力边界.md"),
    ("w4_model_selection.md", "W4_模型选型.md"),
    ("w4_price_quality_result.md", "W4_性价比测评结果.md"),
    ("w4_selftest.md", "W4_自测.md"),
    ("w5_vision_integration_guide.md", "W5_视觉多模态_集成指南.md"),
    ("w5_vision_step_by_step_tutorial.md", "W5_视觉多模态_分步教程.md"),
    ("w7-compressed-sprint-job-first_20260830151400.md",
     "W7_压缩执行清单_秋招优先版_20260830151400.md"),

    # ===== docs/ =====
    ("docs/metrics_log.md", "指标口径日志.md"),
    ("docs/phase1-ai-cost-playbook-token-and-time-20260830011909.md",
     "阶段一_AI资源消耗手册_Token与时间_20260830011909.md"),

    # ===== job_hunt/resumes/ =====
    ("job_hunt/resumes/draft_ai_track.md", "简历草稿_AI方向.md"),
    ("job_hunt/resumes/draft_backend_track.md", "简历草稿_后端方向.md"),
    ("job_hunt/resumes/w6_evidence.md", "W6_作品证据.md"),

    # ===== notes/ =====
    ("notes/gap_list.md", "缺口清单.md"),
    ("notes/industry_watch_20260907.md", "行业动态观察_20260907.md"),
    ("notes/weekly_review_20260906.md", "周复盘_20260906.md"),
    ("notes/weekly_review_risks_20260906.md", "周复盘_风险项_20260906.md"),
    ("notes/eval_expansion/README.md", "说明.md"),

    # ===== notes/interview_prep/ =====
    ("notes/interview_prep/C1_function_calling_deep_dive.md", "C1_函数调用_深度剖析.md"),
    ("notes/interview_prep/C3_termination_talk.md", "C3_终止机制_话术.md"),
    ("notes/interview_prep/C4_working_modes.md", "C4_工作模式.md"),
    ("notes/interview_prep/README.md", "说明.md"),
    ("notes/interview_prep/bug_stories.md", "故障排查故事.md"),
    ("notes/interview_prep/w6_grill.md", "W6_项目追问.md"),

    # ===== notes/interview_qa/（序号保留） =====
    ("notes/interview_qa/01_llm_vs_agent.md", "01_LLM与Agent的区别.md"),
    ("notes/interview_qa/02_agent_vs_workflow.md", "02_Agent与工作流的区别.md"),
    ("notes/interview_qa/03_function_call_4steps.md", "03_函数调用四步法.md"),
    ("notes/interview_qa/04_rag_pipeline.md", "04_RAG流程.md"),
    ("notes/interview_qa/05_hallucination.md", "05_幻觉问题.md"),
    ("notes/interview_qa/06_fc_vs_rag.md", "06_函数调用与RAG对比.md"),
    ("notes/interview_qa/07_react_anti_loop.md", "07_ReAct防死循环.md"),
    ("notes/interview_qa/08_react_vs_plan_execute.md", "08_ReAct与计划执行对比.md"),
    ("notes/interview_qa/09_framework_vs_scratch.md", "09_框架与手写对比.md"),
    ("notes/interview_qa/10_vector_store_sync.md", "10_向量库同步.md"),
    ("notes/interview_qa/11_mcp.md", "11_MCP协议.md"),
    ("notes/interview_qa/12_multi_agent.md", "12_多智能体协作.md"),
    ("notes/interview_qa/13_structured_output.md", "13_结构化输出.md"),
    ("notes/interview_qa/14_context_decay.md", "14_上下文衰减.md"),
    ("notes/interview_qa/15_finetune_vs_rag.md", "15_微调与RAG对比.md"),
    ("notes/interview_qa/16_routing_rate_limit.md", "16_路由与限流.md"),
    ("notes/interview_qa/17_agent_security_cve.md", "17_Agent安全与漏洞.md"),
    ("notes/interview_qa/18_cost_reliability_math.md", "18_成本与可靠性计算.md"),
    ("notes/interview_qa/19_mysql_index.md", "19_MySQL索引.md"),
    ("notes/interview_qa/20_redis_cache_lock.md", "20_Redis缓存与锁.md"),
    ("notes/interview_qa/21_tcp_handshake.md", "21_TCP握手.md"),
    ("notes/interview_qa/reverse_questions.md", "反问面试官问题.md"),

    # ===== notes/l0_bank/ =====
    ("notes/l0_bank/mysql_50.md", "MySQL_八股50题.md"),
    ("notes/l0_bank/network_50.md", "计算机网络_八股50题.md"),
    ("notes/l0_bank/os_50.md", "操作系统_八股50题.md"),
    ("notes/l0_bank/python_50.md", "Python_八股50题.md"),
    ("notes/l0_bank/redis_50.md", "Redis_八股50题.md"),

    # ===== notes/zcode_reports/（纯编号+日期的 A1/Z12 等无英文描述词，保留） =====
    ("notes/zcode_reports/_audit_raw_20260907.md", "审计原始数据_20260907.md"),
    ("notes/zcode_reports/_targets_check_20260907.md", "目标清单核查_20260907.md"),
    ("notes/zcode_reports/audit_metrics_20260907.md", "审计指标_20260907.md"),
    ("notes/zcode_reports/bugs_found_20260906.md", "已发现缺陷_20260906.md"),
    ("notes/zcode_reports/daily_20260906.md", "日报_20260906.md"),
    ("notes/zcode_reports/dimo_systematic_review_20260907.md", "迪莫系统性评审_20260907.md"),
    ("notes/zcode_reports/dimo_to_zcode_20260906.md", "迪莫致zcode_20260906.md"),
    ("notes/zcode_reports/dimo_to_zcode_20260907.md", "迪莫致zcode_20260907.md"),
    ("notes/zcode_reports/full_selfcheck_20260907.md", "全量自检_20260907.md"),
    ("notes/zcode_reports/handover_20260906.md", "交接记录_20260906.md"),
    ("notes/zcode_reports/incident_20260906.md", "事故记录_20260906.md"),
    ("notes/zcode_reports/iteration_log_20260907.md", "迭代日志_20260907.md"),
    ("notes/zcode_reports/night_shift_summary_20260907.md", "夜间值守总结_20260907.md"),
    ("notes/zcode_reports/zcode_to_dimo_20260906.md", "zcode致迪莫_20260906.md"),
    ("notes/zcode_reports/D2_scripts_20260907.md", "D2_脚本_20260907.md"),

    # ===== w6_hr_qa/ =====
    ("w6_hr_qa/README.md", "说明.md"),
    ("w6_hr_qa/data/policies/sample_policy.md", "示例政策.md"),
]


def do_rename(dry: bool) -> tuple[int, int, list[str]]:
    ok, fail = 0, 0
    problems: list[str] = []
    for rel_old, new_name in RENAMES:
        old = PROJECT_ROOT / rel_old
        new = old.parent / new_name
        if not old.exists():
            problems.append(f"❌ 源不存在: {rel_old}")
            fail += 1
            continue
        if new.exists():
            problems.append(f"⚠️ 目标已存在，跳过: {new_name}")
            fail += 1
            continue
        if dry:
            print(f"[dry] {rel_old}  →  {new_name}")
        else:
            old.rename(new)
            print(f"[mv ] {rel_old}  →  {new_name}")
        ok += 1
    return ok, fail, problems


def do_rollback() -> None:
    for rel_old, new_name in reversed(RENAMES):
        old = PROJECT_ROOT / rel_old
        new = old.parent / new_name
        if new.exists() and not old.exists():
            new.rename(old)
            print(f"[undo] {new_name}  →  {rel_old}")


def write_map():
    lines = [
        "# 存量文档中文化 · 改名映射表",
        "",
        "> 生成：2026-09-08 · 迪莫 ｜ 用途：改名留痕 + 回滚依据 + 引用同步核对",
        "> 回滚：`python tools/rename_zh.py --rollback`",
        "> 命名规则：描述词全部中文化；技术专名（RAG/Agent/LLM/MCP/API/MySQL/Redis/TCP/ReAct）保留；",
        "> 版本号、日期后缀、序号、报告编号（A1/Z12）保留；**目录名不改**。",
        "",
        "| # | 原文件名 | 新文件名 | 所在目录 |",
        "|---|---|---|---|",
    ]
    for i, (rel_old, new_name) in enumerate(RENAMES, 1):
        parts = rel_old.split("/")
        old_name = parts[-1]
        d = "/".join(parts[:-1]) if len(parts) > 1 else "（项目根）"
        lines.append(f"| {i} | `{old_name}` | `{new_name}` | `{d}` |")
    lines += ["", f"**合计 {len(RENAMES)} 个文件。**", ""]
    MAP_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n映射表已写入: {MAP_OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    a = ap.parse_args()

    if a.rollback:
        do_rollback()
        sys.exit(0)
    if a.apply:
        ok, fail, problems = do_rename(dry=False)
        write_map()
        print(f"\n改名完成：成功 {ok} / 失败 {fail}")
        for p in problems:
            print(p)
    else:
        ok, fail, problems = do_rename(dry=True)
        print(f"\n[dry-run] 将改 {ok} 个，异常 {fail}")
        for p in problems:
            print(p)
