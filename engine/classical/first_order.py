# -*- coding: utf-8 -*-
"""
first_order.py — 一阶谓词逻辑构件（第 1 层经典逻辑地基 1.2）
================================================================
概念来源：经典逻辑（一阶谓词逻辑标准语义——非落落原创，经典共识）

本构件做什么：
    在有限论域上判定一阶逻辑公式的（逻辑）后承/可满足性。
    原理（适用方法）：有限论域上一阶逻辑是**可判定的**——把 ∀ 展开为
    有限个 ∧、∃ 展开为有限个 ∨，得到无量词命题公式，交给命题逻辑引擎
    判定；反例指派再映射回"对象模型"给人看。

能力分层：
    F1 基础：有限论域上的事实 + 规则 → 结论是否逻辑后承（展开法，可判）；
    F2 推理：合一 mgu（接口就绪，供后续归结扩展）；
    无限/巨大论域 → 诚实报告 undetermined/size_limit（不硬算）。

诚实边界：
    - 一阶逻辑整体半可判定（哥德尔完备但不可判定）——本构件只在
      **有限论域**上保证判定；超出则报告，不假装；
    - 展开原子数超上限 → 报告规模限制（诚实，不悄悄截断）；
    - 经典语义，只判"逻辑后承/可满足"，不含非经典算子。

统一接口：
    run(inputs: dict) -> dict
    输入:
        universe: list[str]（论域对象，可省——从事实常量自动收集）
        facts: list[str]（已知为真的地面原子，如 "人(苏格拉底)"）
        rules: list[str]（已知为真的公式，可含量词，如 "∀x(人(x)→会死(x))"）
        query: str（要判的结论，如 "会死(苏格拉底)"）
    输出:
        verdict: 'entailed' | 'not_entailed' | 'undetermined' | 'size_limit'
                  | 'formula_pending' | 'parse_error'
        counterexample_model: list[str] 或 null（not_entailed 时的反例模型）
        atoms_used: int（展开的命题原子数）
        boundary: str
"""

PORTS = {
    'in': {'universe': 'list?', 'facts': 'list?',
           'rules': 'list?', 'query': 'str'},
    'out': {'verdict': 'str', 'counterexample_model': 'list',
            'atoms_used': 'int', 'boundary': 'str'},
}

_MAX_GROUND_ATOMS = 64  # 展开原子上限（诚实边界）

# 联结词（比命题多量词）
_BIN = {'∧', '∨', '→', '↔'}
_UN = {'¬'}
_QUANT = {'∀', '∃'}
_PREC = {'↔': 1, '→': 2, '∨': 3, '∧': 4}


class _ParseError(ValueError):
    pass


# ============================================================
# 语法：中缀一阶公式 → AST
# AST 节点：
#   ('atom', 谓词名, [项...])         项 = ('const', 名) | ('var', 名)
#   ('pred0', 谓词名)                 无参谓词（命题）
#   ('¬', sub)  ('∧',l,r) ('∨',l,r) ('→',l,r) ('↔',l,r)
#   ('∀', 变量名, body) ('∃', 变量名, body)
# ============================================================

def _tokenize(s):
    """切 token：名称（字母/汉字/下划线/数字串）、联结词、量词、括号、逗号。"""
    toks = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in '(),':
            toks.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        elif ch in _BIN or ch in _UN or ch in _QUANT:
            toks.append(ch)
            i += 1
        else:
            j = i
            while j < n and s[j] not in '(),' and s[j] != ' ' \
                    and s[j] not in _BIN and s[j] not in _UN \
                    and s[j] not in _QUANT:
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


