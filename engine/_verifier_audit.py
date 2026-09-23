# -*- coding: utf-8 -*-
"""
_verifier_audit.py — 验证方登记：每件产物**点名它的验证方**（常设检查，产物落 docs/verifier_audit.md）
================================================================================================
为什么要它（口径来自"工具不可自证"）：**产物没有独立检验方时，处于"未验状态"**——
不是"暂时没验"，而是不得当定论用。本仓此前**没有这张表**（`verifier` 全库零命中）：
"自测绿"到处都有，但"谁给谁当独立验证方"没人登记，于是**只自证的件混在已验证的件里**。

本表回答三件事（**只回答这三件**）：
    ① 每件构件**有没有**独立验证方（四态：外部 / 跨构件 / 独立复算 / 只有性质）；
    ② 验证方**是谁**（点名：哪个外部实现、哪个同仓构件、哪种换算法）；
    ③ **哪些件只自证或没测**——这些必须逐个登记签字（测试里那张表），新增一件就得改一处。

怎么判的（两条来源分开，别混）：
    · **结构性判据**（可信、直接读代码）：测试文件名 ↔ 构件名的对应关系；测试文件 **AST 扫 import**，
      看它引用了哪个**别的构件**（引用了 ＝ 那件在给它当独立验证方）。
    · **关键词初筛**（启发式、**可能有体裁偏差**）：测试文本里出现"按定义直算/穷举/手算/对拍/
      oracle/另一条路"这类字样时，记作"疑似独立复算"，**并把命中的字样写进证据列**，
      供人复核。初筛**不是终判**（外部协作方的同款筛查在另一种文体上几乎全落"待人工"）。
    · **登记**（人工签字）：外部验证方那几条写在下面的 `EXTERNAL` 里——每条的"命中词"
      必须在对应测试文件里真的出现，否则报错（防表格与文件脱钩）。

诚实边界：
    本表只说"**有没有**独立验证方、是谁"，**不说"验得对不对"**（那是变异验收与对拍脚本的活）；
    关键词初筛会**漏**（换了一种写法就认不出）也会**误**（提了一句"对拍"不等于真做了），
    所以四态是**索引不是结论**；`untested`/`property_only` 两类必须在测试里逐个登记。

用法：
    python engine/_verifier_audit.py            # 打印摘要
    python engine/_verifier_audit.py --write    # 写 docs/verifier_audit.md
    python engine/_verifier_audit.py --check    # 漂移检查（产物 == 现算）
"""

import ast
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
OUT = os.path.join(_REPO, 'docs', 'verifier_audit.md')

# ── 外部验证方登记（人工签字）：构件 → (测试里必须出现的命中词, 公开面安全的说明)
EXTERNAL = {
    'criticality': ('外部', '外部协作者另写的 oracle 夹具：同一份合成样本上对拍，'
                            '换算口径后逐位相等；跑法在仓库外（不进公开仓）'),
    'growth_guard': ('外部', '外部协作者另写的参考实现：对照模型边界，'
                             '查出本件缺"步长限幅"这一件；跑法在仓库外'),
    'bisimulation': ('外部第三方', '外部协作者另写的分区细化实现：4 个案例 + 200 组随机结构'
                                   '结论完全一致；跑法在仓库外'),
}

# 关键词初筛用的字样（命中即记"疑似独立复算"，并把命中的字样写进证据）
# **按语料实际用词校准过**（2026-09-23）：先按直觉写的一版漏掉了 `另写/另算/真值表/已知答案/
# 参考实现/手推/穷尽/逐条核` 这些本仓真在用的写法，把一批**有独立路**的件误判成"只有性质测试"。
# 反方向的坑也记着：`模型/反例/见证/对照/不动点` 太泛（很多是构件**自己的输出**），
# 一律**不当**独立验证的证据。
ORACLE_MARKS = ['按定义直算', '定义直算', '按定义', '穷举', '穷尽', '手算', '手推', '对拍',
                'oracle', 'Oracle', 'ORACLE', '换算法', '另一条路', '第二条路', '第三条路',
                '独立的第二条路', '参考实现', '已知答案', '真值表', '逐条核', '反向 BFS',
                '交叉', '互验', 'brute', '暴力', '穷搜', '另写', '另算', '独立的']

STATE_ORDER = ['external', 'cross', 'oracle', 'property_only', 'untested']
STATE_CN = {'external': '外部验证方', 'cross': '跨构件互验', 'oracle': '独立复算（初筛）',
            'property_only': '只有性质/接口测试', 'untested': '无测试引用'}


def _is_component(name):
    return (name.endswith('.py') and not name.startswith('test_')
            and not name.startswith('_') and name != '__init__.py')


def components():
    """扫盘列出构件（与构件参考同一来源口径）。"""
    out = []
    for dp, dn, fn in os.walk(_HERE):
        if '__pycache__' in dp or 'build' in dp.split(os.sep):
            continue
        for f in sorted(fn):
            if _is_component(f):
                out.append(os.path.join(dp, f))
    return sorted(out)


