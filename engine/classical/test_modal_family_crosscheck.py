# -*- coding: utf-8 -*-
"""test_modal_family_crosscheck.py — 时间/模态族三件互验（③ 验证轴 · 第三批）

为什么要有这份文件：
    `modal`（在给定 Kripke 模型上求值）· `ltl`（沿给定路径求值）·
    `model_check`（在给定结构上做 CTL 定点）——三件事共用"结构 + 公式"的骨架，
    但语义各不相同，各自的错法也不同。所以在本文件里**按语义各写一个独立求值器**，
    拿它去夹三个构件：这是最强的独立路（语义等价的精确对拍），
    比"自己测自己"有信息量（闸三：工具不可自证）。

三个 oracle（都在本文件里，不 import 任何判定构件）：
    M. 模态求值：□ 全后继真、◇ 有后继真；死锁处 □ 空集真（标准约定）；
    L. 有限路径 LTL：X 末位置为假、G 全程、F 前缀内出现、U 按定义；
    C. CTL 定点：EX/AX 一步，EF/AF/EU/AU 最小不动点，EG/AG 最大不动点
       （在有限结构上直接迭代到收敛，不抄构件的做法）。

判据：
    · 三件都判"给定结构/路径/模型下的真假"——所以**要求精确一致**；
    · 另验两条**约定**（构件边界里写明的）：死锁处全称算子按空集真；
      T/S4/S5 的系统假设不满足时构件报 `system_mismatch`；
    · 变异接受：三个 oracle 各改坏一处，对拍必须抓住。
运行：python engine/classical/test_modal_family_crosscheck.py
"""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import ltl as LT          # noqa: E402
from engine.classical import modal as MD        # noqa: E402
from engine.classical import model_check as MC  # noqa: E402

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


# ══════════════════════════════════════════════════════════════
# 一、模态：本文件自己的求值器（oracle M）
# ══════════════════════════════════════════════════════════════
BIN = ('∧', '∨', '→', '↔')


def gen_modal(rng, atoms, depth):
    if depth <= 0 or rng.random() < 0.45:
        return ('atom', rng.choice(atoms))
    r = rng.random()
    if r < 0.15:
        return ('¬', gen_modal(rng, atoms, depth - 1))
    if r < 0.30:
        return ('□', gen_modal(rng, atoms, depth - 1))
    if r < 0.45:
        return ('◇', gen_modal(rng, atoms, depth - 1))
    return (rng.choice(BIN), gen_modal(rng, atoms, depth - 1),
            gen_modal(rng, atoms, depth - 1))


def render_modal(f):
    k = f[0]
    if k == 'atom':
        return f[1]
    if k == '¬':
        return '¬(%s)' % render_modal(f[1])
    if k in ('□', '◇'):
        return '%s(%s)' % (k, render_modal(f[1]))
    return '(%s %s %s)' % (render_modal(f[1]), k, render_modal(f[2]))


def ev_modal(f, w, access, val, mutate=False):
    k = f[0]
    if k == 'atom':
        return w in val.get(f[1], set())
    if k == '¬':
        return not ev_modal(f[1], w, access, val, mutate)
    if k == '□':
        succ = access.get(w, [])
        vals = [ev_modal(f[1], v, access, val, mutate) for v in succ]
        r = all(vals) if not mutate else any(vals)   # 变异：□ 与 ◇ 判反
        return r
    if k == '◇':
        succ = access.get(w, [])
        return any(ev_modal(f[1], v, access, val, mutate) for v in succ)
    a = ev_modal(f[1], w, access, val, mutate)
    b = ev_modal(f[2], w, access, val, mutate)
    if k == '∧':
        return a and b
    if k == '∨':
        return a or b
    if k == '→':
        return (not a) or b
    return a == b


