# -*- coding: utf-8 -*-
"""
propositional.py — 命题逻辑构件（第 1 层经典逻辑地基）
========================================================
概念来源：经典逻辑（命题逻辑标准语义——非落落原创，经典共识）
公式卡：docs/formulas/propositional.md（随构件补齐）

本构件做什么：
    判定命题公式的真假、推理有效性、可满足性、重言式/矛盾式。
    经典二值语义（真/假），只判经典框架内能算的；原子过多诚实报规模限制。

统一接口：
    run(inputs: dict) -> dict
    输入:
        formula: str，命题公式（原子+ ¬ ∧ ∨ → ↔ + 括号）
        premises: list[str]，前提集（validity 模式用，可省）
        conclusion: str，结论（validity 模式用）
        mode: 'truth_table' | 'validity' | 'satisfiable' | 'kind'
    输出:
        verdict: str
        counterexample: dict 或 null（invalid 时反例指派）
        truth_table: list 或 null
        atoms: list[str]
        boundary: str（诚实边界说明）
"""

PORTS = {
    'in': {'formula': 'str', 'premises': 'list?',
           'conclusion': 'str?', 'mode': 'str?'},
    'out': {'verdict': 'str', 'counterexample': 'dict',
            'truth_table': 'list', 'atoms': 'list',
            'boundary': 'str'},
}

# 联结词优先级（低→高）：↔ → ∨ ∧ ¬
_CONNECTIVES = {'↔', '→', '∨', '∧', '¬'}
_PRECEDENCE = {'↔': 1, '→': 2, '∨': 3, '∧': 4}
_MAX_ATOMS = 10  # 真值表枚举上限（诚实边界：>10 提示规模限制）


class _ParseError(ValueError):
    """公式解析错误。"""


# ---------- 词法/语法：中缀 → AST ----------

def _tokenize(s):
    """把公式切成 token：原子、联结词、括号。"""
    tokens = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in '()':
            tokens.append(ch)
            i += 1
        elif ch in _CONNECTIVES:
            tokens.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        else:
            # 原子：连续非联结词非括号非空格字符
            j = i
            while j < len(s) and s[j] not in '()' and s[j] not in _CONNECTIVES and s[j] != ' ':
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens


def _parse_impl(tokens, pos, min_prec):
    """Pratt 解析：返回 (AST, 新pos)。"""
    if pos >= len(tokens):
        raise _ParseError("公式不完整")
    tok = tokens[pos]
    if tok == '(':
        node, pos = _parse_impl(tokens, pos + 1, 1)
        if pos >= len(tokens) or tokens[pos] != ')':
            raise _ParseError("缺右括号")
        pos += 1
    elif tok == '¬':
        node, pos = _parse_impl(tokens, pos + 1, 4)  # ¬ 优先级最高
        node = ('¬', node)
    elif tok in _CONNECTIVES:
        raise _ParseError(f"联结词 '{tok}' 缺左操作数")
    else:
        node = ('atom', tok)
        pos += 1
    # 处理后续二元联结词
    while pos < len(tokens):
        op = tokens[pos]
        if op == ')':
            break
        if op not in _PRECEDENCE:
            raise _ParseError(f"无法识别的符号 '{op}'")
        prec = _PRECEDENCE[op]
        if prec < min_prec:
            break
        right, pos = _parse_impl(tokens, pos + 1, prec + 1)
        node = (op, node, right)
    return node, pos


def parse(formula):
    """公式字符串 → AST。"""
    tokens = _tokenize(formula)
    if not tokens:
        raise _ParseError("空公式")
    ast, pos = _parse_impl(tokens, 0, 1)
    if pos != len(tokens):
        raise _ParseError(f"多余内容: {tokens[pos:]}")
    return ast


def atoms_of(ast):
    """AST → 原子集合（按出现序）。"""
    result = []
    seen = set()

    def walk(node):
        if node[0] == 'atom':
            a = node[1]
            if a not in seen:
                seen.add(a)
                result.append(a)
        elif node[0] == '¬':
            walk(node[1])
        else:
            walk(node[1])
            walk(node[2])

    walk(ast)
    return result


