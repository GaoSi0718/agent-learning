# -*- coding: utf-8 -*-
# notes/os/gil_demo.py
"""D2 配套：GIL 实测——CPU 密集 vs I/O 密集下「多线程 / 多进程」的吞吐差异。
用法：python notes/os/gil_demo.py（总时长约 30-60 秒，含进程启动开销）
期望（P0 清单 D2 口径）：
  · CPU 密集：4 线程 ≈ 串行（GIL 把字节码执行串行化），明显慢于 4 进程；
  · I/O 密集：4 线程 ≈ 接近并行（sleep 等待期间 GIL 释放）。
设计：CPU 任务用纯 Python 循环（不用 C 扩展，避免numpy等在 C 层释放 GIL 造成干扰）；
一次调用耗时自动标定为 ~0.6s，保证计时可读。Windows 下进程池为 spawn 启动，
首个用例含解释器启动开销，表后已注明。零第三方依赖、零 API 成本。"""
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def cpu_task(n: int) -> int:
    """纯 Python 整数运算：GIL 下的 CPU 密集负载。"""
    x = 0
    for i in range(n):
        x = (x * 31 + i) % 1000003
    return x

def io_task(t: float) -> float:
    """sleep 模拟 IO 等待（等待期间 GIL 释放，线程可并行阻塞）。"""
    time.sleep(t)
    return t

def calibrate(target: float = 0.6) -> int:
    """标定 CPU 任务规模：让单次 cpu_task ≈ target 秒。"""
    n = 200_000
    t0 = time.perf_counter()
    cpu_task(n)
    per = time.perf_counter() - t0
    return max(200_000, int(n * target / per))

def bench(label: str, fn, args_list, workers: int, use_process: bool) -> float:
    Pool = ProcessPoolExecutor if use_process else ThreadPoolExecutor
    t0 = time.perf_counter()
    if use_process:
        with Pool(max_workers=workers) as pool:          # spawn：with 内启动+回收
            list(pool.map(fn, args_list))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(fn, args_list))
    return time.perf_counter() - t0

def serial(fn, args_list) -> float:
    t0 = time.perf_counter()
    for a in args_list:
        fn(a)
    return time.perf_counter() - t0

def main():
    n = calibrate()
    io_args = [0.6] * 4
    cpu_args = [n] * 4
    print(f"[标定] cpu_task 单次 ≈0.6s（n={n:,}）；I/O 任务 = sleep 0.6s × 4")
    print("-" * 76)

    print("[CPU 密集] 4 个相同 CPU 任务")
    s = serial(cpu_task, cpu_args)
    t = bench("cpu-threads", cpu_task, cpu_args, 4, use_process=False)
    p = bench("cpu-process", cpu_task, cpu_args, 4, use_process=True)
    print(f"  串行   : {s:6.2f}s（基准）")
    print(f"  4 线程 : {t:6.2f}s（加速 {s/t:4.2f}x —— 预期 ≈1x，GIL 串行化）")
    print(f"  4 进程 : {p:6.2f}s（加速 {s/p:4.2f}x —— 预期 >2x，扣除 spawn 启动开销）")
    cpu_gap = t / p
    print(f"  判据：4 线程明显慢于 4 进程（线程耗时 / 进程耗时 = {cpu_gap:.2f}，应 >1.5）")

    print("[I/O 密集] 4 个 sleep 0.6s 任务")
    s = serial(io_task, io_args)
    t = bench("io-threads", io_task, io_args, 4, use_process=False)
    print(f"  串行   : {s:6.2f}s（基准）")
    print(f"  4 线程 : {t:6.2f}s（加速 {s/t:4.2f}x —— 预期 ≈4x，等待期 GIL 释放）")
    print("-" * 76)
    ok = cpu_gap > 1.5 and t < s * 0.5
    print("[PASS] GIL 实测符合预期" if ok else "[FAIL] 实测与预期不符（见上表，请检查负载/机器）")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
