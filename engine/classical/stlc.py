# -*- coding: utf-8 -*-
"""
stlc.py — 简单类型 λ 演算构件（第 1 层经典逻辑基础 1.9）
=========================================================
概念来源：经典类型论（Church 简单类型 + Curry-Howard——非落落原创，经典共识）
详规：《逻辑建模引擎_经典逻辑层详规》七·补F
公式卡：docs/formulas/stlc.md

与 1.6（无类型 λ）的关系：
    1.6 给 Y 组合子（无类型自指，可写 Ω 不死循环）；
    1.9 用类型**拦住自应用**（λx.x x 报 type_error）——类型正确 ⇒
    必然终止（强规范化）。双视角对照：类型能阻止不死循环，代价是
    表达力下降（不能 Y）。

本构件做什么：
    STLC 类型检查与推导——Γ ⊢ M : A（类型规则）+ Curry-Howard 对照
    （类型=命题、程序=证明）。

诚实边界：
    - STLC 强规范化：所有可类型化项都终止（无 Ω）——类型拦自应用；
    - 不自应用 = 类型系统挡住自指——与 1.6 的 Y 对照；
    - System F（多态）/依赖类型 = 后补，不首期。

统一接口：
    run(inputs: dict) -> dict
    输入:
        expr: str，λ 项（含类型标注 λx:A.M 或上下文推断）
        context: dict，类型上下文 {变量: 类型}（可省）
        expected: str 或 None，期望类型（可省——自动推导）
    输出:
        verdict: 'typed' | 'type_error' | 'expr_pending' | 'parse_error'
        inferred: str 或 null（推导的类型）
        derivation: list[step] 或 null（类型推导白箱）
        boundary: str
"""

PORTS = {
    'in': {'expr': 'str?', 'context': 'dict?', 'expected': 'str?'},
    'out': {'verdict': 'str', 'inferred': 'str', 'derivation': 'list',
            'boundary': 'str'},
}


class _TypeError_(ValueError):
    pass


class _ParseError(ValueError):
    pass


# ============================================================
# 类型语法：T ::= A | T→T（→右结合）；项含标注 λx:A.M
# ============================================================

def parse_type(s):
    """类型串 → AST。'A→B→C' = A→(B→C)。"""
    toks = s.replace('→', ' → ').split()
    if not toks:
        raise _ParseError("空类型")

    def parse_atom():
        t = toks.pop(0) if toks else None
        if t == '(':
            ty = parse_arrow()
            if not toks or toks.pop(0) != ')':
                raise _ParseError("类型缺右括号")
            return ty
        if t is None or t == '→':
            raise _ParseError(f"类型原子非法 '{t}'")
        return t

    def parse_arrow():
        left = parse_atom()
        if toks and toks[0] == '→':
            toks.pop(0)
            right = parse_arrow()
            return ('→', left, right)
        return left

    ty = parse_arrow()
    if toks:
        raise _ParseError(f"类型多余内容: {toks}")
    return ty


def fmt_type(t):
    if isinstance(t, tuple):
        return f"({fmt_type(t[1])}→{fmt_type(t[2])})"
    return t


# ============================================================
# λ 项语法（含类型标注）：λx:A.M；应用左结合；变量
# ============================================================

def _tokenize(s):
    toks = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in 'λ.:(),':
            toks.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        elif ch == '\\':
            toks.append('λ')
            i += 1
        elif s.startswith('→', i):
            toks.append('→')
            i += 2
        else:
            j = i
            while j < n and s[j] not in 'λ.:(), ' and s[j] != '→' \
                    and s[j] != '\\':
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


