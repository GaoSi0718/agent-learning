# app.py —— W5 完整版：简历抽取网页工具
from dotenv import load_dotenv
load_dotenv()
import os, json, io
from datetime import datetime
import streamlit as st
from openai import OpenAI
import docx
import pypdf  # PyPDF2 已于 2023 年停止维护，官方继任者为 pypdf（API 基本一致）

st.set_page_config(page_title="简历信息抽取", layout="wide")

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

SYSTEM_PROMPT = """你是简历信息抽取引擎。请抽取以下字段并以 JSON 返回：
{
  "姓名": str | null, "学历": str | null, "工作年限": float | null,
  "技能列表": [str], "期望岗位": str | null, "联系电话": str | null, "邮箱": str | null
}
规则：1. 缺失填 null，禁止编造。2. 技能列表控制在 10 个以内。3. 只输出 JSON。"""

def read_docx(file_obj):
    doc = docx.Document(io.BytesIO(file_obj.read()))
    return "\n".join([p.text for p in doc.paragraphs])

def read_pdf(file_obj):
    reader = pypdf.PdfReader(io.BytesIO(file_obj.read()))
    return "\n".join([(p.extract_text() or "") for p in reader.pages])

def read_file(file_obj):
    name = file_obj.name.lower()
    if name.endswith((".txt", ".md")):
        return file_obj.read().decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        return read_docx(file_obj)
    if name.endswith(".pdf"):
        return read_pdf(file_obj)
    return ""

def call_stream(text, temp, model):
    resp = client.chat.completions.create(
        model=model, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}],
        response_format={"type": "json_object"}, temperature=temp, stream=True)
    for chunk in resp:
        d = chunk.choices[0].delta.content
        if d:
            yield d

st.title("📄 简历信息抽取工具")
st.caption("粘贴简历文本或上传 txt / md / docx / pdf，一键抽取关键字段并导出")

with st.sidebar:
    st.header("⚙️ 设置")
    model = st.selectbox("选择模型", ["deepseek-chat", "deepseek-coder"], index=0)
    temperature = st.slider("temperature", 0.0, 1.5, 0.0, 0.1)
    use_stream = st.checkbox("使用流式输出", value=True)
    st.divider()
    st.header("📜 历史记录")
    if st.button("清空历史"):
        st.session_state.history = []
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = []

col_in, col_out = st.columns([1, 1])
with col_in:
    st.subheader("1️⃣ 输入简历")
    text_input = st.text_area("直接粘贴简历文本", height=180)
    uploaded = st.file_uploader("或上传文件", type=["txt", "md", "docx", "pdf"])
    file_text = ""
    if uploaded is not None:
        file_text = read_file(uploaded)
        if file_text:
            st.success(f"已读取 {uploaded.name}，共 {len(file_text)} 字符")
            st.text_area("文件预览", file_text, height=120, disabled=True)
    final_text = text_input.strip() or file_text.strip()
    if st.button("🚀 开始抽取", type="primary"):
        if not final_text:
            st.warning("请先粘贴简历文本或上传文件。")
        else:
            with st.spinner("正在抽取..."):
                if use_stream:
                    ph = st.empty(); acc = ""
                    for c in call_stream(final_text, temperature, model):
                        acc += c
                        ph.markdown(f"```json\n{acc}\n```")
                    parsed = json.loads(acc) if acc.strip().startswith("{") else None
                else:
                    resp = client.chat.completions.create(
                        model=model, messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": final_text}],
                        response_format={"type": "json_object"}, temperature=temperature)
                    acc = resp.choices[0].message.content
                    parsed = json.loads(acc)
                st.session_state.history.insert(0, {
                    "时间": datetime.now().strftime("%H:%M:%S"),
                    "来源": uploaded.name if uploaded else "文本粘贴",
                    "结果": parsed or acc})
                with col_out:
                    st.subheader("2️⃣ 抽取结果")
                    if parsed:
                        st.json(parsed)
                        st.dataframe([{"字段": k, "值": v} for k, v in parsed.items()],
                                     use_container_width=True, hide_index=True)
                    else:
                        st.error("返回非 JSON，原始输出："); st.code(acc)
                    st.download_button("⬇️ 下载结果 JSON",
                        json.dumps(parsed or acc, ensure_ascii=False, indent=2),
                        file_name=f"result_{datetime.now().strftime('%H%M%S')}.json",
                        mime="application/json")

with st.sidebar:
    for rec in st.session_state.history[:10]:
        with st.expander(f"{rec['时间']} — {rec['来源']}"):
            st.json(rec["结果"])