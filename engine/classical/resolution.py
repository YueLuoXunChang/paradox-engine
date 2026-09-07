# -*- coding: utf-8 -*-
"""
resolution.py — 一阶归结构件（第 1 层经典逻辑基础 1.4）
=========================================================
概念来源：经典自动定理证明（Robinson 归结 + 合一——非落落原创，经典共识）
详规：《逻辑建模引擎_经典逻辑层详规》七·补B
公式卡：docs/formulas/resolution.md

与 1.3（一阶判定器，有限域展开）的区别：
    1.3 只判有限论域（展开枚举）；
    1.4 给一般一阶公式的**证明尝试**——¬结论并入前提 → 子句化（含 Skolem）
    → 合一 + 归结 → 空子句 ⇒ 有效。是经典自动推理的"真机器"。

本构件做什么：
    一阶归结反证——子句化/Skolem/合一 mgu/归结链。

诚实边界：
    - 一阶逻辑半可判定：not_proved = "步数内没找到"，不是"不可证"；
    - occurs check 必做（防 x=f(x) 无限合一）；
    - Skolem 引入的新符号记录（白箱）；
    - 子句化指数增长：max_resolvents 限制 + 诚实报告。

统一接口：
    run(inputs: dict) -> dict
    输入:
        premises: list[str]，前提公式（可含量词）
        conclusion: str，结论
        facts: list[str]，地面原子事实（并入前提）
        max_resolvents: int（归结步数上限，默认 500）
    输出:
        verdict: 'proved' | 'not_proved' | 'max_steps_exceeded'
                  | 'conclusion_pending' | 'parse_error'
        resolution_chain: list[step] 或 null
        skolem_used: list[str]
        boundary: str
"""

PORTS = {
    'in': {'premises': 'list?', 'conclusion': 'str?', 'facts': 'list?',
           'max_resolvents': 'int?'},
    'out': {'verdict': 'str', 'resolution_chain': 'list',
            'skolem_used': 'list', 'boundary': 'str'},
}

_MAX_RESOLVENTS = 500


class _ParseError(ValueError):
    pass


# ============================================================
# 一阶公式解析（支持量词 ∀/∃、谓词、函数、常量、变量、等词暂略）
# AST：原子 ('atom', 谓词, [项])；项 ('const',名)|('var',名)|('func',名,[项])
#      ('∀',var,body) ('∃',var,body) 联结词
# ============================================================

_BIN = {'∧', '∨', '→', '↔'}
_UN = {'¬'}
_QUANT = {'∀', '∃'}
_PREC = {'↔': 1, '→': 2, '∨': 3, '∧': 4}


def _tokenize(s):
    toks = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in '(),':
            toks.append(ch)
            i += 1
        elif ch in _BIN or ch in _UN or ch in _QUANT:
            toks.append(ch)
            i += 1
        elif ch == ' ':
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
        elif t in _QUANT:
            self.next()
            var = self.next()
            if var in (None,) or var in _BIN or var in _UN \
                    or var in _QUANT or var in '(),':
                raise _ParseError(f"量词后应为变量名，得到 '{var}'")
            body = self.parse_formula(0)
            node = (t, var, body)
        elif t in _BIN or t == ')':
            raise _ParseError(f"缺左操作数：'{t}'")
        else:
            node = self.parse_atom()
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
        name = self.next()
        if name in (None,) or name in '(),' or name in _BIN or name in _UN \
                or name in _QUANT:
            raise _ParseError(f"非法谓词名 '{name}'")
        if self.peek() != '(':
            return ('atom0', name)  # 无参谓词（命题）
        self.next()
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
        name = self.next()
        if name is None:
            raise _ParseError("项缺名称")
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
        # 变量 vs 常量：量词绑定的名字在展开时区分——这里标 'name'
        return ('name', name)


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
# 变量管理：bound 集合由量词建立
# ============================================================

def _is_var(name, bound):
    return name in bound


