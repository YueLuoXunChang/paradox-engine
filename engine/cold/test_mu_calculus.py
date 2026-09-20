# -*- coding: utf-8 -*-
"""
test_mu_calculus.py — 正式测试：模态 μ 演算（不动点逻辑）
================================================================
用例依据：Kozen 1983 的 μ 演算语义（最小/最大不动点）、Knaster-Tarski 不动点定理、
Emerson & Jutla 的模型检查与交替深度。五件事分开测：

  ① **不动点算对没有**：μ 从空集往上、ν 从全集往下——同一式子两个解、留痕步数与
     手推距离对得上、嵌套不动点也对；
  ② **与 CTL 构件逐状态对拍**（两条独立实现）：本构件把 CTL 公式翻成 μ 式子再求值，
     CTL 构件走它自己的不动点标记算法——同一结构同一公式，两边的"哪些状态成立"
     必须一模一样（含死锁状态上的约定）；
  ③ **与图算法对拍**（**不用不动点迭代**的另一条路）：EF 用反向 BFS、AG 用正向可达、
     AF/EG 用 SCC 找环——随机结构上逐状态比对；
  ④ **交替式子**：E[GF p] = νZ.μY.(<>(p&Z) | <>Y)（"沿某条无限路 p 无穷多次出现"，
     要 ν 套 μ 才写得出来）与"能走到环上的 p 状态"这条独立判据对拍；
  ⑤ **纪律与边界**：非单调（μX.!X）诚实拦下并摆出振荡过程、重绑/空绑定拦下、
     词表、结构合法性、状态上限、边界声明写出处。

运行：python engine/cold/test_mu_calculus.py
"""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import model_check as ctl          # noqa: E402
from engine.cold import mu_calculus as mc                # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def ev(formula, struct, **kw):
    return mc.run(dict(struct, mode='evaluate', formula=formula, **kw))


# ══════════════════════════════════════════════════════════════
# 一、另写一套图算法（不用不动点迭代）当第二种口径
# ══════════════════════════════════════════════════════════════

def _succ(states, trans):
    m = {s: [] for s in states}
    for e in trans:
        m[e[0]].append(e[1])
    return m


def _pred(states, trans):
    m = {s: [] for s in states}
    for e in trans:
        m[e[1]].append(e[0])
    return m


def _closure(edges, start):
    """从 start 出发沿 edges 能走到的全部（含自身）。"""
    seen, stack = set(start), list(start)
    while stack:
        x = stack.pop()
        for y in edges.get(x, ()):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen


def _on_cycle(states, m, allowed):
    """allowed 里"能沿着 allowed 走回自己（≥1 步）"的状态——即落在环上的。"""
    out = set()
    for t in allowed:
        seen, stack = set(), list(m[t])
        hit = False
        while stack:
            x = stack.pop()
            if x == t:
                hit = True
                break
            if x in seen or x not in allowed:
                continue
            seen.add(x)
            stack.extend(m[x])
        if hit:
            out.add(t)
    return out


def _closure_back(edges, start):
    """**反向**：沿给定边能走到 start 的那些状态（含 start 自身）。
    注意方向——"能回到环上"要用反向闭包，别再写成正向（写反了会多算一堆状态）。"""
    pred = {}
    for a, b in edges:
        pred.setdefault(b, []).append(a)
    seen, stack = set(start), list(start)
    while stack:
        x = stack.pop()
        for y in pred.get(x, ()):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen


def oracle(op, atom, struct):
    """EF/AG/AF/EG 的图算法口径。"""
    states, trans, labels = struct['states'], struct['transitions'], \
        struct['labels']
    m = _succ(states, trans)
    P = {s for s in states if atom in labels.get(s, ())}
    if op == 'EF':
        # 能走到 p（沿**任意**边反着走）
        return set(_closure(_pred(states, trans), P))
    if op == 'AG':
        # 从 s 出发能到达的都在 p 里
        return {s for s in states if _closure(m, [s]) <= P}
    if op == 'AF':
        # s 不在 AF p ⟺ s 能沿 ¬p 走到 ¬p 里的一个环
        notp = set(states) - P
        cyc = _on_cycle(states, m, notp)
        neg_edges = [(e[0], e[1]) for e in trans
                     if e[0] in notp and e[1] in notp]
        return set(states) - _closure_back(neg_edges, cyc)
    if op == 'EG':
        # s 在 EG p ⟺ s ∈ p 且 s 能沿 p 内部走到 p 里的一个环
        cyc = _on_cycle(states, m, P)
        p_edges = [(e[0], e[1]) for e in trans if e[0] in P and e[1] in P]
        return _closure_back(p_edges, cyc) & P
    raise ValueError(op)


