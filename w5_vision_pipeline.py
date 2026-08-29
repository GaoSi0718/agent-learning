"""
W5 视觉推理 Pipeline（同步版）：基于 deepseek-v4-flash-vision-exp 的高级封装
核心目标：
  1. 多模态视觉理解增强 —— 在文本对话之上集成图片理解
  2. 图像批处理 —— 单张/多张图片按统一模板并行/串行处理
  3. 自定义视觉推理逻辑 —— 支持多轮视觉推理、可复用 Prompt 模板、链式任务
"""
import os
import json
import base64
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI

from w5_vision_chat_module import (
    VISION_MODEL,
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

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


@dataclass
class VisionTask:
    """单个视觉任务定义。"""
    task_id: str
    prompt: str
    images: List[Dict[str, Any]] = field(default_factory=list)
    expect_json: bool = False
    json_schema: Optional[Dict[str, Any]] = None
    temperature: float = 0.0


@dataclass
class VisionResult:
    """单个视觉任务结果。"""
    task_id: str
    success: bool
    content: Optional[str] = None
    parsed: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 可复用的视觉 Prompt 模板
# ---------------------------------------------------------------------------
VISION_TEMPLATES: Dict[str, Callable[[str], str]] = {
    "describe": lambda extra="": f"请详细描述这张图片的内容。{extra}",
    "ocr": lambda extra="": f"请提取图片中的所有可见文字，保持原有排版。{extra}",
    "extract_card": lambda extra="": (
        "请识别图片中的名片/证件信息，并以 JSON 返回："
        '{"姓名":"","职位":"","公司":"","电话":"","邮箱":"","地址":""}'
        f"{extra}"
    ),
    "compare": lambda extra="": f"请对比多张图片的异同点。{extra}",
    "qa": lambda question="": question or "请回答关于这张图片的问题。",
}


# ---------------------------------------------------------------------------
# 视觉推理 Pipeline
# ---------------------------------------------------------------------------
class VisionPipeline:
    """
    高级视觉推理 Pipeline：单图多轮推理 + 批量任务 + 自定义模板。
    """

    def __init__(
        self,
        model: str = VISION_MODEL,
        budget_usd: float = 0.50,
        max_retries: int = 3,
        system_prompt: str = "你是一个严谨的视觉分析助手。",
    ):
        self.model = model
        self.budget = budget_usd
        self.spent = 0.0
        self.max_retries = max_retries
        self.system_prompt = system_prompt

    def _cost(self, p: int, c: int) -> float:
        rate = PRICE.get(self.model, PRICE[VISION_MODEL])
        return p / 1000 * rate["prompt"] + c / 1000 * rate["completion"]

    def _check_budget(self, estimated_cost: float):
        if self.spent + estimated_cost > self.budget:
            raise BudgetExceeded(
                f"预算将超限：已花费 ${self.spent:.4f}，本次估算 ${estimated_cost:.4f} > ${self.budget:.4f}"
            )

    def run(
        self,
        task: VisionTask,
        maintain_context: bool = False,
        stream: bool = False,
    ) -> VisionResult:
        """
        执行单个视觉任务。

        参数：
            task: VisionTask 对象
            maintain_context: 是否把当前任务加入多轮上下文（用于链式推理）
            stream: 是否流式输出
        """
        messages: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        if maintain_context and hasattr(self, "_context"):
            messages.extend(self._context)

        content: List[Dict[str, Any]] = [{"type": "text", "text": task.prompt}]
        content.extend(task.images)
        messages.append({"role": "user", "content": content})

        last_exception: Optional[Exception] = None
        wait = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                self._check_budget(0)  # 仅检查是否已超限
                if stream:
                    chunks = []
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=task.temperature,
                        stream=True,
                    )
                    for chunk in resp:
                        delta = chunk.choices[0].delta.content or ""
                        chunks.append(delta)
                    raw = "".join(chunks)
                    est_p = len(task.prompt) + len(task.images) * 384
                    est_c = len(raw)
                else:
                    kwargs: Dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": task.temperature,
                    }
                    if task.expect_json:
                        kwargs["response_format"] = {"type": "json_object"}
                    resp = client.chat.completions.create(**kwargs)
                    raw = resp.choices[0].message.content
                    est_p = resp.usage.prompt_tokens
                    est_c = resp.usage.completion_tokens

                cost = self._cost(est_p, est_c)
                self.spent += cost
                self._check_budget(0)

                parsed = None
                if task.expect_json:
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError as e:
                        return VisionResult(
                            task_id=task.task_id,
                            success=False,
                            content=raw,
                            error=f"JSON 解析失败：{e}",
                        )

                if maintain_context:
                    if not hasattr(self, "_context"):
                        self._context = []
                    self._context.append(messages[-1])
                    self._context.append({"role": "assistant", "content": raw})

                return VisionResult(
                    task_id=task.task_id,
                    success=True,
                    content=raw,
                    parsed=parsed,
                    prompt_tokens=est_p,
                    completion_tokens=est_c,
                    cost_usd=cost,
                )

            except (BudgetExceeded, UnsupportedMediaError):
                raise
            except Exception as e:
                last_exception = e
                if "does not support image" in str(e).lower():
                    raise UnsupportedMediaError(f"模型/服务端拒绝图片输入：{e}") from e
                if attempt < self.max_retries:
                    import time
                    time.sleep(wait)
                    wait *= 2
                else:
                    return VisionResult(
                        task_id=task.task_id,
                        success=False,
                        error=f"重试耗尽：{last_exception}",
                    )
        return VisionResult(
            task_id=task.task_id,
            success=False,
            error=f"重试耗尽：{last_exception}",
        )

    def chain(
        self,
        image: Union[str, Path, Dict[str, Any]],
        steps: List[str],
    ) -> List[VisionResult]:
        """
        链式视觉推理：对同一张图片按顺序执行多轮问题。
        例如：["描述图片", "提取图中所有文字", "总结关键信息"]
        """
        if isinstance(image, (str, Path)):
            img_block = image_block_from_file(image)
        else:
            img_block = image

        results = []
        self._context = []
        for i, prompt in enumerate(steps, 1):
            task = VisionTask(
                task_id=f"chain_step_{i}",
                prompt=prompt,
                images=[img_block],
                temperature=0.0,
            )
            r = self.run(task, maintain_context=True)
            results.append(r)
            if not r.success:
                break
        return results

    def batch_run(
        self,
        tasks: List[VisionTask],
        max_workers: int = 3,
    ) -> List[VisionResult]:
        """
        批量处理视觉任务，使用线程池并行执行。
        注意：并行会共享 self.budget 预算上限。
        """
        results = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_idx = {
                pool.submit(self.run, task): i for i, task in enumerate(tasks)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = VisionResult(
                        task_id=tasks[idx].task_id,
                        success=False,
                        error=str(e),
                    )
        return results

    def describe(self, image_path: Union[str, Path], extra: str = "") -> VisionResult:
        """便捷方法：单张图片描述。"""
        return self.run(
            VisionTask(
                task_id="describe",
                prompt=VISION_TEMPLATES["describe"](extra),
                images=[image_block_from_file(image_path)],
            )
        )

    def ocr(self, image_path: Union[str, Path], extra: str = "") -> VisionResult:
        """便捷方法：单张图片 OCR。"""
        return self.run(
            VisionTask(
                task_id="ocr",
                prompt=VISION_TEMPLATES["ocr"](extra),
                images=[image_block_from_file(image_path)],
            )
        )

    def extract_json(
        self,
        image_path: Union[str, Path],
        template_name: str = "extract_card",
        extra: str = "",
    ) -> VisionResult:
        """便捷方法：按模板提取结构化 JSON。"""
        return self.run(
            VisionTask(
                task_id=f"extract_{template_name}",
                prompt=VISION_TEMPLATES[template_name](extra),
                images=[image_block_from_file(image_path)],
                expect_json=True,
            )
        )


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pipe = VisionPipeline(budget_usd=0.20)

    # 示例 1：单图 OCR
    # result = pipe.ocr("example.jpg")
    # print(result)

    # 示例 2：链式推理
    # results = pipe.chain("example.jpg", [
    #     "先描述图片整体内容。",
    #     "提取图片中所有可见文字。",
    #     "基于以上信息，判断这是否是一份简历，并说明理由。",
    # ])
    # for r in results:
    #     print(r.task_id, r.success, r.content[:100])

    # 示例 3：批量处理（需要当前目录存在 example.jpg / example2.jpg）
    # tasks = [
    #     VisionTask(task_id="img_1", prompt="描述图片", images=[image_block_from_file("example.jpg")]),
    #     VisionTask(task_id="img_2", prompt="描述图片", images=[image_block_from_file("example2.jpg")]),
    # ]
    # batch_results = pipe.batch_run(tasks, max_workers=2)
    # for r in batch_results:
    #     print(r.task_id, r.success, r.content[:80] if r.content else r.error)

    print(f"[Pipeline 就绪] 模型：{pipe.model} 预算：${pipe.budget:.2f}")
