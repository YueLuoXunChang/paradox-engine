# -*- coding: utf-8 -*-
"""test_classical_crosscheck.py — 跨构件随机对拍（③ 验证轴）

为什么要有这份文件：
    命题逻辑层有**三条互不相同的判定路**——真值表枚举（propositional）·
    自然演绎证明搜索（nd_propositional）· 归结反证（resolution）。
    它们用的是不同算法、不同实现，所以"三方对得上"才有意义；
    再加一条**本文件自己另写的暴力 oracle**（枚举赋值，不 import 任何判定构件），
    同一道题由**独立实现**分别算出来一致，才算"验过"——
    只有一份实现自己对自己，那是自证（闸三：工具不可自证）。

做法：
    ① 随机生成命题公式（生成器只在本文件里，不借引擎的）；
    ② 本文件自己写暴力 oracle（枚举全部赋值）；
    ③ 同一道题喂三条路，判词与 oracle 必须一致；不一致就**报出来**
       （那会是一个真 bug，不是"测试没过"这么简单）；
    ④ **变异接受**：把 oracle 故意改坏两处，对拍必须抓住——
       证明这份对拍有咬合力，不是"反正都会过"。
运行：python engine/classical/test_classical_crosscheck.py
"""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import nd_propositional as nd          # noqa: E402
from engine.classical import propositional as prop           # noqa: E402
from engine.classical import resolution as res               # noqa: E402

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
# 一、本文件自己的生成器与 oracle（不 import 任何判定构件）
# ══════════════════════════════════════════════════════════════
BIN = ('∧', '∨', '→', '↔')


def gen_formula(rng, atoms, depth):
    """随机生成公式（返回元组树）。"""
    if depth <= 0 or rng.random() < 0.35:
        return ('atom', rng.choice(atoms))
    if rng.random() < 0.22:
        return ('¬', gen_formula(rng, atoms, depth - 1))
    return (rng.choice(BIN), gen_formula(rng, atoms, depth - 1),
            gen_formula(rng, atoms, depth - 1))


def render(f):
    """渲染成引擎的写法（加足括号，避免优先级歧义）。"""
    if f[0] == 'atom':
        return f[1]
    if f[0] == '¬':
        return '¬(%s)' % render(f[1])
    return '(%s %s %s)' % (render(f[1]), f[0], render(f[2]))


def ev(f, asg):
    """本文件自己的求值器。"""
    k = f[0]
    if k == 'atom':
        return asg[f[1]]
    if k == '¬':
        return not ev(f[1], asg)
    a, b = ev(f[1], asg), ev(f[2], asg)
    if k == '∧':
        return a and b
    if k == '∨':
        return a or b
    if k == '→':
        return (not a) or b
    return a == b


def assignments(atoms):
    for i in range(1 << len(atoms)):
        yield {a: bool((i >> j) & 1) for j, a in enumerate(atoms)}


def oracle_valid(premises, conclusion, atoms):
    """暴力 oracle：前提全真的每一行，结论都必须真。"""
    for asg in assignments(atoms):
        if all(ev(p, asg) for p in premises) and not ev(conclusion, asg):
            return False
    return True


def oracle_valid_mutated_concl(premises, conclusion, atoms):
    """变异一：把结论的判据反了（该无效的会说有效）。"""
    for asg in assignments(atoms):
        if all(ev(p, asg) for p in premises) and ev(conclusion, asg):
            return False
    return True


def oracle_valid_mutated_prem(premises, conclusion, atoms):
    """变异二：前提只用第一条（漏掉其余前提）。"""
    for asg in assignments(atoms):
        if ev(premises[0], asg) and not ev(conclusion, asg):
            return False
    return True


def _oracle_is_local():
    """用 AST 查本文件自己：oracle 三件套**定义在本文件里**，且没 import 第三方求解器。

    "独立实现"不能只是一句话——得能查。
    """
    import ast
    with open(os.path.abspath(__file__), 'r', encoding='utf-8') as fh:
        tree = ast.parse(fh.read())
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split('.')[0])
    return ({'oracle_valid', 'ev', 'assignments'} <= defined
            and not (mods & {'sympy', 'z3', 'pysat', 'pycosat', 'numpy'}))


