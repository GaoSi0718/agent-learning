# -*- coding: utf-8 -*-
# w6_hr_policy/app/rag.py
"""BM25 检索封装：把项目根目录的 w6_rag_retriever.PolicyRetriever（151 chunks 版，
含查询同义词扩展与标题挂载分块，commit 634e49f）包成 async retrieve()，
供 tools.search_policy 使用。索引单例懒加载，进程内只建一次。"""
import asyncio, re, sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from w6_rag_retriever import PolicyRetriever  # noqa: E402

_retriever = None

def _get():
    global _retriever
    if _retriever is None:
        _retriever = PolicyRetriever()
    return _retriever

def _source_of(text: str) -> str:
    """从片段开头提取章节/条款号作为 source；取不到则如实标注。"""
    m = re.search(r"(\d+(?:\.\d+){1,2})", text[:80])
    if m:
        return f"章节 {m.group(1)}"
    m = re.search(r"第([一二三四五六七八九十百零\d]+)条", text[:120])
    if m:
        return f"第{m.group(1)}条"
    return "无章节号"

async def retrieve(query: str, top_k: int = 3, category: str = "其他"):
    """返回 [{"source":…, "text":…, "score":…}, …]。category 由 schema 传入但当前
    BM25 不做类别过滤（保留参数位，W6 v1.6+ 公司归属路由的接入点）。"""
    def _run():
        return _get().retrieve(query, k=top_k)
    hits = await asyncio.to_thread(_run)
    return [{"source": _source_of(t), "text": t, "score": round(float(s), 4)}
            for t, s in hits]
