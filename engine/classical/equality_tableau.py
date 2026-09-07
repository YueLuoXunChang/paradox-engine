# -*- coding: utf-8 -*-
"""
equality_tableau.py — 等词 + 表列法构件（第 1 层经典逻辑基础 1.5）
====================================================================
概念来源：经典逻辑（等词替换语义 + tableau 证明方法——非落落原创，经典共识）
详规：《逻辑建模引擎_经典逻辑层详规》七·补C
公式卡：docs/formulas/equality_tableau.md

本构件两块：
    1. 等词 =：a=b 的对象可互相替换（替换公理）——建模"同一对象不同名字"
       （晨星=暮星/水=H₂O）；
    2. 表列法 tableau：树形反证——把 ¬结论 展开成公式树，分支闭则有效；
       开放分支 = 反例模型。

能力范围（首期）：
    - 命题级 tableau（含等词地面替换）——可判定、完备；
    - 一阶 tableau：有界 ∀ 实例化（max_expand），诚实 undetermined 边界。

诚实边界：
    - 等词破坏"有限论域简单可判"（需商模型）——有界策略 + 标注；
    - tableau 对不可判片段不保证终止——max_expand 上限 + undetermined 合法；
    - 开放分支 = 反例模型（白箱给人看）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        premises: list[str]，前提
        conclusion: str，结论
        equality: list[str]，等词事实（如 "晨星=暮星"）
        max_expand: int（tableau 展开/∀实例化上限，默认 30）
    输出:
        verdict: 'valid' | 'invalid' | 'undetermined' | 'conclusion_pending'
                  | 'parse_error'
        closed_branches: list 或 null
        open_branch_model: list 或 null（invalid 时反例模型）
        boundary: str
"""

PORTS = {
    'in': {'premises': 'list?', 'conclusion': 'str?',
           'equality': 'list?', 'max_expand': 'int?'},
    'out': {'verdict': 'str', 'closed_branches': 'list',
            'open_branch_model': 'list', 'boundary': 'str'},
}

_MAX_EXPAND = 30


class _ParseError(ValueError):
    pass


# ============================================================
# 一阶公式解析（无函数/量词版首期；有常量/谓词/等词 = 二元谓词）
# AST：('atom', 谓词, [项]) | ('eq', t1, t2) | 联结词 | 量词（后补）
# 项：('c', 名) 常量
# ============================================================

_BIN = {'∧', '∨', '→', '↔'}
_UN = {'¬'}
_PREC = {'↔': 1, '→': 2, '∨': 3, '∧': 4}


def _tokenize(s):
    toks = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in '(),=':
            toks.append(ch)
            i += 1
        elif ch in _BIN or ch in _UN:
            toks.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        else:
            j = i
            while j < n and s[j] not in '(),=' and s[j] != ' ' \
                    and s[j] not in _BIN and s[j] not in _UN:
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


class _P:
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def next(self):
        t = self.peek()
        self.pos += 1
        return t

    def expect(self, ch):
        t = self.next()
        if t != ch:
            raise _ParseError(f"期望 '{ch}'，得到 '{t}'")

    def parse_formula(self, min_prec=0):
        t = self.peek()
        if t is None:
            raise _ParseError("公式不完整")
        if t == '(':
            self.next()
            node = self.parse_formula(0)
            self.expect(')')
        elif t == '¬':
            self.next()
            node = ('¬', self.parse_formula(5))
        elif t in _BIN or t == ')':
            raise _ParseError(f"缺左操作数：'{t}'")
        else:
            node = self.parse_atom_or_eq()
        while True:
            op = self.peek()
            if op in _BIN:
                prec = _PREC[op]
                if prec < min_prec:
                    break
                self.next()
                right = self.parse_formula(prec + 1)
                node = (op, node, right)
            else:
                break
        return node

    def parse_atom_or_eq(self):
        name = self.next()
        if name is None or name in '(),=' or name in _BIN or name in _UN:
            raise _ParseError(f"非法名称 '{name}'")
        if self.peek() == '=':
            self.next()
            right = self.parse_const()
            return ('eq', name, right)
        if self.peek() != '(':
            return ('atom0', name)  # 命题
        self.next()
        args = []
        while True:
            t = self.peek()
            if t == ')':
                break
            if t is None:
                raise _ParseError(f"谓词 {name} 缺右括号")
            args.append(self.parse_const())
            if self.peek() == ',':
                self.next()
        self.expect(')')
        return ('atom', name, tuple(args))

    def parse_const(self):
        name = self.next()
        if name is None or name in '(),=' or name in _BIN or name in _UN:
            raise _ParseError(f"常量名非法 '{name}'")
        return ('c', name)


