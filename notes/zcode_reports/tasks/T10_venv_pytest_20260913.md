# T10 · venv 装 pytest + 10 个测试可用性盘点（对应 §十 #11）· 2026-09-13

## ① 目标与结论

**结论：pytest 9.1.1 已装入项目 venv（仅 venv 内，未动全局）；10 个测试全部为"脚本式"（含 `if __name__ == "__main__"`，无 `test_*` 函数）→ pytest 收集 0 条，「一条 pytest 解决」不成立被实测坐实；7 个离线测试以独立进程逐个跑全部 PASS；3 个需 `W6_API_KEY` 标 BLOCKED。**

## ② 实际执行（命令 + 原始输出）

**安装**：
```
venv/Scripts/python.exe -m pip install pytest --no-input --disable-pip-version-check
Successfully installed colorama-0.4.6 iniconfig-2.3.0 pluggy-1.6.0 pygments-2.21.0 pytest-9.1.1（退出码 0）
```

**收集测试**（全目录 `--collect-only -q`）：`6 tests collected` 后 **INTERNALERROR**——`test_v17_fallback.py` 在 **import（模块级）时直接执行整套验收**并 `raise SystemExit`（L74），pytest 采集被它炸断。**单文件收集该文件则正常通过**（详见 ③ 的污染发现）。

**独立进程逐个跑（离线 7 个，全部 rc=0）**：
```
test_b2_dispatch.py       rc=0  [PASS] B2 dispatch：5 条用例全过；并发墙钟 0.51s
test_b1_context_compact.py rc=0 [PASS] compact 机制：22 条 → 5 条
test_b3_resilience.py     rc=0  [PASS] B3 可靠性三件套 5 项断言全过
test_v17_auth.py          rc=0  [PASS] Z2 鉴权+限流 5 项断言全过
test_v17_memory_wal.py    rc=0  [PASS] R14 记忆库 WAL+并发写 3 项断言全过
test_c2_loop_breaker.py   rc=0  [PASS] C2 终止三件套：死循环 3 步停止（**单独进程**）
test_v17_fallback.py      rc=0  [PASS] R6 降级接线 6 项断言全过
```

**需 API 的 3 个（按 T21 约定不尝试执行，只做收集性判定）**：`test_b2_tool_selection.py` / `test_b2_e2e.py` / `test_b1_memory_12rounds.py` —— 可 import、收集 0 条、脚本直跑需 `W6_API_KEY`（`.env` 缺，红线 #4 不补）。

## ③ 重要发现：组合收集时 v17_fallback 会被"前序测试"污染出假失败

全目录采集时 v17_fallback 报 6 项断言失败（SystemExit）；**单独运行 6/6 全过**。根因：字母序在前的测试（e2e 等）先 import 了 `w6_hr_policy.app.main` 并改写 `os.chdir`/memory.db 状态，v17_fallback 的模块级验收在脏状态下运行。**结论：这些脚本式测试只能逐个独立进程跑**——这也写进了 T11 的笔记⑧纠错。

## ④ 推荐跑法（写进报告供孟轩/迪莫直接用）

```bash
cd D:\WorkBuddyData\projects\agent-learning
venv\Scripts\python.exe w6_hr_policy\tests\test_b2_dispatch.py        # 逐个，独立进程
venv\Scripts\python.exe w6_hr_policy\tests\test_c2_loop_breaker.py    # 必须单独进程最后跑
```
（`run_all_tests.py` 也可批量；pytest 留给未来把脚本改造成真 test 函数后再用。）

## ⑤ 遗留 / 阻塞

- 3 个 API 测试：补 `W6_API_KEY` 后逐个跑（见 T21 报告的一条命令）。
- venv 仍缺 sklearn/scipy（9/13 M4 晨报提及的 W1 周一风险）——超出本任务范围，已列入值守总结「给孟轩的下一步」。
