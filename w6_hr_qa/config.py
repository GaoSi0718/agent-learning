"""
W6 HR 问答助手 · 配置中心

所有可调参数集中在这里，改配置不用动业务代码。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── 路径 ──
# .env 放在项目根目录（agent-learning/.env），本文件在 w6_hr_qa/ 下，故 parent.parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BASE_DIR = Path(__file__).resolve().parent
POLICY_DIR = BASE_DIR / "data" / "policies"       # 制度文档目录
CHROMA_DIR = BASE_DIR / "chroma_db"                # 向量库持久化目录
EVAL_FILE = BASE_DIR / "eval" / "questions.json"   # 评测集

# 确保目录存在
POLICY_DIR.mkdir(parents=True, exist_ok=True)
EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── 大模型（生成）──
LLM_PROVIDER = "deepseek"
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
LLM_TEMPERATURE = 0.1        # 制度问答要稳定，温度调低
LLM_MAX_TOKENS = 1500

# 价格（deepseek-chat 参考价，元/千 token，用于成本统计）
LLM_PRICE = {"prompt": 0.0014, "completion": 0.0028}


# ── Embedding（向量化）──
# 可选："siliconflow"（推荐，免费）| "local"（离线兜底）
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "siliconflow")

SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"          # 免费中文 embedding，1024 维
EMBEDDING_DIM = 1024

# 离线兜底模型（EMBEDDING_PROVIDER="local" 时用）
LOCAL_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


# ── 切片策略 ──
CHUNK_SIZE = 500          # 每段最大字数（中文 500 字 ≈ 350 token）
CHUNK_OVERLAP = 80        # 相邻段重叠字数（防关键句被切断）
MIN_CHUNK_SIZE = 50       # 太短的片段丢弃（如只有标题）


# ── 检索 ──
TOP_K = 4                 # 返回最相似的 4 个片段
SIMILARITY_THRESHOLD = 0.35   # 低于此相关度视为"未找到"（cosine distance 越小越相似）


# ── 防幻觉 Prompt ──
SYSTEM_PROMPT = """你是安徽三禾一信息科技有限公司的制度问答助手。

【严格约束 - 必须遵守】
1. 只根据下方【参考内容】回答问题，绝对不得使用你自己的知识或推测。
2. 如果【参考内容】中没有答案，必须且只能回答：
   "根据现有制度文档，未查询到相关规定，建议联系人资部确认。"
   不要尝试给出"一般来说""通常"这类推测性答案。
3. 每个回答末尾必须列出引用的文档名称和条款号，格式：
   📚 引用：《文件名》· 第X条
4. 回答要简洁准确，直接给出结论，然后补充关键细节（数字、条件、流程）。
5. 若参考内容之间存在冲突，明确指出冲突并建议以哪个为准。

【参考内容】
{context}
"""


def check_config() -> list:
    """检查配置是否完整，返回问题列表。"""
    problems = []

    if not LLM_API_KEY:
        problems.append(
            "缺少 DEEPSEEK_API_KEY：请在项目根目录 .env 中配置\n"
            "  格式：DEEPSEEK_API_KEY=sk-xxxxxx"
        )

    if EMBEDDING_PROVIDER == "siliconflow":
        if not SILICONFLOW_API_KEY:
            problems.append(
                "缺少 SILICONFLOW_API_KEY：DeepSeek 不提供 embedding 接口，"
                "需注册硅基流动（https://cloud.siliconflow.cn）获取免费 Key\n"
                "  格式：SILICONFLOW_API_KEY=sk-xxxxxx\n"
                "  或改用离线模型：在 .env 设置 EMBEDDING_PROVIDER=local"
            )
    elif EMBEDDING_PROVIDER == "local":
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            problems.append(
                "EMBEDDING_PROVIDER=local 但未安装 sentence-transformers\n"
                "  安装：pip install sentence-transformers torch"
            )
    else:
        problems.append(f"未知的 EMBEDDING_PROVIDER：{EMBEDDING_PROVIDER}")

    if not any(POLICY_DIR.iterdir()):
        problems.append(f"制度文档目录为空：{POLICY_DIR}")

    return problems


if __name__ == "__main__":
    print("=" * 50)
    print("配置自检")
    print("=" * 50)
    print(f"项目根目录     : {PROJECT_ROOT}")
    print(f"制度文档目录   : {POLICY_DIR}")
    print(f"向量库目录     : {CHROMA_DIR}")
    print(f"生成模型       : {LLM_MODEL} @ {LLM_BASE_URL}")
    print(f"Embedding      : {EMBEDDING_MODEL} ({EMBEDDING_PROVIDER})")
    print(f"切片           : size={CHUNK_SIZE} overlap={CHUNK_OVERLAP}")
    print(f"检索           : top_k={TOP_K} threshold={SIMILARITY_THRESHOLD}")
    print("-" * 50)

    problems = check_config()
    if problems:
        print("❌ 发现问题：")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        sys.exit(1)
    else:
        print("✅ 配置检查通过，可以运行 ingest.py")
