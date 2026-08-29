"""
W5 多模态封装模块（同步版）：在 W4 ChatSession 基础上扩展图片输入能力
模型：deepseek-v4-flash-vision-exp
能力：
  - 文本 + 单张/多张图片混合输入
  - 支持 base64 内联、外部 URL、Files API file_id 三种图片传入方式
  - 保留预算上限、指数退避重试、流式输出
限制：
  - deepseek-v4-flash-vision-exp 目前仅支持图片输入，不支持音频/视频/通用文件
  - 图片只能出现在 user 消息中，否则 API 返回 400
"""
import os
import time
import base64
import mimetypes
from pathlib import Path
from typing import List, Union, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

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

# 支持的视觉模型与参考单价（ vision 模型图片按 token 计费，文本同 v4-flash 参考价）
VISION_MODEL = "deepseek-v4-flash-vision-exp"
TEXT_MODEL = "deepseek-v4-flash"
PRICE = {
    "deepseek-v4-flash": {"prompt": 0.00005, "completion": 0.00009},  # 参考价，需以官网为准
    "deepseek-v4-flash-vision-exp": {"prompt": 0.00005, "completion": 0.00009},
}


class BudgetExceeded(Exception):
    pass


class UnsupportedMediaError(Exception):
    """当前模型不支持该媒体类型。"""
    pass


# ---------------------------------------------------------------------------
# 多模态消息构造工具函数
# ---------------------------------------------------------------------------
def _guess_mime(path: Union[str, Path]) -> str:
    """根据文件内容/后缀推断 MIME 类型；无法推断时默认 image/jpeg。"""
    mime, _ = mimetypes.guess_type(str(path))
    if mime in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        return mime
    return "image/jpeg"


def image_block_from_file(path: Union[str, Path], detail: str = "auto") -> Dict[str, Any]:
    """将本地图片文件转换为 OpenAI 兼容的 image_url block（base64 内联）。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"图片文件不存在：{path}")
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"单张图片超过 32 MiB 限制：{path}")
    mime = _guess_mime(path)
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail},
    }


def image_block_from_url(url: str, detail: str = "auto") -> Dict[str, Any]:
    """将可公开访问的图片 URL 转换为 OpenAI 兼容的 image_url block。"""
    if len(url) > 8192:
        raise ValueError(f"外部图片 URL 超过 8192 字符限制：{len(url)} 字符")
    return {"type": "image_url", "image_url": {"url": url, "detail": detail}}


def image_block_from_file_id(file_id: str) -> Dict[str, Any]:
    """引用通过 DeepSeek Files API 上传的文件（file_id）。"""
    return {"type": "file", "file_id": file_id}


# ---------------------------------------------------------------------------
# ChatSession 多模态扩展
# ---------------------------------------------------------------------------
class VisionChatSession:
    """
    支持文本 + 图片的同步对话会话。
    """

    def __init__(
        self,
        model: str = VISION_MODEL,
        budget_usd: float = 0.05,
        max_retries: int = 3,
        system_prompt: str = "你是一个简洁、有帮助的助手。",
    ):
        if model not in PRICE:
            # 允许未知模型，但给出默认价格；调用时仍由服务端校验
            print(f"[警告] 未配置模型 {model} 的单价，将使用 vision 参考价")
        self.model = model
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        self.budget = budget_usd
        self.spent = 0.0
        self.max_retries = max_retries

    def _cost(self, p: int, c: int) -> float:
        rate = PRICE.get(self.model, PRICE[VISION_MODEL])
        return p / 1000 * rate["prompt"] + c / 1000 * rate["completion"]

    def _build_multimodal_content(
        self,
        text: str,
        images: List[Dict[str, Any]],
    ) -> Union[str, List[Dict[str, Any]]]:
        """将文本与图片 block 合并为 content。"""
        if not images:
            return text
        content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        content.extend(images)
        return content

    def ask(
        self,
        user_input: str,
        images: List[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> str:
        """
        发送单轮请求。

        参数：
            user_input: 文本问题
            images: OpenAI 兼容的 image block 列表，可通过以下工具函数生成：
                    image_block_from_file / image_block_from_url / image_block_from_file_id
            stream: 是否流式输出
        """
        images = images or []
        content = self._build_multimodal_content(user_input, images)
        self.messages.append({"role": "user", "content": content})
        wait = 1
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if stream:
                    chunks = []
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=self.messages,
                        stream=True,
                    )
                    for chunk in resp:
                        delta = chunk.choices[0].delta.content or ""
                        chunks.append(delta)
                        print(delta, end="", flush=True)
                    print()
                    reply = "".join(chunks)
                    # 流式无 usage，按字符粗略估算；非 vision 场景可忽略
                    est_p, est_c = len(user_input) + len(images) * 384, len(reply)
                else:
                    resp = client.chat.completions.create(
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
                return reply
            except BudgetExceeded:
                raise
            except Exception as e:
                last_exception = e
                # 服务端明确不支持图片时直接抛错，不再重试
                if "does not support image" in str(e).lower() or "file" in str(e).lower() and "not found" in str(e).lower():
                    raise UnsupportedMediaError(f"模型/服务端拒绝该输入：{e}") from e
                print(f"[重试 {attempt}/{self.max_retries}] {e}")
                if attempt < self.max_retries:
                    time.sleep(wait)
                    wait *= 2
                else:
                    raise RuntimeError(f"重试耗尽，最后异常：{last_exception}") from last_exception
        raise RuntimeError("重试耗尽")

    def describe_image(self, image_path: Union[str, Path], prompt: str = "描述这张图片。", stream: bool = False) -> str:
        """便捷方法：描述单张本地图片。"""
        return self.ask(prompt, images=[image_block_from_file(image_path)], stream=stream)


if __name__ == "__main__":
    # 演示：纯文本（降级使用）+ 图片描述
    s = VisionChatSession(model=VISION_MODEL, budget_usd=0.05)
    print(s.ask("你好，请用一句话介绍自己。"))

    # 若当前目录有示例图片可取消下行注释运行
    # print(s.describe_image("example.jpg", prompt="这张图片里有什么？请用中文回答。", stream=True))
    print(f"[累计花费] ${s.spent:.4f}")
