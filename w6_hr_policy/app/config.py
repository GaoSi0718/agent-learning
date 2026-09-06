# -*- coding: utf-8 -*-
# w6_hr_policy/app/config.py
"""集中配置：全部从环境变量/.env 读取（D1 模型名配置化），缺项给安全默认值。
注：本机 .env 所有者为 Administrators、普通用户只读，DEEPSEEK_BASE_URL 等 5 项
待孟轩手动补入（见 notes/zcode_reports/handover_20260906.md §四-2）；补入后即优先生效。"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "30"))