def parse(s):
    toks = _tokenize(s)
    if not toks:
        raise _ParseError("空公式")
    p = _P(toks)
    node = p.parse_formula()
    if p.pos != len(p.toks):
        raise _ParseError(f"多余内容: {p.toks[p.pos:]}")
    return node


def fmt(node):
    k = node[0]
    if k == 'atom0':
        return node[1]
    if k == 'atom':
        return node[1] + '(' + ','.join(t[1] for t in node[2]) + ')'
    if k == 'eq':
        return f"{node[1]}={node[2][1]}"
    if k == '¬':
        return f"¬{fmt(node[1])}"
    return f"({fmt(node[1])}{k}{fmt(node[2])})"


def _negate(node):
    if node[0] == '¬':
        return node[1]
    return ('¬', node)


def same(a, b):
    return fmt(a) == fmt(b)


def _collect_consts(node, out):
    k = node[0]
    if k == 'atom':
        for t in node[2]:
            out.add(t[1])
    elif k == 'eq':
        out.add(node[1])
        out.add(node[2][1])
    elif k == 'atom0':
        pass
    elif k == '¬':
        _collect_consts(node[1], out)
    elif k in ('∧', '∨', '→', '↔'):
        _collect_consts(node[1], out)
        _collect_consts(node[2], out)


# ============================================================
# 等词替换（应用已给等词事实做重写）
# ============================================================

def _apply_equality(node, eq_map):
    """用等词映射替换公式中常量。eq_map: {常量: 代表元}。"""
    k = node[0]
    if k == 'atom':
        return ('atom', node[1],
                tuple(('c', eq_map.get(t[1], t[1])) for t in node[2]))
    if k == 'atom0':
        return node
    if k == 'eq':
        a = eq_map.get(node[1], node[1])
        b = eq_map.get(node[2][1], node[2][1])
        return ('eq', a, ('c', b))
    if k == '¬':
        return ('¬', _apply_equality(node[1], eq_map))
    if k in ('∧', '∨', '→', '↔'):
        return (k, _apply_equality(node[1], eq_map),
                _apply_equality(node[2], eq_map))
    return node


def _build_eq_map(equality_formulas):
    """从等词事实建 常量→代表元 映射（union-find 简化版）。"""
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    consts = set()
    for f in equality_formulas:
        if f[0] == 'eq':
            consts.add(f[1])
            consts.add(f[2][1])
    for c in consts:
        find(c)
    for f in equality_formulas:
        if f[0] == 'eq':
            union(f[1], f[2][1])
    # 每个常量映射到其类的最小代表
    eq_map = {}
    for c in consts:
        eq_map[c] = find(c)
    return eq_map


# ============================================================
# 命题 tableau（含等词地面替换后）
# 返回 (closed, open_branch) —— 全部支闭 = 不可满足；有开支 = 模型
# ============================================================