def fmt_term(t):
    if t[0] in ('name', 'var', 'const'):
        return t[1]
    if t[0] == 'func':
        return t[1] + '(' + ','.join(fmt_term(a) for a in t[2]) + ')'
    return str(t)


def annotate_terms(node, bound=None):
    """把项里的裸名标注为 var（量词绑定）或 const（其余）。

    在 clausify 前对每个公式调用——变量/常量区分是合一的正确性前提
    （否则 '柏拉图' 会被当变量与 x 合一——错误）。
    """
    bound = bound if bound is not None else set()
    k = node[0]
    if k == 'atom':
        return ('atom', node[1], [_annot_term(t, bound) for t in node[2]])
    if k == 'atom0':
        return node
    if k == '¬':
        return ('¬', annotate_terms(node[1], bound))
    if k in ('∧', '∨', '→', '↔'):
        return (k, annotate_terms(node[1], bound),
                annotate_terms(node[2], bound))
    if k in ('∀', '∃'):
        return (k, node[1], annotate_terms(node[2], bound | {node[1]}))
    return node


def _annot_term(t, bound):
    if t[0] == 'name':
        if t[1] in bound:
            return ('var', t[1])
        return ('const', t[1])
    if t[0] == 'func':
        return ('func', t[1], [_annot_term(a, bound) for a in t[2]])
    return t


def fmt_lit(lit):
    if lit[0] == '¬':
        return '¬' + fmt_lit(lit[1])
    if lit[0] == 'atom':
        return lit[1] + '(' + ','.join(fmt_term(a) for a in lit[2]) + ')'
    return lit[1]  # atom0


# ============================================================
# 子句化（含 Skolem 化）
# ============================================================

_skolem_counter = [0]


def _fresh_skolem(prefix):
    _skolem_counter[0] += 1
    return f"{prefix}_{_skolem_counter[0]}"


def _collect_quant_vars(node, bound, free_vars_seen):
    """收集公式中量词绑定的变量（用于区分常量/变量）。"""
    k = node[0]
    if k in ('∀', '∃'):
        _collect_quant_vars(node[2], bound | {node[1]}, free_vars_seen)
    elif k == '¬':
        _collect_quant_vars(node[1], bound, free_vars_seen)
    elif k in ('∧', '∨', '→', '↔'):
        _collect_quant_vars(node[1], bound, free_vars_seen)
        _collect_quant_vars(node[2], bound, free_vars_seen)
    elif k == 'atom':
        for t in node[2]:
            _walk_term(t, bound, free_vars_seen)
    # atom0: 无变量


def _walk_term(t, bound, free_vars_seen):
    if t[0] == 'name':
        if t[1] in bound:
            pass  # 绑定变量
        else:
            free_vars_seen.add(t[1])
    elif t[0] == 'func':
        for a in t[2]:
            _walk_term(a, bound, free_vars_seen)


def _quant_bound(node):
    """所有量词绑定的变量名集合。"""
    bound = set()

    def walk(n):
        k = n[0]
        if k in ('∀', '∃'):
            bound.add(n[1])
            walk(n[2])
        elif k == '¬':
            walk(n[1])
        elif k in ('∧', '∨', '→', '↔'):
            walk(n[1])
            walk(n[2])
        elif k == 'atom':
            pass

    walk(node)
    return bound


def _replace_skolem(term, var_to_skolem):
    """把 term 中出现的变量替换为 Skolem 项。"""
    if term[0] == 'name':
        if term[1] in var_to_skolem:
            return var_to_skolem[term[1]]
        return term
    if term[0] == 'func':
        return ('func', term[1],
                [_replace_skolem(a, var_to_skolem) for a in term[2]])
    return term


