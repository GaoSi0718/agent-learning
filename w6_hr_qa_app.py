r"""
W6 HR 政策问答助手（Streamlit 骨架）
====================================
复用：
  - w4_chat_module.ChatSession            → 文本问答（预算上限 / 指数退避重试 / 流式）
  - w5_vision_chat_module.VisionChatSession + image_block_from_* → 多模态图片理解
  - w6_rag_retriever.PolicyRetriever      → 本地 BM25 检索，只召回相关片段，省 Token

运行（在 MAX 上）：
  cd agent-learning
  venv\Scripts\pip install -r requirements.txt
  venv\Scripts\streamlit run w6_hr_qa_app.py

注意：
  - 把真实 HR 政策粘贴进 policy_context.txt（留空会自动回退示例数据 w6_sample_policy.txt）。
  - .env 必须与本文件同目录（含 DEEPSEEK_API_KEY）。
  - 每次 API 调用都重建会话、仅携带本次检索到的上下文，避免历史上下文无限膨胀 → 省 Token。
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# 跨设备：在 import w4/w5 之前先注入脚本同级 .env。
# （w4 写死了 脚本同级 .env，MAX 上不存在；先在此加载可保证跨设备不崩。）
_ENV = Path(__file__).resolve().parent / ".env"
if _ENV.exists():
    load_dotenv(_ENV)
else:
    load_dotenv()

if not os.environ.get("DEEPSEEK_API_KEY"):
    raise RuntimeError(
        f"未找到 DEEPSEEK_API_KEY。请在项目目录放置 .env：{_ENV}\n内容示例：DEEPSEEK_API_KEY=sk-xxxxxxxx"
    )

import streamlit as st
from w6_rag_retriever import PolicyRetriever
from w4_chat_module import ChatSession, BudgetExceeded
from w5_vision_chat_module import VisionChatSession, UnsupportedMediaError

POLICY_FILE = Path(__file__).resolve().parent / "policy_context.txt"
HR_SYSTEM = (
    "你是公司 HR 政策问答助手。只能依据下方【政策上下文】作答，"
    "上下文没有的信息，诚实回答「政策中未提及」，不要编造。"
    "回答要简洁、用中文、给出具体条款要点。\n\n【政策上下文】\n{context}"
)


@st.cache_resource
def get_retriever() -> PolicyRetriever:
    return PolicyRetriever(policy_path=POLICY_FILE)


def main() -> None:
    st.set_page_config(page_title="HR 政策问答助手 · W6", page_icon="📋")
    st.title("📋 HR 政策问答助手 (W6 Demo)")
    st.caption("本地 RAG 检索 + DeepSeek · 每次只携带相关片段，省 Token")

    retriever = get_retriever()

    with st.sidebar:
        st.header("参数")
        budget = st.slider("单次预算上限 (USD)", 0.01, 0.5, 0.05, 0.01)
        top_k = st.slider("检索片段数 k", 1, 8, 4, 1)
        use_vision = st.checkbox("启用图片问答（多模态）", value=False)
        st.divider()
        st.markdown(f"已索引政策片段：**{len(retriever.chunks)}** 段")
        if len(retriever.chunks) == 0:
            st.warning("policy_context.txt 为空，请粘贴真实 HR 政策。")

    if "history" not in st.session_state:
        st.session_state.history = []

    for role, msg in st.session_state.history:
        st.chat_message(role).write(msg)

    uploaded = None
    if use_vision:
        uploaded = st.file_uploader(
            "上传图片（可选，多模态生效时用于图片理解）",
            type=["jpg", "jpeg", "png", "gif", "webp"],
        )

    if prompt := st.chat_input("问 HR 政策，例如：试用期多久？年假怎么请？"):
        st.chat_message("user").write(prompt)
        st.session_state.history.append(("user", prompt))

        context = retriever.build_context(prompt, k=top_k)
        system_prompt = HR_SYSTEM.format(context=context or "（无相关片段）")

        try:
            if use_vision and uploaded is not None:
                import base64
                b64 = base64.b64encode(uploaded.read()).decode()
                mime = uploaded.type or "image/jpeg"
                img_block = {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
                sess = VisionChatSession(
                    model="deepseek-v4-flash-vision-exp",
                    budget_usd=budget,
                    system_prompt=system_prompt,
                )
                reply = sess.ask(prompt, images=[img_block])
                spent = sess.spent
            else:
                sess = ChatSession(budget_usd=budget)
                sess.messages[0]["content"] = system_prompt
                reply = sess.ask(prompt)
                spent = sess.spent
        except BudgetExceeded as e:
            reply = f"⚠️ 预算超限：{e}"
            spent = budget
        except UnsupportedMediaError as e:
            reply = f"⚠️ 模型不支持该输入：{e}"
            spent = 0.0

        st.chat_message("assistant").write(reply)
        st.session_state.history.append(("assistant", reply))
        st.caption(f"本次花费 ≈ ${spent:.4f}")
        with st.expander("🔍 检索到的政策片段"):
            st.write(context or "（无）")


if __name__ == "__main__":
    main()