def eval_ast(ast, assignment):
    """在指派下求值（经典二值）。"""
    op = ast[0]
    if op == 'atom':
        return bool(assignment[ast[1]])
    if op == '¬':
        return not eval_ast(ast[1], assignment)
    if op == '∧':
        return eval_ast(ast[1], assignment) and eval_ast(ast[2], assignment)
    if op == '∨':
        return eval_ast(ast[1], assignment) or eval_ast(ast[2], assignment)
    if op == '→':
        return (not eval_ast(ast[1], assignment)) or eval_ast(ast[2], assignment)
    if op == '↔':
        return eval_ast(ast[1], assignment) == eval_ast(ast[2], assignment)
    raise _ParseError(f"未知节点 {op}")


def _all_assignments(atoms):
    """生成所有真值指派（2^n 个 dict）。"""
    n = len(atoms)
    for mask in range(1 << n):
        yield {atoms[i]: bool((mask >> (n - 1 - i)) & 1) for i in range(n)}


# ---------- 判定 ----------

def _check_size(atoms):
    if len(atoms) > _MAX_ATOMS:
        raise ValueError(
            f"原子数 {len(atoms)} 超过枚举上限 {_MAX_ATOMS}——"
            f"真值表指数爆炸，本构件不硬算（诚实边界：建议拆式/转谓词）")


def truth_table(formula):
    """生成完整真值表。"""
    ast = parse(formula)
    atoms = atoms_of(ast)
    _check_size(atoms)
    rows = []
    for assign in _all_assignments(atoms):
        val = eval_ast(ast, assign)
        rows.append({**assign, '_result': val})
    return atoms, rows


def satisfies(formula):
    """可满足性：有没有指派使公式为真。"""
    atoms, rows = truth_table(formula)
    any_true = any(r['_result'] for r in rows)
    return atoms, any_true, rows


def kind(formula):
    """公式类型：重言式 / 矛盾式 / 可满足（非重言）。"""
    atoms, rows = truth_table(formula)
    vals = [r['_result'] for r in rows]
    if all(vals):
        return atoms, 'tautology'
    if not any(vals):
        return atoms, 'contradiction'
    return atoms, 'contingent'


def validity(premises, conclusion):
    """有效性：前提都真时结论必真吗？无效给反例。"""
    p_asts = [parse(p) for p in premises]
    c_ast = parse(conclusion)
    all_atoms = []
    seen = set()
    for ast in p_asts + [c_ast]:
        for a in atoms_of(ast):
            if a not in seen:
                seen.add(a)
                all_atoms.append(a)
    _check_size(all_atoms)
    for assign in _all_assignments(all_atoms):
        prems_ok = all(eval_ast(a, assign) for a in p_asts)
        concl_ok = eval_ast(c_ast, assign)
        if prems_ok and not concl_ok:
            # 反例指派：只保留出现过的原子
            counter = {a: assign[a] for a in all_atoms if a in assign}
            return all_atoms, 'invalid', counter
    return all_atoms, 'valid', None


# ---------- 机制统一入口 ----------

