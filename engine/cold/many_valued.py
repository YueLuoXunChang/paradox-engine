# -*- coding: utf-8 -*-
"""
many_valued.py — 多值逻辑（三值：Kleene 强三值 K3 · Łukasiewicz 三值 Ł3）（第 3 层补件）
================================================================================
概念来源：**外部经典共识**——Kleene 强三值（1952，第三值 U = 未知/未定义）与
Łukasiewicz 三值（1920，第三值 ½ 当"中间真值"）。本构件为借鉴实现（落落三问：
借什么=三值的真值表与"设计值"这套语义；为什么=第 3 层原先只有 Belnap **四值**
（管"矛盾取两者"），三值这种"**未知/未定义**"的处理一直缺件——而现实材料里
"这条到底真假还不知道"比"既真又假"常见得多；怎么记账=标注来源归借鉴区）。

本构件做什么（一句话）：
    在**三值**语义下算命题公式：给指派求值、判重言式（不是就给反例指派）、
    判前提是否推出结论、以及同一批代表公式在 **K3 / Ł3 / 经典二值** 下的对照表。

两套三值（差别只在蕴含，其余联结词一样——这点常被混为一谈，所以本构件分开算）：
    值     ：0（假）· ½（未知/中间）· 1（真）；**设计值只有 1**（真）；
    ¬      ：1 − a ；
    ∧ / ∨  ：min / max（K3 与 Ł3 相同）；
    →      ：K3 取 max(1−a, b)（= ¬a∨b，把 ½ 当"未知"）；
             Ł3 取 min(1, 1−a+b)（把 ½ 当"中间真值"，故 ½→½ = 1，
             而 K3 里 ½→½ = ½）；
    推结论 ：前提全为 1 时结论必为 1（设计值口径）。

由此有两条**可核对**的对照事实（本构件的自测与正式测试都钉着）：
    - **K3 没有重言式**：所有原子都取 ½ 时，任何公式都算成 ½（每个联结词都保 ½），
      所以"恒为 1"的公式不存在——K3 不是"更宽松的经典逻辑"；
    - **Ł3 有重言式但没有排中律**：P→P 在 Ł3 恒为 1（½→½ = 1），
      而 P∨¬P 在 P=½ 时是 ½；且**肯定前件**（P∧(P→Q)→Q）在 Ł3 **不成立**。

与第 3 层已有的 Belnap 四值（belnap_four）不是一回事（别混）：
    - Belnap 四值：值 = {真, 假, 两者, 皆非}，管的是"**信息既有又有**"（矛盾不爆炸）；
    - 本构件三值：值 = {真, 假, 未知}，管的是"**信息不够**"（一条都没提，或提了不定），
      并且关心的是**设计值/重言式/推理**这套判定，不是四值的格结构。

诚实边界：
    - 只做**命题**三值：语法复用第 1 层命题构件（¬ ∧ ∨ → ↔ 与括号），
      一阶/模态的多值扩展不在本构件范围；
    - 枚举重言式按 3^n 指派，原子数上限 8（超了报 size_limit，不硬跑）；
    - 指派里**没给的原子按 ½（未知）算**——这是"信息不够"的自然读法，不是默认真；
    - 只诊断不决策：给的是"这套三值语义下算出来是什么"，不替使用者选"现实里该用哪套"；
      三值本身也不是"更真的逻辑"，只是另一种约定。

统一接口：
    run(inputs: dict) -> dict
    输入:
        logic: 'k3'|'l3'——哪套三值（默认 k3）
        mode: 'evaluate'|'tautology'|'validity'|'compare'
              （默认按有没有 assignment 推断：给了指派就求值，没给就判重言式）
        formula: str——命题式（evaluate/tautology 用）
        assignment: dict——原子 → 取值（1/0/½；也认 'T'/'F'/'U'、真/假/未知）
        premises / conclusion: list/str（validity 用）
    输出:
        verdict: str——'evaluated'|'tautology'|'not_tautology'|'valid'|'invalid'
                        |'compared'|'input_pending'|'parse_error'|'size_limit'
        value: float?——求值结果（0 / 0.5 / 1）
        counterexample: dict?——不是重言式/推理无效时的反例指派
        table: list——compare 模式的对照表
        atoms: list——公式里出现的原子
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'logic': 'str?', 'mode': 'str?', 'formula': 'str?',
           'assignment': 'dict?', 'premises': 'list?', 'conclusion': 'str?'},
    'out': {'verdict': 'str', 'value': 'float?', 'counterexample': 'dict?',
            'table': 'list', 'atoms': 'list', 'boundary': 'str'},
}

import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MAX_ATOMS = 8          # 3^n 指派枚举上限
TRUE, UNK, FALSE = 1.0, 0.5, 0.0
_VALUE_CN = {1.0: '真（1）', 0.5: '未知（½）', 0.0: '假（0）'}
_TOP = ('1', 'true', 'True', 'T', 't', '真', True)
_BOT = ('0', 'false', 'False', 'F', 'f', '假', False)
_UNK = ('½', '1/2', '0.5', 'U', 'u', 'unknown', '?', '未知', '不定', None)


def _prop():
    """取命题构件的解析与原子提取（同一套语法，不另写一套）。"""
    try:
        from engine.classical.propositional import parse, atoms_of
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        from propositional import parse, atoms_of
    return parse, atoms_of


def _read_value(v):
    """把输入值读成 1 / ½ / 0；读不出来抛 ValueError。"""
    if isinstance(v, bool):
        return TRUE if v else FALSE
    if isinstance(v, (int, float)):
        if v == 1 or v == 1.0:
            return TRUE
        if v == 0 or v == 0.0:
            return FALSE
        if v == 0.5:
            return UNK
        raise ValueError(f'取值只能是 1 / ½ / 0，得到 {v!r}')
    if v in _TOP:
        return TRUE
    if v in _BOT:
        return FALSE
    if v in _UNK:
        return UNK
    raise ValueError(f'取值看不懂：{v!r}（认 1/0/½，或 T/F/U、真/假/未知）')


def _eval3(ast, env, logic):
    """三值求值。K3 与 Ł3 只在蕴含上不同，其余联结词一样。"""
    op = ast[0]
    if op == 'atom':
        return env.get(ast[1], UNK)          # 没给的原子 = 未知
    if op == '¬':
        return 1.0 - _eval3(ast[1], env, logic)
    if op == '∧':
        return min(_eval3(ast[1], env, logic), _eval3(ast[2], env, logic))
    if op == '∨':
        return max(_eval3(ast[1], env, logic), _eval3(ast[2], env, logic))
    if op == '→':
        a = _eval3(ast[1], env, logic)
        b = _eval3(ast[2], env, logic)
        if logic == 'l3':
            return min(1.0, 1.0 - a + b)     # Ł3：½ 当中间真值（½→½ = 1）
        return max(1.0 - a, b)               # K3：¬a∨b（½→½ = ½）
    if op == '↔':
        a = _eval3(ast[1], env, logic)
        b = _eval3(ast[2], env, logic)
        # a ↔ b 定为 (a→b) ∧ (b→a)；两套各自的 → 决定结果
        return min(_eval3(('→', ast[1], ast[2]), env, logic),
                   _eval3(('→', ast[2], ast[1]), env, logic))
    raise ValueError(f'三值求值遇到不认识的节点：{op!r}')


def _eval_classical(ast, env):
    """经典二值求值（对照用）：½ 归成假——所以只在"没有 ½"的指派上谈得上对照。"""
    op = ast[0]
    if op == 'atom':
        return 1.0 if env.get(ast[1], FALSE) == TRUE else 0.0
    if op == '¬':
        return 1.0 - _eval_classical(ast[1], env)
    a, b = 0.0, 0.0
    if op == '∧':
        return min(_eval_classical(ast[1], env), _eval_classical(ast[2], env))
    if op == '∨':
        return max(_eval_classical(ast[1], env), _eval_classical(ast[2], env))
    if op == '→':
        a = _eval_classical(ast[1], env)
        b = _eval_classical(ast[2], env)
        return max(1.0 - a, b)
    if op == '↔':
        a = _eval_classical(ast[1], env)
        b = _eval_classical(ast[2], env)
        return 1.0 if a == b else 0.0
    raise ValueError(f'经典求值遇到不认识的节点：{op!r}')


def _assignments(atoms):
    """所有 3^n 指派（原子 → 0/½/1）。"""
    for combo in itertools.product((FALSE, UNK, TRUE), repeat=len(atoms)):
        yield dict(zip(atoms, combo))


def _tautology(ast, atoms, logic):
    """是不是重言式（所有指派都为 1）。返回 (是否, 反例指派或 None)。"""
    for env in _assignments(atoms):
        if _eval3(ast, env, logic) != TRUE:
            return False, {k: _show(k, v) for k, v in env.items()}
    return True, None


def _show(atom, v):
    return {TRUE: '1', UNK: '½', FALSE: '0'}[v]


def _boundary(logic, n_atoms=None):
    name = 'Kleene 强三值 K3' if logic == 'k3' else 'Łukasiewicz 三值 Ł3'
    extra = ('' if n_atoms is None else f'（本次原子 {n_atoms} 个）')
    return (f'{name}（外部共识，借鉴区）：值 = 0 / ½ / 1，设计值只有 1；'
            f'∧∨ 取 min/max，两套的差别只在蕴含上{K3_NOTE if logic == "k3" else L3_NOTE}'
            f'。指派里没给的原子按 ½（未知）算。'
            f'与 Belnap 四值不是一回事：四值管"矛盾取两者"，三值管"信息不够"。'
            f'只诊断不决策：给的是这套语义下的计算结果，不替使用者选该用哪套。{extra}')


K3_NOTE = ('（K3 的 → 是 ¬a∨b，½→½ = ½，所以**K3 没有重言式**）')
L3_NOTE = ('（Ł3 的 → 是 min(1,1−a+b)，½→½ = 1，所以 Ł3 有重言式但**没有排中律**）')

# compare 模式的代表公式（都是经典重言式，用来三套对照）
_COMPARE = [
    ('P ∨ ¬P', '排中律'),
    ('P → P', '同一律'),
    ('¬(P ∧ ¬P)', '不矛盾律'),
    ('(P → Q) ∨ (Q → P)', 'Ł3 的特征重言式'),
    ('¬¬P → P', '双重否定消去'),
    ('(P ∧ (P → Q)) → Q', '肯定前件'),
]


def _pending(msg):
    return {'verdict': 'input_pending', 'value': None, 'counterexample': None,
            'table': [], 'atoms': [], 'boundary': msg}


def run(inputs):
    """
    做什么：三值语义下的求值 / 重言式判定 / 推理判定 / 三套对照。

    返回 dict（见模块 docstring）。
    """
    if not isinstance(inputs, dict):
        return _pending('inputs 必须是 dict')
    logic = inputs.get('logic') or 'k3'
    if logic not in ('k3', 'l3'):
        return _pending("logic 只能是 k3（Kleene 强三值，默认）或 l3"
                        "（Łukasiewicz 三值），得到 %r" % (logic,))
    mode = inputs.get('mode')
    if mode is None:                          # 没给 mode 就按有没有指派推断
        mode = 'evaluate' if inputs.get('assignment') else 'tautology'
    if mode not in ('evaluate', 'tautology', 'validity', 'compare'):
        return _pending('mode 应为 evaluate/tautology/validity/compare，'
                        '得到 %r' % (mode,))
    parse, atoms_of = _prop()

    if mode == 'compare':
        table = []
        for text, why in _COMPARE:
            ast = parse(text)
            atoms = atoms_of(ast)
            k3_ok, k3_cex = _tautology(ast, atoms, 'k3')
            l3_ok, l3_cex = _tautology(ast, atoms, 'l3')
            cl_ok, cl_cex = _classical_tautology(ast, atoms)
            table.append({'formula': text, 'note': why,
                          'classical': cl_ok, 'k3': k3_ok, 'l3': l3_ok,
                          'k3_counterexample': k3_cex,
                          'l3_counterexample': l3_cex,
                          'classical_counterexample': cl_cex})
        return {'verdict': 'compared', 'value': None, 'counterexample': None,
                'table': table, 'atoms': [],
                'boundary': ('经典二值 / Kleene 强三值 K3 / Łukasiewicz 三值 Ł3 '
                             '三套对照（都是经典重言式的式子）：经典那一列是二值下的'
                             '结论，另两列是三值下的结论。共同点：排中律与不矛盾律在'
                             '两套三值里都不成立；差别：P→P 在 Ł3 成立、在 K3 不成立'
                             '（正是 ½→½ 取值不同所致）。')}

    formula = inputs.get('formula')
    if not isinstance(formula, str) or not formula.strip():
        if mode == 'validity' and inputs.get('premises') \
                and inputs.get('conclusion'):
            pass                              # validity 可以只用 premises/conclusion
        else:
            return _pending('需要 formula（命题式，如 "P ∨ ¬P"）——诚实拦截')
    try:
        f_ast = parse(formula.strip()) if formula and formula.strip() else None
    except Exception as e:  # noqa: BLE001
        return {'verdict': 'parse_error', 'value': None, 'counterexample': None,
                'table': [], 'atoms': [], 'boundary': f'公式解析不了：{e}'}

    if mode == 'validity':
        premises = inputs.get('premises') or []
        conclusion = inputs.get('conclusion')
        if not isinstance(premises, (list, tuple)) or not premises:
            return _pending('validity 模式需 premises（前提式列表）——诚实拦截')
        if not isinstance(conclusion, str) or not conclusion.strip():
            return _pending('validity 模式需 conclusion（结论式）——诚实拦截')
        try:
            p_asts = [parse(p) for p in premises]
            c_ast = parse(conclusion.strip())
        except Exception as e:  # noqa: BLE001
            return {'verdict': 'parse_error', 'value': None,
                    'counterexample': None, 'table': [], 'atoms': [],
                    'boundary': f'前提/结论解析不了：{e}'}
        atoms = []
        for ast in p_asts + [c_ast]:
            for a in atoms_of(ast):
                if a not in atoms:
                    atoms.append(a)
        if len(atoms) > MAX_ATOMS:
            return _size_limit(atoms, logic)
        for env in _assignments(atoms):
            if all(_eval3(a, env, logic) == TRUE for a in p_asts) \
                    and _eval3(c_ast, env, logic) != TRUE:
                return {'verdict': 'invalid', 'value': None,
                        'counterexample': {k: _show(k, v) for k, v in env.items()},
                        'table': [], 'atoms': atoms, 'boundary': _boundary(logic)}
        return {'verdict': 'valid', 'value': None, 'counterexample': None,
                'table': [], 'atoms': atoms, 'boundary': _boundary(logic)}

    if f_ast is None:
        return _pending('需要 formula——诚实拦截')
    atoms = atoms_of(f_ast)
    if len(atoms) > MAX_ATOMS:
        return _size_limit(atoms, logic)

    if mode == 'evaluate':
        raw = inputs.get('assignment') or {}
        if not isinstance(raw, dict):
            return _pending('assignment 应是 dict（原子 → 1/0/½）——诚实拦截')
        try:
            env = {k: _read_value(v) for k, v in raw.items()}
        except ValueError as e:
            return _pending(str(e))
        val = _eval3(f_ast, env, logic)
        missing = [a for a in atoms if a not in env]
        note = ('（没给取值的原子按 ½ 未知算：%s）' % '、'.join(missing)
                if missing else '')
        return {'verdict': 'evaluated', 'value': val, 'counterexample': None,
                'table': [], 'atoms': atoms,
                'boundary': _boundary(logic) + note}

    # mode == 'tautology'
    ok, cex = _tautology(f_ast, atoms, logic)
    return {'verdict': 'tautology' if ok else 'not_tautology',
            'value': None, 'counterexample': cex, 'table': [], 'atoms': atoms,
            'boundary': _boundary(logic, len(atoms))}


def _classical_tautology(ast, atoms):
    """经典二值下的重言式判定（只在 0/1 指配上，用于对照）。"""
    for combo in itertools.product((FALSE, TRUE), repeat=len(atoms)):
        env = dict(zip(atoms, combo))
        if _eval_classical(ast, env) != TRUE:
            return False, {k: _show(k, v) for k, v in env.items()}
    return True, None


def _size_limit(atoms, logic):
    return {'verdict': 'size_limit', 'value': None, 'counterexample': None,
            'table': [], 'atoms': atoms,
            'boundary': f'原子 {len(atoms)} 个 > 上限 {MAX_ATOMS}——'
                        f'3^n 个指派不硬枚举（诚实报告规模限制）'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 68)
    print('多值逻辑（K3 / Ł3）构件 · 自测（第 3 层补件）')
    print('=' * 68)

    # 1) 求值：未知原子的传播
    r1 = run({'formula': 'P ∧ Q', 'assignment': {'P': 1}})
    assert r1['verdict'] == 'evaluated' and r1['value'] == UNK, r1
    r1b = run({'formula': 'P ∨ Q', 'assignment': {'P': 1}})
    assert r1b['value'] == TRUE, r1b
    print('✅ 求值：P ∧ Q（Q 未知）→ ½；P ∨ Q（P 真）→ 1（未知会传播）')

    # 2) 两套的差别只在蕴含：½→½
    k = run({'formula': 'P → P', 'assignment': {'P': '½'}})['value']
    l = run({'formula': 'P → P', 'assignment': {'P': '½'}, 'logic': 'l3'})['value']
    assert (k, l) == (UNK, TRUE), (k, l)
    print('✅ 同一个 ½→½：K3 得 ½、Ł3 得 1（两套三值只差在蕴含）')

    # 3) K3 没有重言式；Ł3 有（P→P）但没有排中律
    assert run({'formula': 'P → P'})['verdict'] == 'not_tautology', 'k3 P→P'
    assert run({'formula': 'P → P', 'logic': 'l3'})['verdict'] == 'tautology'
    assert run({'formula': 'P ∨ ¬P', 'logic': 'l3'})['verdict'] \
        == 'not_tautology'
    print('✅ K3 无重言式（连 P→P 都不是）；Ł3 里 P→P 是、P∨¬P 不是')

    # 4) 经典规则不是"全都失效"：肯定前件在两套三值里都成立，
    #    失效的是排中律/不矛盾律这类；而双重否定消去只在一套里成立
    r4 = run({'mode': 'validity', 'logic': 'l3', 'premises': ['P', 'P → Q'],
              'conclusion': 'Q'})
    r4b = run({'mode': 'validity', 'logic': 'k3', 'premises': ['P', 'P → Q'],
               'conclusion': 'Q'})
    assert r4['verdict'] == 'valid' and r4b['verdict'] == 'valid', (r4, r4b)
    assert run({'formula': '¬¬P → P', 'logic': 'l3'})['verdict'] == 'tautology'
    assert run({'formula': '¬¬P → P', 'logic': 'k3'})['verdict'] \
        == 'not_tautology'
    print('✅ 肯定前件在 K3/Ł3 都成立（经典规则不是全失效）；'
          '双重否定消去只在 Ł3 成立')

    # 5) 三套对照表
    r5 = run({'mode': 'compare'})
    row = {x['formula']: x for x in r5['table']}
    assert row['P ∨ ¬P']['classical'] and not row['P ∨ ¬P']['l3'], row
    assert row['P → P']['l3'] and not row['P → P']['k3'], row
    print('✅ 对照表：排中律经典成立、三值不成立；P→P 在 Ł3 成立、在 K3 不成立')

    # 6) 边界
    assert run({'formula': 'P ∨'})['verdict'] == 'parse_error'
    assert run({'formula': 'P', 'logic': 'x'})['verdict'] == 'input_pending'
    assert run({'formula': 'P', 'assignment': {'P': 2}})['verdict'] \
        == 'input_pending'
    assert run({'formula': ' ∧ '.join('P%d' % i for i in range(9))})['verdict'] \
        == 'size_limit'
    print('✅ 边界：坏公式/坏 logic/坏取值/超上限 → 诚实拦截')

    print('=' * 68)
    print('多值逻辑构件自测：全部通过 ✅')
    print('=' * 68)
