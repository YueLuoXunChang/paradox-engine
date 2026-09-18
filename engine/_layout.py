# -*- coding: utf-8 -*-
"""
_layout.py — 运行环境判定（源码仓 or 安装后的包）
=====================================================
为什么需要它：
    本仓的测试分两类——
      ① 构件级：只依赖 engine/ 内部（装到哪都能跑）；
      ② 门面级：要读仓库根的文件（README、docs/、pyproject、CONTRIBUTING）——
         它们是**源码仓专属**检查（对外承诺的一致性、发布面残留）。
    `pip install paradox-engine` 之后没有仓库根，门面级检查无从查起；此时应当
    **明确跳过并说明原因**，而不是报一堆假失败（也不该静默当通过）。

判定办法（不猜、只看文件系统）：
    仓库根 = engine/ 的上一级。若该目录下同时存在 README.md 与 docs/，判为源码仓。
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)


def repo_root():
    """engine/ 的上一级目录（源码仓时为仓库根；安装后为 site-packages）。"""
    return _REPO


def in_source_checkout():
    """是否在源码仓中运行（而不是安装后的包）。"""
    return (os.path.exists(os.path.join(_REPO, 'README.md'))
            and os.path.isdir(os.path.join(_REPO, 'docs')))


def skip_note(what):
    """统一的跳过说明（诚实：说清为什么不查、去哪查）。"""
    return (f'非源码仓环境（未找到 {os.path.join(_REPO, "README.md")} 与 '
            f'docs/）→ 跳过{what}——这类检查属于源码仓；'
            '请在源码仓运行 python run_tests.py。')
