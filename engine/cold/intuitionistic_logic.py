# -*- coding: utf-8 -*-
"""
intuitionistic_logic.py — 直觉主义逻辑 · 构造性立场构件（第 3 层冷门 3.5）
==========================================================================
概念来源：**外部经典共识**——直觉主义逻辑（intuitionistic logic，Brouwer
的构造主义纲领 / Heyting 的形式化 / Kripke 1959 语义 / BHK 解释）。本构件
为借鉴实现（落落三问：借什么=无排中律的构造性判定与 Kripke 反模型；
为什么=T9 学科建模里"没构造出来就不算真"的立场需要一个能跑的实现——
经典层判"真"的公式，直觉主义层未必成立；怎么记账=标注来源归借鉴区）。
详规：第 3 层冷门详规 §五（构件 3.5 直觉主义逻辑：构造性立场，备用）

本构件做什么（一句话）：
    给"这个公式在构造性立场下成立吗"一个可跑答案——三个能力：
    ① **Kripke 模型求值**（mode='evaluate'）：给定 Kripke 模型（节点 +
       偏序 + 单调赋值），算公式在某节点的真值（直觉主义联结词语义：
       ¬A 要求"所有后继都不 A"，A→B 要求"所有后继里 A 蕴含 B"）；
    ② **反模型搜索**（mode='countermodel'）：自动搜小模型找反例——
       找到 → 该公式**非直觉主义有效**（给反模型，白箱）；
       在完备界内搜不到 → 判定有效；超出算力则诚实报"限内未找到"
       （≠ 有效）；
    ③ **经典 vs 直觉主义对照**（mode='compare'）：标志性公式两系统并排
       判定（排中律 / 双重否定消去 / Peirce 律 / De Morgan 一侧……）——
       一眼看清"哪些经典定理是构造性立场不认的"。

与经典层的差别（为什么算冷门）：
    - 经典逻辑：P∨¬P 恒真（排中律）、¬¬P→P 可用（双重否定消去）；
    - 直觉主义：**没构造出来就不算真**——上述两条都不成立，需要额外
      构造证据（BHK 解释：证明 = 构造；∨ 真必须知道是哪一边）。

诚实边界：
    - 反模型搜索**完备界 = 2^n 个节点**（n = 原子数，直觉主义命题逻辑的
      有限模型性质）：界内搜不到反模型 ⇒ 判定"非有效"为假即**有效**；
      超出界（n 较大）只做有界搜索，报 'not_found_in_limit'——**不冒充
      有效判定**；
    - Kripke 求值要求赋值**单调**（沿偏序只增不减）——非单调赋值不是
      合法直觉主义模型，诚实报 model_invalid 而非硬算；
    - 构造性证据（Curry-Howard 的"证明即程序"）不在本构件重复实现——
      见 engine/classical/stlc.py（类型 = 命题，程序 = 证明）与
      engine/classical/nd_propositional.py（system='intuitionistic'）。

统一接口：
    run(inputs: dict) -> dict
    输入（mode='evaluate'）:
        formula: str；worlds: list；order: list[tuple]；valuation: dict
        （原子 → 为真的节点列表）；world: str（在哪求值，缺省取首个极小点）
    输入（mode='countermodel'）:
        formula: str；max_worlds: int?（默认按 2^n 完备界）
    输入（mode='compare'）:
        formulas: list[str]?（缺省用标志性公式表）
    输出:
        verdict: str——'evaluated'|'refuted'|'valid'|'not_found_in_limit'
                        |'model_invalid'|'input_pending'|'size_limit'
                        |'parse_pending'|'compared'
        value: bool|None——求值结果
        countermodel: dict|None——反模型（节点/序/赋值/反例节点）
        comparison: list[dict]——两系统对照表
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'formula': 'str?', 'worlds': 'list?',
           'order': 'list?', 'valuation': 'dict?', 'world': 'str?',
           'formulas': 'list?', 'max_worlds': 'int?'},
    'out': {'verdict': 'str', 'value': 'bool?', 'countermodel': 'dict?',
            'comparison': 'list', 'boundary': 'str'},
}

import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 标志性公式（经典成立 / 直觉主义不成立 的对照用）
LANDMARKS = [
    ('排中律 P∨¬P', 'P∨¬P'),
    ('双重否定消去 ¬¬P→P', '¬¬P→P'),
    ('Peirce 律 ((P→Q)→P)→P', '((P→Q)→P)→P'),
    ('De Morgan ¬(P∧Q)→(¬P∨¬Q)', '¬(P∧Q)→(¬P∨¬Q)'),
    ('De Morgan ¬(P∨Q)→(¬P∧¬Q)', '¬(P∨Q)→(¬P∧¬Q)'),
    ('爆炸 P→(Q→P)', 'P→(Q→P)'),
]


def _pl():
    """取经典命题逻辑（复用其解析器与 ND 判定）。"""
    try:
        from engine.classical import propositional as pl
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        import propositional as pl
    return pl


def _nd():
    """取自然演绎（intuitionistic 系统判定用）。"""
    try:
        from engine.classical import nd_propositional as nd
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        import nd_propositional as nd
    return nd


def _atoms_of_ast(ast):
    out = []

    def walk(n):
        if n[0] == 'atom':
            if n[1] not in out:
                out.append(n[1])
        elif n[0] == '¬':
            walk(n[1])
        else:
            walk(n[1])
            walk(n[2])

    walk(ast)
    return out


def _holds(ast, world, order_le, val):
    """
    直觉主义 Kripke 语义求值：公式 ast 在节点 world 是否为真。
    order_le: dict 节点 → 其后继集合（含自身）；val: 原子 → 真节点集合。
    """
    kind = ast[0]
    if kind == 'atom':
        return world in val.get(ast[1], ())
    if kind == '¬':
        return all(not _holds(ast[1], v, order_le, val)
                   for v in order_le[world])
    if kind == '∧':
        return (_holds(ast[1], world, order_le, val)
                and _holds(ast[2], world, order_le, val))
    if kind == '∨':
        return (_holds(ast[1], world, order_le, val)
                or _holds(ast[2], world, order_le, val))
    if kind == '→':
        return all((not _holds(ast[1], v, order_le, val))
                   or _holds(ast[2], v, order_le, val)
                   for v in order_le[world])
    raise ValueError(f'未知联结词 {kind!r}')


def _successors(worlds, order):
    """由偏序对构造每个节点的后继集合（含自身）。"""
    le = {w: {w} for w in worlds}
    for a, b in order:
        if a in le and b in le:
            le[a].add(b)
    # 传递闭包
    changed = True
    while changed:
        changed = False
        for w in worlds:
            new = set()
            for v in le[w]:
                new |= le[v]
            if not new <= le[w]:
                le[w] |= new
                changed = True
    return le


def _monotone(worlds, le, val):
    """检查赋值单调：w 为真且 w ≤ v ⇒ v 为真。"""
    for atom, true_worlds in val.items():
        ts = set(true_worlds)
        for w in ts:
            if not le[w] <= ts:
                return False, atom, w
    return True, None, None


def _evaluate(formula, worlds, order, valuation, world=None):
    pl = _pl()
    if not formula or not worlds:
        return {'verdict': 'input_pending', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': 'mode=evaluate 需 formula + worlds（节点集）+ '
                            'order + valuation——诚实拦截，不硬算'}
    try:
        ast = pl.parse(formula)
    except Exception as e:  # noqa: BLE001——解析失败即诚实报告
        return {'verdict': 'parse_pending', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': f'公式解析失败：{e}——诚实拦截'}
    le = _successors(worlds, order or [])
    val = {a: list(v) for a, v in (valuation or {}).items()}
    if world is None:
        world = worlds[0]
    if world not in le:
        return {'verdict': 'input_pending', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': f'节点 {world!r} 不在 worlds 中——诚实拦截'}
    ok, atom, w = _monotone(worlds, le, val)
    if not ok:
        return {'verdict': 'model_invalid', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': f'赋值非单调：原子 {atom} 在 {w} 为真，但其后继'
                            '中有节点不为真——这不是合法的直觉主义 Kripke '
                            '模型（直觉主义要求沿偏序只增不减）。诚实拒绝'
                            '硬算，不给假结果。'}
    value = _holds(ast, world, le, val)
    return {'verdict': 'evaluated', 'value': value, 'countermodel': None,
            'comparison': [],
            'boundary': f'Kripke 求值：{formula} 在节点 {world} → '
                        f'{"真" if value else "假"}（节点 {len(worlds)} 个，'
                        '后继闭包已算）。直觉主义语义：¬ 看所有后继、'
                        '→ 看所有后继。'}


def _all_orders(worlds):
    """枚举 nodes 上的全部偏序（自反/反对称/传递）。"""
    ws = list(worlds)
    n = len(ws)
    pairs = [(ws[i], ws[j]) for i in range(n) for j in range(n)]
    out = []
    for mask in range(1 << (n * n)):
        rel = {pairs[k] for k in range(n * n) if mask >> k & 1}
        if any((w, w) not in rel for w in ws):
            continue
        if any((b, a) in rel and a != b for a, b in rel):
            continue
        if any((a, c) not in rel
               for a in ws for b in ws for c in ws
               if (a, b) in rel and (b, c) in rel):
            continue
        out.append(sorted(rel))
    return out


def _upsets(worlds, order):
    """某偏序下的全部上闭集合（赋值必须取上闭集）。"""
    ws = list(worlds)
    n = len(ws)
    rel = set(order)
    out = []
    for mask in range(1 << n):
        s = {ws[i] for i in range(n) if mask >> i & 1}
        if all(v in s for w in s for v in ws if (w, v) in rel):
            out.append(s)
    return out


def _search_countermodel(formula, ast, atoms, max_worlds):
    """在 ≤ max_worlds 个节点的模型里搜反模型（公式在某节点为假）。"""
    for n_worlds in range(1, max_worlds + 1):
        ws = [f'w{i}' for i in range(n_worlds)]
        for order in _all_orders(ws):
            ups = _upsets(ws, order)
            le = _successors(ws, order)
            for combo in itertools.product(ups, repeat=len(atoms)):
                val = {a: sorted(s) for a, s in zip(atoms, combo)}
                for w in ws:
                    if not _holds(ast, w, le, val):
                        return {'worlds': ws,
                                'order': [list(p) for p in order],
                                'valuation': val, 'refuted_at': w,
                                'note': f'{formula} 在节点 {w} 为假'}
    return None


def _countermodel(formula, max_worlds=None):
    pl = _pl()
    if not formula:
        return {'verdict': 'input_pending', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': 'mode=countermodel 需 formula——诚实拦截'}
    try:
        ast = pl.parse(formula)
    except Exception as e:  # noqa: BLE001
        return {'verdict': 'parse_pending', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': f'公式解析失败：{e}——诚实拦截'}
    atoms = _atoms_of_ast(ast)
    n = len(atoms)
    complete_bound = 2 ** n          # 直觉主义命题逻辑有限模型性质界
    limit = max_worlds or complete_bound
    if limit > 4:
        return {'verdict': 'size_limit', 'value': None,
                'countermodel': None, 'comparison': [],
                'boundary': f'原子 {n} 个 → 完备界 {complete_bound} 个节点，'
                            '模型搜索量超算力（节点×偏序×上闭集赋值指数膨胀）'
                            '——诚实报告 size_limit，不硬搜也不冒充判定。'
                            '可显式给 max_worlds ≤ 4 做有界搜索。'}
    cm = _search_countermodel(formula, ast, atoms, limit)
    if cm:
        return {'verdict': 'refuted', 'value': False, 'countermodel': cm,
                'comparison': [],
                'boundary': f'找到反模型（{len(cm["worlds"])} 个节点）→ '
                            f'{formula} **非直觉主义有效**：构造性立场下'
                            '不成立（经典层可能仍判它有效）。反模型白箱见 '
                            'countermodel 字段。'}
    if limit >= complete_bound:
        return {'verdict': 'valid', 'value': True, 'countermodel': None,
                'comparison': [],
                'boundary': f'在完备界（{limit} 个节点 = 2^{n}）内无反模型 '
                            '→ 由直觉主义命题逻辑的有限模型性质，该公式'
                            '**直觉主义有效**。'}
    return {'verdict': 'not_found_in_limit', 'value': None,
            'countermodel': None, 'comparison': [],
            'boundary': f'在 {limit} 个节点的有界搜索内未找到反模型——'
                        '**这只是"限内没找到"，不等于有效**（完备界为 '
                        f'2^{n} = {complete_bound} 个节点）。诚实标注，'
                        '不冒充判定。'}


def _compare(formulas=None):
    pl = _pl()
    nd = _nd()
    rows = []
    for label, f in (formulas or LANDMARKS):
        try:
            cl_kind = pl.run({'formula': f, 'mode': 'kind'}).get('verdict')
        except Exception:  # noqa: BLE001
            cl_kind = None
        try:
            i_nd = nd.run({'premises': [], 'conclusion': f,
                           'system': 'intuitionistic'}).get('verdict')
        except Exception as e:  # noqa: BLE001
            i_nd = f'error:{e}'
        cm = _countermodel(f, max_worlds=4)
        rows.append({
            'label': label, 'formula': f,
            'intuitionistic_nd': i_nd,
            'kripke': cm['verdict'],
            'refuted_at_worlds': (len(cm['countermodel']['worlds'])
                                  if cm['countermodel'] else None),
            'classical_kind': cl_kind,
        })
    return rows


def run(inputs):
    """
    做什么：直觉主义（构造性立场）——Kripke 求值 / 反模型搜索 / 两系统对照。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'countermodel')

    if mode == 'evaluate':
        return _evaluate(inputs.get('formula'), inputs.get('worlds'),
                         inputs.get('order'), inputs.get('valuation'),
                         inputs.get('world'))

    if mode == 'countermodel':
        return _countermodel(inputs.get('formula'), inputs.get('max_worlds'))

    if mode == 'compare':
        rows = _compare(inputs.get('formulas'))
        return {'verdict': 'compared', 'value': None, 'countermodel': None,
                'comparison': rows,
                'boundary': '经典 vs 直觉主义对照（借鉴 Brouwer/Heyting/'
                            'Kripke 1959 的外部共识）：ND 判定用直觉主义系统'
                            '（无 ¬¬ 消去），Kripke 用有界搜索（≤4 节点）。'
                            '两者都指"构造性立场不认这些经典定理"。'}

    return {'verdict': 'input_pending', 'value': None, 'countermodel': None,
            'comparison': [],
            'boundary': f'mode 应为 evaluate/countermodel/compare，得到 '
                        f'{mode!r}——诚实拦截'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 66)
    print('直觉主义逻辑 · 构造性立场构件 · 自测（第 3 层 3.5）')
    print('=' * 66)

    # 1) 反模型搜索：排中律非直觉主义有效（经典的老例子）
    r1 = run({'mode': 'countermodel', 'formula': 'P∨¬P'})
    assert r1['verdict'] == 'refuted', r1
    assert len(r1['countermodel']['worlds']) == 2, r1
    print(f"✅ 排中律 P∨¬P → {r1['verdict']}"
          f"（{len(r1['countermodel']['worlds'])} 节点反模型："
          f"{r1['countermodel']['note']}）")

    # 2) 双重否定消去同样不成立
    r2 = run({'mode': 'countermodel', 'formula': '¬¬P→P'})
    assert r2['verdict'] == 'refuted', r2
    print(f"✅ 双重否定消去 ¬¬P→P → {r2['verdict']}（构造性立场不认）")

    # 3) 直觉主义自己有效的公式：爆炸 / 有效的 De Morgan 一侧
    r3 = run({'mode': 'countermodel', 'formula': 'P→(Q→P)'})
    assert r3['verdict'] == 'valid', r3
    print(f"✅ P→(Q→P) → {r3['verdict']}（直觉主义有效——完备界内无反模型）")
    r4 = run({'mode': 'countermodel', 'formula': '¬(P∨Q)→(¬P∧¬Q)'})
    assert r4['verdict'] == 'valid', r4
    print(f"✅ ¬(P∨Q)→(¬P∧¬Q) → {r4['verdict']}"
          '（这一侧是直觉主义有效；反向那一侧不是——见对照表）')

    # 4) Kripke 求值：合法模型
    r5 = run({'mode': 'evaluate', 'formula': 'P∨¬P',
              'worlds': ['w0', 'w1'], 'order': [('w0', 'w1')],
              'valuation': {'P': ['w1']}, 'world': 'w0'})
    assert r5['verdict'] == 'evaluated' and r5['value'] is False, r5
    print(f"✅ Kripke 求值：小模型里 P∨¬P 在 w0 → {r5['value']}"
          '（P 在 w0 不真、¬P 也被 w1 的 P 破掉）')

    # 5) 非单调赋值 → 拒绝硬算
    r6 = run({'mode': 'evaluate', 'formula': 'P',
              'worlds': ['w0', 'w1'], 'order': [('w0', 'w1')],
              'valuation': {'P': ['w0']}, 'world': 'w0'})
    assert r6['verdict'] == 'model_invalid', r6
    print(f"✅ 非单调赋值 → {r6['verdict']}（拒绝硬算，不冒充合法模型）")

    # 6) 边界
    r7 = run({'mode': 'xx'})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'mode': 'evaluate'})
    assert r8['verdict'] == 'input_pending', r8
    r9 = run({'mode': 'countermodel', 'formula': 'P∧'})
    assert r9['verdict'] == 'parse_pending', r9
    r10 = run({'mode': 'countermodel', 'formula': 'P1∧P2∧P3∧P4'})
    assert r10['verdict'] == 'size_limit', r10
    print('✅ 边界：坏 mode/缺参/坏公式/超算力 → 诚实拦截')

    # 7) 两系统对照
    r11 = run({'mode': 'compare'})
    assert r11['verdict'] == 'compared', r11
    lem = r11['comparison'][0]
    assert lem['kripke'] == 'refuted', lem
    print(f"✅ 对照表 {len(r11['comparison'])} 行；"
          f"排中律：ND(直觉主义)={lem['intuitionistic_nd']} / "
          f"Kripke={lem['kripke']}")

    print('=' * 66)
    print('直觉主义逻辑构件自测：全部通过 ✅')
    print('=' * 66)
