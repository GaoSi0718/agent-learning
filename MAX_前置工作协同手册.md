# MAX 新设备 · Agent 学习路线前置工作协同手册

> 🗄️ **本文档为历史存档（2026-08-29 更新）**
>
> **迁移已于 2026-08-28 全部完成**，shy 旧机退役、MAX 成为当前唯一设备，文中"待做"事项均已结束。
> 本文保留仅作**过程记录**（当时如何分工、踩过什么坑），**不要再按它执行任何步骤**。
>
> **当前你需要看的文档**：
> - 环境与运行 → `README.md`
> - W7 执行 → `W7_本周执行清单.md`
> - 跨设备同步 → `stage1_review.md` §7（已按"单机"现状简化）

> **目的（历史）**：在把 `agent-learning` 项目迁移到新设备 **MAX** 之前，明确「迪莫（本机）」与「MAX（新设备）」两方的分工与前置工作，做到迁移后**零配置跑通、不丢进度、不泄露密钥**。
> **适用对象（历史）**：孟轩在 MAX 上操作时照第 2 节执行；迪莫照第 3 节执行；第 4 节是双方对齐的时序。

---

## 0. 当前基线（已核实，2026-08-28）

| 项 | 状态 |
|----|------|
| 学习进度 | W1–W5 已完成（W5 多模态 8/26 收尾），W6（HR 政策问答助手）+ 阶段二 ML/DL 补课待推进 |
| 项目路径（本机） | `D:\WorkBuddyData\projects\agent-learning` |
| Git | **无远程**；最后一次 commit 停在 W4；W5 全部文件未提交 |
| 同步状态 | 项目不在 OneDrive 等同步目录，**未自动同步到 MAX** |
| 密钥 | `.env` 含明文 `DEEPSEEK_API_KEY`，已被 `.gitignore` 忽略（安全） |
| 残留文件 | 7 个 0 字节空文件（可删）；`.cleanup_stash/` 含 2 张图片（用途未明，暂保留） |

---

## 1. 分工总览

| 事项 | 负责方 | 前置条件 | 状态 |
|------|--------|----------|------|
| 提交 W5 到本地 git（防迁移丢进度） | 迪莫 | 无 | 待做 |
| 预建 W6 脚手架 + RAG 模板（A） | 迪莫 | 无 | 待做 |
| 生成 W6 评估集（B） | 迪莫 | `policy_context.txt` | 待做 |
| 阶段二 ML/DL 资源包（C） | 迪莫 | 无 | 待做 |
| 框架/模型选型对比（D） | 迪莫 | 无 | 待做 |
| 整理迁移包（清残留、确认 .env 不入库） | 迪莫 | 无 | 待做 |
| 安装 Python 3.10+ | MAX | 无 | 待做 |
| 接收项目文件夹（含 .env） | MAX | 迪莫整理完 | 待做 |
| 建 venv + 装依赖 | MAX | 收到文件夹 | 待做 |
| 放置 `.env` 密钥 | MAX（手动） | 收到文件夹 | 待做 |
| 验证 `demo_minimal.py` | MAX | 依赖装好 | 待做 |
| 同步/复制文件夹到 MAX | 双方 | 整理完 + MAX 环境就绪 | 待做 |

---

## 2. MAX 侧前置工作（详细步骤）

### 2.1 安装 Python 3.10+
- 下载：https://www.python.org/downloads/ （勾选 **Add Python to PATH**）
- 验证命令：
  ```bash
  python --version
  ```
- **预期输出**：`Python 3.10.x` 或更高
- **踩坑**：若 `python` 指向旧版本，用 `py -3.10` 或重装并勾选 PATH。

### 2.2 接收项目文件夹
- 从迪莫处拿到**整个** `agent-learning` 文件夹（必须含 `.env`）。
- 放任意目录，推荐：`D:\WorkBuddyData\projects\agent-learning`
- ⚠️ **整文件夹一起拷**，不要只拷 `.py`——`.env` 与 `.py` 必须在同一层目录。

### 2.3 创建虚拟环境并装依赖
```bash
cd /d 目标路径\agent-learning
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```
- `requirements.txt` 内容：`streamlit / openai / python-docx / PyPDF2 / python-dotenv`
- **预期输出**：末尾显示 `Successfully installed ...`
- **踩坑**：
  - `WinError 5 拒绝访问` → 右键终端「以管理员身份运行」再建 venv；
  - `ModuleNotFoundError` → 必须用 `venv\Scripts\python xxx.py` 运行，别直接用 `python`。

### 2.4 放置 `.env`（安全红线）
- 文件内容（仅一行）：
  ```
  DEEPSEEK_API_KEY=sk-你的真实key
  ```
- 必须与 `.py` 文件放在**同一目录**。
- ⚠️ **不要把 `.env` 放进 OneDrive / 百度网盘 / 任意自动云同步目录**——明文 Key 上云有泄露风险。丢失 Key 去 DeepSeek 控制台重置即可。

### 2.5 验证跑通
```bash
venv\Scripts\python demo_minimal.py
```
- 文件夹里放一张图命名为 `example.jpg`。
- **预期输出**：一段中文的图片描述（如「这是一张……」）。
- 看到中文描述 = 环境 OK，可通知迪莫继续推送 W6 脚手架。

