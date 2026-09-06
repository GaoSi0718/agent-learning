"""
W6 成本实验室：亲手感受 Token 与时间的消耗
=========================================
设计原则：**默认离线运行，不调用任何 API，不花一分钱。**
（唯一例外是文档实验 7 的 usage 检查，需自行另写脚本并设好预算上限。）

四个实验：
  count     数一数文件/图片值多少 token，建立数量级直觉
  snowball  复现"多轮对话滚雪球"曲线，看平方增长
  ab        全文塞入 vs Top-k 检索 的 token 对比（核心实验，服务 W6）
  parallel  串行 vs 并行，理解"时间"维度的优化

用法：
  python w6_cost_lab.py count --file w6_sample_policy.txt
  python w6_cost_lab.py count --image example.jpg
  python w6_cost_lab.py snowball --rounds 20 --per-round 2000
  python w6_cost_lab.py ab --max-q 10 --k 3
  python w6_cost_lab.py parallel --tasks 5 --sleep 1

依赖：纯标准库。装了 tiktoken 会自动切换到精确计数，没装则用经验值估算
      （估算结果在输出中带 [估算] 标记，量级正确，不要拿去精确算钱）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
_CJK = re.compile(r"[\u4e00-\u9fff]")

# ── Token 计数 ────────────────────────────────────────────────
try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> tuple[int, str]:
        return len(_ENC.encode(text)), "tiktoken 精确"

except Exception:  # 没装 tiktoken / 离线无缓存 → 回退估算
    def count_tokens(text: str) -> tuple[int, str]:
        cjk = len(_CJK.findall(text))
        other = len(text) - cjk
        return int(cjk * 1.2 + other / 4), "估算"


def read_text(path: str) -> str:
    p = Path(path)
    raw = p.read_bytes()
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore")


# ── 图片尺寸与视觉 token 估算 ─────────────────────────────────
def image_size(path: str) -> tuple[int, int] | None:
    """纯标准库读取 PNG / JPEG 尺寸，避免依赖 Pillow。"""
    p = Path(path)
    head = p.read_bytes()[:64]
    if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    if head.startswith(b"\xff\xd8"):  # JPEG
        data = p.read_bytes()
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                h = int.from_bytes(data[i + 5 : i + 7], "big")
                w = int.from_bytes(data[i + 7 : i + 9], "big")
                return w, h
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = int.from_bytes(data[i + 2 : i + 4], "big")
            i += 2 + seg
    return None


def vision_tokens(w: int, h: int) -> tuple[int, int, int]:
    """
    返回 (缩放后宽, tile 数, 估算 token)。
    简化模型（参考 GPT-4o 一类方案的公开规则，各家差异很大，仅作量级参考）：
      1) 最长边缩到 ≤2048，短边缩到 ≤768（保持比例）
      2) 按 512x512 切块
      3) token ≈ 85 + 170 * tile 数
    """
    scale = min(2048 / max(w, h), 768 / min(w, h), 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    tiles = -(-nw // 512) * -(-nh // 512)  # ceil 除法
    return nw, tiles, 85 + 170 * tiles


# ── 实验 1：count ─────────────────────────────────────────────
def cmd_count(args):
    if args.image:
        size = image_size(args.image)
        if size is None:
            print(f"[跳过] 无法解析图片尺寸（只支持 PNG/JPEG）：{args.image}")
            print("       如果确定尺寸，可装 Pillow 后重试：pip install pillow")
            return
        w, h = size
        nw, tiles, tok = vision_tokens(w, h)
        print(f"图片: {Path(args.image).name}")
        print(f"  原始尺寸:    {w} x {h}")
        print(f"  缩放后尺寸:  {nw} x {round(h * nw / w)}")
        print(f"  估算 tile 数: {tiles}      → 约 {tok:,} token  [估算]")
        if args.target_width and args.target_width < w:
            tw = args.target_width
            th = round(h * tw / w)
            _, t2, tok2 = vision_tokens(tw, th)
            save = (1 - tok2 / tok) * 100
            print(f"  若上传前先缩到 {tw}px 宽 ({tw} x {th}):")
            print(f"  估算 tile 数: {t2}      → 约 {tok2:,} token  [估算]")
            print(f"  节省: {save:.1f}%")
        print("\n  提示: 视觉 token 规则各家模型不同，精确值请看 API 返回的 usage。")
        return

    text = read_text(args.file)
    n, mode = count_tokens(text)
    print(f"文件: {Path(args.file).name}")
    print(f"  字符数:   {len(text):,}")
    print(f"  token 数: {n:,}  [{mode}]")
    print(f"  参考: 相当于约 {n / 750:.1f} 页 A4 纯文本（按每页约 750 token 折算）")
    print(f"  若每次提问都全文塞入，问 50 个问题 = {n * 50:,} token")


# ── 实验 2：snowball ──────────────────────────────────────────
def cmd_snowball(args):
    per, rounds, window, summary = args.per_round, args.rounds, args.window, args.summary
    print(f"假设：每轮新增 {per:,} token；窗口策略保留最近 {window} 轮 + {summary} token 摘要\n")
    print(f"{'轮次':>4}  {'全量(本轮)':>12}  {'全量(累计)':>12}  {'窗口(本轮)':>12}  {'窗口(累计)':>12}")
    print("-" * 62)
    full_cum = win_cum = 0
    for n in range(1, rounds + 1):
        f = per * n
        w = summary + min(n, window) * per
        full_cum += f
        win_cum += w
        if rounds <= 20 or n in (1, 2, 3, 5, 10, 15, 20) or n == rounds:
            print(f"{n:>4}  {f:>12,}  {full_cum:>12,}  {w:>12,}  {win_cum:>12,}")
    save = (1 - win_cum / full_cum) * 100
    print("-" * 62)
    print(f"\n结论：{rounds} 轮后，全量历史累计 {full_cum:,} token，"
          f"窗口策略 {win_cum:,} token，节省 {save:.1f}%")
    print("关键：全量历史的曲线是『平方增长』——轮次翻倍，总消耗接近四倍。")


# ── 实验 3：ab（全文 vs 检索）────────────────────────────────
_INSTR_FULL = "你是公司 HR 政策助手。仅依据以下政策全文回答，不要编造、不要补充文档外信息。\n\n"
_INSTR_RAG = "你是公司 HR 政策助手。仅依据以下政策片段回答，不要编造、不要补充片段外信息。\n\n"


def cmd_ab(args):
    try:
        from w6_rag_retriever import PolicyRetriever
    except ImportError as e:
        print(f"[错误] 无法导入检索器：{e}")
        print("       请把本脚本放在项目根目录（与 w6_rag_retriever.py 同级）后重试。")
        return

    set_path = HERE / "w6_eval_set.json"
    if not set_path.exists():
        print(f"[错误] 找不到评估集：{set_path}")
        return
    data = json.loads(set_path.read_text(encoding="utf-8"))
    if args.max_q:
        data = data[: args.max_q]

    r = PolicyRetriever(str(HERE / "policy_context.txt"))
    print(f"[检索器] 已索引 {len(r.chunks)} 个片段，来源: {r.policy_path.name}")

    full_text = r.policy_path.read_text(encoding="utf-8")
    base_full, _ = count_tokens(_INSTR_FULL + full_text)
    if base_full < 2000:
        print("[提醒] 当前政策文件较小，全文塞入的绝对成本本来就低，节省比例的参考价值有限。")
        print("       把真实 HR 政策粘贴进 policy_context.txt 后重跑，差距会明显放大。")

    rows, rag_total = [], 0
    for item in data:
        q = item["question"]
        ctx = r.build_context(q, k=args.k)
        rag_tokens, _ = count_tokens(_INSTR_RAG + ctx + f"\n\n问题：{q}\n答案：")
        full_tokens = base_full + count_tokens(f"\n\n问题：{q}\n答案：")[0]
        rag_total += rag_tokens
        rows.append((item.get("id", "?"), q, full_tokens, rag_tokens))

    n = len(rows)
    full_total = sum(x[2] for x in rows)
    print(f"\n问题数: {n}    k={args.k}\n")
    print(f"{'方案':<16}{'平均 prompt token':>20}{'总计':>14}{'相对全文':>12}")
    print("-" * 62)
    print(f"{'全文塞入':<14}{full_total // n:>20,}{full_total:>14,}{100.0:>11.1f}%")
    print(f"{'Top-' + str(args.k) + ' 检索':<14}{rag_total // n:>20,}{rag_total:>14,}"
          f"{rag_total / full_total * 100:>11.1f}%")
    save = (1 - rag_total / full_total) * 100
    print("-" * 62)
    ratio = full_total / rag_total if rag_total else 0
    print(f"\n节省: {save:.1f}%  (约 {ratio:.1f} 倍)")

    print("\n各题明细（前 5 条）:")
    for qid, q, f, g in rows[:5]:
        print(f"  {qid} 全文 {f:,} → 检索 {g:,}  (省 {(1 - g / f) * 100:.1f}%)  {q[:20]}")

    print("\n要点：检索方案的体积与文档总长无关，只与 k 和片段长度有关。")
    print("      试试 --k 1 / --k 3 / --k 5，观察 token 与 k 的线性关系。")


# ── 实验 4：parallel ──────────────────────────────────────────
def cmd_parallel(args):
    tasks, sleep_s = args.tasks, args.sleep
    print(f"模拟 {tasks} 个独立任务，每个耗时 {sleep_s:.2f} 秒\n")

    t0 = time.perf_counter()
    for _ in range(tasks):
        time.sleep(sleep_s)
    serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=tasks) as ex:
        list(ex.map(lambda _: time.sleep(sleep_s), range(tasks)))
    parallel = time.perf_counter() - t0

    print(f"串行执行: {serial:.2f} 秒")
    print(f"并行执行: {parallel:.2f} 秒   (线程数 {tasks})")
    print(f"加速比:   {serial / parallel:.1f}x")
    print("\n注意: 并行不改变 token 总量 —— 它省的是时间，不是钱。")


def main():
    ap = argparse.ArgumentParser(description="W6 成本实验室（离线可跑，零 API 成本）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("count", help="数一数文件/图片值多少 token")
    p1.add_argument("--file", help="要统计的文本文件路径")
    p1.add_argument("--image", help="要估算的 PNG/JPEG 图片路径")
    p1.add_argument("--target-width", type=int, default=512,
                    help="图片对比用的目标宽度（默认 512，传 0 关闭）")
    p1.set_defaults(func=cmd_count)

    p2 = sub.add_parser("snowball", help="复现多轮对话的 token 滚雪球曲线")
    p2.add_argument("--rounds", type=int, default=20, help="对话轮次")
    p2.add_argument("--per-round", type=int, default=2000, help="每轮新增 token")
    p2.add_argument("--window", type=int, default=5, help="窗口策略保留最近 N 轮")
    p2.add_argument("--summary", type=int, default=800, help="摘要的固定 token 开销")
    p2.set_defaults(func=cmd_snowball)

    p3 = sub.add_parser("ab", help="全文塞入 vs Top-k 检索 的 token 对比")
    p3.add_argument("--max-q", type=int, default=None, help="只跑前 N 条")
    p3.add_argument("--k", type=int, default=3, help="检索返回片段数")
    p3.set_defaults(func=cmd_ab)

    p4 = sub.add_parser("parallel", help="串行 vs 并行的时间对比")
    p4.add_argument("--tasks", type=int, default=5, help="任务数")
    p4.add_argument("--sleep", type=float, default=1.0, help="单任务模拟耗时（秒）")
    p4.set_defaults(func=cmd_parallel)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