def run(inputs):
    """
    做什么：命题逻辑判定——真假/有效性/可满足性/公式类型。

    输入:
        inputs: dict
            formula: str（必填）
            premises/conclusion: list/str（validity 模式）
            mode: str（truth_table/validity/satisfiable/kind，默认按有无 premises 推断）

    返回:
        dict: {verdict, counterexample, truth_table, atoms, boundary}
    """
    formula = inputs.get('formula')
    premises = inputs.get('premises') or []
    conclusion = inputs.get('conclusion')
    mode = inputs.get('mode')

    # validity 模式用 premises+conclusion，可无 formula
    if mode == 'validity' or (premises and conclusion):
        if not premises:
            return {'verdict': 'premises_pending', 'counterexample': None,
                    'truth_table': None, 'atoms': [],
                    'boundary': '有效性判定需前提集（premises）——诚实拦截'}
        if not conclusion:
            return {'verdict': 'conclusion_pending', 'counterexample': None,
                    'truth_table': None, 'atoms': [],
                    'boundary': '有效性判定需结论（conclusion）——诚实拦截'}
        try:
            atoms, verdict, counter = validity(premises, conclusion)
        except (_ParseError, ValueError) as e:
            return {'verdict': 'parse_error' if isinstance(e, _ParseError)
                    else 'size_limit', 'counterexample': None,
                    'truth_table': None, 'atoms': [],
                    'boundary': str(e)}
        label = 'valid' if verdict == 'valid' else 'invalid'
        cn = _fmt_assignment(counter) if counter else None
        return {
            'verdict': label,
            'counterexample': cn,
            'truth_table': None,
            'atoms': atoms,
            'boundary': '经典二值语义；invalid 时反例即前提真结论假的指派'
        }

    if not formula:
        return {'verdict': 'formula_pending', 'counterexample': None,
                'truth_table': None, 'atoms': [],
                'boundary': '需先提供命题公式（如 "((P→Q) ∧ P) → Q"）——诚实：不硬判'}

    try:
        if mode == 'truth_table':
            atoms, rows = truth_table(formula)
            return {'verdict': 'truth_table', 'counterexample': None,
                    'truth_table': rows, 'atoms': atoms,
                    'boundary': f'真值表 {len(rows)} 行（原子 {len(atoms)} 个）'}

        if mode == 'satisfiable':
            atoms, any_true, _ = satisfies(formula)
            return {'verdict': 'satisfiable' if any_true else 'unsatisfiable',
                    'counterexample': None, 'truth_table': None,
                    'atoms': atoms,
                    'boundary': '存在真值指派使公式为真 = 可满足'}

        # 默认：公式类型（重言/矛盾/可满足）
        atoms, k = kind(formula)
        label = {'tautology': 'tautology', 'contradiction': 'contradiction',
                 'contingent': 'contingent'}[k]
        return {'verdict': label, 'counterexample': None,
                'truth_table': None, 'atoms': atoms,
                'boundary': '经典二值语义；contingent=既非重言也非矛盾'}
    except _ParseError as e:
        return {'verdict': 'parse_error', 'counterexample': None,
                'truth_table': None, 'atoms': [],
                'boundary': f'公式解析失败：{e}（诚实拦截，不硬算）'}
    except ValueError as e:
        return {'verdict': 'size_limit', 'counterexample': None,
                'truth_table': None, 'atoms': [],
                'boundary': str(e)}


def _fmt_assignment(assign):
    """反例指派 → 可读 dict（原子名: 真/假）。"""
    return {k: ('真' if v else '假') for k, v in sorted(assign.items())}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('命题逻辑构件 · 自测（经典逻辑层 1.1）')
    print('=' * 62)

    # 1) 三段论有效：((P→Q) ∧ P) → Q
    r1 = run({'premises': ['P→Q', 'P'], 'conclusion': 'Q', 'mode': 'validity'})
    assert r1['verdict'] == 'valid', f"三段论应有效: {r1}"
    print('✅ 三段论 (P→Q), P ⊢ Q → valid')

    # 2) 无效 + 反例：P∨Q → P（P=假,Q=真 时前提真结论假）
    r2 = run({'premises': ['P∨Q'], 'conclusion': 'P', 'mode': 'validity'})
    assert r2['verdict'] == 'invalid', f"应无效: {r2}"
    assert r2['counterexample'] is not None, f"应给反例: {r2}"
    print(f"✅ P∨Q ⊢ P → invalid，反例 {r2['counterexample']}")

    # 3) 排中律恒真：P∨¬P → tautology
    r3 = run({'formula': 'P∨¬P'})
    assert r3['verdict'] == 'tautology', f"排中律应重言: {r3}"
    print('✅ P∨¬P → tautology（排中律）')

    # 4) 矛盾式：P∧¬P
    r4 = run({'formula': 'P∧¬P'})
    assert r4['verdict'] == 'contradiction', f"应矛盾: {r4}"
    print('✅ P∧¬P → contradiction')

    # 5) 可满足性：P∧Q
    r5 = run({'formula': 'P∧Q', 'mode': 'satisfiable'})
    assert r5['verdict'] == 'satisfiable', f"应可满足: {r5}"
    print('✅ P∧Q → satisfiable')

    # 6) 真值表
    r6 = run({'formula': 'P→Q', 'mode': 'truth_table'})
    assert r6['verdict'] == 'truth_table' and len(r6['truth_table']) == 4
    print(f"✅ P→Q 真值表 4 行")

    # 7) 解析错误诚实拦截
    r7 = run({'formula': 'P→'})
    assert r7['verdict'] == 'parse_error', f"应解析错误: {r7}"
    print(f"✅ 残缺公式 'P→' → parse_error（诚实拦截）")

    # 8) 缺公式
    r8 = run({})
    assert r8['verdict'] == 'formula_pending', f"应待公式: {r8}"
    print('✅ 空输入 → formula_pending')

    print('=' * 62)
    print('命题逻辑构件自测：全部通过 ✅')
    print('=' * 62)
