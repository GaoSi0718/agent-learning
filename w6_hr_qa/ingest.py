"""
W6 HR 问答助手 · ① 文档灌库

流程：加载文档 → 分层切片 → 向量化 → 存入 Chroma

用法：
    python w6_hr_qa/ingest.py              # 增量灌库
    python w6_hr_qa/ingest.py --rebuild    # 清空重建
"""
import sys
import argparse
import time
from pathlib import Path

import config


# ───────────────────────────────────────────────────────────
# 1. Embedding 客户端（支持硅基流动 / 本地兜底）
# ───────────────────────────────────────────────────────────
class Embedder:
    """统一的 embedding 接口，屏蔽不同 provider 的差异。"""

    def __init__(self):
        self.provider = config.EMBEDDING_PROVIDER
        if self.provider == "siliconflow":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.SILICONFLOW_API_KEY,
                base_url=config.SILICONFLOW_BASE_URL,
            )
            self.model = config.EMBEDDING_MODEL
        elif self.provider == "local":
            from sentence_transformers import SentenceTransformer
            print(f"[加载本地模型] {config.LOCAL_EMBEDDING_MODEL}（首次需下载约 470MB）")
            self.client = SentenceTransformer(config.LOCAL_EMBEDDING_MODEL)
            self.model = config.LOCAL_EMBEDDING_MODEL
        else:
            raise ValueError(f"未知 EMBEDDING_PROVIDER: {self.provider}")

    def embed(self, texts: list) -> list:
        """把文本列表转成向量列表。"""
        if self.provider == "siliconflow":
            # 硅基流动单次最多 64 条，分批
            all_vecs, batch = [], 32
            for i in range(0, len(texts), batch):
                chunk = texts[i:i + batch]
                resp = self.client.embeddings.create(model=self.model, input=chunk)
                all_vecs.extend([d.embedding for d in resp.data])
                print(f"  [向量化] {min(i+batch, len(texts))}/{len(texts)}", end="\r")
            print()
            return all_vecs
        else:
            return self.client.encode(texts, show_progress_bar=True).tolist()


# ───────────────────────────────────────────────────────────
# 2. 文档加载（支持 .md / .txt / .docx / .pdf）
# ───────────────────────────────────────────────────────────
def load_documents(policy_dir: Path) -> list:
    """返回 [{"text": ..., "source": 文件名}, ...]"""
    docs = []
    patterns = ["*.md", "*.txt", "*.docx", "*.pdf"]

    for pattern in patterns:
        for path in sorted(policy_dir.glob(pattern)):
            try:
                if path.suffix in (".md", ".txt"):
                    text = path.read_text(encoding="utf-8")
                elif path.suffix == ".docx":
                    from docx import Document
                    doc = Document(path)
                    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                elif path.suffix == ".pdf":
                    from pypdf import PdfReader
                    reader = PdfReader(path)
                    text = "\n".join(p.extract_text() or "" for p in reader.pages)
                else:
                    continue

                if text.strip():
                    docs.append({"text": text, "source": path.name})
                    print(f"[加载] {path.name}  ({len(text)} 字)")
            except Exception as e:
                print(f"⚠️  [跳过] {path.name}：{e}")

    return docs


# ───────────────────────────────────────────────────────────
# 3. 分层切片（按条款优先 → 超长再按字数切）
# ───────────────────────────────────────────────────────────
def split_by_structure(text: str) -> list:
    """
    第一层：按 Markdown 标题（#/##）和"第 X 条"切分，保持条款完整。
    第二层：超过 CHUNK_SIZE 的段落再按字数滑窗切分（带重叠）。
    """
    import re

    # 第一层：按 "第 X 条" 或 Markdown 标题切
    pattern = r"(?=^#{1,3}\s|^第\s*\d+\s*条)"
    blocks = re.split(pattern, text, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    # 合并相邻的小块（避免条款被标题割裂）
    merged, buffer = [], ""
    for b in blocks:
        if len(b) < config.MIN_CHUNK_SIZE and buffer:
            buffer += "\n" + b
        else:
            if buffer:
                merged.append(buffer)
            buffer = b
    if buffer:
        merged.append(buffer)

    # 第二层：超长块按字数滑窗切（带重叠）
    final = []
    for block in merged:
        if len(block) <= config.CHUNK_SIZE:
            final.append(block)
            continue

        step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
        for i in range(0, len(block), step):
            piece = block[i:i + config.CHUNK_SIZE]
            if len(piece) >= config.MIN_CHUNK_SIZE:
                final.append(piece)
            if i + config.CHUNK_SIZE >= len(block):
                break

    return final


def extract_article_no(chunk: str) -> str:
    """从片段中提取条款号，用于引用溯源。"""
    import re
    m = re.search(r"第\s*(\d+)\s*条", chunk)
    if m:
        return f"第{m.group(1)}条"
    m = re.search(r"^#{1,3}\s*(.+)$", chunk, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()[:20]
    return ""


# ───────────────────────────────────────────────────────────
# 4. 主流程
# ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="清空向量库后重建")
    args = parser.parse_args()

    # 配置自检
    problems = config.check_config()
    if problems:
        print("❌ 配置有问题：")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        sys.exit(1)

    t0 = time.time()

    # ── 加载 ──
    print("=" * 55)
    print("① 加载文档")
    print("=" * 55)
    docs = load_documents(config.POLICY_DIR)
    if not docs:
        print(f"❌ 未找到任何文档：{config.POLICY_DIR}")
        sys.exit(1)
    print(f"共加载 {len(docs)} 个文档\n")

    # ── 切片 ──
    print("=" * 55)
    print("② 分层切片")
    print("=" * 55)
    all_chunks, all_metas, all_ids = [], [], []
    for doc in docs:
        chunks = split_by_structure(doc["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metas.append({
                "source": doc["source"],
                "article": extract_article_no(chunk),
                "chunk_index": i,
            })
            all_ids.append(f"{doc['source']}_{i}")
        print(f"  {doc['source']}: {len(chunks)} 个片段")
    print(f"合计 {len(all_chunks)} 个片段（size={config.CHUNK_SIZE}, "
          f"overlap={config.CHUNK_OVERLAP}）\n")

    # ── 向量化 ──
    print("=" * 55)
    print(f"③ 向量化（{config.EMBEDDING_MODEL}）")
    print("=" * 55)
    embedder = Embedder()
    vectors = embedder.embed(all_chunks)
    print(f"完成，维度 {len(vectors[0])}\n")

    # ── 入库 ──
    print("=" * 55)
    print("④ 存入 Chroma")
    print("=" * 55)
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    if args.rebuild:
        try:
            client.delete_collection("hr_policies")
            print("  [清空] 已删除旧集合")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name="hr_policies",
        metadata={"hnsw:space": "cosine"},   # 余弦相似度
    )

    # 增量：跳过已存在的 id
    existing = set(collection.get()["ids"])
    new_idx = [i for i, id_ in enumerate(all_ids) if id_ not in existing]

    if not new_idx:
        print("  无新增片段（全部已入库）。如需重建请加 --rebuild")
    else:
        collection.upsert(
            ids=[all_ids[i] for i in new_idx],
            embeddings=[vectors[i] for i in new_idx],
            documents=[all_chunks[i] for i in new_idx],
            metadatas=[all_metas[i] for i in new_idx],
        )
        print(f"  新增 {len(new_idx)} 条，跳过 {len(all_ids) - len(new_idx)} 条已存在")

    print(f"\n✅ 完成！向量库共 {collection.count()} 条，耗时 {time.time()-t0:.1f}s")
    print(f"   持久化路径：{config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