def gf_oracle(struct):
    """E[GF p]：能走到「落在环上的 p 状态」（p 无穷多次出现）。"""
    states, trans, labels = struct['states'], struct['transitions'], \
        struct['labels']
    m = _succ(states, trans)
    P = {s for s in states if 'p' in labels.get(s, ())}
    targets = P & _on_cycle(states, m, set(states))
    return set(_closure(_pred(states, trans), targets))


def rnd_struct(rng, n=None):
    n = n or rng.randint(2, 5)
    states = ['s%d' % i for i in range(n)]
    trans = []
    for s in states:
        for t in rng.sample(states, rng.randint(0, min(3, n))):
            trans.append([s, t])
    labels = {}
    for s in states:
        ps = [a for a in ('p', 'q') if rng.random() < 0.45]
        if ps:
            labels[s] = ps
    return {'states': states, 'transitions': trans, 'labels': labels}


# ══════════════════════════════════════════════════════════════
# 二、固定结构
# ══════════════════════════════════════════════════════════════
print('=' * 70)
print('模态 μ 演算 · 正式测试')
print('=' * 70)

CHAIN = {'states': ['s0', 's1', 's2', 's3', 's4'],
         'transitions': [['s0', 's1'], ['s1', 's2'], ['s2', 's3'],
                         ['s3', 's4']],
         'labels': {'s4': ['p']}}
CYC = {'states': ['a', 'b', 'c'],
       'transitions': [['a', 'b'], ['b', 'a'], ['a', 'c'], ['c', 'c']],
       'labels': {'a': ['p'], 'b': ['p']}}

# ── 三、不动点：μ / ν 的差别与留痕
r = ev('μX.(p | <>X)', CHAIN)
check('EF p（μX.(p ∨ <>X)）在链上处处成立', r['holds_in'] == CHAIN['states'], r)
check('★留痕：链上 EF 迭代 5 轮、每轮多大 [0,1,2,3,4,5,5]',
      r['fixpoints'] and r['fixpoints'][0]['kind'] == 'μ'
      and r['fixpoints'][0]['steps'] == 5
      and r['fixpoints'][0]['sizes'] == [0, 1, 2, 3, 4, 5, 5], r['fixpoints'])
check('μX.(p ∨ X) = p（同一个式子，最小解只要 p）',
      ev('μX.(p | X)', CHAIN)['holds_in'] == ['s4'])
check('νX.(p ∨ X) = 全部状态（最大解容得下一切）',
      ev('νX.(p | X)', CHAIN)['holds_in'] == CHAIN['states'])
check('μX.(p ∧ X) = ∅（最小解从空集出发永远得不到 p）',
      ev('μX.(p & X)', CHAIN)['holds_in'] == [])
check('νX.(p ∧ X) = p（最大解就是 p）',
      ev('νX.(p & X)', CHAIN)['holds_in'] == ['s4'])
r = ev('νX.(p & <>X)', CHAIN)
check('EG p 在只到 s4 就断的链上没有状态成立（EG 要无限路）',
      r['holds_in'] == [] and r['fixpoints'][0]['kind'] == 'ν', r)
check('μX.(p | []X) = AF p：链上处处成立（死锁处全称空真）',
      ev('μX.(p | []X)', CHAIN)['holds_in'] == CHAIN['states'])
check('νX.(p & []X) = AG p：链上只有 s4（别处都能走到非 p）',
      ev('νX.(p & []X)', CHAIN)['holds_in'] == ['s4'])
check('EG p 在 a↔b 环上成立、c 进不来',
      ev('νX.(p & <>X)', CYC)['holds_in'] == ['a', 'b'])
check('AF p 在 a↔b 环上成立、c（自环且非 p）不成立',
      ev('μX.(p | []X)', CYC)['holds_in'] == ['a', 'b'])
check('AG p 在有 a→c 的图上不成立（c 非 p 可达）',
      ev('νX.(p & []X)', CYC)['holds_in'] == [])
check('原子/真假/蕴含的基本语义：⊤ 处处、⊥ 无处',
      ev('⊤', CHAIN)['holds_in'] == CHAIN['states']
      and ev('⊥', CHAIN)['holds_in'] == [])
check('蕴含按经典语义：p -> q 在无 q 的结构上只在 ¬p 处成立',
      ev('p -> q', CHAIN)['holds_in'] == ['s0', 's1', 's2', 's3'])
check('check 模式只看 init 给的状态子集',
      mc.run(dict(CHAIN, mode='check', formula='νX.(p & []X)',
                  init=['s4', 's0']))['verdict'] == 'fails'
      and mc.run(dict(CHAIN, mode='check', formula='νX.(p & []X)',
                      init=['s4']))['verdict'] == 'holds')

