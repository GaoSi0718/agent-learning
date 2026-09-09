# DeepSeek V4 Flash Vision-exp 扩展实现方案：分步细致教程

> 适用对象：已拥有 DeepSeek V4 Flash API Key，希望扩展 `deepseek-v4-flash-vision-exp` 多模态视觉能力的开发者。
> 前置知识：会使用 Python、已安装 `openai` SDK、了解基础的 API 调用。

---

## 一、核心目标（为什么要做这个扩展）

`deepseek-v4-flash-vision-exp` 是 DeepSeek 的实验性视觉模型，除文本外支持图片输入。本次扩展围绕 **3 个核心目标** 展开：

| 核心目标 | 说明 | 产出能力 |
|---------|------|---------|
| **1. 多模态视觉理解增强** | 在原有纯文本对话基础上，让模型能"看懂"图片 | 单张图片描述、OCR、图表分析 |
| **2. 图像批处理** | 一次性处理多张图片，提升效率 | 批量描述、批量 OCR、批量结构化抽取 |
| **3. 自定义视觉推理逻辑** | 支持多轮、链式、模板化的视觉任务 | 先看图→再 OCR→再提取 JSON→再判断类型 |

**一句话定位**：本方案不是让你"重新训练模型"，而是在现有 API 之上，搭一套**可复用、可编排、可批量**的视觉推理工程层。

---

## 二、前置条件与环境准备

### 2.1 确认已拥有的资源

根据你截图中的信息，你已具备：

- **API Key**：形如 `sk-eab6a****d97c`，可在 DeepSeek 控制台查看
- **可用模型**：
  - `deepseek-v4-flash`
  - `deepseek-v4-pro`
  - `deepseek-v4-flash-vision-exp`（本次目标）
- **Base URL**：`https://api.deepseek.com`

### 2.2 环境检查清单

在终端依次执行：

```bash
# 进入项目目录（Windows 跨盘符切换目录必须用 cd /d）
cd /d D:\WorkBuddyData\projects\agent-learning

# 激活虚拟环境
venv\Scripts\activate

# 检查 openai SDK 版本
python -c "import openai; print(openai.__version__)"
# 期望输出 >= 1.0.0
```

若版本过低：

```bash
pip install -U "openai>=1.0.0"
```

### 2.3 API Key 配置

继续在项目根目录创建或确认 `.env` 文件：

```bash
DEEPSEEK_API_KEY=sk-eab6a********************d97c
```

> ⚠️ 不要把 `.env` 提交到 git（在 `.gitignore` 里加一行 `.env`）。
>
> **加载策略（当前实现，跨设备零配置）**：所有 `w5_vision_*.py` 与 `demo_minimal.py` 均采用「`.env` 跟随项目目录」——
> 优先读取**脚本自身所在目录**下的 `.env`，找不到才回退到当前工作目录向上查找。
> 因此换设备时只需把整个项目文件夹（含 `.env`）拷过去，**无需修改任何代码**，也不依赖 Windows 用户名。
>
> ```python
> _ENV_FILE = Path(__file__).resolve().parent / ".env"
> if _ENV_FILE.exists():
>     load_dotenv(_ENV_FILE)
> else:
>     load_dotenv()
> ```
>
> 好处：即使从别的盘符/目录运行（如 `cd C:\ && python D:\WorkBuddyData\projects\agent-learning\demo_minimal.py`），也能正确定位到项目里的 `.env`。

---

## 三、第一步：最小可用视觉调用

目标：用 20 行代码验证 `deepseek-v4-flash-vision-exp` 能识别图片。

### 3.1 单张本地图片 base64 调用

在项目根目录准备一张图片 `example.jpg`，然后新建 `demo_minimal.py`：

```python
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
```

运行：

```bash
python demo_minimal.py
```

若看到正常的中文图片描述，说明环境、Key、模型均配置正确。

### 3.2 关键参数解释

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| `model` | string | 是 | 固定 `"deepseek-v4-flash-vision-exp"` |
| `messages[].content` | array | 是 | 必须是数组，不能是字符串 |
| `content[].type` | string | 是 | `"text"` / `"image_url"` |
| `image_url.url` | string | 是 | 外部 URL 或 `data:image/jpeg;base64,...` |
| `image_url.detail` | string | 否 | `low`/`high`/`original`/`auto`，控制图片缩放 |

---

## 四、第二步：封装可复用的视觉会话层

目标：把"预算、重试、流式、错误处理"封装成类，避免每次都写样板代码。

我们已在项目中提供：

- `w5_vision_chat_module.py` —— 同步版 `VisionChatSession`
- `w5_vision_chat_async.py` —— 异步版 `VisionAsyncChatSession`

### 4.1 同步版基本用法

