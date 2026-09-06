# -*- coding: utf-8 -*-
# tools/gen_eval_candidates.py
"""Z4：80 条评测集候选池生成流水线（素材池，非正式评测集——不碰 w6_eval_* 迪莫属主文件）。
流程：
  1) 复用 w6_rag_retriever.PolicyRetriever 的分块（只读不改，得 151 chunks）；
  2) 过滤过短(<80字)与表格类 chunk，按关键词本地归类 5 类（零 API 成本）；
  3) 阶段一：每 chunk 调 DeepSeek 生成 0-1 题（严格 JSON；答案必须忠实条款，不得外推）；
  4) 阶段二（定向补齐）：不足 12 题的类别，用 BM25 定向召回同主题 chunk（≥40 字）打包
     成 packet（≤2 块/包），每包生成至多 2 题——清单「按 category 过滤 chunk 定向补生成」；
  5) 本地反幻觉校验：答案中一切数字必须能在语料全文找到，否则整题丢弃；
  6) 按类别均衡抽样输出 notes/eval_expansion/candidates_80.csv（≥80 行，5 类每类 ≥10）。
断点续传：每次调用结果追加写 _gen_log.jsonl，重跑自动跳过已完成单元。
成本控制：max_tokens=450、入 prompt 文本截断 ≤1200 字；token 用量逐条记录。
用法：
  venv\\Scripts\\python.exe tools\\gen_eval_candidates.py --dry-run   # 只看过滤统计，不调 API
  venv\\Scripts\\python.exe tools\\gen_eval_candidates.py             # 正式生成
"""
import argparse, csv, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                      # noqa: E402
from w6_rag_retriever import PolicyRetriever        # noqa: E402 (只读复用，不修改)

load_dotenv(ROOT / ".env")

OUT_DIR = ROOT / "notes" / "eval_expansion"
LOG_PATH = OUT_DIR / "_gen_log.jsonl"
CSV_PATH = OUT_DIR / "candidates_80.csv"
CATEGORIES = ["加班", "试用期", "年休假", "考勤与请假", "薪酬与社保"]
_CAT_QUERIES = {   # 阶段二 BM25 定向召回用查询词
    "加班": ["加班 加班费", "加班费 支付", "延时工作"],
    "试用期": ["试用期", "试用期 转正", "试用期 解除"],
    "年休假": ["年休假", "年假 安排", "带薪年休假"],
    "考勤与请假": ["请假", "考勤 迟到", "病假 事假"],
    "薪酬与社保": ["工资 发放", "社保 保险", "公积金 福利", "薪酬 绩效"],
}

_RULES = [
    ("加班", ("加班", "加班费", "延时", "值班")),
    ("试用期", ("试用期", "转正", "录用条件")),
    ("年休假", ("年休假", "年假")),
    ("考勤与请假", ("考勤", "请假", "病假", "事假", "迟到", "早退", "旷工", "打卡", "休假", "作息", "工时")),
    ("薪酬与社保", ("工资", "薪酬", "薪资", "社保", "保险", "公积金", "绩效", "奖金", "福利", "调薪", "发放")),
]

def classify(text: str) -> str:
    for cat, kws in _RULES:
        if any(k in text for k in kws):
            return cat
    return "其他"

def is_table_like(text: str) -> bool:
    if text.count("|") >= 3:
        return True
    digits = sum(ch.isdigit() for ch in text)
    return len(text) > 0 and digits / len(text) > 0.4

def load_state():
    done = {}
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                done[rec["unit_id"]] = rec
            except Exception:
                pass
    return done

def make_client():
    from openai import OpenAI
    from w6_hr_policy.app.config import API_TIMEOUT
    return OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                  base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                  timeout=API_TIMEOUT)