def parse_expr(s):
    """λ 项（含标注）→ AST。
    Var(name) | Lam(param, param_ty, body) | App(fn, arg)
    param_ty 可为 None（未标注）。"""
    toks = _tokenize(s)
    if not toks:
        raise _ParseError("空项")
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def next_tok():
        nonlocal pos
        t = peek()
        pos += 1
        return t

    def parse_type_tokens():
        """从当前 token 流读类型（直到右括号/逗号/末尾）。"""
        nonlocal pos
        buf = []
        depth = 0
        while pos < len(toks):
            t = toks[pos]
            if t == '(':
                depth += 1
                buf.append(t)
                pos += 1
            elif t == ')':
                if depth == 0:
                    break
                depth -= 1
                buf.append(t)
                pos += 1
            elif t in (':', ',', '.'):
                break
            else:
                buf.append(t)
                pos += 1
        if not buf:
            return None
        return parse_type(''.join(buf).replace('(', ' ( ').replace(')', ' ) '))

    def parse_abs():
        next_tok()  # λ
        param = next_tok()
        if param in (None, '.') or param in ':(),':
            raise _ParseError(f"λ 后应为变量名，得到 '{param}'")
        param_ty = None
        if peek() == ':':
            next_tok()
            param_ty = parse_type_tokens()
        if peek() != '.':
            raise _ParseError(f"λ{param} 后应为 '.'")
        next_tok()
        body = parse_application()
        return ('lam', param, param_ty, body)

    def parse_atom():
        t = peek()
        if t is None:
            raise _ParseError("项意外结束")
        if t == 'λ':
            return parse_abs()
        if t == '(':
            next_tok()
            inner = parse_application()
            if next_tok() != ')':
                raise _ParseError("缺右括号")
            return inner
        if t in '.:(),→':
            raise _ParseError(f"意外符号 '{t}'")
        next_tok()
        return ('var', t)

    def parse_application():
        first = parse_atom()
        while True:
            t = peek()
            if t is None or t == ')':
                break
            if t in '.:(),→':
                break
            if t == 'λ' or t == '(' or t not in '.:(),→':
                arg = parse_atom()
                first = ('app', first, arg)
            else:
                break
        return first

    node = parse_application()
    if pos != len(toks):
        raise _ParseError(f"多余内容: {toks[pos:]}")
    return node


# ============================================================
# 类型检查（双向：infer 主 + expected 校验）
# ============================================================

def infer(node, ctx, derivation):
    """推导项的类型。返回 (type, derivation) 或抛 _TypeError_。"""
    k = node[0]
    if k == 'var':
        name = node[1]
        if name not in ctx:
            raise _TypeError_(f"变量 {name} 不在上下文中")
        derivation.append({'rule': 'var', 'detail': f'{name} : '
                          f'{fmt_type(ctx[name])}'})
        return ctx[name]
    if k == 'lam':
        _, param, param_ty, body = node
        # 参数类型：标注或从上下文？STLC 需标注或推断——标注优先
        if param_ty is None:
            raise _TypeError_(
                f"λ{param} 缺类型标注——STLC 需显式类型（或提供 expected）")
        new_ctx = dict(ctx)
        new_ctx[param] = param_ty
        body_ty = infer(body, new_ctx, derivation)
        ty = ('→', param_ty, body_ty)
        derivation.append({'rule': '→引入',
                           'detail': f'λ{param}:{fmt_type(param_ty)}.'
                           f'{fmt_type(body_ty)} : {fmt_type(ty)}'})
        return ty
    if k == 'app':
        _, fn, arg = node
        fn_ty = infer(fn, ctx, derivation)
        if not isinstance(fn_ty, tuple) or fn_ty[0] != '→':
            raise _TypeError_(f"应用：{fmt_type(fn_ty)} 不是函数类型")
        arg_ty = infer(arg, ctx, derivation)
        # 参数类型匹配（类型变量无——STLC 需结构一致）
        if fmt_type(arg_ty) != fmt_type(fn_ty[1]):
            raise _TypeError_(
                f"应用类型不匹配：参数 {fmt_type(arg_ty)} 期望 "
                f"{fmt_type(fn_ty[1])}")
        derivation.append({'rule': '→消去',
                           'detail': f'{fmt_type(fn_ty)} 应用 '
                           f'{fmt_type(arg_ty)} : {fmt_type(fn_ty[2])}'})
        return fn_ty[2]
    raise _TypeError_(f"未知节点 {k}")


# ============================================================
# 机制统一入口
# ============================================================

