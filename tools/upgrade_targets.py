# -*- coding: utf-8 -*-
"""升级投递目标清单：新增字段（学历门槛/网申直达/内推码/来源）+ 扩充合肥本地与AI公司。
数据来源均为可核查的公开渠道（高校就业网、企业校招公告、牛客），见每行 referral_source/notes。
禁止编造：凡未获取的信息一律写「待核实」。
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "job_hunt/targets_2026.csv"
OUT = HERE / "job_hunt/targets_2026.csv"

OLD_COLS = ["company", "city", "position", "track", "channel", "url", "priority", "notes"]
NEW_COLS = ["company", "city", "position", "track", "degree_req", "channel",
            "apply_url", "referral_code", "referral_source", "priority",
            "deadline", "jd_keywords", "notes"]

# 已知真实内推码（附可核查来源；多码时取其一，均为公开渠道发布）
REF = {
    "科大讯飞": ("EV3TSV", "郑州大学就业网2027届公告(多校公告另有EVB41G/ISK63A)"),
    "中兴通讯": ("NTAgCyp", "中兴2027届校招官方推文 ⚠前期已投实习生/捧月/领军项目者勿填内推码，否则投递失败"),
    "帆软软件": ("WHUUUL", "华中师大就业网(另有XDUWSK/XJUJYL/FDYHC)"),
    "vivo": ("ES1CKS", "牛客网2027届内推帖"),
    "拼多多": ("snNeFUbpV2", "牛客网2027届秋招帖"),
}

# 新增条目（合肥本地优先 + AI 应用方向公司）
NEW_ROWS = [
    # ---- 合肥本地（2027届校招，有可核查来源）----
    dict(company="联宝科技(联想控股)", city="合肥", position="AI应用开发/智能体开发工程师",
         track="AI应用", degree_req="本科及以上", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="西安邮电大学就业网2027届岗位(10-15K/月)",
         priority="首批", deadline="待核实",
         jd_keywords="AI应用开发,智能体开发,大模型推理,知识增强,数字化",
         notes="★合肥本地+本科可投+AI岗三合一，优先级最高；联想全球最大PC研发制造基地，AIPC方向；网申链接需从校招公告获取"),
    dict(company="科大国创云网(300520)", city="合肥", position="Java开发工程师",
         track="后端数据", degree_req="本科及以上", channel="校招官网",
         apply_url="https://gccloud.zhiye.com/campus",
         referral_code="", referral_source="武汉大学就业网2027届公告(算法岗需硕士/研究员需博士，本科勿投)",
         priority="主力", deadline="2026-10-24",
         jd_keywords="Java,Web开发,软件开发",
         notes="★合肥本地+本科可投；源自中科大，国创九章AI平台；⚠算法工程师要硕士、研究员要博士，本科只投Java岗"),
    dict(company="本源量子", city="合肥", position="应用软件开发工程师",
         track="后端数据", degree_req="本科", channel="邮箱投递",
         apply_url="hr@originqc.com", referral_code="",
         referral_source="本源量子2027届校招公告(合肥高新区)",
         priority="主力", deadline="待核实",
         jd_keywords="应用软件开发,量子计算,软件工程",
         notes="合肥本地量子计算龙头；简历投hr@originqc.com；9/7-9/9在川大/电子科大/成都理工有宣讲"),
    dict(company="中科类脑", city="合肥", position="Go开发工程师/AI Infra推理优化",
         track="AI应用", degree_req="待核实", channel="校招平台",
         apply_url="待核实", referral_code="",
         referral_source="超级简历2027届校招公告(类脑智能国家工程实验室唯一产业化单位)",
         priority="主力", deadline="待核实",
         jd_keywords="Go,AI Infra,推理优化,大模型推理服务,国产芯片加速",
         notes="合肥+北京两地；国家级专精特新小巨人；AI Infra方向与本科背景匹配度待核实"),
    dict(company="容知日新(688768)", city="合肥", position="软件开发工程师",
         track="后端数据", degree_req="本科", channel="校招平台",
         apply_url="待核实", referral_code="",
         referral_source="应届生求职网2026-08-28发布(合肥高新区)",
         priority="主力", deadline="待核实",
         jd_keywords="软件开发,工业智能运维,PHMGPT工业大模型",
         notes="⚠其「大模型应用/智能体开发工程师」岗明确要求硕士及以上，本科不符，改投软件开发岗；网申8/25已启动"),
    # ---- 合肥本地（企业真实存在，2027届校招信息待核实）----
    dict(company="阳光电源", city="合肥", position="软件开发/算法工程师",
         track="后端数据", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="主力", deadline="待核实", jd_keywords="嵌入式,软件开发,新能源",
         notes="合肥本地光伏龙头，市值千亿；校招规模大，待核实AI/软件岗"),
    dict(company="羚羊工业互联网", city="合肥", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在(安徽省属工业互联网平台)，2027届校招待核实",
         priority="主力", deadline="待核实", jd_keywords="工业互联网,大模型应用,Agent",
         notes="合肥本地；省重点工业互联网平台，与三禾一同赛道，简历有加分"),
    dict(company="龙芯中科(合肥)", city="合肥", position="软件工程师",
         track="后端数据", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="练手", deadline="待核实", jd_keywords="国产CPU,软件生态,系统软件",
         notes="合肥有研发中心；国产化方向"),
    dict(company="安徽合力", city="合肥", position="软件开发工程师",
         track="后端数据", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在(叉车龙头,600761)，2027届校招待核实",
         priority="练手", deadline="待核实", jd_keywords="工业软件,智能物流,AGV",
         notes="合肥本地国企；智能物流/AGV方向"),
    dict(company="工大高科", city="合肥", position="软件开发工程师",
         track="后端数据", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在(688367)，2027届校招待核实",
         priority="练手", deadline="待核实", jd_keywords="铁路信号,物联网,嵌入式",
         notes="合肥本地上市公司"),
    # ---- AI 方向公司（补充岗位池，均待核实 2027 届）----
    dict(company="第四范式", city="北京", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="AutoML,大模型应用,企业级AI",
         notes="企业级AI龙头，应用岗偏工程，对本科相对友好"),
    dict(company="云从科技", city="广州", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在(688327)，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="人机协同,大模型,视觉AI",
         notes="AI四小龙之一"),
    dict(company="依图科技", city="上海", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="视觉AI,大模型,AI应用",
         notes="AI四小龙之一"),
    dict(company="旷视科技", city="北京", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="深度学习,AI应用,机器人",
         notes="AI四小龙之一；⚠研究型算法岗卡学历，投应用工程岗"),
    dict(company="MiniMax", city="上海", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在(大模型独角兽)，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="大模型,Agent,AI应用",
         notes="大模型独角兽；AI应用岗与W6项目对口度高"),
    dict(company="智谱AI", city="北京", position="AI应用开发工程师(非算法岗)",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="GLM,大模型应用,Agent",
         notes="⚠算法研究岗在§1.4不投清单内，仅投应用工程岗"),
    dict(company="百川智能", city="北京", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="大模型,AI应用",
         notes="大模型公司，应用岗偏工程"),
    dict(company="月之暗面(Moonshot)", city="北京", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="冲刺", deadline="待核实", jd_keywords="Kimi,长文本,AI应用",
         notes="Kimi 开发方；应用岗为主"),
    dict(company="明略科技", city="北京", position="AI应用开发工程师",
         track="AI应用", degree_req="待核实", channel="校招官网", apply_url="待核实",
         referral_code="", referral_source="企业真实存在，2027届校招待核实",
         priority="练手", deadline="待核实", jd_keywords="知识图谱,NLP,企业AI",
         notes="企业级AI；知识图谱方向与W6 RAG经验相关"),
]

def main():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print("原条目数:", len(rows))

    out = []
    for r in rows:
        code, src = REF.get(r["company"], ("", ""))
        out.append({
            "company": r["company"], "city": r["city"], "position": r["position"],
            "track": r["track"], "degree_req": "待核实", "channel": r["channel"],
            "apply_url": r["url"], "referral_code": code, "referral_source": src,
            "priority": r["priority"], "deadline": "待核实",
            "jd_keywords": "", "notes": r["notes"],
        })
    for r in NEW_ROWS:
        out.append({k: r.get(k, "") for k in NEW_COLS})

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=NEW_COLS)
        w.writeheader()
        w.writerows(out)
    print("新条目数:", len(out))

    # 统计
    from collections import Counter
    print("城市:", Counter(r["city"] for r in out).most_common())
    print("优先级:", Counter(r["priority"] for r in out).most_common())
    print("合肥条目:", [r["company"] for r in out if r["city"] == "合肥"])

if __name__ == "__main__":
    main()
