# W7 压缩执行清单 · 秋招优先版

> 生成时间：2026-08-30 15:14（GMT+8）｜编制：迪莫
> 适用周期：**2026-08-31（周一）~ 09-13（周日）**
> 关系说明：**本文件取代** `W7-W11_ML-DL补课_周次执行清单_详细版_20260829.md` 的**执行口径**。原清单保留作完整知识参考，但节奏以本文件为准。
> 配套：`W7_本周执行清单.md`（项目内，W7 原始详细清单）

---

## 0. 为什么压缩

原清单设计 W7–W11 共 5 周、40h/周，目标是补齐 AI 应用开发岗 JD 硬门槛。但：

- 目标岗位 **AI 应用 / Agent 开发** 考察的是 LLM 落地、RAG、Agent 编排、工程健壮性
- ML/DL 系统性补课是**算法岗**的硬门槛，对应用岗只是加分项
- 时间账：按原节奏 W8–W11 约排到 10 月初，**W12 才包装简历 —— 简历就绪时秋招高峰已过**

**结论：先有弹药，再补短板。**

---

## 1. 本周（W7）压缩方案

原 W7 计划 5 天 40h。压缩为 **2–3 天约 12–16h**，只保留最能包装成作品的两块：

| 处置 | 内容 | 产出 | 预计 |
|---|---|---|---|
| ✅ 保留 | **Day 3 数据清洗实战**：phone 格式统一、education 拆三列、IQR 异常值标记、去重 | `clean_resumes(df)` 可复用函数 + `resumes_30_clean.csv` | 6h |
| ✅ 保留 | **Day 5 可视化与报告**：4 图 + 文字结论 | `w7_hr_report.png` + `W7_分析报告.md` | 6h |
| ⚠️ 可选 | Day 1 向量化提速实验 | 面试素材（能讲清"为什么向量化快"） | 2h |
| ❌ 暂缓 | Day 2 Pandas 基础、Day 4 聚合透视 | 用到时再查 | — |

> Day 2 / Day 4 不是不重要，而是**不紧急**。等面试真问到 `loc`/`iloc`、`groupby` 时再补，带着问题学记忆更牢。

### Day 3 核心代码（清洗）

```python
import pandas as pd
df = pd.read_json("resumes_30_groundtruth.json", encoding="utf-8")

# ① phone 统一：只留数字
df["phone_clean"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True)

# ② education 拆三列："本科 计算机科学与技术 安徽大学" → 学历/专业/学校
df[["degree", "major", "school"]] = df["education"].str.split(n=2, expand=True)

# ③ 缺失值：类别填"未知"，数值用中位数（抗异常值）
df["school"] = df["school"].fillna("未知")
df["years_of_experience"] = df["years_of_experience"].fillna(
    df["years_of_experience"].median())

# ④ 异常值：IQR 标记，不删（年限异常可能是资深专家）
Q1, Q3 = df.years_of_experience.quantile([.25, .75])
IQR = Q3 - Q1
df["is_outlier"] = ~df.years_of_experience.between(Q1-1.5*IQR, Q3+1.5*IQR)

# ⑤ 去重
df = df.drop_duplicates(subset=["email"], keep="last")
df.to_csv("resumes_30_clean.csv", index=False, encoding="utf-8-sig")
```

🔴 **踩坑**：异常值**不要直接删** —— 先看看是不是真数据。这是面试高频追问点。

### Day 5 核心代码（可视化）

```python
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # Windows 必设
plt.rcParams["axes.unicode_minus"] = False

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes[0,0].hist(df.years_of_experience, bins=10, edgecolor="black")
axes[0,0].set_title("工作年限分布")
df.degree.value_counts().plot(kind="barh", ax=axes[0,1])
axes[0,1].set_title("学历分布")
axes[1,0].scatter(df.years_of_experience, df.index, alpha=.6)
axes[1,0].set_title("年限散点")
df.explode("skills")["skills"].value_counts().head(10).plot(kind="barh", ax=axes[1,1])
axes[1,1].set_title("技能词频 Top10")
plt.tight_layout()
plt.savefig("w7_hr_report.png", dpi=150, bbox_inches="tight")
```

🔴 **踩坑**：Windows 不设字体 → 中文全是方框；负号变方框要设 `axes.unicode_minus=False`。

---

## 2. 释放出来的时间怎么用（约 24h）

| 优先级 | 事项 | 预计 | 说明 |
|---|---|---|---|
| **P0** | 解 W6 阻塞：灌入真实政策到 `policy_context.txt` | 4h | 卡住「9 月前上线」的唯一硬卡点 |
| **P0** | W6 全量评估 + 召回调优 | 4h | 实跑 `w6_eval_runner.py` |
| **P0** | 简历 v1 成型 | 8h | 主线 = 5 个 AI 项目，HR 经历作实习素材 |
| P1 | 启动练手投递 | 4h | 上海 / 武汉 / 成都 / 深圳，意愿一般的先投，攒面试经验 |
| P1 | 目标公司清单三档分层 | 4h | 冲刺 / 主力 / 保底 |

---

## 3. W8–W11 转为按需触发

原安排：W8 Scikit-learn 四大模型 → W9 PyTorch / CNN → W10 Transformer → W11 Hugging Face。

**新口径：不再按周推进，改为触发式学习。**

| 触发条件 | 学什么 |
|---|---|
| 面试被问到 ML 基础 / JD 明确要求 | 补 W8（Scikit-learn），约 1 周 |
| JD 要求 PyTorch / 深度学习 | 补 W9，约 1 周 |
| JD 要求 Transformer / 微调 / Hugging Face | 补 W10–W11，各 1 周 |
| 无任何 JD 提及 | **不学** |

---

## 4. 硬规则

1. **每场面试后 24h 内**，把「被问到但答不上来」的知识点记进补缺清单。这份清单是接下来唯一值得花时间学的东西。
2. 简历与可运行作品 > 课程完成度。能用 `streamlit run` 跑起来给人看的，比学完 5 周课管用。
3. **如实呈现项目规模**：W7 数据是 30 条样例，简历上就写 30 条。写成"千条级"面试一问就穿帮。

---

## 5. 本周验收（5 条，全打勾才进下一阶段）

1. [ ] `resumes_30_clean.csv` 已生成，清洗流程封装成 `clean_resumes(df)` 函数
2. [ ] `W7_分析报告.md` 含 4 图 + 文字结论，中文无方框
3. [ ] `policy_context.txt` 已灌入真实政策，W6 能端到端跑通
4. [ ] 简历 v1 成型（5 个项目素材已写入，规模如实）
5. [ ] 至少投递 3 家练手岗位

---

## 6. 卡住了怎么办

| 卡点 | 处理 |
|---|---|
| W6 没有真实政策数据 | 先用 `w6_sample_policy.txt` 跑通链路，再替换为真实制度 |
| 中文乱码 | 依次试 `utf-8-sig` → `gbk` → `utf-8`；Matplotlib 务必设 `Microsoft YaHei` |
| 报错看不懂 | 把完整 traceback 发给迪莫，别自己耗超过 20 分钟 |
| 简历不知道怎么写 | 先列 5 个项目的「做了什么 / 用了什么技术 / 能量化的结果」，再包装 |
| 时间不够 | **保 P0 三项（W6 解阻塞、W6 评估、简历 v1）**，清洗可视化可延到周末 |

---

**生成**：迪莫 ｜ **依据**：2026-08-30 系统记忆审计 + 秋招优先战略（孟轩拍板）
**未核实**：各公司秋招开启时间（需本人核实，不臆测）