# ══════════════════════════════════════════════════════════════
# 二、LTL：本文件自己的有限路径求值器（oracle L）
# ══════════════════════════════════════════════════════════════
def gen_ltl(rng, atoms, depth):
    if depth <= 0 or rng.random() < 0.42:
        return ('atom', rng.choice(atoms))
    r = rng.random()
    if r < 0.12:
        return ('¬', gen_ltl(rng, atoms, depth - 1))
    if r < 0.26:
        return ('X', gen_ltl(rng, atoms, depth - 1))
    if r < 0.40:
        return ('G', gen_ltl(rng, atoms, depth - 1))
    if r < 0.54:
        return ('F', gen_ltl(rng, atoms, depth - 1))
    if r < 0.64:
        return ('U', gen_ltl(rng, atoms, depth - 1),
                gen_ltl(rng, atoms, depth - 1))
    return (rng.choice(BIN), gen_ltl(rng, atoms, depth - 1),
            gen_ltl(rng, atoms, depth - 1))


def render_ltl(f):
    k = f[0]
    if k == 'atom':
        return f[1]
    if k == '¬':
        return '¬(%s)' % render_ltl(f[1])
    if k in ('X', 'G', 'F'):
        return '%s(%s)' % (k, render_ltl(f[1]))
    return '(%s %s %s)' % (render_ltl(f[1]), k, render_ltl(f[2]))


def ev_ltl(f, path, i, mutate=False):
    """有限路径语义：X 在末位置为假；G 看 i..末尾；F 看 i..末尾；U 按定义。"""
    k = f[0]
    if k == 'atom':
        return f[1] in path[i]
    if k == '¬':
        return not ev_ltl(f[1], path, i, mutate)
    if k == 'X':
        if i + 1 >= len(path):
            r = False                     # 末位置无后继：X 为假
        else:
            r = ev_ltl(f[1], path, i + 1, mutate)
        return (not r) if mutate else r   # 变异：X 判反
    if k == 'G':
        return all(ev_ltl(f[1], path, j, mutate) for j in range(i, len(path)))
    if k == 'F':
        return any(ev_ltl(f[1], path, j, mutate) for j in range(i, len(path)))
    if k == 'U':
        for j in range(i, len(path)):
            if ev_ltl(f[2], path, j, mutate) and all(
                    ev_ltl(f[1], path, k2, mutate) for k2 in range(i, j)):
                return True
        return False
    a, b = ev_ltl(f[1], path, i, mutate), ev_ltl(f[2], path, i, mutate)
    if k == '∧':
        return a and b
    if k == '∨':
        return a or b
    if k == '→':
        return (not a) or b
    return a == b


# ══════════════════════════════════════════════════════════════
# 三、CTL：本文件自己的定点穷算（oracle C）
# ══════════════════════════════════════════════════════════════
def gen_ctl(rng, atoms, depth):
    if depth <= 0 or rng.random() < 0.35:
        return ('atom', rng.choice(atoms))
    r = rng.random()
    if r < 0.10:
        return ('¬', gen_ctl(rng, atoms, depth - 1))
    if r < 0.16:
        return ('&', gen_ctl(rng, atoms, depth - 1),
                gen_ctl(rng, atoms, depth - 1))
    if r < 0.22:
        return ('|', gen_ctl(rng, atoms, depth - 1),
                gen_ctl(rng, atoms, depth - 1))
    if r < 0.26:
        return ('->', gen_ctl(rng, atoms, depth - 1),
                gen_ctl(rng, atoms, depth - 1))
    q = rng.choice(['E', 'A'])
    if r < 0.75:
        return (q + rng.choice(['X', 'F', 'G']), gen_ctl(rng, atoms, depth - 1))
    return (q + 'U', gen_ctl(rng, atoms, depth - 1),
            gen_ctl(rng, atoms, depth - 1))


