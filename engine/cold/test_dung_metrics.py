# -*- coding: utf-8 -*-
"""test_dung_metrics.py — 论辩框架的**标准图量**验证（② 算法轴 · 标准量）

为什么补这两个量：`dung_framework` 原只给 grounded/preferred/stable——读者**分不出**
"某个论证进 grounded 是因为它真争出了位置，还是因为根本没人攻击它"。
两个标准量正好补这个盲区，而且都是**线性算法**（O(n+m)）：

    · `components`：把攻击边当**无向边**连出来的**连通分量**——
      诊断意义：这场辩论其实分成几个互不相干的群（互不影响的子辩论）；
    · `degree_centrality`：每个论证的出入度之和 `degree` 与归一化 `degree/(n−1)`——
      读作「争议中心」（被围攻或到处开战的那个）。

本文件在**已知图**上验数值（路径图 / 两个不连通对 / 完全图 K3 / 单点 /
自环 / 星形），并断言**语义输出没被这两量影响**（加的是诊断，不是改判）。

运行：python engine/cold/test_dung_metrics.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.cold import dung_framework as D   # noqa: E402

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


def run(args, attacks):
    return D.run({'arguments': list(args), 'attacks': list(attacks)})


def deg(r):
    return {k: v['degree'] for k, v in r['degree_centrality'].items()}


def cen(r):
    return {k: v['centrality'] for k, v in r['degree_centrality'].items()}


print('=' * 70)
print('一、连通分量：已知图上数群')
_r = run(['A', 'B', 'C'], [('A', 'B'), ('B', 'C')])
check('路径图 A→B→C：一个分量（3 个节点连成一条链）',
      _r['components'] == [['A', 'B', 'C']], _r['components'])
_two = run(['A', 'B', 'C', 'D'], [('A', 'B'), ('C', 'D')])
check('两个互不相干的攻击对：**两个**分量',
      _two['components'] == [['A', 'B'], ['C', 'D']], _two['components'])
_iso = run(['A', 'B', 'C'], [('A', 'B')])
check('孤立节点 C 单独成组（诊断价值就在这：它没参与任何争论）',
      _iso['components'] == [['A', 'B'], ['C']], _iso['components'])
check('分量按**大小降序**再按名字排（可复现）',
      run(['A', 'B', 'C', 'D', 'E'],
          [('A', 'B'), ('B', 'C'), ('D', 'E')])['components']
      == [['A', 'B', 'C'], ['D', 'E']])

print()
print('=' * 70)
print('二、度中心性：已知图上验数值（degree 与 degree/(n−1)）')
check('路径图：中间节点 degree=2、两端=1（入+出）',
      deg(_r) == {'A': 1, 'B': 2, 'C': 1}, deg(_r))
check('路径图（n=3）：centrality = 0.5 / 1.0 / 0.5',
      cen(_r) == {'A': 0.5, 'B': 1.0, 'C': 0.5}, cen(_r))
_k3 = run(['A', 'B', 'C'],
          [('A', 'B'), ('B', 'A'), ('A', 'C'), ('C', 'A'),
           ('B', 'C'), ('C', 'B')])
check('完全图 K3：每个 degree=4（三个对手各双向）→ centrality=2.0?',
      deg(_k3) == {'A': 4, 'B': 4, 'C': 4}, deg(_k3))
_hub = run(['A', 'B', 'C', 'D'],
           [('B', 'A'), ('C', 'A'), ('D', 'A')])
check('星形：被围攻的 A degree=3、其余各 1 → A 的 centrality 最高',
      deg(_hub) == {'A': 3, 'B': 1, 'C': 1, 'D': 1}
      and cen(_hub)['A'] == 1.0, (deg(_hub), cen(_hub)['A']))
check('单论证框架：degree=0、centrality=0.0（n−1=0 不许除零崩）',
      run(['A'], [])['degree_centrality'] == {'A': {'degree': 0,
                                                   'centrality': 0.0}},
      run(['A'], [])['degree_centrality'])
check('自环 A→A：degree=2（自环按图论惯例给两端各 +1）',
      deg(run(['A', 'B'], [('A', 'A')]))['A'] == 2,
      deg(run(['A', 'B'], [('A', 'A')])))

print()
print('=' * 70)
print('三、加的是**诊断**、不是改判：语义输出不许被影响')
_sem = run(['A', 'B', 'C'], [('B', 'A'), ('C', 'B')])
check('grounded/preferred 仍按 Dung 语义给（A←B←C → grounded {A, C}）',
      _sem['grounded'] == ['A', 'C'], _sem['grounded'])
check('早退分支也带两键（PORTS 形状统一，早退不许缺键）',
      run([], [])['components'] == []
      and run([], [])['degree_centrality'] == {})
check('PORTS 声明了这两个量（对外契约）',
      all(k in D.PORTS['out'] for k in ('components', 'degree_centrality')),
      list(D.PORTS['out']))
check('docstring 写了复杂度声明（O(n+m) 线性）与两量的读法',
      'O(n + m)' in (D.__doc__ or '')
      and '连通分量' in (D.__doc__ or ''))

print()
print('=' * 70)
print(f'结果: {PASS}/14 通过')
raise SystemExit(0 if PASS == 14 else 1)