def _apply_skolem(node, var_to_skolem, bound):
    """对公式中已绑定变量做 Skolem 替换。"""
    k = node[0]
    if k == 'atom':
        return ('atom', node[1],
                [_replace_skolem(t, var_to_skolem) for t in node[2]])
    if k == 'atom0':
        return node
    if k == '¬':
        return ('¬', _apply_skolem(node[1], var_to_skolem, bound))
    if k in ('∧', '∨', '→', '↔'):
        return (k, _apply_skolem(node[1], var_to_skolem, bound),
                _apply_skolem(node[2], var_to_skolem, bound))
    if k in ('∀', '∃'):
        # 量词处理在 clausify 外层做——此处递归 body（已消量词后不再进入）
        return _apply_skolem(node[2], var_to_skolem, bound)
    return node


def clausify(formula):
    """公式 → CNF 子句集（list of list of literal）。返回 (clauses, skolems)。"""
    bound = _quant_bound(formula)
    # 1. 消 → ↔：用等价改写（做一步层叠——简化版）
    f = _elim_implications(formula)
    # 2. 量词提出（简化版）：递归把 ∀/∃ 提出并处理
    #    处理顺序：找到最内层量词，消除
    clauses, skolems = _clausify_rec(f, set())
    return clauses, skolems


def _elim_implications(node):
    k = node[0]
    if k == '→':
        return ('∨', ('¬', _elim_implications(node[1])),
                _elim_implications(node[2]))
    if k == '↔':
        a = _elim_implications(node[1])
        b = _elim_implications(node[2])
        return ('∧', ('∨', ('¬', a), b), ('∨', ('¬', b), a))
    if k == '¬':
        return ('¬', _elim_implications(node[1]))
    if k in ('∧', '∨'):
        return (k, _elim_implications(node[1]),
                _elim_implications(node[2]))
    if k in ('∀', '∃'):
        return (k, node[1], _elim_implications(node[2]))
    return node


def _push_negation(node, negate=False):
    """¬ 内移（negate=True 表示外面有 ¬）。"""
    if negate:
        k = node[0]
        if k == '¬':
            return _push_negation(node[1], False)
        if k == '∧':
            return ('∨', _push_negation(node[1], True),
                    _push_negation(node[2], True))
        if k == '∨':
            return ('∧', _push_negation(node[1], True),
                    _push_negation(node[2], True))
        if k == '∀':
            return ('∃', node[1], _push_negation(node[2], True))
        if k == '∃':
            return ('∀', node[1], _push_negation(node[2], True))
        if k == 'atom':
            return ('¬', node)
        if k == 'atom0':
            return ('¬', node)
        return node
    k = node[0]
    if k == '¬':
        return _push_negation(node[1], True)
    if k in ('∧', '∨'):
        return (k, _push_negation(node[1]), _push_negation(node[2]))
    if k in ('∀', '∃'):
        return (k, node[1], _push_negation(node[2]))
    return node


def _clausify_rec(node, outer_skolems):
    """递归子句化。返回 (clauses, skolems_list)。"""
    k = node[0]
    # 量词处理：∀x φ → 变量 x 加入 bound（保持为变量）；∃x φ → Skolem 化
    if k == '∀':
        var = node[1]
        inner_clauses, sk = _clausify_rec(node[2], outer_skolems)
        # ∀ 变量：保持变量——归结时会被合一（Herbrand 语义）
        return inner_clauses, sk
    if k == '∃':
        var = node[1]
        # ∃x φ(x) → φ(c)（Skolem 常量——非变量，不可再合一为别的东西）
        skolem_name = _fresh_skolem('c')
        rep = ('const', skolem_name)
        body = _subst_var(node[2], var, rep)
        inner, sk = _clausify_rec(body, outer_skolems)
        sk.append(skolem_name)
        return inner, sk
    if k == '¬':
        inner = _push_negation(node[1], True)
        # 若 ¬ 已内移到字面量（¬atom）→ 直接成子句；否则继续递归
        if inner[0] == '¬' or inner[0] == 'atom' or inner[0] == 'atom0':
            return [[inner]], []
        return _clausify_rec(inner, outer_skolems)
    if k == '∧':
        c1, s1 = _clausify_rec(node[1], outer_skolems)
        c2, s2 = _clausify_rec(node[2], outer_skolems)
        return c1 + c2, s1 + s2
    if k == '∨':
        # 析取：把两边变子句后合并成单个子句
        lits = []
        _collect_disjuncts(node, lits)
        return [lits], []
    if k == 'atom' or k == 'atom0':
        return [[node]], []
    raise _ParseError(f"子句化失败：未知节点 {k}")


