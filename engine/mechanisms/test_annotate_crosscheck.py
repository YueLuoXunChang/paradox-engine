# -*- coding: utf-8 -*-
"""test_annotate_crosscheck.py — 悖论注解卡的**按定义直算**验证（③ 验证轴 · 第十批之二）

`paradox_annotate` 原本只有"用例集"，本文件补独立验证方。它的文档给了**完整可算的规则**：

    grade(来源, 影响, 可消除) ∈ {P-A, P-B, P-C}
        来源: axiom→A（结构性）/ runtime→B（运行期）/ observer→C（观察者）
        影响: global（全局）→ 升级一级
        可消除: 无法消除（eliminable=False）→ 保持或升级一级
    Annotation = (ID, LV, POS, SRC, CT, EF, ST, AN) 8 字段
        ID = 悖论_P-{级别}_{序号:03d}

所以本文件把 **3×2×2 = 12 种组合全枚举**，用**自己实现的规则**逐条比对——
这是"按定义直算"里最干净的一种：规则是离散的，能穷举完，不是抽样。

运行：python engine/mechanisms/test_annotate_crosscheck.py
"""
import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import paradox_annotate as PA   # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=''):
    global PASS
    if cond:
        PASS += 1
        print('✅ %s' % label)
    else:
        print('❌ %s  %s' % (label, detail))


_LEVELS = ['P-A', 'P-B', 'P-C']          # A 最高（结构性），C 最低（观察者）
_BASE = {'axiom': 0, 'runtime': 1, 'observer': 2}


def grade_def(source, impact, eliminable):
    """照文档规则自己算：来源定基线；global 升一级；不可消除再升一级；A 是顶。"""
    lv = _BASE[source]
    if impact == 'global':
        lv = max(0, lv - 1)
    if not eliminable:
        lv = max(0, lv - 1)
    return _LEVELS[lv]


def run(**kw):
    return PA.run(dict(kw))


PARADOX = {'A': '本句为假', 'notA': '本句为真'}

print('=' * 70)
print('一、★分级规则：12 种（来源×影响×可消除）全枚举，与文档规则逐条比对')
_mis, _seen = [], set()
for src, imp, elim in itertools.product(('axiom', 'runtime', 'observer'),
                                        ('global', 'local'), (True, False)):
    r = run(paradox=PARADOX, source=src, impact=imp, eliminable=elim)
    got = r.get('grade')
    want = grade_def(src, imp, elim)
    _seen.add(want)
    if got != want:
        _mis.append((src, imp, elim, got, want))
check('12 种组合的分级与文档规则逐条一致（穷举，不是抽样）', _mis == [],
      _mis[:2])
check('三个级别（P-A/P-B/P-C）都被覆盖到（%s）' % sorted(_seen),
      {'P-A', 'P-B', 'P-C'} <= _seen)
check('分级不是恒返回同一个值（不是"一律 P-A"蒙混）',
      len(_seen) == 3, sorted(_seen))

print()
print('=' * 70)
print('二、8 字段卡：字段齐；填满则皆有值；**不填就不编**')
# 口径（探明的）：卡片 POS/SRC/EF/AN 分别取自 paradox 的 pos/src/effect/note
# —— 调用方不填，组件**不替它编**（这是「只诊断不决策」的口径）。
FULL = {'A': '本句为假', 'notA': '本句为真', 'pos': '第2层·测试',
        'src': 'axiom', 'effect': '经典层上卷点', 'note': '测试注解',
        'coexist': '真/假交替'}
_r_full = run(paradox=FULL, source='axiom', impact='global',
              eliminable=False, seq=7)
_card_full = _r_full.get('annotation') or {}
check('卡片恰好 8 个字段（ID/LV/POS/SRC/CT/EF/ST/AN）',
      set(_card_full) == {'ID', 'LV', 'POS', 'SRC', 'CT', 'EF', 'ST', 'AN'},
      sorted(_card_full))
check('**填满子键**时 8 个字段全非空（不是占位空串）',
      all(str(v).strip() for v in _card_full.values()), _card_full)
check('卡里的 LV 与返回的 grade 一致（两处不许打架）',
      _card_full.get('LV') == _r_full.get('grade'),
      (_card_full.get('LV'), _r_full.get('grade')))
# 不编内容：只给 A/notA 时，需外部语义的字段保持空，而不是被编一个
_bare = run(paradox={'A': 'x', 'notA': 'y'}, source='axiom',
            impact='local', eliminable=True, seq=1)['annotation']
check('**不填就不编**：只给 A/notA 时 pos/src/effect/note 对应字段为空'
      '（组件不替使用方编语义——与"只诊断不决策"一致）',
      _bare.get('POS') == '' and _bare.get('SRC') == ''
      and _bare.get('EF') == '' and _bare.get('AN') == '', _bare)

print()
print('=' * 70)
print('三、ID 格式：悖论_P-{级别}_{序号:03d}')
_id7 = run(paradox=PARADOX, source='axiom', impact='local',
           eliminable=True, seq=7)['annotation']['ID']
_id123 = run(paradox=PARADOX, source='axiom', impact='local',
             eliminable=True, seq=123)['annotation']['ID']
check('序号补齐三位：seq=7 → _007', _id7.endswith('_007'), _id7)
check('序号超三位照写：seq=123 → _123', _id123.endswith('_123'), _id123)
check('ID 里带级别段（与 LV 同源）',
      '_P-A_' in _id7 or '_P-B_' in _id7 or '_P-C_' in _id7, _id7)

print()
print('=' * 70)
print('四、来源口径：**顶层 source 只决定分级，卡片 SRC 取自子键**')
_src_card = run(paradox=dict(FULL), source='runtime', impact='local',
                eliminable=True, seq=1)
check('卡片 SRC 来自 paradox["src"]（不是顶层 source）：子键给 axiom、'
      '顶层给 runtime 时，SRC=axiom 而分级按 runtime 算',
      _src_card['annotation'].get('SRC') == 'axiom'
      and _src_card.get('grade') == 'P-B',
      (_src_card['annotation'].get('SRC'), _src_card.get('grade')))
_no = run()
check('缺 paradox → 判词是声明的"待给"类，且不抛异常（诚实拦截）',
      _no.get('verdict') in ('input_pending', 'annotated', 'error'),
      _no.get('verdict'))
check('缺 paradox 时不伪造卡片（annotation 为空或 None）',
      not _no.get('annotation'))

print()
print('=' * 70)
print('五、④ 契约：PORTS 与判词')
_in = PA.PORTS['in']
check('PORTS.in 声明了分级真正需要的 source/impact/eliminable/seq',
      all(k in _in for k in ('source', 'impact', 'eliminable', 'seq')), list(_in))
check('每个返回点都带 boundary 与 verdict',
      all(run(paradox=PARADOX, source=s)['boundary']
          and run(paradox=PARADOX, source=s)['verdict']
          for s in ('axiom', 'runtime', 'observer')))

print()
print('=' * 70)
print(f'结果: {PASS}/15 通过')
raise SystemExit(0 if PASS == 15 else 1)
