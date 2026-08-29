"""
W6 HR 问答助手 · ② RAG 问答核心

流程：问题 → 向量化 → Chroma 检索 top-k → 组装 Prompt → DeepSeek 生成 → 带引用返回

用法：
    python w6_hr_qa/qa.py                      # 交互式问答
    python w6_hr_qa/qa.py "年假有几天？"        # 单条问答
"""
import sys
import time
from pathlib import Path

import config
from ingest import Embedder

from openai import OpenAI


# ───────────────────────────────────────────────────────────
# 检索器
# ───────────────────────────────────────────────────────────
class PolicyRetriever:
    """从 Chroma 检索最相关的制度片段。"""

    def __init__(self):
        import chromadb
        from chromadb.config import Settings

        self.embedder = Embedder()
        self.client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        try:
            self.collection = self.client.get_collection("hr_policies")
        except Exception:
            raise RuntimeError(
                f"向量库不存在或为空，请先运行：python {Path(__file__).name.replace('qa.py','ingest.py')}"
            )

    def retrieve(self, question: str, top_k: int = None) -> list:
        """
        返回 [{"text", "source", "article", "score"}, ...]
        score 为余弦相似度（0-1，越大越相似）
        """
        top_k = top_k or config.TOP_K
        q_vec = self.embedder.embed([question])[0]

        res = self.collection.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        results = []
        for i in range(len(res["documents"][0])):
            # Chroma 用 cosine 空间时 distance = 1 - similarity
            similarity = 1 - res["distances"][0][i]
            if similarity < config.SIMILARITY_THRESHOLD:
                continue
            results.append({
                "text": res["documents"][0][i],
                "source": res["metadatas"][0][i].get("source", "未知"),
                "article": res["metadatas"][0][i].get("article", ""),
                "score": round(similarity, 4),
            })
        return results


# ───────────────────────────────────────────────────────────
# 问答链
# ───────────────────────────────────────────────────────────
class QAChain:
    """检索 + 生成，带引用溯源和成本统计。"""

    def __init__(self):
        self.retriever = PolicyRetriever()
        self.llm = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.total_cost = 0.0

    def _build_context(self, hits: list) -> str:
        """把检索结果组装成带编号的上下文（便于模型引用）。"""
        parts = []
        for i, h in enumerate(hits, 1):
            label = f"《{h['source']}》"
            if h["article"]:
                label += f" · {h['article']}"
            parts.append(f"[{i}] 来源：{label}\n{h['text']}\n")
        return "\n".join(parts)

    def ask(self, question: str, stream: bool = False, verbose: bool = True) -> dict:
        """
        返回 {"answer", "hits", "elapsed", "tokens", "cost"}
        """
        t0 = time.time()

        # ① 检索
        hits = self.retriever.retrieve(question)

        # ② 无命中 → 直接拒答（不调 LLM，省成本）
        if not hits:
            return {
                "answer": "根据现有制度文档，未查询到相关规定，建议联系人资部确认。",
                "hits": [],
                "elapsed": round(time.time() - t0, 2),
                "tokens": 0,
                "cost": 0.0,
            }

        context = self._build_context(hits)
        messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT.format(context=context)},
            {"role": "user", "content": question},
        ]

        # ③ 生成
        if stream:
            chunks = []
            resp = self.llm.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
                stream=True,
            )
            answer_parts = []
            for chunk in resp:
                delta = chunk.choices[0].delta.content or ""
                answer_parts.append(delta)
                if verbose:
                    print(delta, end="", flush=True)
            if verbose:
                print()
            answer = "".join(answer_parts)
            # 流式无 usage，粗估：中文 1 字 ≈ 0.6 token
            est_prompt = len(context + question) * 0.6
            est_completion = len(answer) * 0.6
        else:
            resp = self.llm.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
            )
            answer = resp.choices[0].message.content
            est_prompt = resp.usage.prompt_tokens
            est_completion = resp.usage.completion_tokens

        cost = (est_prompt / 1000 * config.LLM_PRICE["prompt"]
                + est_completion / 1000 * config.LLM_PRICE["completion"])
        self.total_cost += cost

        return {
            "answer": answer,
            "hits": hits,
            "elapsed": round(time.time() - t0, 2),
            "tokens": int(est_prompt + est_completion),
            "cost": round(cost, 6),
        }


def format_result(q: str, r: dict) -> str:
    """格式化输出（命令行用）。"""
    lines = [f"\n问题：{q}", "", f"回答：{r['answer']}"]

    if r["hits"]:
        lines.append("")
        lines.append("📚 引用来源：")
        for i, h in enumerate(r["hits"], 1):
            art = f" · {h['article']}" if h["article"] else ""
            lines.append(f"  {i}. {h['source']}{art}（相关度 {h['score']}）")

    lines.append("")
    lines.append(f"[耗时] {r['elapsed']}s | [Token] {r['tokens']} | "
                 f"[花费] ¥{r['cost']:.6f}")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────
def main():
    problems = config.check_config()
    if problems:
        print("❌ 配置有问题：")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        sys.exit(1)

    try:
        chain = QAChain()
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 单条问答模式
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        r = chain.ask(q, stream=True)
        print(format_result(q, r))
        return

    # 交互模式
    print("=" * 55)
    print("HR 制度问答助手（输入 q 退出，输入 s 查看统计）")
    print("=" * 55)

    while True:
        try:
            q = input("\n❓ 你的问题 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not q:
            continue
        if q.lower() in ("q", "quit", "exit"):
            print("再见！")
            break
        if q.lower() == "s":
            print(f"本次会话累计花费：¥{chain.total_cost:.6f}")
            continue

        try:
            r = chain.ask(q, stream=True)
            print(format_result(q, r))
        except Exception as e:
            print(f"⚠️  出错了：{e}")

    print(f"\n本次会话累计花费：¥{chain.total_cost:.6f}")


if __name__ == "__main__":
    main()