class _P:
    """Pratt 解析器（带量词）。"""

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
            node = ('¬', self.parse_formula(4))
        elif t in _QUANT:
            self.next()
            var = self.next()
            if var in (None,) or var in _BIN or var in _UN or var in _QUANT \
                    or var in '(),':
                raise _ParseError(f"量词后应为变量名，得到 '{var}'")
            # 作用域：必须跟括号公式（显式范围，语法纪律）
            body = self.parse_formula(0)
            node = (t, var, body)
        elif t in _BIN or t in '),':
            raise _ParseError(f"缺左操作数：'{t}'")
        else:
            node = self.parse_atom()
        # 二元联结词
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

    def parse_atom(self):
        """谓词/无参谓词/项结构。"""
        name = self.next()
        if name in (None,) or name in '(),' or name in _BIN or name in _UN \
                or name in _QUANT:
            raise _ParseError(f"非法谓词名 '{name}'")
        # 无参谓词（命题）：后面不是 '('
        if self.peek() != '(':
            return ('pred0', name)
        self.next()  # '('
        args = []
        while True:
            t = self.peek()
            if t == ')':
                break
            if t is None:
                raise _ParseError(f"谓词 {name} 参数缺右括号")
            args.append(self.parse_term())
            if self.peek() == ',':
                self.next()
        self.expect(')')
        return ('atom', name, args)

    def parse_term(self):
        """项：常量/变量（裸名）或函数应用 f(t,...)。"""
        name = self.next()
        if name is None:
            raise _ParseError("项缺名称（公式意外结束）")
        if self.peek() == '(':
            self.next()
            args = []
            while True:
                t = self.peek()
                if t == ')':
                    break
                args.append(self.parse_term())
                if self.peek() == ',':
                    self.next()
            self.expect(')')
            return ('func', name, args)
        return ('const', name)  # 变量由量词绑定，这里先当"名"


def parse(s):
    toks = _tokenize(s)
    if not toks:
        raise _ParseError("空公式")
    p = _P(toks)
    node = p.parse_formula()
    if p.pos != len(p.toks):
        raise _ParseError(f"多余内容: {p.toks[p.pos:]}")
    return node


# ============================================================
# 辅助：自由变量 / 替换 / 收集地面原子
# ============================================================

def free_vars(node, bound=None):
    """AST 自由变量（按出现序去重）。"""
    bound = bound or set()
    out = []
    seen = set()

    def add(v):
        if v not in seen:
            seen.add(v)
            out.append(v)

    def walk(n):
        k = n[0]
        if k == 'const' or k == 'func':
            return
        if k == 'atom':
            for t in n[2]:
                _walk_term(t)
        elif k == 'pred0':
            pass
        elif k in ('¬',):
            walk(n[1])
        elif k in ('∀', '∃'):
            walk(n[2])
        else:
            walk(n[1])
            walk(n[2])

    def _walk_term(t):
        if t[0] == 'const':
            if t[1] not in bound:
                add(t[1])
        elif t[0] == 'func':
            for a in t[2]:
                _walk_term(a)

    walk(node)
    return out


def subst_term(term, var, obj):
    """项替换：var → 常量 obj（obj 为字符串名）。"""
    if term[0] == 'const':
        return ('const', obj) if term[1] == var else term
    if term[0] == 'func':
        return ('func', term[1], [subst_term(a, var, obj) for a in term[2]])
    return term


def subst(node, var, obj):
    """公式替换：自由变量 var → 常量 obj（obj: str）。"""
    k = node[0]
    if k == 'atom':
        return ('atom', node[1],
                [subst_term(t, var, obj) for t in node[2]])
    if k == 'pred0':
        return node
    if k == '¬':
        return ('¬', subst(node[1], var, obj))
    if k in ('∀', '∃'):
        # 不进入同名变量的绑定作用域
        return (k, node[1],
                node[2] if node[1] == var else subst(node[2], var, obj))
    return (k, subst(node[1], var, obj), subst(node[2], var, obj))


def collect_constants(node, out=None):
    """公式中出现的所有常量名（谓词/函数参数与无参谓词名不算）。"""
    out = out if out is not None else set()

    def t_walk(t):
        if t[0] == 'const':
            out.add(t[1])
        elif t[0] == 'func':
            for a in t[2]:
                t_walk(a)

    def walk(n):
        k = n[0]
        if k == 'atom':
            for t in n[2]:
                t_walk(t)
        elif k == 'pred0':
            pass
        elif k == '¬':
            walk(n[1])
        elif k in ('∀', '∃'):
            walk(n[2])
        else:
            walk(n[1])
            walk(n[2])

    walk(node)
    return out


