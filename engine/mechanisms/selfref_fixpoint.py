# -*- coding: utf-8 -*-
"""
selfref_fixpoint.py — 递归修正 × 自指检测构件（第 2 层悖论创生 2.3，钻墙主力）
================================================================================
概念来源：落落逻辑体系原创——递归修正公理（修正不是消除，
是逼近可接受态）+ P-Logic 自指递归四态（有限收敛/渐进收敛/发散/
自指悖论[每步翻转]）+ 无限递归收敛三态（不动点收敛/
共振带收敛/发散）。非外部共识，落落原创区。
详规：《逻辑建模引擎_第2层悖论创生详规》§三
组合：管线 A"钻墙"步（40 组合方案 §三 A）

本构件做什么（一句话）：
    把"不可判定/自指"从死胡同变成可诊断态——跑递归修正序列
    x_{n+1}=f(x_n) 观测定态：不动点收敛（良性自指）/ 共振带收敛
    （悖论型自指：振荡但稳定）/ 发散（真墙）/ 自指悖论态（每步翻转）。

诚实边界（钉死，不越线）：
    - 共振带收敛 ≠ 判定了说谎者真值——只说"修正序列在稳定范围内
      振荡"（判振荡模式，不判真值，不违反哥德尔）；
    - 哥德尔型（"本句不可证"）→ 注解 P-A + 明确声明"此为算术编码自指，
      经典框架不可判定；引擎立场：测度+注解+振荡观察，不宣称判定"；
    - 观察窗口不足 → 诚实报 undetermined（可能还需更多步），不硬判发散。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: str——'iterate'（自定义修正函数）| 'sentence'（内置自指句）
        f: callable——mode='iterate' 时必填，修正函数 f(state)->state
        state0: any——迭代初值（默认 False）
        sentence: str——mode='sentence' 时用：'liar'|'truth_teller'|'godel'
        max_steps: int——观察窗口（默认 100）
        tol: float——数值状态判重容差（默认 1e-9）
    输出:
        verdict: str——'fixed_point'|'resonance_band'|'diverge'|
                        'liar_cycle'|'annotated_pa'|'undetermined'|
                        'input_pending'
        selfref_type: str——'liar'|'truth_teller'|'godel'|'custom'
        detail: dict——白箱（周期/范围/到达步/轨迹节选等）
        annotation: dict 或 None——8 字段注解卡（悖论型/结构性时给出）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'f': 'callable?', 'state0': 'any?',
           'sentence': 'str?', 'max_steps': 'int?', 'tol': 'float?'},
    'out': {'verdict': 'str', 'selfref_type': 'str', 'detail': 'dict',
            'annotation': 'dict', 'boundary': 'str'},
}


def _same(a, b, tol):
    """判重：相等或数值容差内相等。"""
    try:
        if a == b:
            return True
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) < tol
    except Exception:
        pass
    return False


def _observe(f, state0, max_steps, tol):
    """
    跑修正序列并观测定态。返回 (kind, meta)。
    kind: 'fixed_point' | 'cycle' | 'grow' | 'open'
    meta: 补充信息 dict。
    """
    trace = [state0]   # 完整轨迹（白箱）
    seen = [state0]    # 已访问状态（判重用，含初值）
    state = state0
    for step in range(max_steps):
        nxt = f(state)
        trace.append(nxt)
        # 不动点：f(x)=x（数值容差内也算）
        if _same(nxt, state, tol):
            return 'fixed_point', {'reached_at': step + 1,
                                   'fixed_value': nxt,
                                   'trace': trace}
        # 周期检测：新状态是否曾在 seen 中出现（有限值域抽屉原理必重复）
        for i, s in enumerate(seen):
            if _same(s, nxt, tol):
                period = len(seen) - i
                return 'cycle', {'period': period, 'cycle_start': i,
                                 'cycle': trace[i + 1:], 'trace': trace}
        seen.append(nxt)
        state = nxt
        # 数值发散试探：|x| 持续放大且超阈值（仅数值状态）
        if isinstance(nxt, (int, float)) and abs(nxt) > 1e12:
            return 'grow', {'trace': trace}
    return 'open', {'trace': trace, 'steps': max_steps}


# 内置自指句的修正函数（sentence 模式）
def _liar_fn(state):
    """说谎者 P↔¬P：真值修正即翻转（自指悖论态/每步翻转）。"""
    return not state


def _truth_teller_fn(state):
    """本句为真 P↔P：修正即恒等（每个初值都是不动点——无信息量）。"""
    return state


def _to_card(verdict, sentence, detail, selfref_type):
    """生成 8 字段注解卡（复用体系注解语义；不引入跨文件依赖，直接构造）。"""
    if verdict == 'resonance_band':
        note = (f"共振带收敛：修正序列在稳定范围内振荡（周期 "
                f"{detail.get('period', '?')}）——判振荡模式，不判真值")
    elif verdict == 'liar_cycle':
        note = "说谎者核：每步翻转（真/假/真/假…）——自指悖论态，振荡稳定"
    elif verdict == 'annotated_pa':
        note = ("哥德尔型：算术编码自指（本句不可证），经典框架不可判定——"
                "引擎立场：测度+注解+振荡观察，不宣称判定")
    elif verdict == 'fixed_point':
        note = f"良性自指：修正序列收敛到不动点 {detail.get('fixed_value')}"
    else:
        note = "发散/观察未决——真墙标记或需扩展窗口"
    return {
        'ID': f"悖论_P-A_2_3_{sentence or 'custom'}",
        'LV': 'P-A' if verdict in ('resonance_band', 'liar_cycle',
                                   'annotated_pa') else 'P-B',
        'POS': f'第2层·递归修正自指·{sentence or "custom"}',
        'SRC': 'axiom' if verdict in ('resonance_band', 'liar_cycle',
                                      'annotated_pa') else 'runtime',
        'CT': f"A=自指句成立, ¬A=自指句不成立, 共存形式=修正序列{sentence or '自定义'}",
        'EF': '上卷第1层不可判定处（经典框架停住点）',
        'ST': '活跃',
        'AN': note,
    }


def run(inputs):
    """
    做什么：跑递归修正序列，把自指/不可判定诊断成可观察定态。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode')
    if mode not in ('iterate', 'sentence'):
        return {'verdict': 'input_pending', 'selfref_type': 'custom',
                'detail': {'reason': "mode 应为 'iterate'（自定义修正函数）"
                                     "或 'sentence'（内置自指句）"},
                'annotation': None,
                'boundary': '诚实：不给 mode 不硬判——先说明要观察哪类自指'}
    max_steps = inputs.get('max_steps', 100)
    tol = inputs.get('tol', 1e-9)

    # ── sentence 模式：内置自指句
    if mode == 'sentence':
        sentence = inputs.get('sentence')
        if sentence == 'liar':
            kind, meta = _observe(_liar_fn, False, max_steps, tol)
            # 说谎者必成周期 2（真/假翻转）
            period = meta.get('period')
            if kind == 'cycle' and period == 2:
                return {'verdict': 'liar_cycle', 'selfref_type': 'liar',
                        'detail': {'period': 2, 'pattern': [False, True],
                                   'trace': meta['trace'][:8],
                                   'stable': '振荡但稳定（共振带）'},
                        'annotation': _to_card('liar_cycle', 'liar', meta,
                                               'liar'),
                        'boundary': '说谎者 P↔¬P：每步翻转（自指悖论态）。'
                                    '引擎不判真值——只说修正序列在'
                                    '{假,真} 间稳定振荡（判振荡模式）。'
                                    '不违反哥德尔。'}
            return {'verdict': 'undetermined', 'selfref_type': 'liar',
                    'detail': meta, 'annotation': None,
                    'boundary': f'观察 {max_steps} 步未见周期 2——诚实未决'}
        if sentence == 'truth_teller':
            kind, meta = _observe(_truth_teller_fn, False, max_steps, tol)
            return {'verdict': 'fixed_point', 'selfref_type': 'truth_teller',
                    'detail': {'fixed_value': meta.get('fixed_value'),
                               'note': '每个初值都是不动点（P↔P 恒等修正）'
                                       '——不动点不唯一，无信息量自指',
                               'trace': meta['trace'][:4]},
                    'annotation': _to_card('fixed_point', 'truth_teller',
                                           meta, 'truth_teller'),
                    'boundary': '本句为真 P↔P：修正恒等，任意真值自洽。'
                                '稳定但不动点不唯一——需外部锚定才有信息，'
                                '引擎不替它选真值。'}
        if sentence == 'godel':
            # 哥德尔句无真值修正函数可跑（可证性谓词非真值函数）——
            # 诚实：不假装跑序列，直接注解 P-A + 明确边界
            return {'verdict': 'annotated_pa', 'selfref_type': 'godel',
                    'detail': {'note': 'G ↔ ¬可证(G)：算术编码自指，'
                                       '经典框架不可判定'},
                    'annotation': _to_card('annotated_pa', 'godel', {},
                                           'godel'),
                    'boundary': '哥德尔型自指：引擎立场=测度+注解+振荡观察，'
                                '不宣称判定（不推翻不完备定理）。'}
        return {'verdict': 'input_pending', 'selfref_type': 'custom',
                'detail': {'reason': f"sentence 应为 'liar'/'truth_teller'/"
                                     f"'godel'，得到 {sentence!r}"},
                'annotation': None,
                'boundary': '诚实：不支持该自指句预设，不硬跑'}

    # ── iterate 模式：自定义修正函数
    f = inputs.get('f')
    state0 = inputs.get('state0', False)
    if f is None:
        return {'verdict': 'input_pending', 'selfref_type': 'custom',
                'detail': {'reason': "mode='iterate' 需给 f(state) 修正函数"},
                'annotation': None,
                'boundary': '诚实：无修正函数不硬判'}
    try:
        kind, meta = _observe(f, state0, max_steps, tol)
    except Exception as e:
        return {'verdict': 'parse_error', 'selfref_type': 'custom',
                'detail': {'error': str(e)}, 'annotation': None,
                'boundary': f'修正函数执行出错（诚实拦截）：{e}'}

    if kind == 'fixed_point':
        return {'verdict': 'fixed_point', 'selfref_type': 'custom',
                'detail': {'reached_at': meta['reached_at'],
                           'fixed_value': meta['fixed_value'],
                           'trace': meta['trace'][:8]},
                'annotation': _to_card('fixed_point', 'custom', meta,
                                       'custom'),
                'boundary': '修正序列收敛到不动点——良性自指（可给结果）。'
                            '注意：收敛 ≠ 正确（收敛到不动点不等于该不动点'
                            '是唯一真值），白箱如上。'}
    if kind == 'cycle':
        period = meta['period']
        cycle = meta['cycle']
        if period == 2 and all(
                isinstance(s, bool) for s in cycle):
            return {'verdict': 'liar_cycle', 'selfref_type': 'custom',
                    'detail': {'period': 2, 'pattern': cycle,
                               'trace': meta['trace'][:8],
                               'stable': '振荡但稳定（共振带）'},
                    'annotation': _to_card('liar_cycle', 'custom', meta,
                                           'custom'),
                    'boundary': '每步翻转（周期 2）——说谎者核形态。'
                                '判振荡模式，不判真值。'}
        # 数值/多态周期 → 共振带收敛
        nums = [s for s in cycle if isinstance(s, (int, float))]
        rng = None
        if nums:
            rng = [min(nums), max(nums)]
        return {'verdict': 'resonance_band', 'selfref_type': 'custom',
                'detail': {'period': period, 'cycle': cycle,
                           'range': rng,
                           'stable': '振荡但稳定（共振带收敛）',
                           'trace': meta['trace'][:8]},
                'annotation': _to_card('resonance_band', 'custom', meta,
                                       'custom'),
                'boundary': '共振带收敛：修正序列进入稳定周期振荡——'
                            '不判真值，判振荡模式（周期/范围如上）。'}
    if kind == 'grow':
        return {'verdict': 'diverge', 'selfref_type': 'custom',
                'detail': {'note': '数值无界放大', 'trace': meta['trace'][:8]},
                'annotation': _to_card('diverge', 'custom', meta, 'custom'),
                'boundary': '发散：真墙（标记，不硬钻）。引擎不宣称'
                            '能判它——诚实报告发散。'}
    return {'verdict': 'undetermined', 'selfref_type': 'custom',
            'detail': {'steps': meta['steps'],
                       'note': f'{max_steps} 步内未见不动点/周期/发散——'
                               '可能还需更多步或真墙'},
            'annotation': None,
            'boundary': '观察窗口不足：undetermined 是合法输出（诚实），'
                        '不硬判发散/收敛。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('递归修正 × 自指检测构件 · 自测（第 2 层 2.3）')
    print('=' * 62)

    # 1) 说谎者：每步翻转 → liar_cycle（自指悖论态）
    r1 = run({'mode': 'sentence', 'sentence': 'liar'})
    assert r1['verdict'] == 'liar_cycle', r1
    assert r1['detail']['period'] == 2, r1
    print(f"✅ 说谎者 P↔¬P → {r1['verdict']}（周期 {r1['detail']['period']}，"
          f"振荡稳定）")
    print(f"   boundary: {r1['boundary']}")

    # 2) 本句为真：不动点（但不动点不唯一——诚实标注）
    r2 = run({'mode': 'sentence', 'sentence': 'truth_teller'})
    assert r2['verdict'] == 'fixed_point', r2
    assert '不唯一' in r2['detail']['note'], r2
    print(f"✅ 本句为真 P↔P → {r2['verdict']}（{r2['detail']['note']}）")

    # 3) 哥德尔句：注解 P-A，不假装跑序列
    r3 = run({'mode': 'sentence', 'sentence': 'godel'})
    assert r3['verdict'] == 'annotated_pa', r3
    assert r3['annotation']['LV'] == 'P-A', r3
    print(f"✅ 哥德尔句 → {r3['verdict']}（P-A 卡，不宣称判定）")

    # 4) 自定义：压缩修正 → 不动点（良性自指）
    r4 = run({'mode': 'iterate', 'f': lambda x: x / 2, 'state0': 1.0})
    assert r4['verdict'] == 'fixed_point', r4
    print(f"✅ 自定义 f(x)=x/2 → {r4['verdict']}（定点 "
          f"{r4['detail']['fixed_value']}）")

    # 5) 自定义：数值共振带（周期 2 数值振荡）
    r5 = run({'mode': 'iterate', 'f': lambda x: 1 - x, 'state0': 0.2})
    assert r5['verdict'] == 'resonance_band', r5
    assert r5['detail']['period'] == 2, r5
    print(f"✅ f(x)=1-x → {r5['verdict']}（周期 {r5['detail']['period']}，"
          f"范围 {r5['detail']['range']}）")

    # 6) 自定义：发散 → 真墙
    r6 = run({'mode': 'iterate', 'f': lambda x: 2 * x, 'state0': 1.0,
              'max_steps': 200})
    assert r6['verdict'] == 'diverge', r6
    print(f"✅ f(x)=2x → {r6['verdict']}（真墙标记，不硬钻）")

    # 7) 边界：缺 mode / 坏 sentence → 诚实拦截
    r7 = run({})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'mode': 'sentence', 'sentence': 'not_a_sentence'})
    assert r8['verdict'] == 'input_pending', r8
    print('✅ 缺 mode / 未知预设 → input_pending（不硬判）')

    print('=' * 62)
    print('递归修正 × 自指检测构件自测：全部通过 ✅')
    print('=' * 62)
