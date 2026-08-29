"""
W3 批量评测：统计简历抽取字段准确率
来源：阶段一待办清单 W3 ②步「跑脚本统计字段准确率」

运行：
  cd D:/WorkBuddyData/projects/agent-learning
  venv\Scripts\activate
  python w3_batch_eval.py

读取：resumes_30.txt（30 条真实简历） + resumes_30_groundtruth.json（标准答案）
输出：各字段准确率 + 是否达 ≥90% 达标线
"""
import json
import os
import re
import sys

from pathlib import Path
from dotenv import load_dotenv
from w3_extract_resume import extract, validate

load_dotenv(Path(__file__).resolve().parent / ".env")

FIELDS = ["name", "email", "phone", "skills", "years_of_experience", "education"]


def norm_phone(s):
    return re.sub(r"\D", "", s or "")


def norm_skills(lst):
    return set((x or "").strip().lower() for x in lst or [])


def norm_text(s):
    return (s or "").strip()


def load_resumes(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    blocks = re.split(r"===== \d+ =====", raw)
    return [b.strip() for b in blocks if b.strip()]


def field_correct(pred, truth, field):
    if field == "phone":
        return norm_phone(pred.get("phone")) == norm_phone(truth.get("phone"))
    if field == "email":
        return norm_text(pred.get("email")).lower() == norm_text(truth.get("email")).lower()
    if field == "skills":
        return norm_skills(pred.get("skills")) == norm_skills(truth.get("skills"))
    if field == "years_of_experience":
        return pred.get("years_of_experience") == truth.get("years_of_experience")
    # name / education
    return norm_text(pred.get(field)) == norm_text(truth.get(field))


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    resumes = load_resumes(os.path.join(base, "resumes_30.txt"))
    with open(os.path.join(base, "resumes_30_groundtruth.json"), "r", encoding="utf-8") as f:
        truths = json.load(f)

    assert len(resumes) == len(truths), f"条数不一致：文本{len(resumes)} vs 答案{len(truths)}"

    stats = {f: {"ok": 0, "total": 0} for f in FIELDS}
    fails = []

    for i, (text, truth) in enumerate(zip(resumes, truths), 1):
        try:
            pred = extract(text)
        except Exception as e:
            print(f"[第{i}条] 抽取异常: {e}")
            fails.append((i, "exception", str(e)))
            for f in FIELDS:
                stats[f]["total"] += 1
            continue

        for f in FIELDS:
            stats[f]["total"] += 1
            if field_correct(pred, truth, f):
                stats[f]["ok"] += 1
            else:
                fails.append((i, f, {"pred": pred.get(f), "truth": truth.get(f)}))

    print("\n===== W3 字段准确率（30 条）=====")
    all_ok = all_ok_total = 0
    for f in FIELDS:
        ok, total = stats[f]["ok"], stats[f]["total"]
        rate = ok / total * 100 if total else 0
        all_ok += ok
        all_ok_total += total
        flag = "✅达标" if rate >= 90 else "⚠️未达标"
        print(f"  {f:<20} {ok}/{total} = {rate:5.1f}%  {flag}")

    overall = all_ok / all_ok_total * 100 if all_ok_total else 0
    print(f"\n  整体字段准确率: {all_ok}/{all_ok_total} = {overall:.1f}%")
    print(f"  达标线 ≥90%: {'✅ 已达标' if overall >= 90 else '⚠️ 未达标，需修复'}")

    if fails:
        print(f"\n===== 失败明细（{len(fails)} 项）=====")
        for i, f, detail in fails[:20]:
            print(f"  第{i}条 [{f}]: {detail}")
        if len(fails) > 20:
            print(f"  ... 其余 {len(fails)-20} 项省略")


if __name__ == "__main__":
    main()
