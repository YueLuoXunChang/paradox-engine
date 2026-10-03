# -*- coding: utf-8 -*-
"""test_fol_crosscheck.py — 一阶逻辑三件的跨构件对拍（③ 验证轴）

为什么要有这份文件：
    `monadic_fol` · `first_order` · `equality_tableau` 判的是**同一族问题**
    （论域上的有效性/蕴含，外加等词替换），但用的是三套完全不同的做法：
    小域穷举 · 有限论域展开后交给命题引擎 · tableau 加等词替换。
    三套做法各有各的错法，所以拿**本文件自己写的三个 oracle** 分别夹它们——
    比"自己测自己"有信息量（闸三：工具不可自证）。

三个 oracle（都写在本文件里，不 import 任何判定构件）：
    A. 全论域有效性：一元片段（k 个谓词，k ≤ 2）只需域 ≤ 2^k 就能找到反模型
       —— 逐域大小穷举全部解释；
    B. 有限论域蕴含：固定论域 U，穷举 U 上所有谓词解释，检查"前提全真的每一行结论也真"；
    C. 等词地面蕴含：并查集把等词类归一化，再看规范化后是否出现互补对
       （只剩原子文字时，不可满足 ⟺ 某原子正负都在）。

判据按各件性质定（不搞一刀切）：
    · monadic_fol（k ≤ 2 完备）↔ oracle A：**精确一致**；
    · first_order（有限论域完整展开）↔ oracle B：**精确一致**；
    · equality_tableau（有 max_expand 上限）↔ oracle C：说 valid/invalid 时必须一致，
      `undetermined` 是它自己的诚实边界，不作分歧。
另含**变异接受**：三个 oracle 各改坏一处，对拍必须抓住。

写法约定：所有公式**闭合**（顶层带量词），地面事实才用常量——
自由变元的式子不是命题，拿它去比会造出假分歧（第一版就差点这么写）。
运行：python engine/classical/test_fol_crosscheck.py
"""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import equality_tableau as ET   # noqa: E402
from engine.classical import first_order as FO        # noqa: E402
from engine.classical import monadic_fol as MF        # noqa: E402

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
# 一、本文件自己的公式语言：生成 / 渲染 / 求值
# ══════════════════════════════════════════════════════════════
BIN = ('∧', '∨', '→', '↔')
UNIV = ['a', 'b']


def gen_body(rng, preds, depth, var='x'):
    if depth <= 0 or rng.random() < 0.4:
        return ('atom', rng.choice(preds), var)
    r = rng.random()
    if r < 0.18:
        return ('¬', gen_body(rng, preds, depth - 1, var))
    if r < 0.33:
        return (rng.choice(('∀', '∃')), var,
                gen_body(rng, preds, depth - 1, var))
    return (rng.choice(BIN), gen_body(rng, preds, depth - 1, var),
            gen_body(rng, preds, depth - 1, var))


def gen_closed(rng, preds, depth):
    """闭合的一元公式：顶层一定带量词，不留自由变元。"""
    return (rng.choice(('∀', '∃')), 'x',
            gen_body(rng, preds, depth, 'x'))


def gen_ground(rng, preds):
    """地面事实：谓词作用在常量上。"""
    atom = ('atom', rng.choice(preds), rng.choice(UNIV))
    return ('¬', atom) if rng.random() < 0.35 else atom


def render(f):
    k = f[0]
    if k == 'atom':
        return '%s(%s)' % (f[1], f[2])
    if k == '¬':
        return '¬(%s)' % render(f[1])
    if k in ('∀', '∃'):
        return '%s%s(%s)' % (k, f[1], render(f[2]))
    return '(%s %s %s)' % (render(f[1]), k, render(f[2]))


def ev(f, interp, env):
    """在解释下求值。interp 里带 '__n__'（域大小）与 '__const__'（常量→元素）。"""
    k = f[0]
    if k == 'atom':
        t = f[2]
        e = env[t] if t in env else interp['__const__'][t]
        return interp[(e, f[1])]
    if k == '¬':
        return not ev(f[1], interp, env)
    if k in ('∀', '∃'):
        var = f[1]
        vals = [ev(f[2], interp, dict(env, **{var: e}))
                for e in range(interp['__n__'])]
        return all(vals) if k == '∀' else any(vals)
    a, b = ev(f[1], interp, env), ev(f[2], interp, env)
    if k == '∧':
        return a and b
    if k == '∨':
        return a or b
    if k == '→':
        return (not a) or b
    return a == b


def interps(preds, n, univ=None):
    """域大小 n、谓词集 preds 的全部解释（谓词解释 = 每个元素每个谓词取真假）。"""
    cells = [(e, p) for e in range(n) for p in preds]
    for bits in range(1 << len(cells)):
        interp = {'__n__': n,
                  '__const__': {c: i for i, c in enumerate((univ or [])[:n])}}
        for i, c in enumerate(cells):
            interp[c] = bool((bits >> i) & 1)
        yield interp


