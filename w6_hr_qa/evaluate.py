"""
W6 HR 问答助手 · ④ 离线评测

评测三个维度：
  1. 检索命中率   —— 正确条款是否被检索到（考察切片 + 向量化质量）
  2. 答案准确率   —— 答案是否与参考答案一致（用 LLM 当裁判）
  3. 拒答正确率   —— 文档中没有的问题是否老实说"不知道"（防幻觉，最关键）

用法：
    python w6_hr_qa/evaluate.py              # 跑全部
    python w6_hr_qa/evaluate.py --limit 5    # 只跑前 5 题（快速验证）
"""
import json
import argparse
import time
from pathlib import Path

import config
from qa import QAChain

# 拒答标准话术（与 config.SYSTEM_PROMPT 中的约定保持一致）
REFUSAL_MARKER = "未查询到相关规定"


# ───────────────────────────────────────────────────────────
# LLM 裁判：判断答案是否与参考答案一致
# ───────────────────────────────────────────────────────────
JUDGE_PROMPT = """你是一个严格的评测裁判。判断【系统回答】是否准确回答了【用户问题】。

【参考答案】
{reference}

【用户问题】
{question}

【系统回答】
{answer}

【判定标准】
1. 系统回答的核心事实（数字、条件、流程）必须与参考答案一致
2. 参考答案中的关键信息不能缺失
3. 系统回答不能出现参考答案之外的事实性错误
4. 若系统回答是拒答（说未查询到），判为不一致

只输出一个 JSON，不要任何其他文字：
{{"correct": true或false, "reason": "一句话说明"}}
"""


def judge(chain: QAChain, question: str, reference: str, answer: str) -> dict:
    """用 LLM 判断答案正确性。"""
    from openai import OpenAI
    client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)

    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(
                question=question, reference=reference, answer=answer
            ),
        }],
        temperature=0,
        max_tokens=200,
    )
    raw = resp.choices[0].message.content.strip()

    # 容错：模型可能包 ```json ```
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"correct": False, "reason": f"裁判输出解析失败：{raw[:80]}"}


# ───────────────────────────────────────────────────────────
# 主流程
# ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 题")
    parser.add_argument("--no-judge", action="store_true", help="跳过 LLM 裁判（只测检索+拒答）")
    args = parser.parse_args()

    problems = config.check_config()
    if problems:
        print("❌ 配置有问题：")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        return

    # 读评测集
    if not config.EVAL_FILE.exists():
        print(f"❌ 评测集不存在：{config.EVAL_FILE}")
        return
    data = json.loads(config.EVAL_FILE.read_text(encoding="utf-8"))
    questions = data["questions"]
    if args.limit:
        questions = questions[:args.limit]

    try:
        chain = QAChain()
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    print("=" * 60)
    print(f"离线评测 · 共 {len(questions)} 题")
    print("=" * 60)

    results = {
        "answerable": {"total": 0, "retrieved": 0, "correct": 0},
        "unanswerable": {"total": 0, "correct_refusal": 0},
    }
    elapsed_list, cost_list = [], []

    for i, item in enumerate(questions, 1):
        q = item["question"]
        answerable = item["answerable"]
        print(f"\n[{i}/{len(questions)}] {q}")

        r = chain.ask(q, stream=False, verbose=False)
        answer = r["answer"]
        hits = r["hits"]
        elapsed_list.append(r["elapsed"])
        cost_list.append(r["cost"])

        if answerable:
            results["answerable"]["total"] += 1

            # ① 检索命中：命中正确条款号
            hit_articles = [h["article"] for h in hits]
            expected = item.get("expected_article")
            retrieved = expected in hit_articles if expected else len(hits) > 0
            if retrieved:
                results["answerable"]["retrieved"] += 1
            print(f"    检索: {'✅' if retrieved else '❌'} "
                  f"期望 {expected} | 命中 {hit_articles}")

            # ② 答案准确：LLM 裁判
            if args.no_judge:
                correct = None
                print("    答案: （--no-judge 已跳过）")
            else:
                j = judge(chain, q, item["reference"], answer)
                correct = j["correct"]
                if correct:
                    results["answerable"]["correct"] += 1
                print(f"    答案: {'✅' if correct else '❌'} {j['reason']}")

            # ③ 误拒答检查（有答案却拒答 = 严重问题）
            if REFUSAL_MARKER in answer:
                print("    ⚠️  误拒答！文档中有答案但系统拒答了")
        else:
            results["unanswerable"]["total"] += 1
            refused = REFUSAL_MARKER in answer
            if refused:
                results["unanswerable"]["correct_refusal"] += 1
            print(f"    拒答: {'✅ 正确拒答' if refused else '❌ 产生幻觉！'}")
            if not refused:
                print(f"    幻觉内容: {answer[:100]}...")

        print(f"    ⏱ {r['elapsed']}s | 🔤 {r['tokens']} tokens | 💰 ¥{r['cost']:.6f}")

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("评测结果汇总")
    print("=" * 60)

    a = results["answerable"]
    u = results["unanswerable"]

    print(f"\n【有答案题】{a['total']} 题")
    print(f"  检索命中率  : {a['retrieved']}/{a['total']} = {a['retrieved']/a['total']:.1%}")
    if not args.no_judge:
        print(f"  答案准确率  : {a['correct']}/{a['total']} = {a['correct']/a['total']:.1%}")

    if u["total"]:
        print(f"\n【无答案题（防幻觉）】{u['total']} 题")
        print(f"  正确拒答率  : {u['correct_refusal']}/{u['total']} = "
              f"{u['correct_refusal']/u['total']:.1%}")

    # 综合分：检索 30% + 答案 40% + 拒答 30%
    if args.no_judge:
        composite = (a['retrieved'] / a['total'] * 0.45
                     + u['correct_refusal'] / u['total'] * 0.55 if u['total'] else 0)
    else:
        composite = (a['retrieved'] / a['total'] * 0.30
                     + a['correct'] / a['total'] * 0.40
                     + (u['correct_refusal'] / u['total'] * 0.30 if u['total'] else 0.30))
    print(f"\n  综合得分    : {composite:.1%}")

    print(f"\n  平均响应    : {sum(elapsed_list)/len(elapsed_list):.2f}s")
    print(f"  平均成本    : ¥{sum(cost_list)/len(cost_list):.6f}/次")
    print(f"  本次评测总花费: ¥{sum(cost_list):.4f}")

    # ── 保存结果 ──
    out_file = config.BASE_DIR / "eval" / f"result_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_questions": len(questions),
        "results": results,
        "composite_score": round(composite, 4),
        "avg_elapsed": round(sum(elapsed_list) / len(elapsed_list), 2),
        "avg_cost": round(sum(cost_list) / len(cost_list), 6),
        "total_cost": round(sum(cost_list), 4),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  结果已保存: {out_file}")

    print("\n" + "─" * 60)
    print("⚠️  说明：本评测集仅 20 题，样本偏小，不足以支撑强结论。")
    print("   写在简历上请注明「内部评测集 20 题」。")
    print("   真实上线后必须收「在线采纳率」（用户点有用/没用）才是硬指标。")


if __name__ == "__main__":
    main()
