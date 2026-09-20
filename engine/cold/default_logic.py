# -*- coding: utf-8 -*-
"""
default_logic.py — 默认逻辑（Reiter 完整不动点）构件（第 3 层冷门 3.3 补件）
================================================================================
概念来源：**外部经典共识**——Reiter, R. (1980) "A Logic for Default Reasoning"
（默认理论 (W, D)；扩展 = 算子 Γ 的不动点）。本构件为借鉴实现（落落三问：
借什么=Γ 不动点这套语义与"扩展"这套说法；为什么=`agm_revision` 里的默认推理
当初就写明是**工程简化**（有例外即阻断），不是 Reiter 原义——那条边界一直挂着，
本构件把"完整不动点"补齐，并让两者各说自己算的是什么；怎么记账=标注来源归借鉴区）。

本构件做什么（一句话）：
    给一套默认规则（前提 : 辩护 / 结论）+ 一组事实 → 算出**所有站得住的扩展**
    （Γ 的不动点），据此说清：哪些结论每个扩展里都成立（怀疑论）、哪些只在部分
    扩展里成立（轻信论）、哪些压根推不出来；以及每条默认规则在哪些扩展里生效。

语义（Reiter 1980 原义，实话实说，不改口径）：
    - 默认规则写成 α : β / γ（前提 α、辩护 β、结论 γ）；正常默认是 β = γ；
    - 对一套假设的理论 S，算子 Γ(S) = Th(W ∪ {γ : α∈S 且 ¬β∉S})；
    - **扩展 E 就是 Γ(Ε) = E 的不动点**——即"假设成立、推出来的又正好是假设"；
    - 一条默认在 E 里生效，要**同时**满足：前提推得出（α∈E）且**辩护不被推翻**
      （¬β∉E）。辩护被推翻才是阻断——**不是"有例外就阻断"**；
    - 有限命题情形下，扩展必形如 Th(W ∪ 若干默认结论)，所以本构件在默认条数的
      2^n 个子集上枚举候选、再逐个验不动点（这就是"完整"的意思：不漏扩展）。

与 agm_revision 的关系（两边都说清自己算的是哪个）：
    - 本构件 = Reiter **原义**：企鹅那种"鸟会飞 + 企鹅不会飞"，如果只写
      (鸟 : 会飞)/会飞 与 (企鹅 : ¬会飞)/¬会飞，会得到**两个扩展**（歧义）——
      这是 Reiter 语义的真实结果，不是 bug；
    - 想要"企鹅这种例外一定压过鸟"，Reiter 的标准写法是把例外**写进前提**：
      (鸟 ∧ ¬企鹅 : 会飞)/会飞——这样只剩一个扩展。本构件的自测与正式测试
      把这两种写法摆在一起对照；
    - agm_revision 的 mode='default' 仍是那个**简化版**（有例外即阻断），
      保留不动；要完整不动点就来本构件。

诚实边界：
    - 只做**有限命题**默认逻辑：前提/辩护/结论都是命题公式（复用第 1 层命题构件
      的解析与求值），一阶默认逻辑不在本构件范围；
    - 原子数沿用经典层真值表的上限（10）：超了报 undecided——**算不动 ≠ 没有扩展**
      （绝不冒充"无扩展"）；
    - 默认条数上限（默认 12）内枚举 2^n 个子集，超了诚实报 size_limit；
    - 事实集自相矛盾时报 facts_unsatisfiable：经典上这时"全部公式"平凡地算一个
      扩展，那种平凡扩展对诊断没用，本构件如实报"事实打架"而不报"有扩展"；
    - 有的默认理论**本来就没有扩展**（如 W=∅、(: P)/¬P）——这时报 no_extension，
      是语义结果，不是"算不出来"；
    - 只诊断不决策：本构件算的是"这套规则下能推出什么、有几种立场"，
      不判断规则本身是否合理（规则由使用者/上层给）。
    - ⊤ / ⊥ 只在**整条**公式的位置上被认（表示无前提/恒假）；混在式子中间
      一律 parse_error（不把它们偷偷当原子名用）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        facts: list[str]——事实集 W（命题式，如 ['鸟', '企鹅']；可空 = 无事实）
        defaults: list——默认规则，四种写法都认：
            ('前提', '结论')                        —— 正常默认（辩护=结论）
            ('前提', '辩护', '结论')                —— 完整默认
            {'prerequisite':…, 'justification':…, 'consequent':…}（键可省）
            '前提 : 辩护 / 结论'                    —— 一行字符串
            前提写 ⊤ / 空 / 省掉 = 无前提
        query: str?——想问的命题式（可省）：看它在所有/部分/没有扩展里成立
        max_defaults: int——枚举上限（默认 12）
    输出:
        verdict: str——'evaluated'|'no_extension'|'facts_unsatisfiable'
                        |'undecided'|'size_limit'|'input_pending'|'parse_error'
        extensions: list[dict]——每个扩展：{index, derived, applicable_defaults}
        in_all / in_some / in_none: list[str]——各原子在各扩展中的成立情况
        default_status: list[dict]——每条默认：{default, applicable_in, status}
        ambiguous_defaults: list——从不共存的默认规则对（立场之争）
        query_status: str?——'in_all'|'in_some'|'in_none'（给了 query 才有）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'facts': 'list?', 'defaults': 'list?', 'query': 'str?',
           'max_defaults': 'int?'},
    'out': {'verdict': 'str', 'extensions': 'list', 'in_all': 'list',
            'in_some': 'list', 'in_none': 'list', 'default_status': 'list',
            'ambiguous_defaults': 'list', 'query_status': 'str?',
            'boundary': 'str'},
}

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MAX_ATOMS = 10        # 沿用经典层真值表的原子上限（超了报 undecided）
MAX_DEFAULTS = 12     # 默认条数上限（枚举 2^n 个子集）
_TOP_WORDS = ('⊤', 'true', 'True', 'T', '真', '空', '无')
_BOT_WORDS = ('⊥', 'false', 'False', 'F', '假')

BOUNDARY = ('默认逻辑（Reiter 1980 原义）：扩展 = 算子 Γ 的不动点，在默认条数的 '
            '2^n 个子集上枚举候选再逐个验不动点——**完整**（不漏扩展）。'
            '一条默认生效要求前提推得出**且**辩护不被推翻；"有例外就阻断"是 '
            'agm_revision 的简化版，不是本构件。只做有限命题情形；原子数超上限报 '
            'undecided（算不动 ≠ 没有扩展），默认条数超上限报 size_limit。'
            '有的理论本来就没有扩展（报 no_extension，是语义结果）。只诊断不决策：'
            '规则本身合不合理由使用者判断。')


# ── 复用第 1 层命题构件的解析与求值（同仓同语义，不另写一套）
def _prop():
    """取命题逻辑的 parse / atoms_of / eval_ast。"""
    try:
        from engine.classical.propositional import (parse, atoms_of, eval_ast)
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        from propositional import parse, atoms_of, eval_ast
    return parse, atoms_of, eval_ast


def _is_word(x, words):
    return isinstance(x, str) and x.strip() in words


def _prepare(formula, prop, where):
    """公式 → 节点：('top',) / ('bot',) / 语法树。混写 ⊤⊥ 中间一律拒。"""
    parse = prop[0]
    if formula is None or _is_word(formula, _TOP_WORDS):
        return ('top',)
    if _is_word(formula, _BOT_WORDS):
        return ('bot',)
    if not isinstance(formula, str) or not formula.strip():
        raise ValueError(f'{where} 要是命题式（或省略表示无前提），得到 {formula!r}')
    body = formula.strip()
    for sym in ('⊤', '⊥'):
        if sym in body:
            raise ValueError(f'{where} 里的 {sym} 只能整条用（表示无前提/恒假），'
                             f'不能混在式子中间：{formula!r}')
    try:
        return parse(body)
    except Exception as e:  # noqa: BLE001——解析器抛什么都归成"解析不了"
        raise ValueError(f'{where} 解析不了（{formula!r}）：{e}')


def _norm_default(d, prop, idx):
    """把四种写法归一成 (α, β, γ) 三个节点 + 一条给人看的标签。"""
    where = f'第 {idx} 条默认规则'
    if isinstance(d, dict):
        alpha = _prepare(d.get('prerequisite'), prop, where + '的前提')
        gamma = _prepare(d.get('consequent'), prop, where + '的结论')
        beta = _prepare(d.get('justification'), prop, where + '的辩护')
        if _is_word(d.get('justification'), _TOP_WORDS) or 'justification' not in d:
            beta = gamma                      # 没写辩护 = 正常默认（β = γ）
    elif isinstance(d, (list, tuple)):
        if len(d) == 2:
            alpha = _prepare(d[0], prop, where + '的前提')
            gamma = _prepare(d[1], prop, where + '的结论')
            beta = gamma
        elif len(d) == 3:
            alpha = _prepare(d[0], prop, where + '的前提')
            beta = _prepare(d[1], prop, where + '的辩护')
            gamma = _prepare(d[2], prop, where + '的结论')
        else:
            raise ValueError(f'{where} 应是 (前提,结论) 或 (前提,辩护,结论)，'
                             f'得到 {len(d)} 项')
    elif isinstance(d, str):
        body, sep, cons = d.rpartition('/')
        if not sep:
            raise ValueError(f'{where} 字符串要写成「前提 : 辩护 / 结论」，'
                             f'得到 {d!r}')
        pre, sep2, jus = body.rpartition(':')
        if not sep2:
            pre, jus = body, cons           # 只有「前提 / 结论」= 正常默认
        alpha = _prepare(pre, prop, where + '的前提')
        beta = _prepare(jus, prop, where + '的辩护')
        gamma = _prepare(cons, prop, where + '的结论')
    else:
        raise ValueError(f'{where} 写法不认识：{d!r}')
    if gamma[0] == 'top':
        raise ValueError(f'{where} 的结论不能是 ⊤（推不出东西的默认没有意义）')
    label = '%s : %s / %s' % (_show_node(alpha), _show_node(beta),
                              _show_node(gamma))
    return alpha, beta, gamma, label


def _show_node(node):
    """节点 → 给人看的字符串（只为标签与说明）。"""
    if node[0] == 'top':
        return '⊤'
    if node[0] == 'bot':
        return '⊥'
    return _render(node)


def _render(ast):
    """语法树 → 字符串。"""
    op = ast[0]
    if op == 'atom':
        return ast[1]
    if op == '¬':
        return '¬' + _render(ast[1])
    return '(%s %s %s)' % (_render(ast[1]), op, _render(ast[2]))


def _atoms_of_all(nodes, prop):
    atoms_of = prop[1]
    out, seen = [], set()
    for node in nodes:
        if node[0] in ('top', 'bot'):
            continue
        for a in atoms_of(node):
            if a not in seen:
                seen.add(a)
                out.append(a)
    return out


def _mask(node, atoms, prop):
    """节点在所有指派上的真值位掩码（位 i = 第 i 个指派为真）。"""
    if node[0] == 'top':
        return (1 << (1 << len(atoms))) - 1
    if node[0] == 'bot':
        return 0
    eval_ast = prop[2]
    n = len(atoms)
    out = 0
    for mask in range(1 << n):
        assign = {atoms[i]: bool((mask >> (n - 1 - i)) & 1) for i in range(n)}
        if eval_ast(node, assign):
            out |= 1 << mask
    return out


def _literals(models, atoms, atom_masks):
    """这套模型下必然成立的文字（正/负），按原子序给。"""
    out = []
    for a in atoms:
        m = atom_masks[a]
        if models & ~m == 0:
            out.append(a)
        elif models & m == 0:
            out.append('¬' + a)
    return out


def run(inputs):
    """
    做什么：默认逻辑（Reiter 完整不动点）——算出所有扩展与各结论的成立情况。

    返回 dict（见模块 docstring）。
    """
    if not isinstance(inputs, dict):
        return _pending('inputs 必须是 dict')
    facts = inputs.get('facts') or []
    defaults = inputs.get('defaults')
    if not isinstance(facts, (list, tuple)):
        return _pending('facts 应是命题式列表（可空）——诚实拦截')
    if not isinstance(defaults, (list, tuple)) or not defaults:
        return _pending('需 defaults（默认规则），四种写法都认：'
                        "('前提','结论') / ('前提','辩护','结论') / "
                        "{'prerequisite':…,'justification':…,'consequent':…} / "
                        "'前提 : 辩护 / 结论'——诚实拦截")
    max_def = inputs.get('max_defaults', MAX_DEFAULTS)
    if not isinstance(max_def, int) or max_def < 1:
        return _pending('max_defaults 应是正整数——诚实拦截')
    if len(defaults) > max_def:
        return _sized(f'默认规则 {len(defaults)} 条 > 上限 {max_def}——'
                      f'2^n 个子集枚举不硬跑')

    prop = _prop()
    try:
        fact_nodes = [_prepare(f, prop, f'第 {i + 1} 条事实')
                      for i, f in enumerate(facts)]
        norm = [_norm_default(d, prop, i + 1) for i, d in enumerate(defaults)]
    except ValueError as e:
        return {'verdict': 'parse_error', 'extensions': [], 'in_all': [],
                'in_some': [], 'in_none': [], 'default_status': [],
                'ambiguous_defaults': [], 'query_status': None,
                'boundary': str(e)}

    nodes = list(fact_nodes)
    for alpha, beta, gamma, _lab in norm:
        nodes += [alpha, beta, gamma]
    # query 里的新原子也要进原子集，否则算 query 时会找不到指派（踩过）
    query = inputs.get('query')
    q_node, q_err = None, None
    if isinstance(query, str) and query.strip():
        try:
            q_node = _prepare(query, prop, 'query')
            nodes.append(q_node)
        except ValueError as e:
            q_node, q_err = None, str(e)
    atoms = _atoms_of_all(nodes, prop)
    if len(atoms) > MAX_ATOMS:
        return {'verdict': 'undecided', 'extensions': [], 'in_all': [],
                'in_some': [], 'in_none': [], 'default_status': [],
                'ambiguous_defaults': [], 'query_status': None,
                'boundary': f'原子 {len(atoms)} 个 > 真值表上限 {MAX_ATOMS}——'
                            '算不动（**算不动 ≠ 没有扩展**），不冒充结论'}

    try:
        all_of = (1 << (1 << len(atoms))) - 1
        atom_masks = {a: _mask(('atom', a), atoms, prop) for a in atoms}
        facts_mask = all_of
        for node in fact_nodes:
            facts_mask &= _mask(node, atoms, prop)
        masks = []
        for alpha, beta, gamma, lab in norm:
            masks.append({'alpha': _mask(alpha, atoms, prop),
                          'beta': _mask(beta, atoms, prop),
                          'gamma': _mask(gamma, atoms, prop),
                          'label': lab})
    except Exception as e:  # noqa: BLE001——真出意外如实报，不假装有结论
        return {'verdict': 'undecided', 'extensions': [], 'in_all': [],
                'in_some': [], 'in_none': [], 'default_status': [],
                'ambiguous_defaults': [], 'query_status': None,
                'boundary': f'求值遇到意外（{type(e).__name__}: {e}）——不硬给结论'}

    if facts_mask == 0:
        return {'verdict': 'facts_unsatisfiable', 'extensions': [], 'in_all': [],
                'in_some': [], 'in_none': [], 'default_status': [],
                'ambiguous_defaults': [], 'query_status': None,
                'boundary': '事实集自相矛盾：经典上"全部公式"平凡地算一个扩展，'
                            '那种平凡扩展对诊断没有用——本构件如实报"事实打架"，'
                            '不报"有扩展"。请先修事实集。'}

    n = len(masks)
    found = {}                                # 模型集 → 扩展记录（同一理论只留一份）
    for subset in range(1 << n):              # 候选：默认结论的任意子集
        t_models = facts_mask
        for i in range(n):
            if (subset >> i) & 1:
                t_models &= masks[i]['gamma']
        if t_models == 0:
            continue
        applic = [i for i in range(n)
                  if (t_models & ~masks[i]['alpha']) == 0      # α ∈ Th(T)
                  and (t_models & masks[i]['beta']) != 0]      # ¬β ∉ Th(T)（辩护没被推翻）
        g_models = facts_mask
        for i in applic:
            g_models &= masks[i]['gamma']
        if g_models != t_models:              # 不动点才算扩展
            continue
        if t_models in found:
            continue
        found[t_models] = applic

    if not found:
        return {'verdict': 'no_extension', 'extensions': [], 'in_all': [],
                'in_some': [], 'in_none': list(atoms) + ['¬' + a for a in atoms],
                'default_status': [{'default': m['label'], 'applicable_in': [],
                                    'status': 'never'} for m in masks],
                'ambiguous_defaults': [], 'query_status': None,
                'boundary': '一个扩展都没有——这是这套默认规则**语义上的结果**'
                            '（例如「无前提 : P / ¬P」自相拆台），不是算不出来。'
                            '可以试试把例外写进前提，或补一条事实。'}

    ext_models = sorted(found, key=lambda m: (bin(m).count('1'), m))
    index_of = {m: i + 1 for i, m in enumerate(ext_models)}
    extensions, literal_sets = [], []
    for m in ext_models:
        lits = _literals(m, atoms, atom_masks)
        literal_sets.append(set(lits))
        extensions.append({'index': index_of[m], 'derived': lits,
                           'applicable_defaults':
                               [masks[i]['label'] for i in found[m]]})

    in_all, in_some, in_none = [], [], []
    for a in atoms:
        for lit in (a, '¬' + a):
            where = [lit in s for s in literal_sets]
            if all(where):
                in_all.append(lit)
            elif any(where):
                in_some.append(lit)
            else:
                in_none.append(lit)

    default_status = []
    for i, m in enumerate(masks):
        where = [index_of[mm] for mm in ext_models if i in found[mm]]
        state = ('always' if len(where) == len(ext_models)
                 else ('never' if not where else 'sometimes'))
        default_status.append({'default': m['label'], 'applicable_in': where,
                               'status': state})

    ambiguous = []
    for i in range(n):
        for j in range(i + 1, n):
            if not any(i in found[mm] and j in found[mm] for mm in ext_models):
                ambiguous.append([masks[i]['label'], masks[j]['label']])

    out = {'verdict': 'evaluated', 'extensions': extensions,
           'in_all': in_all, 'in_some': in_some, 'in_none': in_none,
           'default_status': default_status,
           'ambiguous_defaults': ambiguous, 'query_status': None,
           'boundary': _boundary_text(len(ext_models), len(atoms))}

    if q_err:
        out['boundary'] += f'（query 没算：{q_err}）'
    elif q_node is not None:
        q_mask = _mask(q_node, atoms, prop)
        holds = [m for m in ext_models if m & ~q_mask == 0]
        if len(holds) == len(ext_models):
            out['query_status'] = 'in_all'
        elif holds:
            out['query_status'] = 'in_some'
        else:
            out['query_status'] = 'in_none'
    return out


def _boundary_text(n_ext, n_atoms):
    return (f'默认逻辑（Reiter 1980 原义，借鉴区）：扩展 = Γ 的不动点，本构件在默认'
            f'结论的 2^n 个子集上枚举候选、逐个验不动点，得到 {n_ext} 个扩展。'
            f'一条默认生效要求前提推得出**且**辩护不被推翻（"有例外就阻断"是 '
            f'agm_revision 的简化版，不是这里）。只做有限命题情形（原子 {n_atoms} 个）；'
            '同一原子在所有扩展里都成立 = 怀疑论结论，只在部分扩展成立 = 轻信论结论。'
            '只诊断不决策：规则本身合不合理由使用者判断。')


def _pending(msg):
    return {'verdict': 'input_pending', 'extensions': [], 'in_all': [],
            'in_some': [], 'in_none': [], 'default_status': [],
            'ambiguous_defaults': [], 'query_status': None, 'boundary': msg}


def _sized(msg):
    return {'verdict': 'size_limit', 'extensions': [], 'in_all': [],
            'in_some': [], 'in_none': [], 'default_status': [],
            'ambiguous_defaults': [], 'query_status': None, 'boundary': msg}


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
    print('默认逻辑（Reiter 完整不动点）构件 · 自测（第 3 层 3.3 补件）')
    print('=' * 68)

    # 1) 单条正常默认：鸟 → 会飞
    r1 = run({'facts': ['鸟'], 'defaults': [('鸟', '会飞')]})
    assert r1['verdict'] == 'evaluated', r1
    assert len(r1['extensions']) == 1, r1
    assert set(r1['extensions'][0]['derived']) == {'会飞', '鸟'}, r1
    assert set(r1['in_all']) == {'会飞', '鸟'}, r1
    print(f"✅ 鸟 + (鸟:会飞/会飞) → 1 个扩展，共同结论 {r1['in_all']}")

    # 2) Reiter 原义下"鸟/企鹅"是**两个**扩展（歧义，不是 bug）
    r2 = run({'facts': ['鸟', '企鹅'],
              'defaults': [('鸟', '会飞'), ('企鹅', '¬会飞')]})
    assert r2['verdict'] == 'evaluated', r2
    assert len(r2['extensions']) == 2, r2
    assert '会飞' in r2['in_some'] and '¬会飞' in r2['in_some'], r2
    print(f"✅ 鸟+企鹅（两条默认各管各的）→ {len(r2['extensions'])} 个扩展："
          f"会飞/¬会飞 都只是「部分扩展成立」——Reiter 原义的歧义")

    # 3) 把例外写进前提 → 只剩一个扩展（Reiter 的标准写法）
    r3 = run({'facts': ['鸟', '企鹅'],
              'defaults': [('鸟 ∧ ¬企鹅', '会飞'), ('企鹅', '¬会飞')]})
    assert r3['verdict'] == 'evaluated', r3
    assert len(r3['extensions']) == 1, r3
    assert '¬会飞' in r3['in_all'] and '会飞' in r3['in_none'], r3
    print(f"✅ 例外写进前提（鸟∧¬企鹅 : 会飞 / 会飞）→ 1 个扩展，"
          f"共同结论含 {r3['in_all']}")

    # 4) 没有扩展的理论：W=∅，(⊤ : P)/¬P
    r4 = run({'defaults': ['⊤ : P / ¬P']})
    assert r4['verdict'] == 'no_extension', r4
    print(f"✅ 自相拆台的默认 → {r4['verdict']}（语义上就没有不动点，"
          f"不是算不出来）")

    # 5) 平淡默认 (: P)/P → 一个扩展
    r5 = run({'defaults': ['⊤ : P / P']})
    assert r5['verdict'] == 'evaluated' and len(r5['extensions']) == 1, r5
    assert 'P' in r5['in_all'], r5
    print(f"✅ 无前提默认 → 1 个扩展，共同结论 {r5['in_all']}")

    # 6) 边界：事实打架 / 缺参 / 坏写法 / 超上限
    r6 = run({'facts': ['P', '¬P'], 'defaults': [('P', 'Q')]})
    assert r6['verdict'] == 'facts_unsatisfiable', r6
    r7 = run({})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'defaults': [('P',)]})
    assert r8['verdict'] == 'parse_error', r8
    r9 = run({'defaults': [('P', 'Q')] * 13})
    assert r9['verdict'] == 'size_limit', r9
    print('✅ 边界：事实打架 / 缺参 / 坏写法 / 超上限 → 诚实拦截')

    print('=' * 68)
    print('默认逻辑构件自测：全部通过 ✅')
    print('=' * 68)
