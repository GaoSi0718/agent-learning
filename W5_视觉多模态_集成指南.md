# DeepSeek V4 Flash Vision 多模态扩展方案

> 目标：在已有的 DeepSeek V4 Flash API 调用基础上，扩展 `deepseek-v4-flash-vision-exp` 的图片理解能力，保持代码风格与现有 `w4_chat_module.py`、`w4_chat_async.py` 一致。

---

## 1. 能力边界（关键前提）

根据 DeepSeek 官方文档，`deepseek-v4-flash-vision-exp` 目前**仅支持图片输入**，**不支持音频、视频或通用文件输入**。

| 媒体类型 | 是否支持 | 说明 |
|---------|---------|------|
| 图片（JPEG/PNG/GIF/WebP） | ✅ 支持 | 可通过 base64 内联 / 外部 URL / Files API `file_id` 三种方式传入 |
| 音频 | ❌ 不支持 | 当前模型无音频理解能力 |
| 视频 | ❌ 不支持 | 当前模型无视频理解能力；如需处理视频，需先抽帧为图片 |
| 通用文件（PDF/Word/Excel 等） | ❌ 不支持 | 仅当文件本质是图片格式时才可上传；文档需先提取文本 |

**结论**：本次扩展聚焦「图片输入」，音频/视频不在该实验模型的能力范围内；若后续 DeepSeek 开放音频/视频接口，只需新增对应 content block 类型即可沿用同一套封装结构。

---

## 2. 接口调用方式

DeepSeek API 使用与 OpenAI 兼容的对话补全格式。调用视觉模型时：

- `model` 固定为 `"deepseek-v4-flash-vision-exp"`
- `base_url` 保持 `"https://api.deepseek.com"`
- `messages` 中 `user` 角色的 `content` 从**纯字符串**扩展为**数组（content blocks）**