def test_files():
    out = []
    for dp, dn, fn in os.walk(_HERE):
        if '__pycache__' in dp or 'build' in dp.split(os.sep):
            continue
        for f in sorted(fn):
            if f.startswith('test_') and f.endswith('.py'):
                out.append(os.path.join(dp, f))
    return sorted(out)


def imports_of(path):
    """AST 扫出该文件 import 的模块名（末段）。"""
    try:
        tree = ast.parse(io.open(path, encoding='utf-8').read())
    except SyntaxError:
        return set(), set()
    names, raw = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                names.add(al.name.split('.')[-1])
                raw.add(al.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split('.')[-1])
                raw.add(node.module)
            for al in node.names:
                names.add(al.name.split('.')[-1])
    return names, raw


def _read(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def _hardcoded_checks(text):
    """数一下"期望值直接写死"的断言（用例集的强度指标，不是独立验证）。"""
    return len(re.findall(r"check\([^)]*,\s*(?:True|False|\d+|'[^']*'|\"[^\"]*\")", text))


def audit():
    """返回 (rows, problems)。problems 里装"表格与文件脱钩"这类必须报出来的事。"""
    problems = []
    comps = components()
    tests = test_files()
    test_by_stem = {os.path.basename(t)[5:-3]: t for t in tests}   # test_X.py → X
    comp_modules = {os.path.basename(c)[:-3]: c for c in comps}
    # 每个测试文件引用了哪些"别的构件"
    cross_of = {}
    for t in tests:
        names, _ = imports_of(t)
        cross_of[t] = {n for n in names if n in comp_modules}
    rows = []
    for stem, path in sorted(comp_modules.items()):
        layer = os.path.basename(os.path.dirname(path)) or 'engine'
        own = test_by_stem.get(stem)
        refs = [own] if own else []
        for t in tests:
            if own and t == own:
                continue
            if stem in cross_of.get(t, set()):
                refs.append(t)
        text = '\n'.join(_read(t) for t in refs if t)
        has_selftest = '__main__' in _read(path)
        cross = sorted(cross_of.get(own, set()) - {stem}) if own else []
        marks = sorted({m for m in ORACLE_MARKS if m in text})
        ext = None
        if stem in EXTERNAL:
            token, note = EXTERNAL[stem]
            if token not in text:
                problems.append('%s 的外部验证方登记与文件脱钩：命中词 %r 没在测试里出现'
                                % (stem, token))
            else:
                ext = note
        if ext:
            state = 'external'
        elif cross:
            state = 'cross'
        elif marks:
            state = 'oracle'
        elif refs:
            state = 'property_only'
        else:
            state = 'untested'
        ev = []
        if ext:
            ev.append('外部：' + EXTERNAL[stem][1].split('：')[0])
        if cross:
            ev.append('引用了同仓构件 ' + '、'.join(cross))
        if marks:
            ev.append('疑似独立复算：命中 ' + '、'.join(marks[:4]))
        if not ev:
            if refs:
                n_hard = _hardcoded_checks(text)
                ev.append('用例集：期望值直接写死 %d 条（能挡回归，**不构成独立验证方**）'
                          % n_hard if n_hard else '只有接口/性质断言（无独立验证方）')
            else:
                ev.append('没有任何测试文件引用它')
        rows.append({'comp': stem, 'path': os.path.relpath(path, _REPO).replace('\\', '/'),
                     'layer': layer, 'tests': [os.path.relpath(t, _REPO).replace('\\', '/')
                                               for t in refs],
                     'selftest': has_selftest, 'state': state, 'evidence': '；'.join(ev)})
    return rows, problems


def render(rows):
    n = len(rows)
    cnt = {s: sum(1 for r in rows if r['state'] == s) for s in STATE_ORDER}
    L = []
    L.append('# 验证方登记（每件产物点名它的验证方）')
    L.append('')
    L.append('> 本文件由 `engine/_verifier_audit.py` 自动生成（`--check` 守着漂移）。**别手改**。')
    L.append('>')
    L.append('> **口径**（来自"工具不可自证"）：**产物没有独立检验方时处于"未验状态"**——不是')
    L.append('> "暂时没验"，而是不得当定论用。本表只回答"**有没有**独立验证方、**是谁**"，')
    L.append('> **不回答"验得对不对"**（那是变异验收与对拍脚本的活）。')
    L.append('>')
    L.append('> **五态怎么判**：结构性判据（测试文件 ↔ 构件的对应、**AST 扫 import** 看它引用了')
    L.append('> 哪个别的构件）＋ 关键词初筛（"按定义直算/穷举/手算/对拍/oracle"等字样，**命中词写进')
    L.append('> 证据列**、供人复核）＋ 人工登记（外部验证方那几条）。**初筛不是终判**：会漏（换写法就')
    L.append('> 认不出）也会误（提了一句"对拍"不等于真做了）。')
    L.append('>')
    L.append('> 因此：**`只有性质/接口测试` 与 `无测试引用` 两类必须逐个登记签字**'
             '（见 `engine/test_verifier_audit.py` 的登记表），新增这类件就得改一处。')
    L.append('')
    L.append('## 一、统计')
    L.append('')
    L.append('| 态 | 件数 | 含义 |')
    L.append('|:--|--:|:--|')
    meaning = {
        'external': '有**外部/第三方**实现当验证方（人工登记，命中词须在测试里出现）',
        'cross': '同仓**另一个构件**参与互验（AST 扫 import 判出来的）',
        'oracle': '测试里有**独立复算**的痕迹（关键词初筛）',
        'property_only': '只有性质/接口断言（PORTS · boundary · 单调/恒等 · 拒绝路径）——**待人工确认**',
        'untested': '没有测试文件引用它——**待人工确认**',
    }
    for s in STATE_ORDER:
        L.append('| %s | **%d** | %s |' % (STATE_CN[s], cnt[s], meaning[s]))
    L.append('| 合计 | **%d** | 构件总数（扫盘口径，与 `docs/components.md` 同源） |' % n)
    L.append('')
    L.append('## 二、逐件登记')
    L.append('')
    L.append('| 构件 | 层 | 状态 | 验证方/证据 | 被哪个测试文件引用 | 自带自测 |')
    L.append('|:--|:--|:--|:--|:--|:--|')
    for r in rows:
        tests = '、'.join('`%s`' % t.split('/')[-1] for t in r['tests']) or '—'
        L.append('| `%s` | %s | %s | %s | %s | %s |'
                 % (r['comp'], r['layer'], STATE_CN[r['state']], r['evidence'], tests,
                    '✅' if r['selftest'] else '—'))
    L.append('')
    L.append('> "自带自测"指模块自己的 `__main__` 里跑的那套——**那是自证，不算独立验证方**，')
    L.append('> 单独列出来是为了看清"自测绿"与"有人独立验过"是两件事。')
    L.append('')
    L.append('## 三、只自证 / 没测的（这些必须登记签字）')
    L.append('')
    L.append('判据：这些件**没有**独立验证方——测试只能挡回归，不能证明对。')
    L.append('补法（按省事程度）：① 找**同仓另一个构件**互验（把问题翻译过去，两条独立实现互相验）；')
    L.append('② 在测试里写**另一条算法**（穷举小模型 / 按定义直算 / 反向 BFS 这类，不走构件内部那条路）；')
    L.append('③ 请**外部实现**对拍（跑法可留在仓库外，本仓测试里点名验证方即可）。')
    L.append('')
    L.append('| 构件 | 层 | 状态 | 现在有什么 |')
    L.append('|:--|:--|:--|:--|')
    for r in rows:
        if r['state'] in ('property_only', 'untested'):
            L.append('| `%s` | %s | %s | %s |' % (r['comp'], r['layer'],
                                                  STATE_CN[r['state']], r['evidence']))
    L.append('')
    L.append('> **口径提醒**：`只有性质/接口测试` 是"关键词初筛 ＋ 结构判据"的结果，**不是终判**——')
    L.append('> 换一种写法就可能认不出来（本表第一版就因为词表没对上语料，把一批有独立路的件误判进来，')
    L.append('> 校准后从 26 件降到 21 件）。所以每一件都留了**人工确认位**（登记表在测试文件里）。')
    L.append('')
    return '\n'.join(L) + '\n'


def main(argv):
    rows, problems = audit()
    text = render(rows)
    if '--write' in argv:
        io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
        print('已写出 %s（%d 件构件）' % (os.path.relpath(OUT, _REPO), len(rows)))
        for p in problems:
            print('  ⚠️ ' + p)
        return 0
    if '--check' in argv:
        if problems:
            print('❌ 登记与文件脱钩（先修这个）：')
            for p in problems:
                print('   ' + p)
            return 1
        if not os.path.exists(OUT):
            print('缺产物：%s（跑 --write）' % OUT)
            return 1
        cur = io.open(OUT, encoding='utf-8').read()
        if cur != text:
            print('❌ 验证方登记与现状不一致（产物被手改，或构件/测试变了）——跑 --write 更新')
            return 1
        print('验证方登记一致')
        return 0
    cnt = {s: sum(1 for r in rows if r['state'] == s) for s in STATE_ORDER}
    print('验证方登记（总 %d 件）' % len(rows))
    for s in STATE_ORDER:
        print('  %-14s %d' % (STATE_CN[s], cnt[s]))
    print('  只自证/没测的（要登记签字）：')
    for r in rows:
        if r['state'] in ('property_only', 'untested'):
            print('    - %-24s %s' % (r['comp'], r['evidence']))
    return 0


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印中文/emoji 会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main(sys.argv[1:]))
