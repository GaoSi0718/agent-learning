# -*- coding: utf-8 -*-
"""
kb_uploader.py
==============
ima 知识库「Agent学习路线」(ID=7491061882583856) 批量上传工具 · 离线规划层

职责
----
1. 校验 知识库上传清单.md 中的每个待传文件（存在 / 大小 / 后缀 / content_type）
2. 校验 知识库文件夹映射表.md 中的 folder_id 是否已填（不能是 TODO_FILL_*）
3. 生成按 batch 的 dry-run 执行计划（Markdown 表格）
4. 验证 REPLACE 策略（对比 KB 内已有同名条目的 size）
5. --apply 模式打印操作清单（**本脚本不直接调 MCP**，真传由主会话调 DeferExecuteTool）

用法
----
    # 默认 dry-run，列出所有待传文件的完整性检查结果
    python tools/kb_uploader.py --check-integrity

    # 列出所有 57 个待传文件（按 batch）
    python tools/kb_uploader.py --list

    # 只看某个 batch
    python tools/kb_uploader.py --batch 01

    # 生成某个 batch 的 dry-run 操作清单（Markdown）
    python tools/kb_uploader.py --batch 01 --plan-out plans/batch01_plan.md

    # 真传（仅打印 MCP 调用清单，不实际执行——主会话拿这份清单去调 DeferExecuteTool）
    python tools/kb_uploader.py --batch 01 --apply --plan-out plans/batch01_apply.md

约束
----
- 本脚本是 v2 配套交付，与 知识库上传清单.md / 知识库文件夹映射表.md 严格对齐
- 真传必须由能调 MCP 的主会话执行（mcp__ima-mcp__create_media / add_knowledge）
- 任何字段改动先改 md → 同步改本脚本 → 再上传
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 1. 常量：KB 身份与文件夹映射（与 知识库文件夹映射表.md 严格一致）
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_ID = "7491061882583856"  # "Agent学习路线", type=1001, 个人知识库

# 与 知识库文件夹映射表.md §1+§2 完全一致。建好文件夹后由 --refresh 替换 TODO_FILL_*。
FOLDER_MAP = {
    # 一级（2026-09-08 16:40 实测 refresh，来源 知识库文件夹映射表.md §1）
    "00_入口与交接":                  "folder_7503007604289198",
    "01_学习路线与执行清单":          "folder_7503007730118501",
    "02_求职与投递":                  "folder_7503007801420633",
    "03_简历与作品证据":              "folder_7503007851771666",
    "04_面试备战":                    "folder_7503007914685075",  # 客户端实际名带"（含 3 子层）"后缀
    "05_行业与城市调研":              "folder_7503007990182166",
    "06_知识与教程参考":              "folder_7503008048904723",
    "07_进度记录与工作日志":          "folder_7503008095043157",
    "99_待定":                        "folder_7503008136985281",
    # 04 子层（parent = folder_7503007914685075）
    "04-1_逐题QA":                    "folder_7503008191510516",
    "04-2_专项深挖":                  "folder_7503008283784767",
    "04-3_八股题库":                  "folder_7503008317339234",
}

# content_type 对照表（create_media 严格按此校验，找不到则拒绝上传）
CONTENT_TYPE_TABLE = {
    ".pdf":  "application/pdf",
    ".doc":  "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt":  "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls":  "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv":  "text/csv",
    ".md":   "text/markdown",
    ".markdown": "text/markdown",
    ".txt":  "text/plain",
    ".xmind": "application/x-xmind",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp3":  "audio/mpeg",
    ".m4a":  "audio/x-m4a",
    ".wav":  "audio/wav",
    ".aac":  "audio/aac",
    ".html": "text/html",
    ".epub": "application/epub+zip",
}
# 显式禁传清单（A4/A5 + 内部资料）
FORBIDDEN_EXTENSIONS = {".json", ".py", ".db", ".env", ""}

# REPLACE 命中的 KB 内已有条目（来自 get_knowledge_list 实测，2026-09-08 16:10）
# 用于 dry-run 时对比 file_size，验证是否真覆盖
KB_EXISTING_REPLACE_TARGETS = {
    "阶段一_P0_执行清单_v1.8_20260906.md":            {"size": 197193, "media_type": 7},
    "阶段一_P0_执行清单_学习笔记_v1.9_20260907.md":  {"size":  20070, "media_type": 7},
    "秋招冲刺版-参考方案-v7-20260901_260905155524.md": {"size": 27192, "media_type": 7},
    "长期成长版-主路线方案-v7-20260901_260905155430.md": {"size": 76978, "media_type": 7},
}

# ---------------------------------------------------------------------------
# 2. 57 个文件清单（与 知识库上传清单.md §2 严格一致）
# ---------------------------------------------------------------------------

PROJECT_ROOT = r"D:\WorkBuddyData\projects\agent-learning"
MEMORY_ROOT  = r"C:\Users\高斯\.workbuddy\2026-09-06-01-00-17"


@dataclass
class UploadItem:
    batch: str                # "01", "01-1" 等
    idx: int                  # batch 内序号
    source_path: str          # 本地绝对路径
    target_folder: str        # FOLDER_MAP 的 key
    target_file_name: str     # 上传时 file_name
    strategy: str             # "SAVE" or "REPLACE"
    notes: str = ""           # 备注

    # 计算字段
    content_type: str = ""
    size: int = 0
    exists: bool = False
    folder_id: str = ""
    errors: list = field(default_factory=list)


UPLOAD_PLAN: list[UploadItem] = [
    # === 批次 1 · 00 入口与交接（7 个 SAVE） ===
    UploadItem("00", 1,
        rf"{PROJECT_ROOT}\会话交接文档_20260908.md",
        "00_入口与交接", "会话交接文档_20260908.md", "SAVE"),
    UploadItem("00", 2,
        rf"{PROJECT_ROOT}\全局进度报告_20260908.md",
        "00_入口与交接", "全局进度报告_20260908.md", "SAVE"),
    UploadItem("00", 3,
        rf"{PROJECT_ROOT}\docs\指标口径日志.md",
        "00_入口与交接", "指标口径日志.md", "SAVE"),
    UploadItem("00", 4,
        rf"{PROJECT_ROOT}\新会话开场提示语.md",
        "00_入口与交接", "新会话开场提示语.md", "SAVE"),
    UploadItem("00", 5,
        rf"{PROJECT_ROOT}\项目上下文.md",
        "00_入口与交接", "项目上下文.md", "SAVE"),
    UploadItem("00", 6,
        rf"{PROJECT_ROOT}\今日执行手册_20260907.md",
        "00_入口与交接", "今日执行手册_20260907.md", "SAVE"),
    UploadItem("00", 7,
        rf"{MEMORY_ROOT}\.workbuddy\memory\MEMORY.md",
        "00_入口与交接", "区②_记忆审计工作区_MEMORY.md", "SAVE",
        "跨路径：区② DriverStore 工作区 memory"),
    # === 批次 2 · 01 学习路线（4 个 REPLACE；v1.9 笔记首选作 REPLACE 验证） ===
    UploadItem("01", 1,
        rf"{PROJECT_ROOT}\阶段一_P0_执行清单_v1.8_20260906.md",
        "01_学习路线与执行清单",
        "阶段一_P0_执行清单_v1.8_20260906.md", "REPLACE",
        "KB 同名 197193 B → 本地 199844 B"),
    UploadItem("01", 2,
        rf"{PROJECT_ROOT}\阶段一_P0_执行清单_学习笔记_v1.9_20260907.md",
        "01_学习路线与执行清单",
        "阶段一_P0_执行清单_学习笔记_v1.9_20260907.md", "REPLACE",
        "★ 验证 REPLACE：KB 同名 20070 B → 本地 20141 B（差值最小，先跑）"),
    UploadItem("01", 3,
        rf"{PROJECT_ROOT}\秋招冲刺版-参考方案-v7-20260901.md",
        "01_学习路线与执行清单",
        "秋招冲刺版-参考方案-v7-20260901_260905155524.md", "REPLACE",
        "本地无后缀，上传必须改名匹配 KB 内 27192 B 条目"),
    UploadItem("01", 4,
        rf"{PROJECT_ROOT}\长期成长版-主路线方案-v7-20260901.md",
        "01_学习路线与执行清单",
        "长期成长版-主路线方案-v7-20260901_260905155430.md", "REPLACE",
        "本地无后缀，上传必须改名匹配 KB 内 76978 B 条目"),
    # === 批次 3 · 02 求职与投递（2 个 SAVE） ===
    UploadItem("02", 1,
        rf"{PROJECT_ROOT}\job_hunt\投递清单_v3.0_20260907_完整证据版.md",
        "02_求职与投递",
        "投递清单_v3.0_20260907_完整证据版.md", "SAVE"),
    UploadItem("02", 2,
        rf"{PROJECT_ROOT}\job_hunt\AI工具支持度独立调研_20260906.md",
        "02_求职与投递",
        "AI工具支持度独立调研_20260906.md", "SAVE",
        "⚠️ 本地 git 未跟踪，需先 git add"),
    # === 批次 4 · 03 简历与作品证据（6 个 SAVE） ===
    UploadItem("03", 1,
        rf"{PROJECT_ROOT}\job_hunt\resumes\W6_作品证据.md",
        "03_简历与作品证据", "W6_作品证据.md", "SAVE"),
    UploadItem("03", 2,
        rf"{PROJECT_ROOT}\job_hunt\resumes\简历草稿_AI方向.md",
        "03_简历与作品证据", "简历草稿_AI方向.md", "SAVE"),
    UploadItem("03", 3,
        rf"{PROJECT_ROOT}\job_hunt\resumes\简历草稿_后端方向.md",
        "03_简历与作品证据", "简历草稿_后端方向.md", "SAVE"),
    UploadItem("03", 4,
        rf"{PROJECT_ROOT}\RAG_HR问答项目_说明.md",
        "03_简历与作品证据", "RAG_HR问答项目_说明.md", "SAVE"),
    UploadItem("03", 5,
        rf"{PROJECT_ROOT}\v1版本_能力边界.md",
        "03_简历与作品证据", "v1版本_能力边界.md", "SAVE"),
    UploadItem("03", 6,
        rf"{PROJECT_ROOT}\W7_分析报告.md",
        "03_简历与作品证据", "W7_分析报告.md", "SAVE"),
    # === 批次 5 · 04-1 逐题QA（22 个 SAVE） ===
    *[
        UploadItem("04-1", i,
            rf"{PROJECT_ROOT}\notes\interview_qa\{name}",
            "04-1_逐题QA", name, "SAVE")
        for i, name in enumerate([
            "01_LLM与Agent的区别.md",
            "02_Agent与工作流的区别.md",
            "03_函数调用四步法.md",
            "04_RAG流程.md",
            "05_幻觉问题.md",
            "06_函数调用与RAG对比.md",
            "07_ReAct防死循环.md",
            "08_ReAct与计划执行对比.md",
            "09_框架与手写对比.md",
            "10_向量库同步.md",
            "11_MCP协议.md",
            "12_多智能体协作.md",
            "13_结构化输出.md",
            "14_上下文衰减.md",
            "15_微调与RAG对比.md",
            "16_路由与限流.md",
            "17_Agent安全与漏洞.md",
            "18_成本与可靠性计算.md",
            "19_MySQL索引.md",
            "20_Redis缓存与锁.md",
            "21_TCP握手.md",
            "反问面试官问题.md",
        ], start=1)
    ],
    # === 批次 6 · 04-2 专项深挖（6 个 SAVE） ===
    *[
        UploadItem("04-2", i,
            rf"{PROJECT_ROOT}\notes\interview_prep\{name}",
            "04-2_专项深挖", name, "SAVE")
        for i, name in enumerate([
            "C1_函数调用_深度剖析.md",
            "C3_终止机制_话术.md",
            "C4_工作模式.md",
            "故障排查故事.md",
            "W6_项目追问.md",
        ], start=1)
    ],
    UploadItem("04-2", 6,
        rf"{PROJECT_ROOT}\notes\行业动态观察_20260907.md",
        "04-2_专项深挖", "行业动态观察_20260907.md", "SAVE",
        "面试速报，按 A3 §1.4 归 04-2 而非 05 调研"),
    # === 批次 7 · 04-3 八股题库（5 个 SAVE） ===
    *[
        UploadItem("04-3", i,
            rf"{PROJECT_ROOT}\notes\l0_bank\{name}",
            "04-3_八股题库", name, "SAVE")
        for i, name in enumerate([
            "MySQL_八股50题.md",
            "计算机网络_八股50题.md",
            "操作系统_八股50题.md",
            "Python_八股50题.md",
            "Redis_八股50题.md",
        ], start=1)
    ],
    # === 批次 8 · 04 根（2 个 SAVE） ===
    UploadItem("04-root", 1,
        rf"{PROJECT_ROOT}\notes\interview_prep\面试备战_说明.md",
        "04_面试备战", "面试备战_说明.md", "SAVE",
        "README 04 总索引，文件名加前缀避免与 KB 已有 README 冲突"),
    UploadItem("04-root", 2,
        rf"{PROJECT_ROOT}\notes\缺口清单.md",
        "04_面试备战", "缺口清单.md", "SAVE",
        "补缺清单，按 A2 §2.2 归 04 而非 01"),
    # === 批次 9 · 05 行业与城市调研（1 个 SAVE） ===
    UploadItem("05", 1,
        rf"{PROJECT_ROOT}\AI岗位_城市调研_20260830_20260830153500.md",
        "05_行业与城市调研",
        "AI岗位_城市调研_20260830_20260830153500.md", "SAVE",
        "唯一未上传的 8/30 系列调研"),
    # === 批次 10 · 07 进度记录（2 个 SAVE） ===
    UploadItem("07", 1,
        rf"{MEMORY_ROOT}\.workbuddy\memory\2026-09-06.md",
        "07_进度记录与工作日志",
        "区②_工作日志_2026-09-06.md", "SAVE"),
    UploadItem("07", 2,
        rf"{MEMORY_ROOT}\.workbuddy\memory\2026-09-07.md",
        "07_进度记录与工作日志",
        "区②_工作日志_2026-09-07.md", "SAVE"),
]


# ---------------------------------------------------------------------------
# 3. 校验函数
# ---------------------------------------------------------------------------

def detect_content_type(file_name: str) -> tuple[str, str]:
    """返回 (content_type, 状态)。状态: 'ok' / 'forbidden' / 'unknown'"""
    ext = os.path.splitext(file_name)[1].lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return ("", "forbidden")
    if ext in CONTENT_TYPE_TABLE:
        return (CONTENT_TYPE_TABLE[ext], "ok")
    return ("", "unknown")


def validate_item(item: UploadItem) -> UploadItem:
    """填充 item 的计算字段，错误入 item.errors"""
    # 1. 文件存在 + 大小
    p = Path(item.source_path)
    if not p.exists():
        item.errors.append(f"本地文件不存在：{item.source_path}")
    else:
        item.exists = True
        item.size = p.stat().st_size

    # 2. content_type
    ct, st = detect_content_type(item.target_file_name)
    item.content_type = ct
    if st == "forbidden":
        item.errors.append(f"扩展名禁传（content_type 对照表无 / 内部资料）")
    elif st == "unknown":
        item.errors.append(f"扩展名未知，未在 content_type 对照表")

    # 3. folder_id
    fid = FOLDER_MAP.get(item.target_folder, "")
    item.folder_id = fid
    if not fid:
        item.errors.append(f"target_folder 不在 FOLDER_MAP：{item.target_folder}")
    elif fid.startswith("TODO_FILL_"):
        item.errors.append(f"folder_id 未填（知识库文件夹映射表.md §1/§2 等待孟轩建文件夹）")

    # 4. REPLACE 命中校验
    if item.strategy == "REPLACE":
        kb_meta = KB_EXISTING_REPLACE_TARGETS.get(item.target_file_name)
        if not kb_meta:
            item.errors.append(f"REPLACE 目标不在 KB_EXISTING_REPLACE_TARGETS，需先用 get_knowledge_list 复核")
        else:
            # 本地 size 必须 ≠ KB size，否则是空覆盖/没真改
            if item.exists and item.size == kb_meta["size"]:
                item.notes = (item.notes + " | ").lstrip(" | ") + f"⚠️ 本地 size 与 KB 完全相同（{item.size} B），可能没真改"
            elif item.exists:
                diff = item.size - kb_meta["size"]
                item.notes = (item.notes + " | ").lstrip(" | ") + f"覆盖差值：{kb_meta['size']} → {item.size} B ({diff:+d})"

    return item


# ---------------------------------------------------------------------------
# 4. 输出
# ---------------------------------------------------------------------------

def cmd_check_integrity():
    """检查所有 57 个文件的完整性"""
    print(f"\n{'='*78}\n 完整性检查（{len(UPLOAD_PLAN)} 个文件）\n{'='*78}")
    all_ok = True
    for item in UPLOAD_PLAN:
        validate_item(item)
        status = "✅" if not item.errors else "❌"
        if item.errors:
            all_ok = False
        size_str = f"{item.size:>8} B" if item.exists else "(缺失)"
        print(f"{status} [{item.batch:>8} #{item.idx:>2}] {size_str}  "
              f"{item.target_folder:<24} ← {Path(item.source_path).name}")
        for err in item.errors:
            print(f"     ⚠️  {err}")
    print(f"\n{'='*78}\n 总结：{'全部通过 ✅' if all_ok else '存在问题 ❌'}\n{'='*78}")
    # 汇总
    n_total = len(UPLOAD_PLAN)
    n_missing = sum(1 for it in UPLOAD_PLAN if not it.exists)
    n_replace = sum(1 for it in UPLOAD_PLAN if it.strategy == "REPLACE")
    n_save = n_total - n_replace
    n_error = sum(1 for it in UPLOAD_PLAN if it.errors)
    print(f"  总数 {n_total} | REPLACE {n_replace} | SAVE {n_save} | "
          f"缺失 {n_missing} | 错误 {n_error}")
    sys.exit(0 if all_ok else 1)


def cmd_list():
    """列出所有待传文件（按 batch）"""
    from collections import defaultdict
    groups = defaultdict(list)
    for item in UPLOAD_PLAN:
        validate_item(item)
        groups[item.batch].append(item)
    print(f"\n{'='*78}\n 待传文件清单（{len(UPLOAD_PLAN)} 个，{len(groups)} 个 batch）\n{'='*78}")
    for batch in sorted(groups.keys()):
        items = groups[batch]
        n = len(items)
        rep = sum(1 for it in items if it.strategy == "REPLACE")
        print(f"\n## Batch {batch}（{n} 个，REPLACE {rep} 个）")
        for it in items:
            mark = "🔁" if it.strategy == "REPLACE" else "  "
            print(f"  {mark} #{it.idx:>2} {it.target_file_name}")
    print()


def cmd_batch(batch_filter: str):
    """查看单个 batch"""
    items = [it for it in UPLOAD_PLAN if it.batch == batch_filter]
    if not items:
        print(f"❌ batch '{batch_filter}' 不存在。可用值：{sorted(set(it.batch for it in UPLOAD_PLAN))}")
        sys.exit(2)
    for it in items:
        validate_item(it)
    print(f"\n## Batch {batch_filter} · {len(items)} 个文件")
    for it in items:
        status = "✅" if not it.errors else "❌"
        print(f"\n{status} #{it.idx}  {it.strategy}")
        print(f"  source_path:    {it.source_path}")
        print(f"  target_folder:  {it.target_folder}")
        print(f"  folder_id:      {it.folder_id or '(TODO)'}")
        print(f"  target_file:    {it.target_file_name}")
        print(f"  content_type:   {it.content_type}")
        print(f"  size:           {it.size} B (exists={it.exists})")
        if it.notes:
            print(f"  notes:          {it.notes}")
        if it.errors:
            for e in it.errors:
                print(f"  ⚠️ {e}")


def cmd_plan(batch_filter: Optional[str], plan_out: Optional[str], apply_mode: bool):
    """生成 dry-run / apply 操作清单（Markdown）"""
    items = [it for it in UPLOAD_PLAN if batch_filter is None or it.batch == batch_filter]
    if not items:
        print(f"❌ 没有匹配 batch='{batch_filter}' 的项")
        sys.exit(2)
    for it in items:
        validate_item(it)

    lines = []
    title = f"Batch {batch_filter} · {len(items)} 个文件 · {'APPLY' if apply_mode else 'DRY-RUN'}"
    lines.append(f"# {title}\n")
    lines.append(f"- 生成时间：{os.environ.get('COMPUTERNAME', '?')}\n")
    lines.append(f"- 真传环境：{'是' if apply_mode else '否（dry-run，仅打印操作清单）'}\n")
    lines.append(f"- KB：Agent学习路线 ({KNOWLEDGE_BASE_ID})\n\n")

    for it in items:
        lines.append(f"\n### #{it.idx} · {it.target_file_name}\n")
        lines.append(f"| 字段 | 值 |\n|---|---|\n")
        lines.append(f"| batch | `{it.batch}` |\n")
        lines.append(f"| source | `{it.source_path}` |\n")
        lines.append(f"| target_folder | `{it.target_folder}` |\n")
        lines.append(f"| folder_id | `{it.folder_id or '(TODO 未填)'}` |\n")
        lines.append(f"| target_file_name | `{it.target_file_name}` |\n")
        lines.append(f"| strategy | **{it.strategy}** |\n")
        lines.append(f"| content_type | `{it.content_type}` |\n")
        lines.append(f"| file_size | {it.size} B |\n")
        if it.notes:
            lines.append(f"| notes | {it.notes} |\n")
        if it.errors:
            lines.append(f"| ❌ errors | {'; '.join(it.errors)} |\n")

        if apply_mode:
            # 输出 MCP 调用清单
            lines.append(f"\n**MCP 调用序列**（主会话按顺序执行）\n")
            lines.append(f"```\n")
            lines.append(f"# 1) 创建媒体条目（拿 COS 上传凭证）\n")
            lines.append(f"mcp__ima-mcp__create_media(\n")
            lines.append(f"    knowledge_base_id='{KNOWLEDGE_BASE_ID}',\n")
            lines.append(f"    file_name='{it.target_file_name}',\n")
            lines.append(f"    file_ext='{os.path.splitext(it.target_file_name)[1]}',\n")
            lines.append(f"    content_type='{it.content_type}',\n")
            lines.append(f"    file_size={it.size}\n")
            lines.append(f")  → 返回 media_id + COS 凭证\n\n")
            lines.append(f"# 2) 用返回的 COS 凭证把本地文件 PUT 到 COS（curl/SDK，外部命令）\n")
            lines.append(f"#    （这一步不在 MCP 里，需另调 COS 上传工具）\n\n")
            lines.append(f"# 3) 入库到目标文件夹\n")
            lines.append(f"mcp__ima-mcp__add_knowledge(\n")
            lines.append(f"    knowledge_base_id='{KNOWLEDGE_BASE_ID}',\n")
            lines.append(f"    media_id='<步骤1返回>',\n")
            lines.append(f"    folder_id='{it.folder_id}',\n")
            lines.append(f"    duplicate_name_strategy='{it.strategy}'\n")
            lines.append(f")\n")
            lines.append(f"```\n")
        else:
            lines.append(f"\n**dry-run 操作**（不会真执行）：\n")
            lines.append(f"- 调 `create_media({it.target_file_name}, {it.content_type}, {it.size})`\n")
            lines.append(f"- 调 COS 上传凭证上传\n")
            lines.append(f"- 调 `add_knowledge(folder_id={it.folder_id}, strategy={it.strategy})`\n")
        lines.append("\n---\n")

    text = "".join(lines)
    if plan_out:
        Path(plan_out).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_out).write_text(text, encoding="utf-8")
        print(f"✅ 已写入 {plan_out}（{len(text)} 字符）")
    else:
        print(text)


# ---------------------------------------------------------------------------
# 5. CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="ima 知识库上传工具（离线规划层）")
    ap.add_argument("--check-integrity", action="store_true",
                    help="检查所有 57 个文件完整性（默认 dry-run）")
    ap.add_argument("--list", action="store_true",
                    help="列出所有待传文件（按 batch）")
    ap.add_argument("--batch", type=str, default=None,
                    help="只看某个 batch，如 '01' / '04-1' / '00' / '04-root' / '05' / '07' / '00-verify'(保留以兼容)")
    ap.add_argument("--plan-out", type=str, default=None,
                    help="把 dry-run/apply 清单写到指定文件")
    ap.add_argument("--apply", action="store_true",
                    help="apply 模式：生成可执行的 MCP 调用清单")
    args = ap.parse_args()

    if args.check_integrity:
        cmd_check_integrity()
    elif args.list:
        cmd_list()
    elif args.batch:
        cmd_plan(args.batch, args.plan_out, args.apply)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()