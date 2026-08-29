"""
W4 模型选型与 API 工程细节（chat 封装模块）
能力：单会话预算上限、指数退避重试、流式输出接口
"""
import os
import time

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")
client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"
PRICE = {"prompt": 0.00027, "completion": 0.0011}  # deepseek-chat 参考价


class BudgetExceeded(Exception):
    pass


class ChatSession:
    def __init__(self, budget_usd: float = 0.05, max_retries: int = 3):
        self.messages = [{"role": "system", "content": "你是一个简洁、有帮助的助手。"}]
        self.budget = budget_usd
        self.spent = 0.0
        self.max_retries = max_retries

    def _cost(self, p: int, c: int) -> float:
        return p / 1000 * PRICE["prompt"] + c / 1000 * PRICE["completion"]

    def ask(self, user_input: str, stream: bool = False) -> str:
        self.messages.append({"role": "user", "content": user_input})
        wait = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                if stream:
                    chunks = []
                    resp = client.chat.completions.create(model=MODEL, messages=self.messages, stream=True)
                    for chunk in resp:
                        delta = chunk.choices[0].delta.content or ""
                        chunks.append(delta)
                        print(delta, end="", flush=True)
                    print()
                    reply = "".join(chunks)
                    est_p, est_c = len(reply) // 2, len(reply) // 2  # 流式无 usage，粗估
                else:
                    resp = client.chat.completions.create(model=MODEL, messages=self.messages, stream=False)
                    reply = resp.choices[0].message.content
                    est_p, est_c = resp.usage.prompt_tokens, resp.usage.completion_tokens

                self.spent += self._cost(est_p, est_c)
                if self.spent > self.budget:
                    raise BudgetExceeded(f"会话预算超限：已花费 ${self.spent:.4f} > ${self.budget:.4f}")
                self.messages.append({"role": "assistant", "content": reply})
                return reply
            except BudgetExceeded:
                raise
            except Exception as e:
                print(f"[重试 {attempt}/{self.max_retries}] {e}")
                if attempt < self.max_retries:
                    time.sleep(wait)
                    wait *= 2
                else:
                    raise
        raise RuntimeError("重试耗尽")


if __name__ == "__main__":
    s = ChatSession(budget_usd=0.02)
    print(s.ask("用一句话解释什么是 MCP。", stream=True))
    print(f"[累计花费] ${s.spent:.4f}")