# -*- coding: utf-8 -*-
"""T22：候选池转正 —— 按 D001 判据 84→64，与现行 31 题对齐集合并为 w6_eval_set_v2_20260913.json。
参考答案口径 = policy_context.txt 原文条款（孟轩批准的零成本路线）；source_excerpt 程序化比对原文。
不覆盖任何既有文件。"""
import csv
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"D:\WorkBuddyData\projects\agent-learning"
CSV = BASE + r"\notes\eval_expansion\candidates_80.csv"
ALIGNED = BASE + r"\w6_eval_set_aligned.json"
POLICY = BASE + r"\policy_context.txt"
OUT = BASE + r"\notes\eval_expansion\w6_eval_set_v2_20260913.json"
MAP = r"D:\WorkBuddyData\projects\agent-learning\notes\zcode_reports\tasks\_t22_dedup_map.csv"

A_LEVEL = {"cand-%03d" % n for n in
           (1, 8, 9, 11, 24, 36, 39, 49, 50, 53, 56, 58, 59, 67, 68, 78, 81)}
INTERNAL = {"cand-029", "cand-042", "cand-060"}  # 045~060 组保留先出现的 cand-045
INTERNAL_REASON = {
    "cand-029": "与 cand-015 q_con=1.0（仅差标点语气词），保留 cand-015",
    "cand-042": "与 cand-038 q_con=0.714 且与 Q09 亦重叠，D001 建议弃",
    "cand-060": "与 cand-045 同事实仅换措辞（q_con=0.763），按『保留先出现者』弃 cand-060",
}
A_REASON = "D001 §二 A 级：同章节同事实被现行题覆盖（q_con/a_con 证据见 D001 表）"


def norm(s):
    return re.sub(r"[\s，。；：、！？（）()【】\[\]“”\"'‘’·…\-—~～]", "", s or "").lower()


def main():
    policy_text = norm(open(POLICY, encoding="utf-8", errors="replace").read())
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print("候选池行数: %d" % len(rows))
    aligned = json.load(open(ALIGNED, encoding="utf-8"))
    print("对齐集条数: %d" % len(aligned))

    kept, dropped = [], []
    for r in rows:
        qid = r["q_id"].strip()
        if qid in A_LEVEL:
            dropped.append((qid, "A", A_REASON))
        elif qid in INTERNAL:
            dropped.append((qid, "IN", INTERNAL_REASON[qid]))
        else:
            kept.append(r)
    print("保留 %d / 剔除 %d" % (len(kept), len(dropped)))
    assert len(kept) == 64 and len(dropped) == 20, "数量与 D001 结论不符，中止"

    # 原文比对验证
    verified = 0
    for r in kept:
        ex = norm(r.get("source_excerpt", ""))
        ok = len(ex) >= 10 and ex in policy_text
        r["_excerpt_verified"] = bool(ok)
        verified += ok
    print("source_excerpt 原文命中: %d/64（未命中条目在 v2 中标注 false，需人工复核）" % verified)
    for r in kept:
        if not r["_excerpt_verified"]:
            print("  UNVERIFIED: %s（chunk=%s）" % (r["q_id"], r["source_chunk_id"]))

    # v2 组装
    items = []
    for it in aligned:
        rec = dict(it)
        rec["origin"] = "aligned_v1"
        if it.get("id") in ("Q27", "Q31"):
            rec["pending_ruling"] = ("D001 §五：与同章节 6.2.1(6) 同事实疑似重复（互为双问法），"
                                     "待孟轩裁决（改写或加注），本集未自行删除")
        items.append(rec)
    for r in kept:
        items.append({
            "id": r["q_id"].strip(),
            "category": r["category"].strip(),
            "question": r["question"].strip(),
            "reference_answer": r["reference_answer"].strip(),
            "reference_source": "原文条款（chunk=%s）" % r["source_chunk_id"].strip(),
            "source_excerpt": r["source_excerpt"].strip(),
            "excerpt_verified_in_policy": r["_excerpt_verified"],
            "reference_answer_policy": "原文条款口径（2026-09-13 零成本路线，孟轩批准）",
            "proposed_by": r.get("proposed_by", "").strip(),
            "origin": "candidates_80",
        })
    v2 = {
        "meta": {
            "name": "w6_eval_set_v2_20260913",
            "generated_by": "zcode T22（2026-09-13），依据 notes/night_reports/D001_dedup_check_20260911.md",
            "composition": "现行对齐集 31 条 + 候选池转正 64 条 = 95 条",
            "dedup": "候选池 84 → 64：A 级剔除 17（D001 §二）+ 内部自重复剔除 3（cand-029/042/060；"
                     "045~060 组按『保留先出现者』弃 cand-060）",
            "reference_answer_policy": "参考答案 = policy_context.txt 原文条款（零成本路线，孟轩 2026-09-13 批准）；"
                                       "候选条目 source_excerpt 已程序化比对原文（excerpt_verified_in_policy 字段）",
            "baseline_note": "⚠️ 新基线与旧 0.674（k=6 score2，31 题）不可直接比较：题量 31→95、"
                             "参考答案口径=原文条款，均为口径差异，须在 docs/指标口径日志.md 显式标注",
            "pending_ruling": "Q27/Q31 同章节同事实双问法待孟轩裁决（本集保留未删）；"
                              "候选 64 条类别分布失衡（加班/薪酬社保被削），配平属内容判断，交迪莫",
        },
        "items": items,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(v2, f, ensure_ascii=False, indent=2)
    import os
    os.replace(tmp, OUT)
    print("v2 已写: %s（%d 条）" % (OUT, len(items)))

    dist = Counter(i["category"] for i in items)
    print("v2 类别分布:", dict(dist))
    dist_c = Counter(r["category"].strip() for r in kept)
    print("转正 64 条类别分布:", dict(dist_c))

    with open(MAP, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["q_id", "处置", "理由"])
        for r in rows:
            qid = r["q_id"].strip()
            if qid in A_LEVEL:
                w.writerow([qid, "剔除", A_REASON])
            elif qid in INTERNAL:
                w.writerow([qid, "剔除", INTERNAL_REASON[qid]])
            else:
                w.writerow([qid, "保留", "转入 v2（excerpt_verified=%s）" % r["_excerpt_verified"]])
    print("去重对照表: %s" % MAP)
    print("T22_OK")


if __name__ == "__main__":
    sys.exit(main())
