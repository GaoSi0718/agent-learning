"""
W5 多模态封装模块（异步版）：在 W4 AsyncChatSession 基础上扩展图片输入能力
模型：deepseek-v4-flash-vision-exp
能力：
  - 文本 + 单张/多张图片混合输入
  - 并发限流 / 指数退避 / 熔断 / 流式输出 / 预算控制
  - 支持 base64 内联、外部 URL、Files API file_id 三种图片传入方式
限制：
  - deepseek-v4-flash-vision-exp 目前仅支持图片输入，不支持音频/视频/通用文件
"""
import os
import time
import asyncio
from pathlib import Path
from typing import List, Union, Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from w5_vision_chat_module import (
    VISION_MODEL,
    TEXT_MODEL,
    PRICE,
    BudgetExceeded,
    UnsupportedMediaError,
    image_block_from_file,
    image_block_from_url,
    image_block_from_file_id,
)

# .env 跟随项目目录：优先读取本文件同级的 .env，缺失时回退到当前工作目录向上查找
_ENV_FILE = Path(__file__).resolve().parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()

if not os.environ.get("DEEPSEEK_API_KEY"):
    raise RuntimeError(
        f"未找到 DEEPSEEK_API_KEY。请在项目目录放置 .env 文件：{_ENV_FILE}\n"
        '内容示例：DEEPSEEK_API_KEY=sk-xxxxxxxx'
    )

client = AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


class CircuitOpen(Exception):
    """熔断打开时抛出：连续失败过多，暂时拒绝调用。"""
    pass


class VisionAsyncChatSession:
    """
    支持文本 + 图片的异步对话会话。
    """

    def __init__(
        self,
        model: str = VISION_MODEL,
        budget_usd: float = 0.10,
        max_retries: int = 3,
        concurrency: int = 3,
        circuit_threshold: int = 5,
        cooldown_sec: float = 10.0,
        system_prompt: str = "你是一个简洁、有帮助的助手。",
    ):
        if model not in PRICE:
            print(f"[警告] 未配置模型 {model} 的单价，将使用 vision 参考价")
        self.model = model
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        self.budget = budget_usd
        self.spent = 0.0
        self.max_retries = max_retries
        self.sem = asyncio.Semaphore(concurrency)
        self.consecutive_failures = 0
        self.circuit_open_until = 0.0
        self.circuit_threshold = circuit_threshold
        self.cooldown_sec = cooldown_sec

    def _cost(self, p: int, c: int) -> float:
        rate = PRICE.get(self.model, PRICE[VISION_MODEL])
        return p / 1000 * rate["prompt"] + c / 1000 * rate["completion"]

    def _check_circuit(self):
        if time.time() < self.circuit_open_until:
            raise CircuitOpen(f"熔断中，冷却至 {self.circuit_open_until:.1f}")

    def _on_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.circuit_threshold:
            self.circuit_open_until = time.time() + self.cooldown_sec
            print(f"[熔断] 连续失败 {self.consecutive_failures} 次，暂停调用 {self.cooldown_sec}s")

    def _on_success(self):
        self.consecutive_failures = 0

    def _build_multimodal_content(
        self,
        text: str,
        images: List[Dict[str, Any]],
    ) -> Union[str, List[Dict[str, Any]]]:
        if not images:
            return text
        content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        content.extend(images)
        return content

    async def ask(
        self,
        user_input: str,
        images: List[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> str:
        """
        发送单轮异步请求。

        参数：
            user_input: 文本问题
            images: OpenAI 兼容的 image block 列表
            stream: 是否流式输出
        """
        self._check_circuit()
        images = images or []
        content = self._build_multimodal_content(user_input, images)
        self.messages.append({"role": "user", "content": content})
        wait = 1
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with self.sem:
                    if stream:
                        chunks = []
                        resp = await client.chat.completions.create(
                            model=self.model,
                            messages=self.messages,
                            stream=True,
                        )
                        async for chunk in resp:
                            delta = chunk.choices[0].delta.content or ""
                            chunks.append(delta)
                            print(delta, end="", flush=True)
                        print()
                        reply = "".join(chunks)
                        est_p, est_c = len(user_input) + len(images) * 384, len(reply)
                    else:
                        resp = await client.chat.completions.create(
                            model=self.model,
                            messages=self.messages,
                            stream=False,
                        )
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
                last_exception = e
                self._on_failure()
                if "does not support image" in str(e).lower() or ("file" in str(e).lower() and "not found" in str(e).lower()):
                    raise UnsupportedMediaError(f"模型/服务端拒绝该输入：{e}") from e
                print(f"[重试 {attempt}/{self.max_retries}] {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(wait)
                    wait *= 2
                else:
                    raise RuntimeError(f"重试耗尽，最后异常：{last_exception}") from last_exception
        raise RuntimeError("重试耗尽")

    async def describe_image(self, image_path: Union[str, Path], prompt: str = "描述这张图片。", stream: bool = False) -> str:
        """便捷方法：异步描述单张本地图片。"""
        return await self.ask(prompt, images=[image_block_from_file(image_path)], stream=stream)


async def _one_image_task(session, image_path, i):
    t0 = time.time()
    try:
        await session.describe_image(image_path, prompt=f"描述第 {i} 张图片，一句话。")
        return (i, True, time.time() - t0)
    except Exception as e:
        print(f"  [任务 {i} 失败] {e}")
        return (i, False, time.time() - t0)


async def stress_test_vision(n=5, concurrency=3):
    """并发压测：需要当前目录存在 example.jpg 才会真正发起图片请求。"""
    print(f"===== W5 视觉并发压测：{n} 请求 / 限流 {concurrency} / 模型 {VISION_MODEL} =====")
    session = VisionAsyncChatSession(budget_usd=0.50, concurrency=concurrency)
    t_start = time.time()

    import os
    if not os.path.exists("example.jpg"):
        print("⚠️ 当前目录无 example.jpg，仅发起文本请求作为兼容性测试。")
        tasks = [session.ask(f"用一句话介绍第 {i} 个 HR 领域的核心概念。") for i in range(1, n + 1)]
    else:
        tasks = [_one_image_task(session, "example.jpg", i) for i in range(1, n + 1)]

    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t_start
    ok = [r for r in results if r[1]]
    fail = [r for r in results if not r[1]]
    print(f"\n--- 结果 ---")
    print(f"成功: {len(ok)}/{n}  失败: {len(fail)}/{n}")
    print(f"总耗时: {elapsed:.2f}s  单请求均值: {sum(r[2] for r in results)/n:.2f}s")
    print(f"累计花费: ${session.spent:.4f}")
    if fail:
        print(f"失败序号: {[r[0] for r in fail]}")
        return False
    print("✅ 并发压测完成")
    return True


if __name__ == "__main__":
    asyncio.run(stress_test_vision(n=5, concurrency=2))
