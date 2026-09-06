# -*- coding: utf-8 -*-
"""
W7 数据清洗实战
===============

读取 resumes_30.txt（30 份简历原始文本），解析并清洗为结构化数据，
输出 resumes_30_clean.csv，并将清洗逻辑封装为可复用的 clean_resumes(df)。

设计要点（遵循 w7-compressed-sprint 验收口径）：
  - phone 统一：只保留数字 -> phone_clean
  - education 拆三列：学历 / 专业 / 学校
  - 缺失值：类别填“未知”，数值用中位数（抗异常值）
  - 异常值：IQR 标记 is_outlier，不删除（资深专家年限异常属正常）
  - 去重：按 email 去重

clean_resumes(df) 可被 import 复用：传入一个含原始字段的 DataFrame，
返回清洗后的 DataFrame。
"""

import os
import re

import pandas as pd

# --------------------------------------------------------------------------- #
# 路径约定
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_TXT = os.path.join(BASE_DIR, "resumes_30.txt")
CLEAN_CSV = os.path.join(BASE_DIR, "resumes_30_clean.csv")
GT_JSON = os.path.join(BASE_DIR, "resumes_30_groundtruth.json")

DEGREE_PATTERNS = ["本科在读", "本科", "硕士研究生", "硕士", "博士"]

