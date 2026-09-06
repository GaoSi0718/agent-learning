# -*- coding: utf-8 -*-
# notes/cache/cache_problems_demo.py —— 用字典模拟缓存三大问题（P0 清单源码转写）
# 实测预期：无防护约 100 次回源；有防护 1 次（互斥锁 + 空值缓存生效）。
# 运行：venv\\Scripts\\python.exe notes\\cache\\cache_problems_demo.py
import threading, time

class FakeDB:
    def __init__(self):
        self.hits = 0
        self.data = {1: "real"}
    def get(self, k):
        self.hits += 1            # 每次回源都计数
        time.sleep(0.01)          # 模拟 DB 耗时
        return self.data.get(k)

db, cache, lock = FakeDB(), {}, threading.Lock()

def get_naive(k):                 # ❌ 无防护：穿透 + 击穿
    if k in cache:
        return cache[k]
    v = db.get(k)
    if v:
        cache[k] = v
    return v

def get_safe(k):                  # ✅ 空值缓存 + 互斥锁
    if k in cache:
        return cache[k]
    with lock:                    # 互斥：只有一个线程回源
        if k in cache:            # 双重检查：拿到锁后再查一次
            return cache[k]
        v = db.get(k)
        cache[k] = v if v else "__NULL__"   # 空值也缓存，防穿透
        return v

# 压测：100 个并发查同一个不存在的 key
def bench(fn, key, n=100):
    db.hits = 0
    ts = [threading.Thread(target=fn, args=(key,)) for _ in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return db.hits

if __name__ == "__main__":
    naive = bench(get_naive, 999)
    safe = bench(get_safe, 999)
    print("无防护 DB 回源次数:", naive)
    print("有防护 DB 回源次数:", safe)
    assert naive >= 90, f"无防护基线异常：{naive}"
    assert safe == 1, f"有防护应恰好 1 次回源，实得 {safe}"
    print("[PASS] 缓存三大问题演示：100 并发穿透，防护后回源 100→1")
