# -*- coding: utf-8 -*-
# tools/check_targets.py
"""R7：投递清单 URL 可达性批量检测（零第三方依赖）。
用法：venv\\Scripts\\python.exe tools\\check_targets.py [--out 报告路径]
逻辑：读 job_hunt/targets_2026.csv 的 url 列 → 逐条 GET（跟随跳转，10s 超时）→
按响应分级：200 可达 / 3xx 跳转(记录最终地址) / 4xx-5xx 异常 / 连接失败(DNS/TLS)。
注意：仅做可达性初筛——「可达」≠「是校招入口」，JS 渲染页需人工复核；
此工具只减少盲跑，最终以浏览器打开为准。零 API 成本。"""
import argparse, csv, io, ssl, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "job_hunt" / "targets_2026.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LinkCheck/1.0"

def check(url: str) -> tuple[str, str]:
    """返回 (级别, 说明)。级别：OK / REDIRECT / HTTP_ERR / CONN_ERR。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            final = r.geturl()
            if final.rstrip("/") != url.rstrip("/"):
                return "REDIRECT", f"→ {final}"
            return "OK", f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return "HTTP_ERR", f"HTTP {e.code}"
    except Exception as e:
        return "CONN_ERR", f"{type(e).__name__}: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = list(csv.DictReader(io.open(CSV_PATH, encoding="utf-8-sig")))
    lines = ["| 公司 | URL | 级别 | 说明 |", "|---|---|---|---|"]
    n_bad = 0
    for r in rows:
        url = (r["url"] or "").strip()
        if not url:
            continue
        level, note = check(url)
        if level not in ("OK", "REDIRECT"):
            n_bad += 1
        lines.append(f"| {r['company']} | {url} | {level} | {note} |")
        print(f"[{level:9s}] {r['company']:14s} {url} {note}")
    print(f"\n[汇总] 共 {len(rows)} 条；异常 {n_bad} 条（需人工搜索修正官方入口）")
    if args.out:
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[check_targets] 报告已写入 {args.out}")

if __name__ == "__main__":
    main()
