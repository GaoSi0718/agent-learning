# -*- coding: utf-8 -*-
# tools/make_cards.py
"""R10：把 notes/l0_bank/ 五科题库转成 Anki 可导入的记忆卡 CSV。
用法：venv\\Scripts\\python.exe tools\\make_cards.py [--out-dir 目录]
输入格式约定（l0_bank 五份 md）：
  ### 序号. 题干
  - **简答**：…
  - **深答**：…（可多行续写，直到下一个 - ** 开头或下一个 ###）
  - **来源**：…
输出：notes/l0_bank/cards/<科目>_cards.csv（UTF-8-SIG，4 列 Front/Back/Extra/Tags）
  Front=题干；Back=简答（默写档）；Extra=深答+来源（展开档）；Tags=科目名
导入法：Anki → 文件导入 → 字段映射 Front/Back/Extra/Tags，按 Tags 建牌组。
纯标准库、零 API 成本；题库更新后重跑即可重新生成。"""
import argparse, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "notes" / "l0_bank"
OUT_DIR = BANK_DIR / "cards"
FILES = ["network_50.md", "os_50.md", "mysql_50.md", "redis_50.md", "python_50.md"]
FIELD_RE = re.compile(r"^-\s+\*\*(简答|深答|来源)\*\*[：:]\s*")

def parse(path: Path):
    """返回 [(题干, 简答, 深答, 来源), ...]；解析失败行为不计入，末尾汇总报告。"""
    cards, skipped = [], []
    cur = None  # dict: title/简答/深答(列表)/来源
    def flush():
        nonlocal cur
        if cur and cur["title"]:
            if not cur["简答"]:
                skipped.append(cur["title"][:40] + "（缺简答）")
            else:
                cards.append((cur["title"], cur["简答"], "\n".join(cur["深答"]), cur["来源"]))
        cur = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^###\s+\d+\.\s*(.+?)\s*$", raw)
        if m:
            flush()
            cur = {"title": m.group(1), "简答": "", "深答": [], "来源": ""}
            continue
        if cur is None:
            continue
        fm = FIELD_RE.match(raw.strip())
        if fm:
            field, rest = fm.group(1), raw.strip()[fm.end():].strip()
            if field == "深答":
                cur["深答"].append(rest)
            else:
                cur[field] = rest
        elif raw.strip().startswith("- ") and cur["深答"]:
            cur["深答"].append(raw.strip()[2:].strip())   # 深答的续行
        elif raw.startswith("###") or raw.startswith("## "):
            flush()
    flush()
    return cards, skipped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    total, problems = 0, []
    for name in FILES:
        path = BANK_DIR / name
        if not path.exists():
            problems.append(f"缺文件：{name}")
            continue
        cards, skipped = parse(path)
        out = out_dir / (name.replace(".md", "_cards.csv"))
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Front", "Back", "Extra", "Tags"])
            for title, brief, deep, src in cards:
                w.writerow([title, brief, (deep + ("\n【来源】" + src if src else "")).strip(), name.split("_")[0]])
        tag = name.split("_")[0]
        print(f"[{tag}] {len(cards)} 卡 → {out.relative_to(ROOT)}（跳过 {len(skipped)}）")
        for s in skipped:
            print(f"    ⚠️ 跳过：{s}")
        problems.extend(f"{tag}: {s}" for s in skipped)
        total += len(cards)
    print(f"\n[汇总] 共 {total} 卡；问题 {len(problems)} 条")
    if problems:
        print("（跳过明细见上——通常是该题缺「简答」段，回题库补齐后重跑）")
    return 1 if total < 200 else 0

if __name__ == "__main__":
    raise SystemExit(main())
