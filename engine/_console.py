# -*- coding: utf-8 -*-
"""
_console.py — 控制台编码自愈（Windows 中文环境友好）
=========================================================
问题（真实踩过）：构件自测/CLI 报告里含 ✅⚠️→ 等符号，Windows 默认控制台是
GBK，直接 `print` 会 UnicodeEncodeError 崩掉——用户第一次跑就以为工具坏了。

做法：入口处把 stdout/stderr 重设为 UTF-8（不依赖用户先设 PYTHONIOENCODING）。
诚实边界：只改**本进程输出流编码**，不动系统代码页；老 Python（<3.7）或流
不支持 reconfigure 时静默跳过（不影响功能，仍可按老办法设环境变量）。
"""

import sys


def ensure_utf8_console():
    """把 stdout/stderr 设为 UTF-8（能设才设，设不了不报错）。返回是否成功。"""
    ok = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:  # noqa: BLE001——重定向流/老版本不支持即跳过
            ok = False
    return ok
