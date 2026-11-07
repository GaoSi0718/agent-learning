# -*- coding: utf-8 -*-
"""Run reviewed offline checks by default; --e2e also runs API/service checks.

New test files require explicit classification before execution. Exit 0 means
all selected checks passed, 1 means failure, and 77 means selected checks skipped.
Unselected E2E checks are counted as SKIP without making the offline gate fail.
Offline checks may write local test data; use an isolated project copy.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "w6_hr_policy" / "tests"
PER_TEST_TIMEOUT = 120
SKIP_EXIT_CODE = 77

# Explicit list prevents newly added API tests from silently entering offline runs.
OFFLINE_TESTS = {
    "test_b1_context_compact.py",
    "test_b2_dispatch.py",
    "test_b3_resilience.py",
    "test_c2_loop_breaker.py",
    "test_pii_guard.py",
    "test_v17_auth.py",
    "test_v17_fallback.py",
    "test_v17_memory_wal.py",
}
E2E_TESTS = {
    "test_b2_e2e.py": "requires local service and real API",
    "test_b1_memory_12rounds.py": "requires local service and 12 real LLM rounds",
    "test_b2_tool_selection.py": "requires real tool-selection API calls",
    "test_eval_gate.py": "requires real DeepSeek judge API calls",
}


def discover():
    offline, e2e, unknown = [], [], []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name in OFFLINE_TESTS:
            offline.append(path)
        elif path.name in E2E_TESTS:
            e2e.append(path)
        else:
            unknown.append(path)
    return offline, e2e, unknown


def run_one(py, path):
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [py, str(path)], cwd=str(ROOT), timeout=PER_TEST_TIMEOUT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        output = "\n".join(s for s in (result.stdout, result.stderr) if s)
        # Compatibility with existing script tests that print SKIP and exit 0.
        skipped = re.search(r"^\s*(?:SKIP:|\[SKIP\])", output, re.MULTILINE)
        if result.returncode == SKIP_EXIT_CODE:
            mark = "SKIP"
        elif result.returncode != 0:
            mark = "FAIL"
        else:
            mark = "SKIP" if skipped else "PASS"
        return mark, time.perf_counter() - started, output.strip()
    except subprocess.TimeoutExpired:
        return "FAIL", time.perf_counter() - started, f"Timeout (>{PER_TEST_TIMEOUT}s)"
    except Exception as error:
        return "FAIL", time.perf_counter() - started, f"{type(error).__name__}: {error}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e2e", action="store_true", help="include real API/service tests (may incur cost)")
    args = parser.parse_args()
    offline, e2e, unknown = discover()
    print(f"[run_all_tests] Python: {sys.executable}")
    print(f"[run_all_tests] offline={len(offline)} E2E={len(e2e)} unclassified={len(unknown)}")
    if unknown:
        for path in unknown:
            print(f"[FAIL] {path.name}: unclassified; review API usage before adding to a list")
        return 1
    if not offline:
        print("[FAIL] No offline tests discovered; refusing an empty success")
        return 1
    results = []
    selected_skips = 0
    for path in offline + e2e:
        if path.name in E2E_TESTS and not args.e2e:
            mark, elapsed, output = "SKIP", 0.0, E2E_TESTS[path.name] + "; --e2e not enabled"
        else:
            mark, elapsed, output = run_one(sys.executable, path)
            selected_skips += mark == "SKIP"
        print(f"[{mark}] {path.name} ({elapsed:.2f}s)")
        if output:
            print(output)
        results.append(mark)
    passed, failed, skipped = (results.count(mark) for mark in ("PASS", "FAIL", "SKIP"))
    print(f"[summary] PASS {passed} / FAIL {failed} / SKIP {skipped} (total {len(results)})")
    if failed:
        print("[result] FAILED: at least one selected test failed")
        return 1
    if selected_skips:
        print("[result] INCOMPLETE: selected tests skipped; not an all-pass result")
        return SKIP_EXIT_CODE
    print("[result] Selected tests passed" + (" (including E2E)" if args.e2e else " (E2E not run)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
