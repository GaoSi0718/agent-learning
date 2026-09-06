# -*- coding: utf-8 -*-
# tools/g1_gate_check.py
"""Z8：G1 Gate 十项自动检查——把人工判定变成可重复的命令。
用法（cwd 任意）：
  venv\\Scripts\\python.exe tools\\g1_gate_check.py
  venv\\Scripts\\python.exe tools\\g1_gate_check.py --strict-venv   # 第1项按字面「3.13.12」判（默认按 Z1 裁决建议：受管解释器即绿+备注）
判据来源：大任务清单 §A2 的 10 项自检表，按 2026-09-07 实况做了两处口径落地：
  #1 venv 版本：受管解释器二进制自报 3.13.14（目录名 3.13.12 名不符实，Z1 实测），
     默认「≥3.13.12 即绿+备注」，--strict-venv 保留字面判据——最终口径待迪莫裁决；
  #7 投递台账：按 CONTEXT §5.1 语义判「数据行 ≥5」为绿（唯一硬红项），修复动作只能孟轩执行，标 MANUAL。
输出：「X绿Y红」清单，每项打印检查明细（不打印 .env 的任何值）。
"""
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = r"D:\WorkBuddyData\binaries\PortableGit\versions\1.2.0\cmd\git.exe"
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"
APPLOG = ROOT / "job_hunt" / "log" / "applications.csv"
CORPUS = ROOT / "policy_context.txt"
METRICS = ROOT / "docs" / "metrics_log.md"

REQUIRED_ENV_KEYS = ["LLM_PROVIDER", "GLM_MODEL", "DEEPSEEK_MODEL",
                     "FALLBACK_PROVIDER", "API_TIMEOUT", "MAX_STEPS"]
REQUIRED_DIRS = ["w6_hr_policy", "job_hunt", "notes", "docs"]

def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)

results = []
def record(no, name, ok, detail, manual=False):
    mark = "绿" if ok else "红"
    tag = "【需人工修复：MANUAL】" if manual else ""
    print(f"  #{no:<2} [{mark}] {name}")
    print(f"        {tag}{detail}")
    results.append((no, name, ok, manual))

def check_venv(strict):
    name = "venv 版本正确（受管解释器）"
    if not VENV_PY.exists():
        return record(1, name, False, f"venv 解释器不存在：{VENV_PY}")
    r = sh([str(VENV_PY), "-V"])
    ver = (r.stdout or r.stderr).strip()
    m = re.match(r"Python (\d+)\.(\d+)\.(\d+)", ver)
    if not m:
        return record(1, name, False, f"无法解析版本输出：{ver!r}")
    triple = tuple(int(x) for x in m.groups())
    if strict:
        ok = ver == "Python 3.13.12"
        note = "--strict-venv 字面判据" + ("" if ok else "；受管解释器二进制自报 3.13.14（Z1 实测），字面判据不可达，需裁决")
        record(1, name, ok, f"实测 {ver}；{note}")
    elif triple >= (3, 13, 12):
        note = "" if ver == "Python 3.13.12" else \
            "受管解释器二进制版本（目录名 3.13.12 名不符实，Z1 实测）；判据按 Z1 裁决建议「≥3.13.12」执行，待迪莫确认"
        record(1, name, True, f"实测 {ver}；{note}")
    else:
        record(1, name, False, f"实测 {ver}，低于 3.13.12（G1 #1 红项）")

def check_deps():
    r = sh([str(VENV_PY), "-c", "import fastapi, sse_starlette, dotenv, pandas, jsonschema; print('ok')"])
    record(2, "P0 依赖齐备", r.returncode == 0,
           "import fastapi/sse_starlette/dotenv/pandas/jsonschema 全部成功" if r.returncode == 0
           else "导入失败：" + str((r.stderr or "").strip().splitlines()[-1:]))

def check_lock():
    lock = ROOT / "requirements.lock.txt"
    if not lock.exists():
        return record(3, "依赖已锁版本", False, "requirements.lock.txt 不存在")
    lines = lock.read_text(encoding="utf-8", errors="replace").splitlines()
    pinned = [l for l in lines if "==" in l and not l.strip().startswith("#")]
    key = [l for l in pinned if l.split("==")[0].strip() in ("openai", "jsonschema", "fastapi")]
    record(3, "依赖已锁版本", len(pinned) >= 20 and len(key) == 3,
           f"requirements.lock.txt 共 {len(pinned)} 条精确锁定；关键包抽查 openai/jsonschema/fastapi 命中 {len(key)}/3")

