# -*- coding: utf-8 -*-
"""
relevance_logic.py — 相干逻辑 · 论证相关性构件（第 3 层冷门 3.4）
====================================================================
概念来源：**外部经典共识**——相干逻辑（relevance logic / entailment，
Anderson & Belnap 1975《Entailment》）。本构件为借鉴实现（落落三问：
借什么=相干蕴含的"前提与结论必须共享变量"要求；为什么=经典逻辑允许
"A ⊢ B∨¬B"这类前提结论毫不相干的推理照样有效（爆炸/废话有效），
T2 论证矛盾检查需要区分"真冲突"与"话术冲突"；怎么记账=来源归借鉴区）。
详规：第 3 层冷门详规 §四（构件 3.4 相干逻辑：论证相关性）

本构件做什么（一句话）：
    给"这个推理是真有效，还是只是形式有效"一个可跑答案——两个能力：
    ① **相干检查**（mode='relevance'）：推理 Γ ⊢ C 中，前提集与结论是否
       共享至少一个原子？共享 → 相干；不共享 → 标记
       "推理形式有效但不相干"（如 P ⊢ Q∨¬Q）；
    ② **冲突定性**（mode='conflict'）：两个命题"冲突"吗？冲突时再看是否
       相干 → **真冲突**（相干）vs **话术冲突**（毫无共享变量的"矛盾"更
       可能是废话而非悖论）。

与经典层的差别（为什么算冷门）：
    - 经典逻辑：Γ 不一致 ⟹ Γ ⊢ C（任何 C，爆炸）——前提与结论可以毫不
      相干；
    - 相干逻辑：有效推理的前提与结论**必须共享变量**——把"废话有效"
      （vacuously valid）标出来，这正是 T2"真冲突 vs 话术冲突"的判据。

诚实边界：
    - 相干性 = **语法级**变量共享检查（不做语义相干/主题相干判断）；
    - 经典有效性复用第 2 层命题逻辑（有原子数上限 10），超限报
      'undecided'——相干检查本身仍给出，但不冒充有效性结论；
    - 本构件只**报告**相干性，不替使用者裁决"该不该采信这个论证"。

统一接口：
    run(inputs: dict) -> dict
    输入（mode='relevance'）:
        premises: list[str]——前提集（命题式）
        conclusion: str——结论（命题式）
    输入（mode='conflict'）:
        prop_a: str——命题 A
        prop_b: str——命题 B
    输出:
        verdict: str——'relevant_valid'|'relevant_invalid'|'irrelevant_valid'
                        |'irrelevant_invalid'|'real_conflict'|'hollow_conflict'
                        |'no_conflict'|'undecided'|'input_pending'
                        |'parse_pending'
        shared_atoms: list[str]——共有的原子（相干性证据）
        premise_atoms / conclusion_atoms: list[str]——各自原子
        classically_valid: bool|None——经典有效性（None = 算不动）
        counterexample: str|None——无效时的反例指派
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'premises': 'list?', 'conclusion': 'str?',
           'prop_a': 'str?', 'prop_b': 'str?'},
    'out': {'verdict': 'str', 'shared_atoms': 'list',
            'premise_atoms': 'list', 'conclusion_atoms': 'list',
            'classically_valid': 'bool?', 'counterexample': 'str?',
            'boundary': 'str'},
}

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pl():
    """取经典命题逻辑模块（有效性判定 + 原子抽取）。"""
    try:
        from engine.classical import propositional as pl
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        import propositional as pl
    return pl


def _atoms(pl, formula):
    """抽原子（语法级，无枚举上限）。返回 (atoms, error)。"""
    try:
        return pl.atoms_of(pl.parse(formula)), None
    except Exception as e:  # noqa: BLE001——解析失败即诚实报告
        return [], str(e)


def _result(verdict, shared, p_atoms, c_atoms, valid, counter, boundary):
    return {'verdict': verdict, 'shared_atoms': shared,
            'premise_atoms': p_atoms, 'conclusion_atoms': c_atoms,
            'classically_valid': valid, 'counterexample': counter,
            'boundary': boundary}


def _relevance(pl, premises, conclusion):
    """相干检查 + 经典有效性（详规 §4.2 判定结构）。"""
    p_atoms = []
    for p in premises:
        a, err = _atoms(pl, p)
        if err:
            return _result('parse_pending', [], [], [], None, None,
                           f'前提 {p!r} 解析失败：{err}——诚实拦截')
        for x in a:
            if x not in p_atoms:
                p_atoms.append(x)
    c_atoms, err = _atoms(pl, conclusion)
    if err:
        return _result('parse_pending', [], p_atoms, [], None, None,
                       f'结论 {conclusion!r} 解析失败：{err}——诚实拦截')

    shared = [a for a in p_atoms if a in c_atoms]
    relevant = bool(shared)

    r = pl.run({'mode': 'validity', 'premises': premises,
                'conclusion': conclusion})
    v = r.get('verdict')
    if v == 'valid':
        valid, counter = True, None
    elif v == 'invalid':
        valid, counter = False, r.get('counterexample')
    else:
        # 算不动（size_limit / parse_error）：相干检查仍给，有效性诚实留空
        return _result('undecided', shared, p_atoms, c_atoms, None, None,
                       f'相干检查已完成（共享原子 {shared or "无"}），但经典'
                       f'有效性算不动：{v}（{r.get("boundary", "")}）——'
                       '不冒充有效性结论')

    if relevant:
        verdict = 'relevant_valid' if valid else 'relevant_invalid'
        boundary = ('前提与结论共享原子 '
                    f'{shared} → 通过相干检查，再走经典有效性：'
                    f'{"有效" if valid else "无效"}。')
        if not valid and counter:
            boundary += f'反例：{counter}。'
    else:
        verdict = 'irrelevant_valid' if valid else 'irrelevant_invalid'
        boundary = ('前提与结论**不共享任何原子** → 不相干。')
        if valid:
            boundary += ('经典层判"形式有效"，但属**空洞有效**（废话有效）：'
                         '前提没提供任何与结论相关的东西，如 P ⊢ Q∨¬Q。'
                         '相干逻辑立场：这不算真正的蕴含。')
        else:
            boundary += '经典层亦判无效 → 既不相干又无效。'
    return _result(verdict, shared, p_atoms, c_atoms, valid, counter,
                   boundary)


def _conflict(pl, prop_a, prop_b):
    """冲突定性：真冲突（相干）vs 话术冲突（不相干）（详规 §4.3 T2 增强）。"""
    a_atoms, err_a = _atoms(pl, prop_a)
    if err_a:
        return _result('parse_pending', [], [], [], None, None,
                       f'命题 A {prop_a!r} 解析失败：{err_a}——诚实拦截')
    b_atoms, err_b = _atoms(pl, prop_b)
    if err_b:
        return _result('parse_pending', a_atoms, a_atoms, [], None, None,
                       f'命题 B {prop_b!r} 解析失败：{err_b}——诚实拦截')

    shared = [a for a in a_atoms if a in b_atoms]

    conj = f'({prop_a})∧({prop_b})'
    r = pl.run({'formula': conj, 'mode': 'satisfiable'})
    v = r.get('verdict')
    if v not in ('satisfiable', 'unsatisfiable'):
        return _result('undecided', shared, a_atoms, b_atoms, None, None,
                       f'相干检查已完成（共享原子 {shared or "无"}），但'
                       f'"可否同真"算不动：{v}——不冒充冲突结论')

    if v == 'satisfiable':
        return _result('no_conflict', shared, a_atoms, b_atoms, None, None,
                       f'A∧B 可同真 → 不构成冲突（共享原子 '
                       f'{shared or "无"}）。')

    if shared:
        return _result('real_conflict', shared, a_atoms, b_atoms, None, None,
                       f'A∧B 不可同真且二者共享原子 {shared} → **真冲突**：'
                       '矛盾落在同一批变量上，是实质对立，值得进一步做'
                       '悖论度量。')
    return _result('hollow_conflict', shared, a_atoms, b_atoms, None, None,
                   'A∧B 不可同真但二者**不共享任何原子** → **话术冲突**'
                   '（空洞对立）：连相关性都没有的"矛盾"更可能是各说各话'
                   '或废话，而非悖论——T2 增强判据。')


def run(inputs):
    """
    做什么：相干逻辑检查（论证相关性）/ 冲突定性（真冲突 vs 话术冲突）。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'relevance')
    pl = _pl()

    if mode == 'conflict':
        a = inputs.get('prop_a')
        b = inputs.get('prop_b')
        if not a or not b:
            return _result('input_pending', [], [], [], None, None,
                           'mode=conflict 需 prop_a + prop_b（两命题）'
                           '——诚实拦截，不硬判')
        return _conflict(pl, a, b)

    if mode != 'relevance':
        return _result('input_pending', [], [], [], None, None,
                       f'mode 应为 relevance/conflict，得到 {mode!r}'
                       '——诚实拦截')

    premises = inputs.get('premises') or []
    conclusion = inputs.get('conclusion')
    if not premises or not conclusion:
        return _result('input_pending', [], [], [], None, None,
                       'mode=relevance 需 premises（前提集）+ conclusion'
                       '（结论）——诚实拦截，不硬判')
    return _relevance(pl, premises, conclusion)


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 62)
    print('相干逻辑 · 论证相关性构件 · 自测（第 3 层 3.4）')
    print('=' * 62)

    # 1) 相干且有效：三段论
    r1 = run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})
    assert r1['verdict'] == 'relevant_valid', r1
    assert r1['shared_atoms'] == ['Q'], r1
    print(f"✅ P→Q, P ⊢ Q → {r1['verdict']}（共享 {r1['shared_atoms']}）")

    # 2) 详规例子：形式有效但不相干（空白有效/废话有效）
    r2 = run({'premises': ['P'], 'conclusion': 'Q∨¬Q'})
    assert r2['verdict'] == 'irrelevant_valid', r2
    assert r2['shared_atoms'] == [], r2
    print(f"✅ P ⊢ Q∨¬Q → {r2['verdict']}"
          '（不相干：前提没提供与结论相关的东西）')

    # 3) 爆炸例：前提不一致 → 经典层判有效，相干层判不相干
    r3 = run({'premises': ['P', '¬P'], 'conclusion': 'Q'})
    assert r3['verdict'] == 'irrelevant_valid', r3
    print(f"✅ P, ¬P ⊢ Q → {r3['verdict']}（经典爆炸有效但不相干）")

    # 4) 不相干且无效
    r4 = run({'premises': ['P'], 'conclusion': 'Q'})
    assert r4['verdict'] == 'irrelevant_invalid', r4
    print(f"✅ P ⊢ Q → {r4['verdict']}（既不相干又无效）")

    # 5) 真冲突（相干）
    r5 = run({'mode': 'conflict', 'prop_a': 'P', 'prop_b': '¬P'})
    assert r5['verdict'] == 'real_conflict', r5
    print(f"✅ P vs ¬P → {r5['verdict']}（共享 {r5['shared_atoms']}）")

    # 6) 话术冲突（不相干）
    r6 = run({'mode': 'conflict', 'prop_a': 'P∧¬P', 'prop_b': 'Q∧¬Q'})
    assert r6['verdict'] == 'hollow_conflict', r6
    print(f"✅ P∧¬P vs Q∧¬Q → {r6['verdict']}（毫无共享变量的矛盾"
          f'更可能是废话）')

    # 7) 不冲突
    r7 = run({'mode': 'conflict', 'prop_a': 'P', 'prop_b': 'P'})
    assert r7['verdict'] == 'no_conflict', r7
    print(f"✅ P vs P → {r7['verdict']}（可同真）")

    # 8) 边界：缺参/坏公式/坏 mode
    r8 = run({})
    assert r8['verdict'] == 'input_pending', r8
    r9 = run({'premises': ['P'], 'conclusion': 'Q∧'})
    assert r9['verdict'] == 'parse_pending', r9
    r10 = run({'mode': 'xx'})
    assert r10['verdict'] == 'input_pending', r10
    r11 = run({'mode': 'conflict', 'prop_a': 'P'})
    assert r11['verdict'] == 'input_pending', r11
    print('✅ 边界：缺参/坏公式/坏 mode → 诚实拦截')

    print('=' * 62)
    print('相干逻辑构件自测：全部通过 ✅')
    print('=' * 62)
