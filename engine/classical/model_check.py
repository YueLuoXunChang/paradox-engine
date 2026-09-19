# -*- coding: utf-8 -*-
"""
model_check.py — CTL 模型检查（显式 Kripke 结构）· 第 1 层经典构件
================================================================
概念来源：经典共识（Clarke–Emerson 1981 的 CTL 标记算法 / Pnueli 1977 时序逻辑）
——「给定有限状态图与初始状态，公式是否在所有可达行为上成立」是可判的，
而且算法简单到可以手写：不动点标记。

本构件做什么（一句话）：
    输入一个**显式 Kripke 结构**（状态、迁移、每个状态上的原子命题）与一个
    **CTL 公式**，算出公式在每个状态是否成立，并回答「初始状态上成立吗」。

CTL 支持的写法（工程子集）：
    原子   := 命题名（如 `c1`，`!` 用 `!` 或 `¬`）
    一元   := ! p | EX p | AX p | EF p | AF p | EG p | AG p
    二元   := p & q | p | q | p -> q | E[p U q] | A[p U q]
    括号与优先级：U 最松 → `->` → `|` → `&` → 一元最紧。

诚实边界：
    - **只管 CTL**（每条路径量词 E/A 都紧跟时态算子）；**LTL 不在本构件**——
      LTL 有效性仍走 `ltl` 构件（本构件不假装能做自动机翻译）；
    - 状态图必须是**有限且迁移闭合**的：迁移里出现没声明的状态一律诚实拦下；
    - 死锁状态（无出边）：`AX`/`AG` 一类全称算子按"空集上真"处理（这是标准约定，
      写在这里免得被当成 bug）；`EX`/`EG` 在死锁处为假；
    - 「成立」是**相对给定结构**的结论，不是逻辑普遍有效——本构件不做普遍有效性。
"""

PORTS = {
    'in': {'states': 'list?', 'transitions': 'list?', 'labels': 'dict?',
           'formula': 'str?', 'init': 'list?'},
    'out': {'verdict': 'str', 'explanation': 'str', 'holds_in': 'list',
            'fails_in': 'list', 'sat_count': 'int?', 'boundary': 'str'},
}

import re
import sys

BOUNDARY = ('CTL 模型检查：结论是「相对给定 Kripke 结构」的，不是逻辑普遍有效；'
            '只管 CTL（E/A 紧跟时态算子），LTL 走 ltl 构件；死锁状态上全称算子按'
            '空集真处理（标准约定）。引擎只诊断不决策。')

_TOKEN = re.compile(r'\s*(->|E\[|A\[|EX|AX|EF|AF|EG|AG|U|[!¬&|()\[\]]|[A-Za-z_][A-Za-z0-9_]*)')



def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            raise ValueError('无法识别的字符：%r' % s[i:i + 8])
        out.append(m.group(1))
        i = m.end()
    return out


def _parse(tokens):
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def formula():
        left = impl()
        if peek() == 'U':                  # 裸 U 需要外面有 E[ / A[
            raise ValueError('U 必须写在 E[ p U q ] 或 A[ p U q ] 里')
        return left

    def impl():
        left = disj()
        if peek() == '->':
            take()
            return ('->', left, impl())
        return left

    def disj():
        left = conj()
        while peek() == '|':
            take()
            left = ('|', left, conj())
        return left

    def conj():
        left = unary()
        while peek() == '&':
            take()
            left = ('&', left, unary())
        return left

    def unary():
        t = peek()
        if t in ('!', '¬'):
            take()
            return ('!', unary())
        if t in ('EX', 'AX', 'EF', 'AF', 'EG', 'AG'):
            take()
            return (t, unary())
        if t in ('E[', 'A['):
            take()
            # 在 U 这一层**之下**解析两侧（U 属于 E[/A[ 的语法，不是独立算子）
            p = impl()
            if take() != 'U':
                raise ValueError('E[ / A[ 里必须是 p U q')
            q = impl()
            if take() != ']':
                raise ValueError('E[ / A[ 没闭合（缺 ]）')
            return ('E[U]' if t == 'E[' else 'A[U]', p, q)
        if t == '(':
            take()
            inner = formula()
            if take() != ')':
                raise ValueError('括号没闭合')
            return inner
        if t and re.match(r'^[A-Za-z_]', t):
            take()
            return ('atom', t)
        raise ValueError('看不懂的记号：%r' % t)

    ast = formula()
    if pos[0] != len(tokens):
        raise ValueError('公式解析完还有多余记号：%r' % tokens[pos[0]:])
    return ast