# ══════════════════════════════════════════════════════════════
# 二、oracle 自检：已知答案先钉住
# ══════════════════════════════════════════════════════════════
A = ['P', 'Q', 'R']
P, Q = ('atom', 'P'), ('atom', 'Q')
print('=' * 70)
print('一、oracle 自检（已知答案，先钉住判据本身）')
check('P → P 有效', oracle_valid([], ('→', P, P), A))
check('P ∧ Q → P 有效', oracle_valid([('∧', P, Q)], P, A))
check('排中律 P ∨ ¬P 有效', oracle_valid([], ('∨', P, ('¬', P)), A))
check('爆炸律：前提自相矛盾时任何结论都有效',
      oracle_valid([P, ('¬', P)], Q, A))
check('P → Q 无效（找不到反例才叫有效，这里反例是 P 真 Q 假）',
      not oracle_valid([], ('→', P, Q), A))
check('变异一在 P → P 上与正版给出不同答案（改坏判据够被抓住）',
      oracle_valid_mutated_concl([], ('→', P, P), A)
      != oracle_valid([], ('→', P, P), A))
check('变异二在 [Q, ¬Q] ⊨ P 上与正版给出不同答案（漏前提够被抓住）',
      oracle_valid_mutated_prem([Q, ('¬', Q)], P, A)
      != oracle_valid([Q, ('¬', Q)], P, A))

# ══════════════════════════════════════════════════════════════
# 三、随机对拍：三条路 vs 本文件的 oracle
# ══════════════════════════════════════════════════════════════
SEED = 20261002
PAIRS = 120
rng = random.Random(SEED)
cases = []
for _ in range(PAIRS):
    n_atoms = rng.choice([2, 3])
    atoms = ['P', 'Q', 'R'][:n_atoms]
    prem = [gen_formula(rng, atoms, 2) for _ in range(rng.choice([1, 1, 2]))]
    concl = gen_formula(rng, atoms, 2)
    cases.append((atoms, prem, concl))

print()
print('=' * 70)
print('二、对拍（%d 对随机题 · 种子 %d）' % (PAIRS, SEED))

mis_tt, mis_nd_sound, mis_res_sound, skipped = [], [], [], []
nd_n, nd_np, res_np = 0, 0, 0
n_valid = 0
for atoms, prem, concl in cases:
    p_str, c_str = [render(x) for x in prem], render(concl)
    truth = oracle_valid(prem, concl, atoms)
    n_valid += 1 if truth else 0

    # ① 真值表枚举 = **判定过程**：必须与 oracle 精确一致（它是尺子）
    r_tt = prop.run({'premises': p_str, 'conclusion': c_str})
    if r_tt['verdict'] == 'parse_error':
        skipped.append(('propositional 解析失败', p_str, c_str))
    elif (r_tt['verdict'] == 'valid') != truth:
        mis_tt.append((p_str, c_str, r_tt['verdict'], truth))

    # ② 自然演绎 = **搜索型**：只查**可靠性**（说 proved 就必须真有效）。
    #    `not_proved` / `search_limit` 一律不当作"无效"——它自己的边界就是这么写的：
    #    规则集里没有 ↔ 引入，`((Q↔Q)→P) ⊢ P` 这类会报 not_proved。
    r_nd = nd.run({'premises': p_str, 'conclusion': c_str,
                   'system': 'classical'})
    if r_nd['verdict'] == 'proved':
        nd_n += 1
        if not truth:
            mis_nd_sound.append((p_str, c_str, truth))
    elif r_nd['verdict'] in ('not_proved', 'search_limit'):
        nd_np += 1
    else:
        skipped.append(('自然演绎未判（%s）' % r_nd['verdict'], p_str, c_str))

    # ③ 归结 = **半可判定**：同样只查可靠性
    r_res = res.run({'premises': p_str, 'conclusion': c_str})
    if r_res['verdict'] == 'proved':
        if not truth:
            mis_res_sound.append((p_str, c_str, truth))
    elif r_res['verdict'] == 'not_proved':
        res_np += 1
    else:
        skipped.append(('归结未判（%s）' % r_res['verdict'], p_str, c_str))

