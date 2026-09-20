# -*- coding: utf-8 -*-
"""
_capability_matrix.py — 能力矩阵自动生成（docs/capability_matrix.md）+ 漂移检查
================================================================================
为什么有它：作者手上有一个待定问题——**四件外部机制（区间代数 / ALC / μ 演算 / ASP）
要不要接进判类路由**。这个决定需要一份能一眼看全的数据：每个题型**现在**被送到哪些构件、
哪些构件**能单独调但判类器不会自动送材料**、以及没接线的都是什么。

这三样都躺在活代码里（`control/classifier.py` 的 ROUTE 表 + `ai/tools.py` 的注册表 +
各构件 docstring），散着看没法决策——生成成一张表，就不会与代码脱钩。

生成什么：
    docs/capability_matrix.md——① 12 题型 × 3 档的路由明细（构件 + 路由理由，逐字来自
    ROUTE 表）② 每个题型的接线概览 ③ **没接线的构件**清单（工具名 + 一句话）④ 覆盖率小结。

口径（写进产物，免得被误读）：
    - **"已接线" = 判类器会把材料送到它**；没接线的构件**照样能单独调用**
      （命令行 `--call 工具`、AI 工具 `call_tool`），只是不会自动被送材料；
    - 表格内容全部由活代码生成；**唯一人工写的是文件末尾那一节"提案"**（候选接线的题型），
      并明确标注是提案、待作者定。

用法：
    python engine/_capability_matrix.py            # 打印
    python engine/_capability_matrix.py --write    # 落盘
    python engine/_capability_matrix.py --check    # 与现有文件比对（漂移即非零退出）
"""

import ast
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
DOC = os.path.join(_REPO, 'docs', 'capability_matrix.md')

_LEVELS = ('L1', 'L2', 'L3')

# 这一节是**提案**（人工写的，不在生成口径里）：来源见 ROADMAP 的候选清单与本仓 CHANGELOG 里各件的「为什么做」段，
# 只列"这件没接线，接线大概能补哪个题型"——**待作者定**，别当事实读。

def _router():
    """拿路由表与题型名（import 活代码）。"""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from control.classifier import ROUTE, _TYPE_NAME
    return ROUTE, _TYPE_NAME


def _supplement():
    """线索触发补跑表（总控里的 CLUE_SUPPLEMENT）：这些构件**不进默认管线**，
    题型对得上 + 人给足线索就跑（哪一档都跑得到）。"""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from control.controller import CLUE_SUPPLEMENT
    return CLUE_SUPPLEMENT


def _tools():
    """工具注册表：工具名 → (叶子模块名, 一句话)。"""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from ai.tools import _TOOL_REGISTRY
    out = {}
    for name, modpath, desc in _TOOL_REGISTRY:
        out[name] = (modpath, modpath.split('.')[-1], desc)
    return out


def _summaries():
    """各构件的一句话（AST 只读，不执行）——按叶子模块名索引。"""
    from _components_doc import scan
    out = {}
    for layer, items in scan().items():
        for it in items:
            leaf = os.path.basename(it['path'])[:-3]
            out[leaf] = (it['path'], it.get('summary', ''), layer)
    return out


def _routed_modules(route):
    """路由表里出现过的构件（叶子模块名）→ 出现在哪些题型/档。"""
    seen = {}
    for (typ, lvl), (calls, _why) in sorted(route.items()):
        for call in calls:
            mod = call.split('.')[0]
            seen.setdefault(mod, []).append('%s-%s' % (typ, lvl))
    return seen


