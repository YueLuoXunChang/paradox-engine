# -*- coding: utf-8 -*-
"""test_converge_check.py — 收敛判定件的正式测试（③ 验证轴 · 第九批之一）

这一件此前**零测试**（登记表"无测试引用"）。本文件按**解析可预测**的例子验，
并且把**入参形状**这条口径一起钉住：

    真实契约（旧版 PORTS 没写清，照它写代码会直接 TypeError）：
        `f(x, e) -> 新 x`   —— **二元**，状态是 (x, e) 一对（e 是"误差方向"）
        `err_fn(x) -> 误差` —— **一元**，到可接受集的距离
    分支返回还各不相同：分支2 给 `reached/finite_steps`、分支3 给
    `decreasing/err_tail`、分支4 给 `q_T/converges`——`run` 负责归一成
    `{verdict, converges, rate, detail, branch, boundary}`，所以判"收敛与否"
    走 `run`，验"解析值"（q_T、步数）走分支函数。

解析预测：
    · 分支2：f(x,e)=0 → 第 1 步进可接受态（**手算**）；
    · 分支3：x/2 误差每步减半 → 渐进；x+1 误差不降 → 非渐进（**手算**）；
    · 分支4：-(1/2)x 每两步压缩 1/4（q_2=0.25）→ 收敛；2x 每两步放大 4 倍 → 不收敛
      （**手算**，解析上 q_T=|a|^T）；
    · Lipschitz：err(t)=2t → 2 · t/2 → 0.5 · sin → 差商下界（≤1）
      —— L 的**定义**就是差商上确界，所以这里是**按定义直算**，不是抄构件的输出。

运行：python engine/mechanisms/test_converge_check.py
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import converge_check as CC   # noqa: E402

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


ERR = abs                       # 一元：err_fn(x) = |x|（到 0 的距离）

print('=' * 70)
print('一、Lipschitz 估计（解析值：err(t)=k·t → L=k；差商是下界）')
check('err(t)=2t 上 L=2', abs(CC.estimate_lipschitz(lambda t: 2 * t,
                                                   [-1.0, 0.0, 1.0, 2.0]) - 2.0)
      < 1e-9, CC.estimate_lipschitz(lambda t: 2 * t, [-1.0, 0.0, 1.0, 2.0]))
check('err(t)=t/2 上 L=0.5（与 2t 形成对照，不是恒返回同一个数）',
      abs(CC.estimate_lipschitz(lambda t: t / 2,
                                [-1.0, 0.0, 1.0, 2.0]) - 0.5) < 1e-9)
_L_sin = CC.estimate_lipschitz(math.sin, [0.0, 0.5, 1.0, 1.4])
check('err(t)=sin(t) 的差商估计落在 (0.9, 1] 内（**下界估计**，不超过解析上确界）',
      0.9 <= _L_sin <= 1.0 + 1e-12, _L_sin)

print()
print('=' * 70)
print('二、分支2 有限步：一步进可接受态')
_r2 = CC.branch2_finite(lambda x, e: 0.0, ERR, 1.0)
check('f(x,e)=0 从 1 出发 → 第 1 步就可达（finite_steps=1）',
      _r2.get('reached') is True and _r2.get('finite_steps') == 1, _r2)

print()
print('=' * 70)
print('三、分支3 渐进：x/2 误差每步减半（解析上几何衰减）')
_r3 = CC.branch3_asymptotic(lambda x, e: x / 2, ERR, 1.0)
check('x/2 → 误差递减 → 渐进收敛', _r3.get('decreasing') is True, _r3)
check('x/2 的末段误差确实极小（<1e-100，几何衰减的解析预期）',
      abs(_r3.get('err_tail', 1.0)) < 1e-100, _r3.get('err_tail'))
_r3b = CC.branch3_asymptotic(lambda x, e: x + 1, ERR, 0.0)
check('对照：x+1 误差不降 → 非渐进收敛', _r3b.get('decreasing') is False, _r3b)

print()
print('=' * 70)
print('四、分支4 振荡：每 T=2 步的压缩比 q_T（解析值）')
_r4 = CC.branch4_oscillation(lambda x, e: -0.5 * x, ERR, 1.0)
check('-(1/2)x：q_2 = 0.25（每两步压缩 1/4）→ 收敛且 q_T 与解析值一致',
      _r4.get('converges') is True and abs(_r4.get('q_T') - 0.25) < 1e-9, _r4)
_r4b = CC.branch4_oscillation(lambda x, e: 2 * x, ERR, 1.0)
check('2x：q_2 = 4（每两步放大 4 倍）→ 不收敛且 q_T 与解析值一致',
      _r4b.get('converges') is False and abs(_r4b.get('q_T') - 4.0) < 1e-9, _r4b)

print()
print('=' * 70)
print('五、分支1 压缩：纯方向样本是 [(x, e), …]；缺样本要诚实报"数据不足"')
_SX = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]      # e 固定 → 纯 x 方向
_SE = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]      # x 固定 → 纯 e 方向
_r1 = CC.branch1_compression(lambda x, e: 0.5 * x, ERR, [1.0, 2.0, 4.0],
                             samples_x=_SX, samples_e=_SE)
check('给了纯方向样本 → 分支1 给出收敛判定（不再是"数据不足"）',
      _r1.get('converges') is True, _r1)
_r1n = CC.branch1_compression(lambda x, e: 0.5 * x, ERR, [1.0, 2.0, 4.0])
check('**缺样本 → 诚实报"数据不足"**（不硬判收敛/发散）',
      _r1n.get('converges') is None, _r1n)

print()
print('=' * 70)
print('六、run 的归一契约（四分支 → {verdict, converges, …}）')
_runs = {b: CC.run({'branch': b, 'f': lambda x, e: x / 2, 'err_fn': ERR,
                    'x0': 1.0}) for b in ('finite', 'asymptotic',
                                          'oscillation')}
check('run 走三分支都归一出 converges 布尔与 verdict',
      all(v.get('converges') in (True, False) and v.get('verdict')
          for v in _runs.values()), {k: v.get('verdict') for k, v in
                                     _runs.items()})
check('run 压缩分支缺样本 → 判词如实说"数据不足"',
      '数据不足' in str(CC.run({'branch': 'compression',
                                'f': lambda x, e: x / 2, 'err_fn': ERR,
                                'x0': 1.0})['verdict']))

print()
print('=' * 70)
print('七、④ 契约：PORTS.in 声明各分支真正需要的入参（含**可调用形状**）')
_ports_in = CC.PORTS['in']
_must = ('branch', 'f', 'err_fn', 'x0', 'samples', 'samples_x', 'samples_e',
         'L_est')
_missing = [k for k in _must if k not in _ports_in]
check('PORTS.in 声明了分支1 真正需要的 samples/samples_x/samples_e/L_est',
      _missing == [], _missing)
check('PORTS.in 写清了可调用**形状**（f 二元、err_fn 一元）——'
      '照旧版只写 callable 会直接 TypeError',
      '二元' in str(_ports_in.get('f')) and '一元' in str(_ports_in.get('err_fn')),
      (_ports_in.get('f'), _ports_in.get('err_fn')))

print()
print('=' * 70)
print(f'结果: {PASS}/15 通过')
raise SystemExit(0 if PASS == 15 else 1)
