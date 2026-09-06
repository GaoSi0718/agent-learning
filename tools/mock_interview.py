# -*- coding: utf-8 -*-
# tools/mock_interview.py
"""R16：面试自测 CLI——从 notes/interview_qa/ 随机抽题，先自己答，回车后看 30 秒参考答案。
用法：
  venv\\Scripts\\python.exe tools\\mock_interview.py            # 交互模式（Ctrl+C 退出）
  venv\\Scripts\\python.exe tools\\mock_interview.py --list     # 列出全部题目
  venv\\Scripts\\python.exe tools\\mock_interview.py --n 5      # 抽 5 题后结束
解析约定（interview_qa/*.md）：`## 题面` 与 `## 30 秒答` 两个小节。
纯标准库、零 API 成本；题库扩充后自动生效。"""
import argparse, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "notes" / "interview_qa"

def section(text: str, name: str) -> str:
    """提取 `## <name>` 小节正文（到下一个 ## 为止）。"""
    m = re.search(rf"^## {re.escape(name)}.*?\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""

def load():
    qs = []
    for p in sorted(QA_DIR.glob("*.md")):
        if p.name == "reverse_questions.md":
            continue
        text = p.read_text(encoding="utf-8")
        title = ""
        tm = re.match(r"^#\s*(\d+\s*·\s*.+)$", text, flags=re.M)
        if tm:
            title = tm.group(1).strip()
        q, a = section(text, "题面"), section(text, "30 秒答")
        if a:   # 只要求「30 秒答」；题面可选（缺省时以标题为题）
            qs.append({"file": p.name, "title": title, "q": q, "a": a})
    return qs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="抽题数量（0=不限，直到 Ctrl+C）")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    qs = load()
    if not qs:
        print("没有可用的题目（检查 notes/interview_qa/ 是否存在且含「题面/30 秒答」小节）")
        return 1
    if args.list:
        for i, x in enumerate(qs, 1):
            print(f"{i:2d}. {x['title'] or x['file']}")
        return 0
    print(f"[mock_interview] 已加载 {len(qs)}/21 题（缺「30 秒答」小节的文件会被列出）")
    qs_all = {p.name for p in QA_DIR.glob("*.md") if p.name != "reverse_questions.md"}
    qs_have = {x["file"] for x in qs}
    for name in sorted(qs_all - qs_have):
        print(f"  ⚠️ 未加载：{name}（缺「题面/30 秒答」小节）")

    random.shuffle(qs)
    asked = 0
    print(f"自测开始：共 {len(qs)} 题，先口头作答再按回车看参考。Ctrl+C 结束。\n")
    for x in qs:
        if args.n and asked >= args.n:
            break
        asked += 1
        print(f"─" * 60)
        print(f"[{asked}] {x['title'] or x['file']}")
        if x["q"]:
            print(x["q"][:300])          # 有独立题面小节则展示；无则标题即题目
        try:
            input("（自己答完后按回车看参考…）")
        except (KeyboardInterrupt, EOFError):
            print("\n结束。")
            return 0
        print("【30 秒参考】")
        print(x["a"])
        print()
    print(f"完成 {asked} 题。建议：答不顺的题回 interview_qa/ 对应文件重读 2 分钟深答。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
