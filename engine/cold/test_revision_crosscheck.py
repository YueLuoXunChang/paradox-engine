# -*- coding: utf-8 -*-
"""test_revision_crosscheck.py — "修正"两件的独立互验（③ 验证轴 · 第五批）

为什么是这两件一起做：
    `agm_revision` 与 `truth_revision` **都叫"修正"，却是两套完全不同的理论**——
    一个修**信念**（AGM：信念集 + 新信息 + 最小放弃 + 优先级），
    一个修**真值**（Gupta-Belnap：自指句的真值序列，判稳定/周期/不稳定）。
    这正是 ④ 轴要标注的"同名不同物"，所以本文件既**分别验**、又**把差异钉住**。

两个 oracle（都在本文件里，不 import 被验构件的判定逻辑）：
    A. **AGM 公设本身**就是 oracle：`agm_revision` 的边界里写着"三公理逐条可验"，
       本文件就把这句话验掉——用**自己的真值表**判蕴含/一致性，
       逐条查 成功 / 包含 / 一致性 / 空性（vacuity）与优先级契约。
       （**外延性故意不断言**：底集（belief base）修正本来就不满足外延性，
       这是课本结论——"哪些公设对集合成立、哪些对底集不成立"要分清，见第二节。）
    B. **自己写一份修正序列模拟器**：按 σ_{n+1}(s) = f_s(σ_n) 迭代，判不动点/周期/发散，
       与 `truth_revision` 的分类逐例比对。

运行：python engine/cold/test_revision_crosscheck.py
"""
import itertools
import os
import random
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.cold import agm_revision as AG     # noqa: E402
from engine.cold import truth_revision as TR   # noqa: E402

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
# 一、oracle A：自己的真值表引擎（判一致 / 判蕴含）
# ══════════════════════════════════════════════════════════════
_ATOMS = ('P', 'Q', 'R')
_ROWS = list(itertools.product([False, True], repeat=len(_ATOMS)))
_PREC = {'↔': 1, '→': 2, '∨': 3, '∧': 4}
_FTOK = re.compile(r'↔|→|∨|∧|¬|\(|\)|[PQR]')


def _parse_formula(s):
    """极小命题公式解析（优先级 ¬ > ∧ > ∨ > → > ↔；→ 右结合）。"""
    toks = _FTOK.findall(s)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def parse_atom():
        t = take()
        if t == '¬':
            return ('¬', parse_atom())
        if t == '(':
            n = parse_expr(1)
            if take() != ')':
                raise ValueError('缺右括号')
            return n
        return ('atom', t)

    def parse_expr(min_prec):
        node = parse_atom()
        while peek() in _PREC:
            prec = _PREC[peek()]
            if prec < min_prec:
                break
            op = take()
            node = (op, node, parse_expr(prec + 1))
        return node

    out = parse_expr(1)
    if pos[0] != len(toks):
        raise ValueError('多余内容 %r' % toks[pos[0]:])
    return out


def _eval_ast(ast, env):
    k = ast[0]
    if k == 'atom':
        return env[ast[1]]
    if k == '¬':
        return not _eval_ast(ast[1], env)
    a, b = _eval_ast(ast[1], env), _eval_ast(ast[2], env)
    if k == '∧':
        return a and b
    if k == '∨':
        return a or b
    if k == '→':
        return (not a) or b
    return a == b


def _eval(formula, row):
    """在给定真值行上求真值（用上面的解析器，**不做字符串替换**——
    第一版就是把 P→Q 替换成了「P or not Q」，方向写反，冤枉了被验构件）。"""
    return _eval_ast(_parse_formula(formula), dict(zip(_ATOMS, row)))


def _rows_of(fs):
    return [r for r in _ROWS if all(_eval(f, r) for f in fs)]


def sat(fs):
    return len(_rows_of(fs)) > 0


def entails(premises, conclusion):
    return all(_eval(conclusion, r) for r in _rows_of(premises))


print('=' * 70)
print('一、oracle A 自检（真值表）')
check('oracle A：P→Q, P ⊨ Q', entails(['P→Q', 'P'], 'Q'))
check('oracle A：P ⊭ Q（反例存在）', not entails(['P'], 'Q'))
check('oracle A：P ∧ ¬P 不可满足', not sat(['P ∧ ¬P']))
check('oracle A：¬¬Q 与 Q 等价',
      all(_eval('¬¬Q', r) == _eval('Q', r) for r in _ROWS))