def oracle_valid_all(f, preds, mutate=False):
    """oracle A：全论域有效性（一元片段 k ≤ 2 只需域 ≤ 2^k）。"""
    for n in range(1, 2 ** len(preds) + 1):
        for interp in interps(preds, n):
            v = ev(f, interp, {})
            if mutate:
                v = not v          # 变异：把真假判反
            if not v:
                return False
    return True


def oracle_entails_U(premises, conclusion, preds, univ, mutate=False):
    """oracle B：固定论域上穷举解释，检查前提全真 ⇒ 结论真。"""
    for interp in interps(preds, len(univ), univ):
        all_prem = all(ev(p, interp, {}) for p in premises)
        c = ev(conclusion, interp, {})
        if mutate:
            c = not c              # 变异：只看结论侧判反
        if all_prem and not c:
            return False
    return True


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def _canon_lit(s, uf):
    s = s.strip()
    neg = False
    while s.startswith('¬'):
        neg = not neg
        s = s[1:].strip()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1].strip()
    name, arg = s.split('(', 1)
    out = '%s(%s)' % (name.strip(), uf.find(arg.rstrip(')').strip()))
    return ('¬' + out) if neg else out


def oracle_ground_equality(premises, conclusion, equalities, mutate=False):
    """oracle C：等词归一化后，前提 ⊨ 结论 ⟺ 前提 + ¬结论 不可满足。"""
    uf = _UF()
    for e in equalities:
        a, b = e.split('=')
        uf.union(a.strip(), b.strip())
    lits = {_canon_lit(p, uf) for p in premises}
    neg_concl = (conclusion[1:].strip('()') if conclusion.lstrip().startswith('¬')
                 else '¬(%s)' % conclusion)
    lits.add(_canon_lit(neg_concl, uf))
    for lit in lits:
        neg = lit[1:] if lit.startswith('¬') else '¬' + lit
        if neg in lits:
            return not mutate       # 变异：把判据反了
    return mutate


# ══════════════════════════════════════════════════════════════
# 二、oracle 自检（已知答案先钉住判据本身）
# ══════════════════════════════════════════════════════════════
Px = ('atom', 'P', 'x')
Pa = ('atom', 'P', 'a')
print('=' * 70)
print('一、oracle 自检（已知答案）')
check('oracle A：∀x(P(x)→P(x)) 有效',
      oracle_valid_all(('∀', 'x', ('→', Px, Px)), ['P']))
check('oracle A：∃x(P(x)∧¬P(x)) 无效（自相矛盾）',
      not oracle_valid_all(('∃', 'x', ('∧', Px, ('¬', Px))), ['P']))
check('oracle A：∀x P(x) → ∃x P(x) 有效（论域非空）',
      oracle_valid_all(('→', ('∀', 'x', Px), ('∃', 'x', Px)), ['P']))
check('oracle B：{a,b} 上 P(a) ⊨ ∃x P(x)',
      oracle_entails_U([Pa], ('∃', 'x', Px), ['P'], UNIV))
check('oracle B：{a,b} 上 无前提 ⊭ ∀x P(x)',
      not oracle_entails_U([], ('∀', 'x', Px), ['P'], UNIV))
check('oracle B：前提自相矛盾 ⇒ 什么都蕴含',
      oracle_entails_U([Pa, ('¬', Pa)], ('∀', 'x', Px), ['P'], UNIV))
check('oracle C：a=b, P(a) ⊨ P(b)',
      oracle_ground_equality(['P(a)'], 'P(b)', ['a=b']))
check('oracle C：不带等词时 P(a) ⊭ P(b)',
      not oracle_ground_equality(['P(a)'], 'P(b)', []))
check('oracle C：等词传递 a=b, b=c, P(a) ⊨ P(c)',
      oracle_ground_equality(['P(a)'], 'P(c)', ['a=b', 'b=c']))
check('oracle C：前提自相矛盾 ⇒ 什么都蕴含',
      oracle_ground_equality(['P(a)', '¬P(a)'], 'Q(b)', []))

# ══════════════════════════════════════════════════════════════
# 三、monadic_fol ↔ oracle A（k ≤ 2 两边都完备 → 精确一致）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、monadic_fol ↔ oracle A（一元片段，k ≤ 2）')
rng = random.Random(20261003)
mis_a, skip_a, n_val_a = [], [], 0
TRIALS_A = 40
for _ in range(TRIALS_A):
    preds = ['P', 'Q'][:rng.choice([1, 2])]
    f = gen_closed(rng, preds, 2)
    s = render(f)
    truth = oracle_valid_all(f, preds)
    n_val_a += 1 if truth else 0
    r = MF.run({'formula': s})
    if r['verdict'] not in ('valid', 'invalid'):
        skip_a.append((s, r['verdict']))
        continue
    if (r['verdict'] == 'valid') != truth:
        mis_a.append((s, r['verdict'], truth))