PROMPT_ONE = """你是严谨的评测题生成器。依据以下公司 HR 政策条款片段，出一道员工可能真实提问的问题与参考答案。
硬性要求：
1. 问题口语化，像员工向 HR 提问；
2. 参考答案必须且只能依据片段原文，不得外推、不得补充片段外知识；
3. 答案中出现的一切数字必须来自片段原文，一个都不能编；
4. 类别只能取：{cats}；
5. 只输出一个 JSON 对象（禁止 markdown 代码块、禁止解释）：
   {{"question": "...", "answer": "...", "category": "..."}}
6. 若片段不适合出题（无实质规则、目录、签名、与 HR 无关），输出：{{"skip": true}}

条款片段（chunk_id={cid}）：
{chunk}"""

PROMPT_PACK = """你是严谨的评测题生成器。以下是同一主题（{cat}）的若干公司 HR 政策条款片段，请最多出 {n} 道员工可能真实提问的问题与参考答案（能出几道出几道，但不得凑数）。
硬性要求：
1. 问题口语化，像员工向 HR 提问；多道题之间角度必须明显不同；
2. 每道题的参考答案必须且只能依据片段原文，不得外推、不得补充片段外知识；
3. 答案中出现的一切数字必须来自片段原文，一个都不能编；
4. 只输出一个 JSON 数组（禁止 markdown 代码块、禁止解释），元素形如：
   {{"question": "...", "answer": "...", "category": "{cat}"}}

条款片段（chunk_id={cid}）：
{chunk}"""

def call_llm(client, model, prompt):
    from w6_hr_policy.app.resilience import call_with_retry
    trace = []
    r = call_with_retry(
        client.chat.completions.create,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=450, temperature=0.3,
        max_attempts=2, backoff=(3,), trace=trace)
    content = r.choices[0].message.content or ""
    usage = getattr(r, "usage", None)
    return content, {"prompt_tokens": getattr(usage, "prompt_tokens", 0),
                     "completion_tokens": getattr(usage, "completion_tokens", 0)}

