# Agent 学习路线 · 代码库

阶段一（LLM 应用基础）**W2–W6** 的实战脚本、数据集与评估集。

> **当前进度（2026-08-29）**：W2–W6 代码骨架已全部跑通，核心能力（预算护栏 / 指数退避重试 / 异步限流熔断 / 多模态 / 本地 RAG）已沉淀为**可复用模块**。
> **下一步**：向 `policy_context.txt` 灌入真实 HR 政策数据，跑全量 `w6_eval_runner.py` 评估。

---

## 1. 环境搭建

```bash
cd D:/WorkBuddyData/projects/agent-learning

# 创建并激活虚拟环境（Windows）
python -m venv venv
venv\Scripts\activate                 # macOS/Linux: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**密钥配置**：在项目根目录创建 `.env`（已在 `.gitignore` 中，不入库）：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> 所有脚本遵循同一约定：**优先读取脚本同级目录下的 `.env`**，找不到才向上查找。因此在任何设备、任何工作目录下运行都不会 Key 丢失。

**依赖说明**：`requirements.txt` 只含主线（W2–W6 根目录脚本）必需的 5 个包。
可选的语义检索方案需额外安装，见 [§5 W6 两套检索方案](#5-w6-两套检索方案重要)。

---

## 2. 脚本一览

| 文件 | 周次 | 能力 | 状态 |
|------|------|------|------|
| `w2_chat_cli.py` | W2 | 多轮 CLI 问答：指数退避重试 + token 统计 + 代码输出保险 | ✅ |
| `w3_extract_resume.py` | W3 | 简历关键信息抽取：DeepSeek 兼容 JSON 模式 + 字段校验 + 拒绝策略 | ✅ |
| `w3_batch_eval.py` | W3 | 批量评测：读 30 条简历 + 标准答案，输出各字段准确率（已 100% 达标） | ✅ |
| `w4_chat_module.py` | W4 | **同步 chat 封装**：预算上限 + 指数退避 + 流式输出（下游模块的基础依赖） | ✅ |
| `w4_chat_async.py` | W4 | **异步封装**：Semaphore 限流 + 熔断 + 退避 + 流式 + 预算；自带 50 并发压测 | ✅ |
| `w4_price_quality.py` | W4 | 两模型在 10 个固定任务上对比「价格 vs 质量」 | ✅ |
| `app.py` | W5 | **简历抽取网页工具**：上传 docx/pdf 直接抽取结构化字段（Streamlit） | ✅ |
| `demo_minimal.py` | W5 | 视觉最小示例：对 `example.jpg` 做图片理解，验证多模态链路连通性 | ✅ |
| `w5_vision_chat_module.py` | W5 | 视觉会话封装（`VisionChatSession`），供下游复用 | ✅ |
| `w5_vision_chat_async.py` | W5 | 视觉异步版本 | ✅ |
| `w5_vision_pipeline.py` | W5 | 视觉批处理流水线 | ✅ |
| `w6_rag_retriever.py` | W6 | **本地 BM25 检索器**（零依赖，主线检索方案） | ✅ |
| `w6_hr_qa_app.py` | W6 | **HR 政策问答助手**（Streamlit，主线应用入口） | ✅ |
| `w6_eval_runner.py` | W6 | 评估集跑批：40 条问答，输出关键词命中率，含双层预算护栏 | ✅ |

**模块复用链**（主线自洽，改一处即全链路生效）：

```
w4_chat_module.ChatSession ──┬──> w6_hr_qa_app.py
                             └──> w6_eval_runner.py
w5_vision_chat_module ───────────> w6_hr_qa_app.py（多模态问答，可选）
w6_rag_retriever.PolicyRetriever ─> w6_hr_qa_app.py + w6_eval_runner.py
```

---

## 3. 快速开始

```bash
# ── W2 多轮对话 ──
python w2_chat_cli.py

# ── W3 简历抽取（单条 / 批量评测 30 条）──
python w3_extract_resume.py
python w3_batch_eval.py

