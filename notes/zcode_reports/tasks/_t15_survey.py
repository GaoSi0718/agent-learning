# -*- coding: utf-8 -*-
"""T15 勘探：L1 MEMORY.md 的标题结构与字节占比。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L1 = r"C:\Users\高斯\.workbuddy\MEMORY.md"
text = open(L1, encoding="utf-8").read()
print("总大小: %d B / %d 行" % (len(text.encode("utf-8")), text.count("\n") + 1))
lines = text.split("\n")
heads = []
for i, ln in enumerate(lines):
    if re.match(r"^#{1,3} ", ln):
        heads.append((i, ln))
for j, (i, ln) in enumerate(heads):
    end = heads[j + 1][0] if j + 1 < len(heads) else len(lines)
    span = "\n".join(lines[i:end])
    print("%6d B  L%-5d %s" % (len(span.encode("utf-8")), i + 1, ln[:70]))
