# -*- coding: utf-8 -*-
"""T4+T5 证据采集：settings 逐键差异（脱敏）+ 身份文件双根状态 + 引用统计。"""
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
C_ROOT = r"C:\Users\高斯\.workbuddy"
D_ROOT = r"D:\WorkBuddyData"
SECRET_HINT = re.compile(r"secret|token|key|password", re.I)


def flat(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            p = prefix + "." + k if prefix else k
            out.update(flat(v, p))
    else:
        out[prefix] = d
    return out


def redact(v):
    s = json.dumps(v, ensure_ascii=False)
    if SECRET_HINT.search(s.split("=")[0][-40:] if "=" in s else ""):
        return "<脱敏:%d B>" % len(s)
    if SECRET_HINT.search(" ".join(re.findall(r"[A-Za-z_]+", s))):
        return "<含敏感字段:%d B>" % len(s)
    return s if len(s) <= 80 else s[:77] + "..."


print("===== T4 · settings.json 逐键差异 =====")
cj = json.load(open(os.path.join(C_ROOT, "settings.json"), encoding="utf-8"))
dj = json.load(open(os.path.join(D_ROOT, "settings.json"), encoding="utf-8"))
cf, df = flat(cj), flat(dj)
allkeys = sorted(set(cf) | set(df))
for k in allkeys:
    inc, ind = k in cf, k in df
    if inc and ind and cf[k] == df[k]:
        continue
    cv = redact(cf[k]) if inc else "<缺失>"
    dv = redact(df[k]) if ind else "<缺失>"
    print("  [%s] %s\n      C根: %s\n      D根: %s" % (
        "仅D" if not inc else ("仅C" if not ind else "值异"), k, cv, dv))

print("\n===== T5 · 身份/记忆文件双根状态 =====")
for f in ("SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"):
    for root in (C_ROOT, D_ROOT):
        p = os.path.join(root, f)
        if os.path.isfile(p):
            b = open(p, "rb").read()
            st = os.stat(p)
            import time
            print("  %s | %d B | sha16=%s | mtime=%s" % (
                p, len(b), hashlib.sha256(b).hexdigest()[:16],
                time.strftime("%m-%d %H:%M", time.localtime(st.st_mtime))))
        else:
            print("  %s | 不存在" % p)

print("\n===== T4/T5 · 引用关系统计 =====")
pat_a = re.compile(r"\.workbuddy\\settings\.json|\.workbuddy/settings\.json", re.I)
pat_b = re.compile(r"D:\\WorkBuddyData\\settings\.json|WorkBuddyData/settings\.json", re.I)
pat_soul = re.compile(r"SOUL\.md|IDENTITY\.md|USER\.md", re.I)
hits = {"C_settings": [], "D_settings": [], "identity": []}
for base, tag in ((r"D:\WorkBuddyData", "D"), (C_ROOT, "C")):
    for dp, dn, fn in os.walk(base):
        dn[:] = [x for x in dn if x not in ("venv", "node_modules", ".git", "_archive", "backup",
                                            "binaries", "versions")]
        if tag == "C" and "_archive" in dp:
            continue
        for f in fn:
            if not f.endswith((".py", ".json", ".cjs", ".js", ".md", ".yml", ".yaml", ".sh")):
                continue
            if f in ("settings.json", "MEMORY.md", "SOUL.md", "IDENTITY.md", "USER.md"):
                continue
            p = os.path.join(dp, f)
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if pat_a.search(t):
                hits["C_settings"].append(p)
            if pat_b.search(t):
                hits["D_settings"].append(p)
            if pat_soul.search(t) and f.endswith((".py", ".cjs", ".js", ".json", ".yml")):
                hits["identity"].append(p)
for k, v in hits.items():
    print("  %s: %d 处" % (k, len(v)))
    for p in v[:12]:
        print("    - %s" % p)