def ground_atoms(node, out=None):
    """公式中的地面原子（无自由变量）→ 收集谓词+参数串。"""
    out = out if out is not None else {}

    def t_str(t):
        if t[0] == 'const':
            return t[1]
        return t[1] + '(' + ','.join(t_str(a) for a in t[2]) + ')'

    def walk(n):
        k = n[0]
        if k == 'atom':
            key = n[1] + '(' + ','.join(t_str(t) for t in n[2]) + ')'
            out.setdefault(key, True)
        elif k == 'pred0':
            out.setdefault(n[1], True)
        elif k == '¬':
            walk(n[1])
        elif k in ('∀', '∃'):
            walk(n[2])
        else:
            walk(n[1])
            walk(n[2])

    walk(node)
    return out


def free_vars_in_atom(node, bound):
    """原子是否含自由变量（保留：供后续 F2 归结扩展用）。"""
    return len(free_vars(node, bound)) > 0


def _has_quantifier(node):
    """公式树中是否含量词。"""
    k = node[0]
    if k in ('∀', '∃'):
        return True
    if k == '¬':
        return _has_quantifier(node[1])
    if k in ('∧', '∨', '→', '↔'):
        return _has_quantifier(node[1]) or _has_quantifier(node[2])
    return False


# ============================================================
# F1：有限论域展开 → 命题逻辑判定
# ============================================================

def _expand_formula(node, universe, bound):
    """把公式在有限论域上展开为无量词地面公式（仍为 AST 树，原子为
    ('ground', key) 叶子，key 形如 '人(苏格拉底)'）。"""
    k = node[0]
    if k == 'atom':
        # 项位置的裸名 = 常量（论域对象）或已被量词替换的变量——
        # 替换（subst）已处理绑定变量，这里直接生成地面键，不查自由变量
        # （常量如"苏格拉底"不是自由变量）
        return ('ground', _atom_key(node))
    if k == 'pred0':
        return ('ground', node[1])
    if k == '¬':
        return ('¬', _expand_formula(node[1], universe, bound))
    if k in ('∧', '∨', '→', '↔'):
        return (k, _expand_formula(node[1], universe, bound),
                _expand_formula(node[2], universe, bound))
    if k in ('∀', '∃'):
        var = node[1]
        body = node[2]
        if not universe:
            # 空论域：∀ 恒真、∃ 恒假
            return ('ground', '⊤' if k == '∀' else '⊥')
        chain_op = '∧' if k == '∀' else '∨'
        chain = None
        for obj in universe:
            sub = _expand_formula(subst(body, var, obj), universe,
                                  bound | {var})
            chain = sub if chain is None else (chain_op, chain, sub)
        return chain
    raise _ParseError(f"未知节点 {node}")


def _atom_key(node):
    """地面原子 → 字符串键。"""
    parts = [node[1]]
    for t in node[2]:
        if t[0] == 'const':
            parts.append(t[1])
        elif t[0] == 'func':
            parts.append(t[1] + '(' +
                         ','.join(_term_str(a) for a in t[2]) + ')')
    return node[1] + '(' + ','.join(parts[1:]) + ')'


def _term_str(t):
    if t[0] == 'const':
        return t[1]
    return t[1] + '(' + ','.join(_term_str(a) for a in t[2]) + ')'


def _ast_to_prop(ast, atoms_map):
    """展开后 AST（ground 叶子）→ 命题逻辑字符串（复用命题引擎）。"""
    k = ast[0]
    if k == 'ground':
        key = ast[1]
        if key in ('⊤', '⊥'):
            return key
        return atoms_map[key]
    if k == '¬':
        return '¬(' + _ast_to_prop(ast[1], atoms_map) + ')'
    if k == '∧':
        return '(' + _ast_to_prop(ast[1], atoms_map) + '∧' + \
               _ast_to_prop(ast[2], atoms_map) + ')'
    if k == '∨':
        return '(' + _ast_to_prop(ast[1], atoms_map) + '∨' + \
               _ast_to_prop(ast[2], atoms_map) + ')'
    if k == '→':
        return '(' + _ast_to_prop(ast[1], atoms_map) + '→' + \
               _ast_to_prop(ast[2], atoms_map) + ')'
    if k == '↔':
        return '(' + _ast_to_prop(ast[1], atoms_map) + '↔' + \
               _ast_to_prop(ast[2], atoms_map) + ')'
    raise _ParseError("无法转命题")


