# -*- coding: utf-8 -*-
"""test_boundary_crosscheck.py — 边界悖论的**解析验证**（③ 验证轴 · 第十一批之一）

`boundary_paradox` 把"墙"当**边界对象**诊断。它的核心量 tension 实测是**三态规则**：

    inside 与 outside 都给且相等 → 0.0（边界根本没划出对立）
    两边都给且不等            → 1.0（对立成立，张力满）
    只给一边 / 都不给          → 0.5（信息不足，取中——**不是** 0 也不是 1）

外加公理级断言：有墙时 `self_undermining=True`（划设即撤销）、`removable=True`
（框架层可换）、`advice` 给 5 条不重复的操作建议（**诊断不执行**）。

验证方式：tension 的三态规则从输入/输出关系归纳出来，再取五个点位**逐条核**；
公理级断言（自削弱/可撤/建议条数）是照着它的边界声明**手算**出该成立什么再比对
——不是把构件输出抄进期望值。

运行：python engine/mechanisms/test_boundary_crosscheck.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import boundary_paradox as BP   # noqa: E402

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


def run(**kw):
    return BP.run(dict(kw))


print('=' * 70)
print('一、tension 三态规则（两边相等/不等/缺一边）')
_grid = [
    ({'wall_name': 'W', 'inside': 'x', 'outside': 'x'}, 0.0, '两边相等'),
    ({'wall_name': 'W', 'inside': 'x', 'outside': 'y'}, 1.0, '两边不等'),
    ({'wall_name': 'W', 'inside': 'x'}, 0.5, '只给 inside'),
    ({'wall_name': 'W', 'outside': 'y'}, 0.5, '只给 outside'),
    ({'wall_name': 'W'}, 0.5, '两边都没给'),
]
_bad = []
for _inp, _want, _tag in _grid:
    _got = run(**_inp).get('tension')
    if _got is None or abs(_got - _want) > 1e-9:
        _bad.append((_tag, _got, _want))
check('tension 在五点上与三态规则一致', _bad == [], _bad[:2])
check('tension ∈ [0,1] 恒成立（五个点全检查）',
      all(0.0 <= run(**_inp).get('tension') <= 1.0 for _inp, _w, _t in _grid))

print()
print('=' * 70)
print('二、公理级断言：有墙 → 自削弱 + 可撤（"划设即撤销"）')
_r = run(wall_name='扩容悖论', inside='修路', outside='不修路')
check('有墙 → verdict=wall_exists',
      _r['verdict'] == 'wall_exists', _r['verdict'])
check('self_undermining=True（划设本身预设了可撤销）',
      _r['self_undermining'] is True)
check('removable=True（可撤 = 框架层可换，**不是**"图灵可判"）',
      _r['removable'] is True and '图灵' in _r['boundary'])
_adv = _r.get('advice') or []
check('advice 给 5 条操作建议且互不重复（划设/维护/检测/撤销/重生这一类）',
      len(_adv) == 5 and len(set(_adv)) == 5, _adv)
check('advice 是**诊断建议**不是执行动作（边界里写明只诊断不决策）',
      '诊断' in _r['boundary'] or '不决策' in _r['boundary'])

print()
print('=' * 70)
print('三、输入口径与 ④ 契约')
check('只给 domain 不给 wall → input_pending（诚实：没有墙可诊断）',
      run(domain='D', inside='x')['verdict'] == 'input_pending')
check('input_pending 时不出半截结果（tension/advice 为空）',
      run(domain='D')['tension'] is None and not run(domain='D')['advice'])
check('不认识 mode → 仍有声明判词（不崩）',
      run(mode='zzz', wall_name='W', inside='x')['verdict']
      in ('wall_exists', 'input_pending', 'mode_pending', 'parse_error'))
check('PORTS 声明了六个入参（wall_name/domain/inside/outside/'
      'recursive_layer/mode）',
      all(k in BP.PORTS['in'] for k in
          ('wall_name', 'domain', 'inside', 'outside', 'recursive_layer',
           'mode')), list(BP.PORTS['in']))
check('每个返回点都带 boundary 与 verdict',
      all(run(**i)['boundary'] and run(**i)['verdict'] for i, _w, _t in _grid))

print()
print('=' * 70)
print(f'结果: {PASS}/12 通过')
raise SystemExit(0 if PASS == 12 else 1)
