"""
W2 多轮 CLI 问答脚本（含重试、token 统计）
来源：阶段一待办清单 W2 产出物

运行：
  cd D:/WorkBuddyData/projects/agent-learning
  venv\Scripts\activate
  python w2_chat_cli.py

说明：
  - 密钥从 项目同级 .env 的 DEEPSEEK_API_KEY 读取（不在此硬编码）
  - DeepSeek 兼容 OpenAI SDK，base_url=https://api.deepseek.com
"""
import os
import time

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 直接加载本机已有的 key 文件（r"" 原始字符串，避免 \U 转义报错），避免复制明文
load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"
MAX_RETRIES = 3
BASE_WAIT = 1  # 指数退避：1s -> 2s -> 4s

# 判断模型返回是否像"代码"而非自然语言对话
CODE_MARKERS = ("```", "def ", "import ", "from ", "class ", "print(", "#!/", "async def ", "function ")


def looks_like_code(text: str) -> bool:
    """简单启发式：前 200 字符里出现代码标记即视为代码。"""
    head = text.strip()[:200]
    return any(marker in head for marker in CODE_MARKERS)


def chat_once(messages):
    """单次请求，带指数退避重试。返回 (reply, prompt_tokens, completion_tokens)。"""
    wait = BASE_WAIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=False,
            )
            return (
                resp.choices[0].message.content,
                resp.usage.prompt_tokens,
                resp.usage.completion_tokens,
            )
        except Exception as e:  # 断网/限流等
            print(f"[重试 {attempt}/{MAX_RETRIES}] 出错: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(wait)
                wait *= 2
            else:
                raise
    raise RuntimeError("重试耗尽仍失败")


def chat_safe(messages):
    """带"代码检测"保险：若模型返回代码而非自然语言，自动追加指令重问一次。"""
    reply, p, c = chat_once(messages)
    if looks_like_code(reply):
        print("[保险] 检测到返回为代码，已自动要求模型改用自然语言重答…")
        retry_messages = messages + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "请用纯自然语言回答，不要输出任何代码或脚本。"},
        ]
        reply2, p2, c2 = chat_once(retry_messages)
        return reply2, p + p2, c + c2
    return reply, p, c


def main():
    print("=== W2 多轮 CLI 问答（输入 exit/quit 退出）===")
    messages = [{"role": "system", "content": "你是一个友好、简洁的对话助手。用自然语言回答问题，不要输出代码或脚本。如果用户问的是编程相关的问题，用文字解释概念即可。"}]
    total_prompt = total_completion = 0

    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[已退出]")
            break
        if user_input.lower() in {"exit", "quit", "q"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            reply, p, c = chat_safe(messages)
        except Exception as e:
            print(f"[请求失败] {e}")
            messages.pop()  # 回滚本次用户输入，避免污染历史
            continue

        messages.append({"role": "assistant", "content": reply})
        total_prompt += p
        total_completion += c
        print(f"AI> {reply}")
        print(f"[token] 本次 p={p} c={c} | 累计 p={total_prompt} c={total_completion}")

    print(f"\n=== 会话结束，累计 token：prompt={total_prompt} completion={total_completion} ===")


if __name__ == "__main__":
    main()