```python
from w5_vision_chat_module import VisionChatSession, image_block_from_file

session = VisionChatSession(model="deepseek-v4-flash-vision-exp", budget_usd=0.1)

# 方式 1：直接描述单张图
reply = session.describe_image("example.jpg")
print(reply)

# 方式 2：自定义问题 + 多张图
img1 = image_block_from_file("example.jpg")
img2 = image_block_from_file("example2.jpg")
reply = session.ask(
    "请对比这两张图片，告诉我它们最明显的 3 个不同点。",
    images=[img1, img2],
)
print(reply)
```

### 4.2 异步版基本用法

```python
import asyncio
from w5_vision_chat_async import VisionAsyncChatSession, image_block_from_file

async def main():
    session = VisionAsyncChatSession(budget_usd=0.1, concurrency=2)
    reply = await session.ask(
        "描述这张图片",
        images=[image_block_from_file("example.jpg")],
    )
    print(reply)

asyncio.run(main())
```

---

## 五、第三步：实现图像批处理

目标：一次性处理 N 张图片，每张图独立提问，结果统一返回。

### 5.1 使用 VisionPipeline 的 `batch_run`

```python
from w5_vision_pipeline import VisionPipeline, VisionTask, image_block_from_file

pipe = VisionPipeline(budget_usd=0.5)

tasks = [
    VisionTask(
        task_id="id_card_front",
        prompt="提取身份证正面的姓名、性别、民族、出生、住址、身份证号，以 JSON 返回。",
        images=[image_block_from_file("id_card_front.jpg")],
        expect_json=True,
    ),
    VisionTask(
        task_id="id_card_back",
        prompt="提取身份证反面的签发机关和有效期限，以 JSON 返回。",
        images=[image_block_from_file("id_card_back.jpg")],
        expect_json=True,
    ),
    VisionTask(
        task_id="resume_screenshot",
        prompt="这是一张简历截图，请提取姓名、学历、工作年限、技能、邮箱、电话。以 JSON 返回。",
        images=[image_block_from_file("resume.png")],
        expect_json=True,
    ),
]

results = pipe.batch_run(tasks, max_workers=3)

for r in results:
    print(f"[{r.task_id}] success={r.success}")
    if r.success:
        print(f"  content: {r.content[:120]}")
        print(f"  parsed: {r.parsed}")
        print(f"  cost: ${r.cost_usd:.6f}")
    else:
        print(f"  error: {r.error}")

print(f"总花费：${pipe.spent:.6f}")
```

### 5.2 批处理背后的机制

- 使用 `ThreadPoolExecutor` 并行发起 API 请求
- `max_workers` 控制并发数，避免触发速率限制
- 所有任务共享 `VisionPipeline` 的 `budget_usd` 预算上限
- 每个 `VisionResult` 独立记录 token 与成本

---

## 六、第四步：自定义视觉推理逻辑（链式 + 模板）

目标：让模型先看图，再 OCR，再结构化抽取，最后再判断一次——形成可配置的推理链。

### 6.1 使用内置模板

```python
from w5_vision_pipeline import VisionPipeline

pipe = VisionPipeline()

# 模板：describe / ocr / extract_card / compare / qa
r = pipe.extract_json("business_card.jpg", template_name="extract_card")
print(r.parsed)
```

### 6.2 自定义模板

在 `w5_vision_pipeline.py` 中修改 `VISION_TEMPLATES`，或运行时传入完整 prompt：

```python
from w5_vision_pipeline import VisionPipeline, VisionTask, image_block_from_file

pipe = VisionPipeline()

task = VisionTask(
    task_id="custom_invoice",
    prompt="""
    你是一名财务审核助手。请从这张发票图片中提取以下字段，并以 JSON 返回：
    {
      "发票代码": "",
      "发票号码": "",
      "开票日期": "",
      "购买方": "",
      "销售方": "",
      "金额合计": "",
      "税率": "",
      "价税合计": ""
    }
    缺失字段填 null，不要编造。
    """.strip(),
    images=[image_block_from_file("invoice.jpg")],
    expect_json=True,
)

result = pipe.run(task)
print(result.parsed)
```

### 6.3 链式推理（多轮看图）

```python
from w5_vision_pipeline import VisionPipeline

pipe = VisionPipeline()

steps = [
    "请先用一段话描述这张图片的整体内容。",
    "请提取图片中所有可见文字。",
    "根据以上信息，判断这是否是一份正式合同，并给出理由。",
]

results = pipe.chain("contract_scan.jpg", steps)

for r in results:
    print(f"\n=== {r.task_id} ===")
    print(r.content)
```

**链式推理的优势**：
- 第一轮先拿到全局描述
- 第二轮聚焦 OCR 文字
- 第三轮做高阶判断
- 每轮共享上下文，模型能基于前面结果继续推理

---

## 七、第五步：把视觉能力集成到现有项目

### 7.1 集成到 `app.py` 简历工具

打开 `app.py`，把侧边栏模型选项改为：