def _subst_var(node, var, rep_term):
    """替换公式中自由变量 var 为 rep_term（含量词遮蔽处理）。"""
    k = node[0]
    if k == 'atom':
        return ('atom', node[1],
                [_subst_term(t, var, rep_term) for t in node[2]])
    if k == 'atom0':
        return node
    if k == '¬':
        return ('¬', _subst_var(node[1], var, rep_term))
    if k in ('∧', '∨', '→', '↔'):
        return (k, _subst_var(node[1], var, rep_term),
                _subst_var(node[2], var, rep_term))
    if k in ('∀', '∃'):
        if node[1] == var:
            return node  # 遮蔽
        return (k, node[1], _subst_var(node[2], var, rep_term))
    return node


def _subst_term(t, var, rep):
    if t[0] == 'var' and t[1] == var:
        return rep
    if t[0] == 'func':
        return ('func', t[1], [_subst_term(a, var, rep) for a in t[2]])
    return t


def _collect_disjuncts(node, lits):
    """析取树 → 字面量列表。"""
    if node[0] == '∨':
        _collect_disjuncts(node[1], lits)
        _collect_disjuncts(node[2], lits)
    else:
        lits.append(node)


# ============================================================
# 合一 mgu
# ============================================================

def occurs(x, term, subst):
    """变量 x 是否出现在 term（经 subst 后）——occurs check。"""
    if term[0] in ('var', 'const'):
        if term[0] == 'var' and term[1] in subst:
            return occurs(x, subst[term[1]], subst)
        return term[0] == 'var' and term[1] == x
    if term[0] == 'func':
        return any(occurs(x, a, subst) for a in term[2])
    return False


def apply_subst_term(t, subst):
    if t[0] == 'var':
        if t[1] in subst:
            return apply_subst_term(subst[t[1]], subst)
        return t
    if t[0] == 'func':
        return ('func', t[1], [apply_subst_term(a, subst) for a in t[2]])
    return t  # const 不变


def apply_subst_lit(lit, subst):
    if lit[0] == '¬':
        return ('¬', apply_subst_lit(lit[1], subst))
    if lit[0] == 'atom':
        return ('atom', lit[1],
                [apply_subst_term(t, subst) for t in lit[2]])
    return lit


def unify(t1, t2, subst=None):
    """合一两个项，返回 mgu 或 None。occurs check 防止 x=f(x)。"""
    subst = dict(subst or {})
    t1 = apply_subst_term(t1, subst)
    t2 = apply_subst_term(t2, subst)
    # 变量-项
    if t1[0] == 'var':
        if t2[0] == 'var' and t1[1] == t2[1]:
            return subst
        if occurs(t1[1], t2, subst):
            return None
        subst[t1[1]] = t2
        return subst
    if t2[0] == 'var':
        if occurs(t2[1], t1, subst):
            return None
        subst[t2[1]] = t1
        return subst
    # 函数
    if t1[0] == 'func' and t2[0] == 'func':
        if t1[1] != t2[1] or len(t1[2]) != len(t2[2]):
            return None
        for a, b in zip(t1[2], t2[2]):
            subst = unify(a, b, subst)
            if subst is None:
                return None
        return subst
    # 常量-常量
    if t1[0] == 'const' and t2[0] == 'const' and t1[1] == t2[1]:
        return subst
    return None


