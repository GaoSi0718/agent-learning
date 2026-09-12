# -*- coding: utf-8 -*-
"""T2 辅助：列出待汇聚的 workspace memory 文件（全路径 + 大小 + 热度）。"""
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\高斯\.workbuddy"
now = time.time()
hot = 0
for dp, dn, fn in os.walk(ROOT):
    if os.path.basename(dp) != "memory":
        continue
    low = os.path.abspath(dp).lower()
    if "_archive" in low or "backup" in low:
        continue
    for f in fn:
        if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f):
            p = os.path.join(dp, f)
            st = os.stat(p)
            age = (now - st.st_mtime) / 60
            flag = " 🔥HOT" if age < 10 else ""
            if age < 10:
                hot += 1
            print("%s | %d B | %.1f min 前%s" % (p, st.st_size, age, flag))
print("HOT_COUNT=%d" % hot)
