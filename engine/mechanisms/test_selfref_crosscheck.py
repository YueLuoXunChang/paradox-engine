# -*- coding: utf-8 -*-
"""test_selfref_crosscheck.py — 自指不动点件的独立互验（③ 验证轴 · 第六批）

为什么要有这份文件：
    `selfref_fixpoint` 是**引擎原创**件（三态：不动点 / 共振带 / 发散 + 说谎者周期 +
    哥德尔注解）。原创件的口径是作者定的，所以验法要分两层：
      ① **口径内自洽**：实现必须与它**自己文档写的规则**一致（定义↔实现对齐）；
      ② **预测可对上**：拿**解析公式**（仿射映射）与**函数图全局分析**（布尔系统）
         这两条**与构件顺序检测不同的路**去预测，看它对不对得上。

两条 oracle（都在本文件里）：
    P. **解析预测**（仿射 f(x)=a·x+b）：
       · |a|<1 → 收缩，第 n 步差 |a|^n·d0；首个 <tol 的 n 就是该报不动点的步；
       · a=−1 → 交替，周期 2；|a|>1 → 几何放大，|x|>1e12 才叫发散（否则诚实未决）。
    G. **函数图全局分析**（布尔系统）：把状态转移当函数图，**全局**找出环与入环距离，
       预测「不动点 / 周期几 / 观察窗内未决」——与构件"边走边查重"不是同一条路。

运行：python engine/mechanisms/test_selfref_crosscheck.py
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

from engine.mechanisms import selfref_fixpoint as SF   # noqa: E402

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


def run_iter(f, x0, steps=100, tol=1e-9):
    return SF.run({'mode': 'iterate', 'f': f, 'state0': x0,
                   'max_steps': steps, 'tol': tol})


# ══════════════════════════════════════════════════════════════
# 一、oracle P：仿射映射的解析预测（不用构件的算法）
# ══════════════════════════════════════════════════════════════
BLOW = 1e12          # 构件文档写死的发射阈值（|x| > 1e12 才算 grow）
MAXB = 100


def affine_expect(a, b, x0, max_steps=MAXB, tol=1e-9):
    """返回 (预期判词, 预期到达步 或 None)。

    推导（都是自己算的，没抄构件）：
      · d_n = |x_{n+1} - x_n| = |a|^n · d0，d0 = |x1 - x0|
      · a=1,b=0：恒等 → 第 1 步就不动点
      · |a|<1：收缩；首个满足 d0·|a|^n < tol 的 n → 报不动点（reached_at = n+1）
      · a=-1：交替（周期 2）；若 d0 < tol 则第 1 步就当"容差内不动点"
      · |a|>1：|x_n| 几何放大；首个 |x_n| > 1e12 在窗口内 → 发散，否则诚实未决
    """
    x1 = a * x0 + b
    d0 = abs(x1 - x0)
    # ① 恒等或容差内已不动
    if d0 == 0:
        return 'fixed_point', 1
    if d0 < tol and a in (1, -1):
        return 'fixed_point', 1
    # ② 收缩
    if abs(a) < 1:
        n = 0
        while n < max_steps:
            if d0 * (abs(a) ** n) < tol:
                return 'fixed_point', n + 1
            n += 1
        return 'undetermined', None
    # ③ 交替
    if a == -1:
        return 'resonance_band', None
    # ④ 放大：看首个越阈步
    if abs(a) > 1:
        x = x0
        for n in range(max_steps + 1):
            if abs(x) > BLOW:
                return 'diverge', None
            x = a * x + b
        return 'undetermined', None
    # a == 1 且 b != 0：线性增长，永远追不上 1e12（窗口内）→ 诚实未决
    return 'undetermined', None


print('=' * 70)
print('一、oracle P 自检（解析公式自己算一遍）')
check('收缩预测：x/2+1 从 0 起步，需 30 步降到 1e-9 以下（报 reached_at=31）',
      affine_expect(0.5, 1, 0.0) == ('fixed_point', 31),
      affine_expect(0.5, 1, 0.0))
check('放大预测：2x 从 1 起步，44 步内越 1e12（因此该报发散）',
      affine_expect(2, 0, 1.0)[0] == 'diverge')
check('缓涨预测：1.1x 在 100 步窗口内追不上阈值（该报诚实未决）',
      affine_expect(1.1, 0, 1.0)[0] == 'undetermined')

# ══════════════════════════════════════════════════════════════
# 二、selfref_fixpoint ↔ 解析预测（仿射族网格）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、selfref_fixpoint ↔ oracle P（仿射族：a × b × x0 网格）')
_mis_cls, _mis_step, _n_cls = [], [], {}
for _a in (0.0, 0.5, 0.9, -0.5, -0.9, -1.0, 1.0, 1.1, 2.0, -2.0):
    for _b in (0.0, 1.0):
        for _x0 in (0.0, 1.0, -3.0):
            _want, _want_at = affine_expect(_a, _b, _x0)
            _r = run_iter((lambda x, _a=_a, _b=_b: _a * x + _b), _x0)
            _got = _r['verdict']
            _n_cls[_got] = _n_cls.get(_got, 0) + 1
            if _got != _want:
                _mis_cls.append((_a, _b, _x0, _got, _want))
            elif _want == 'fixed_point':
                _seen_at = _r['detail'].get('reached_at')
                if _seen_at != _want_at:
                    _mis_step.append((_a, _b, _x0, _seen_at, _want_at))
check('仿射族 60 例：判词与解析预测全一致（含固定点/共振带/发散/未决四态）',
      _mis_cls == [], _mis_cls[:2])
check('报不动点的那批：**到达步数**也与解析公式一致（不是只对了个判词）',
      _mis_step == [], _mis_step[:2])
check('四态都被覆盖到（%s）' % _n_cls,
      all(k in _n_cls for k in ('fixed_point', 'resonance_band', 'diverge',
                                'undetermined')), _n_cls)

# ══════════════════════════════════════════════════════════════
# 三、selfref_fixpoint ↔ oracle G（布尔系统：函数图全局分析）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、selfref_fixpoint ↔ oracle G（布尔系统：全局找环，与边走边查重不同路）')


def graph_expect(next_of, start, max_steps):
    """全局分析：先在整张函数图上找每个状态的环，再算初值入环距离。

    返回 (预期判词, 预期周期)。周期 2 且状态是布尔 → 构件口径叫 liar_cycle。
    """
    states = list(next_of)
    # 某状态所在环的长度（跟着走最多 |S| 步回到自己）
    def cyc_len(s):
        cur = next_of[s]
        for k in range(1, len(states) + 1):
            if cur == s:
                return k
            cur = next_of[cur]
        return None
    seen, cur = [], start
    while cur not in seen and len(seen) <= max_steps:
        seen.append(cur)
        cur = next_of[cur]
    if cur not in seen:
        return 'undetermined', None          # 窗口内没入环
    dist = seen.index(cur)
    period = cyc_len(cur)
    detect_at = dist + period
    if detect_at > max_steps:
        return 'undetermined', None
    if period == 1:
        return 'fixed_point', 1
    if period == 2 and all(isinstance(s, bool) for s in
                           (next_of[s] for s in states)):
        return 'liar_cycle', 2
    return 'resonance_band', period


def make_bool_fn(table, bits=2):
    def f(state):
        idx = 0
        for b in state:
            idx = idx * 2 + (1 if b else 0)
        return table[idx]
    return f


_all1 = []
for _t in itertools.product([(False,), (True,)], repeat=2):
    _all1.append((_t, make_bool_fn(list(_t), bits=1)))
_mis1 = []
for _t, _f in _all1:
    _nxt = {s: _f(s) for s in [(False,), (True,)]}
    _want, _wp = graph_expect(_nxt, (False,), 20)
    _r = run_iter(_f, (False,), steps=20)
    if _r['verdict'] != _want:
        _mis1.append((_t, _r['verdict'], _want))
check('1 位布尔函数全枚举（4 个）：判词与函数图预测一致', _mis1 == [], _mis1[:2])

_rng = random.Random(20261011)
_mis2, _pers, _kinds = [], 0, {}
for _ in range(40):
    _table = [tuple(bool(_rng.random() < 0.5) for _ in range(2))
              for _ in range(4)]
    _f = make_bool_fn(_table, bits=2)
    _states = [(False, False), (False, True), (True, False), (True, True)]
    _nxt = {s: _f(s) for s in _states}
    _want, _wp = graph_expect(_nxt, (False, False), 30)
    _r = run_iter(_f, (False, False), steps=30)
    _kinds[_r['verdict']] = _kinds.get(_r['verdict'], 0) + 1
    if _r['verdict'] != _want:
        _mis2.append((_table, _r['verdict'], _want))
    elif _want == 'resonance_band' and _r['detail'].get('period') != _wp:
        _mis2.append((_table, 'period', _r['detail'].get('period'), _wp))
    else:
        _pers += 1
check('随机 40 个两位布尔系统：判词（含周期长度）与函数图预测一致',
      _mis2 == [], _mis2[:2])
check('随机样本覆盖多种走向（%s）' % _kinds, len(_kinds) >= 2)

# ══════════════════════════════════════════════════════════════
# 四、内置自指句与注解卡（口径层）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、内置自指句 + 8 字段注解卡')
_liar = SF.run({'mode': 'sentence', 'sentence': 'liar', 'max_steps': 50})
check('说谎者 → liar_cycle，周期 2（与 §246 的 truth_revision 同源结论）',
      _liar['verdict'] == 'liar_cycle' and _liar['detail'].get('period') == 2)
check('说谎者注解卡 8 字段齐，且判为悖论型（LV=P-A）',
      len(_liar['annotation'] or {}) == 8
      and _liar['annotation']['LV'] == 'P-A')
_tt = SF.run({'mode': 'sentence', 'sentence': 'truth_teller', 'max_steps': 50})
check('真话者 → fixed_point，且边界写清"不动点不唯一、需外部锚定"',
      _tt['verdict'] == 'fixed_point' and '不唯一' in _tt['boundary'])
_gd = SF.run({'mode': 'sentence', 'sentence': 'godel', 'max_steps': 50})
check('哥德尔 → annotated_pa，且**不假装跑序列**（诚实口径：可证性谓词不是真值函数）',
      _gd['verdict'] == 'annotated_pa' and len(_gd['annotation'] or {}) == 8
      and '不宣称判定' in _gd['boundary'])
check('不认得的自指句 → input_pending（不猜、不硬跑）',
      SF.run({'mode': 'sentence', 'sentence': 'zzz'})['verdict']
      == 'input_pending')

# ══════════════════════════════════════════════════════════════
# 五、诚实边界与容差（① 轴：边界要钉住）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('五、诚实边界与容差')
check('窗口不足 → undetermined（**不许硬判发散**）：x/2+1 只给 1 步',
      run_iter(lambda x: x / 2 + 1, 0.0, steps=1)['verdict'] == 'undetermined')
check('线性增长 x+1 在窗口内 → undetermined（不硬判发散，文档承诺）',
      run_iter(lambda x: x + 1, 0.0, steps=100)['verdict'] == 'undetermined')
_tol_strict = run_iter(lambda x: x / 2 + 1, 0.0, steps=1, tol=1.0)['verdict']
check('★容差是**严格小于**：差恰好等于 tol 不算"相同"（该报未决，不是不动点）'
      f'（实测 {_tol_strict}）', _tol_strict == 'undetermined')
check('容差调紧/调松会改变到达步（tol 真的在起作用）：tol=1e-3 比 tol=1e-9 早',
      run_iter(lambda x: x / 2 + 1, 0.0, tol=1e-3)['detail'].get('reached_at')
      < run_iter(lambda x: x / 2 + 1, 0.0, tol=1e-9)['detail'].get('reached_at'))
check('修正函数抛异常 → parse_error（诚实拦截，不静默）',
      run_iter(lambda x: 1 / 0, 0.0)['verdict'] == 'parse_error')

print()
print('=' * 70)
print(f'结果: {PASS}/19 通过')
raise SystemExit(0 if PASS == 19 else 1)