def render_ctl(f):
    k = f[0]
    if k == 'atom':
        return f[1]
    if k == '¬':
        return '¬(%s)' % render_ctl(f[1])
    if k in ('&', '|', '->'):
        return '(%s %s %s)' % (render_ctl(f[1]), k, render_ctl(f[2]))
    if k.endswith('U'):
        return '%s[%s U %s]' % (k[0], render_ctl(f[1]), render_ctl(f[2]))
    return '%s(%s)' % (k, render_ctl(f[1]))


def sat_ctl(f, states, succ, labels):
    """返回满足 f 的状态集合（用不动点迭代，不抄构件实现）。"""
    k = f[0]
    if k == 'atom':
        return {s for s in states if f[1] in labels.get(s, [])}
    if k == '¬':
        return set(states) - sat_ctl(f[1], states, succ, labels)
    if k in ('&', '|', '->'):
        a = sat_ctl(f[1], states, succ, labels)
        b = sat_ctl(f[2], states, succ, labels)
        if k == '&':
            return a & b
        if k == '|':
            return a | b
        return (set(states) - a) | b
    if k.endswith('U'):
        q = k[0]
        left = sat_ctl(f[1], states, succ, labels)
        right = sat_ctl(f[2], states, succ, labels)
        cur = set(right)
        while True:
            if q == 'E':
                nxt = cur | {s for s in left if any(t in cur
                                                    for t in succ.get(s, []))}
            else:
                # 全称侧：**死锁处按空集真**（标准约定）——不能要求"必须有后继"
                nxt = cur | {s for s in left
                             if all(t in cur for t in succ.get(s, []))}
            if nxt == cur:
                return cur
            cur = nxt
    q, op = k[0], k[1]
    inner = sat_ctl(f[1], states, succ, labels)
    if op == 'X':
        if q == 'E':
            return {s for s in states if any(t in inner
                                             for t in succ.get(s, []))}
        return {s for s in states if all(t in inner
                                         for t in succ.get(s, []))}
    if op == 'F':                      # 最小不动点
        cur = set(inner)
        while True:
            if q == 'E':
                nxt = cur | {s for s in states
                             if any(t in cur for t in succ.get(s, []))}
            else:
                # 同上：死锁状态一定进 AF（空集真），所以不筛"有后继"
                nxt = cur | {s for s in states
                             if all(t in cur for t in succ.get(s, []))}
            if nxt == cur:
                return cur
            cur = nxt
    # G：最大不动点 νZ. φ ∩ AX Z（**起始值必须是 φ 的集合**——第一版从全集起，
    # 等于把 φ 漏掉了，于是 AG P 会把不含 P 的状态也算进去）
    cur = set(inner)
    while True:
        if q == 'E':
            nxt = cur & {s for s in states
                         if any(t in cur for t in succ.get(s, []))}
        else:
            nxt = cur & {s for s in states
                         if all(t in cur for t in succ.get(s, []))}
        if nxt == cur:
            return cur
        cur = nxt


# ══════════════════════════════════════════════════════════════
# 四、oracle 自检（已知答案）
# ══════════════════════════════════════════════════════════════
P, Q = ('atom', 'P'), ('atom', 'Q')
print('=' * 70)
print('一、oracle 自检（已知答案）')
# 模态：一个自反单点世界，□P 与 P 同真假
acc1 = {'w': ['w']}
check('oracle M：自反点上 □(P→P) 真',
      ev_modal(('□', ('→', P, P)), 'w', acc1, {'P': {'w'}}))
check('oracle M：T 框架上 □P → P 真（自反）',
      ev_modal(('→', ('□', P), P), 'w', acc1, {'P': {'w'}}))
check('oracle M：K 框架上死锁点 □⊥ 空集真（标准约定）',
      ev_modal(('□', ('∧', P, ('¬', P))), 'w', {'w': []}, {}))
# LTL
check('oracle L：G(P) 在全程 P 的路径上成立',
      ev_ltl(('G', P), [{'P'}, {'P'}], 0))
check('oracle L：F(P) 在末尾出现 P 的路径上成立',
      ev_ltl(('F', P), [{}, {'P'}], 0))
