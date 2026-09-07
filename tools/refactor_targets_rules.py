# -*- coding: utf-8 -*-
"""
Z15: 按孟轩 2026-09-07 新规则重构投递清单
规则：
  R1 城市：合肥/杭州/北京 优先；其次长三角(上海/南京/苏州/宁波/无锡)；其他需注明理由
  R2 学历：明确要求硕士及以上/硕士硬性条件 → 一律剔除
  R3 类型：正式岗 + 实习岗，分开归类（新增 job_type 字段）
输出：job_hunt/targets_2026.csv（新增 job_type 列，按城市优先级 + 类型排序）
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CSV = HERE / "job_hunt/targets_2026.csv"

# ---------- 城市分层 ----------
TIER1 = ("合肥", "杭州", "北京")
TIER2 = ("上海", "南京", "苏州", "宁波", "无锡")


def city_rank(city: str) -> int:
    for t in TIER1:
        if t in city:
            return 0
    for t in TIER2:
        if t in city:
            return 1
    return 2


# ---------- 新增：正式岗 ----------
NEW_FULL = [
    dict(company="中科类脑(合肥)", city="合肥", position="算电协同解决方案工程师", track="AI应用",
         degree_req="本科及以上", channel="邮箱投递 hr@leinao.ai / 牛企直聘校招页",
         apply_url="https://campus.niuqizp.com/job-vkk5atNaC.html",
         referral_code="", referral_source="安徽省大学生就业服务平台/牛企直聘2027届简章",
         priority="主力", deadline="待核实",
         jd_keywords="电气/计算机/电子信息/能源动力/人工智能、算电协同、AI Infra、15-25W/年",
         notes="★合肥本地+本科可投(官方简章明确本科及以上15-25W)；类脑国工实验室唯一产业化单位、专精特新小巨人；注意其AI Infra岗均要硕士(30-50W)，只有解决方案岗本科可投"),

    dict(company="寒武纪(688256)", city="北京/上海/深圳/合肥/西安/南京", position="软件类/研发工程师(2027届校招)", track="AI应用",
         degree_req="本科", channel="寒武纪校招官网",
         apply_url="https://www.cambricon.com/",
         referral_code="", referral_source="腾讯新闻/网易2027届校招汇总(2026-08-13)",
         priority="冲刺", deadline="待核实",
         jd_keywords="AI芯片软件栈、芯片类/软件类/职能与研发支持类",
         notes="★工作地含合肥与南京——唯一同时覆盖两个主力城市的AI芯片龙头；面向2026.9-2027.8毕业，本科可投"),

    dict(company="阿里云(阿里巴巴)", city="杭州/北京/上海/南京等", position="AI Agent研发工程师 / Agent Infra工程师 / AI应用研发工程师", track="AI应用",
         degree_req="本科", channel="阿里巴巴校招官网 campus-talent.alibaba.com",
         apply_url="https://campus-talent.alibaba.com/campus/alistar",
         referral_code="", referral_source="中科大就业网/中国农大就业网2027届公告",
         priority="冲刺", deadline="待核实(27届网申8/5启动)",
         jd_keywords="AI应用研发、AI Agent优化、Agent Infra、AI全栈开发、大模型应用",
         notes="★本届新增七大AI岗，AI岗占比超80%；杭州总部+北京+南京均有岗；每位同学每个业务集团仅一次投递机会、最多2个意向，投递前务必想清楚；另有阿里星顶尖人才计划(基础模型/AI Infra/大模型应用)"),

    dict(company="合肥人工智能与大数据研究院", city="合肥", position="大模型算法实习生→留用", track="AI应用",
         degree_req="本科", channel="安徽省大中专毕业生就业信息网(电话18256514456)",
         apply_url="https://aiit.ahbys.com/job.html?id=314946&cid=175639",
         referral_code="", referral_source="安徽省大中专毕业生就业信息网",
         priority="主力", deadline="待核实",
         jd_keywords="Python、大语言模型、提示词工程、文档解析算法、数据处理自动化",
         notes="★合肥蜀山+本科+JD只要Python/LLM/Prompt三条，与W6技术栈完全重合；鄂维南院士领衔、北大-合肥共建新型研发机构；写明'出色实习生可发展为管培生'"),
]

# ---------- 新增：实习岗 ----------
NEW_INTERN = [
    dict(company="科大讯飞", city="合肥", position="技术支持实习生(智能体平台/磐智MaaS)", track="AI应用",
         degree_req="本科", channel="实习僧",
         apply_url="https://www.shixiseng.com/intern/inn_vhn0uoqeab23",
         referral_code="EV3TSV", referral_source="实习僧(科大讯飞官方发布)",
         priority="首批", deadline="2026-09-13",
         jd_keywords="智能体平台、MaaS平台、Linux、docker/k8s、MySQL、shell/Python、大模型与智能体概念",
         notes="★★★合肥本地+本科+JD含'了解Linux/docker/k8s/MySQL/Python/大模型智能体'——与技能栈几乎逐条命中；实习6个月可长期；要求计算机相关专业，完全对口；⚠️9/13截止，最紧"),

    dict(company="科大讯飞", city="合肥", position="产品实习生(人工智能开放平台方向)", track="AI应用",
         degree_req="本科", channel="得早学就创 / 邮件投递",
         apply_url="https://www.deizao.net/index/index/shixixq/jobid/235982",
         referral_code="EV3TSV", referral_source="得早学就创(科大讯飞官方发布)",
         priority="主力", deadline="2026-09-13",
         jd_keywords="AI开放平台、API能力体系、PRD、Axure/Figma、大模型应用",
         notes="★★★要求'了解基础编程、熟悉JSON数据结构'——偏产品但技术门槛低、本科可投；讯飞开放平台是核心业务；⚠️9/13截止"),

    dict(company="科大讯飞", city="合肥", position="商业分析实习生(MaaS大模型/AI智能体方向)", track="AI应用",
         degree_req="学历不限", channel="得早学就创",
         apply_url="https://www.deizao.net/index/index/shixixq/jobid/243469",
         referral_code="EV3TSV", referral_source="得早学就创(科大讯飞官方发布)",
         priority="主力", deadline="2026-09-13",
         jd_keywords="MaaS大模型、AI智能体赛道调研、数据清洗、数据可视化",
         notes="★★支持全程远程+合肥base+学历不限——零地理门槛；明确写'有使用Codex/Claude Code/WorkBuddy等工具者优先'，你日常就在用；⚠️9/13截止，需提交Kimi/DeepSeek产品研究报告PPT"),

    dict(company="科大讯飞", city="合肥", position="AI视频生成实习生", track="AI应用",
         degree_req="本科", channel="实习僧",
         apply_url="https://www.shixiseng.com/intern/inn_mn8xxmwtxma4",
         referral_code="EV3TSV", referral_source="实习僧(科大讯飞官方发布)",
         priority="练手", deadline="2026-09-13",
         jd_keywords="大模型、AI视频生成、AIGC内容、Prompt编写、跨境电商短视频",
         notes="120-150元/天；偏内容运营而非研发，与W5多模态图片问答有弱关联；⚠️9/13截止；作为合肥本地保底实习选项"),

    dict(company="江苏欣网视讯", city="南京", position="AI开发工程师(实习生)", track="AI应用",
         degree_req="本科(2027届)", channel="应届生求职网/51job",
         apply_url="https://www.yingjiesheng.com/job-007-987-868.html",
         referral_code="", referral_source="应届生求职网(2026-09-01发布,来源51job)",
         priority="首批", deadline="待核实(9/1发布,招满即止)",
         jd_keywords="大模型API调用、Agent开发(多轮对话/工具调用/RAG)、Prompt设计优化、ASR/TTS、企业知识库问答系统(RAG)、Flask/FastAPI/Spring Boot",
         notes="★★★JD与W6项目几乎逐字对应：明确写'大模型API调用、智能体Agent开发(多轮对话/工具调用/RAG)、Prompt设计与优化、企业知识库问答系统(RAG)'；本科2027届；南京=主力城市；⚠️考核期4周补贴仅800元，转正后按正常标准，需权衡"),

    dict(company="字节跳动(火山方舟MaaS)", city="上海", position="豆包大模型产品解决方案实习生", track="AI应用",
         degree_req="本科(2027届)", channel="实习僧",
         apply_url="https://www.shixiseng.com/intern/inn_8oywnoaxyfyi",
         referral_code="", referral_source="实习僧(字节跳动官方发布)",
         priority="练手", deadline="2026-09-12",
         jd_keywords="豆包大模型、火山方舟MaaS、GTM、Python、解决方案",
         notes="320-350元/天+免费三餐；Bytelntern面向2027届有转正机会；偏解决方案而非纯研发；⚠️9/12截止(明天)；上海属长三角第二梯队"),

    dict(company="上海人工智能实验室", city="上海", position="【27届留用实习生】Agent研发-工程平台中心", track="AI应用",
         degree_req="本科(985/211优先)", channel="智联校园",
         apply_url="https://xiaoyuan.zhaopin.com/job/CCL1384980490J41002355804",
         referral_code="", referral_source="智联校园(上海AI实验室官方发布)",
         priority="练手", deadline="待核实",
         jd_keywords="AI Agent设计实现、LangChain/llamaIndex/Dify、CoT/ReACT、代码生成Agent",
         notes="★★岗位名即Agent研发，300-400元/天、4个月可转正；⚠️明确写985/211优先(安徽理工为双非)，竞争极激烈，作冲刺练手；上海"),

    dict(company="MiniMax", city="北京/上海", position="2027届实习生(大模型系统/Agent后端/AI评测)", track="AI应用",
         degree_req="本科", channel="飞书校招(2027届实习生+日常实习双通道)",
         apply_url="https://vrfi1sk8a0.jobs.feishu.cn/s/AGKFQfFwHZo",
         referral_code="4HFM3WU", referral_source="牛客(上海交大同学发布,附内推链接)",
         priority="冲刺", deadline="招满即止",
         jd_keywords="大模型Agent应用后端、Golang/Python、AI评测开发、数据采集平台、机器学习系统",
         notes="★多模态独角兽；本科占比92.8%(爱企查数据)——对本科生友好；内推码4HFM3WU；要求能实习≥3个月；北京属T1城市"),

    dict(company="百川智能", city="北京", position="「源点计划」27届实习生(Agent算法/AI Infra)", track="AI应用",
         degree_req="本科(面向本硕博,2027毕业在校生)", channel="百川源点计划官网 / campus@baichuan-inc.com",
         apply_url="https://careers.baichuan-inc.com/origin-program",
         referral_code="", referral_source="北航就业资讯网(百川官方发布)",
         priority="冲刺", deadline="待核实",
         jd_keywords="大模型算法、Agent算法、AI Infra推理/训练、AI产品",
         notes="★王小川创办；实习岗明确面向2027年毕业在校生且向本科生开放；终面由王小川亲自参与；北京= T1城市；竞争大作冲刺"),

    dict(company="上海祥承通讯", city="上海", position="实习AI智能体开发工程师", track="AI应用",
         degree_req="本科", channel="猎聘",
         apply_url="https://m.liepin.com/lptjob/81183671",
         referral_code="", referral_source="猎聘(企业直招)",
         priority="练手", deadline="2027-03-24",
         jd_keywords="AI智能体搭建、Python/Java/Go、OpenAI API/Claude/智谱/通义、LangChain/LangGraph/Dify、RAG、Function Calling",
         notes="★150-200元/天、明确可转正；JD加分项'LangChain/LangGraph/Dify、RAG、Function Calling'与W6技术栈高度重合；本科在读即可；上海张江；薪资偏低但门槛友好，适合作为第一份AI实习跳板"),

    dict(company="上海仙工智能", city="上海", position="Agent开发实习生(27届可转正)", track="AI应用",
         degree_req="本科(27届优先)", channel="应届生求职网",
         apply_url="https://www.yingjiesheng.com/job-008-029-826.html",
         referral_code="", referral_source="应届生求职网(2026-08-17发布)",
         priority="练手", deadline="待核实",
         jd_keywords="Agent OS、Agent运行时/任务调度/工具调用/上下文管理、Rust、MCP/工具协议",
         notes="★岗位名即Agent开发、27届可转正、具身智能赛道；⚠️主要要求Rust(你有Python/Java)，需评估语言转换成本，匹配度中等"),
]


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    before = len(rows)

    # R2: 剔除明确硕士
    dropped = [r["company"] for r in rows if "硕士" in r["degree_req"]]
    rows = [r for r in rows if "硕士" not in r["degree_req"]]

    # 老条目补 job_type=正式
    for r in rows:
        r["job_type"] = "正式"

    # 新增
    for r in NEW_FULL:
        r["job_type"] = "正式"
    for r in NEW_INTERN:
        r["job_type"] = "实习"
    rows.extend(NEW_FULL)
    rows.extend(NEW_INTERN)

    # R1 排序：城市层级 → 类型(正式优先) → 保持原序
    order = {"正式": 0, "实习": 1}
    rows.sort(key=lambda r: (city_rank(r["city"]), order.get(r["job_type"], 9)))

    fields = ["company", "city", "position", "track", "job_type", "degree_req", "channel",
              "apply_url", "referral_code", "referral_source", "priority", "deadline",
              "jd_keywords", "notes"]

    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"原 {before} 条 → 剔除硕士 {len(dropped)} 条 → 新增 {len(NEW_FULL)+len(NEW_INTERN)} 条 "
          f"(正式{len(NEW_FULL)}/实习{len(NEW_INTERN)}) → 最终 {len(rows)} 条")
    print(f"剔除: {dropped}")
    from collections import Counter
    print("城市分层:", Counter(city_rank(r["city"]) for r in rows))
    print("类型分布:", Counter(r["job_type"] for r in rows))


if __name__ == "__main__":
    main()