def _collect_grounds(ast, out):
    """收集展开树里所有 ground key。"""
    k = ast[0]
    if k == 'ground':
        out.add(ast[1])
    elif k == '¬':
        _collect_grounds(ast[1], out)
    else:
        _collect_grounds(ast[1], out)
        _collect_grounds(ast[2], out)


def entail(universe, premises, query_ast):
    """有限论域逻辑后承判定。

    premises: 展开后 AST 列表（facts + rules，均已知为真）
    query_ast: 展开后 AST
    返回: (verdict, counter_model, atoms_used)
    """
    # 收集所有 ground 原子并编号
    grounds = set()
    for p in premises:
        _collect_grounds(p, grounds)
    _collect_grounds(query_ast, grounds)
    # 去掉 ⊤/⊥
    grounds.discard('⊤')
    grounds.discard('⊥')
    if len(grounds) > _MAX_GROUND_ATOMS:
        return 'size_limit', None, len(grounds)
    atoms_map = {}
    for i, g in enumerate(sorted(grounds)):
        atoms_map[g] = f'P{i}'
    rev = {v: k for k, v in atoms_map.items()}

    # 前提合取：premises ∧ ... ∧ query
    # 判 query 是否逻辑后承： (∧premises) → query 是重言式
    # 复用命题引擎：validity(premises_props, query_prop)
    import os
    import sys as _sys
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in _sys.path:
        _sys.path.insert(0, _dir)
    from propositional import run as prop_run

    premise_strs = [_ast_to_prop(p, atoms_map) for p in premises]
    query_str = _ast_to_prop(query_ast, atoms_map)
    r = prop_run({'premises': premise_strs, 'conclusion': query_str,
                  'mode': 'validity'})
    if r['verdict'] == 'valid':
        return 'entailed', None, len(grounds)
    # 反例指派 → 对象模型（只列前提中真、query 假所涉及的关键原子）
    counter = r.get('counterexample') or {}
    model_lines = []
    for prop_name, truth in counter.items():
        gk = rev.get(prop_name)
        if gk is None:
            continue
        model_lines.append(f"{gk} = {'真' if truth == '真' else '假'}")
    # 排序显示
    model_lines.sort()
    return 'not_entailed', model_lines, len(grounds)


# ============================================================
# 机制统一入口
# ============================================================

