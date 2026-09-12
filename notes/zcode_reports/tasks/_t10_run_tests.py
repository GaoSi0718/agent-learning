# -*- coding: utf-8 -*-
"""T10/T21 测试跑批：逐个独立进程运行离线测试，记录退出码与尾部输出。"""
import subprocess
import sys

PY = r"D:\WorkBuddyData\projects\agent-learning\venv\Scripts\python.exe"
BASE = r"D:\WorkBuddyData\projects\agent-learning"

OFFLINE = [
    "test_b2_dispatch.py",
    "test_b1_context_compact.py",
    "test_b3_resilience.py",
    "test_v17_auth.py",
    "test_v17_memory_wal.py",
]
SPECIAL = "test_c2_loop_breaker.py"  # 必须单独进程（污染 IMPL）
API_BLOCKED = ["test_b2_tool_selection.py", "test_b2_e2e.py", "test_b1_memory_12rounds.py"]


def run(path):
    try:
        p = subprocess.run([PY, path], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240, cwd=BASE)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT 240s"


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "offline"
    files = OFFLINE + [SPECIAL] if which == "offline" else API_BLOCKED
    for fn in files:
        rc, out = run(BASE + "\\w6_hr_policy\\tests\\" + fn)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        tail = " || ".join(lines[-3:])[:300]
        print("### %s\n    rc=%s\n    tail: %s" % (fn, rc, tail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
