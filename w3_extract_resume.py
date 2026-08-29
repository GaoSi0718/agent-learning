"""
W3 简历关键信息抽取脚本（JSON 模式 + 校验 + 拒绝策略）
来源：阶段一待办清单 W3 产出物

运行：
  cd D:/WorkBuddyData/projects/agent-learning
  venv\Scripts\activate
  python w3_extract_resume.py

输入：一段简历文本
输出：结构化 JSON（姓名/邮箱/电话/技能/工作年限/教育），缺失字段一律 null
安全：模型输出必须可校验、不可全信（见待办清单"安全习惯前置"）
"""
import json
import os

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
MODEL = "deepseek-chat"

# JSON Schema 约束输出结构（结构化输出的"可校验"前提）
SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "years_of_experience": {"type": ["number", "null"]},
        "education": {"type": "string"},
        "is_resume": {"type": "boolean", "description": "输入是否为简历，否=拒绝"},
    },
    "required": ["name", "email", "phone", "skills", "years_of_experience", "education", "is_resume"],
}


def _extract_json(text: str) -> dict:
    """从模型返回中提取 JSON（兼容裸 JSON 和 ```json 包裹）。"""
    import re
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 ```json ... ``` 中的内容
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 尝试提取第一个 { ... } 对象
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"无法从返回中提取有效 JSON:\n{text[:500]}")


def extract(text: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是 HR 简历信息抽取助手。你必须且只能输出一个 JSON 对象，"
                    "不要输出任何其他文字、解释或 markdown 标记。\n\n"
                    "JSON schema 如下：\n"
                    + json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n\n"
                    "规则：\n"
                    "- 缺失字段填 null\n"
                    "- 若输入不是简历，is_resume 填 false 且其余字段置空字符串/null\n"
                    "- skills 必须是字符串数组"
                ),
            },
            {"role": "user", "content": text},
        ],
        # 注意：DeepSeek 不支持 response_format，改用 prompt 约束 + 后处理
    )
    raw = resp.choices[0].message.content.strip()
    data = _extract_json(raw)
    return data


def validate(data: dict) -> bool:
    """拒绝策略：非简历或关键字段全空则视为不可信。"""
    if not data.get("is_resume"):
        print("[拒绝] 输入不是简历，已拒绝抽取。")
        return False
    has_any = any([
        data.get("name"), data.get("email"), data.get("phone"),
        data.get("skills"), data.get("education"),
    ])
    if not has_any:
        print("[拒绝] 抽取结果为空，疑似模型幻觉，已拒绝。")
        return False
    return True


if __name__ == "__main__":
    sample = """
    张伟 | 资深 Python 工程师
    邮箱 zhangwei@example.com / 电话 138-0000-1234
    技能：Python, FastAPI, PostgreSQL, Docker
    5 年工作经验，本科计算机科学
    """
    result = extract(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    validate(result)