# ── W4 同步封装 / 异步 50 并发压测 / 价格质量对比 ──
python w4_chat_module.py
python w4_chat_async.py
python w4_price_quality.py

# ── W5 简历抽取网页工具 / 视觉最小示例 ──
streamlit run app.py
python demo_minimal.py              # 会读取 example.jpg

# ── W6 HR 政策问答助手（主线应用）──
streamlit run w6_hr_qa_app.py

# ── W6 评估集跑批 ──
python w6_eval_runner.py --max-q 5 --per-q 0.005   # 先小批量试 5 条
python w6_eval_runner.py                            # 全量 40 条（总预算护栏 0.10 USD）
```

---

## 4. 数据集与素材

| 文件 | 用途 |
|------|------|
| `resumes_30.txt` + `resumes_30_groundtruth.json` | W3 批量评测用 30 条简历及标准答案 |
| `boundary_samples.txt` | W3 边界样例（字段缺失 / 格式混乱 / 多候选人） |
| `example.jpg` | W5 视觉示例图片，`demo_minimal.py` 默认读取它 |
| `w6_eval_set.json` | W6 评估集：40 条 HR 政策问答 + 标准答案 |
| `w6_sample_policy.txt` | W6 **示例**政策文本（当 `policy_context.txt` 为空时自动回退使用） |

---

## 5. W6 两套检索方案（重要）

W6 存在两套并存的检索实现，**定位和依赖关系不同，请勿混用**：

| 维度 | **主线：BM25 零依赖**（默认） | **可选进阶：语义向量** |
|------|------------------------------|------------------------|
| 位置 | 根目录 `w6_rag_retriever.py` | `w6_hr_qa/` 子目录 |
| 检索方式 | BM25 关键词匹配（中文 unigram + bigram） | bge-m3 语义向量 + Chroma |
| 依赖 | **零依赖**，仅 Python 标准库 | 需 `pip install chromadb` |
| 外网 / API Key | **完全不需要** | 需注册硅基流动拿 embedding Key |
| 启动速度 | 瞬时 | 首次需建索引 |
| 政策数据源 | `policy_context.txt`（留空则回退 `w6_sample_policy.txt`，5 章 15 条） | `w6_hr_qa/data/policies/*.md`（示例 7 章 24 条） |
| 适用 | 政策/制度类术语固定的文档（默认用这个） | 用户问法与文档用词差异大的场景 |

> ⚠️ **两套方案的示例政策数据内容不同**（上班时间 9:00 vs 8:30、工资发放 次月 10 日 vs 每月 15 日、调休 6 个月 vs 3 个月）。
> **同一个问题在两套方案下会得到不同答案，这是示例数据差异，不是程序错误。**
> 确定最终方案后，建议统一为一份政策源，并在正式使用前替换为公司真实制度。两份示例均为**虚构数据**，不可用于业务答复。

**为什么主线选 BM25**：依据 `framework_model_selection.md` 的选型结论——阶段一不引入重量级框架，自研轻量封装足以支撑 W6。BM25 方案零依赖、零外网、零阻塞，`pip install -r requirements.txt` 后立刻可跑。

**如何切换到向量方案**（仅在 BM25 召回不佳时才需要）：

```bash
pip install chromadb          # 额外依赖，主线不需要
# 在 .env 追加：SILICONFLOW_API_KEY=sk-xxxx（DeepSeek 不提供 embedding 接口）
cd w6_hr_qa && python ingest.py
```
详见 `w6_hr_qa/README.md`。

---

## 6. 目录约定

| 文件 / 目录 | 说明 |
|-------------|------|
| `policy_context.txt` | **默认为空文件**（这是设计，不是错误）。把真实 HR 政策粘贴进去即可生效；留空时 `PolicyRetriever` 会自动回退到 `w6_sample_policy.txt` 并在终端提示。 |
| `.env` | 存放 `DEEPSEEK_API_KEY`，已加入 `.gitignore`，不入库。 |
| `.gitignore` | 已忽略 `.env` / `venv/` / `__pycache__/` / `chroma_db/` / 评测结果文件。 |
| `venv/` | 虚拟环境，已加入 `.gitignore`。 |
| `w6_hr_qa/` | W6 **可选进阶**的语义检索方案（见 §5），主线不依赖它。 |
| `__pycache__/` | Python 字节码缓存，无需关注。 |

> ✅ **版本控制已启用（2026-08-29 17:25）**：本目录已完成 `git init` 并提交首个 commit（47 个文件）。
> `.gitignore` 现已**正式生效**——`.env` / `venv/` / `__pycache__/` / `chroma_db/` / 评测结果均不会被提交。
> 已验证：`.env` 未入库、`venv/` 未入库。
>
> ⚠️ **仍需注意**：git 只管"提交"，管不了"整夹拷贝"。
> 若用 U 盘/网盘复制整个文件夹（而非 `git clone`），`.env` 仍会被带走——拷贝前请手动排除。

---

## 7. 相关文档索引

| 文档 | 内容 | 何时看 |
|------|------|--------|
| **`W7_本周执行清单.md`** | **W7 的 1 页执行清单**（周一到周五拆到具体命令，用现成 `resumes_30_groundtruth.json`） | **现在做 W7 就看这个** |
| `stage1_review.md` | 阶段一（W1–W6）复盘与作品集说明 | 阶段一收尾后回顾 |
| `stage2_mldl_resource_pack.md` | ⚠️ **已降级为「理论资源索引」**（非执行计划）；周次编号与主线冲突，见其 §0 | 实操卡壳时查章节，**不要顺序执行** |
| `framework_model_selection.md` | Agent 框架与模型选型（**仅适用于阶段一**；阶段三需引入 LangGraph，见其 §五） | 选型犹豫时 |
| `w4_model_selection.md` / `w4_selftest.md` | W4 模型选型要点与自测题 | W4 阶段 |
| `w4_price_quality_result.md` | W4 价格 vs 质量对比结果 | W4 阶段 |
| `w5_vision_integration_guide.md` | W5 多模态**能力边界与接口规范**（先看：了解能做什么/不能做什么） | W5 上手前 |
| `w5_vision_step_by_step_tutorial.md` | W5 **分步实现教程**（15KB，6 步完整代码；要照着写时看这份） | W5 动手时 |
| `route_resource_evaluation.html` | 资源消耗评估与提效方案（浏览器打开，5 章完整） | 规划资源时 |
| `README_跨设备使用说明.md` | 跨设备迁移与同步说明（**shy 旧机已于 2026-08 退役，当前仅 MAX 一台** → 本文降为存档） | 一般不用看 |
| `MAX_前置工作协同手册.md` | MAX 迁移前置手册（**迁移已于 08-28 完成、shy 已退役**，现为记录存档） | 一般不用看 |
| `api_gateway_deploy_guide.md` | API 网关（New API + 硅基流动）**可执行部署文档** | 要部署网关时 |
| `api_gateway_deploy_template.md` | 同上的**模板版**（含待拍板确认项；如已按 guide 部署则此份可归档） | 部署前确认时 |

> 📖 **W5 两份文档的分工**（避免重复阅读）：
> `integration_guide` 讲**规范与边界**（能做什么、请求怎么拼），`step_by_step_tutorial` 讲**怎么一步步写出来**。
> **先看 guide 再看 tutorial**，不要两份同时翻。

> **学习路线总纲**（本文档是它的代码落地部分）：
> `C:\Users\高斯\.workbuddy\2026-08-27-14-25-25\AI应用与智能体开发_学习路线_v8.0_通用AI岗位版_20260829.md`
>
> **执行优先级**：
> `W7_本周执行清单.md`（1 页，立即执行）→ `W7-W11_ML-DL补课_周次执行清单_详细版_20260829.md`（完整代码）→ v8.0 §5.6（路线上下文）→ `stage2_mldl_resource_pack.md`（理论查漏，按需）
