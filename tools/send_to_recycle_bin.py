# -*- coding: utf-8 -*-
"""
把指定文件送入 Windows 回收站（可还原），而非直接删除。

背景：本机 PowerShell 会拦截 New-Object -ComObject 与 Add-Type，
send2trash 库对含中文的路径会错误转换成 DOS 短名导致失败。
因此直接用 ctypes 调用 shell32.SHFileOperationW，传 Unicode 长路径。

用法：
    python send_to_recycle_bin.py <文件1> <文件2> ... [--apply]

默认 dry-run 只打印待删清单；加 --apply 才真正送入回收站。
"""

import sys
from ctypes import (Structure, byref, c_int, c_void_p, cast, c_wchar_p,
                    create_unicode_buffer, windll, POINTER)
from pathlib import Path

FOF_ALLOWUNDO = 0x0040          # 送回收站
FOF_NOCONFIRMATION = 0x0010     # 不弹确认框
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400

LPCWSTR = c_wchar_p


class SHFILEOPSTRUCTW(Structure):
    _fields_ = [
        ("hwnd", c_void_p),
        ("wFunc", c_int),
        ("pFrom", LPCWSTR),
        ("pTo", LPCWSTR),
        ("fFlags", c_int),
        ("fAnyOperationsAborted", c_int),
        ("hNameMappings", c_void_p),
        ("lpszProgressTitle", LPCWSTR),
    ]


def to_recycle_bin(path: Path) -> bool:
    """把单个文件/目录送入回收站，返回是否成功。

    注意：SHFileOperationW 必须接收**绝对路径**，传相对路径会静默失败。
    """
    abs_path = str(path.resolve()) + "\0\0"
    buf = create_unicode_buffer(abs_path)
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = 3  # FO_DELETE
    op.pFrom = cast(buf, LPCWSTR)
    op.pTo = None
    op.fAnyOperationsAborted = 0
    op.hNameMappings = None
    op.lpszProgressTitle = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    rc = windll.shell32.SHFileOperationW(byref(op))
    return rc == 0


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv

    if not args:
        print(__doc__)
        return

    files = []
    for a in args:
        p = Path(a)
        if not p.exists():
            print(f"[跳过] 不存在：{p.name}")
            continue
        files.append(p)

    print(f"待送入回收站 {len(files)} 个文件：")
    total = 0
    for p in files:
        size = p.stat().st_size
        total += size
        print(f"  {size:>10,} B  {p.name}")
    print(f"合计 {total:,} B\n")

    if not apply:
        print("[dry-run] 未执行，加 --apply 送入回收站。")
        return

    ok, fail = 0, []
    for p in files:
        if to_recycle_bin(p):
            ok += 1
            print(f"  ✅ {p.name}")
        else:
            fail.append(p.name)
            print(f"  ❌ 失败：{p.name}")

    print(f"\n完成：成功 {ok} / 失败 {len(fail)}")
    if fail:
        print("失败清单：" + ", ".join(fail))


if __name__ == "__main__":
    main()
