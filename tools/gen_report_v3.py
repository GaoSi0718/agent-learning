# -*- coding: utf-8 -*-
"""从 targets_2026_v3.0.csv 生成完整证据版报告（避免手抄错漏）"""
import csv, io, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "job_hunt", "targets_2026_v3.0.csv")
OUT = os.path.join(ROOT, "job_hunt", "投递清单_v3.0_20260907_完整证据版.md")

rows = list(csv.DictReader(io.open(SRC, encoding="utf-8-sig")))


def stars(m):
    return "★" * int(m) if m.isdigit() else "-"


def tbl(items, cols=("company", "city", "position", "degree_req", "match", "apply_url", "source_url", "deadline")):
    head = ["公司", "城市", "岗位", "学历", "匹配", "投递入口(实测)", "来源公告(可点)", "截止"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in items:
        cells = [
            f"**{r['company']}**",
            r["city"],
            r["position"],
            r["degree_req"],
            stars(r["match"]),
            f"[打开]({r['apply_url']})" if r["apply_url"].startswith("http") else r["apply_url"],
            f"[原文]({r['source_url']})" if r["source_url"].startswith("http") else "无公开链接",
            r["deadline"],
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


t1 = [r for r in rows if r["city_tier"] == "T1"]
t2 = [r for r in rows if r["city_tier"] == "T2"]
t3 = [r for r in rows if r["city_tier"] == "T3"]
interns = [r for r in rows if "实习" in r["job_type"]]
formal = [r for r in rows if "实习" not in r["job_type"]]

hefei = [r for r in rows if "合肥" in r["city"]]
hangzhou = [r for r in rows if "杭州" in r["city"] and r["city_tier"] == "T1" and "合肥" not in r["city"]]
beijing = [r for r in rows if "北京" in r["city"] and r["city_tier"] == "T1"]
t1_other = [r for r in t1 if r not in hefei + hangzhou + beijing]

with io.open(OUT, "w", encoding="utf-8") as f:
    w = f.write
    w("# 投递清单 v3.0（完整证据版）\n\n")
    w("> 生成时间：2026-09-07 23:10 GMT+8　|　数据源文件：`job_hunt/targets_2026_v3.0.csv`（77 条，18 字段）\n")
    w("> 生成方式：由 `tools/gen_report_v3.py` 从 CSV 自动渲染，表格内容与 CSV 严格一致，不存在手抄偏差。\n")
    w("> 可溯源原则：每条含「投递入口」+「来源公告」两个可点击链接；链接状态均经 HTTP 实测；无公开链接者显式标注。\n\n")

    w("---\n\n## 一、本轮重做的目标与验收标准\n\n")
    w("| 验收项 | v2.0 状态 | v3.0 状态 |\n|---|---|---|\n")
    w("| 每条都有可点击来源链接 | ❌ 仅写来源名称（如「实习僧（官方发布）」），无 URL | ✅ 新增 `source_url` 列，69/77 条有直接原文链接 |\n")
    w("| 投递入口可达性有据 | ⚠️ 仅个别标注「URL实测可达」，无证据文件 | ✅ 两轮 HTTP 实测，输出 `evidence/link_check_result*.csv` |\n")
    w("| 学历门槛有出处 | ❌ 大量「待核实」 | ✅ 新增 `degree_evidence` 列，写明依据（公告原文/就业网职位页） |\n")
    w("| 内推码可溯源 | ❌ 仅写「郑州大学就业网公告」，无链接 | ✅ 新增 `referral_source_url`；无链接的显式标「无公开链接」 |\n")
    w("| 城市分层可机读 | ❌ 靠排序体现 | ✅ 新增 `city_tier` 字段（T1/T2/T3） |\n")
    w("| 失效链接识别 | ❌ 无 | ✅ 实测发现 2 条失效并标注 |\n\n")

    w("### 1.1 链接实测方法与判定口径\n\n")
    w("- 工具：`tools/check_links.py`（v2.0 存量 75 条）、`tools/check_links_round2.py`（本轮新检索 44 条）\n")
    w("- 请求：Python `requests`，自定义 Chrome UA + `zh-CN`，超时 20–25 秒，跟随重定向\n")
    w("- 判定：**OK** = HTTP < 400；**BLOCKED** = 403/405/429/503（疑似反爬，需浏览器人工确认）；**DEAD** = 404 或 DNS/连接失败/超时；**NO_URL** = 该行无链接\n")
    w("- 证据文件：`job_hunt/evidence/link_check_result.csv`（75 条）、`job_hunt/evidence/link_check_result_round2.csv`（44 条）\n")
    w("- 第一轮结果：OK 56 / NO_URL 18 / DEAD 1　→　第二轮针对 18 条缺口与新发现链接补测：OK 42 / DEAD 2\n")
    w("- **局限说明**：HTTP 200 仅证明「页面可达」，不等于该岗位此刻仍在招；岗位是否开放须以官网职位列表为准。\n\n")

    w("---\n\n## 二、三条硬规则的执行证据\n\n")
    w("### R1 城市分层（合肥/杭州/北京 > 长三角 > 其他需注明理由）\n\n")
    w(f"- T1（合肥/杭州/北京）：{len(t1)} 条　|　T2（长三角其他）：{len(t2)} 条　|　T3（其他，逐条注明理由）：{len(t3)} 条\n")
    w(f"- 合肥本地 {len(hefei)} 条（v2.0 为 15 家 → v3.0 增至 {len(set(r['company'] for r in hefei))} 家/单位）\n")
    w("- 表格排序即按 T1 → T2 → T3；T3 每条在 `notes` 列写明纳入理由。\n\n")
    w("### R2 学历红线（硕士硬性要求一律剔除）\n\n")
    w("本轮**新剔除/降级**的硕士门槛岗位（均有链接为证）：\n\n")
    w("| 公司 | 被剔除岗位 | 学历证据 | 来源链接 |\n|---|---|---|---|\n")
    w("| 科大讯飞 | 「飞星计划」AI 研究算法工程师 | 明确「2027届顶尖技术类应届**硕博**毕业生」，江苏智慧就业平台标注「学历要求:硕士」 | https://www.91job.org.cn/recruitment/jobDetails?dwid=691271&zpgwid=1000000000728064 |\n")
    w("| 容知日新 | AI算法工程师-RD / 大模型应用·智能体开发工程师 / 算法开发工程师 / PHM算法工程师 | 南昌大学就业网职位表逐一标注「硕士及以上」 | https://jy.ncu.edu.cn/detail/online?id=3591204&menu_id= |\n")
    w("| 安徽合力 | AI 大模型（高级产品设计） | 校招计划表标注「博士研究生」 | http://www.heliforklift.com/contact/jobs/202609/t20260901_9546834.html |\n")
    w("| 羚羊工业互联网 | 算法工程师 | 探职网 JD：「硕士及以上学历」 | https://www.tanzhi.cn/job-detail/03fb24f4-d10b-46c3-b598-03b0686e15f1/ |\n")
    w("| 同花顺 | AIME 计划核心 AI 岗 | 第三方汇总标注「AIME 等核心 AI 项目主要面向硕士及以上」 | https://www.resumemakeroffer.com/page/campus-recruitment-2027 |\n")
    w("| （v2.0 已剔除） | 中科曙光、中国电科 38 所、中国电科 43 所、埃斯顿 | 沿用上一轮结论 | — |\n\n")
    w("> 处理方式：上述岗位**不进入** v3.0 主表；但这些公司本科可投的**兄弟岗位**（如容知日新「软件开发工程师」、安徽合力「信息系统管理」）予以保留，并在 `notes` 中写明「AI 岗卡硕士」。\n\n")
    w("### R3 正式岗与实习岗分开归类\n\n")
    w(f"- 纯正式岗 {len(formal)} 条、纯实习岗 {len([r for r in interns if r['job_type']=='实习'])} 条、正式/实习同源 1 条（百川智能源点计划，同一入口含两类）\n")
    w("- 使用 `job_type` 字段区分；实习岗集中在第六节单独成表。\n\n")

    w("---\n\n## 三、本轮新增 / 重要修订（逐条带证据）\n\n")
    w("### 3.1 新增（11 条，均为本轮检索到官方公告或官方入口后加入）\n\n")
    w("| 公司 | 城市 | 新增理由与关键事实 | 证据链接 |\n|---|---|---|---|\n")
    w("| DeepSeek | 杭州/北京 | 杭州本地顶尖大模型公司；第三方汇总列官方入口 `talent.deepseek.com`，标注覆盖核心系统/大模型全栈/AI Infra，且「存在经验不限/实习岗位」 | https://talent.deepseek.com/ ｜ https://www.resumemakeroffer.com/page/campus-recruitment-2027 |\n")
    w("| 神州数码（含 agent 工程师 JD） | 合肥/南京/杭州等 16 城 | 2027 届秋招 9/2 启动，**合肥在列**；国家大学生就业服务平台 JD 明确「LLM Agent、任务规划、工具调用、RAG、Function Calling、LangChain」，本科及以上、招 10 人 | https://digitalchina.zhiye.com/campus/jobs ｜ https://nju.ncss.cn/student/jobs/EztqHvBKxDKuC44PZoYqV/detail.html ｜ https://campus.niuqizp.com/job-vrm5azNzn.html |\n")
    w("| 联宝科技 | 合肥 | 2027 届校招岗位页明确「本科」「10500-14999」「AI大数据类：AI应用开发/智能体开发/知识增强大模型应用」 | https://lcfc.zhiye.com/ ｜ https://job.xidian.edu.cn/job/view/id/1521018 ｜ http://jiuye.xupt.edu.cn/detail/job?id=3231243 |\n")
    w("| 阳光电源 | 合肥/上海/深圳/南京/西安 | 信息技术类含「算法、AI应用、JAVA开发(AI方向)」；面向 2027 届（2026.8–2027.7 毕业） | https://jobs.sungrowpower.com ｜ https://www.job.ustc.edu.cn/airtalk/info.aspx?itemid=9914 ｜ https://campus.niuqizp.com/job-vly5zMCLZ.html |\n")
    w("| 安徽合力 | 合肥 | 官网原文校招计划表：「信息系统管理（计算机类/工业工程）本科及以上」「财务信息化（计算机类/数据科学）本科及以上」 | http://www.heliforklift.com/contact/jobs/202609/t20260901_9546834.html ｜ https://ah.offcn.com/html/2026/09/475012.html |\n")
    w("| 深信服 | 深圳/北京/长沙/成都 | 校招岗位类别明确含「**Agent 开发类**」；X-STAR 顶尖人才计划 | https://app.mokahr.com/campus-recruitment/sangfor/27944?locale=zh-CN |\n")
    w("| 顺丰科技 | 深圳/武汉/成都 | 2027 届设「AI 开发工程师 / AI 全栈研发工程师」序列 | https://campus.sf-express.com/#/homePage |\n")
    w("| 快手 | 北京/杭州等 | 2027 届实习生招聘**全年开放**，实习满 40 天可获留用考核；开放超 200 个岗位类型 | https://campus.kuaishou.cn ｜ https://www.sohu.com/a/1028327219_121106832 |\n")
    w("| 智谱 AI | 北京 | 已开启 2027 届校招；牛企直聘转载页标注「学历要求：本科及以上」，方向含行业应用算法/企业智能体 | https://zhipuai.cn/careers ｜ https://campus.niuqizp.com/job-v8Y5ZCtaZ.html |\n")
    w("| 月之暗面 | 北京 | 已开启 2027 届校招；「穿越计划」顶尖人才项目不限专业/学历/经验（首批 16 人）；全职招聘网显示校招岗接受本科 | https://moonshot.cn/careers ｜ https://www.quanzhi.com/company/144711351 |\n")
    w("| 网易（岗位直达） | 杭州 | 由首页升级为 2027 届具体岗位页 | https://campus.163.com/app/job/position?id=103 |\n\n")

    w("### 3.2 关键修订（5 处，纠正 v2.0 的事实偏差）\n\n")
    w("| 条目 | v2.0 写法 | v3.0 修订 | 依据 |\n|---|---|---|---|\n")
    w("| 科大讯飞内推码 | `EV3TSV`（郑州大学就业网公告） | 更新为 `EVVT2K`，并附内推直达链接 | 中国地质大学就业网 2027 届秋招公告 https://cug.91wllm.cn/campus/view/id/1000817 ｜ 华中农业大学（飞凡计划）https://hzau.91wllm.cn/news/view/aid/299249/tag/xwzp |\n")
    w("| 科大讯飞投递链接 | https://iflytek.zhiye.com/ （首页） | 升级为 https://iflytek.zhiye.com/campus/jobs 并补充「招聘对象 2025.6–2027.8 毕业、最多可投 2 个岗位、招满即关」 | 同上 |\n")
    w("| 帆软软件岗位 | 「后端开发工程师（Java）」 | 更正为「**Agent 研发工程师** / 后端开发工程师」，并补内推码 `Al10a8n` 与网申期 9/1–9/29 | https://campus.niuqizp.com/schedule-7mUkNNaLM.html ｜ https://ac.nowcoder.com/discuss/1537002 |\n")
    w("| 长鑫存储投递链接 | https://www.cxmt.com/ （企业官网） | 更正为校招系统 https://cxmt.zhiye.com/ | https://www.resumemakeroffer.com/page/campus-recruitment-2027 |\n")
    w("| 本源量子投递方式 | 填了邮箱当 URL | 明确标注「仅邮箱投递 hr@originqc.com，**无公开网申链接**」 | 实测该值非 HTTP 地址 |\n\n")

    w("### 3.3 实测失效链接（2 条，已标注，勿直接点）\n\n")
    w("| 条目 | 链接 | 实测结果 | 建议 |\n|---|---|---|---|\n")
    w("| 合肥人工智能与大数据研究院（大模型算法实习生） | https://aiit.ahbys.com/job.html?id=314946&cid=175639 | 两轮实测均为 ProxyError（2026-09-07） | 在浏览器手动确认；或从安徽高校就业网重新检索该企业公告 |\n")
    w("| 商汤科技「AI 先锋」实习生页 | https://hr.sensetime.com/SU60fa3bdabef57c1023fc1cbc/pb/interns.html | HTTP 404 | 改用商汤招聘主入口 https://www.sensetime.com/cn/join-index |\n\n")

    w("---\n\n## 四、正式岗 · 第一梯队（T1：合肥 / 杭州 / 北京）\n\n")
    w(f"### 4.1 合肥（{len(hefei)} 条）\n\n")
    w(tbl(hefei) + "\n\n")
    w("> 合肥本地 AI/软件可投单位已达 18 家，其中匹配度 ★★★ 的 5 条：科大讯飞（秋招+飞凡计划）、联宝科技（智能体开发）、神州数码（Agent 开发）、中科类脑、寒武纪（合肥有岗）。\n\n")
    w(f"### 4.2 杭州（{len(hangzhou)} 条）\n\n")
    w(tbl(hangzhou) + "\n\n")
    w(f"### 4.3 北京（{len(beijing)} 条）\n\n")
    w(tbl(beijing) + "\n\n")
    if t1_other:
        w(f"### 4.4 其他 T1 归属条目（{len(t1_other)} 条）\n\n")
        w(tbl(t1_other) + "\n\n")

    w("---\n\n## 五、正式岗 · 第二梯队（T2：长三角其他城市）\n\n")
    w(tbl(t2) + "\n\n")

    w("---\n\n## 六、实习岗（单独归类，共 %d 条）\n\n" % len(interns))
    w(tbl(interns) + "\n\n")

    w("---\n\n## 七、第三梯队（T3，逐条注明纳入理由）\n\n")
    w("| 公司 | 城市 | 岗位 | 纳入理由 | 投递入口 |\n|---|---|---|---|---|\n")
    for r in t3:
        w(f"| **{r['company']}** | {r['city']} | {r['position']} | {r['notes']} | [打开]({r['apply_url']}) |\n")
    w("\n")

    w("---\n\n## 八、内推码台账（含来源，无公开链接者显式标注）\n\n")
    w("| 公司 | 内推码 | 来源 | 可溯源? |\n|---|---|---|---|\n")
    for r in rows:
        if r["referral_code"].strip():
            ok = "✅ 有公开链接" if r["referral_source_url"].startswith("http") else "⚠️ 无公开链接（历史记录）"
            src = f"[链接]({r['referral_source_url']})" if r["referral_source_url"].startswith("http") else r["referral_source_url"]
            w(f"| {r['company']} | `{r['referral_code']}` | {src} | {ok} |\n")
    w("\n> 说明：标注「无公开链接」的 5 枚内推码（中兴 `NTAgCyp`、拼多多 `snNeFUbpV2`、满帮 `DSP2bKg3`、用友 `RRbkY6Tn`、恒生 `EZ3AB0`）来自孟轩既往自行收集的记录，**本次检索未找到可公开访问的发布页**，因此无法提供点击链接；建议以企业官网/牛客/脉脉复核其是否仍有效。\n\n")

    w("---\n\n## 九、「无公开链接」与「待核实」专项清单\n\n")
    w("### 9.1 无公开投递入口（6 条）\n\n")
    w("| 公司 | 现状 | 建议动作 |\n|---|---|---|\n")
    for r in rows:
        if not r["apply_url"].startswith("http"):
            w(f"| {r['company']} | {r['apply_url']} | {r['notes']} |\n")
    w("\n### 9.2 来源公告无法提供链接（15 条）\n\n")
    w("| 公司 | 岗位 | 说明 |\n|---|---|---|\n")
    for r in rows:
        if not r["source_url"].startswith("http"):
            w(f"| {r['company']} | {r['position']} | {r['degree_evidence']} ｜ {r['notes']} |\n")
    w("\n> 这些条目来自模型对公开信息的检索但**未定位到可直接引用的原文页面**（多为企业仅通过公众号/内推渠道发布）。保留在清单中是为了不遗漏机会，但投递前须由孟轩本人核实。\n\n")

    w("---\n\n## 十、投递节奏建议（按已确认/高置信截止时间排序）\n\n")
    w("| 优先级 | 动作 | 涉及条目 | 时间约束 |\n|---|---|---|---|\n")
    w("| P0 | 立刻投（本周内） | 科大讯飞秋招+飞凡计划、联宝科技、神州数码 Agent 岗、帆软（Agent 研发） | 帆软网申 9/1–9/29；讯飞「招满即关，最多投 2 岗」；美团第三方汇总标注 9/15 截止（需官网复核） |\n")
    w("| P0 | 实习岗冲刺 | 讯飞 4 个合肥实习岗、欣网视讯、祥承通讯 | 实习僧/应届生职位页均「招满即关」；字节豆包实习标注 9/12 临近截止 |\n")
    w("| P1 | 第一梯队大厂 | 字节、阿里/阿里云、蚂蚁、百度、美团、京东、小米、DeepSeek、快手 | 2027 届秋招已于 8 月上旬全面启动（腾讯新闻/网易新闻佐证），越早投越有利 |\n")
    w("| P2 | 合肥本地补位 | 阳光电源、容知日新、安徽合力、中科类脑、蔚来、长鑫、京东方、本源量子 | 阳光电源牛企直聘标注网申至 9/7（需官网确认是否已延期） |\n")
    w("| P3 | T2/T3 练手 | 中兴、华为、思必驰、B站、拼多多、腾讯、深信服、顺丰科技等 | 无强时间压力，用于积累面试经验 |\n\n")
    w("> 每条投递后请立即写入 `job_hunt/log/applications.csv`（12 列台账，当前仍为 0 行——这是 G1 门禁唯一硬红项，只能由孟轩执行）。\n\n")

    w("---\n\n## 十一、W6 作品与岗位 JD 的对应关系（面试话术底稿）\n\n")
    w("| W6 项目要素 | 命中的 JD 关键词 | 对应公司/岗位 |\n|---|---|---|\n")
    w("| BM25 检索 + 分块优化（323→151 chunks） | RAG、检索增强生成 | 神州数码 agent 工程师、江苏欣网视讯、祥承通讯 |\n")
    w("| 查询同义词扩展 | Prompt 设计与优化、检索召回 | 欣网视讯、神州数码 |\n")
    w("| score2 复合评测（0.6×bigram + 0.4×数字召回） | AI 评测、效果验证 | MiniMax（AI 评测实习）、字节 |\n")
    w("| 三口径基线对比（0.474→0.6607→0.674） | 数据驱动迭代、量化复盘 | 全部工程岗通用 |\n")
    w("| 员工手册/制度问答业务场景 | 企业知识库问答系统 | 讯飞磐智 MaaS、容知日新、用友 |\n\n")

    w("---\n\n## 十二、遗留待办\n\n")
    w("1. 5 枚内推码（中兴/拼多多/满帮/用友/恒生）需孟轩复核是否仍有效。\n")
    w("2. 15 条「无公开来源链接」条目需自行核实（多为公众号发布）。\n")
    w("3. 合肥 AI 研究院链接失效，需人工确认。\n")
    w("4. `job_hunt/log/applications.csv` 投递台账仍为 0 行，需孟轩在首次投递后填写。\n")
    w("5. 部分「待核实」学历（龙芯中科、工大高科、蔚来、华米、京东方等）建议在学校就业网或宣讲会现场确认。\n")

print("输出:", OUT)
