# -*- coding: utf-8 -*-
"""test_measure_crosscheck.py — 悖论测度 μ 的**按定义直算**验证（③ 验证轴 · 第十批之一）

`paradox_measure` 原本只有"用例集"（期望值写死的几条），本文件补**独立验证方**：
四分支的公式都在模块文档里写明，这里照着公式**自己算一遍**再比。

    mu1 证据权重型：μ = 1 − |wA−wNotA| / (wA + wNotA + ε)
    mu2 自指型   ：μ = 1
    mu3 层级型   ：μ = |tau_L1 − tau_L2|
    mu4 熵权型   ：p = wA/(wA+wNotA+ε)，μ = H(p)/log2，H = −p·log2p − (1−p)·log2(1−p)

另钉三条：
    · **路由优先级** mu2 > mu3 > mu4 > mu1（`choose_branch` 是纯函数，8 种组合全枚举）；
    · **P8 边界**（模块 docstring 记着 EPS/TOL 修复）：p→1 时 μ→0，不许残留 ~1e-8 噪声；
    · **μ ∈ [0,1] 不变式**（随机网格）。

运行：python engine/mechanisms/test_measure_crosscheck.py
"""
import itertools
import math
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import paradox_measure as PM   # noqa: E402

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


EPS = 1e-9          # 模块里声明的 ε


def mu1_def(wA, wNotA):
    return 1.0 - abs(wA - wNotA) / (wA + wNotA + EPS)


def mu4_def(wA, wNotA):
    p = wA / (wA + wNotA + EPS)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return (-(p * math.log2(p)) - (1 - p) * math.log2(1 - p))


def run(**kw):
    return PM.run(dict(kw))


print('=' * 70)
print('一、mu1 证据权重型：μ = 1 − |wA−wNotA|/(wA+wNotA+ε)')
_mis1 = []
for wA, wNotA in [(0, 0), (1, 1), (9, 1), (1, 9), (3, 7), (0, 5), (5, 0),
                  (2.5, 7.5)]:
    got = run(mode='mu1', wA=wA, wNotA=wNotA)['mu']
    want = mu1_def(wA, wNotA)
    if abs(got - want) > 1e-6:
        _mis1.append((wA, wNotA, got, want))
check('mu1 在八个权重点上与定义逐点一致', _mis1 == [], _mis1[:2])
check('mu1 边界：两边无证据（0,0）→ μ=1（不可判定也算完全悖论）',
      abs(run(mode='mu1', wA=0, wNotA=0)['mu'] - 1.0) < 1e-6)
check('mu1 对称性：交换 wA/wNotA 结果不变',
      abs(run(mode='mu1', wA=9, wNotA=1)['mu']
          - run(mode='mu1', wA=1, wNotA=9)['mu']) < 1e-9)

print()
print('=' * 70)
print('二、mu2 自指型 → 1；mu3 层级型 → |tau_L1 − tau_L2|')
check('mu2 自指 → μ=1', abs(run(mode='mu2')['mu'] - 1.0) < 1e-12)
_mis3 = []
for t1, t2 in [(0.2, 0.8), (0.5, 0.5), (0.0, 1.0), (0.3, 0.1)]:
    got = run(mode='mu3', tau_L1=t1, tau_L2=t2)['mu']
    if abs(got - abs(t1 - t2)) > 1e-9:
        _mis3.append((t1, t2, got))
check('mu3 在四个层差点上与 |τ1−τ2| 一致', _mis3 == [], _mis3[:2])
check('mu3 缺层参数 → input_pending（不硬算成 0）',
      run(mode='mu3')['verdict'] == 'input_pending')

print()
print('=' * 70)
print('三、mu4 熵权型：p=wA/(Σ+ε)，μ=H(p)/log2')
_mis4 = []
for wA, wNotA in [(1, 1), (9, 1), (1, 9), (5, 1), (1, 5)]:
    got = run(mode='mu4', wA=wA, wNotA=wNotA)['mu']
    want = mu4_def(wA, wNotA)
    if abs(got - want) > 1e-6:
        _mis4.append((wA, wNotA, got, want))
check('mu4 在五个权重点上与 H(p)/log2 逐点一致', _mis4 == [], _mis4[:2])
check('mu4 最大熵：p=0.5（wA=wNotA=5）→ μ=1',
      abs(run(mode='mu4', wA=5, wNotA=5)['mu'] - 1.0) < 1e-6)
_p8 = run(mode='mu4', wA=5, wNotA=1e-9)['mu']
check('P8 边界：p→1（wA=5, wNotA=1e-9）→ μ≈0（不许残留 ~1e-8 噪声）',
      abs(_p8) < 1e-6, _p8)
check('mu4 对照：p→0（wA=1e-9, wNotA=5）同样 → 0（对称）',
      abs(run(mode='mu4', wA=1e-9, wNotA=5)['mu']) < 1e-6)

print()
print('=' * 70)
print('四、路由优先级 mu2 > mu3 > mu4 > mu1（8 种组合全枚举）')
_mis_r = []
for self_ref, layers, entropy in itertools.product((False, True), repeat=3):
    want = ('mu2' if self_ref else 'mu3' if layers else
            'mu4' if entropy else 'mu1')
    got = PM.choose_branch(is_self_ref=self_ref, has_layers=layers,
                           need_entropy=entropy)
    if got != want:
        _mis_r.append((self_ref, layers, entropy, got, want))
check('choose_branch 的 8 种组合与优先级定义全一致', _mis_r == [], _mis_r[:2])

print()
print('=' * 70)
print('五、不变式与 ④ 契约')
_rng = random.Random(20261003)
_bad_range = []
for _ in range(40):
    wA, wNotA = _rng.uniform(0, 10), _rng.uniform(0, 10)
    for mode in ('mu1', 'mu4'):
        mu = run(mode=mode, wA=wA, wNotA=wNotA)['mu']
        if not (0.0 - 1e-9 <= mu <= 1.0 + 1e-9):
            _bad_range.append((mode, wA, wNotA, mu))
check('μ ∈ [0,1]（随机 40 点 × mu1/mu4 都成立）', _bad_range == [],
      _bad_range[:2])
_ports_in = PM.PORTS['in']
_missing = [k for k in ('tau_L1', 'tau_L2') if k not in _ports_in]
check('PORTS.in 声明了 mu3 真正需要的 tau_L1/tau_L2'
      '（旧版只写 mode/wA/wNotA——对外声明不全）', _missing == [], _missing)
check('每个返回点都带 boundary 与 verdict',
      all(run(mode=m)['boundary'] and run(mode=m)['verdict']
          for m in ('mu1', 'mu2', 'mu3', 'mu4')))

print()
print('=' * 70)
print(f'结果: {PASS}/14 通过')
raise SystemExit(0 if PASS == 14 else 1)