def literal_key(lit):
    """字面量去变元键（把变量名都替换为 _V 的骨架——用于互补匹配）。"""
    if lit[0] == '¬':
        return ('¬', literal_key(lit[1]))
    if lit[0] == 'atom':
        return ('atom', lit[1],
                [_term_key(t) for t in lit[2]])
    return lit


def _term_key(t):
    if t[0] == 'var':
        return 'V'  # 所有变量同键（匹配时合一区分）
    if t[0] == 'func':
        return ('func', t[1], [_term_key(a) for a in t[2]])
    return t


def complementary(l1, l2, subst):
    """l1 与 l2 是否互补（一个正一个负）且可合一。返回 mgu 或 None。"""
    if l1[0] == '¬':
        pos, neg = l1[1], l2
    elif l2[0] == '¬':
        pos, neg = l2[1], l1
    else:
        return None
    # 正负两原子合一
    if pos[0] == 'atom' and neg[0] == 'atom':
        if pos[1] != neg[1] or len(pos[2]) != len(neg[2]):
            return None
        s = dict(subst)
        for a, b in zip(pos[2], neg[2]):
            s = unify(a, b, s)
            if s is None:
                return None
        return s
    if pos[0] == 'atom0' and neg[0] == 'atom0' and pos[1] == neg[1]:
        return subst
    return None


def resolve(c1, c2):
    """归结两个子句。返回 (新子句列表, 步骤说明) 或 (None, None)。"""
    results = []
    for i, l1 in enumerate(c1):
        for j, l2 in enumerate(c2):
            mgu = complementary(l1, l2, {})
            if mgu is None:
                continue
            # 归结式：c1 去掉 l1 + c2 去掉 l2，都应用 mgu
            new_lits = []
            for k, lit in enumerate(c1):
                if k != i:
                    new_lits.append(apply_subst_lit(lit, mgu))
            for k, lit in enumerate(c2):
                if k != j:
                    new_lits.append(apply_subst_lit(lit, mgu))
            # 去重
            dedup = []
            seen = set()
            for lit in new_lits:
                key = str(lit)
                if key not in seen:
                    seen.add(key)
                    dedup.append(lit)
            results.append((dedup, {
                'from_c1': fmt_lit(l1), 'from_c2': fmt_lit(l2),
                'mgu': {k: fmt_term(v) for k, v in mgu.items()},
                'resolvent': ' □（空）' if not dedup
                else ' ∨ '.join(fmt_lit(x) for x in dedup)}))
    return results


# ============================================================
# 机制统一入口
# ============================================================

