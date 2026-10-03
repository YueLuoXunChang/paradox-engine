# -*- coding: utf-8 -*-
"""硬核度体检：把"判据够不够硬"变成可跑的检查。

第一条硬规矩（① 判据轴）：
    每个数值阈值常数，**要么被测试钉住边界，要么声明它不是判据**。
    - 钉住＝该常数的名字在对应测试文件里出现（说明有人真的动过这个值去看行为）；
    - 声明＝定义行附近写着"参数 / 约定 / 默认 / 不是体系结论 / 启发式 / 护栏"之一
      （参数＝可调默认值；护栏＝内部兜底，不作判据阈值）。
    两者都没有 → 硬错。理由：阈值没被钉过的构件，判据其实只是"我写了一个数"，
    换个数会不会变结论，没人知道——那正是"启发式冒充判据"。

其余三条轴只**报数**（不判错），当作后续批次的靶子：
    ② 算法：有嵌套循环但没有任何上限/复杂度声明；
    ③ 验证：测试里有没有随机对拍 / 独立互验 / 变异接受；
    ④ 契约：PORTS 与 boundary 的覆盖缺口。

用法：
    python -B engine/_rigor_audit.py --check      # 体检（有硬错就退出码 1）
    python -B engine/_rigor_audit.py --write      # 同时写出 docs/rigor_audit.md
    python -B engine/_rigor_audit.py --json       # 机器可读
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, 'docs')
REPORT = os.path.join(DOCS, 'rigor_audit.md')

PORTS = {
    'in': {'mode': 'str?'},
    'out': {'verdict': 'str', 'detail': 'dict', 'boundary': 'str'},
}

BOUNDARY = (
    '本件只做**静态体检**：数阈值、数覆盖、数验证手段，不执行被测构件、不判对错。'
    '阈值那条是**硬错**（没被钉住或声明就是没钉住）；其余三条轴只报数，'
    '因为"该用什么验证手段"要按构件性质定，不由本件替它决定。'
)

# 阈值型常数：全大写名 + 数字（含小数）
THRESHOLD_RE = re.compile(
    r'^(\s*)([A-Z][A-Z0-9_]{2,})\s*=\s*(-?\d+(?:\.\d+)?)\b', re.M)
# 允许的"这个数不是判据"声明词：参数（可调默认值）· 护栏（内部兜底，不作判据阈值）
PARAM_WORDS = ('参数', '约定', '默认', '不是体系结论', '启发式', '近似', '护栏')
# 上限/复杂度声明的迹象
BOUND_WORDS = ('O(', '复杂度', '上限', '不硬跑', 'MAX', 'LIMIT', 'CAP', '步数')
RAND_WORDS = ('random', 'shuffle', 'seed', 'Random')
INDEP_WORDS = ('外部', '独立复算', '另一实现', '第三方', '对拍', '交叉')
MUT_WORDS = ('变异', 'mutant', '改坏')

# 语料/场景类构件：它们的"阈值"多是样本统计口径，按约定单独列出但仍要钉或声明
LAYERS = ('ai', 'classical', 'cold', 'control', 'engine', 'mechanisms',
          'scenarios', 'skeleton')


def _read(path):
    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except (IOError, UnicodeDecodeError):
        return ''


def components():
    """全仓构件清单（engine 各层的 .py）。

    跳过两类：下划线开头的检查脚本（本件这类）、`test_*.py`（它们自己的
    计数器 `PASS` / `TOTAL` 也是全大写常数，会被误当阈值——第一版就是这么错的）。
    """
    out = []
    for layer in LAYERS:
        d = os.path.join(HERE, layer)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.py'):
                continue
            if f.startswith('_') or f.startswith('test_'):
                continue
            out.append(os.path.join(d, f))
    return out


def test_file_of(name):
    for root, _dirs, files in os.walk(HERE):
        for f in files:
            if f == 'test_%s.py' % name:
                return os.path.join(root, f)
    return None


def classify_threshold(cname, ctx, test_src):
    """一个阈值算不算"钉住了"——三态，是本件唯一的判据，单独拎出来可测。

    - 'pinned'：测试文件里**按词边界**点到这个常量名（说明有人真的动过它看行为）；
      用词边界而不是子串：`MAX_A` 不该被 `MAX_ABC` 蒙过去。
    - 'declared'：定义行附近写明它不是判据（参数 / 护栏 / 约定 / 默认 …）。
    - 'loose'：两者都没有——硬错。
    """
    if re.search(r'\b%s\b' % re.escape(cname), test_src or ''):
        return 'pinned'
    if any(w in ctx for w in PARAM_WORDS):
        return 'declared'
    return 'loose'


def thresholds_of(src):
    """返回 [(常数名, 行号, 该行附近的原文)]。"""
    out = []
    lines = src.split('\n')
    for m in THRESHOLD_RE.finditer(src):
        name = m.group(2)
        line_no = src[:m.start()].count('\n')
        ctx = '\n'.join(lines[max(0, line_no - 1):line_no + 2])
        out.append((name, line_no + 1, ctx))
    return out


def audit():
    """返回 (rows, problems)。problems 里只有 ① 轴的硬错。"""
    rows, problems = [], []
    for comp in components():
        name = os.path.basename(comp)[:-3]
        layer = os.path.basename(os.path.dirname(comp)) or 'engine'
        src = _read(comp)
        tf = test_file_of(name)
        tsrc = _read(tf) if tf else ''
        row = {
            'comp': name, 'layer': layer, 'has_ports': 'PORTS' in src,
            'n_return': len(re.findall(r'\breturn\b', src)),
            'n_boundary': len(re.findall(r"'boundary'|\"boundary\"", src)),
            'thr_pinned': [], 'thr_declared': [], 'thr_loose': [],
            'rand': any(w in tsrc for w in RAND_WORDS),
            'indep': any(w in tsrc for w in INDEP_WORDS),
            'mut': any(w in tsrc for w in MUT_WORDS),
            'has_test': bool(tf),
        }
        for cname, line_no, ctx in thresholds_of(src):
            verdict = classify_threshold(cname, ctx, tsrc)
            if verdict == 'pinned':
                row['thr_pinned'].append(cname)
            elif verdict == 'declared':
                row['thr_declared'].append(cname)
            else:
                row['thr_loose'].append(cname)
                problems.append(
                    '%s：阈值 %s（第 %d 行）既没被测试钉住，也没声明不是判据'
                    % (name, cname, line_no))
        if not row['has_ports']:
            row['ports_gap'] = True
        if row['n_boundary'] == 0:
            row['bnd_gap'] = True
        rows.append(row)
    return rows, problems


def registry_weak():
    """③ 验证轴的**权威口径**：读验证方登记（`engine/_verifier_audit.py`）。

    为什么不在这儿自己扫关键词：同一件事两把尺子，数一定对不上——
    本件第一版就是关键词扫描报 35 件，而登记（AST 扫 import ＋ 人工签字的外部验证方）
    报 23 件。**两个数并存等于没有口径**，所以这里直接读登记，关键词扫描降级成旁证。

    返回 {'weak': [...], 'breakdown': {...}, 'source': '...'}；读不到就如实返回空并标原因。
    """
    import importlib.util
    p = os.path.join(HERE, '_verifier_audit.py')
    try:
        sp = importlib.util.spec_from_file_location('_va_for_rigor', p)
        va = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(va)
        rows, _problems = va.audit()
    except Exception as exc:  # noqa: BLE001——登记本身坏了要如实说，不能假装没这回事
        return {'weak': [], 'breakdown': {'property_only': 0, 'untested': 0,
                                          'error': str(exc)[:60]},
                'source': '读登记失败：%s' % str(exc)[:60]}
    weak, bd = [], {}
    for r in rows:
        if r['state'] in ('property_only', 'untested'):
            weak.append(r['comp'])
            bd[r['state']] = bd.get(r['state'], 0) + 1
    bd.setdefault('property_only', 0)
    bd.setdefault('untested', 0)
    return {'weak': sorted(weak), 'breakdown': bd,
            'source': '验证方登记 engine/_verifier_audit.py（AST 扫 import ＋ 人工签字）'}


def stats(rows):
    """其余三条轴的统计（只报数）。"""
    nested_free = []
    for r in rows:
        src = _read(os.path.join(HERE, r['layer'], '%s.py' % r['comp']))
        nested = len(re.findall(r'for .*:\n(?:.*\n){0,12}?\s+for ', src))
        if nested and not any(w in src for w in BOUND_WORDS):
            nested_free.append(r['comp'])
    weak = [r['comp'] for r in rows
            if not (r['rand'] or r['indep'] or r['mut'])]
    reg = registry_weak()
    return {
        'n_components': len(rows),
        'ports_gap': [r['comp'] for r in rows if r.get('ports_gap')],
        'boundary_gap': [r['comp'] for r in rows if r.get('bnd_gap')],
        'no_test': [r['comp'] for r in rows if not r['has_test']],
        'thr_loose': {r['comp']: r['thr_loose'] for r in rows if r['thr_loose']},
        'thr_pinned_n': sum(len(r['thr_pinned']) for r in rows),
        'thr_declared_n': sum(len(r['thr_declared']) for r in rows),
        'nested_no_bound': nested_free,
        # ③ 轴**以验证方登记为准**（AST 口径）；关键词扫描降级成"旁证"，不参与口径
        'weak_verification': reg['weak'],
        'weak_breakdown': reg['breakdown'],
        'weak_source': reg['source'],
        'supplementary': {'rand': [r['comp'] for r in rows if r['rand']],
                          'indep': [r['comp'] for r in rows if r['indep']],
                          'mut': [r['comp'] for r in rows if r['mut']],
                          'keyword_weak': weak},
    }


def render(rows, problems, st):
    L = []
    L.append('# 硬核度体检报告')
    L.append('')
    L.append('> 本文件由 `engine/_rigor_audit.py --write` 生成，**不要手改**。')
    L.append('> 口径：① 判据＝阈值必须被测试钉住或声明为参数（硬错）；'
             '②③④ 只报数，不判错。')
    L.append('')
    L.append('## 一、① 判据轴（阈值钉边界）')
    L.append('')
    L.append('- 阈值被测试钉住 %d 个 · 声明为参数 %d 个 · **未钉未声明 %d 个**'
             % (st['thr_pinned_n'], st['thr_declared_n'], len(problems)))
    if problems:
        L.append('')
        for p in problems:
            L.append('- ❌ %s' % p)
    L.append('')
    L.append('## 二、② 算法轴（有嵌套循环、无上限或复杂度声明）')
    L.append('')
    L.append('共 **%d** 件：%s' % (len(st['nested_no_bound']),
                                   '、'.join(st['nested_no_bound']) or '无'))
    L.append('')
    L.append('## 三、③ 验证轴（口径：**验证方登记**，不是本件自己扫的）')
    L.append('')
    L.append('- 口径来源：%s' % st['weak_source'])
    L.append('- 处于"未验状态"的构件 **%d** 件（只有性质·接口测试 %d 件 ＋ 无测试引用 %d 件）：'
             % (len(st['weak_verification']),
                st['weak_breakdown'].get('property_only', 0),
                st['weak_breakdown'].get('untested', 0)))
    L.append('')
    L.append('```')
    for i in range(0, len(st['weak_verification']), 6):
        L.append('、'.join(st['weak_verification'][i:i + 6]))
    L.append('```')
    L.append('')
    sup = st['supplementary']
    L.append('**旁证**（关键词扫描，**不参与口径**，只作参考）：'
             '随机对拍 %d 件 · 独立互验字样 %d 件 · 变异字样 %d 件；'
             '三样都扫不到的是 %d 件——**与上面那个数不同是正常的**，'
             '差异来自判据不同（关键词 vs AST），以登记为准。'
             % (len(sup['rand']), len(sup['indep']), len(sup['mut']),
                len(sup['keyword_weak'])))
    L.append('')
    L.append('## 四、④ 契约轴（PORTS / boundary 缺口）')
    L.append('')
    L.append('- 没有 PORTS：**%s**' % ('、'.join(st['ports_gap']) or '无'))
    L.append('- 返回里没有 boundary：**%s**' % ('、'.join(st['boundary_gap']) or '无'))
    L.append('- 没有测试文件：**%s**' % ('、'.join(st['no_test']) or '无'))
    L.append('')
    L.append('## 五、边界')
    L.append('')
    L.append(BOUNDARY)
    L.append('')
    L.append('> 更正记录：第一版把"模块里写过参数/约定这类词"当作已声明，'
             '结果 11 件阈值全部"看起来合规"——太松。改成"阈值名必须出现在测试里，'
             '或定义行附近写明是参数"，才量出真实缺口。')
    return '\n'.join(L) + '\n'


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass
    mode = argv[1] if len(argv) > 1 else '--check'
    rows, problems = audit()
    st = stats(rows)
    if mode == '--json':
        print(json.dumps({'problems': problems, 'stats': st},
                         ensure_ascii=False, indent=2))
        return 0
    if mode == '--write':
        os.makedirs(DOCS, exist_ok=True)
        with io.open(REPORT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(render(rows, problems, st))
        print('已写出：%s' % os.path.relpath(REPORT, REPO))
    print('① 判据：阈值钉住 %d · 声明为参数 %d · 未钉未声明 %d'
          % (st['thr_pinned_n'], st['thr_declared_n'], len(problems)))
    print('② 算法：嵌套循环无上限声明 %d 件' % len(st['nested_no_bound']))
    print('③ 验证：未验状态 %d 件（口径＝验证方登记）' % len(st['weak_verification']))
    print('④ 契约：缺 PORTS %d 件 · 缺 boundary %d 件'
          % (len(st['ports_gap']), len(st['boundary_gap'])))
    if problems:
        print('')
        print('❌ 硬核度体检没过（%d 条）：' % len(problems))
        for p in problems:
            print('   %s' % p)
        return 1
    print('')
    print('✅ 硬核度体检通过（① 轴无硬错）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
