"""
W6 HR 问答助手 · ③ Streamlit 网页界面

启动：streamlit run w6_hr_qa/app.py
"""
import sys
from pathlib import Path

import streamlit as st

import config
from qa import QAChain

# ── 页面配置 ──
st.set_page_config(
    page_title="HR 制度问答助手",
    page_icon="📋",
    layout="wide",
)

# ── 简单样式 ──
st.markdown("""
<style>
    .block-container {padding-top: 2rem; max-width: 900px;}
    .source-box {
        background-color: #f6f8fa;
        border-left: 3px solid #4a90d9;
        padding: 0.6rem 0.9rem;
        margin: 0.4rem 0;
        border-radius: 0 4px 4px 0;
        font-size: 0.88rem;
        color: #333;
    }
    .metric-row {display: flex; gap: 1.5rem; font-size: 0.82rem; color: #888;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_chain():
    """加载问答链（缓存，避免每次提问都重建）。"""
    problems = config.check_config()
    if problems:
        return None, problems
    try:
        return QAChain(), None
    except Exception as e:
        return None, [str(e)]


def main():
    st.title("📋 HR 制度问答助手")
    st.caption("基于 RAG 的企业制度智能问答 · 答案带条款级溯源")

    chain, problems = load_chain()

    if problems:
        st.error("配置有问题，请先解决：")
        for i, p in enumerate(problems, 1):
            st.code(p, language="text")
        st.info("解决后请刷新页面。配置自检命令：`python w6_hr_qa/config.py`")
        st.stop()

    # ── 侧边栏 ──
    with st.sidebar:
        st.subheader("⚙️ 设置")
        top_k = st.slider("检索片段数", 1, 8, config.TOP_K,
                          help="越多越全，但 Token 成本更高")
        threshold = st.slider("相关度阈值", 0.0, 1.0, config.SIMILARITY_THRESHOLD, 0.05,
                              help="低于此值视为未找到，直接拒答")
        show_context = st.checkbox("显示检索到的原文", value=False)

        st.divider()
        st.subheader("💡 示例问题")
        examples = [
            "年假有几天？",
            "试用期多久？",
            "病假要交什么材料？",
            "出差住宿费标准是多少？",
            "报销多久能到账？",
            "迟到怎么扣钱？",
            "辞职要提前多久说？",
            "年终奖一般发几个月？",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True):
                st.session_state.pending_question = ex

        st.divider()
        st.caption(f"生成模型：{config.LLM_MODEL}")
        st.caption(f"向量模型：{config.EMBEDDING_MODEL}")
        st.caption(f"向量库：{chain.retriever.collection.count()} 条片段")

    # ── 会话历史 ──
    if "history" not in st.session_state:
        st.session_state.history = []
    if "total_cost" not in st.session_state:
        st.session_state.total_cost = 0.0

    # ── 输入框 ──
    question = st.chat_input("输入你的问题，例如：年假有几天？")

    # 侧边栏示例问题触发
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    if question:
        with st.spinner("检索并生成中..."):
            try:
                # 临时覆盖配置
                old_k, old_th = config.TOP_K, config.SIMILARITY_THRESHOLD
                config.TOP_K, config.SIMILARITY_THRESHOLD = top_k, threshold

                result = chain.ask(question, stream=False, verbose=False)

                config.TOP_K, config.SIMILARITY_THRESHOLD = old_k, old_th

                st.session_state.history.append({
                    "q": question,
                    "a": result["answer"],
                    "hits": result["hits"],
                    "elapsed": result["elapsed"],
                    "tokens": result["tokens"],
                    "cost": result["cost"],
                })
                st.session_state.total_cost += result["cost"]
            except Exception as e:
                st.error(f"出错了：{e}")

    # ── 渲染历史 ──
    for item in reversed(st.session_state.history):
        with st.chat_message("user"):
            st.write(item["q"])

        with st.chat_message("assistant"):
            st.write(item["a"])

            if item["hits"]:
                with st.expander(f"📚 引用来源（{len(item['hits'])}）", expanded=False):
                    for i, h in enumerate(item["hits"], 1):
                        art = f" · {h['article']}" if h["article"] else ""
                        st.markdown(
                            f'<div class="source-box">'
                            f'<b>[{i}] {h["source"]}{art}</b> '
                            f'<span style="color:#888;">（相关度 {h["score"]}）</span><br>'
                            f'{h["text"][:300]}{"..." if len(h["text"]) > 300 else ""}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.caption("⚠️ 未检索到相关条款，已拒答")

            st.markdown(
                f'<div class="metric-row">'
                f'<span>⏱ {item["elapsed"]}s</span>'
                f'<span>🔤 {item["tokens"]} tokens</span>'
                f'<span>💰 ¥{item["cost"]:.6f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 底栏统计 ──
    if st.session_state.history:
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("问答轮次", len(st.session_state.history))
        col2.metric("累计花费", f"¥{st.session_state.total_cost:.5f}")
        col3.metric("平均响应",
                    f"{sum(h['elapsed'] for h in st.session_state.history) / len(st.session_state.history):.2f}s")

        if st.button("🗑️ 清空会话"):
            st.session_state.history = []
            st.session_state.total_cost = 0.0
            st.rerun()


if __name__ == "__main__":
    main()