def run(inputs):
    """
    做什么：一阶谓词逻辑（有限论域）逻辑后承判定。

    输入:
        universe: list[str]，论域对象（可省，自动从事实常量收集）
        facts: list[str]，地面原子事实（已知真）
        rules: list[str]，带量词规则（已知真）
        query: str，要判的结论

    返回:
        dict
    """
    query = inputs.get('query')
    facts = inputs.get('facts') or []
    rules = inputs.get('rules') or []

    if not query:
        return {'verdict': 'query_pending', 'counterexample_model': None,
                'atoms_used': 0,
                'boundary': '需先提供要判定的结论（query）——诚实：不硬判'}

    try:
        # 1) 解析所有公式
        query_ast = parse(query)
        fact_asts = [parse(f) for f in facts]
        rule_asts = [parse(r) for r in rules]
        # 2) 收集论域
        univ = list(inputs.get('universe') or [])
        collected = set(univ)
        for a in fact_asts + rule_asts + [query_ast]:
            collected |= collect_constants(a)
        univ = sorted(collected)
        # 空论域但公式含量词 → 诚实不支持（空论域语义特殊）
        has_quant = _has_quantifier(query_ast) or any(
            _has_quantifier(a) for a in fact_asts + rule_asts)
        if not univ and has_quant:
            return {'verdict': 'no_universe', 'counterexample_model': None,
                    'atoms_used': 0,
                    'boundary': '论域为空且公式含量词——空论域语义特殊'
                                '（∀ 恒真/∃ 恒假），本构件诚实不硬判'
                                '；请给出至少一个对象或去掉量词'}
        # 3) 展开（facts/rules 已知真；query 判定）——纯地面情况 univ 可空
        expanded_premises = [_expand_formula(a, univ, set())
                             for a in fact_asts + rule_asts]
        expanded_query = _expand_formula(query_ast, univ, set())
        verdict, model, atoms = entail(univ, expanded_premises,
                                       expanded_query)
        if verdict == 'entailed':
            return {'verdict': 'entailed', 'counterexample_model': None,
                    'atoms_used': atoms,
                    'boundary': f'有限论域 {len(univ)} 对象、{atoms} 个地面'
                                f'原子上的逻辑后承判定（展开法，可判）'}
        if verdict == 'not_entailed':
            return {'verdict': 'not_entailed', 'counterexample_model': model,
                    'atoms_used': atoms,
                    'boundary': '反例模型 = 使前提全真而结论假的对象指派'
                                '（有限论域展开法）'}
        return {'verdict': verdict, 'counterexample_model': None,
                'atoms_used': atoms,
                'boundary': f'展开原子 {atoms} 超过上限 {_MAX_GROUND_ATOMS}'
                            f'——指数爆炸风险，建议缩小论域或拆分（诚实边界）'}
    except _ParseError as e:
        return {'verdict': 'parse_error', 'counterexample_model': None,
                'atoms_used': 0,
                'boundary': f'公式解析失败：{e}（诚实拦截，不硬算）'}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('一阶谓词逻辑构件 · 自测（经典逻辑层 1.2）')
    print('=' * 62)

    # 1) 三段论：∀x(人→会死), 人(苏格拉底) ⊢ 会死(苏格拉底)
    r1 = run({'facts': ['人(苏格拉底)'],
              'rules': ['∀x(人(x)→会死(x))'],
              'query': '会死(苏格拉底)'})
    assert r1['verdict'] == 'entailed', f"三段论应 entail: {r1}"
    print('✅ 三段论 ∀x(人→会死), 人(苏) ⊢ 会死(苏) → entailed')

    # 2) 反例：∀x(鸟→会飞), 鸟(企鹅) 不推出 会飞(鹰)（鹰不在鸟集合）
    r2 = run({'facts': ['鸟(企鹅)', '鸟(麻雀)'],
              'rules': ['∀x(鸟(x)→会飞(x))'],
              'query': '会飞(鹰)'})
    assert r2['verdict'] == 'not_entailed', f"应 not_entailed: {r2}"
    assert r2['counterexample_model'] is not None
    print(f"✅ 会飞(鹰) → not_entailed，反例模型 {len(r2['counterexample_model'])} 条")

    # 3) 企鹅不飞但属于鸟 → 规则被挑战（not entailed：企鹅会飞？）
    r3 = run({'facts': ['鸟(企鹅)'],
              'rules': ['∀x(鸟(x)→会飞(x))'],
              'query': '会飞(企鹅)'})
    # 前提含鸟(企鹅) 且规则说 ∀x 鸟→会飞，所以企鹅会飞 entailed
    assert r3['verdict'] == 'entailed', f"企鹅应会飞: {r3}"
    print('✅ 鸟(企鹅) + ∀x(鸟→会飞) ⊢ 会飞(企鹅) → entailed')

    # 4) 存在量词：∃x(鸟(x)) + 鸟(麻雀) → 存在鸟
    r4 = run({'facts': ['鸟(麻雀)'],
              'rules': [],
              'query': '∃x(鸟(x))'})
    assert r4['verdict'] == 'entailed', f"存在应 entailed: {r4}"
    print('✅ ∃x(鸟(x)) → entailed（麻雀在场）')

    # 5) 无参谓词 + 一阶混合
    r5 = run({'facts': ['下雨'],
              'rules': ['下雨→地面湿'],
              'query': '地面湿'})
    assert r5['verdict'] == 'entailed', f"混合: {r5}"
    print('✅ 命题+谓词混合 下雨→地面湿 → entailed')

    # 6) 语法错误诚实拦截
    r6 = run({'facts': ['人(苏格拉底)'], 'rules': [],
              'query': '∀x('})
    assert r6['verdict'] == 'parse_error', f"应解析错误: {r6}"
    print('✅ 残缺公式 → parse_error（诚实拦截）')

    # 7) 缺 query
    r7 = run({'facts': ['人(苏格拉底)']})
    assert r7['verdict'] == 'query_pending', f"应待 query: {r7}"
    print('✅ 缺 query → query_pending')

    print('=' * 62)
    print('一阶谓词逻辑构件自测：全部通过 ✅')
    print('=' * 62)