# --------------------------------------------------------------------------- #
# 1. 解析原始文本
# --------------------------------------------------------------------------- #
def parse_resumes(txt_path: str = RAW_TXT) -> pd.DataFrame:
    """把 resumes_30.txt 拆块解析成结构化 DataFrame。

    原始文本每块形如：
        ===== 1 =====
        张伟 资深Python工程师
        邮箱：zhangwei@example.com
        电话：138-0000-1234
        技能：Python, FastAPI, PostgreSQL, Docker, Redis
        5年工作经验，本科 计算机科学与技术 安徽大学
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 按分隔行 “===== N =====” 切块
    blocks = re.split(r"^=+\s*\d+\s*=+\s*$", text, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    records = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

        # 1) 第一行：姓名 + 职位
        name, title = "", ""
        if lines:
            first = lines[0]
            parts = first.split(None, 1)
            name = parts[0] if parts else ""
            title = parts[1] if len(parts) > 1 else ""

        # 2) 邮箱
        email = ""
        for ln in lines:
            m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+)", ln)
            if m:
                email = m.group(1)
                break

        # 3) 电话：11 位手机号（允许中间短横）
        phone = ""
        for ln in lines:
            m = re.search(r"\d{3}-?\d{4}-?\d{4}", ln)
            if m:
                phone = m.group(0)
                break

        # 4) 技能
        skills = []
        for ln in lines:
            if "技能" in ln:
                # 取“：/ :”之后的部分
                body = re.split(r"[:：]", ln, maxsplit=1)[-1]
                skills = [s.strip() for s in re.split(r"[,，]", body) if s.strip()]
                break

        # 5) 年限 + 学历/专业/学校（含“年”的那一行）
        years = None
        degree, major, school = "", "", ""
        for ln in lines:
            if "年" in ln and any(k in ln for k in ("本科", "硕士", "博士")):
                years, degree, major, school = _parse_education_line(ln)
                break

        records.append(
            {
                "name": name,
                "title": title,
                "email": email,
                "phone": phone,
                "skills": skills,
                "years_of_experience": years,
                "degree": degree,
                "major": major,
                "school": school,
            }
        )

    return pd.DataFrame(records)


def _parse_education_line(ln: str):
    """从“5年工作经验，本科 计算机科学与技术 安徽大学”类文本解析出
    (年限, 学历, 专业, 学校)。兼容多种语序：
      - 5年工作经验，本科 计算机科学与技术 安徽大学
      - 本科 视觉传达设计 江南大学 5年
      - 本科在读 统计学 安徽大学 0年（实习）
      - 4年，本科 软件工程 合肥工业大学
    """
    # 年限
    years = None
    m = re.search(r"(\d+)\s*年", ln)
    if m:
        years = int(m.group(1))

    # 学历
    degree = ""
    for d in DEGREE_PATTERNS:
        if d in ln:
            degree = d
            break

    # 去掉前导“X年工作经验，” / “X年，”
    rest = re.sub(r"^\s*\d+\s*年[^，,]*[，,]?\s*", "", ln)
    # 去掉尾部“X年（实习）”等
    rest = re.sub(r"\s*\d+\s*年.*$", "", rest)
    # 去掉学历词（仅首处）
    if degree:
        rest = rest.replace(degree, "", 1)
    # 清理并拆分
    rest = re.sub(r"[，,]+", " ", rest).strip()
    parts = rest.split()
    major = parts[0] if len(parts) >= 1 else ""
    school = parts[1] if len(parts) >= 2 else ""

    return years, degree, major, school


# --------------------------------------------------------------------------- #
# 2. 清洗（可复用核心函数）
# --------------------------------------------------------------------------- #
def clean_resumes(df: pd.DataFrame) -> pd.DataFrame:
    """对解析后的简历 DataFrame 执行清洗，返回清洗后的 DataFrame。

    入参 df 至少应包含：phone, education 相关字段或 (degree/major/school)、
    years_of_experience、email、skills。
    本函数会：
      ① phone 统一为纯数字 phone_clean
      ② 重建 education 文本（学历 专业 学校），缺失学校填“未知”
      ③ 工作年限缺失用中位数填充
      ④ IQR 标记异常值 is_outlier（不删除）
      ⑤ 按 email 去重
    """
    out = df.copy()

    # ① 电话统一：只留数字
    out["phone_clean"] = (
        out["phone"].astype(str).str.replace(r"\D", "", regex=True)
    )

    # ② 重建 education 文本
    def _build_edu(row):
        deg = row.get("degree", "") or ""
        maj = row.get("major", "") or ""
        sch = row.get("school", "") or ""
        return f"{deg} {maj} {sch}".strip()

    out["education"] = out.apply(_build_edu, axis=1)
    # 缺失学校填“未知”
    out["school"] = out["school"].fillna("未知").replace("", "未知")
    # 重新生成 education，确保未知被纳入
    out["education"] = out.apply(_build_edu, axis=1)

    # skills 统一成字符串（便于 CSV 展示与核验）
    if "skills" in out.columns:
        out["skills"] = out["skills"].apply(
            lambda s: "，".join(s) if isinstance(s, list) else (s if isinstance(s, str) else "")
        )

    # ③ 工作年限缺失：用中位数填充
    if "years_of_experience" in out.columns:
        out["years_of_experience"] = pd.to_numeric(
            out["years_of_experience"], errors="coerce"
        )
        med = out["years_of_experience"].median()
        out["years_of_experience"] = out["years_of_experience"].fillna(med)

    # ④ 异常值：IQR 标记（不删）
    if "years_of_experience" in out.columns:
        Q1, Q3 = out["years_of_experience"].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        out["is_outlier"] = ~out["years_of_experience"].between(
            Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        )
    else:
        out["is_outlier"] = False

    # ⑤ 去重（按 email，保留最后一条）
    if "email" in out.columns:
        before = len(out)
        out = out.drop_duplicates(subset=["email"], keep="last").reset_index(drop=True)
        out.attrs["dropped_duplicates"] = before - len(out)

    return out


# --------------------------------------------------------------------------- #
# 3. 入口
# --------------------------------------------------------------------------- #
def main():
    raw = parse_resumes(RAW_TXT)
    clean = clean_resumes(raw)
    clean.to_csv(CLEAN_CSV, index=False, encoding="utf-8-sig")
    print(f"[w7_clean] 解析 {len(raw)} 条，清洗后 {len(clean)} 条")
    print(f"[w7_clean] 已写出 -> {CLEAN_CSV}")
    dropped = clean.attrs.get("dropped_duplicates", 0)
    print(f"[w7_clean] 去重删除 {dropped} 条")
    return clean


if __name__ == "__main__":
    main()
