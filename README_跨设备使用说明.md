# DeepSeek V4 Flash Vision 多模态调用包 · 跨设备使用说明

> 加载策略：**方式二 —— `.env` 跟随项目目录，换设备零配置、不改任何代码。**

---

## 一、包内文件

| 文件 | 作用 | 是否必需 |
|-----|------|---------|
| `demo_minimal.py` | 最小可运行示例（20 行验证图片识别） | 建议保留 |
| `w5_vision_chat_module.py` | 同步版 `VisionChatSession`（预算控制/重试/流式） | 必需（其他文件依赖它） |
| `w5_vision_chat_async.py` | 异步版（并发限流/熔断/流式） | 可选 |
| `w5_vision_pipeline.py` | 批量图片处理 + 链式视觉推理 + 结构化抽取 | 可选 |
| `.env` | 存放 `DEEPSEEK_API_KEY` | **必需** |
| `w5_vision_integration_guide.md` | API 参数与集成说明 | 参考文档 |
| `w5_vision_step_by_step_tutorial.md` | 分步教程 | 参考文档 |

---

## 二、新设备三步跑通

### 第 1 步：整个文件夹拷过去

放在任意目录都可以，推荐：

```
D:\WorkBuddyData\projects\agent-learning
```

**关键：`.env` 必须和这些 `.py` 文件放在同一个目录里**（保持现在的结构，不要单独把 `.env` 挪走）。

### 第 2 步：装依赖

```bash
cd /d 目标路径\deepseek-vision-multimodal
python -m venv venv
venv\Scripts\pip install openai python-dotenv
```

> Windows 跨盘符切换必须用 `cd /d`，否则不会真正切换盘符。  
> 如果创建 `venv` 时报 `WinError 5 拒绝访问`，见第六节第一项。

### 第 3 步：验证

在文件夹里放一张图片命名为 `example.jpg`，然后：

```bash
venv\Scripts\python demo_minimal.py
```

看到中文的图片描述输出即为成功。

---

## 三、为什么换设备不用改代码

四个 `.py` 文件里的加载逻辑都是这样：

```python
_ENV_FILE = Path(__file__).resolve().parent / ".env"   # 脚本自己所在目录
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()                                       # 回退：从当前工作目录向上找
```

- 用的是 **脚本所在目录**，不是当前工作目录，所以从任何盘符/目录运行都能找到 `.env`；
- 不含任何 Windows 用户名（不再写死 `C:\Users\shy`），换用户名照样能跑；
- 如果 `.env` 意外丢失，程序会直接抛出明确报错并提示应放置的路径，而不是报一个看不懂的 `KeyError`。

---

## 四、必读的三个注意点

1. **`.env` 含明文 API Key。** 不要提交到 git（`.gitignore` 加一行 `.env`），也不要长期放在会自动云同步的目录（OneDrive / 百度网盘 / 同步盘）。担心泄露时去 DeepSeek 控制台重置 Key，旧 Key 立即失效。
2. **模型名不能写错。** 必须是 `deepseek-v4-flash-vision-exp`，写成 `deepseek-chat` 或 `deepseek-v4-flash` 会退化为纯文本，传图片会报 400。
3. **`vision-exp` 是实验性模型。** 可能限流或不稳定，重要场景保留纯文本 `deepseek-v4-flash` 作为降级路径。

---

## 五、能力边界（避免误用）

| 输入类型 | 是否支持 |
|---------|---------|
| 图片（JPEG / PNG / GIF / WebP） | ✅ 支持 |
| 音频 | ❌ 不支持，需先用 ASR 转文本 |
| 视频 | ❌ 不支持，需先抽帧 + 转字幕 |
| PDF / Word | ❌ 模型不直接吃，需先抽取文本再传 |

---

## 六、常见报错速查

| 报错 | 原因 | 解决 |
|-----|------|------|
| `RuntimeError: 未找到 DEEPSEEK_API_KEY` | `.env` 不在脚本同目录 | 把 `.env` 放回和 `.py` 同一层 |
| `KeyError: 'DEEPSEEK_API_KEY'` | `.env` 里变量名拼错 | 检查是否为 `DEEPSEEK_API_KEY=sk-...` |
| `Connection error / timeout` | 网络或代理拦截 `api.deepseek.com` | 换网络、关代理或配置代理白名单 |
| `400 invalid request` | 模型名写错，或图片放进了 `system` 消息 | 模型改 `deepseek-v4-flash-vision-exp`，图片只放 `user` 消息 |
| `ModuleNotFoundError: openai` | 没装依赖或没用 venv | `venv\Scripts\pip install openai python-dotenv` |
| `ModuleNotFoundError: No module named 'dotenv'` | 执行时用了系统 Python，而不是 venv 里的 Python | 用 `venv\Scripts\python demo_minimal.py` 运行（不要直接 `python demo_minimal.py`），或先执行 `venv\Scripts\activate` 激活环境 |
| `Error: [WinError 5] 拒绝访问。: '...\\venv'` | 当前用户没有权限创建虚拟环境目录 | ① 右键 CMD/终端 →「以管理员身份运行」；② 或把文件夹移到用户目录如 `C:\Users\<用户名>\deepseek-vision-multimodal` 再创建 venv |