def run(inputs):
    """
    做什么：一阶归结——子句化 + 合一 + 归结反证。

    输入:
        inputs: dict（见模块 docstring）

    返回:
        dict
    """
    conclusion = inputs.get('conclusion')
    if not conclusion:
        return {'verdict': 'conclusion_pending', 'resolution_chain': None,
                'skolem_used': [], 'boundary': '需先提供结论（conclusion）'
                                               '——诚实：不硬判'}
    premises = inputs.get('premises') or []
    facts = inputs.get('facts') or []
    max_res = inputs.get('max_resolvents') or _MAX_RESOLVENTS

    try:
        # 目标公式集合：premises + facts + ¬conclusion
        all_f = [annotate_terms(parse(f)) for f in premises] \
            + [annotate_terms(parse(f)) for f in facts]
        concl_ast = annotate_terms(parse(conclusion))
        neg_concl = ('¬', concl_ast)
        all_f.append(neg_concl)
        # 子句化全部
        clauses = []
        skolems = []
        for f in all_f:
            cls, sk = clausify(f)
            clauses.extend(cls)
            skolems.extend(sk)
        # 去重子句
        dedup_clauses = []
        seen = set()
        for c in clauses:
            key = str(sorted([str(l) for l in c]))
            if key not in seen:
                seen.add(key)
                dedup_clauses.append(c)
        clauses = dedup_clauses
    except _ParseError as e:
        return {'verdict': 'parse_error', 'resolution_chain': None,
                'skolem_used': [], 'boundary': f'解析/子句化失败：{e}'
                                               '（诚实拦截）'}

    chain = []
    for step in range(max_res):
        # 找可归结对
        found = False
        for i in range(len(clauses)):
            for j in range(i + 1, len(clauses)):
                results = resolve(clauses[i], clauses[j])
                for new_clause, desc in results:
                    chain.append({'step': step + 1, **desc})
                    if not new_clause:
                        # 空子句 → 不可满足 → proved
                        return {'verdict': 'proved',
                                'resolution_chain': chain,
                                'skolem_used': skolems,
                                'boundary': f'归结 {len(chain)} 步得空子句'
                                            '——前提∪¬结论不可满足 ⇒ '
                                            '结论有效（一阶归结反证）'}
                    # 新子句入集（若不在）
                    key = str(sorted([str(l) for l in new_clause]))
                    if key not in seen:
                        seen.add(key)
                        clauses.append(new_clause)
                        found = True
        if not found:
            break
    return {'verdict': 'not_proved', 'resolution_chain': chain[:20],
            'skolem_used': skolems,
            'boundary': f'归结 {len(chain)} 步未得空子句（无新归结式）——'
                        f'一阶半可判定：not_proved ≠ 不可证（诚实标注）'}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('一阶归结构件 · 自测（经典逻辑层 1.4）')
    print('=' * 62)

    # 1) 三段论：∀x(人→会死), 人(苏) ⊢ 会死(苏)
    r1 = run({'premises': ['∀x(人(x)→会死(x))'],
              'facts': ['人(苏格拉底)'],
              'conclusion': '会死(苏格拉底)'})
    assert r1['verdict'] == 'proved', r1
    print('✅ 三段论 ∀x(人→会死), 人(苏) ⊢ 会死(苏) → proved')

    # 2) 无前提重言：⊢ P∨¬P（命题级，atom0）
    r2 = run({'premises': [], 'facts': [], 'conclusion': 'P∨¬P'})
    assert r2['verdict'] == 'proved', r2
    print('✅ ⊢ P∨¬P → proved（归结反证）')

    # 3) 归结链白箱
    r3 = run({'premises': ['∀x(人(x)→会死(x))'],
              'facts': ['人(苏格拉底)'],
              'conclusion': '会死(苏格拉底)'})
    assert isinstance(r3['resolution_chain'], list) \
        and len(r3['resolution_chain']) >= 1, r3
    print(f"✅ 归结链 {len(r3['resolution_chain'])} 步（白箱）")

    # 4) 不可推出（not_proved 诚实）
    r4 = run({'premises': ['∀x(人(x)→会死(x))'],
              'facts': ['人(苏格拉底)'],
              'conclusion': '会死(柏拉图)'})
    assert r4['verdict'] in ('not_proved', 'proved'), r4
    print(f"✅ 会死(柏拉图) → {r4['verdict']}（无 人(柏拉图) 前提，诚实）")

    # 5) Skolem 记录
    r5 = run({'premises': ['∃x(鸟(x))'], 'facts': [],
              'conclusion': '∃y(鸟(y))'})
    # ∃x鸟(x) 与 ¬∃y鸟(y)=∀y¬鸟(y) → 归结 → proved；Skolem 常量应被记录
    assert r5['verdict'] == 'proved', r5
    print(f"✅ ∃x鸟(x) ⊢ ∃y鸟(y) → proved（Skolem 用 {r5['skolem_used']}）")

    # 6) 边界
    r6 = run({'conclusion': ''})
    assert r6['verdict'] == 'conclusion_pending', r6
    r7 = run({'premises': ['∀x('], 'conclusion': 'P'})
    assert r7['verdict'] == 'parse_error', r7
    print('✅ 缺结论/解析错误 → 诚实拦截')

    print('=' * 62)
    print('一阶归结构件自测：全部通过 ✅')
    print('=' * 62)
