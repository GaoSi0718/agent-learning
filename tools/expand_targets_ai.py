# -*- coding: utf-8 -*-
"""
Z14: 投递清单第二轮拓展 —— AI 行业内新增岗位
- 依据 2026-09-07 实测检索（各高校就业网/企业官方公告/牛企直聘）
- 严格去重：与现有 51 条无公司重复
- 新增字段全部按 v1.2 规范填写（学历/网申直达/内推码+来源/截止/JD关键词）
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "job_hunt/targets_2026.csv"

NEW = [
    # ---------- 高优先：本科可投 + JD 与技能栈直接对口 ----------
    dict(company="满帮集团", city="南京", position="全栈开发工程师（AI Agent 方向）", track="AI应用",
         degree_req="本科", channel="Moka 校招官网 + 学长学姐内推",
         apply_url="https://app.mokahr.com/campus_apply/manbang/94191?recommendCode=DSP2bKg3",
         referral_code="DSP2bKg3", referral_source="桂林电子科技大学就业网2027届公告",
         priority="首批", deadline="2026-11-30",
         jd_keywords="Java/Spring Boot、Vue/React、大模型API接入、Prompt工程调优、AI Agent开发",
         notes="★高度对口：JD 原文明确列『大模型 API 接入、Prompt 工程调优、AI Agent 开发』，与 W6 Agent 项目逐条吻合；美股上市(数字货运第一股)，南京雨花台；网申 8/26-11/30，三轮线上面试；本科 200 人规模"),

    dict(company="容知日新(688768)", city="合肥", position="大模型应用/智能体开发工程师", track="AI应用",
         degree_req="本科(2027届应届)", channel="官网/超级简历校招页",
         apply_url="https://www.wondercv.com/xiaozhao/ronds-2027-global-campus-recruitment-13234-7ae8cb",
         referral_code="", referral_source="超级简历WonderCV校招页(企业官方发布)",
         priority="首批", deadline="2026-10-31(网申8/25起,Offer10月起)",
         jd_keywords="PHMGPT行业大模型、智能体开发、工业互联网、设备智能运维",
         notes="★合肥本地+AI岗+本科可投三合一；科创板上市；AI+工业互联网赛道与三禾一实习背景同赛道，简历可直接迁移；网申8/25已启动，9月起笔试面试，建议尽快"),

    dict(company="大华股份(002236)", city="杭州", position="AI应用开发/大模型应用工程师", track="AI应用",
         degree_req="本科", channel="大华招聘官网(校园招聘板块)",
         apply_url="https://job.dahuatech.com/#/CampusPosition?id=11",
         referral_code="", referral_source="大华股份招聘公众号/牛企直聘2027届公告",
         priority="冲刺", deadline="2026-09-23",
         jd_keywords="AI应用开发、大模型应用、大数据(Agent方向)、AI交付",
         notes="🔴急招且临近截止：网申 8/26-9/23，仅剩约 2 周；全球视频监控TOP2，研发占比超50%；软件类岗位明确含『大数据(Agent方向)』『AI应用开发』『大模型应用』；注意：每人仅可投 1 个岗位"),

    dict(company="恒生电子(600570)", city="杭州", position="AI应用开发/智能体开发工程师", track="AI应用",
         degree_req="本科", channel="恒生校招官网(内推链接)",
         apply_url="https://campus.hundsun.com/campus/jobs?shareId=5a906016-60c2-4f9b-820a-6a7d7ce8bb1c&shareSource=2",
         referral_code="EZ3AB0", referral_source="深圳北理莫斯科大学就业网2027届公告",
         priority="冲刺", deadline="2026-09-23(首轮笔试投递截止)/10-23(网申)",
         jd_keywords="AI应用开发、智能体开发、模型后训练、Java/C++、金融IT",
         notes="🔴时间敏感：首轮笔试需 9/23 前完成投递；AI方向招 40 人(算法/AI应用/智能体/模型后训练)；连续18年FinTech100，技术占比67.2%；内推码 EZ3AB0 优先筛选；内推QQ群 995749213"),

    dict(company="达梦数据(688692)", city="武汉", position="Agent开发工程师", track="AI应用",
         degree_req="本科", channel="达梦官网校园招聘板块 / 邮箱 campus@dameng.com",
         apply_url="https://www.dameng.com/",
         referral_code="", referral_source="华中科技大学计算机学院/厦门大学就业网2027届公告",
         priority="主力", deadline="待核实",
         jd_keywords="Agent开发、数据库内核、算法工程、国产数据库",
         notes="★岗位名直含『Agent』且明确本科，20-25K；中国电子(CEC)旗下国产数据库龙头，688692上市；六大研发中心含武汉/成都/苏州/北京/上海；练手城市里含金量最高的选项"),

    dict(company="用友网络(600588)", city="北京", position="全栈开发工程师（企业级 AI）", track="AI应用",
         degree_req="本科", channel="用友招聘官网 career.yonyou.com",
         apply_url="http://career.yonyou.com",
         referral_code="RRbkY6Tn", referral_source="哈工大就业网2027届公告(空宣专属内推码)",
         priority="冲刺", deadline="2026-11-30",
         jd_keywords="Java/Spring Boot/Spring Cloud、React/Vue、AI大模型预研、AI Coding(Claude Code/CodeX)",
         notes="★隐藏高匹配：B端产品线含『人力(HR)模块』，孟轩 HR 实习经历可直接迁移为业务理解优势；IDC 中国 AI-Enabled ERP 市占率第一；全栈岗招 200 人本科；JD 明确要求用 AI 工具编码；注意：工作地点均为北京"),

    # ---------- 中优先：竞争度较低 / 本科友好 ----------
    dict(company="神州数码", city="合肥/南京/杭州/武汉等16城", position="Agent开发工程师 / AI应用开发工程师", track="AI应用",
         degree_req="本科", channel="神州数码校招官网(待核实具体入口)",
         apply_url="待核实",
         referral_code="", referral_source="职芽求职公众号整理(来源企业公开校招信息)",
         priority="主力", deadline="招满即止",
         jd_keywords="Agent开发、AI应用开发、多模态算法、具身智能、解决方案",
         notes="💎竞争度低：本科起投、不卡学校、双非友好；Agent工程师 16-20K/月；工作地含合肥(同时覆盖南京/杭州/武汉/成都)；七险一金+公租房；宣讲会现场有快速面试及 offer，招满即止，宜早投"),

    dict(company="中新赛克(002912)", city="南京", position="全栈开发工程师 / 大模型算法工程师", track="AI应用",
         degree_req="本科", channel="中新赛克校招官网",
         apply_url="https://recruit.sinovatio.com/home/student",
         referral_code="", referral_source="西安交大就业网/牛企直聘2027届提前批公告",
         priority="主力", deadline="2026-08-21(提前批，正式批待核实)",
         jd_keywords="全栈开发、大模型算法、网络/电磁空间安全、AI Native",
         notes="深创投控股上市国企；南京/深圳/重庆三大研发中心，本科及以上占95%；研发占比65%；提前批已过(8/21)，需盯正式批开放；内推可找校园大使拿码"),

    dict(company="联宝科技(联想控股)", city="合肥", position="AI应用开发/智能体开发工程师", track="AI应用",
         degree_req="本科及以上", channel="校招平台(西安邮电大学就业网可见岗位)",
         apply_url="待核实",
         referral_code="", referral_source="西安邮电大学就业创业信息网2027届岗位(10-15K/月)",
         priority="主力", deadline="待核实",
         jd_keywords="AI应用开发、智能体开发、大模型高效推理、知识增强大模型应用、数据管理",
         notes="【状态升级】此前标『待核实』，现已获实证：本科及以上、10-15K/月、合肥；全球最大PC研发制造基地(灯塔工厂)；AI岗方向含『知识增强大模型应用』，与 W6 RAG 项目直接对口"),

    dict(company="科大讯飞-飞凡计划", city="合肥", position="未来领导者专项（研发方向）", track="AI应用",
         degree_req="本科", channel="讯飞校招官网(飞凡计划专区)",
         apply_url="https://iflytek.zhiye.com/5/jobs?shareId=4ab0c7b7-0b2d-426c-928c-ae6c998cae49&shareSource=2",
         referral_code="EV3TSV", referral_source="郑州大学就业网2027届公告(四个项目独立投递)",
         priority="主力", deadline="待核实",
         jd_keywords="研发/产品/营销方向、专业不限、未来领导者",
         notes="与『秋招正式批』相互独立、可同时投递；专业不限；合肥本地；注意与清单第 1 条(正式批)区分，不要重复投递同一项目"),

    # ---------- 低优先 / 竞争极激烈 ----------
    dict(company="阶跃星辰(StepFun)", city="北京/上海", position="StepStar 计划 · Agent/工程岗", track="AI应用",
         degree_req="本科(顶尖人才计划)", channel="校招官网 / 邮箱 campus@stepfun.com",
         apply_url="https://app.mokahr.com/campus-recruitment/step/141903",
         referral_code="", referral_source="北大/中科大就业网2027届公告",
         priority="练手", deadline="招满即止",
         jd_keywords="Agent、大语言模型、多模态、端侧、Infra",
         notes="⚠️竞争激烈：要求『科研功底+竞赛/科研/实践突出成就+技术社区影响力』；笔试含 LeetCode 中等、手撕 BLEU/AOC、MoE路由、KV Cache；建议作为练手投递，不作为主攻"),

    # ---------- 排除项（记录检索结论，避免重复调研） ----------
    dict(company="中科曙光(603019)", city="北京/南京/杭州/成都等", position="工业Agent研发/AI应用开发工程师", track="AI应用",
         degree_req="硕士及以上", channel="中科曙光校招官网",
         apply_url="https://go.sugon.com/campus",
         referral_code="", referral_source="哈工大(威海)/中国海洋大学就业网2027届简章",
         priority="排除-学历不符", deadline="2027-12-31",
         jd_keywords="工业Agent、AI应用开发、超算互联网、工业互联网",
         notes="❌本科不符：招聘对象明确『2027年1-12月毕业的应届硕士/博士』，招1000+人；岗位本身与工业互联网背景高度契合，若后续读研或放宽可优先"),

    dict(company="中国电科38所", city="合肥", position="信息系统开发/B-S架构设计师", track="AI应用",
         degree_req="硕士/博士", channel="智联招聘校招专区",
         apply_url="https://cetc38.zhaopin.com",
         referral_code="", referral_source="安徽省大学生就业服务平台/中南大学就业网2027届简章",
         priority="排除-学历不符", deadline="待核实",
         jd_keywords="人工智能算法、数据处理、信息系统开发",
         notes="❌本科不符：明确『硕博研究生(博士为主,少量硕士)』；合肥军工电子国家队，福利优厚(事业编/安家费)，读研后值得考虑"),

    dict(company="中国电科43所", city="合肥", position="人工智能工程师", track="AI应用",
         degree_req="硕士及以上(博士优先)", channel="43所校招(腾讯文档投递/内推)",
         apply_url="http://www.cetc43.com.cn",
         referral_code="", referral_source="哈工大就业网/牛企直聘2027届公告",
         priority="排除-学历不符", deadline="2026-09-04(已过)",
         jd_keywords="端侧AI、模型剪枝量化、多源传感数据",
         notes="❌本科不符 + 网申已截止：招聘对象为硕士/博士；合肥高新区央企，混合集成电路国标制定者"),

    dict(company="埃斯顿(002747)", city="南京", position="软件工程师(研发类)", track="AI应用",
         degree_req="硕士", channel="埃斯顿校招官网",
         apply_url="https://estun1.zhiye.com/campus",
         referral_code="", referral_source="安徽省大学生就业服务平台2027届全球校招公告",
         priority="排除-学历不符", deadline="待核实",
         jd_keywords="运动控制、具身智能、机器人操作系统",
         notes="❌本科不符(研发岗)：研发类软件工程师明确硕士，具身智能/视觉AI算法要博士；本科仅开放技术服务工程师、销售工程师；国产工业机器人销量第一"),
]

FIELDS = ['company', 'city', 'position', 'track', 'degree_req', 'channel', 'apply_url',
          'referral_code', 'referral_source', 'priority', 'deadline', 'jd_keywords', 'notes']


def main():
    with open(SRC, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))

    existing = {r['company'] for r in rows}
    added, skipped = [], []
    for item in NEW:
        if item['company'] in existing:
            skipped.append(item['company'])
            continue
        rows.append(item)
        added.append(item['company'])
        existing.add(item['company'])

    with open(SRC, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"新增 {len(added)} 条，跳过(重复) {len(skipped)} 条，总计 {len(rows)} 条")
    for a in added:
        print("  +", a)
    if skipped:
        print("  跳过:", skipped)


if __name__ == '__main__':
    main()
