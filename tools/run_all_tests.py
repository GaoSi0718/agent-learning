# -*- coding: utf-8 -*-
# tools/run_all_tests.py
"""Z8：一键自测脚本——把「全部自测通过」从口头声明变成一键命令。
用法（cwd 任意）：
  venv\\Scripts\\python.exe tools\\run_all_tests.py           # 跑全部离线测试（门禁口径）
  venv\\Scripts\\python.exe tools\\run_all_tests.py --e2e     # 追加联调测试（需本地服务已启动+真实API）
设计：
- 离线测试 = w6_hr_policy/tests/ 下全部 test_*.py，剔除 E2E 集合（需起服务+真实 API，成本与稳定性都不适合做门禁）；
- 每个测试独立子进程（venv 内运行）、cwd=项目根（main.py 的 memory.db 是 cwd 相对路径）、120s 超时；
- 汇总 PASS/FAIL 表 + 失败输出尾部（便于定位）；退出码：离线全过=0，任一失败=1；
- 零 API 成本（联调测试默认 SKIP 且打印原因，不静默）。
"""
import argparse, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "w6_hr_policy" / "tests"
PER_TEST_TIMEOUT = 120

# 这些测试按设计需要「真实 LLM API」或「本地服务已启动」，不进默认门禁（--e2e 显式开启才跑）。
# test_b2_tool_selection 曾被误归类为离线（每次门禁烧 10 次真实调用），Z12 修正——以其自身
# docstring「走真实 DeepSeek tool_calls 判定」为准。
E2E_TESTS = {
    "test_b2_e2e.py": "HTTP 段需本地服务已启动；进程内段需真实 API",
    "test_b1_memory_12rounds.py": "12 轮真实 LLM 调用 + 需本地服务",
    "test_b2_tool_selection.py": "10 条问句走真实 DeepSeek tool_calls（约 10 次 API 调用）",
}

def discover():
    offline, e2e = [], []
    for p in sorted(TESTS_DIR.glob("test_*.py")):
        (e2e if p.name in E2E_TESTS else offline).append(p)
    return offline, e2e

def run_one(py, path):
    t0 = time.perf_counter()
    try:
        r = subprocess.run([py, str(path)], cwd=str(ROOT), timeout=PER_TEST_TIMEOUT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        elapsed = time.perf_counter() - t0
        ok = (r.returncode == 0)
        tail = "\n".join((r.stdout or "").strip().splitlines()[-3:])
        return ok, elapsed, tail, None
    except subprocess.TimeoutExpired:
        return False, PER_TEST_TIMEOUT, "", f"超时（>{PER_TEST_TIMEOUT}s）"
    except Exception as e:
        return False, time.perf_counter() - t0, "", f"{type(e).__name__}: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2e", action="store_true",
                    help="追加联调测试（需先起服务：set W6_API_KEY=<key> 后 uvicorn w6_hr_policy.app.main:app）")
    args = ap.parse_args()

    py = sys.executable   # 用运行本脚本的解释器（约定：venv 内运行，保证依赖一致）
    offline, e2e = discover()
    planned = offline + (e2e if args.e2e else [])
    print(f"[run_all_tests] 解释器：{py}")
    print(f"[run_all_tests] 离线测试 {len(offline)} 个；E2E {len(e2e)} 个"
          + ("（--e2e 已启用）" if args.e2e else "（默认跳过，需本地服务+真实API；--e2e 显式开启）"))
    print("-" * 72)

    results = []
    for p in planned:
        skipped = (p.name in E2E_TESTS and not args.e2e)
        if skipped:
            print(f"  [SKIP] {p.name:34s} 联调测试默认跳过（需本地服务+真实API）")
            results.append((p.name, "SKIP", 0.0, ""))
            continue
        ok, elapsed, tail, err = run_one(py, p)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {p.name:34s} {elapsed:5.1f}s" + (f" | {err}" if err else ""))
        if not ok and tail:
            for line in tail.splitlines():
                print(f"         │ {line[:110]}")
        results.append((p.name, mark, elapsed, err or tail))

    print("-" * 72)
    passed = sum(1 for _, m, *_ in results if m == "PASS")
    failed = sum(1 for _, m, *_ in results if m == "FAIL")
    skipped = sum(1 for _, m, *_ in results if m == "SKIP")
    print(f"[汇总] PASS {passed} / FAIL {failed} / SKIP {skipped}（共 {len(results)}）")
    if failed:
        print("[结论] 门禁未通过：离线测试存在失败项")
        sys.exit(1)
    print("[结论] 离线测试全部通过，门禁通过" + ("（含联调）" if args.e2e else "（联调未含）"))
    sys.exit(0)

if __name__ == "__main__":
    main()