### 2.6 与迪莫的对齐点
- 跑通 2.5 后，**截图/告知迪莫**「MAX 已验证」。
- 迪莫随后把 W6 脚手架等增量文件复制给你，你再跑 W6 demo 验证。

---

## 3. 迪莫本机侧前置工作（详细步骤）

### 3.1 提交 W5（防迁移丢进度）
```bash
cd D:/WorkBuddyData/projects/agent-learning
git add w5_vision_chat_module.py w5_vision_chat_async.py w5_vision_pipeline.py \
        w5_vision_integration_guide.md w5_vision_step_by_step_tutorial.md \
        demo_minimal.py example.jpg README_跨设备使用说明.md app.py \
        policy_context.txt route_resource_evaluation.html MAX_前置工作协同手册.md .gitignore
git commit -m "W5 多模态收尾 + 跨设备说明 + 资源评估 + MAX 协同手册"
```
- 校验：`.env` 不应出现在 `git status` 中（已被忽略）。

### 3.2 预建 W6 脚手架 + RAG 模板（A）
- 复用 `w4_chat_module.py` 的预算/重试封装 + `w5_vision_chat_module.py` 的多模态。
- 产出：`w6_hr_qa_app.py`（Streamlit 问答骨架）+ `w6_rag_retriever.py`（本地向量库 Chroma/FAISS，免服务器）。
- 省下：约 8–12h 胶水代码，MAX 侧只需填政策文本、调 prompt。

### 3.3 生成 W6 评估集（B）
- 基于 `policy_context.txt` 预生成 30–50 条典型问答 + 标准答案（对标 W3 的 `resumes_30_groundtruth.json` 做法）。
- 配合 W4 预算逻辑做成本护栏，避免开发期反复端到端烧 Token。

### 3.4 阶段二 ML/DL 资源包（C）
- 课程清单（吴恩达 / 李宏毅 / 泡蛋等）、数学先修顺序（线代→概率→微积分）、与 Agent 相关的重点章节（Transformer / 注意力 / RAG 底层）、带「停止条件」的周计划。

### 3.5 框架/模型选型对比（D）
- 对比 LangChain / LlamaIndex / 原生 OpenAI SDK（你已有 w4 封装，大概率无需重框架）；
- 多模态模型对比：DeepSeek vision / Qwen-VL / GLM-4V。

### 3.6 整理迁移包
- 删除 7 个 0 字节残留：`1.0.0` `1.1.0` `1.30.0` `3.0.0` `float` `str` `（若未激活先`
- 确认 `.env` 被 `.gitignore` 忽略（已验证）。
- `.cleanup_stash/`（2 张图片）用途未明，**暂保留**，待你确认。

### 3.7 设置自动化（1–5，可选）
1. 每日 09:40 AI 资讯 → 每周五自动生成下周学习重点；
2. 生成文档自动上传 ima「Agent学习路线」知识库（符合上传约定）；
3. 进度笔记自动追加；
4. 周计划自动刷新（整合近一周 AI 动态）；
5. W6 跑批时 Token 预算自动守护（复用 w4 预算逻辑）。

---

## 4. 协同时序（建议路径）

```
[迪莫] 3.1–3.6 本机准备（不依赖 MAX）
   │
[MAX ] 2.1–2.4 环境 + 密钥（不依赖代码）
   │
[双方] 同步文件夹（U 盘 / 手动复制，含 .env）
   │
[MAX ] 2.5 验证 demo_minimal.py → 通知迪莫「MAX 已验证」
   │
[迪莫] 把 3.2–3.5 增量文件复制给 MAX
   │
[MAX ] 验证 W6 demo
```

> 两路可并行：迪莫准备代码的同时，MAX 先把环境搭好，能大幅压缩等待时间。

---

## 5. 安全红线（必读）

1. **`.env` 明文 Key 不上云同步**（OneDrive / 百度网盘 / 同步盘）——泄露风险。
2. **不提交 `.env` 到 git**（已 gitignore，提交前务必 `git status` 复核）。
3. 模型名必须 `deepseek-v4-flash-vision-exp`，写错退化为纯文本、传图报 400。
4. `vision-exp` 实验性，重要场景保留纯文本 `deepseek-v4-flash` 作为降级路径。
5. `.cleanup_stash/` 含 2 张图片，用途未明，**暂不动**，待你确认后再处理。

---

## 6. 完成判定清单

- [ ] MAX 上 `demo_minimal.py` 输出中文图片描述
- [ ] W5 已 commit 到本地 git
- [ ] 迁移包无 0 字节残留文件
- [ ] W6 脚手架可在 MAX 跑通
- [ ] 阶段二资源包就位
- [ ] （可选）自动化 1–5 已设置

---

## 7. 迪莫将交付的「前置」产出物（供 MAX 预期）

| 编号 | 产出物 | 说明 |
|------|--------|------|
| A | `w6_hr_qa_app.py` + `w6_rag_retriever.py` | W6 开箱即跑骨架 |
| B | `w6_eval_set.json` | 30–50 条 HR 问答 + 标准答案 |
| C | `stage2_mldl_roadmap.md` | 阶段二资源包 + 停止条件周计划 |
| D | `framework_model_selection.md` | 框架/模型选型对比 |
| F | 阶段一复盘 / 作品集说明 | 为 9 月作品上线铺垫 |
| 1–5 | 自动化配置 | 资讯周报 / ima 上传 / 进度笔记 / 周计划刷新 / Token 守护 |
