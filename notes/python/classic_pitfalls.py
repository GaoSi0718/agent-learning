# -*- coding: utf-8 -*-
# notes/python/classic_pitfalls.py —— Python 经典坑演示（P0 清单 W4「速记」配套）
# 面试常考「这段代码输出什么」——每个坑都带断言，跑一遍=复习一遍。
# 运行：venv\\Scripts\\python.exe notes\\python\\classic_pitfalls.py
import functools

def pitfall_mutable_default():
    """坑 1：默认参数用可变对象（出现率极高）。"""
    def append_to(x, lst=[]):          # ❌ 默认列表只创建一次，跨调用共享
        lst.append(x)
        return lst

    assert append_to(1) == [1]
    assert append_to(2) == [1, 2], "第二次调用不是 [2]——默认列表被共享"
    print("[OK] 可变默认参数：两次调用结果 [1] → [1, 2]（列表跨调用共享）")

    @functools.lru_cache(maxsize=None)
    def _ok(x, lst=None):
        lst = lst if lst is not None else []
        lst.append(x)
        return lst
    assert _ok(1) == [1] and _ok(2) == [2], "None 哨兵写法每次新建列表"
    print("[OK] 正确写法：lst=None + 函数体内初始化")

def pitfall_late_binding():
    """坑 2：闭包晚绑定——循环里定义的 lambda 捕获变量本身，不是值。"""
    fns = [lambda: i for i in range(3)]
    assert [f() for f in fns] == [2, 2, 2], "三个 lambda 都读到循环结束后的 i=2"
    fns_fixed = [lambda i=i: i for i in range(3)]   # 默认参数在定义时固化
    assert [f() for f in fns_fixed] == [0, 1, 2]
    print("[OK] 闭包晚绑定：lambda 捕获变量绑定（[2,2,2]），默认参数固化可解（[0,1,2]）")

def pitfall_shallow_copy():
    """坑 3：浅拷贝嵌套结构。"""
    import copy
    a = [[1, 2], [3, 4]]
    b = copy.copy(a)
    b[0].append(99)
    assert 99 in a[0], "浅拷贝后内层列表仍共享，改 b 影响 a"
    c = copy.deepcopy(a)
    c[0].append(100)
    assert 100 not in a[0], "深拷贝后内层独立"
    print("[OK] 深浅拷贝：copy.copy 共享内层，deepcopy 递归独立")

def pitfall_generator_once():
    """坑 4：生成器只能遍历一次。"""
    def gen():
        yield from [1, 2, 3]
    g = gen()
    assert list(g) == [1, 2, 3]
    assert list(g) == [], "生成器耗尽后再次遍历为空（易踩）"
    print("[OK] 生成器一次性：耗尽后再 list() 得空列表，复用需重新构造")

def pitfall_decorator():
    """坑 5：装饰器 + functools.wraps 保留元信息。"""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **k):
            return fn(*a, **k)
        return wrapper

    @deco
    def hello():
        """doc"""
    assert hello.__name__ == "hello" and hello.__doc__ == "doc", "wraps 应保留元信息"
    print("[OK] 装饰器：@functools.wraps 保留 __name__/__doc__")

if __name__ == "__main__":
    pitfall_mutable_default()
    pitfall_late_binding()
    pitfall_shallow_copy()
    pitfall_generator_once()
    pitfall_decorator()
    print("[PASS] Python 经典坑演示 5 项全过（跑一遍=复习一遍）")
