# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_v17_memory_wal.py
"""R14 验收：记忆库 WAL 模式 + 并发写冒烟。
① init_db 后 PRAGMA journal_mode 返回 wal；
② 4 线程 × 25 次并发 save（默认 journal 下并发写易报 'database is locked'），
   断言全部落库、零异常、busy_timeout 生效。
全离线，API 成本 $0。运行：venv\\Scripts\\python.exe w6_hr_policy\\tests\\test_v17_memory_wal.py"""
import os, sqlite3, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import w6_hr_policy.app.main as m

failures = []
def expect(name, cond, extra=""):
    print(("[PASS] " if cond else "[FAIL] ") + name + (f" | {extra}" if extra and not cond else ""))
    if not cond:
        failures.append(name)

m.init_db()
con = m._connect()
mode = con.execute("PRAGMA journal_mode").fetchone()[0]
con.close()
expect("① journal_mode = wal", str(mode).lower() == "wal", f"got {mode}")

SID = f"t-wal-{threading.get_ident()}"
N_THREADS, N_WRITES = 4, 25
errors = []

def writer(tid):
    try:
        for i in range(N_WRITES):
            m.save(SID, "user", f"t{tid}-m{i}")
    except Exception as e:
        errors.append(f"t{tid}: {type(e).__name__}: {e}")

threads = [threading.Thread(target=writer, args=(i,)) for i in range(N_THREADS)]
for t in threads:
    t.start()
for t in threads:
    t.join()

con = m._connect()
n = con.execute("SELECT COUNT(*) FROM memory WHERE session_id=?", (SID,)).fetchone()[0]
con.close()
expect("② 并发写无异常", not errors, str(errors[:3]))
expect("③ 全部落库", n == N_THREADS * N_WRITES, f"got {n}, want {N_THREADS * N_WRITES}")

if failures:
    raise SystemExit(f"R14 WAL 验收未通过：{failures}")
print("[PASS] R14 记忆库 WAL+并发写 3 项断言全过（离线，API 成本 $0）")