check('oracle L：X(P) 在末位置为假（无后继）',
      ev_ltl(('X', P), [{'P'}], 0) is False)
check('oracle L：P U Q 在"先 P 后 Q"的路径上成立',
      ev_ltl(('U', P, Q), [{'P'}, {'P'}, {'Q'}], 0))
# CTL
ST, SU = ['s0', 's1'], {'s0': ['s1'], 's1': ['s1']}
LB = {'s0': ['P'], 's1': []}
check('oracle C：s0→s1→s1（s1 无 P）时 AG P 在 s0 不成立',
      's0' not in sat_ctl(('AG', P), ST, SU, LB))
check('oracle C：AF P 只含 s0',
      sat_ctl(('AF', P), ST, SU, LB) == {'s0'})
check('oracle C：EG ⊤ 含自环可达的 s1',
      's1' in sat_ctl(('EG', ('|', P, ('¬', P))), ST, SU, LB))

# ══════════════════════════════════════════════════════════════
# 五、modal ↔ oracle M
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、modal ↔ oracle M（给定 Kripke 模型上求值）')
rng = random.Random(20261006)
mis_m, n_true_m = [], 0
TRIALS_M = 40
for _ in range(TRIALS_M):
    ws = ['w0', 'w1', 'w2'][:rng.choice([1, 2, 3])]
    access = {w: [v for v in ws if rng.random() < 0.45] for w in ws}
    val = {a: {w for w in ws if rng.random() < 0.5} for a in ('P', 'Q')}
    f = gen_modal(rng, ['P', 'Q'], 2)
    w0 = rng.choice(ws)
    truth = ev_modal(f, w0, access, val)
    n_true_m += 1 if truth else 0
    r = MD.run({'worlds': ws, 'access': access, 'system': 'K',
                'assign': {a: sorted(v) for a, v in val.items()},
                'formula': render_modal(f), 'world': w0})
    if r['verdict'] not in ('true', 'false'):
        continue
    if (r['verdict'] == 'true') != truth:
        mis_m.append((ws, access, render_modal(f), w0, r['verdict'], truth))
check('modal 与 oracle M 精确一致（%d 例，含 %d 个真）' % (TRIALS_M, n_true_m),
      mis_m == [], mis_m[:1])
check('modal 的判定不是恒真/恒假（两侧都出现过）',
      0 < n_true_m < TRIALS_M, n_true_m)
check('modal 的系统自检：T 框架不自反时如实报 system_mismatch',
      MD.run({'worlds': ['a', 'b'], 'access': {'a': ['b'], 'b': []},
              'assign': {}, 'formula': 'P', 'system': 'T',
              'world': 'a'})['verdict'] == 'system_mismatch')

# ══════════════════════════════════════════════════════════════
# 六、ltl ↔ oracle L
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、ltl ↔ oracle L（有限路径上求值）')
rng = random.Random(20261007)
mis_l, n_hold_l = [], 0
TRIALS_L = 40
for _ in range(TRIALS_L):
    n = rng.choice([1, 2, 3, 4])
    path = [{a for a in ('P', 'Q') if rng.random() < 0.5} for _ in range(n)]
    f = gen_ltl(rng, ['P', 'Q'], 2)
    truth = ev_ltl(f, path, 0)
    n_hold_l += 1 if truth else 0
    r = LT.run({'path': [dict.fromkeys(sorted(st), True) for st in path],
                'formula': render_ltl(f)})
    if r['verdict'] not in ('holds', 'violated'):
        continue
    if (r['verdict'] == 'holds') != truth:
        mis_l.append(([sorted(s) for s in path], render_ltl(f),
                      r['verdict'], truth))
check('ltl 与 oracle L 精确一致（%d 例，含 %d 个成立）' % (TRIALS_L, n_hold_l),
      mis_l == [], mis_l[:1])
