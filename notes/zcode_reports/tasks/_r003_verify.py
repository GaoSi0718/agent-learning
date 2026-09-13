# -*- coding: utf-8 -*-
"""R-003 独立复核：②零丢失复验（T3/T15）③v2 抽验+0.6737 ④git 快照。全部当轮实测。"""
import csv
import json
import random
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"D:\WorkBuddyData\projects\agent-learning"
BK = r"D:\WorkBuddyData\backup\zcode-20260913"


def norm(s):
    return re.sub(r"[\s，。；：、！？（）()【】\[\]“”\"'‘’·…\-—~～]", "", s or "").lower()


def multiset_check(name, orig_lines, *containers):
    orig = Counter(ln for ln in orig_lines if ln.strip())
    pool = Counter()
    for c in containers:
        pool.update(ln for ln in c.split("\n") if ln.strip())
    lost = orig - pool
    print("[%s] 原非空行 %d，丢失 %d" % (name, sum(orig.values()), sum(lost.values())))
    for ln, n in list(lost.items())[:3]:
        print("   LOST: %r" % ln[:90])
    return not lost


ok_all = True

# ---- ② T3：备份 L2 的 §十 块 vs OPEN_ITEMS.md（零丢失范围=条目正文，节标题系有意替换，不计） ----
before = open(BK + r"\T3\CURRENT_STATUS.md.before-T3", encoding="utf-8").read()
blines = before.split("\n")
s = next(i for i, ln in enumerate(blines) if ln.startswith("## 十、开放问题"))
e = next(i for i, ln in enumerate(blines) if ln.startswith("## ") and i > s)
block = "\n".join(blines[s + 1:e])  # 跳过原节标题（其被有意替换为指针版标题）
oi = open(r"C:\Users\高斯\.workbuddy\OPEN_ITEMS.md", encoding="utf-8").read()
# 9→9b 唯一例外（原行形如 `9. **[新增 2026-09-11]** 项目级任务…`）
block_adj = re.sub(r"^9\. (\*\*\[新增 2026-09-11\]\*\* 项目级任务)", r"9b. \1", block, count=1, flags=re.M)
r3 = multiset_check("T3 §十→OPEN_ITEMS(9→9b校正后)", block_adj.split("\n"), oi)
entry_lines = [ln[:60] for ln in oi.split("\n") if re.match(r"^\d{1,2}[ab]?\.\s", ln)]
print("[T3] OPEN_ITEMS 顶层条目行 %d 行（期望 18）: %s" % (len(entry_lines), [x.split(".")[0] for x in entry_lines]))
ok3 = r3 and len(entry_lines) == 18
ok_all &= ok3

# ---- ② T15：备份 L1 vs 现 L1 + 归档 + 蒸馏行 ----
sys.path.insert(0, r"D:\WorkBuddyData\projects\agent-learning\notes\zcode_reports\tasks")
import _t15_migrate as M  # noqa: E402  # 只取 DISTILL 常量

l1_before = open(BK + r"\T15\MEMORY.md.before", encoding="utf-8").read()
l1_now = open(r"C:\Users\高斯\.workbuddy\MEMORY.md", encoding="utf-8").read()
arch = open(r"C:\Users\高斯\.workbuddy\MEMORY_ARCHIVE_20260913.md", encoding="utf-8").read()
distilled = Counter()
for v in M.DISTILL.values():
    distilled.update(ln for ln in v if ln.strip())
orig15 = Counter(ln for ln in l1_before.split("\n") if ln.strip())
pool15 = Counter(ln for ln in l1_now.split("\n") if ln.strip()) + \
    Counter(ln for ln in arch.split("\n") if ln.strip()) + distilled
lost15 = orig15 - pool15
invented = Counter(ln for ln in l1_now.split("\n") if ln.strip()) - \
    (Counter(ln for ln in l1_before.split("\n") if ln.strip()) + distilled)
# mem_edit 行内版本标记为预期产物，不计入凭空新增
invented = Counter({ln: n for ln, n in invented.items() if not ln.startswith("<!-- last-edit:")})
print("[T15] 原非空行 %d，丢失 %d，现L1凭空新增(除版本标记) %d，现L1=%d B，归档=%d B"
      % (sum(orig15.values()), sum(lost15.values()), sum(invented.values()),
         len(l1_now.encode('utf-8')), len(arch.encode('utf-8'))))
for ln, n in list(lost15.items())[:3]:
    print("   LOST: %r" % ln[:90])
ok_all &= not lost15 and not invented

# ---- ③ T22：v2 抽验 10 条 ----
v2 = json.load(open(BASE + r"\notes\eval_expansion\w6_eval_set_v2_20260913.json", encoding="utf-8"))
items = v2["items"]
policy = norm(open(BASE + r"\policy_context.txt", encoding="utf-8", errors="replace").read())
cands = [it for it in items if it.get("origin") == "candidates_80"]
aligned = [it for it in items if it.get("origin") == "aligned_v1"]
random.seed(20260913)
sample = random.sample(cands, 10)
hit = 0
for it in sample:
    ok = norm(it["source_excerpt"]) in policy
    hit += ok
    if not ok:
        print("   MISS: %s" % it["id"])
print("[T22] v2 总数 %d（期望 95）= aligned %d + candidates %d；抽验 10 条原文命中 %d/10"
      % (len(items), len(aligned), len(cands), hit))
q27 = next(it for it in aligned if it["id"] == "Q27")
q31 = next(it for it in aligned if it["id"] == "Q31")
print("[T22] Q27/Q31 pending_ruling 标记: %s / %s" % (
    bool(q27.get("pending_ruling")), bool(q31.get("pending_ruling"))))
ok_all &= len(items) == 95 and len(cands) == 64 and hit == 10

# ---- ③ T23：0.6737 复现 ----
fin = json.load(open(BASE + r"\w6_eval_final_k6.json", encoding="utf-8"))
scores = [x["score2"] for x in fin if isinstance(x.get("score2"), (int, float))]
avg = sum(scores) / len(scores)
print("[T23] avg(score2) = %.4f (n=%d)，与 0.674 基线偏差 %.4f" % (avg, len(scores), abs(avg - 0.674)))
ok_all &= abs(avg - 0.674) < 0.001

# ---- ④ git 快照（含时点，遵循新的并发窗口声明纪律） ----
import subprocess
G = r"D:\WorkBuddyData\binaries\PortableGit\versions\1.2.0\cmd\git.exe"
env = None
out = subprocess.run([G, "branch", "-vv"], cwd=BASE, capture_output=True, text=True,
                     encoding="utf-8", errors="replace").stdout
print("[GIT] %s" % out.strip())
out2 = subprocess.run([G, "status", "--porcelain"], cwd=BASE, capture_output=True, text=True,
                      encoding="utf-8", errors="replace").stdout
print("[GIT] 未提交 %d 项（快照时点见报告头）" % len(out2.splitlines()))

print("\nR003_VERIFY_%s" % ("OK" if ok_all else "FAIL"))
sys.exit(0 if ok_all else 1)