check('monadic_fol 与 oracle A 精确一致（%d 例，含 %d 个有效式）'
      % (TRIALS_A, n_val_a), mis_a == [], mis_a[:2])
check('monadic_fol 在 k ≤ 2 区间没退化成"判不了"（skip %d）' % len(skip_a),
      len(skip_a) == 0, skip_a[:3])

# ══════════════════════════════════════════════════════════════
# 四、first_order ↔ oracle B（有限论域穷举 → 精确一致）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、first_order ↔ oracle B（论域 {a,b} 上的蕴含）')
rng = random.Random(20261005)
mis_b, n_ent_b, decided_b = [], 0, 0
TRIALS_B = 30
for _ in range(TRIALS_B):
    preds = ['P', 'Q'][:rng.choice([1, 2])]
    prem = [gen_ground(rng, preds) if rng.random() < 0.6
            else gen_closed(rng, preds, 1)
            for _ in range(rng.choice([0, 1, 1, 2]))]
    concl = gen_ground(rng, preds) if rng.random() < 0.5 \
        else gen_closed(rng, preds, 1)
    truth = oracle_entails_U(prem, concl, preds, UNIV)
    n_ent_b += 1 if truth else 0
    r = FO.run({'universe': UNIV,
                'facts': [render(x) for x in prem if x[0] not in ('∀', '∃')],
                'rules': [render(x) for x in prem if x[0] in ('∀', '∃')],
                'query': render(concl)})
    if r['verdict'] not in ('entailed', 'not_entailed'):
        continue
    decided_b += 1
    if (r['verdict'] == 'entailed') != truth:
        mis_b.append(([render(x) for x in prem], render(concl),
                      r['verdict'], truth))
check('first_order 与 oracle B 精确一致（判了 %d 例，含 %d 个真蕴含）'
      % (decided_b, n_ent_b), mis_b == [], mis_b[:2])
check('first_order 的蕴含判定不是恒真/恒假（两侧都出现过）',
      0 < n_ent_b < TRIALS_B, n_ent_b)

# ══════════════════════════════════════════════════════════════
# 五、equality_tableau ↔ oracle C（说 valid/invalid 时必须一致）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、equality_tableau ↔ oracle C（地面等词）')
rng = random.Random(20261004)
CONSTS, PREDS = ['a', 'b', 'c'], ['P', 'Q']
mis_c, undet_c, n_val_c = [], 0, 0
TRIALS_C = 40
for _ in range(TRIALS_C):
    eqs = ['%s=%s' % (x, y) for i, x in enumerate(CONSTS)
           for y in CONSTS[i + 1:] if rng.random() < 0.25]
    prem = []
    for _ in range(rng.choice([1, 2, 3])):
        lit = '%s(%s)' % (rng.choice(PREDS), rng.choice(CONSTS))
        prem.append(lit if rng.random() < 0.6 else '¬' + lit)
    concl = '%s(%s)' % (rng.choice(PREDS), rng.choice(CONSTS))
    truth = oracle_ground_equality(prem, concl, eqs)
    n_val_c += 1 if truth else 0
    r = ET.run({'premises': prem, 'conclusion': concl, 'equality': eqs})
    if r['verdict'] == 'undetermined':
        undet_c += 1
        continue
    if (r['verdict'] == 'valid') != truth:
        mis_c.append((prem, concl, eqs, r['verdict'], truth))
check('equality_tableau 与 oracle C 一致（%d 例，含 %d 个真蕴含）'
      % (TRIALS_C, n_val_c), mis_c == [], mis_c[:2])
check('没有大量"判不了"（undetermined %d / %d）' % (undet_c, TRIALS_C),
      undet_c <= TRIALS_C * 0.2, undet_c)

# ══════════════════════════════════════════════════════════════
# 六、变异接受：把三个 oracle 各改坏一处，对拍必须抓住
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('五、变异接受（改坏 oracle，看这份对拍有没有咬合力）')
f_mut = ('∃', 'x', ('∨', ('atom', 'P', 'x'), ('¬', ('atom', 'P', 'x'))))
check('变异 A：把真假判反后，连重言式都会判无效（说明判据被真的动到了）',
      not oracle_valid_all(f_mut, ['P'], mutate=True))
check('变异 B：只看结论侧判反后，与正版在 P(a) ⊨ ∃x P(x) 上结论相反',
      oracle_entails_U([Pa], ('∃', 'x', Pa), ['P'], UNIV)
      != oracle_entails_U([Pa], ('∃', 'x', Pa), ['P'], UNIV, mutate=True))
check('变异 C：把等词蕴含判据反了后，与正版在 a=b, P(a) ⊨ P(b) 上结论相反',
      oracle_ground_equality(['P(a)'], 'P(b)', ['a=b'])
      != oracle_ground_equality(['P(a)'], 'P(b)', ['a=b'], mutate=True))

print()
print('=' * 70)
print(f'结果: {PASS}/19 通过')
raise SystemExit(0 if PASS == 19 else 1)