# ── 四、与 CTL 构件逐状态对拍（两条独立实现）
CTL_CASES = [('EF p', CHAIN), ('AF p', CHAIN), ('EG p', CHAIN),
             ('AG p', CHAIN), ('EX p', CHAIN), ('AX p', CHAIN),
             ('E[p U q]', CHAIN), ('A[p U q]', CHAIN),
             ('EF p', CYC), ('AG !(p & q)', CYC), ('EG p', CYC),
             ('A[p U !p]', CYC), ('EX EF p', CYC), ('AG AF p', CYC),
             ('!(EF p)', CYC), ('EX p -> AX p', CYC)]
bad = []
for f, st in CTL_CASES:
    mine = mc.run(dict(st, mode='ctl', ctl=f))
    ref = ctl.run(dict(st, formula=f, init=st['states']))
    if mine['verdict'] != 'evaluated' or \
            sorted(mine['holds_in']) != sorted(ref['holds_in']):
        bad.append((f, sorted(mine['holds_in'] if mine['model'] is None
                              else mine['holds_in']),
                    sorted(ref['holds_in'])))
check('★16 条 CTL 公式与 CTL 构件逐状态一致（两条独立实现）', not bad, bad)
check('★CTL 翻译表写对：EF p → μX1.(p | <>X1)、AG p → νX1.(p & []X1)',
      mc.run(dict(CHAIN, mode='ctl', ctl='EF p'))['translation']
      == 'μX1.(p | <>X1)'
      and mc.run(dict(CHAIN, mode='ctl', ctl='AG p'))['translation']
      == 'νX1.(p & []X1)'
      and mc.run(dict(CHAIN, mode='ctl',
                      ctl='E[p U q]'))['translation']
      == 'μX1.(q | (p & <>X1))')
check('★翻译结果能当 μ 式子直接粘贴回来用（翻译 → 再求值同一结论）',
      mc.run(dict(CHAIN, mode='evaluate',
                  formula=mc.run(dict(CHAIN, mode='ctl',
                                      ctl='AF p'))['translation']))['holds_in']
      == mc.run(dict(CHAIN, mode='ctl', ctl='AF p'))['holds_in'])

# ── 五、与图算法对拍（随机结构，另一条实现路径）
rng = random.Random(20260920)
bad2 = []
for _ in range(40):
    st = rnd_struct(rng)
    for op, f in (('EF', 'μX.(p | <>X)'), ('AG', 'νX.(p & []X)'),
                  ('AF', 'μX.(p | []X)'), ('EG', 'νX.(p & <>X)')):
        got = set(ev(f, st)['holds_in'])
        want = oracle(op, 'p', st)
        if got != want:
            bad2.append((op, st, sorted(got), sorted(want)))
check('★40 个随机结构 × 4 个算子与图算法（BFS/可达/SCC）逐状态一致',
      not bad2, bad2[:2])
bad3 = []
for _ in range(40):
    st = rnd_struct(rng)
    got = set(ev('νZ.μY.(<>(p & Z) | <>Y)', st)['holds_in'])
    want = gf_oracle(st)
    if got != want:
        bad3.append((st, sorted(got), sorted(want)))
check('★E[GF p]（ν 套 μ 的交替式）与"能走到环上的 p"独立判据一致',
      not bad3, bad3[:2])

# ── 六、多动作与空后继约定
MA = {'states': ['x', 'y'], 'transitions': [['x', 'y', 'a'], ['y', 'y', 'b']],
      'labels': {'y': ['q']}}
check('<a>q 只看动作 a 的边（x 有 a 边到 y）', ev('<a>q', MA)['holds_in'] == ['x'])
check('<b>q 只看动作 b 的边', ev('<b>q', MA)['holds_in'] == ['y'])
check('[b]q 在 x 也成立（x 没有 b 后继——全称算子空真，与 CTL 构件约定一致）',
      ev('[b]q', MA)['holds_in'] == ['x', 'y'])
check('<>/[a] 与 <a>/[b] 在多动作结构上给出不同结果（不是通用后继）',
      ev('<b>q', MA)['holds_in'] != ev('<>q', MA)['holds_in'])

# ── 七、compare：两条式子在这个系统上是不是同一集合
r = mc.run(dict(CHAIN, mode='compare', c1='μX.(p | <>X)',
                c2='μX.(q | <>X)'))
check('compare：EF p 与 EF q 在只有 s4 带 p 的链上不同，并点出差异状态',
      r['verdict'] == 'different'
      and r['compare']['only_in_c1'] == CHAIN['states']
      and r['compare']['only_in_c2'] == [], r['compare'])
r = mc.run(dict(CHAIN, mode='compare', c1='μX.(p | <>X)',
                c2='p | <>μX.(p | <>X)'))