def _check(ast, states, succ, labels):
    """标准 CTL 标记：返回 {state: bool}（不动点用迭代到底实现）。"""
    S = set(states)
    k = ast[0]
    if k == 'atom':
        return {s: ast[1] in labels.get(s, []) for s in states}
    if k == '!':
        sub = _check(ast[1], states, succ, labels)
        return {s: not sub[s] for s in states}
    if k in ('&', '|', '->'):
        a = _check(ast[1], states, succ, labels)
        b = _check(ast[2], states, succ, labels)
        if k == '&':
            return {s: a[s] and b[s] for s in states}
        if k == '|':
            return {s: a[s] or b[s] for s in states}
        return {s: (not a[s]) or b[s] for s in states}
    if k == 'EX':
        sub = _check(ast[1], states, succ, labels)
        return {s: any(sub[t] for t in succ.get(s, [])) for s in states}
    if k == 'AX':
        sub = _check(ast[1], states, succ, labels)
        return {s: all(sub[t] for t in succ.get(s, [])) for s in states}

    # 不动点类
    if k == 'EF' or k == 'AF' or k == 'EG' or k == 'AG':
        sub = _check(ast[1], states, succ, labels)
        cur = dict(sub)
        while True:
            if k == 'EF':
                nxt = {s: sub[s] or any(cur[t] for t in succ.get(s, []))
                       for s in states}
            elif k == 'EG':
                nxt = {s: sub[s] and any(cur[t] for t in succ.get(s, []))
                       for s in states}
            elif k == 'AF':
                nxt = {s: sub[s] or all(cur[t] for t in succ.get(s, []))
                       for s in states}
            else:                           # AG
                nxt = {s: sub[s] and all(cur[t] for t in succ.get(s, []))
                       for s in states}
            if nxt == cur:
                return cur
            cur = nxt
    if k in ('E[U]', 'A[U]'):
        p = _check(ast[1], states, succ, labels)
        q = _check(ast[2], states, succ, labels)
        cur = dict(q)
        while True:
            if k == 'E[U]':
                nxt = {s: q[s] or (p[s] and any(cur[t]
                                                for t in succ.get(s, [])))
                       for s in states}
            else:
                nxt = {s: q[s] or (p[s] and all(cur[t]
                                                for t in succ.get(s, [])))
                       for s in states}
            if nxt == cur:
                return cur
            cur = nxt
    raise ValueError('不认识的算子：%r' % (k,))


def run(inputs):
    """
    做什么：在显式 Kripke 结构上跑 CTL 模型检查，回答公式在初始状态是否成立。

    返回 dict（PORTS['out']）：verdict ∈ holds / fails / input_pending /
    parse_error。缺参数或状态图不合法一律诚实拦下。
    """
    def bad(v, why):
        return {'verdict': v, 'explanation': why, 'holds_in': [],
                'fails_in': [], 'boundary': BOUNDARY}

    if not isinstance(inputs, dict):
        return bad('input_pending', 'inputs 必须是 dict')
    states = inputs.get('states')
    trans = inputs.get('transitions')
    labels = inputs.get('labels')
    formula = inputs.get('formula')
    if not states or not isinstance(states, list) or not isinstance(trans, list):
        return bad('input_pending', '需要 states（状态名列表）与 transitions'
                                    '（[from, to] 列表）')
    if not isinstance(formula, str) or not formula.strip():
        return bad('input_pending', '需要 formula（CTL 公式，如 AG !(c1 & c2)）')
    if labels is None:
        labels = {}
    if not isinstance(labels, dict):
        return bad('input_pending', 'labels 必须是 {状态: [命题]} 的 dict')

    S = list(states)
    Sset = set(S)
    succ = {s: [] for s in S}
    for pair in trans:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or pair[0] not in Sset or pair[1] not in Sset):
            return bad('input_pending', '迁移必须是 [已声明状态, 已声明状态]，'
                                        '这一条不合法：%r' % (pair,))
        succ[pair[0]].append(pair[1])
    for s, ps in labels.items():
        if s not in Sset:
            return bad('input_pending', 'labels 里有未声明的状态：%r' % s)
        if not isinstance(ps, list):
            return bad('input_pending', 'labels[%r] 必须是命题名列表' % s)

    try:
        ast = _parse(_tokenize(formula.strip()))
    except ValueError as e:
        return bad('parse_error', str(e))

    try:
        sat = _check(ast, S, succ, labels)
    except ValueError as e:
        return bad('parse_error', str(e))

    init = inputs.get('init') or S
    if not isinstance(init, list) or any(s not in Sset for s in init):
        return bad('input_pending', 'init 必须是已声明状态的子集')

    holds = sorted(s for s in init if sat.get(s))
    fails = sorted(s for s in init if not sat.get(s))
    ok = not fails
    return {
        'verdict': 'holds' if ok else 'fails',
        'explanation': ('公式在所有初始状态成立（共 %d 个初始状态）' % len(init))
                       if ok else
                       ('公式在 %d 个初始状态不成立：%s'
                        % (len(fails), '、'.join(fails))),
        'holds_in': holds, 'fails_in': fails,
        'sat_count': sum(1 for s in S if sat.get(s)),
        'boundary': BOUNDARY,
    }


MUTEX = {'states': ['n1n2', 'c1n2', 'n1c2'],
         'transitions': [['n1n2', 'c1n2'], ['n1n2', 'n1c2'],
                         ['c1n2', 'n1n2'], ['n1c2', 'n1n2']],
         'labels': {'n1n2': [], 'c1n2': ['c1'], 'n1c2': ['c2']},
         'init': ['n1n2']}


def _selftest():
    g = MUTEX
    assert run(dict(g, formula='AG !(c1 & c2)'))['verdict'] == 'holds'
    assert run(dict(g, formula='EF c1'))['verdict'] == 'holds'
    assert run(dict(g, formula='EG c1'))['verdict'] == 'fails'
    run2 = {'states': ['a', 'b'], 'transitions': [['a', 'b'], ['b', 'b']],
            'labels': {'a': [], 'b': ['p']}, 'init': ['a']}
    assert run(dict(run2, formula='AF p'))['verdict'] == 'holds'
    assert run(dict(run2, formula='E[p U p]'))['verdict'] == 'fails'
    assert run(dict(run2, formula='A[!p U p]'))['verdict'] == 'holds'
    print('✅ CTL 模型检查自测：互斥不变式 / EF / EG / AF / EU / AU 结论正确')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    _selftest()
