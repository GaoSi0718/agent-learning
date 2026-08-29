"""
W4 异步封装模块（升级版）：并发限流 / 指数退避 / 熔断 / 流式 / 预算
"""
import os, time, asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")
client = AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"
PRICE = {"prompt": 0.00027, "completion": 0.0011}


class BudgetExceeded(Exception):
    pass


class CircuitOpen(Exception):
    """熔断打开时抛出：连续失败过多，暂时拒绝调用。"""
    pass


class AsyncChatSession:
    def __init__(self, budget_usd=0.10, max_retries=3, concurrency=3, circuit_threshold=5, cooldown_sec=10.0):
        self.messages = [{"role": "system", "content": "你是一个简洁、有帮助的助手。"}]
        self.budget = budget_usd
        self.spent = 0.0
        self.max_retries = max_retries
        self.sem = asyncio.Semaphore(concurrency)  # 限流：同时最多 concurrency 个请求
        self.consecutive_failures = 0
        self.circuit_open_until = 0.0

    def _cost(self, p, c):
        return p / 1000 * PRICE["prompt"] + c / 1000 * PRICE["completion"]

    def _check_circuit(self):
        if time.time() < self.circuit_open_until:
            raise CircuitOpen(f"熔断中，冷却至 ...")

    def _on_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.circuit_threshold:
            self.circuit_open_until = time.time() + 10.0
            print(f"[熔断] 连续失败 {self.consecutive_failures} 次，暂停调用 10s")

    def _on_success(self):
        self.consecutive_failures = 0

    async def ask(self, user_input, stream=False):
        self._check_circuit()
        self.messages.append({"role": "user", "content": user_input})
        wait = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self.sem:  # 限流
                    if stream:
                        chunks = []
                        resp = await client.chat.completions.create(model=MODEL, messages=self.messages, stream=True)
                        async for chunk in resp:
                            delta = chunk.choices[0].delta.content or ""
                            chunks.append(delta); print(delta, end="", flush=True)
                        print()
                        reply = "".join(chunks)
                        est_p, est_c = len(reply) // 2, len(reply) // 2
                    else:
                        resp = await client.chat.completions.create(model=MODEL, messages=self.messages, stream=False)
                        reply = resp.choices[0].message.content
                        est_p, est_c = resp.usage.prompt_tokens, resp.usage.completion_tokens
                self.spent += self._cost(est_p, est_c)
                if self.spent > self.budget:
                    raise BudgetExceeded(f"会话预算超限：已花费 ${self.spent:.4f} > ${self.budget:.4f}")
                self.messages.append({"role": "assistant", "content": reply})
                self._on_success()
                return reply
            except (BudgetExceeded, CircuitOpen):
                raise
            except Exception as e:
                self._on_failure()
                print(f"[重试 {attempt}/{self.max_retries}] {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(wait); wait *= 2
                else:
                    raise
        raise RuntimeError("重试耗尽")


async def _one_question(session, i):
    t0 = time.time()
    try:
        await session.ask(f"用一句话介绍第 {i} 个 HR 领域的核心概念。")
        return (i, True, time.time() - t0)
    except Exception as e:
        return (i, False, time.time() - t0)


async def stress_test(n=50, concurrency=3):
    print(f"===== W4 并发压测：{n} 请求 / 限流 {concurrency} / 模型 {MODEL} =====")
    session = AsyncChatSession(budget_usd=0.50, concurrency=concurrency)
    t_start = time.time()
    tasks = [_one_question(session, i) for i in range(1, n + 1)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t_start
    ok = [r for r in results if r[1]]
    fail = [r for r in results if not r[1]]
    print(f"\n--- 结果 ---")
    print(f"成功: {len(ok)}/{n}  失败: {len(fail)}/{n}")
    print(f"总耗时: {elapsed:.2f}s  单请求均值: {sum(r[2] for r in results)/n:.2f}s")
    print(f"累计花费: ${session.spent:.4f}")
    if fail:
        print(f"失败序号: {[r[0] for r in fail]}"); return False
    print(f"✅ {n} 并发压测零失败，达成 Task 6 完成标准")
    return True


if __name__ == "__main__":
    asyncio.run(stress_test(n=50, concurrency=3))