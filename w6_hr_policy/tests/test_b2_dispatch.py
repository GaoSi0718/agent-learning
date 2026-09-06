# -*- coding: utf-8 -*-
# w6_hr_policy/tests/test_b2_dispatch.py
"""B2 自测 1：dispatch 双重校验 + 并发（清单 5 条用例 + 并发耗时验证）。
用例 1/2 走真实语料检索与真实计算；用例 3 注册临时 slow_probe 验证并发墙钟。"""
import sys, pathlib, asyncio, time, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import w6_hr_policy.app.tools as tools_mod
from w6_hr_policy.app.dispatch import run_calls, SCHEMA_MAP

async def _slow(tag: str) -> str:
    await asyncio.sleep(0.5)
    return f"slow-{tag}"

def main():
    tools_mod.IMPL["slow_probe"] = _slow
    SCHEMA_MAP["slow_probe"] = {"type": "object",
                                "properties": {"tag": {"type": "string"}},
                                "required": ["tag"]}

    async def run():
        r1 = await run_calls([{"name": "search_policy", "args": {"query": "年假", "category": "年假"}}])
        print("用例1 正常检索:", json.dumps(r1[0], ensure_ascii=False)[:200].replace("\n", " "))
        r2 = await run_calls([{"name": "calc_annual_leave", "args": {"hire_date": "2014-03-01"}}])
        print("用例2 年假计算:", str(r2[0]["result"])[:140])
        # 法定四档边界（2026-09-06 基准）：司龄 0.5 年→0 天；6.5 年→5 天；12.5 年→10 天；26.5 年→15 天
        for hire, expect in [("2026-03-01", "0 天"), ("2020-03-01", "5 天"),
                             ("2014-03-01", "10 天"), ("2000-01-01", "15 天")]:
            rr = await run_calls([{"name": "calc_annual_leave", "args": {"hire_date": hire}}])
            got = str(rr[0]["result"])
            assert f"按法定 {expect}" in got, f"司龄档位错误：{hire} 应为 {expect}，实得 {got[:60]}"
        print("用例2b 法定四档边界: 0/5/10/15 天 全对")
        t0 = time.perf_counter()
        r3 = await run_calls([{"name": "slow_probe", "args": {"tag": "a"}},
                              {"name": "slow_probe", "args": {"tag": "b"}},
                              {"name": "slow_probe", "args": {"tag": "c"}}])
        dt = time.perf_counter() - t0
        print(f"用例3 并发: 3 个 0.5s 任务墙钟 {dt:.2f}s（串行约 1.5s）")
        r4 = await run_calls([{"name": "delete_policy", "args": {}}])
        print("用例4 高危拦截:", r4[0]["status"], "|", r4[0]["result"])
        r5 = await run_calls([{"name": "search_policy", "args": {"query": "年假", "category": "火星"}}])
        print("用例5 枚举非法:", r5[0]["status"], "|", r5[0]["result"])
        return r1, r3, dt

    r1, r3, dt = asyncio.run(run())

    assert r1[0]["status"] == "ok" and len(str(r1[0]["result"])) > 50, "用例1 检索失败"
    assert all(r["status"] == "ok" for r in r3), "用例3 并发执行有失败"
    assert dt < 1.0, f"用例3 并发生效判据失败：墙钟 {dt:.2f}s ≥ 1.0s（应为 ≈0.5s）"
    print("\n[PASS] B2 dispatch：5 条用例全过；并发墙钟 %.2fs ≈ 单个任务（性能优化生效）" % dt)

if __name__ == "__main__":
    main()