def run(inputs):
    """
    做什么：STLC 类型检查/推导。

    输入:
        inputs: dict（见模块 docstring）

    返回:
        dict
    """
    expr_s = inputs.get('expr')
    if not expr_s:
        return {'verdict': 'expr_pending', 'inferred': None,
                'derivation': None,
                'boundary': '需先提供 λ 项（expr，如 "λx:A.x"）——诚实：不硬判'}
    try:
        node = parse_expr(expr_s)
    except _ParseError as e:
        return {'verdict': 'parse_error', 'inferred': None,
                'derivation': None,
                'boundary': f'项解析失败：{e}（诚实拦截，不硬算）'}

    # 上下文
    ctx = {}
    raw_ctx = inputs.get('context') or {}
    for name, ty_s in raw_ctx.items():
        try:
            ctx[name] = parse_type(ty_s)
        except _ParseError as e:
            return {'verdict': 'parse_error', 'inferred': None,
                    'derivation': None,
                    'boundary': f'上下文类型 {ty_s} 解析失败：{e}'}

    derivation = []
    try:
        ty = infer(node, ctx, derivation)
    except _TypeError_ as e:
        return {'verdict': 'type_error', 'inferred': None,
                'derivation': derivation,
                'boundary': f'类型错误：{e}（诚实拦截——STLC 类型正确 '
                            '⇒ 必然终止，拦下类型错即拦下潜在错误）'}

    inferred_s = fmt_type(ty)
    # expected 校验（若给）
    expected = inputs.get('expected')
    if expected:
        try:
            exp_ty = parse_type(expected)
        except _ParseError:
            return {'verdict': 'parse_error', 'inferred': inferred_s,
                    'derivation': derivation,
                    'boundary': f'期望类型 {expected} 解析失败——诚实拦截'}
        if fmt_type(exp_ty) != inferred_s:
            return {'verdict': 'type_error', 'inferred': inferred_s,
                    'derivation': derivation,
                    'boundary': f'推断 {inferred_s} ≠ 期望 '
                                f'{fmt_type(exp_ty)}——类型不匹配'
                                '（诚实拦截）'}

    return {'verdict': 'typed', 'inferred': inferred_s,
            'derivation': derivation,
            'boundary': f'STLC 类型检查通过：类型 = {inferred_s}'
                        '（Curry-Howard：此程序即该命题的证明）'}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('简单类型 λ（STLC）构件 · 自测（经典逻辑层 1.9）')
    print('=' * 62)

    # 1) 恒等函数：λx:A.x : A→A
    r1 = run({'expr': 'λx:A.x'})
    assert r1['verdict'] == 'typed' and r1['inferred'] == '(A→A)', r1
    print(f"✅ λx:A.x : A→A → typed（{r1['inferred']}）")

    # 2) K 组合子：λx:A.λy:B.x : A→B→A
    r2 = run({'expr': 'λx:A.λy:B.x'})
    assert r2['verdict'] == 'typed', r2
    print(f"✅ λx:A.λy:B.x → typed（{r2['inferred']}）")

    # 3) 应用：恒等应用于常量（需上下文）
    r3 = run({'expr': '(λx:A.x) c', 'context': {'c': 'A'}})
    assert r3['verdict'] == 'typed' and r3['inferred'] == 'A', r3
    print(f"✅ (λx:A.x) c : A → typed（{r3['inferred']}）")

    # 4) 自应用 λx:x.x x → type_error（STLC 拦自应用——关键特性）
    r4 = run({'expr': 'λx:A.x x'})
    assert r4['verdict'] == 'type_error', r4
    print('✅ λx:A.x x → type_error（STLC 拦住自应用——类型正确 ⇒ 终止）')

    # 5) 类型不匹配应用
    r5 = run({'expr': '(λx:A.x) c', 'context': {'c': 'B'}})
    assert r5['verdict'] == 'type_error', r5
    print('✅ 参数类型 B ≠ A → type_error')

    # 6) 缺类型标注的 λ → type_error（STLC 需显式类型）
    r6 = run({'expr': 'λx.x'})
    assert r6['verdict'] == 'type_error', r6
    print('✅ λx.x（缺标注）→ type_error（STLC 需显式类型）')

    # 7) 推导白箱
    r7 = run({'expr': 'λx:A.x'})
    assert r7['verdict'] == 'typed' and len(r7['derivation']) >= 1, r7
    print(f"✅ 推导白箱 {len(r7['derivation'])} 步")

    # 8) 边界
    r8 = run({})
    assert r8['verdict'] == 'expr_pending', r8
    r9 = run({'expr': 'λx:A.'})
    assert r9['verdict'] in ('parse_error', 'type_error'), r9
    print('✅ 缺项/残缺项 → 诚实拦截')

    print('=' * 62)
    print('简单类型 λ（STLC）构件自测：全部通过 ✅')
    print('=' * 62)
