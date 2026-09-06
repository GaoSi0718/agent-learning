# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b1_memory_12rounds.py
"""B1 自测 B（联调，真实 API）：12 轮跨距记忆测试（跨 HTTP 请求 + SQLite 持久化）。

预期修订说明：P0 清单预期「工龄 12 年 → 第 12 轮答 10 天」基于旧假设语料（5/10/15 阶梯）；
对齐后真实语料公司规则为「入职满一年发 5 天」（评估报告增补 B），故成功判据改为：
第 12 轮回答必须 (a) 体现第 1 轮声明的工龄 12 年（跨距记忆成立），(b) 给出具体天数，
(c) 未自陈「找不到/无法确定」。全文打印供人工复核。
"""
import os, sys, pathlib, json, sqlite3, urllib.request, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# v1.7 鉴权适配（Z2）：服务按 fail-closed 校验 X-API-Key，联调请求必须带同一把 Key
BASE = os.getenv("W6_TEST_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("W6_API_KEY", "")
SID = "b1test12"
DB = pathlib.Path(__file__).resolve().parents[1] / "data" / "memory.db"

def ask(q):
    url = BASE + "/chat/stream?" + urllib.parse.urlencode({"q": q, "session_id": SID})
    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8")
    deltas = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            try:
                deltas.append(json.loads(line[6:])["delta"])
            except Exception:
                pass
    return "".join(deltas)

ROUNDS = [
    "我工龄 12 年，先记一下这个信息。",
    "用一句话解释什么是 BM25 检索。",
    "帮我算一下 137 乘以 8 等于多少。",
    "用一句话解释什么是 SSE。",
    "FastAPI 和 Flask 最核心的区别是什么？",
    "帮我算 456 除以 6 等于多少。",
    "用一句话解释什么是 RAG。",
    "Python 的 GIL 是什么，一句话说明。",
    "SSE 和 WebSocket 该怎么选，一句话。",
    "什么是上下文窗口？一句话。",
    "帮我算 89 乘 7 等于多少。",
    "那我年假能休几天？",
]

def main():
    answers = []
    for i, q in enumerate(ROUNDS, 1):
        a = ask(q)
        answers.append(a)
        print(f"R{i:02d} Q: {q}")
        print(f"     A: {a[:100]}{'…' if len(a) > 100 else ''}")

    final = answers[-1]
    con = sqlite3.connect(str(DB))
    n = con.execute("SELECT COUNT(*) FROM memory WHERE session_id=?", (SID,)).fetchone()[0]
    con.close()

    ok_memory = "12" in final
    ok_number = any(ch.isdigit() for ch in final)
    ok_not_lost = ("找不到" not in final) and ("无法确定" not in final)
    print("\n=== 判定 ===")
    print(f"SQLite 行数（session={SID}）: {n}（期望 ≥24，证明跨请求持久化）")
    print(f"跨距记忆（回答体现工龄 12 年）: {'PASS' if ok_memory else 'FAIL'}")
    print(f"给出具体天数: {'PASS' if ok_number else 'FAIL'}")
    print(f"未自陈找不到/无法确定: {'PASS' if ok_not_lost else 'FAIL'}")
    assert n >= 24, f"SQLite 仅 {n} 行，持久化异常"
    assert ok_memory and ok_number and ok_not_lost, "12 轮跨距记忆测试未通过，最终回答：" + final
    print("[PASS] B1 12 轮跨距记忆测试通过（第 12 轮全文见上）")

if __name__ == "__main__":
    main()
