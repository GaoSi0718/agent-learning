# -*- coding: utf-8 -*-
"""T16：枚举 per-workspace memory 下的 MEMORY.md 类僵尸副本，按判定标准分类（只列不动）。"""
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\高斯\.workbuddy"
now = time.time()


def sha16(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


print("== A. 工作区 .workbuddy/memory/ 下所有文件 ==")
for dp, dn, fn in os.walk(ROOT):
    if os.path.basename(dp) != "memory":
        continue
    low = os.path.abspath(dp).lower()
    if "_archive" in low or "backup" in low or low == os.path.join(ROOT.lower(), "memory"):
        continue
    for f in sorted(fn):
        p = os.path.join(dp, f)
        st = os.stat(p)
        age_d = (now - st.st_mtime) / 86400
        print("  %s | %d B | mtime %.1f 天前 | sha16=%s" % (p, st.st_size, age_d, sha16(p)))

print("\n== B. 工作区下的 MEMORY.md 同名文件（任意层级） ==")
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [x for x in dn if x not in ("_archive", "backup")]
    for f in fn:
        if f == "MEMORY.md":
            p = os.path.join(dp, f)
            st = os.stat(p)
            print("  %s | %d B | mtime %s" % (p, st.st_size, time.strftime("%m-%d %H:%M", time.localtime(st.st_mtime))))

print("\n== C. 工作区下的 2026-09-12.md 残留 ==")
for dp, dn, fn in os.walk(ROOT):
    if os.path.basename(dp) != "memory":
        continue
    low = os.path.abspath(dp).lower()
    if "_archive" in low or "backup" in low:
        continue
    for f in fn:
        if f == "2026-09-12.md":
            p = os.path.join(dp, f)
            print("  %s" % p)
