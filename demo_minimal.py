import os
import base64
from pathlib import Path
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

with open("example.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

resp = client.chat.completions.create(
    model="deepseek-v4-flash-vision-exp",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请用中文描述这张图片里有什么。"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ],
        }
    ],
)
print(resp.choices[0].message.content)
