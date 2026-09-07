# -*- coding: utf-8 -*-
"""
truth_revision.py — Gupta-Belnap 真值修正 · 真理论演示构件（第 3 层扩展）
=========================================================================
概念来源：**外部经典共识**——Gupta & Belnap (1993) 真值修正理论
（Revision Theory of Truth）：含真谓词的语言没有"一次性"的经典真值
赋值，改用**修正序列**——每轮按真值条件重新计算所有句子的真值，
观察序列走向（稳定值 / 周期振荡 / 不稳定）。本构件为借鉴实现
（落落三问：借什么=修正序列与稳定/振荡分类；为什么=给第 2 层
selfref_fixpoint（2.3 共振带收敛）一个**学界锚点**——说谎者句在
修正理论里落入周期 2 振荡是教科书结论，不是引擎自创；怎么记账=
标注来源归借鉴区）。
详规：ROADMAP 阶段 7（Gupta-Belnap 真值修正——共振带收敛的学界锚点）

与 selfref_fixpoint（2.3，引擎原创）的分工：
    - selfref_fixpoint：单个修正函数 f 的三态观察（不动点/共振带/发散）——
      引擎的诊断工具；
    - 本构件：**多句子的真值赋值向量**按 Gupta-Belnap 框架修正——给
      "共振带收敛"补上学术出处与多句系统（如 P↔Q 真、Q↔P 假 的互相
      引用系统）的观察能力。

本构件做什么（一句话）：
    给定一组句子的真值条件（每句 = 布尔函数 over 全体句子当前真值），
    从初始赋值出发跑 Gupta-Belnap 修正序列，判定走向：
    稳定（收敛到固定赋值）/ 周期振荡（含说谎者经典周期 2）/
    不稳定（无周期）。

诚实边界：
    - 本构件演示有限句子集的修正序列分类（可计算部分）；无限语言/真
      谓词自指的一般理论不在首期（诚实：我们做有限可算的示意）；
    - 周期振荡 ≠ 判定了句子的真值——修正理论说这类句子"无稳定真值，
      落入振荡"（学术结论，非引擎自创）；说谎者取周期 2 是教科书结果；
    - 借来源归借鉴区（Gupta & Belnap 1993），不混原创区。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: str——'demo'（内置三例：说谎者/互指环/良性）| 'custom'
        sentences: dict——custom 模式：{句名: 真值条件 callable}
                   （callable 接收当前赋值 dict{句名: bool} → bool）
        start: dict——初始赋值（缺省全 False）
        max_steps: int——观察上限（默认 50）
    输出:
        verdict: str——'stable'|'periodic'|'unstable'|'input_pending'
        detail: dict——{period, cycle 或 fixed_value, trace 节选, note}
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'sentences': 'dict?', 'start': 'dict?',
           'max_steps': 'int?'},
    'out': {'verdict': 'str', 'detail': 'dict', 'boundary': 'str'},
}


# ── 内置演示句系统（Gupta-Belnap 教科书三例）
def _liar_system():
    """说谎者 P↔¬P：真值条件 = 非自己当前真值 → 周期 2 振荡。"""
    return {'P': lambda a: not a.get('P', False)}


def _mutual_ring():
    """互指环：P 说 Q 真（P 真 ⟺ Q 真），Q 说 P 假（Q 真 ⟺ P 假）。
    解：P=真,Q=假 是唯一解？检查：P=T→Q=T→但 Q 条件为 ¬P=F 矛盾…
    用修正序列观察（这正是 Gupta-Belnap 的价值——不用先解方程）。"""
    return {'P': lambda a: a.get('Q', False),
            'Q': lambda a: not a.get('P', False)}


def _benign():
    """良性：P ⟺ P∧Q，Q=真（无自指矛盾 → 稳定）。"""
    return {'P': lambda a: a.get('Q', False) and a.get('P', False),
            'Q': lambda a: True}


def _observe(conditions, start, max_steps):
    """跑修正序列：赋值向量每轮全量更新。返回 (kind, meta)。"""
    names = list(conditions.keys())
    assign = {n: bool(start.get(n, False)) for n in names}
    trace = []
    seen = []  # (assign_tuple, step)
    for step in range(max_steps):
        trace.append(dict(assign))
        key = tuple(assign[n] for n in names)
        # 周期检测：当前赋值是否曾出现
        for i, (old_key, _old_step) in enumerate(seen):
            if old_key == key:
                period = step - _old_step
                if period == 1:
                    # 周期 1 = 定点：修正序列稳定（良性/可给结果）
                    return 'stable', {'fixed_value': trace[-1],
                                      'trace': trace}
                return 'periodic', {'period': period,
                                    'cycle': trace[i:],
                                    'cycle_start': i,
                                    'trace': trace}
        seen.append((key, step))
        # 修正一步：每句按真值条件重算
        new_assign = {}
        for n in names:
            try:
                new_assign[n] = bool(conditions[n](assign))
            except Exception:
                new_assign[n] = False
        assign = new_assign
    # 序列稳定（连续多步不变）→ stable；否则 unstable
    if len(trace) >= 3 and trace[-1] == trace[-2] == trace[-3]:
        return 'stable', {'fixed_value': trace[-1], 'trace': trace}
    return 'unstable', {'trace': trace, 'steps': max_steps}


def _describe(kind, meta, system_note):
    if kind == 'stable':
        fv = meta.get('fixed_value', {})
        note = ('修正序列收敛到稳定赋值 '
                + str({k: v for k, v in fv.items()}))
    elif kind == 'periodic':
        p = meta.get('period')
        if p == 1:
            # 周期 1 = 自指系统走到定点（等价稳定，只是到达方式为一步）
            note = ('周期 1（一步到定点）：修正序列稳定在 '
                    + str(meta.get('cycle', [{}])[-1])
                    + '——良性（可给结果）')
        elif p == 2:
            note = ('周期 2 振荡——说谎者型：句子在真/假间每步翻转。'
                    '修正理论结论：无稳定真值，落入振荡（学界共识，'
                    '非引擎自创）')
        else:
            note = f'周期 {p} 振荡——修正序列进入长度 {p} 的循环'
    else:
        note = '不稳定：观察窗口内无稳定值也无周期——' \
               '可能需更长观察或属更复杂系统'
    return note


def run(inputs):
    """
    做什么：Gupta-Belnap 真值修正——多句系统修正序列分类。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'demo')
    max_steps = inputs.get('max_steps', 50) or 50

    if mode == 'demo':
        results = {}
        for tag, sys_fn, sn in [('liar', _liar_system, '说谎者 P↔¬P'),
                                ('ring', _mutual_ring, '互指环 P↔Q真/Q↔P假'),
                                ('benign', _benign, '良性 P↔P∧Q')]:
            conds = sys_fn()
            start = inputs.get('start') or {}
            kind, meta = _observe(conds, start, max_steps)
            note = _describe(kind, meta, sn)
            results[tag] = {'verdict': kind, 'note': note,
                            'period': meta.get('period'),
                            'cycle': meta.get('cycle'),
                            'fixed_value': meta.get('fixed_value')}
        return {'verdict': 'demo', 'detail': {'systems': results},
                'boundary': 'Gupta-Belnap 真值修正（外部共识，借鉴区）。'
                            '说谎者周期 2 振荡是教科书结论（非引擎自创）；'
                            '周期振荡≠判定真值（无稳定真值落入振荡）。'
                            '演示为有限句集的可算示意，无限语言一般理论'
                            '不在首期。'}

    if mode == 'custom':
        sentences = inputs.get('sentences')
        if not sentences or not isinstance(sentences, dict):
            return {'verdict': 'input_pending', 'detail': {},
                    'boundary': 'custom 需 sentences：{句名: 真值条件 callable}'
                                '——诚实拦截'}
        bad = [n for n, c in sentences.items() if not callable(c)]
        if bad:
            return {'verdict': 'input_pending', 'detail': {},
                    'boundary': f'句 {bad} 的真值条件不是 callable——诚实拦截'}
        start = inputs.get('start') or {}
        kind, meta = _observe(sentences, start, max_steps)
        note = _describe(kind, meta, 'custom')
        return {'verdict': kind,
                'detail': {'period': meta.get('period'),
                           'cycle': meta.get('cycle'),
                           'fixed_value': meta.get('fixed_value'),
                           'note': note},
                'boundary': 'Gupta-Belnap 修正序列分类（借鉴区）。'
                            '观察窗口有限（max_steps）——unstable 是'
                            '"窗口内未见"，非理论判决。'}
    return {'verdict': 'input_pending', 'detail': {},
            'boundary': f"mode 应为 demo/custom，得到 {mode!r}——诚实拦截"}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('Gupta-Belnap 真值修正 · 自测（第 3 层扩展）')
    print('=' * 62)

    # 1) demo 三例
    r1 = run({'mode': 'demo'})
    assert r1['verdict'] == 'demo', r1
    sys_ = r1['detail']['systems']
    assert sys_['liar']['verdict'] == 'periodic', r1
    assert sys_['liar']['period'] == 2, r1
    assert '教科书' in sys_['liar']['note'] or '学界' in sys_['liar']['note'], r1
    print(f"✅ 说谎者 P↔¬P → {sys_['liar']['verdict']}（周期 "
          f"{sys_['liar']['period']}——教科书结论）")
    assert sys_['ring']['verdict'] in ('periodic', 'stable'), r1
    print(f"✅ 互指环 → {sys_['ring']['verdict']}"
          f"（period={sys_['ring'].get('period')}）")
    assert sys_['benign']['verdict'] == 'stable', r1
    print(f"✅ 良性 P↔P∧Q → {sys_['benign']['verdict']}"
          f"（定点 {sys_['benign'].get('fixed_value')}）")

    # 2) custom：自定义句系统
    r2 = run({'mode': 'custom',
              'sentences': {'A': lambda a: not a.get('A', False)},
              'start': {'A': False}, 'max_steps': 20})
    assert r2['verdict'] == 'periodic' and r2['detail']['period'] == 2, r2
    print(f"✅ custom 说谎者 → {r2['verdict']}（周期 {r2['detail']['period']}）")

    # 3) custom：稳定系统
    r3 = run({'mode': 'custom',
              'sentences': {'A': lambda a: True},
              'start': {'A': False}})
    assert r3['verdict'] == 'stable', r3
    print(f"✅ custom A⟺真 → {r3['verdict']}")

    # 4) 边界
    r4 = run({'mode': 'xx'})
    assert r4['verdict'] == 'input_pending', r4
    r5 = run({'mode': 'custom'})
    assert r5['verdict'] == 'input_pending', r5
    r6 = run({'mode': 'custom', 'sentences': {'A': 'not_callable'}})
    assert r6['verdict'] == 'input_pending', r6
    print('✅ 坏 mode / 缺句 / 非 callable → input_pending')

    print('=' * 62)
    print('Gupta-Belnap 真值修正构件自测：全部通过 ✅')
    print('=' * 62)
