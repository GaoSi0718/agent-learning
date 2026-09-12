# -*- coding: utf-8 -*-
"""T15：L1 MEMORY.md 瘦身 —— 5 个大块逐字迁入 MEMORY_ARCHIVE_20260913.md，L1 原位留蒸馏版+指针。
零丢失校验：multiset(原全文行) == multiset(新L1行) ∪ multiset(归档行)。
L1 写入走 mem_edit（整文件替换：备份+原子+回读断言）。"""
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\WorkBuddyData\tools")
import mem_edit  # noqa: E402

L1 = r"C:\Users\高斯\.workbuddy\MEMORY.md"
ARCH = r"C:\Users\高斯\.workbuddy\MEMORY_ARCHIVE_20260913.md"
BK = r"D:\WorkBuddyData\backup\zcode-20260913\T15"

DISTILL = {
    "env": [
        "## 环境事实（蒸馏速查 · 2026-09-13 T15 瘦身；完整历史版逐字存于 `MEMORY_ARCHIVE_20260913.md` §A）",
        "- **agent-learning 项目唯一真身：`D:\\WorkBuddyData\\projects\\agent-learning`**；D 盘根不可写、`D:\\WorkBuddyData` 可写。",
        "- **git 真身（PATH 里没有 git）**：`D:\\WorkBuddyData\\binaries\\PortableGit\\versions\\1.2.0\\cmd\\git.exe`；**受管 Python**：`D:\\WorkBuddyData\\binaries\\python\\versions\\3.13.12\\python.exe`；项目 venv：`<项目根>\\venv\\Scripts\\python.exe`。",
        "- **工具链硬事实（勿重试已知死路）**：PowerShell 工具 stdout 拿不到 → `Out-File` 落盘 + Read 读回，或受管 Python subprocess 中转（根因 `CODEBUDDY_POWERSHELL_USE_PTY=1` ConPTY 回传缺陷）；Bash 工具 coreutils 全灭（注入 PATH 未含 PortableGit `usr\\bin`）→ 受管 Python 直读直写；`schtasks`/`wscript`/`cscript`/`mshta`/`wmic`/`sc`/`reg`/`Add-Type`/`Invoke-Expression` 均被沙箱拦截，不要反复重试；提权进程内 `schtasks`/`Dism` 等可用。",
        "- **判定 Windows 版本/UI 语言一律走 WMI / 注册表权威路径**（注册表 ProductName 显示 \"Windows 10\" 不可信；Git Bash 会话注入的 LANG/LC_ALL 会污染 .NET 语言判断）。",
        "- **WorkBuddy 更新 EBUSY 根治**：`enabledPlugins.\"weixinpay@workbuddy-builtin\": false`（嵌套在 enabledPlugins 内）——**不要改回 true**；`D:\\Workbuddy\\RepairApp.exe` 不是给用户双击的（无 context 参数会静默退出，属预期行为）。",
        "- MAX 设备：Win11 家庭中文版 25H2（build 26200），HP ZBook Power 15.6 G10。UWP/Electron 排查方法论、Codex/ChatGPT 配置要点、跨设备 git 约定等长文 → 归档 §A。",
    ],
    "remind": [
        "## 提醒机制（workbuddy-notify · 精简版 2026-09-13 T15；hook 根因排查史等完整版逐字存于 `MEMORY_ARCHIVE_20260913.md` §B）",
        "- 位置：`D:\\WorkBuddyData\\notify\\`（`notify.py` 入口 / `reminder.py` 核心 / `session_check.py` 开场自检 / `session_bootstrap.py` 开场接管注入）；运行环境 = 受管 venv。",
        "- **迪莫硬性调用约定**：任务完成 → `notify.py --level normal`；阻塞待确认 → `--level blocked`（**必须以 run_in_background 后台任务运行**，会原地阻塞等点击；**绝不可自分离子进程**——实测派生进程 ~1 秒内被回收）。",
        "- SessionStart hook 三 matcher（startup/resume/compact）× 2 脚本已生效；**每次会话自动注入开场接管**（先读 CURRENT_STATUS / 当轮实测 / 当轮落盘）；`hook_run.log` 是生效性探针。",
        "- **双保险**：开场主动读 `D:\\WorkBuddyData\\notify\\status.json`，`level==blocked` 且未 acknowledged → 以后台任务接手重发。",
        "- 用户明确表态：不需要\"开机自启\"级持久化，**若会变成噪声宁可放弃该功能** → 任何加重占用/打扰的改动前先问。",
    ],
    "research": [
        "### 系统性调研结论（2026-08-30 完成）→ 全文逐字迁至 `MEMORY_ARCHIVE_20260913.md` §C（核心结论与拍板已并入「秋招策略」，明细报告见 `ai-job-market-systematic-research` 系列文件）",
    ],
    "fourq": [
        "### 四问回复与双版本方案（2026-08-31 拍板，长期有效）→ 全文逐字迁至 `MEMORY_ARCHIVE_20260913.md` §D（决策结论不受影响，过程与文本细节查归档）",
    ],
    "kb": [
        "## Agent 学习路线知识库维护约定（精简版 2026-09-13 T15；API 实测细节/事故史完整版逐字存于 `MEMORY_ARCHIVE_20260913.md` §E）",
        "- 周计划因行业动态做**较大调整**时，默认一并动态修改 KB「Agent学习路线」的待办清单文档。",
        "- **默认自动上传**：本地生成/修订「Agent学习路线」相关文档后直接上传 KB，文件名加 `_YYYYMMDDHHMMSS` 保留两者；上传流程 = ima-skill knowledge-base 子模块（preflight-check → create_media → cos-upload → add_knowledge）；**用户当次明说\"已手动上传/本次无需\"则跳过**。",
        "- **KB ID 双通道**：OpenAPI 通道认加密串、MCP 通道认数字 ID（各库双形态 ID 全表见 `D:\\WorkBuddyData\\projects\\agent-learning\\tools\\kb_config.json` 与 CURRENT_STATUS §六）；⛔ `1991288913110421505` 是错误 ID，账号内不存在，勿引用。",
        "- **能力边界**：删除/重命名**无 API**（只能请孟轩客户端手删）；REPLACE 覆盖只走 MCP 通道；新建文件夹走 `create_folder`（同样删不掉，命名想清楚）；复制 = 已有 media_id + 新 folder_id（原条目仍在旧 folder）；🔒 **指示孟轩删任何条目前，必须先实测确认副本存在**；📌 重要文件本地必须留原件。",
        "- 笔记能力只能走脚本通道（`openapi/note/v1/*`，MCP 无笔记工具），知识库能力走 MCP 更稳；ima 笔记 `- [ ]`/`- [x]` 可点击且写回服务端，⚠️ 禁用的是 `☐`（U+2610）普通字符；`get_doc_content` 核对结构必须传 `target_content_format:1`。",
        "- **详版标准**（最高优先级之一）：配套资料必须给可复制命令行/预期输出/踩坑笔记；**输出格式默认仅 .md**（不附 HTML，除非当次说明）；动态学习计划必须整合 AI 日报（08:20，自动化时间一律当轮实测）等实时资讯。",
    ],
}


