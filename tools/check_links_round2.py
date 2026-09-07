# -*- coding: utf-8 -*-
"""第二轮：实测本轮新检索到的公告/投递链接（补充证据链）"""
import csv, io, os, time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "job_hunt", "evidence")
os.makedirs(OUTDIR, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

# (标签, 公司/用途, URL)
TARGETS = [
    ("正式-投递", "神州数码校招官网", "https://digitalchina.zhiye.com/campus/jobs"),
    ("正式-JD", "神州数码 agent工程师(国家大学生就业服务平台)", "https://nju.ncss.cn/student/jobs/EztqHvBKxDKuC44PZoYqV/detail.html"),
    ("正式-公告", "神州数码2027秋招(牛企直聘)", "https://campus.niuqizp.com/job-vrm5azNzn.html"),
    ("正式-公告", "神州信息2027校招(得早学就创)", "https://www.deizao.net/index/index/gonggaoxq/nwid/22211"),
    ("正式-投递", "联宝科技校招官网(zhiye)", "https://lcfc.zhiye.com/"),
    ("正式-JD", "联宝2027届校招岗位(西安电子科技大学)", "https://job.xidian.edu.cn/job/view/id/1521018"),
    ("正式-JD", "联宝2027届校招岗位(西安邮电大学)", "http://jiuye.xupt.edu.cn/detail/job?id=3231243"),
    ("正式-投递", "容知日新校招官网", "https://job.ronds.com/campus-recruitment/anhuirohgzhirixin/"),
    ("正式-公告", "容知日新2027校招(南昌大学)", "https://jy.ncu.edu.cn/detail/online?id=3591204&menu_id="),
    ("正式-投递", "阳光电源校招官网", "https://jobs.sungrowpower.com"),
    ("正式-公告", "阳光电源2027届宣讲会(中科大就业网)", "https://www.job.ustc.edu.cn/airtalk/info.aspx?itemid=9914"),
    ("正式-公告", "阳光电源27届校招(牛企直聘)", "https://campus.niuqizp.com/job-vly5zMCLZ.html"),
    ("正式-公告", "安徽合力(合力叉车)2027全球校招原文", "http://www.heliforklift.com/contact/jobs/202609/t20260901_9546834.html"),
    ("正式-公告", "安徽合力2027校招(中公转载)", "https://ah.offcn.com/html/2026/09/475012.html"),
    ("正式-官网", "龙芯中科", "https://www.loongson.cn"),
    ("正式-公告", "龙芯中科合肥研发中心(湖南第一师范学院)", "https://eis.hnfnu.edu.cn/info/1368/7947.htm"),
    ("正式-公告", "中科类脑2027校招(超级简历)", "https://www.chaojijianli.com/xiaozhao/cas-brain-2027-campus-recruitment-13847-ec914f"),
    ("正式-投递", "科大讯飞2027秋招内推(地大就业网公告)", "https://cug.91wllm.cn/campus/view/id/1000817"),
    ("正式-公告", "科大讯飞飞凡计划(华中农大就业网)", "https://hzau.91wllm.cn/news/view/aid/299249/tag/xwzp"),
    ("正式-公告", "科大讯飞飞星计划(江苏智慧就业平台·硕士)", "https://www.91job.org.cn/recruitment/jobDetails?dwid=691271&zpgwid=1000000000728064"),
    ("正式-投递", "百川智能源点计划官网", "https://careers.baichuan-inc.com/origin-program"),
    ("正式-公告", "百川智能源点计划(北大就业网)", "https://scc.pku.edu.cn/f/recruitmentinfo/show?recruitmentId=0ebdb7fbfec74639a788bef71544fd25"),
    ("正式-投递", "智谱AI careers", "https://zhipuai.cn/careers"),
    ("正式-公告", "智谱27届实习(牛企直聘)", "https://campus.niuqizp.com/job-v8Y5ZCtaZ.html"),
    ("正式-投递", "月之暗面 careers", "https://moonshot.cn/careers"),
    ("正式-投递", "MiniMax careers", "https://minimaxi.com/careers"),
    ("正式-投递", "DeepSeek 招聘", "https://talent.deepseek.com/"),
    ("正式-投递", "旷视校招(moka)", "https://app.mokahr.com/campus_apply/megviihr/38642"),
    ("实习-投递", "商汤AI先锋实习生", "https://hr.sensetime.com/SU60fa3bdabef57c1023fc1cbc/pb/interns.html"),
    ("正式-投递", "网易2027校招岗位页", "https://campus.163.com/app/job/position?id=103"),
    ("正式-投递", "顺丰科技2027校招", "https://campus.sf-express.com/#/homePage"),
    ("正式-投递", "快手2027校招", "https://campus.kuaishou.cn"),
    ("正式-投递", "B站2027校招岗位", "https://jobs.bilibili.com/campus/positions?type=3&channel=bilibiliaccounts"),
    ("正式-投递", "深信服2027校招(Agent开发类)", "https://app.mokahr.com/campus-recruitment/sangfor/27944?locale=zh-CN"),
    ("正式-投递", "美团2027校招", "https://zhaopin.meituan.com/web/home"),
    ("正式-公告", "帆软2027校招(牛企直聘·含Agent研发工程师)", "https://campus.niuqizp.com/schedule-7mUkNNaLM.html"),
    ("正式-内推", "帆软2027内推码(牛客)", "https://ac.nowcoder.com/discuss/1537002"),
    ("正式-公告", "帆软2027提前批内推码FDYHC(华中师大就业网)", "https://ccnu.91wllm.cn/campus/view/id/1001243"),
    ("正式-JD", "羚羊工业互联网算法工程师(探职·硕士)", "https://www.tanzhi.cn/job-detail/03fb24f4-d10b-46c3-b598-03b0686e15f1/"),
    ("汇总-合肥", "牛企直聘·合肥2027校招截止汇总", "https://campus.niuqizp.com/deadline-all-hefei-1/"),
    ("正式-JD", "合肥AI与大数据研究院(复测)", "https://aiit.ahbys.com/job.html?id=314946&cid=175639"),
    ("宏观-新闻", "多家大厂2027校招启动(腾讯新闻)", "https://news.qq.com/rain/a/20260810A06T9600"),
    ("宏观-新闻", "2027届校招开启时间与城市(网易新闻)", "https://c.m.163.com/news/a/L47Q7G4J0553BGPW.html"),
]

rows = []
for tag, name, url in TARGETS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        code, final = str(r.status_code), r.url
        note = "OK" if r.status_code < 400 else ("BLOCKED" if r.status_code in (403, 405, 429, 503) else "DEAD")
    except Exception as e:
        code, final, note = type(e).__name__, "", "DEAD"
    rows.append([tag, name, url, note, code, final, time.strftime("%Y-%m-%d %H:%M")])
    print(f"{note:8s} {code:22s} {name}")

out = os.path.join(OUTDIR, "link_check_result_round2.csv")
with io.open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tag", "name", "input_url", "verdict", "http_status", "final_url", "checked_at"])
    w.writerows(rows)
print("输出:", out)
