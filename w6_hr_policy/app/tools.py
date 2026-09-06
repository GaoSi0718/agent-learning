# w6_hr_policy/app/tools.py
"""W6 v1.6 多工具注册表：TOOLS（给 LLM 看的 schema）+ IMPL（可执行实现）。
schema 三原则：描述即契约（何时用+何时不用）/ 参数最小化+枚举 / 单一职责。
注：calc_annual_leave 只算司龄与国家法定档；公司手册条款一律以 search_policy 检索结果
为准（对齐语料与国家条例并存，硬编码任一口径都会造成评估报告增补 B 记录的「双源混淆」）。"""
import asyncio

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "检索公司 HR 政策文档。仅当问题涉及年假/报销/考勤/社保/公积金等制度时使用；闲聊或计算类问题不要用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":   {"type": "string", "description": "检索关键词，尽量简短（2-6 个字）"},
                    "category": {"type": "string", "enum": ["年假", "报销", "考勤", "社保", "公积金", "其他"],
                                 "description": "政策类别；不确定时填'其他'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calc_annual_leave",
            "description": "根据入职日期计算司龄与国家法定年假档位。公司手册条款不在本工具职责内——回答公司口径前请先用 search_policy 检索'年假'核实。仅在需要具体数字时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "hire_date": {"type": "string", "description": "入职日期，格式 YYYY-MM-DD"},
                    "as_of":     {"type": "string", "description": "计算基准日，格式 YYYY-MM-DD；默认今天"}
                },
                "required": ["hire_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "workday_lookup",
            "description": "查询某日期是星期几、按双休规则是否为休息日。仅当问题涉及具体日期是否工作日时使用；不处理法定节假日与调休明细。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "查询日期，格式 YYYY-MM-DD"}
                },
                "required": ["date"]
            }
        }
    },
]

IMPL = {}

def register(name):
    def deco(fn):
        IMPL[name] = fn
        return fn
    return deco

@register("search_policy")
async def _search(query: str, category: str = "其他") -> str:
    """真实实现：调用项目根 w6_rag_retriever（BM25）经 rag.py 封装。"""
    from .rag import retrieve
    hits = await retrieve(query, top_k=3, category=category)
    if not hits:
        return "未检索到相关条款。建议改用更短的关键词，或换 category 重试。"
    return "\n---\n".join(f"[{h['source']}] {h['text']}" for h in hits)

@register("calc_annual_leave")
async def _leave(hire_date: str, as_of: str | None = None) -> str:
    from datetime import date, datetime
    try:
        d0 = datetime.strptime(hire_date, "%Y-%m-%d").date()
    except ValueError:
        return f"参数错误：hire_date 需为 YYYY-MM-DD，收到 {hire_date!r}。请修正后重试。"
    d1 = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else date.today()
    if d1 < d0:
        return "参数错误：基准日早于入职日期，无法计算司龄。请检查日期后重试。"
    years = (d1 - d0).days // 365
    # 国家法定四档（国务院令第 514 号：满1年不满10年5天/满10年不满20年10天/满20年15天；
    # 不满 1 年无法定年假）——不要用嵌套三元合并成三档，司龄 12 年会被错算成 15 天
    if years < 1:
        statutory = 0
    elif years < 10:
        statutory = 5
    elif years < 20:
        statutory = 10
    else:
        statutory = 15
    return (f"截至 {d1.isoformat()}，司龄约 {years} 年。"
            f"【国家法定】累计工龄满1年不满10年 5 天 / 满10年不满20年 10 天 / 满20年 15 天"
            f"→ 本例按法定 {statutory} 天。"
            f"【注意】公司手册对年假另有规定，具体条款请先 search_policy 检索「年假」核实；"
            f"两口径不一致时，回答中须并列说明并注明各自出处。")

@register("workday_lookup")
async def _workday(date_str: str) -> str:
    from datetime import datetime
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return f"参数错误：date 需为 YYYY-MM-DD，收到 {date_str!r}。请修正后重试。"
    wd = "一二三四五六日"[d.weekday()]
    weekend = d.weekday() >= 5
    return (f"{d.isoformat()} 是星期{wd}，按双休规则属于{'休息日' if weekend else '工作日'}。"
            f"注：仅按周末规则判断，法定节假日/调休以国务院当年公告为准。")
