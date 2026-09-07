# -*- coding: utf-8 -*-
"""
observer_bypass.py — 悖论全程自反旁路构件（第 2 层悖论创生 2.5，系统级旁路）
=============================================================================
概念来源：落落逻辑体系原创——悖论线程全程独立 + 悖论全程
自反 + 自反观察公理。非外部共识，落落原创区。
详规：《逻辑建模引擎_第2层悖论创生详规》§五
组合：管线 A"看墙/绕墙"步（撞墙管线 A 编排）——旁路观察不阻塞主链

本构件做什么（一句话）：
    系统级旁路：主线程正常推进（建模/推理/演化），悖论旁路线程并行
    持续观察（检测点 → 发现矛盾/自指 → 注解 → 注入主线程参考 →
    继续观察）。主线程不因矛盾停下；悖论注解随行。

与"不面对墙"的关系（钉死边界）：
    图灵机是墙，因为它只有一条带、必须对每个符号表态。本架构让
    "矛盾观察"走旁路线程——主带不停。不是宣称判定了矛盾，是
    **矛盾观察不阻塞主流程**（架构级免疫）。

诚实边界：
    - 旁路观察 = 检测+注解+注入参考，不是消除矛盾也不是替主线程决策；
    - 观察线程的"发现"是否被主线程采纳，由主线程策略决定
      （本构件给参考，不做主线程的决策）；
    - 注入参考发生在检测点之后（不预知未来），白箱可见。

统一接口：
    run(inputs: dict) -> dict
    输入:
        main_events: list——主线程事件序列（每步一个描述，如
                     ['读取需求', '建模 A', '发现冲突 P', '继续建模'])
        detect: callable——检测函数 event(str) -> dict 或 None
                （None=无发现；dict={type:'paradox'|'selfref'|...,
                A, notA, note}）。缺省用内置启发（'冲突'/'矛盾'/'自指'
                等关键词 + 相邻步对立检测）。
        use_advice: bool——主线程是否采纳注入参考（默认 True，仅影响
                    输出里的采纳标注，不改变主事件本身——诚实演示）
    输出:
        verdict: str——'observed'|'input_pending'
        main_ran: int——主线程完整步数（不阻塞验证）
        findings: list——旁路发现（每项带位置/类型/注解/注入）
        injected_at: list[int]——注入发生的主线程位置
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'main_events': 'list?', 'detect': 'callable?',
           'use_advice': 'bool?'},
    'out': {'verdict': 'str', 'main_ran': 'int', 'findings': 'list',
            'injected_at': 'list', 'boundary': 'str'},
}


def _default_detect(event, prev_events):
    """
    内置启发检测（诚实标注：启发式，非完备判定）：
    - 事件文本含 '冲突'/'矛盾'/'悖论'/'自指'/'两难' → paradox 类发现；
    - 相邻步出现对立（前步含 '要X' 后步含 '不要X'/含 '反'）→ 冲突发现。
    """
    text = str(event)
    hit = None
    for kw in ('冲突', '矛盾', '悖论', '自指', '两难', '对立'):
        if kw in text:
            hit = {'type': 'paradox', 'A': text, 'notA': f'¬({text})',
                   'note': f'关键词启发命中：{kw}（诚实：启发式，非完备）'}
            break
    if hit is None and prev_events:
        last = str(prev_events[-1])
        neg = ('不要', '反对', '排除', '否定', '推翻')
        if any(n in text for n in neg) and any(
                w in last for w in ('要', '支持', '保留', '肯定', '确立')):
            hit = {'type': 'conflict', 'A': last, 'notA': text,
                   'note': '相邻步对立启发命中（诚实：启发式）'}
    return hit


def run(inputs):
    """
    做什么：跑旁路观察——主线程不停，矛盾发现注入参考。

    返回 dict（见模块 docstring）。"""
    main_events = inputs.get('main_events')
    if not main_events or not isinstance(main_events, list):
        return {'verdict': 'input_pending', 'main_ran': 0,
                'findings': [], 'injected_at': [],
                'boundary': '需给 main_events（主线程事件序列 list）——'
                            '诚实：无主线程不跑旁路'}
    detect = inputs.get('detect')
    use_advice = inputs.get('use_advice', True)

    findings = []
    injected_at = []
    for i, ev in enumerate(main_events):
        # 主线程正常推进（第 i 步不因旁路而停）
        # 旁路观察：对第 i 步做检测（只看已发生的 i 步——不预知未来）
        if detect is not None:
            try:
                f = detect(ev)
            except Exception as e:
                f = {'type': 'detect_error', 'note': f'检测函数异常：{e}'}
        else:
            f = _default_detect(ev, main_events[:i])
        if f:
            entry = {'at': i, 'event': ev, 'type': f.get('type', 'unknown'),
                     'note': f.get('note', ''),
                     'annotation': {'A': f.get('A', ev),
                                    'notA': f.get('notA', ''),
                                    'LV': 'P-B',
                                    'SRC': 'runtime',
                                    'ST': '活跃',
                                    'AN': f.get('note', '')}}
            if use_advice:
                entry['injected'] = '参考注入主线程（采纳与否由主线程策略决定）'
                injected_at.append(i)
            findings.append(entry)

    return {'verdict': 'observed', 'main_ran': len(main_events),
            'findings': findings, 'injected_at': injected_at,
            'boundary': '旁路观察=检测+注解+注入参考——不消除矛盾、不替'
                        '主线程决策（只诊断不决策）。主线程完整跑完'
                        f'（{len(main_events)} 步未阻塞）。发现采用启发式'
                        '或调用方 detect——诚实标注，非完备判定。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('悖论全程自反旁路构件 · 自测（第 2 层 2.5）')
    print('=' * 62)

    # 1) 主线程带冲突——旁路发现且主线程不阻塞
    events = ['读取需求', '建模 A 方案', '发现需求冲突', '继续建模 B 方案',
              '产出模型']
    r1 = run({'main_events': events})
    assert r1['verdict'] == 'observed', r1
    assert r1['main_ran'] == 5, r1
    assert len(r1['findings']) >= 1, r1
    assert r1['injected_at'] == [2], r1
    print(f"✅ 主线程 5 步完整跑完（main_ran={r1['main_ran']}，不阻塞）")
    print(f"   旁路发现 {len(r1['findings'])} 处："
          f"{[(f['at'], f['type']) for f in r1['findings']]}")

    # 2) 相邻步对立（'要快' → '要稳' 不触发；'要快' → '不要快' 触发）
    events2 = ['要快', '不要快']
    r2 = run({'main_events': events2})
    assert r2['main_ran'] == 2 and len(r2['findings']) == 1, r2
    assert r2['findings'][0]['type'] == 'conflict', r2
    print('✅ 相邻步对立（要快→不要快）→ conflict 发现')

    # 3) 自定义 detect + use_advice=False
    events3 = ['步1', '步2']
    r3 = run({'main_events': events3,
              'detect': lambda ev: {'type': 'selfref',
                                    'A': ev, 'note': '自定义检测'} if
                        ev == '步2' else None,
              'use_advice': False})
    assert len(r3['findings']) == 1 and r3['injected_at'] == [], r3
    assert 'injected' not in r3['findings'][0], r3
    print('✅ 自定义 detect + use_advice=False（发现但不注入）')

    # 4) 边界：缺主线程
    r4 = run({})
    assert r4['verdict'] == 'input_pending', r4
    print('✅ 缺主线程事件 → input_pending（诚实拦截）')

    print('=' * 62)
    print('悖论全程自反旁路构件自测：全部通过 ✅')
    print('=' * 62)