def find_spans(lines):
    idx = {}
    for i, ln in enumerate(lines):
        if ln.startswith("## 环境事实（2026-08-30 实测更正）"):
            idx["env_s"] = i
        elif ln.startswith("### 双根结构：") and "env_e" not in idx:
            idx["env_e"] = i
        elif ln.startswith("## 提醒机制（workbuddy-notify"):
            idx["remind_s"] = i
        elif ln.startswith("## 沟通风格") and "remind_e" not in idx:
            idx["remind_e"] = i
        elif ln.startswith("### 系统性调研结论（"):
            idx["research_s"] = i
        elif ln.startswith("### 四问回复与双版本方案（"):
            if "research_e" not in idx:
                idx["research_e"] = i
            if "fourq_s" not in idx:
                idx["fourq_s"] = i
        elif ln.startswith("## Agent 学习路线知识库维护约定（"):
            idx["kb_s"] = i
        elif ln.startswith("## 信息搜集协作约定") and "kb_e" not in idx:
            idx["kb_e"] = i
    idx["fourq_e"] = idx["kb_s"]
    return idx


def main():
    text = open(L1, encoding="utf-8").read()
    lines = text.split("\n")
    n0 = len(text.encode("utf-8"))
    idx = find_spans(lines)
    for k in ("env_s", "env_e", "remind_s", "remind_e", "research_s", "research_e",
              "fourq_s", "fourq_e", "kb_s", "kb_e"):
        if k not in idx:
            print("FATAL: 锚点缺失 %s" % k)
            return 1

    spans = [
        ("A", "环境事实", idx["env_s"], idx["env_e"], "env"),
        ("B", "提醒机制", idx["remind_s"], idx["remind_e"], "remind"),
        ("C", "系统性调研结论", idx["research_s"], idx["research_e"], "research"),
        ("D", "四问回复与双版本方案", idx["fourq_s"], idx["fourq_e"], "fourq"),
        ("E", "KB 维护约定", idx["kb_s"], idx["kb_e"], "kb"),
    ]
    os.makedirs(BK, exist_ok=True)
    open(os.path.join(BK, "MEMORY.md.before"), "w", encoding="utf-8", newline="").write(text)

    # 归档文件
    arch_parts = [
        "# MEMORY_ARCHIVE_20260913.md — L1 瘦身迁出内容存档（T15 · 对应 S4）",
        "",
        "> **建立**：2026-09-13 04:1x ｜ **执行**：zcode ｜ **性质**：**逐字迁出存档（零删改）**，L1 对应位置已留蒸馏版+指针",
        "> **回滚**：把 §X 原文搬回 L1 原位置即可；或从 `D:\\WorkBuddyData\\backup\\zcode-20260913\\T15\\MEMORY.md.before` 整文件恢复",
        "> **维护**：本文件只读存档；新内容不要往这里追加（除非迪莫复核后决定回迁）",
        "",
    ]
    moved_lines = []
    for tag, name, s, e, key in spans:
        block = lines[s:e]
        moved_lines.extend(block)
        arch_parts.append("## §%s %s（原 L1 第 %d–%d 行，逐字迁出）" % (tag, name, s + 1, e))
        arch_parts.append("")
        arch_parts.extend(block)
        arch_parts.append("")
    arch_content = "\n".join(arch_parts).rstrip("\n") + "\n"
    tmp = ARCH + ".tmp"
    open(tmp, "w", encoding="utf-8", newline="").write(arch_content)
    os.replace(tmp, ARCH)

    # 新 L1：倒序替换（避免行号失效）
    new_lines = list(lines)
    for tag, name, s, e, key in sorted(spans, key=lambda x: -x[2]):
        new_lines[s:e] = list(DISTILL[key]) + [""]
    new_text = "\n".join(new_lines)
    n1 = len(new_text.encode("utf-8"))

    # 零丢失校验（multiset）
    orig_counter = Counter(ln for ln in lines if ln.strip())
    new_counter = Counter(ln for ln in new_lines if ln.strip())
    arch_counter = Counter(ln for ln in (arch_content.split("\n")) if ln.strip())
    # 原文每个非空行 = 新L1 + 归档（允许归档新增的标题/头注行，反向校验：新L1不得出现原文没有的行，蒸馏行除外）
    distilled_set = Counter()
    for v in DISTILL.values():
        distilled_set.update(ln for ln in v if ln.strip())
    lost = orig_counter - (new_counter + arch_counter)
    invented = new_counter - (orig_counter + distilled_set)  # 新 L1 里的行必须来自原文或蒸馏集
    print("原 %d B → 新 L1 %d B（归档 %d B）" % (n0, n1, len(arch_content.encode("utf-8"))))
    print("丢失行数（原文有而两处皆无）: %d" % (sum(lost.values())))
    for ln, c in list(lost.items())[:5]:
        print("  LOST: %r" % ln[:80])
    print("凭空新增行数（新L1有但原文/蒸馏皆无）: %d" % (sum(invented.values())))
    if sum(lost.values()) or sum(invented.values()):
        print("FATAL: 零丢失校验未通过，L1 未写入（归档已写，可用备份恢复）")
        return 1

    # L1 走 mem_edit 整文件替换
    rc, msg = mem_edit.edit_file(L1, text, new_text, occurrence="1", caller="zcode-T15",
                                 backup_root=BK)
    print("mem_edit L1: rc=%d %s" % (rc, msg))
    if rc != 0:
        return rc
    print("T15_OK 新L1=%d B (%.1f KB)" % (n1, n1 / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