### 2.1 请求地址与认证

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
```

### 2.2 基础调用（文本 + 图片 base64）

```python
resp = client.chat.completions.create(
    model="deepseek-v4-flash-vision-exp",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "这张图片里有什么？"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."},
                },
            ],
        }
    ],
)
print(resp.choices[0].message.content)
```

### 2.3 响应格式

与文本模型一致：

```python
{
  "choices": [{"message": {"role": "assistant", "content": "..."}}],
  "usage": {"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168}
}
```

---

## 3. 请求参数结构

### 3.1 `content` 数组元素类型

| 类型 | 字段 | 必填 | 说明 |
|-----|------|-----|------|
| `text` | `text` | 是 | 文本内容 |
| `image_url` | `image_url.url` | 是 | 图片 URL 或 `data:image/xxx;base64,...` |
| `image_url` | `image_url.detail` | 否 | `low`/`high`/`original`/`auto`，控制图片缩放 |
| `file` | `file_id` | 是（与 `file_data` 互斥） | Files API 返回的 ID，如 `file-api-xxx` |
| `file` | `file_data` | 是（与 `file_id` 互斥） | base64 data URL |
| `file` | `filename` | 否 | 配合 `file_data` 使用 |

### 3.2 `image_url.detail` 取值

| 取值 | 行为 |
|-----|------|
| `low` | 缩放至 512×512，更快更省 token |
| `high`/`original` | 保留原图 |
| `auto` | 当前等价于 `original` |

### 3.3 官方限制

| 限制项 | 数值 |
|-------|------|
| 支持格式 | JPEG、PNG、GIF、WebP |
| 外部 URL 长度 | ≤ 8192 字符 |
| 请求体大小 | ≤ 48 MiB |
| 单张图片最大（base64 / 外部 URL） | ≤ 32 MiB |
| 单张图片最大（Files API `file_id`） | ≤ 64 MiB |
| 单个请求最大图片数 | ≤ 600 张 |
| 单图 token 消耗上限 | 384 tokens |
| 图片位置 | 仅允许出现在 `user` 消息中；`system`/`assistant` 携带图片会返回 400 |

---

## 4. 现有代码集成方案

### 4.1 新增文件

为了保持 W4 学习成果不被覆盖，本次采用「新增 W5 文件」而非直接修改 W4 文件：

| 文件 | 说明 |
|-----|------|
| `w5_vision_chat_module.py` | 同步版多模态 `VisionChatSession` |
| `w5_vision_chat_async.py` | 异步版多模态 `VisionAsyncChatSession` |
| `w5_vision_integration_guide.md` | 本方案文档 |

### 4.2 与现有 `w4_chat_module.py` 的差异点

| 项目 | W4 | W5 变更 |
|-----|-----|---------|
| 模型名 | `deepseek-chat` | 默认 `deepseek-v4-flash-vision-exp`，保留切换能力 |
| `content` | 纯字符串 | 支持字符串或 content block 数组 |
| 输入 | 仅文本 | 文本 + 图片（base64 / URL / file_id） |
| 新增工具函数 | 无 | `image_block_from_file` / `image_block_from_url` / `image_block_from_file_id` |
| 异常 | `BudgetExceeded` | 新增 `UnsupportedMediaError` |
| 价格字典 | 单一 | 按模型名索引，vision 与文本模型分别定价 |

### 4.3 三种图片传入方式示例

```python
from w5_vision_chat_module import VisionChatSession, image_block_from_file, image_block_from_url, image_block_from_file_id

session = VisionChatSession(model="deepseek-v4-flash-vision-exp", budget_usd=0.1)

# 方式一：本地文件 base64 内联
img1 = image_block_from_file("example.jpg", detail="auto")

# 方式二：外部 URL
img2 = image_block_from_url("https://example.com/image.jpg", detail="low")

# 方式三：Files API file_id
img3 = image_block_from_file_id("file-api-xxxxxxxxxxxxxxxx")

reply = session.ask(
    "请对比这三张图片的共同点。",
    images=[img1, img2, img3],
    stream=False,
)
```

### 4.4 在 `app.py` 中集成（简历抽取工具升级示例）

若想让简历抽取工具也支持「上传证件照/截图并分析」，可在 `app.py` 中替换模型并增加图片上传：

```python
# 替换模型
VISION_MODEL = "deepseek-v4-flash-vision-exp"

# 新增图片上传组件
uploaded_image = st.file_uploader("上传证件照/截图（可选）", type=["jpg", "jpeg", "png", "gif", "webp"])
images = []
if uploaded_image:
    import base64, io
    b64 = base64.b64encode(uploaded_image.read()).decode()
    mime = uploaded_image.type or "image/jpeg"
    images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

# 调用时传入 images
resp = client.chat.completions.create(
    model=VISION_MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [{"type": "text", "text": final_text}] + images},
    ],
)
```

---

## 5. 错误处理

### 5.1 已覆盖的错误场景

| 场景 | 处理方式 |
|-----|---------|
| 本地图片不存在 | `FileNotFoundError` |
| 单张图片 > 32 MiB | `ValueError`（仅 base64/URL 路径） |
| 外部 URL > 8192 字符 | `ValueError` |
| 模型不支持图片 | 识别服务端返回的 `does not support image`，抛出 `UnsupportedMediaError` |
| Files API file_id 不存在 | 抛出 `UnsupportedMediaError` |
| 网络/API 异常 | 按 W4 原有指数退避重试，最终抛出 `RuntimeError` |
| 预算超限 | 抛出 `BudgetExceeded` |

### 5.2 异常类定义

```python
class BudgetExceeded(Exception):
    pass

class UnsupportedMediaError(Exception):
    """当前模型不支持该媒体类型或服务端拒绝该输入。"""
    pass
```

---

## 6. 快速验证

### 6.1 环境要求

- `openai>=1.0.0`
- 已配置 `DEEPSEEK_API_KEY`
- Python 3.10+

### 6.2 运行同步示例

```bash
D:\WorkBuddyData\projects\agent-learning\venv\Scripts\python w5_vision_chat_module.py
```

### 6.3 运行异步压测

```bash
D:\WorkBuddyData\projects\agent-learning\venv\Scripts\python w5_vision_chat_async.py
```

若当前目录无 `example.jpg`，压测会自动降级为文本请求，用于验证代码兼容性。

---

## 7. 待确认/后续扩展

1. **真实单价**：代码中 `PRICE` 使用参考价，请根据 DeepSeek 官网最新定价更新。
2. **音频/视频**：当前模型不支持；若未来开放，可新增 `audio_block_*` / `video_block_*` 工具函数，并在 `UnsupportedMediaError` 之外增加对应校验。
3. **Files API 上传**：`file_id` 方式需要先调用 `client.files.create(...)`，本方案未封装上传流程，可后续单独抽出 `upload_image_to_deepseek(file_path)` 工具函数。

---

## 8. 参考链接

- DeepSeek 图像理解文档：https://api-docs.deepseek.com/zh-cn/guides/vision
- DeepSeek Files API：https://api-docs.deepseek.com/zh-cn/guides/files_api
