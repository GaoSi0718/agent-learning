# -*- coding: utf-8 -*-
"""批量实测投递链接可达性 —— 输出 evidence/link_check_result.csv
判定口径：
  OK          HTTP 200/301/302 且最终 URL 非空
  BLOCKED     403/405/429/503（疑似反爬，需浏览器人工确认）
  DEAD        404/410 或 DNS/连接失败/超时
  NO_URL      该行原始 apply_url 为空或为"待核实"
"""
import csv, io, os, sys, time, json
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "job_hunt", "targets_2026.csv")
OUTDIR = os.path.join(ROOT, "job_hunt", "evidence")
os.makedirs(OUTDIR, exist_ok=True)
OUT = os.path.join(OUTDIR, "link_check_result.csv")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

rows = list(csv.DictReader(io.open(SRC, encoding="utf-8-sig")))
res = []
for i, r in enumerate(rows, 1):
    url = (r.get("apply_url") or "").strip()
    name = f"{i:02d} {r['company']}"
    if not url or url in ("待核实", "N/A", "-"):
        res.append([i, r["company"], r["city"], r["position"], url, "NO_URL", "", "", ""])
        print(f"[{i:02d}] NO_URL  {r['company']}")
        continue
    if not url.startswith("http"):
        url = "https://" + url
    status, final, note = "", "", ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        status = str(resp.status_code)
        final = resp.url
        code = resp.status_code
        if code in (200, 201):
            note = "OK"
        elif code in (301, 302, 303, 307, 308):
            note = "OK"
        elif code in (403, 405, 429, 503):
            note = "BLOCKED"
        elif code in (404, 410):
            note = "DEAD"
        else:
            note = "OTHER"
    except Exception as e:
        status = type(e).__name__
        note = "DEAD"
        final = ""
    res.append([i, r["company"], r["city"], r["position"], url, note, status, final, time.strftime("%Y-%m-%d %H:%M")])
    print(f"[{i:02d}] {note:8s} {status:22s} {r['company']}  -> {(final or '')[:70]}")
    time.sleep(0.4)

with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["idx", "company", "city", "position", "input_url", "verdict", "http_status", "final_url", "checked_at"])
    w.writerows(res)

from collections import Counter
c = Counter(x[5] for x in res)
print("\n=== 汇总 ===", dict(c))
print("输出:", OUT)
