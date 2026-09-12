# -*- coding: utf-8 -*-
"""断点状态更新器（zcode 20260913 长时运行协议配套工具）
用法:
  _run_state_updater.py T1 DONE                      # 置任务状态
  _run_state_updater.py T1 IN_PROGRESS 3 note文本    # 置状态+步号+备注(空格分词)
  _run_state_updater.py --hint "从 T2 第 3 步继续"    # 更新 resume_hint（可与其他参数同用）
  _run_state_updater.py                              # 仅刷新心跳
写入方式：tmp + os.replace 原子写。
"""
import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "_run_state.json")


def load():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "run_id": "zcode-20260913-1",
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tasks": {},
        "blocked": [],
        "budget_used_usd": 0.0,
        "resume_hint": "",
    }


def main():
    st = load()
    st["last_heartbeat"] = datetime.now().astimezone().isoformat(timespec="seconds")
    args = sys.argv[1:]
    if args and args[0] == "--hint":
        st["resume_hint"] = args[1]
        args = args[2:]
    if len(args) >= 2:
        tid, status = args[0], args[1]
        t = st["tasks"].setdefault(tid, {})
        t["status"] = status
        if len(args) >= 3:
            t["step"] = args[2]
        if len(args) >= 4:
            t["note"] = " ".join(args[3:])
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)
    print("STATE_OK")


if __name__ == "__main__":
    main()