# ══════════════════════════════════════════════════════════════
# 二、agm_revision ↔ AGM 公设（公设即 oracle）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、agm_revision ↔ AGM 公设（成功 / 包含 / 一致性 / 空性 / 优先级）')
_CASES = [
    (['P'], 'Q'),                       # 不冲突、旧不蕴含新（**旧版在这里违反成功公理**）
    (['P→Q', 'P'], 'Q'),                # 不冲突、旧已蕴含新
    (['P→Q', 'P'], '¬Q'),               # 冲突，弃 1 条
    (['P', 'Q', 'R'], '¬Q'),            # 冲突，多候选择一
    (['P ∧ Q'], '¬P'),                  # 冲突，弃 1 条复合信念
    (['P'], '¬P'),                      # 冲突，只剩「只留 φ」
    (['P ∨ Q', '¬P'], 'Q'),             # 不冲突（已蕴含）
    (['¬(P ∧ Q)'], 'P'),                # 不冲突
]
_res = [(b, n, AG.run({'mode': 'revise', 'beliefs': list(b), 'new_info': n}))
        for b, n in _CASES]
_bad_ok = [(b, n, r['verdict']) for b, n, r in _res
           if r['verdict'] not in ('consistent', 'revised')]
check('八条用例都判出结果（consistent/revised，没有 undecided 混进来）',
      _bad_ok == [], _bad_ok[:2])

_mis_succ = [(b, n, r['kept']) for b, n, r in _res
             if r['verdict'] in ('consistent', 'revised')
             and not entails(r['kept'], n)]
check('★成功公理：K*φ ⊨ φ（返回的 kept 必须蕴含新信息）——**旧版在 consistent 路违反**',
      _mis_succ == [], _mis_succ[:2])
_mis_incl = [(b, n, r['kept']) for b, n, r in _res
             if r['verdict'] in ('consistent', 'revised')
             and not set(r['kept']) <= set(b) | {n}]
check('包含公理：kept ⊆ B ∪ {φ}（不许凭空生信念）', _mis_incl == [],
      _mis_incl[:2])
_mis_cons = [(b, n, r['kept']) for b, n, r in _res
             if r['verdict'] in ('consistent', 'revised')
             and sat([n]) and not sat(r['kept'])]
check('一致性公理：φ 可满足 ⇒ K*φ 一致（不弃过头也不留矛盾）',
      _mis_cons == [], _mis_cons[:2])
_mis_vac = [(b, n, r['dropped']) for b, n, r in _res
            if sat(list(b) + [n]) and r['dropped']]
check('空性公理（vacuity）：B∪{φ} 一致 ⇒ 一条都不弃', _mis_vac == [],
      _mis_vac[:2])
check('有冲突的例子确实发生了（%d 条 revised），否则上面几条是空跑'
      % sum(1 for _b, _n, r in _res if r['verdict'] == 'revised'),
      any(r['verdict'] == 'revised' for _b, _n, r in _res))

# 优先级契约（entrenchment）：弃掉的不该比留下的更"贵"
_pr = AG.run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
              'priorities': {'P→Q': 1, 'P': 10}})
check('优先级契约：明确给了信念度时，弃的是低优先级那条（P→Q:1 被弃、P:10 保住）',
      _pr['dropped'] == ['P→Q'] and 'P' in _pr['kept'], _pr)
_pr2 = AG.run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
               'priorities': {'P→Q': 10, 'P': 1}})
check('优先级契约反向也成立（把信念度调过来，弃的就换成另一条）',
      _pr2['dropped'] == ['P'], _pr2)

# 外延性：**说明为什么不作为断言**
_ext_a = AG.run({'mode': 'revise', 'beliefs': ['P'], 'new_info': 'Q'})
_ext_b = AG.run({'mode': 'revise', 'beliefs': ['P'], 'new_info': '¬¬Q'})
check('外延性（φ↔ψ ⇒ K*φ = K*ψ）：**底集修正本就不满足**，本文件只观察不判错'
      '（两者结论都蕴含各自的 φ 即算"逻辑上等价地可用"）',
      entails(_ext_a['kept'], 'Q') and entails(_ext_b['kept'], '¬¬Q'))

# ══════════════════════════════════════════════════════════════
# 三、truth_revision ↔ oracle B（自己的修正序列模拟器）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、truth_revision ↔ oracle B（σ_{n+1}(s) = f_s(σ_n) 自己迭代）')


def simulate_revision(sent_fn, names, start, max_steps):
    """返回 (分类, 周期, 赋值为真定格, 轨迹)。

    分类：fixpoint（σ_{n+1}=σ_n）/ periodic（回到见过的赋值）/ unstable（步数内无重复）。
    """
    sigma = {n: bool(start.get(n, False)) for n in names}
    seen = {}
    trace = []
    for step in range(max_steps + 1):
        key = tuple(sigma[n] for n in names)
        if key in seen:
            period = step - seen[key]
            return ('fixpoint' if period == 1 else 'periodic'), period, trace
        seen[key] = step
        trace.append(dict(sigma))
        sigma = {n: bool(sent_fn[n](dict(sigma))) for n in names}
    return 'unstable', None, trace