def parse_json(content):
    content = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.M).strip()
    m = re.search(r"\[.*\]|\{.*\}", content, flags=re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    return data if isinstance(data, list) else [data]

def valid_qa(obj, corpus):
    """返回 (record, reason)：通过硬校验返回 (record, None)。"""
    q, a, c = ((obj.get("question") or "").strip(), (obj.get("answer") or "").strip(),
               (obj.get("category") or "").strip())
    if obj.get("skip") or not q or not a:
        return None, "skip_or_empty"
    if c not in CATEGORIES:
        return None, "bad_category"
    if len(q) > 60 or len(a) > 400:
        return None, "too_long"
    nums = re.findall(r"\d+(?:\.\d+)?", a)
    bad = [x for x in nums if x not in corpus]
    if bad:
        return None, f"hallucinated_numbers:{bad}"
    return {"question": q, "answer": a, "category": c}, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--target", type=int, default=84)
    ap.add_argument("--cov-thresh", type=float, default=0.35,
                    help="答案-源块 bigram 覆盖率阈值（默认 0.35：Fabricated≈0.1 与忠实转述≈0.4+ 之间的分界）")
    ap.add_argument("--report-cov", action="store_true",
                    help="只本地统计每题覆盖率分布（不调 API），用于校准阈值")
    args = ap.parse_args()

    retriever = PolicyRetriever()
    corpus = retriever.policy_path.read_text(encoding="utf-8")
    chunks = retriever.chunks
    print(f"[分块] 复用 PolicyRetriever：{len(chunks)} chunks，语料 {len(corpus)} 字")

    eligible = []       # 阶段一：(unit_id, chunk_text, category)
    for i, c in enumerate(chunks):
        if len(c.strip()) < 80 or is_table_like(c):
            continue
        cat = classify(c)
        if cat == "其他":
            continue                     # 5 类之外的 chunk 不烧 API
        eligible.append((f"chunk_{i:03d}", c, cat))
    from collections import Counter, defaultdict
    dist = Counter(cat for _, _, cat in eligible)
    print(f"[过滤] 阶段一可出题 chunk {len(eligible)} 个；类别分布：{dict(dist)}")
    if args.dry_run:
        # 阶段二召回预估
        for cat, qs in _CAT_QUERIES.items():
            pool = set()
            for q in qs:
                for t, _s in retriever.retrieve(q, k=20):
                    idx = chunks.index(t)
                    if len(t.strip()) >= 40 and not is_table_like(t):
                        pool.add(idx)
            print(f"  [召回预估] {cat}: {len(pool)} chunks")
        return

    state = load_state()
    tokens = {"prompt_tokens": 0, "completion_tokens": 0}
    valid = {}          # unit_id -> [record, ...]
    for uid, rec in state.items():
        if rec.get("records"):
            valid[uid] = rec["records"]
        tokens["prompt_tokens"] += rec.get("usage", {}).get("prompt_tokens", 0)
        tokens["completion_tokens"] += rec.get("usage", {}).get("completion_tokens", 0)

    client, model = make_client(), os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    print(f"[模型] {model} @ {os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def run_unit(unit_id, prompt, fallback_cat):
        """调一次 API：解析、硬校验、断点落盘。返回新增有效题数。"""
        rec = {"unit_id": unit_id}
        try:
            content, usage = call_llm(client, model, prompt)
            rec["usage"] = usage
            tokens["prompt_tokens"] += usage["prompt_tokens"]
            tokens["completion_tokens"] += usage["completion_tokens"]
            objs = parse_json(content) or []
            records = []
            reasons = []
            for o in objs:
                r, why = valid_qa(o if isinstance(o, dict) else {}, corpus)
                if r:
                    records.append(r)
                elif why != "skip_or_empty":
                    reasons.append(why)
            if records:
                rec["records"] = records
                valid[unit_id] = records
            else:
                rec["reason"] = reasons[0] if reasons else "all_skip"
        except Exception as e:
            rec["reason"] = f"api_error:{type(e).__name__}"
            rec["usage"] = {"prompt_tokens": 0, "completion_tokens": 0}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        got = len(valid.get(unit_id, []))
        print(f"  {unit_id} → 有效 {got} {rec.get('reason', '')}"
              f"  [累计 tokens in/out={tokens['prompt_tokens']}/{tokens['completion_tokens']}]")
        return got

    # ── 阶段一：每 chunk 0-1 题 ──
    todo1 = [(uid, c, cat) for uid, c, cat in eligible if uid not in state]
    print(f"[阶段一] 待跑 {len(todo1)}（已完成 {len([u for u,_,_ in eligible if u in state])}）")
    for uid, c, cat in todo1:
        run_unit(uid, PROMPT_ONE.format(cats="|".join(CATEGORIES), cid=uid, chunk=c[:900]), cat)

    def count_cat(cat):
        return sum(len(v) for uid, v in valid.items() if v and v[0]["category"] == cat)

    # ── 阶段二：不足 12 题的类别定向补生成 ──
    print("[阶段二] 定向补齐（目标每类 ≥12）")
    for cat in CATEGORIES:
        have = count_cat(cat)
        if have >= 12:
            print(f"  {cat}: 已有 {have} 题，跳过")
            continue
        # BM25 定向召回（含较短块 ≥40 字），按 chunk 序号稳定排序
        pool = set()
        for q in _CAT_QUERIES[cat]:
            for t, _s in retriever.retrieve(q, k=20):
                idx = chunks.index(t)
                if len(t.strip()) >= 40 and not is_table_like(t):
                    pool.add(idx)
        used_units = {u for u in valid if u.startswith("pack_")}
        n = 0
        print(f"  {cat}: 已有 {have} 题，召回 {len(pool)} chunks，开始补齐")
        for i in sorted(pool):
            if count_cat(cat) >= 12:
                break
            for j in (i + 1,):            # 两块一包，不足单块也行
                unit_id = f"pack_{cat}_{i:03d}"
                if unit_id in state:
                    continue
                text = "\n".join(chunks[k] for k in (i, j) if k < len(chunks))[:1200]
                got = run_unit(unit_id, PROMPT_PACK.format(cat=cat, n=2, cid=f"chunk_{i:03d}+chunk_{j:03d}", chunk=text), cat)
                n += 1
                if n >= 15:               # 单类补包上限，控成本
                    break
            if n >= 15:
                print(f"  {cat}: 达到补包上限 15，停止（当前 {count_cat(cat)} 题）")
                break
        print(f"  {cat}: 补齐后 {count_cat(cat)} 题")

    # ── 忠实度/类别一致性过滤（本地，零 API；人工抽检发现的两种坏题都要拦） ──
    # 坏题 A：答案忠实但类别错标（公司简介块被 BM25 召回进「年休假」包）→ 关键词不一致
    # 坏题 B：源块是目录行，答案外推细节（无数字逃过反幻觉校验）→ bigram 覆盖率过低
    _REVIEW_KWS = dict(_RULES)
    _REVIEW_KWS["考勤与请假"] = _REVIEW_KWS["考勤与请假"] + ("婚假", "产假", "产检", "丧假", "调休", "放假", "假期")

    def chunk_union(uid):
        """该出题单元实际携带的源块集合：阶段二两块包兼容（i 与 i+1）。"""
        m = re.search(r"(\d+)$", uid.split("+")[0])
        if not m:
            return ""
        i = int(m.group(1))
        parts = [chunks[i]]
        if uid.startswith("pack_") and i + 1 < len(chunks):
            parts.append(chunks[i + 1])
        return "\n".join(parts)

    def bigram_cov(text, ref):
        t = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", text)
        if len(t) < 2:
            return 1.0
        gs = [t[i:i + 2] for i in range(len(t) - 1)]
        return sum(1 for g in gs if g in ref) / len(gs)

    def _strip_boilerplate(ans):
        """剥掉开场套话与「片段未提及」类让步句，返回 (剩余文本, 是否纯拒答)。
        纯拒答（剥完几乎不剩字）是合法的负样本题，豁免覆盖率过滤；
        「先编造规则再补一句未提及」的混合体不豁免（编造内容仍在剩余文本里参与判定）。"""
        ans = re.sub(r"^(根据|按照|依据)[条款规定]{1,6}[,，：:]?", "", ans.strip())
        clauses = [c for c in re.split(r"[。；！？\n]", ans) if c.strip()]
        keep = [c for c in clauses if ("片段" not in c and "原文" not in c)]
        stripped = "。".join(keep)
        return stripped, len(re.sub(r"\s", "", stripped)) < 20

    def build_flat():
        out = []
        for uid, records in valid.items():
            ref = chunk_union(uid)
            for r in records:
                stripped, pure_refusal = _strip_boilerplate(r["answer"])
                if pure_refusal:
                    out.append((uid, r))     # 拒答型负样本：不参与忠实度/关键词过滤
                    continue
                kws = _REVIEW_KWS[r["category"]]
                # 类别一致性：Q+A 与源块三处都无类别关键词才判错标
                # （防「公司简介块标成年休假」；同时不误杀不含关键词的合法问法）
                kw_hit = any(k in r["question"] + r["answer"] for k in kws)
                if not kw_hit and not (ref and any(k in ref for k in kws)):
                    continue
                # 忠实度：答案（剥套话后）与源块 bigram 覆盖率
                if ref and bigram_cov(stripped, ref) < args.cov_thresh:
                    continue
                out.append((uid, r))
        return out

    if args.report_cov:
        rows = []
        for uid, records in valid.items():
            ref = chunk_union(uid)
            for r in records:
                stripped, pure_refusal = _strip_boilerplate(r["answer"])
                cov = bigram_cov(stripped, ref) if ref else -1.0
                rows.append((cov, uid, r["category"], r["question"]))
        rows.sort()
        for cov, uid, cat, q in rows:
            print(f"{cov:.2f}  {uid:22s} {cat:6s} {q[:38]}")
        return

    flat = build_flat()
    print(f"[过滤] 忠实度/类别一致性过滤后剩 {len(flat)} 题")

    # ── 补齐循环：过滤后总量 <target 或某类 <12（留缓冲）时轮转各类别补包 ──
    # 池子按类别关键词硬门槛（_REVIEW_KWS）：杜绝公司简介/转正流程块混进「年休假」包
    # ——这是早前「答案忠实但类别错标」坏题的根因。
    pools = {}
    for cat in CATEGORIES:
        pool = set()
        for q in _CAT_QUERIES[cat]:
            for t, _s in retriever.retrieve(q, k=25):
                idx = chunks.index(t)
                if (len(t.strip()) >= 40 and not is_table_like(t)
                        and any(k in t for k in _REVIEW_KWS[cat])):
                    pool.add(idx)
        pools[cat] = sorted(pool)
    print("[补齐池] " + ", ".join(f"{c}:{len(pools[c])}" for c in CATEGORIES))
    extra_calls = 0
    def need_more():
        d = Counter(r["category"] for _, r in flat)
        return len(flat) < args.target or any(d.get(c, 0) < 12 for c in CATEGORIES)
    while need_more() and extra_calls < 25:
        progressed = False
        d = Counter(r["category"] for _, r in flat)
        # 优先补最薄、且距 12 最远的类别
        for cat in sorted(CATEGORIES, key=lambda c: d.get(c, 0)):
            if not need_more():
                break
            for i in pools[cat]:
                unit_id = f"pack_{cat}_{i:03d}"
                if unit_id in state:
                    continue
                state[unit_id] = {"unit_id": unit_id, "placeholder": True}   # 防本轮重跑
                run_unit(unit_id, PROMPT_PACK.format(cat=cat, n=2,
                          cid=f"chunk_{i:03d}", chunk=chunks[i][:1200]), cat)
                extra_calls += 1
                progressed = True
                break
        flat = build_flat()
        if not progressed:
            print("  [补齐] 各类别无新包可跑，提前结束")
            break
    print(f"[补齐] 额外 {extra_calls} 次调用；过滤后总量 {len(flat)}，"
          f"分布 {dict(Counter(r['category'] for _, r in flat))}")

    # ── 均衡抽样出 CSV（flat 已过滤；每类 ≤17 先取，不足再从各类剩余补到 target） ──
    per_cat = defaultdict(list)
    for uid, r in flat:
        per_cat[r["category"]].append((uid, r))
    picked, used_units = [], set()
    for cat in CATEGORIES:
        for uid, r in per_cat[cat][:17]:
            picked.append((uid, r)); used_units.add(uid)
    if len(picked) < 80:
        for cat in CATEGORIES:
            for uid, r in per_cat[cat][17:]:
                if len(picked) >= args.target:
                    break
                picked.append((uid, r)); used_units.add(uid)
            if len(picked) >= args.target:
                break
    picked.sort(key=lambda ur: (CATEGORIES.index(ur[1]["category"]), ur[0]))

    def excerpt_of(uid):
        """取该单元第一个 chunk 的最长行（必然是语料连续子串），≤200 字。
        uid 两种形态：chunk_025 / pack_加班_020——统一按尾部数字解析 chunk 序号。"""
        part = uid.split("+")[0]
        m = re.search(r"(\d+)$", part)
        if not m:
            return ""
        return max(chunks[int(m.group(1))].split("\n"), key=len)[:200]

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["q_id", "question", "reference_answer", "source_chunk_id",
                    "source_excerpt", "category", "proposed_by"])
        for i, (uid, r) in enumerate(picked, 1):
            w.writerow([f"cand-{i:03d}", r["question"], r["answer"], uid,
                        excerpt_of(uid), r["category"], "zcode+deepseek-chat(20260907)"])

    final_dist = Counter(r["category"] for _, r in picked)
    print("\n[汇总] 有效单元 {}，CSV 数据行 {}；类别分布：{}".format(
        len(valid), len(picked), dict(final_dist)))
    print(f"[成本] 累计 tokens：in={tokens['prompt_tokens']} out={tokens['completion_tokens']}"
          f"（成本估算见 README，以 DeepSeek 官网价格为准）")

if __name__ == "__main__":
    main()
