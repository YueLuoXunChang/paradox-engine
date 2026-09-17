# -*- coding: utf-8 -*-
"""
agm_revision.py — AGM 信念修正 · 非单调推理构件（第 3 层冷门 3.3）
====================================================================
概念来源：**外部经典共识**——AGM 模型（Alchourrón, Gärdenfors & Makinson
1985）信念修正 + 非单调逻辑（Reiter 默认逻辑）。本构件为借鉴实现
（落落三问：借什么=AGM 三操作[扩张/收缩/修正]与非单调默认推理；
为什么=T5 知识更新痛点的核心构件——"所有天鹅白 + 发现黑天鹅"要能
撤销旧结论，而经典逻辑单调（新前提不推翻旧结论）；怎么记账=标注
来源归借鉴区）。
详规：第 3 层冷门详规 §三（非单调/AGM 信念修正）

本构件做什么（一句话）：
    给"新信息来了旧结论还成立吗"一个可跑答案——两个能力：
    ① **AGM 修正**：旧信念集 B + 新信息 φ → 若 B∪{φ} 不一致，按
       **最小放弃原则**（改动最小 + 优先级最低者先弃）收缩出 B'，
       使 B' 一致且含 φ；
    ② **非单调默认推理**：默认规则（鸟 ⇒ 默认会飞）+ 例外（企鹅不会飞）
       → 输出可废止结论（有例外时默认被阻断，而非推出矛盾）。

与经典层的差别（为什么算冷门）：
    - 经典逻辑**单调**：Γ ⊢ C ⟹ Γ∪{φ} ⊢ C（新前提不推翻旧结论）；
    - 非单调：新信息可**撤销**旧结论（黑天鹅撤销"所有天鹅白"）——
      AI 学习、科研假设修正的现实形态。

诚实边界：
    - 一致性判定复用经典命题逻辑（须给可判定的命题式）——自然语言
      需要先结构化（诚实：不做通用 NLP 抽取）；
    - 极小收缩在信念数上限内枚举（>上限诚实报 size_limit）；
    - 一致性判定复用经典命题逻辑，而经典层 truth-table 枚举有 **原子数
      上限 10**——超限时本构件报 'undecided'（算不动），**绝不冒充
      "不一致"**去乱弃信念（诚实边界：算不动 ≠ 矛盾）；
    - AGM 三公理（成功/包含/一致性）逐条可验，但"最优修正"依赖
      优先级输入（entrenchment 信念度）——不替使用者定优先级；
    - 默认推理是**可废止**的（defeasible）：结论标"默认成立"，有例外
      即阻断，不给绝对真值。

统一接口：
    run(inputs: dict) -> dict
    输入（mode='revise'）:
        beliefs: list[str]——旧信念集（命题式，如 ['P→Q', 'P']）
        new_info: str——新信息（命题式，如 '¬Q'）
        priorities: dict[str,int]——信念优先级（越大越不易放弃，可省）
        max_beliefs: int——枚举上限（默认 12）
    输入（mode='default'）:
        defaults: list[tuple]——默认规则 [(前提, 默认结论), ...]
        facts: list[str]——已知事实
        exceptions: list[str]——例外条件（命中则阻断默认）
    输出:
        verdict: str——'revised'|'consistent'|'size_limit'|'input_pending'
                        |'default_reasoned'|'undecided'
                        |'new_info_unsatisfiable'
        kept: list[str]——修正后保留的信念
        dropped: list[str]——被放弃的信念
        conclusions: list[dict]——默认推理结论（含 status: holds/blocked）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'beliefs': 'list?', 'new_info': 'str?',
           'priorities': 'dict?', 'defaults': 'list?', 'facts': 'list?',
           'exceptions': 'list?', 'max_beliefs': 'int?'},
    'out': {'verdict': 'str', 'kept': 'list', 'dropped': 'list',
            'conclusions': 'list', 'boundary': 'str'},
}

import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _get_prop():
    """取经典命题逻辑的 satisfiable 判定（一致性检查用）。"""
    try:
        from engine.classical.propositional import run as pl
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'classical'))
        from propositional import run as pl
    return pl


def _consistent(prop, formulas):
    """
    一致性检查：formulas 全体可同时为真吗？
    做法：合取式（A∧B∧C）是否可满足——可满足 ⟺ 一致。
    返回 (state, reason)，**三态**：
      'yes'     —— 可满足 = 一致；
      'no'      —— 不可满足 = 不一致；
      'unknown' —— 经典层算不动（如原子数超真值表枚举上限 10）→
                   **不冒充"不一致"**，否则会把自洽信念集错判成矛盾、
                   平白弃掉一堆信念（诚实边界）。
    """
    if not formulas:
        return 'yes', '空集视为一致'
    conj = '∧'.join(f'({f})' for f in formulas)
    r = prop({'formula': conj, 'mode': 'satisfiable'})
    v = r.get('verdict')
    if v == 'satisfiable':
        return 'yes', ''
    if v == 'unsatisfiable':
        return 'no', ''
    return 'unknown', f"{v}（{r.get('boundary', '')}）"


def _minimal_drops(prop, beliefs, new_info, priorities, max_beliefs):
    """
    找最小放弃集：枚举"放弃 k 个信念"（k 从小到大），
    返回第一个使 (beliefs - dropped) ∪ {new_info} 一致的最小放弃集列表。
    返回 (candidates, tested, unknown_reason)；candidates 空时，
    unknown_reason 非空表示"不是无解，是算不动"（诚实区分）。
    """
    n = len(beliefs)
    tested = 0
    unknown_reason = ''
    for k in range(0, n + 1):
        candidates = []
        for drop_idx in itertools.combinations(range(n), k):
            dropped = {beliefs[i] for i in drop_idx}
            kept = [b for b in beliefs if b not in dropped]
            tested += 1
            state, why = _consistent(prop, kept + [new_info])
            if state == 'yes':
                candidates.append(sorted(dropped))
            elif state == 'unknown' and not unknown_reason:
                unknown_reason = why
        if candidates:
            # 同规模候选中，按优先级和最小选（信念度低者先弃）
            def cost(drop_set):
                return sum(priorities.get(b, 0) for b in drop_set)
            candidates.sort(key=cost)
            return candidates, tested, ''
    return [], tested, unknown_reason


def _default_reasoning(defaults, facts, exceptions):
    """
    非单调默认推理（Reiter 简化版）：
    默认 [(前提, 结论)] + facts；若存在例外命中该默认结论的前提 → 阻断。
    诚实：这是工程化简化（不做完整默认逻辑不动点），标注清楚。
    """
    conclusions = []
    fact_blob = '，'.join(str(f) for f in facts)
    exc_blob = '，'.join(str(e) for e in exceptions)
    for pre, con in defaults:
        blocked = False
        reason = ''
        # 例外检查：例外条件与 facts 同现（子串匹配，工程约定）
        for exc in exceptions:
            if exc and (exc in fact_blob or exc in exc_blob):
                # 例外直接针对该默认前提或结论
                if exc in str(pre) or exc in str(con) or exc in fact_blob:
                    blocked = True
                    reason = f'命中例外「{exc}」→ 默认「{pre} ⇒ {con}」被阻断'
                    break
        # 前提是否满足（facts 含前提或前提子串）
        prem_met = bool(pre) and (str(pre) in fact_blob)
        if not prem_met and not blocked:
            status = 'not_applicable'
            reason = reason or f'前提「{pre}」未满足'
        elif blocked:
            status = 'blocked'
        else:
            status = 'holds'
            reason = reason or f'前提「{pre}」满足且无例外 → 默认结论成立'
        conclusions.append({'default': f'{pre} ⇒ {con}', 'status': status,
                            'reason': reason})
    return conclusions


def run(inputs):
    """
    做什么：AGM 信念修正 / 非单调默认推理。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'revise')

    if mode == 'default':
        defaults = inputs.get('defaults')
        if not defaults:
            return {'verdict': 'input_pending', 'kept': [], 'dropped': [],
                    'conclusions': [],
                    'boundary': 'mode=default 需 defaults：[（前提, 默认结论）'
                                '…]——诚实拦截，不硬推'}
        facts = inputs.get('facts') or []
        exceptions = inputs.get('exceptions') or []
        conclusions = _default_reasoning(defaults, facts, exceptions)
        return {'verdict': 'default_reasoned', 'kept': [], 'dropped': [],
                'conclusions': conclusions,
                'boundary': '非单调默认推理（外部共识：Reiter 默认逻辑，'
                            '借鉴区）。默认结论是**可废止**的：有例外即阻断，'
                            '不给绝对真值；本实现为工程简化（不做完整默认'
                            '逻辑不动点），诚实标注。'}

    if mode != 'revise':
        return {'verdict': 'input_pending', 'kept': [], 'dropped': [],
                'conclusions': [],
                'boundary': f"mode 应为 revise/default，得到 {mode!r}"
                            '——诚实拦截'}

    beliefs = inputs.get('beliefs') or []
    new_info = inputs.get('new_info')
    if not beliefs or not new_info:
        return {'verdict': 'input_pending', 'kept': [], 'dropped': [],
                'conclusions': [],
                'boundary': 'mode=revise 需 beliefs（旧信念集）+ new_info'
                            '（新信息）——诚实拦截'}
    priorities = inputs.get('priorities') or {}
    max_beliefs = inputs.get('max_beliefs', 12)
    if len(beliefs) > max_beliefs:
        return {'verdict': 'size_limit', 'kept': [], 'dropped': [],
                'conclusions': [],
                'boundary': f'信念 {len(beliefs)} > 上限 {max_beliefs}——'
                            '枚举极小收缩的规模诚实报告，不硬跑'}

    prop = _get_prop()

    # ⓪ 一致性判定本身算不动 → 诚实拦截（不冒充"不一致"乱弃信念）
    state0, why0 = _consistent(prop, beliefs + [new_info])
    if state0 == 'unknown':
        return {'verdict': 'undecided', 'kept': [], 'dropped': [],
                'conclusions': [],
                'boundary': f'一致性判定算不动：{why0}——诚实报告，'
                            '既不硬判"不一致"（会平白弃掉自洽信念），'
                            '也不硬给修正结果。建议减少原子数或拆式。'}

    # ① 一致性：B ∪ {φ} 一致 → 直接扩张（无需放弃）
    if state0 == 'yes':
        return {'verdict': 'consistent', 'kept': list(beliefs),
                'dropped': [], 'conclusions': [],
                'boundary': f'B∪{{{new_info}}} 一致 → 直接扩张（无信念被'
                            '放弃）。AGM 扩张操作。'}

    # ② 不一致 → 最小放弃收缩 + 加入 φ（AGM 修正 B'=(B-α)+φ）
    drops_list, tested, unknown_reason = _minimal_drops(
        prop, beliefs, new_info, priorities, max_beliefs)
    if not drops_list:
        if unknown_reason:
            return {'verdict': 'undecided', 'kept': [], 'dropped': [],
                    'conclusions': [],
                    'boundary': f'未找到可行收缩，但一致性判定算不动：'
                                f'{unknown_reason}——诚实报告，不硬给结果。'}
        # 枚举到底：连 k=n（只留 φ）都不一致 → 新信息本身不可满足
        st_phi, why_phi = _consistent(prop, [new_info])
        if st_phi == 'no':
            return {'verdict': 'new_info_unsatisfiable', 'kept': [],
                    'dropped': [], 'conclusions': [],
                    'boundary': f'新信息 {new_info!r} 自身不可满足 → 无一致'
                                '信念集能容纳它，AGM 修正无解（诚实报告，'
                                '不硬凑结果）。'}
        return {'verdict': 'size_limit', 'kept': [], 'dropped': [],
                'conclusions': [],
                'boundary': '枚举耗尽未找到可行收缩——诚实报告，'
                            '不硬给结果'}
    dropped = drops_list[0]
    kept = [b for b in beliefs if b not in dropped]
    return {'verdict': 'revised', 'kept': kept + [new_info],
            'dropped': dropped,
            'conclusions': [],
            'boundary': f'B∪{{{new_info}}} 不一致 → 按最小放弃原则收缩：'
                        f'放弃 {dropped}（同规模候选中优先级和最小）'
                        f'，得 B\' 一致且含新信息。AGM 修正操作'
                        f'（三公理：成功/包含/一致性成立）。'
                        f'枚举 {tested} 个子集。'}


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
    print('AGM 信念修正 · 非单调推理构件 · 自测（第 3 层 3.3）')
    print('=' * 62)

    # 1) 一致 → 直接扩张（无需放弃）
    r1 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'],
              'new_info': 'Q'})
    assert r1['verdict'] == 'consistent', r1
    assert r1['dropped'] == [], r1
    print(f"✅ B={{P→Q, P}} + Q → {r1['verdict']}（直接扩张，无放弃）")

    # 2) 不一致 → 最小放弃（天鹅例的命题版）
    r2 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
    assert r2['verdict'] == 'revised', r2
    assert len(r2['dropped']) == 1, r2
    assert '¬Q' in r2['kept'], r2
    print(f"✅ B={{P→Q, P}} + ¬Q → 放弃 {r2['dropped']}（最小放弃，"
          f"kept={r2['kept']}）")

    # 3) 优先级影响放弃对象（信念度低者先弃）
    r3 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
              'priorities': {'P→Q': 1, 'P': 10}})
    assert r3['dropped'] == ['P→Q'], r3
    print(f"✅ 优先级：P 信念度高(10) → 放弃低者 {r3['dropped']}")

    # 4) 默认推理：鸟会飞 + 无例外 → 成立
    r4 = run({'mode': 'default', 'defaults': [('鸟', '会飞')],
              'facts': ['鸟'], 'exceptions': []})
    assert r4['verdict'] == 'default_reasoned', r4
    assert r4['conclusions'][0]['status'] == 'holds', r4
    print(f"✅ 默认「鸟⇒会飞」+ 事实鸟 → {r4['conclusions'][0]['status']}")

    # 5) 默认推理：企鹅例外 → 阻断（可废止性——非单调核心）
    r5 = run({'mode': 'default', 'defaults': [('鸟', '会飞')],
              'facts': ['鸟', '鸟(企鹅)'], 'exceptions': ['鸟(企鹅)']})
    assert r5['conclusions'][0]['status'] == 'blocked', r5
    print(f"✅ 企鹅例外 → {r5['conclusions'][0]['status']}"
          f"（{r5['conclusions'][0]['reason'][:30]}…）——可废止")

    # 6) 边界
    r6 = run({'mode': 'xx'})
    assert r6['verdict'] == 'input_pending', r6
    r7 = run({'mode': 'revise', 'beliefs': ['P']})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'mode': 'default'})
    assert r8['verdict'] == 'input_pending', r8
    r9 = run({'mode': 'revise', 'beliefs': [f'P{i}' for i in range(15)],
              'new_info': 'Q', 'max_beliefs': 12})
    assert r9['verdict'] == 'size_limit', r9
    print('✅ 边界：坏 mode/缺参/超上限 → 诚实拦截')

    # 7) 算不动 ≠ 不一致（原子数超经典层枚举上限 → undecided，不乱弃信念）
    r10 = run({'mode': 'revise', 'beliefs': [f'P{i}' for i in range(12)],
               'new_info': 'Q'})
    assert r10['verdict'] == 'undecided', r10
    assert r10['dropped'] == [], r10
    print(f"✅ 原子数超枚举上限 → {r10['verdict']}（不冒充不一致，"
          f"dropped 为空）")

    # 8) 新信息本身不可满足 → 无解（诚实报告）
    r11 = run({'mode': 'revise', 'beliefs': ['P'], 'new_info': 'Q∧¬Q'})
    assert r11['verdict'] == 'new_info_unsatisfiable', r11
    print(f"✅ 新信息 {r11['verdict']} → 不硬凑结果")

    print('=' * 62)
    print('AGM 信念修正构件自测：全部通过 ✅')
    print('=' * 62)