check('compare：展开一步与不展开在这个系统上一样（不动点的解性质）',
      r['verdict'] == 'same', r['compare'])

# ── 八、纪律与边界
V = ('evaluated', 'holds', 'fails', 'same', 'different', 'parse_error',
     'input_pending', 'non_monotone', 'size_limit', 'internal_error')
seen = set()
for inp in [dict(CHAIN, mode='evaluate', formula='μX.(p | <>X)'),
            dict(CHAIN, mode='check', formula='p', init=['s4']),
            dict(CHAIN, mode='evaluate', formula='μX.!X'),
            dict(CHAIN, mode='evaluate', formula='p q'),
            {'mode': 'evaluate', 'formula': 'p'},
            dict(CHAIN, mode='evaluate', formula='μX.p'),
            dict(CHAIN, mode='evaluate', formula='μX.(p X)'),
            dict(CHAIN, mode='evaluate', formula='νY.μX.(X & Y)'),
            {'mode': 'evaluate', 'formula': 'p', 'states': ['a'] * 3},
            {'mode': 'evaluate', 'formula': 'p', 'states': ['a'],
             'transitions': [['a', 'zz']]},
            mc.run and {'mode': 'evaluate', 'formula': 'p',
                        'states': ['a'], 'labels': {'zz': ['p']}}]:
    seen.add(mc.run(inp)['verdict'])
check('所有判定都落在文档写明的词表里', seen <= set(V), seen)

r = ev('μX.!X', CHAIN)
check('★非单调（μX.!X）→ non_monotone，并把迭代振荡过程摆出来',
      r['verdict'] == 'non_monotone' and '迭代过程' in r['boundary']
      and '→' in r['boundary'], r['boundary'][:60])
check('重绑变量（遮蔽）→ parse_error（不做遮蔽，免得看错作用域）',
      mc.run(dict(CHAIN, mode='evaluate',
                  formula='μX.(X & νX.X)'))['verdict'] == 'parse_error')
check('空绑定（μX.p：绑了没用）→ parse_error（多半是变量名写错）',
      mc.run(dict(CHAIN, mode='evaluate',
                  formula='μX.p'))['verdict'] == 'parse_error')
check('写坏的公式 → parse_error（不猜）',
      mc.run(dict(CHAIN, mode='evaluate', formula='μX'))['verdict']
      == 'parse_error'
      and mc.run(dict(CHAIN, mode='evaluate', formula='<>'))['verdict']
      == 'parse_error')
check('缺结构/缺公式 → input_pending（诚实拦截）',
      mc.run({'mode': 'evaluate', 'formula': 'p'})['verdict'] == 'input_pending'
      and mc.run(dict(CHAIN, mode='evaluate'))['verdict'] == 'input_pending'
      and mc.run({'mode': 'ctl', 'states': CHAIN['states']})['verdict']
      == 'input_pending')
check('迁移两端必须是已声明状态 / labels 里不许出现未声明状态'
      '（结构类问题一律 input_pending，与 CTL 构件口径一致）',
      mc.run({'mode': 'evaluate', 'formula': 'p', 'states': ['a'],
              'transitions': [['a', 'zz']]})['verdict'] == 'input_pending'
      and mc.run({'mode': 'evaluate', 'formula': 'p', 'states': ['a'],
                  'labels': {'zz': ['p']}})['verdict'] == 'input_pending'
      and mc.run({'mode': 'evaluate', 'formula': 'p', 'states': ['a'],
                  'transitions': [['a']]})['verdict'] == 'input_pending')
check('状态名重复 → input_pending（结构不合法不硬算）',
      mc.run({'mode': 'evaluate', 'formula': 'p',
              'states': ['a', 'a']})['verdict'] == 'input_pending')
check('状态数超上限 → size_limit（不硬跑）',
      mc.run({'mode': 'evaluate', 'formula': 'p',
              'states': ['s%d' % i for i in range(mc.MAX_STATES + 1)]})
      ['verdict'] == 'size_limit')
b = mc.run(dict(CHAIN, mode='evaluate', formula='p'))['boundary']
check('边界声明标出处与借鉴区（Kozen / Knaster-Tarski / Emerson-Jutla / 借鉴区）',
      'Kozen 1983' in b and 'Knaster-Tarski' in b and 'Emerson' in b
      and '借鉴区' in b)
check('边界声明写清能力圈：只做给定结构上的 model checking、不做可满足性判定',
      'model checking' in b and '可满足性' in b and '不碰' in b)
check('边界声明写清非单调会被拦下、状态数有上限', '正出现' in b and 'size_limit' in b)
check('边界声明写清"只诊断不决策"', '只诊断不决策' in b)

print('=' * 70)
print(f"结果: {PASS}/39 通过")
raise SystemExit(0 if PASS == 39 else 1)