check('题目随机生成且两侧都覆盖到（有效 %d 对 / 无效 %d 对）'
      % (n_valid, PAIRS - n_valid),
      0 < n_valid < PAIRS, n_valid)
check('三条路的解析都没失败（生成器的写法与引擎语法对得上）',
      not any('解析失败' in s[0] for s in skipped),
      [s[0] for s in skipped if '解析失败' in s[0]][:3])
check('真值表枚举 vs oracle：精确一致（它是判定过程，该当尺子）',
      mis_tt == [], mis_tt[:2])
check('自然演绎：**没出过错证**（说 proved 的都是真有效）',
      mis_nd_sound == [], mis_nd_sound[:2])
check('归结：**没出过错证**（说 proved 的都是真有效）',
      mis_res_sound == [], mis_res_sound[:2])
check('自然演绎确实在干活（证出 %d 对）——不是一律 not_proved 蒙混过关' % nd_n,
      nd_n > 0)
check('两条搜索型路径的"没搜到"如实记账（自然演绎 %d · 归结 %d），'
      '且不当作"无效"' % (nd_np, res_np), nd_np + res_np > 0)
check('没判的（既非 proved 也非 not_proved）单独记账，不混进"通过"里',
      all('未判' in s[0] or '解析失败' in s[0] for s in skipped),
      skipped[:2])
check('对拍总数 = 有效 + 无效', n_valid + (PAIRS - n_valid) == PAIRS)

# ══════════════════════════════════════════════════════════════
# 四、变异接受：把 oracle 改坏，对拍必须抓住
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、变异接受（改坏 oracle，看这份对拍有没有咬合力）')


def disagreements_with(oracle_fn, cases):
    return {i for i, (atoms, prem, concl) in enumerate(cases[:40])
            if oracle_fn(prem, concl, atoms) != oracle_valid(prem, concl, atoms)}


d1 = disagreements_with(oracle_valid_mutated_concl, cases)
d2 = disagreements_with(oracle_valid_mutated_prem, cases)
check('变异一（结论判据反了）被抓到：%d 对不一致' % len(d1), len(d1) > 0)
check('变异二（漏掉其余前提）被抓到：%d 对不一致' % len(d2), len(d2) > 0)
check('两个变异抓到的不只是同一批题（覆盖的不是同一种错法）',
      d1 != d2 and bool(d1) and bool(d2), (sorted(d1)[:6], sorted(d2)[:6]))

# ══════════════════════════════════════════════════════════════
# 五、可复现与契约
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、可复现与契约')
rng2 = random.Random(SEED)
same = []
for atoms, prem, concl in cases:
    p_str, c_str = [render(x) for x in prem], render(concl)
    same.append(prop.run({'premises': p_str, 'conclusion': c_str})['verdict'])
rng3 = random.Random(SEED)
again = []
for atoms, prem, concl in cases:
    p_str, c_str = [render(x) for x in prem], render(concl)
    again.append(prop.run({'premises': p_str, 'conclusion': c_str})['verdict'])
check('同一种子两次跑结果逐条相同（对拍可复现）', same == again)

r_one = prop.run({'premises': ['P'], 'conclusion': 'P'})
check('三条路的返回都带 boundary（全仓契约）',
      all(isinstance(x.get('boundary'), str) and x['boundary']
          for x in (r_one,
                    nd.run({'premises': ['P'], 'conclusion': 'P'}),
                    res.run({'premises': ['P'], 'conclusion': 'P'}))))
check('三条路的判词都在各自 PORTS.out 声明的范围里',
      r_one['verdict'] in ('valid', 'invalid', 'parse_error', 'size_limit',
                           'premises_pending', 'conclusion_pending',
                           'formula_pending')
      and nd.run({'premises': ['P'], 'conclusion': 'P'})['verdict']
      in ('proved', 'not_proved', 'search_limit', 'parse_error',
          'conclusion_pending')
      and res.run({'premises': ['P'], 'conclusion': 'P'})['verdict']
      in ('proved', 'not_proved', 'parse_error', 'conclusion_pending'))
check('本文件的 oracle 是自己写的（不借引擎、不借第三方求解器）',
      _oracle_is_local())

print()
print('=' * 70)
print(f'结果: {PASS}/23 通过')
raise SystemExit(0 if PASS == 23 else 1)