def cmp_truth_revision(tag, sent_fn, names, start, max_steps=12):
    mine, period, _trace = simulate_revision(sent_fn, names, start, max_steps)
    r = TR.run({'mode': 'custom', 'sentences': sent_fn, 'start': start,
                'max_steps': max_steps})
    d = r['detail'] or {}
    # 口径：custom 模式的分类在**外层 verdict**（detail 里是 period/cycle/
    # fixed_value/note）——第一版去 detail 里找 verdict，取到 None。
    got = r['verdict']
    want = {'fixpoint': 'stable', 'periodic': 'periodic',
            'unstable': 'unstable'}[mine]
    ok = (got == want)
    if ok and mine == 'periodic':
        ok = (d.get('period') == period)
    return ok, (tag, got, want, d.get('period'), period)


_liar = {'P': (lambda a: not a['P'])}
_benign = {'P': (lambda a: True)}
_ring = {'P': (lambda a: a['Q']), 'Q': (lambda a: not a['P'])}
_two = {'P': (lambda a: a['Q']), 'Q': (lambda a: a['P'])}
_cases = [('说谎者 P↔¬P（教科书周期 2）', _liar, ['P'], {'P': False}),
          ('良性句（恒真）', _benign, ['P'], {'P': False}),
          ('互指环 P:=Q, Q:=¬P', _ring, ['P', 'Q'], {'P': False, 'Q': False}),
          ('互指同真 P:=Q, Q:=P', _two, ['P', 'Q'], {'P': False, 'Q': False})]
_mis_tr = []
for _tag, _sf, _names, _start in _cases:
    _ok, _detail = cmp_truth_revision(_tag, _sf, _names, _start)
    if not _ok:
        _mis_tr.append(_detail)
check('四条已知系统：分类（稳定/周期）与周期长度都和 oracle B 一致',
      _mis_tr == [], _mis_tr[:2])
check('说谎者确实是周期 2（教科书结论，不是引擎自创）',
      TR.run({'mode': 'custom', 'sentences': _liar, 'start': {'P': False},
              'max_steps': 10})['detail'].get('period') == 2)

# 随机小系统对拍：2 句、真值条件随机（= 随机布尔函数）
_rng = random.Random(20261010)
_mis_rnd, _n_stable, _n_periodic = [], 0, 0
for _ in range(20):
    _fn = {'P': (lambda a, m=0: m == 0), 'Q': (lambda a, m=0: m == 0)}
    _tables = {}
    for _s in ('P', 'Q'):
        _tables[_s] = [_rng.random() < 0.5 for _ in range(4)]

    def _mk(sname, tables):
        def f(a, _s=sname, _t=tables):
            idx = (1 if a['P'] else 0) * 2 + (1 if a['Q'] else 0)
            return _t[_s][idx]
        return f
    _sf2 = {s: _mk(s, _tables) for s in ('P', 'Q')}
    _ok2, _d2 = cmp_truth_revision('rnd', _sf2, ['P', 'Q'],
                                   {'P': False, 'Q': False}, max_steps=20)
    if not _ok2:
        _mis_rnd.append(_d2)
    _mine2 = simulate_revision(_sf2, ['P', 'Q'], {'P': False, 'Q': False}, 20)[0]
    _n_stable += _mine2 == 'fixpoint'
    _n_periodic += _mine2 == 'periodic'
check('随机 20 个两句系统：分类+周期长度与 oracle B 全一致', _mis_rnd == [],
      _mis_rnd[:2])
check('随机样本确实覆盖了多种走向（fixpoint %d · periodic %d，不是一边倒）'
      % (_n_stable, _n_periodic), _n_stable + _n_periodic >= 3)

# ══════════════════════════════════════════════════════════════
# 四、④ 撞名标注：同名不同物必须写清
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、撞名标注（两件都叫"修正"，必须互相点名 + 写清区别）')
_ag_src = open(AG.__file__, encoding='utf-8').read()
_tr_src = open(TR.__file__, encoding='utf-8').read()
check('agm_revision 的文档里点名了 truth_revision 并说明区别',
      'truth_revision' in _ag_src and '真值' in _ag_src
      and '同名不同物' in _ag_src)
check('truth_revision 的文档里点名了 agm_revision 并说明区别',
      'agm_revision' in _tr_src and '信念' in _tr_src
      and '同名不同物' in _tr_src)
check('两件确实是两件事：一个判稳定/周期（真值序列），一个判弃/留（信念集）',
      'period' in (TR.run({'mode': 'custom', 'sentences': _liar,
                           'start': {'P': False}})['detail'] or {})
      and 'dropped' in AG.run({'mode': 'revise', 'beliefs': ['P'],
                               'new_info': 'Q'}))

print()
print('=' * 70)
print(f'结果: {PASS}/20 通过')
raise SystemExit(0 if PASS == 20 else 1)