def render():
    route, type_name = _router()
    tools = _tools()
    sums = _summaries()
    routed = _routed_modules(route)
    supplement = _supplement()
    sup_names = {c for c, _t, _w in supplement}
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from control.controller import ADAPTER_SPECS
    L = []
    L.append('# 能力矩阵（题型 × 构件 × 接线状态）')
    L.append('')
    L.append('> 本文件由 `python engine/_capability_matrix.py` 从**活代码**自动生成'
             '（`control/classifier.py` 的 ROUTE 表 + `ai/tools.py` 的注册表 + 各构件 '
             'docstring），请勿手改；漂移检查见 `engine/test_capability_matrix.py`。')
    L.append('>')
    L.append('> 口径（**三态**）：')
    L.append('> 1. **默认管线**——判类器按"题型 × 复杂度档"自动把材料送过去；')
    L.append('> 2. **线索触发补跑**——题型对得上 + 人给足该构件的线索就跑。'
             '这些构件都要"人写的正式式子"（formula / program / relations / '
             'tbox / states / arguments），**不进默认管线**：放进管线会让本来线索'
             '齐了的材料显示"还欠"，也破坏 L1/L2/L3 的档位语义；')
    L.append('> 3. **未接线**——只能单独调用（命令行 `paradox-engine --call 工具`、'
             'AI 工具 `call_tool`）。')
    L.append('')
    L.append('## 一、每个题型现在接了什么（逐字来自 ROUTE 表）')
    L.append('')
    for typ in sorted(type_name):
        L.append('### %s %s' % (typ, type_name[typ]))
        L.append('')
        L.append('| 档 | 路由到的构件 | 路由理由（路由表原文） |')
        L.append('|---|---|---|')
        for lvl in _LEVELS:
            entry = route.get((typ, lvl))
            if not entry:
                L.append('| %s | **（没配）** |  |' % lvl)
                continue
            calls, why = entry
            mods = []
            for c in calls:
                mod = c.split('.')[0]
                if mod not in mods:
                    mods.append(mod)
            L.append('| %s | %s | %s |' % (lvl, ' · '.join(mods), why))
        L.append('')

    L.append('## 二、每个题型的接线概览')
    L.append('')
    L.append('| 题型 | 名称 | L1 | L2 | L3 | 涉及构件数 |')
    L.append('|---|---|---|---|---|---|')
    for typ in sorted(type_name):
        cells, mods = [], set()
        for lvl in _LEVELS:
            e = route.get((typ, lvl))
            if not e:
                cells.append('—')
                continue
            ms = []
            for c in e[0]:
                mod = c.split('.')[0]
                if mod not in ms:
                    ms.append(mod)
            mods |= set(ms)
            cells.append(' + '.join(ms) if ms else '—')
        L.append('| %s | %s | %s | %s | %s | %d |'
                 % (typ, type_name[typ], cells[0], cells[1], cells[2],
                    len(mods)))
    L.append('')

    L.append('## 三、线索触发补跑（题型对得上 + 线索给全就跑；不进默认管线）')
    L.append('')
    L.append('| 构件 | 适用题型 | 需要的线索（键） | 补跑能补什么 |')
    L.append('|---|---|---|---|')
    for comp, types, why in supplement:
        spec = ADAPTER_SPECS.get(comp)
        keys = '、'.join(spec[1]) if spec else '?'
        L.append('| `%s` | %s | %s | %s |'
                 % (comp, ' · '.join(types), keys, why))
    L.append('')
    L.append('## 四、未接线（只能单独调用）的构件')
    L.append('')
    L.append('（工具名 → 一句话；这些正是"要不要接线"这件事的对象）')
    L.append('')
    L.append('| 工具 | 层 | 构件文件 | 一句话 |')
    L.append('|---|---|---|---|')
    # 引擎自身（判类器/总控等在 control 层）不参与"接线"讨论——它们就是路由本身
    _SELF = ('control',)
    # 路由名可能是**层前缀**（如 `skeleton` ↔ 工具模块 `skeleton.mtmp`），
    # 所以按模块路径匹配，而不是只比叶子名。
    def _wired(name):
        modpath, leaf, _desc = tools[name]
        if leaf in routed:              # 工具注册名就是路由里的名字
            return True
        return any(modpath.startswith(rn + '.') for rn in routed)   # 层前缀

    all_unwired = [n for n in sorted(tools)
                   if not _wired(n) and n not in sup_names]
    unwired, self_ones = [], []
    for name in all_unwired:
        modpath, leaf, desc = tools[name]
        path, _summ, layer = sums.get(leaf, ('engine/%s.py' % leaf, '', '?'))
        row = (name, layer, path, desc)
        (self_ones if layer in _SELF else unwired).append(row)
    for name, layer, path, desc in unwired:
        L.append('| `%s` | %s | `%s` | %s |' % (name, layer, path, desc))
    L.append('')
    L.append('另有 **%d** 件属于引擎自身（%s），不参与"要不要接线"的讨论——它们就是'
             '路由本身。'
             % (len(self_ones), '、'.join('`%s`' % r[0] for r in self_ones)))
    L.append('')

    L.append('## 五、小结（机器算）')
    L.append('')
    have = [t for t in sorted(type_name) if any((t, lv) in route
                                               for lv in _LEVELS)]
    L.append('- 有路由的题型：**%d/%d**（%s）'
             % (len(have), len(type_name), '、'.join(have)))
    L.append('- 路由表条目：**%d** 条（题型 × 档）' % len(route))
    L.append('- 路由里的构件名：**%d** 个（%s）——其中 **%d 个有对应工具**，'
             '其余是入口/层名，不占工具位'
             % (len(routed), '、'.join(sorted(routed)),
                len(tools) - len(unwired) - len(self_ones) - len(sup_names)))
    L.append('- 工具总数：**%d** 件，分三态：**默认管线 %d 件** · '
             '**线索触发补跑 %d 件** · **未接线（只 --call）%d 件**'
             '（另有 %d 件是引擎自身，见上一节）'
             % (len(tools),
                len(tools) - len(unwired) - len(self_ones) - len(sup_names),
                len(sup_names), len(unwired), len(self_ones)))
    L.append('')

    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    text = render()
    if '--write' in argv:
        io.open(DOC, 'w', encoding='utf-8', newline='\n').write(text)
        print('已写出 %s（%d 字）'
              % (os.path.relpath(DOC, _REPO).replace('\\', '/'), len(text)))
        return 0
    if '--check' in argv:
        have = io.open(DOC, encoding='utf-8').read() if os.path.exists(DOC) else ''
        if have != text:
            print('能力矩阵与代码不一致（跑 --write 更新）')
            return 1
        print('能力矩阵一致')
        return 0
    print(text)
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