def check_env_keys():
    env = ROOT / ".env"
    if not env.exists():
        return record(4, "模型名配置化（.env 六变量）", False, ".env 不存在")
    keys = set()
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    missing = [k for k in REQUIRED_ENV_KEYS if k not in keys]
    if not missing:
        record(4, "模型名配置化（.env 六变量）", True, "六变量齐备（只查键名，不读值）")
    else:
        note = "；".join(
            f"{k}: {'预期缺失——待 §11 GLM Key 开通后添加' if k == 'GLM_MODEL' else '已被 B3 降级函数设计取代（resilience.py 直连检索），建议迪莫修订此判据'}"
            for k in missing)
        record(4, "模型名配置化（.env 六变量）", False, f"按 §A2 字面判据缺失：{missing}。说明：{note}")

def check_secret_not_tracked():
    r1 = sh([GIT, "check-ignore", ".env"], cwd=str(ROOT))
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace") if (ROOT / ".gitignore").exists() else ""
    ok = (r1.returncode == 0) and (".env" in gi)
    record(5, "密钥未入库", ok,
           f".gitignore 含 .env 条目={'.env' in gi}；git check-ignore 命中={r1.returncode == 0}")

def check_dirs():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    record(6, "目录骨架完整", not missing,
           "w6_hr_policy/job_hunt/notes/docs 四目录齐备" if not missing else f"缺失：{missing}")

def check_ledger():
    if not APPLOG.exists():
        return record(7, "投递台账数据行 ≥5", False,
                      f"{APPLOG.name} 不存在；【需人工修复：MANUAL】投递动作只能孟轩执行（CONTEXT §12）", manual=True)
    lines = [l for l in APPLOG.read_text(encoding="utf-8-sig", errors="replace").splitlines() if l.strip()]
    data_rows = max(0, len(lines) - 1)   # 表头不算
    ok = data_rows >= 5
    record(7, "投递台账数据行 ≥5", ok,
           f"当前数据行 {data_rows}（表头不计）" + ("" if ok else "；【需人工修复：MANUAL】投递动作只能孟轩执行（CONTEXT §12）"),
           manual=not ok)

def check_corpus():
    ok = CORPUS.exists() and CORPUS.stat().st_size >= 47313
    size = CORPUS.stat().st_size if CORPUS.exists() else 0
    record(8, "语料已灌入（≥47313B）", ok, f"policy_context.txt 实测 {size} 字节")

def check_baseline():
    if not METRICS.exists():
        return record(9, "评测基线已记录", False, "docs/metrics_log.md 不存在")
    text = METRICS.read_text(encoding="utf-8", errors="replace")
    ok = ("0.6607" in text) and ("0.674" in text)
    record(9, "评测基线已记录", ok,
           "台账含对齐基线 0.6607 与最终基线 score2=0.674" if ok else "台账缺 0.6607/0.674 行")

def check_git_remote():
    r1 = sh([GIT, "remote", "-v"], cwd=str(ROOT))
    r2 = sh([GIT, "rev-list", "--count", "HEAD"], cwd=str(ROOT))
    has_origin = "origin" in (r1.stdout or "")
    try:
        n = int((r2.stdout or "0").strip())
    except ValueError:
        n = 0
    record(10, "git 远端已备份", has_origin and n >= 7,
           f"origin 已配置={has_origin}；本地提交数 {n}（判据 ≥7）")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict-venv", action="store_true",
                    help="第 1 项按字面「Python 3.13.12」判（默认按 Z1 裁决建议：受管解释器 ≥3.13.12 即绿+备注）")
    args = ap.parse_args()
    print("[g1_gate_check] G1 Gate 十项检查（判据：大任务清单 §A2 + CONTEXT §5.1 实况口径）")
    print("-" * 72)
    check_venv(args.strict_venv)
    check_deps()
    check_lock()
    check_env_keys()
    check_secret_not_tracked()
    check_dirs()
    check_ledger()
    check_corpus()
    check_baseline()
    check_git_remote()
    print("-" * 72)
    green = sum(1 for _, _, ok, _ in results if ok)
    red = sum(1 for _, _, ok, _ in results if not ok)
    manual = sum(1 for _, _, _, m in results if m)
    print(f"[结论] {green}绿 {red}红（人工项 MANUAL：{manual} 个，当前为投递台账——只能孟轩执行）")
    for no, name, ok, m in results:
        if not ok:
            print(f"        红项处置建议：#{no} {name}")
    sys.exit(0 if red == 0 else 1)

if __name__ == "__main__":
    main()
