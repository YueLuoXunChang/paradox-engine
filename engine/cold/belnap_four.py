# -*- coding: utf-8 -*-
"""
belnap_four.py — Belnap 四值逻辑构件（第 3 层冷门 3.1，次协调语义地基）
========================================================================
概念来源：**外部经典共识**——Belnap, N. (1977) 四值逻辑（真 T/假 F/
两者 B/皆非 N），用 {真,假} 子集语义：T={t}, F={f}, B={t,f}, N={}。
本构件为借鉴实现（落落三问：借什么=四值真值表语义；为什么=给第 2 层
对位创生/共振带收敛一个可判定语义地基；怎么记账=标注来源归借鉴区，
不混原创区）。
详规：《第3层冷门详规》§一（3.1 次协调——首期做 Belnap 四值）
配套：内部详规 2.6 对位创生（矛盾"两者"值 = 明确真值对象非无解）

本构件做什么（一句话）：
    给"矛盾该共存"一个可判定的语义——四值真值表：A 与 ¬A 都有证据
    时命题取"两者"B，不是爆炸（经典 A∧¬A⊢一切）也不是无解。

与经典二值的差别（为什么算冷门）：
    - 经典：A∧¬A 恒假（排中/不矛盾律下不可能）→ 爆炸律 ex falso；
    - Belnap：A∧¬A 可取 B（两者）——矛盾是**一类信息态**不是错误；
    - 说谎者句在四值里可稳定取"两者"——共振带收敛的语义锚点。

诚实边界：
    - 四值语义是"信息序"（N⊏T⊏B、N⊏F⊏B 双链格），不是"真值序"——
      不宣称解决了说谎者真值问题（哥德尔不违反），只是给它一个
      可判定的语义对象（两者值）；
    - 本构件只做真值表/求值（判定语义），不做证明论（次协调演算
      LP/m4 留扩展）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        formula: str——命题公式（原子 + ¬ ∧ ∨ →，四值语义求值）
        assign: dict——原子 → 四值名（'T'/'F'/'B'/'N'，缺省 'N'）
                特殊：不给 assign 且 formula 是 A∧¬A 形 → 演示"两者"
        demo: bool——演示模式（缺省 False；True 时内置说谎者/矛盾演示）
    输出:
        verdict: str——'evaluated'|'input_pending'|'parse_error'|
                       'assign_pending'
        value: str——四值名 'T'/'F'/'B'/'N'
        truth_set: list——{真,假} 子集视角（['真']/['假']/['真','假']/[]）
        rows: list——真值表（该公式各关键赋值下的四值）
        note: str——语义说明（是否"两者"态/非爆炸演示）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'formula': 'str?', 'assign': 'dict?', 'demo': 'bool?'},
    'out': {'verdict': 'str', 'value': 'str', 'truth_set': 'list',
            'rows': 'list', 'note': 'str', 'boundary': 'str'},
}

# 四值名（字符串全程）：'T' 真 / 'F' 假 / 'B' 两者 / 'N' 皆非
_FULL = ['T', 'F', 'B', 'N']


def _truth_set(vname):
    """四值 → {真,假} 子集视角（输出用，非运算）。"""
    return {'T': ['真'], 'F': ['假'], 'B': ['真', '假'],
            'N': []}[vname]


def _name(s):
    return s


# ── 四值联结词（Belnap 1977：菱形格 F<N<T、F<B<T，N∥B）
#    ∧ = truth-order meet（下确界）、∨ = join（上确界）
#    ¬ = 菱形垂直翻转（T↔F、N↔N、B↔B）
_MEET = {
    'F': {'F': 'F', 'N': 'F', 'B': 'F', 'T': 'F'},
    'N': {'F': 'F', 'N': 'N', 'B': 'F', 'T': 'N'},
    'B': {'F': 'F', 'N': 'F', 'B': 'B', 'T': 'B'},
    'T': {'F': 'F', 'N': 'N', 'B': 'B', 'T': 'T'},
}
_JOIN = {
    'F': {'F': 'F', 'N': 'N', 'B': 'B', 'T': 'T'},
    'N': {'F': 'N', 'N': 'N', 'B': 'T', 'T': 'T'},
    'B': {'F': 'B', 'N': 'T', 'B': 'B', 'T': 'T'},
    'T': {'F': 'T', 'N': 'T', 'B': 'T', 'T': 'T'},
}


def _neg(a):
    return {'T': 'F', 'F': 'T', 'B': 'B', 'N': 'N'}[a]


def _and(a, b):
    return _MEET[a][b]


def _or(a, b):
    return _JOIN[a][b]


def _imp(a, b):
    # a→b = ¬a ∨ b（经典定义延拓到四值）
    return _or(_neg(a), b)


def _tokenize(s):
    toks, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in '¬∧∨→()':
            toks.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        else:
            j = i
            while j < len(s) and s[j] not in '¬∧∨→() ':
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


def _parse(s):
    toks = _tokenize(s)
    if not toks:
        raise ValueError('空公式')
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def parse_imp():
        nonlocal pos
        left = parse_or()
        if peek() == '→':
            pos += 1
            return ('→', left, parse_imp())
        return left

    def parse_or():
        nonlocal pos
        left = parse_and()
        while peek() == '∨':
            pos += 1
            left = ('∨', left, parse_and())
        return left

    def parse_and():
        nonlocal pos
        left = parse_atom()
        while peek() == '∧':
            pos += 1
            left = ('∧', left, parse_atom())
        return left

    def parse_atom():
        nonlocal pos
        t = peek()
        if t == '¬':
            pos += 1
            return ('¬', parse_atom())
        if t == '(':
            pos += 1
            e = parse_imp()
            if peek() != ')':
                raise ValueError('缺右括号')
            pos += 1
            return e
        if t is None:
            raise ValueError('公式意外结束')
        if t in '¬∧∨→()':
            raise ValueError(f'意外符号 {t}')
        pos += 1
        return ('atom', t)

    ast = parse_imp()
    if pos != len(toks):
        raise ValueError(f'多余内容 {toks[pos:]}')
    return ast


def _eval(node, assign):
    k = node[0]
    if k == 'atom':
        return assign.get(node[1], 'N')   # 未赋值原子 → 皆非（无信息，诚实）
    if k == '¬':
        return _neg(_eval(node[1], assign))
    if k == '∧':
        return _and(_eval(node[1], assign), _eval(node[2], assign))
    if k == '∨':
        return _or(_eval(node[1], assign), _eval(node[2], assign))
    if k == '→':
        return _imp(_eval(node[1], assign), _eval(node[2], assign))
    raise ValueError(f'未知节点 {k}')


def _atoms(node, acc=None):
    if acc is None:
        acc = set()
    if node[0] == 'atom':
        acc.add(node[1])
    else:
        for ch in node[1:]:
            _atoms(ch, acc)
    return acc


def _truth_table_rows(formula, assign):
    """对公式建真值表：给各原子扫 4 值，输出关键行（含给定赋值行）。"""
    ast = _parse(formula)
    atoms = sorted(_atoms(ast))
    rows = []
    if len(atoms) <= 2:
        import itertools
        for combo in itertools.product(_FULL, repeat=len(atoms)):
            a = dict(zip(atoms, combo))
            v = _eval(ast, a)
            row = dict(zip(atoms, combo))
            row['→'] = _name(v)
            rows.append(row)
    else:
        a = {x: assign.get(x, 'N') for x in atoms}
        v = _eval(ast, a)
        rows.append({**a, '→': _name(v), 'note': '原子>2 仅显示给定赋值行'})
    return rows


def run(inputs):
    """
    做什么：Belnap 四值求值——矛盾取"两者"B，非爆炸。

    返回 dict（见模块 docstring）。"""
    formula = inputs.get('formula')
    demo = inputs.get('demo', False)

    # 演示模式（不传 formula 也可看核心演示）
    if demo and not formula:
        rows = []
        notes = []
        # 排中律在四值：P∨¬P 对 B 取 B（不是恒真）——信息语义
        for pv in ('T', 'F', 'B', 'N'):
            a = {'P': pv}
            v = _eval(_parse('P∨¬P'), a)
            rows.append({'P': pv, 'P∨¬P': _name(v)})
        notes.append('排中律 P∨¬P 在四值非恒真：P=两者(B) 时 P∨¬P=两者(B)')
        # 矛盾式 A∧¬A 对 B 取 B（不爆炸）
        for pv in ('T', 'F', 'B', 'N'):
            a = {'A': pv}
            v = _eval(_parse('A∧¬A'), a)
            rows.append({'A': pv, 'A∧¬A': _name(v)})
        notes.append('A∧¬A 在四值可取 B（两者）——矛盾是信息态，不爆炸')
        return {'verdict': 'evaluated', 'value': None,
                'truth_set': None, 'rows': rows,
                'note': '；'.join(notes),
                'boundary': '四值是信息序不是真值序——不宣称解决说谎者'
                            '真值问题（哥德尔不违反），只是给矛盾一个'
                            '可判定的语义对象（两者值）。'}
    if not formula:
        return {'verdict': 'input_pending', 'value': None,
                'truth_set': None, 'rows': [],
                'boundary': '需给 formula（命题公式）或 demo=True——诚实'}
    try:
        ast = _parse(formula)
    except ValueError as e:
        return {'verdict': 'parse_error', 'value': None,
                'truth_set': None, 'rows': [],
                'boundary': f'公式解析失败（诚实拦截）：{e}'}
    atoms = sorted(_atoms(ast))
    assign = {}
    raw = inputs.get('assign') or {}
    for k, v in raw.items():
        if v not in _FULL:
            return {'verdict': 'assign_pending', 'value': None,
                    'truth_set': None, 'rows': [],
                    'boundary': f'赋值 {k}={v!r} 非法（应为 T/F/B/N）'
                                '——诚实拦截'}
        assign[k] = v
    if not assign:
        return {'verdict': 'assign_pending', 'value': None,
                'truth_set': None, 'rows': [],
                'boundary': f'需给 assign（原子→T/F/B/N），原子为 '
                            f'{atoms}——四值求值必须有赋值（无信息=N）'}
    val = _eval(ast, assign)
    vname = _name(val)
    note = ''
    if vname == 'B':
        note = ('命题处于"两者"态（A 与 ¬A 都有证据）——矛盾是一类'
                '信息态，不爆炸（次协调立场）')
    elif vname == 'N':
        note = '皆非（无信息）——该命题当前无真值证据'
    elif vname == 'T':
        note = '真（只有真证据）'
    else:
        note = '假（只有假证据）'
    rows = _truth_table_rows(formula, raw)
    return {'verdict': 'evaluated', 'value': vname,
            'truth_set': _truth_set(vname), 'rows': rows, 'note': note,
            'boundary': 'Belnap 四值（外部共识，借鉴区）。四值语义是'
                        '信息序不是真值序——不宣称判定说谎者真值，'
                        '只给"两者"态一个可判定对象。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('Belnap 四值构件 · 自测（第 3 层 3.1）')
    print('=' * 62)

    # 1) 矛盾 A∧¬A 取 B：assign A=B → 两者
    r1 = run({'formula': 'A∧¬A', 'assign': {'A': 'B'}})
    assert r1['verdict'] == 'evaluated' and r1['value'] == 'B', r1
    assert set(r1['truth_set']) == {'假', '真'}, r1
    print(f"✅ A∧¬A 在 A=两者 → {r1['value']}（truth_set={r1['truth_set']}"
          f"，不爆炸）")

    # 2) A=T 时 A∧¬A = F（一致时仍是假）
    r2 = run({'formula': 'A∧¬A', 'assign': {'A': 'T'}})
    assert r2['value'] == 'F', r2
    print(f"✅ A∧¬A 在 A=真 → {r2['value']}（一致时不矛盾）")

    # 3) 排中律 P∨¬P 在 P=B → B（四值非恒真）
    r3 = run({'formula': 'P∨¬P', 'assign': {'P': 'B'}})
    assert r3['value'] == 'B', r3
    print(f"✅ P∨¬P 在 P=两者 → {r3['value']}（四值下排中律非恒真）")

    # 4) ¬B = B（两者否定仍两者）
    r4 = run({'formula': '¬P', 'assign': {'P': 'B'}})
    assert r4['value'] == 'B', r4
    print(f"✅ ¬P 在 P=两者 → {r4['value']}（¬B=B）")

    # 5) 蕴含/合取组合
    r5 = run({'formula': 'P→Q', 'assign': {'P': 'T', 'Q': 'B'}})
    assert r5['value'] == 'B', r5
    print(f"✅ P→Q 在 P=真,Q=两者 → {r5['value']}（→=¬P∨Q 延拓）")

    # 6) demo 模式（不传 formula）
    r6 = run({'demo': True})
    assert r6['verdict'] == 'evaluated' and len(r6['rows']) >= 8, r6
    print('✅ demo 模式：排中律/A∧¬A 四值表（矛盾取两者非爆炸）')

    # 7) 边界
    r7 = run({})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'formula': 'A∧', 'assign': {'A': 'T'}})
    assert r8['verdict'] == 'parse_error', r8
    r9 = run({'formula': 'A', 'assign': {'A': 'X'}})
    assert r9['verdict'] == 'assign_pending', r9
    r10 = run({'formula': 'A', 'assign': {}})
    assert r10['verdict'] == 'assign_pending', r10
    print('✅ 边界：缺公式/解析错/坏赋值/缺赋值 → 诚实拦截')

    print('=' * 62)
    print('Belnap 四值构件自测：全部通过 ✅')
    print('=' * 62)