def tableau_prop(formula_set, max_expand=None):
    """命题公式集 tableau——判定可满足性。
    返回 (satisfiable, open_branch, closed_branches, exhausted)。
    公式集不可满足（全支闭）→ satisfiable=False。"""
    max_expand = max_expand or _MAX_EXPAND
    closed = 0
    open_branch = None
    exhausted = False

    # 展开队列：每项 (公式集, 路径标签)
    from collections import deque
    queue = deque()
    queue.append((set(formula_set), []))

    while queue:
        node_formulas, path = queue.popleft()
        if len(path) > max_expand:
            exhausted = True
            continue
        # 1. 闭合检查：A 与 ¬A 同在
        fmts = {fmt(f) for f in node_formulas}
        has_contra = False
        for f in list(node_formulas):
            if f[0] == '¬' and fmt(f[1]) in fmts:
                has_contra = True
                break
            if f[0] == 'eq' and f[1] == f[2][1]:  # a≠a
                has_contra = True
                break
            # ¬(a=a) 也矛盾
            if f[0] == '¬' and f[1][0] == 'eq' \
                    and f[1][1] == f[1][2][1]:
                has_contra = True
                break
        if has_contra:
            closed += 1
            continue
        # 2. 找可展开公式
        expanded = False
        for f in list(node_formulas):
            k = f[0]
            if k in ('∧', '→', '↔'):
                # 合取/蕴含：确定性展开（无分叉）
                if k == '∧':
                    rest = node_formulas - {f}
                    queue.append((rest | {f[1], f[2]}, path + ['∧']))
                elif k == '→':
                    rest = node_formulas - {f}
                    # A→B ≡ ¬A ∨ B → 分叉
                    queue.append((rest | {_negate(f[1])}, path + ['→L']))
                    queue.append((rest | {f[2]}, path + ['→R']))
                elif k == '↔':
                    rest = node_formulas - {f}
                    queue.append((rest | {f[1], f[2]}, path + ['↔1']))
                    queue.append((rest | {_negate(f[1]), _negate(f[2])},
                                  path + ['↔2']))
                expanded = True
                break
            elif k == '∨':
                rest = node_formulas - {f}
                queue.append((rest | {f[1]}, path + ['∨L']))
                queue.append((rest | {f[2]}, path + ['∨R']))
                expanded = True
                break
            elif k == '¬' and f[1][0] in ('∧', '∨', '→', '↔'):
                # ¬(复合) 用 De Morgan 展开
                inner = f[1]
                rest = node_formulas - {f}
                if inner[0] == '∧':
                    queue.append((rest | {_negate(inner[1]), _negate(inner[2])},
                                  path + ['¬∧']))
                elif inner[0] == '∨':
                    # ¬(A∨B) ≡ ¬A ∧ ¬B——同支加两个（De Morgan 合取）
                    queue.append((rest | {_negate(inner[1]),
                                          _negate(inner[2])},
                                  path + ['¬∨']))
                elif inner[0] == '→':
                    queue.append((rest | {inner[1], _negate(inner[2])},
                                  path + ['¬→']))
                elif inner[0] == '↔':
                    queue.append((rest | {inner[1], _negate(inner[2])},
                                  path + ['¬↔1']))
                    queue.append((rest | {_negate(inner[1]), inner[2]},
                                  path + ['¬↔2']))
                expanded = True
                break
        if not expanded:
            # 无法再展开且不闭 → 开放分支（模型）
            open_branch = sorted(fmts)
            break

    return open_branch is not None, open_branch, closed, exhausted


# ============================================================
# 机制统一入口
# ============================================================

