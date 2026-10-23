# -*- coding: utf-8 -*-
"""test_bypass_crosscheck.py — 全程自反旁路的**解析验证**（③ 验证轴 · 第十一批之二）

`observer_bypass` 的核心主张是**架构级**的："主线程不因矛盾停下，悖论注解随行"。
这句话可以被精确验证，因为：

    · `main_ran` 必须 == 事件条数（**不管命中多少矛盾**）——这就是"主链不停"；
    · `findings` 必须**恰好**是我给的 `detect` 命中的那些位点（**不自己编检测**）；
    · `injected_at` 必须 == `[f['at'] for f in findings]`（注入点在检测点之后，白箱可见）；
    · 每条 finding 带**注解卡**（复用 paradox_annotate 的 8 字段卡）。

本文件自己写 `detect`（按文本里的 `¬A` / `矛盾` 判定），于是"命中集合"是我算出来的，
不是从构件输出里抄的。

**契约口径**（旧版 PORTS 只写 `callable?`，实测踩过）：`detect(event) -> dict | None`
—— 返回 **dict 视为命中**（会取 `f.get('type')`），返回 `None`/假值视为未命中；
**返回 bool 会直接 AttributeError**。

验证方式：**对拍**——我自己写 `detect` 并**自己算出**命中下标集合，
再与构件的 `findings`/`injected_at` 逐条比对；`main_ran == 事件数` 是
照它"主链不停"的架构声明**手算**出来的应然值。

运行：python engine/mechanisms/test_bypass_crosscheck.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.mechanisms import observer_bypass as OB   # noqa: E402

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


def my_detect(ev):
    """我自己的检测器：文本含 ¬A 或"矛盾" → 命中（返回 dict，不是 bool）。"""
    txt = str(ev.get('text', ''))
    return {'type': 'contradiction'} if ('¬A' in txt or '矛盾' in txt) else None


EV = [{'id': 1, 'text': 'A 与 ¬A 共存'}, {'id': 2, 'text': '普通'},
      {'id': 3, 'text': '出现矛盾'}, {'id': 4, 'text': '普通'}]
WANT_AT = [0, 2]          # 我自己算的命中下标（第 1、3 条）

print('=' * 70)
print('一、★主链不停：main_ran == 事件条数（不管命中多少矛盾）')
_bad_main = []
for _n in (1, 2, 4, 7):
    _ev = [{'id': i, 'text': 'A 与 ¬A' if i % 2 else '普通'} for i in range(_n)]
    _got = OB.run({'main_events': _ev, 'detect': my_detect})['main_ran']
    if _got != _n:
        _bad_main.append((_n, _got))
check('main_ran 在 1/2/4/7 条事件上都等于条数（含全命中与半命中）',
      _bad_main == [], _bad_main[:2])
_r = OB.run({'main_events': EV, 'detect': my_detect})
check('矛盾命中 2 条时主链仍然跑完（4 条全跑）', _r['main_ran'] == 4, _r['main_ran'])

print()
print('=' * 70)
print('二、findings 恰好是**我算出的**命中位点（不自己编检测）')
check('findings 的位点 == [0, 2]（与我的 detect 逐条一致）',
      [f['at'] for f in _r['findings']] == WANT_AT,
      [f['at'] for f in _r['findings']])
check('每条 finding 的 type 来自我的 detect 返回（contradiction）',
      all(f.get('type') == 'contradiction' for f in _r['findings']))
check('finding 里带着被命中事件的原文（白箱：能对上）',
      all(f.get('event') == EV[f['at']] for f in _r['findings']))
# 不传 detect 时组件有**内置关键词启发检测**——关键是它**如实标注了这是启发式**
_nodef = OB.run({'main_events': EV})
check('不传 detect → 走内置**关键词启发**检测，且卡片明说"启发式/非完备"'
      '（① 轴：启发式必须标注，不许冒充完备检测）',
      any('启发' in str((f.get('annotation') or {}).get('AN', ''))
          for f in _nodef['findings']), _nodef['findings'])
_no_hit = OB.run({'main_events': [{'id': 9, 'text': '全是普通陈述'}],
                  'detect': my_detect})
check('零命中时 findings 为空但主链照跑（main_ran=1）',
      _no_hit['findings'] == [] and _no_hit['main_ran'] == 1)

print()
print('=' * 70)
print('三、注入点与注解卡')
check('injected_at == [f["at"] for f in findings]（注入在检测点之后）',
      _r['injected_at'] == [f['at'] for f in _r['findings']], _r['injected_at'])
_cards = [f.get('annotation') or {} for f in _r['findings']]
check('每条 finding 都带注解卡，且是**6 字段**轻量卡'
      '（A/notA/LV/SRC/ST/AN——比 paradox_annotate 的 8 字段卡少 ID/POS）',
      all(set(c) == {'A', 'notA', 'LV', 'SRC', 'ST', 'AN'} for c in _cards),
      [sorted(c) for c in _cards][:1])
check('注解卡的关键字段非空（LV/A 有值——卡不是空壳；notA/AN 可空：'
      '取决于检测器给不给否定式与说明）',
      all(c.get('LV') and c.get('A') for c in _cards),
      _cards[0] if _cards else None)
check('verdict=observed（有事件可观察）', _r['verdict'] == 'observed',
      _r['verdict'])

print()
print('=' * 70)
print('四、边界与 ④ 契约')
check('空事件 → input_pending（没东西可观察，诚实）',
      OB.run({'main_events': []})['verdict'] == 'input_pending')
check('boundary 写明"旁路不消除矛盾、也不替主线程决策"',
      '不' in OB.run({'main_events': EV})['boundary']
      and ('决策' in OB.run({'main_events': EV})['boundary'] or
           '消除' in OB.run({'main_events': EV})['boundary']))
check('PORTS 声明 main_ran/findings/injected_at（白箱三件齐）',
      all(k in OB.PORTS['out'] for k in
          ('main_ran', 'findings', 'injected_at')), list(OB.PORTS['out']))

print()
print('=' * 70)
print(f'结果: {PASS}/14 通过')
raise SystemExit(0 if PASS == 14 else 1)
