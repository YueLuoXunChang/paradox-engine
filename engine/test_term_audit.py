# -*- coding: utf-8 -*-
"""test_term_audit.py — ④ 轴撞名登记的正式测试

锁三件事：
    ① 撞名登记册与实测一致（重算 = 已写出的那份，不漂移）；
    ② **不同型撞名全部有判定**（没判定就是错——这是 ④ 轴的硬要求）；
    ③ 判定表**不许有幽灵条目**（给一个不存在的名字写判定 = 记账作假），
       并且"同型但不同物"的（如 `components`）必须靠判定表兜住——类型检查看不出来。
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine import _term_audit as T   # noqa: E402

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


rows, problems = T.audit()
names = {r['name'] for r in rows}

print('=' * 70)
print('一、登记册与实测一致（不漂移）')
check('撞名数 >= 20（防扫描退化成空）', len(rows) >= 20, len(rows))
check('撞名定义成立：每个名字都真出现在 >= 2 件里',
      all(r['n'] >= 2 for r in rows), [r['name'] for r in rows if r['n'] < 2])
_md = T.render(rows, problems)
_on_disk = io.open(T.OUT, encoding='utf-8').read()
check('docs/term_collisions.md 与重算结果**逐字一致**（没漂移）',
      _on_disk == _md, '字数 盘=%d 算=%d' % (len(_on_disk), len(_md)))

print()
print('=' * 70)
print('二、④ 轴硬要求：不同型撞名全部有判定')
check('未判定的不同型撞名 = 0 个', problems == [], problems)
_mixed = [r for r in rows if r['mixed']]
check('不同型撞名被登记（>= 5 个）', len(_mixed) >= 5, len(_mixed))
check('每个不同型撞名都有判定条目',
      all(r['judgment'] is not None for r in _mixed),
      [r['name'] for r in _mixed if r['judgment'] is None])

print()
print('=' * 70)
print('三、判定表不许有幽灵条目；同型不同物靠判定兜住')
_ghost = set(T.JUDGMENTS) - names
check('判定表里的名字**都是**实际撞名（幽灵条目 = 记账作假）',
      _ghost == set(), _ghost)
_comp = [r for r in rows if r['name'] == 'components']
check('`components` 同型（都是 list）但已判定为**同名不同物**'
      '（类型检查抓不到，靠判定表）',
      bool(_comp) and _comp[0]['mixed'] is False
      and _comp[0]['judgment'] is not None
      and _comp[0]['judgment'][0] is False,
      _comp[0] if _comp else '缺')
_rev = [r for r in rows if r['name'] == 'review']
check('`review` 不同型（dict vs str）且已判定为不同物',
      bool(_rev) and _rev[0]['mixed'] is True
      and _rev[0]['judgment'] is not None
      and _rev[0]['judgment'][0] is False, _rev[0] if _rev else '缺')

print()
print('=' * 70)
print('四、明细可回溯')
_band = [r for r in rows if r['name'] == 'branch']
check('`branch` 命中 converge_check 与 paradox_measure 两件（命名空间撞车）',
      bool(_band) and {e[1] for e in _band[0]['entries']}
      == {'converge_check', 'paradox_measure'},
      _band[0]['entries'] if _band else '缺')
check('每条登记都带 层/件/声明原文/基类型 四项',
      all(len(e) == 4 and all(e) for r in rows for e in r['entries']))

print()
print('=' * 70)
print(f'结果: {PASS}/11 通过')
raise SystemExit(0 if PASS == 11 else 1)