```python
model = st.selectbox(
    "选择模型",
    ["deepseek-v4-flash", "deepseek-v4-flash-vision-exp"],
    index=0,
)
```

增加图片上传：

```python
uploaded_image = st.file_uploader(
    "上传简历截图/证件照（可选）",
    type=["jpg", "jpeg", "png", "gif", "webp"],
)

images = []
if uploaded_image:
    import base64
    b64 = base64.b64encode(uploaded_image.read()).decode()
    mime = uploaded_image.type or "image/jpeg"
    images.append({
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    })
```

调用时：

```python
content = [{"type": "text", "text": SYSTEM_PROMPT + "\n\n" + final_text}]
content.extend(images)

resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": content}],
    response_format={"type": "json_object"},
    temperature=temperature,
)
```

---

## 八、第六步：测试验证

### 8.1 验证清单

| 验证项 | 命令 | 期望结果 |
|-------|------|---------|
| 语法检查 | `python -m py_compile w5_vision_pipeline.py` | 无报错 |
| 最小调用 | `python demo_minimal.py` | 输出图片描述 |
| 单图描述 | 取消 `w5_vision_chat_module.py` 底部注释运行 | 输出描述 |
| 批量处理 | 准备多张图片后运行 pipeline 脚本 | 输出每张结果 |
| 链式推理 | 准备一张合同/简历截图运行 | 三轮结果连续 |

### 8.2 一个完整的端到端测试脚本

创建 `test_vision_e2e.py`：

```python
import os
from w5_vision_pipeline import VisionPipeline, VisionTask, image_block_from_file

def test_minimal():
    pipe = VisionPipeline(budget_usd=0.05)
    r = pipe.describe("example.jpg")
    assert r.success, f"描述失败：{r.error}"
    print("✅ 单图描述通过")

def test_batch():
    if not os.path.exists("example2.jpg"):
        print("⚠️ 跳过批量测试：缺少 example2.jpg")
        return
    pipe = VisionPipeline(budget_usd=0.2)
    tasks = [
        VisionTask("t1", "描述图片", [image_block_from_file("example.jpg")]),
        VisionTask("t2", "描述图片", [image_block_from_file("example2.jpg")]),
    ]
    results = pipe.batch_run(tasks, max_workers=2)
    assert all(r.success for r in results)
    print("✅ 批量处理通过")

def test_chain():
    pipe = VisionPipeline(budget_usd=0.1)
    results = pipe.chain("example.jpg", [
        "描述图片。",
        "提取图片中所有文字。",
    ])
    assert all(r.success for r in results)
    print("✅ 链式推理通过")

if __name__ == "__main__":
    test_minimal()
    test_batch()
    test_chain()
```

运行：

```bash
python test_vision_e2e.py
```

---

## 九、关键限制与踩坑点

| 坑点 | 说明 | 规避方法 |
|-----|------|---------|
| 图片只能放在 `user` 消息 | `system`/`assistant` 带图片会 400 | 永远把图片放在 `user` 的 `content` 数组里 |
| 单张图片 32 MiB 上限 | base64 / URL 图片均受此限制 | 大图先用 Pillow 压缩或改用 Files API |
| 请求体 48 MiB 上限 | 多图 base64 容易超限 | 超过 2-3 张大图改用 Files API `file_id` |
| 不支持音频/视频 | 该实验模型仅支持图片 | 音频用 Whisper，视频先抽帧 |
| `expect_json=True` 但返回非 JSON | 模型未按要求输出 | 在 prompt 里明确写"只输出 JSON"，并捕获解析异常 |
| 预算共享导致批量提前失败 | `VisionPipeline.spent` 是共享的 | 批量前预估总成本，或每个任务新建 pipeline |
| 流式无 `usage` | 流式响应不返回 token 数 | 按字数/图片数粗略估算，非精确计费 |

---

## 十、可继续扩展的方向

1. **接入 Files API**：对超过 32 MiB 或需复用的图片，先 `client.files.create()` 上传，再用 `file_id` 引用。
2. **加入 Agent 工具**：把 `VisionPipeline` 注册为 LangChain / 自定义 Agent 的工具，让 LLM 决定何时看图。
3. **做 HR 证件/合同识别专项**：基于 `extract_json` 模板，固化身份证、银行卡、合同、简历等结构化抽取 prompt。
4. **异步批量**：在 `w5_vision_chat_async.py` 基础上实现 `asyncio.gather` 批量，适合高并发场景。

---

## 参考文件

| 文件 | 作用 |
|-----|------|
| `w5_vision_chat_module.py` | 同步基础封装 |
| `w5_vision_chat_async.py` | 异步基础封装 |
| `w5_vision_pipeline.py` | 批处理 + 链式推理 |
| `w5_vision_integration_guide.md` | API 参数与集成说明 |
| `w5_vision_step_by_step_tutorial.md` | 本教程 |