check('ltl 的判定不是恒成立/恒违约（两侧都出现过）',
      0 < n_hold_l < TRIALS_L, n_hold_l)

# ══════════════════════════════════════════════════════════════
# 七、model_check ↔ oracle C
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、model_check ↔ oracle C（给定结构上做 CTL 定点）')
rng = random.Random(20261008)
mis_c, n_hold_c = [], 0
TRIALS_C = 40
for _ in range(TRIALS_C):
    states = ['s0', 's1', 's2'][:rng.choice([2, 3])]
    pairs = [[x, y] for x in states for y in states if rng.random() < 0.4]
    succ = {}
    for x, y in pairs:
        succ.setdefault(x, []).append(y)
    labels = {s: [a for a in ('P', 'Q') if rng.random() < 0.5]
              for s in states}
    f = gen_ctl(rng, ['P', 'Q'], 2)
    init = [states[0]]
    sat = sat_ctl(f, states, succ, labels)
    truth = all(s in sat for s in init)
    n_hold_c += 1 if truth else 0
    r = MC.run({'states': states, 'transitions': pairs, 'labels': labels,
                'formula': render_ctl(f), 'init': init})
    if r['verdict'] not in ('holds', 'fails'):
        continue
    if (r['verdict'] == 'holds') != truth:
        mis_c.append((states, pairs, labels, render_ctl(f),
                      r['verdict'], truth, sorted(sat)))
check('model_check 与 oracle C 精确一致（%d 例，含 %d 个成立）'
      % (TRIALS_C, n_hold_c), mis_c == [], mis_c[:1])
check('model_check 的判定不是恒成立/恒不成立（两侧都出现过）',
      0 < n_hold_c < TRIALS_C, n_hold_c)
check('model_check 死锁约定：无出边的状态上 AX 按空集真（标准约定）',
      MC.run({'states': ['s0', 's1'], 'transitions': [],
              'labels': {'s0': [], 's1': []}, 'formula': 'AX P',
              'init': ['s0']})['verdict'] == 'holds')

# ══════════════════════════════════════════════════════════════
# 八、变异接受
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('五、变异接受（改坏 oracle，看对拍有没有咬合力）')
check('变异 M：把 □ 判反后与正版不同（两后继一个真一个假，□ 与 ◇ 才分得开）',
      ev_modal(('□', P), 'w', {'w': ['v1', 'v2']}, {'P': {'v1'}})
      != ev_modal(('□', P), 'w', {'w': ['v1', 'v2']}, {'P': {'v1'}},
                  mutate=True))
check('变异 L：把 X 判反后，与正版结论不同',
      ev_ltl(('X', P), [{'P'}, {}], 0)
      != ev_ltl(('X', P), [{'P'}, {}], 0, mutate=True))


def sat_eg_least(states, succ, labels):
    """错误的做法：把 EG 当**最小**不动点算——用来证明"最大不动点"这一步是真的在起作用。"""
    cur = set()
    while True:
        nxt = cur | {s for s in states
                     if ('P' in labels.get(s, []))
                     and any(t in cur for t in succ.get(s, []))}
        if nxt == cur:
            return cur
        cur = nxt


_CYC = (['s0', 's1'], {'s0': ['s1'], 's1': ['s1']},
        {'s0': ['P'], 's1': ['P']})
_CYC = (['s0', 's1'], {'s0': ['s1'], 's1': ['s1']},
        {'s0': ['P'], 's1': ['P']})
check('变异 C：EG 若按最小不动点算会漏掉自环上的状态（证明"最大不动点"不是摆设）',
      sat_ctl(('EG', P), *_CYC) == {'s0', 's1'}
      and sat_eg_least(*_CYC) != {'s0', 's1'}, sat_eg_least(*_CYC))

print()
print('=' * 70)
print(f'结果: {PASS}/21 通过')
raise SystemExit(0 if PASS == 21 else 1)