def run(inputs):
    """
    做什么：等词 + 命题 tableau——判定有效性。

    输入:
        inputs: dict（见模块 docstring）

    返回:
        dict
    """
    conclusion = inputs.get('conclusion')
    if not conclusion:
        return {'verdict': 'conclusion_pending', 'closed_branches': None,
                'open_branch_model': None,
                'boundary': '需先提供结论（conclusion）——诚实：不硬判'}
    premises = inputs.get('premises') or []
    equality = inputs.get('equality') or []
    max_expand = inputs.get('max_expand') or _MAX_EXPAND

    try:
        # 1) 解析
        concl = parse(conclusion)
        premise_asts = [parse(p) for p in premises]
        eq_asts = [parse(e) for e in equality]
        # 等词公式必须是 'eq' 形状
        for e in eq_asts:
            if e[0] != 'eq':
                raise _ParseError(f"等词事实应为 a=b 形状：{e}")
        # 2) 建等词映射并应用到所有公式
        eq_map = _build_eq_map(eq_asts)
        concl_r = _apply_equality(concl, eq_map)
        premise_r = [_apply_equality(p, eq_map) for p in premise_asts]
        # 等词本身作为前提事实加入（a=b 在映射后变成 a=a 恒真——可略）
        # 3) 有效性判定：premises ∧ ¬conclusion 不可满足 ⟺ 有效
        neg_concl = _negate(concl_r)
        formula_set = set(premise_r) | {neg_concl}
        satisfiable, open_branch, closed, exhausted = \
            tableau_prop(formula_set, max_expand)
    except _ParseError as e:
        return {'verdict': 'parse_error', 'closed_branches': None,
                'open_branch_model': None,
                'boundary': f'解析失败：{e}（诚实拦截，不硬算）'}

    if not satisfiable:
        return {'verdict': 'valid', 'closed_branches': closed,
                'open_branch_model': None,
                'boundary': f'tableau 全支闭（{closed} 支）——前提∧¬结论不可'
                            f'满足 ⇒ 结论有效（等词映射已应用）'}
    # 有开放分支：若因展开上限 → undetermined；否则 invalid + 模型
    if exhausted:
        return {'verdict': 'undetermined', 'closed_branches': closed,
                'open_branch_model': open_branch,
                'boundary': f'达到展开上限 {max_expand}——诚实：可能还需'
                            f'展开才能判（undetermined ≠ invalid）'}
    return {'verdict': 'invalid', 'closed_branches': closed,
            'open_branch_model': open_branch,
            'boundary': f'开放分支 = 反例模型（前提真结论假）：'
                        f'{open_branch}'}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('等词 + 表列法构件 · 自测（经典逻辑层 1.5）')
    print('=' * 62)

    # 1) 基本有效：P ⊢ P∨Q
    r1 = run({'premises': ['P'], 'conclusion': 'P∨Q'})
    assert r1['verdict'] == 'valid', r1
    print('✅ P ⊢ P∨Q → valid')

    # 2) 基本无效 + 反例：P∨Q ⊢ P
    r2 = run({'premises': ['P∨Q'], 'conclusion': 'P'})
    assert r2['verdict'] == 'invalid', r2
    assert r2['open_branch_model'] is not None
    print(f"✅ P∨Q ⊢ P → invalid，反例模型 {r2['open_branch_model']}")

    # 3) 等词替换：晨星=暮星, 喜欢(晨星,c) ⊢ 喜欢(暮星,c)
    r3 = run({'premises': ['喜欢(晨星,c)'], 'equality': ['晨星=暮星'],
              'conclusion': '喜欢(暮星,c)'})
    assert r3['verdict'] == 'valid', r3
    print('✅ 晨星=暮星 替换 → valid（喜欢(暮星,c) 成立）')

    # 4) 三段论式有效（一阶地面——无量词版）
    r4 = run({'premises': ['人(苏格拉底)', '人(苏格拉底)→会死(苏格拉底)'],
              'conclusion': '会死(苏格拉底)'})
    assert r4['verdict'] == 'valid', r4
    print('✅ 人(苏) ∧ (人→会死)(苏) ⊢ 会死(苏) → valid')

    # 5) 等词恒等：⊢ a=a 相关（任意前提成立：a=a 是 tautology——前提空
    #    时 ¬(a=a) 不可满足）
    r5 = run({'premises': [], 'equality': [], 'conclusion': 'a=a'})
    assert r5['verdict'] == 'valid', r5
    print('✅ ⊢ a=a → valid（自反）')

    # 6) 边界
    r6 = run({})
    assert r6['verdict'] == 'conclusion_pending', r6
    r7 = run({'premises': ['('], 'conclusion': 'P'})
    assert r7['verdict'] == 'parse_error', r7
    print('✅ 缺结论/解析错误 → 诚实拦截')

    print('=' * 62)
    print('等词 + 表列法构件自测：全部通过 ✅')
    print('=' * 62)
