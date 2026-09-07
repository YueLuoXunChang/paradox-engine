# -*- coding: utf-8 -*-
"""
wall_pipeline.py — 撞墙处理管线 A 编排构件（第 2 层，组合件）
================================================================
概念来源：落落逻辑体系原创（构件来源见各子构件 docstring）
详规：《第2层悖论创生详规》§七（管线 A）+《机制组合方案》
§三 A（测墙→钻墙→看墙→换位→创生）
组合：本文件把 2.1(μ)/2.2(注解)/2.3(递归修正自指)/2.4(边界悖论)/
      2.5(全程自反旁路)/2.6(对位创生) 编成一条可执行管线——
      输出**五选一诊断**（可判/良性自指/共振带自指/发散真墙/可创生）。

本构件做什么（一句话）：
    输入一个"疑似墙"（自指/矛盾/不可判定/冲突），跑完管线各步，
    输出五选一诊断 + 注解卡 + 各步白箱——把"墙"从终点变成状态机的一格。

管线（详规 §七）：
    输入 → [2.1 测墙] μ 测度（mu2 自指直判 μ=1）
         → [2.2 注解墙] 悖论注解卡
         → [2.3 钻墙] 递归修正×自指检测：观测定态
              ├── 不动点收敛 → 良性自指
              ├── 共振带/每步翻转 → 共振带自指
              └── 发散 → 真墙
         → [2.4 看墙] 边界悖论判定（张力/可撤性/重生）
         → [2.5 旁路] 全程自反观察（系统级，演示为附加观察）
         → [2.6 创生] 对位创生第三态（可选——对立文本时给候选）
    输出：五选一诊断 verdict + annotation + steps 白箱

诚实边界：
    - 五选一诊断是**诊断**不是判决（只诊断不决策）；
    - "共振带自指" ≠ 判定了真值——判振荡模式；
    - 管线能走多远依赖输入给了什么（缺文本走不了创生）——诚实标注每步
      状态（run/pending/skip）；
    - 不宣称绕停机/哥德尔——真墙也是合法输出。
"""

PORTS = {
    'in': {'wall': 'str?', 'thesis': 'str?', 'antithesis': 'str?',
           'events': 'list?'},
    'out': {'verdict': 'str', 'diagnosis': 'dict', 'annotation': 'dict',
            'steps': 'list', 'boundary': 'str'},
}

# 子构件（双模式导入：pip 安装走 engine. 前缀；直接运行走平级）
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from engine.mechanisms.paradox_measure import run as measure_run  # noqa: E402,F401
    from engine.mechanisms.paradox_annotate import run as annotate_run  # noqa: E402,F401
    from engine.mechanisms.selfref_fixpoint import run as fixpoint_run  # noqa: E402,F401
    from engine.mechanisms.boundary_paradox import run as boundary_run  # noqa: E402,F401
    from engine.mechanisms.observer_bypass import run as bypass_run  # noqa: E402,F401
    from engine.mechanisms.counterpoint_gen import run as counterpoint_run  # noqa: E402,F401
except ImportError:
    from paradox_measure import run as measure_run  # noqa: E402,F401
    from paradox_annotate import run as annotate_run  # noqa: E402,F401
    from selfref_fixpoint import run as fixpoint_run  # noqa: E402,F401
    from boundary_paradox import run as boundary_run  # noqa: E402,F401
    from observer_bypass import run as bypass_run  # noqa: E402,F401
    from counterpoint_gen import run as counterpoint_run  # noqa: E402,F401


def run(inputs):
    """
    做什么：跑撞墙处理管线 A，输出五选一诊断。

    输入:
        wall: str——疑似墙描述（如 '这句话是假的'/'G 不可证'）
        thesis/antithesis: str——对立立场（可选；给则走 2.6 创生）
        events: list——主线程事件（可选；给则走 2.5 旁路演示）

    返回:
        dict
    """
    wall = inputs.get('wall')
    thesis = inputs.get('thesis')
    antithesis = inputs.get('antithesis')
    events = inputs.get('events')

    if not wall and not (thesis and antithesis):
        return {'verdict': 'input_pending', 'diagnosis': None,
                'annotation': None, 'steps': [],
                'boundary': '需给 wall（疑似墙描述）或 thesis+antithesis'
                            '（对立立场）——诚实：无线索不硬判'}

    steps = []

    # ── 2.1 测墙：μ 测度（自指句走 mu2 直判 μ=1）
    s1 = measure_run({'mode': 'mu2' if wall else 'mu1',
                      'wA': 5, 'wNotA': 5})
    steps.append({'step': '2.1 测墙', 'status': 'run',
                  'detail': {'mu': s1.get('mu'),
                             'branch': s1.get('mode', 'mu2')}})

    # ── 2.2 注解墙：给悖论对象一张卡
    is_selfref = wall is not None and any(
        k in wall for k in ('这句话', '本句', '自己', '不可证', '假'))
    src = 'axiom' if is_selfref else 'runtime'
    s2 = annotate_run({'paradox': {'A': wall or thesis,
                                   'notA': f'¬({antithesis or wall})',
                                   'pos': '第2层·撞墙管线入口',
                                   'src': src,
                                   'effect': '经典层上卷点'},
                       'source': src, 'impact': 'global',
                       'eliminable': False})
    annotation = s2.get('annotation', {})
    steps.append({'step': '2.2 注解墙', 'status': 'run',
                  'detail': {'grade': s2.get('grade'),
                             'ID': annotation.get('ID')}})

    # ── 2.3 钻墙：递归修正×自指检测
    if wall:
        sentence = None
        for key, val in (('godel', '不可证'), ('liar', '这句话是假的'),
                         ('liar', '本句为假'), ('truth_teller', '本句为真'),
                         ('truth_teller', '这句话是真的')):
            if val in wall:
                sentence = key
                break
        s3 = fixpoint_run({'mode': 'sentence', 'sentence': sentence}
                          if sentence else
                          {'mode': 'iterate',
                           'f': lambda x: not x if isinstance(x, bool)
                           else 1 - x, 'state0': False})
        fv = s3.get('verdict')
        steps.append({'step': '2.3 钻墙', 'status': 'run',
                      'detail': {'verdict': fv,
                                 'period': s3.get('detail', {}).get(
                                     'period')}})
    else:
        fv = 'skip（无自指文本）'
        steps.append({'step': '2.3 钻墙', 'status': 'skip',
                      'detail': {'verdict': 'skip——wall 未给'}})

    # ── 2.4 看墙：边界悖论判定
    s4 = boundary_run({'wall_name': wall or f'{thesis} vs {antithesis}',
                       'inside': wall or thesis,
                       'outside': antithesis or '不可判定',
                       'recursive_layer': 0})
    steps.append({'step': '2.4 看墙', 'status': 'run',
                  'detail': {'tension': s4.get('tension'),
                             'advice_count': len(s4.get('advice', []))}})

    # ── 2.5 旁路：全程自反观察（有 events 才真正跑，否则演示降级）
    if events:
        s5 = bypass_run({'main_events': events})
        steps.append({'step': '2.5 旁路', 'status': 'run',
                      'detail': {'main_ran': s5.get('main_ran'),
                                 'findings': len(s5.get('findings', []))}})
    else:
        steps.append({'step': '2.5 旁路', 'status': 'skip',
                      'detail': {'reason': 'events 未给（可选步）'}})

    # ── 2.6 创生：对位创生第三态（有对立文本才跑）
    if thesis and antithesis:
        s6 = counterpoint_run({'thesis': thesis, 'antithesis': antithesis})
        steps.append({'step': '2.6 创生', 'status': 'run',
                      'detail': {'coupling': s6.get('coupling'),
                                 'third_state': (s6.get('third_state') or {})
                                 .get('label')}})
    else:
        steps.append({'step': '2.6 创生', 'status': 'skip',
                      'detail': {'reason': 'thesis/antithesis 未给（可选步）'}})

    # ── 五选一诊断
    if fv in ('fixed_point',):
        verdict = 'benign_selfref'      # 良性自指（可给结果）
        label = '良性自指——修正序列收敛到不动点，可给结果'
    elif fv in ('resonance_band', 'liar_cycle'):
        verdict = 'resonance_selfref'   # 共振带自指（振荡稳定）
        label = '共振带自指——修正序列稳定振荡（不判真值，判振荡模式）'
    elif fv == 'diverge':
        verdict = 'divergent_wall'      # 发散真墙
        label = '发散真墙——引擎诚实标记，不硬钻'
    elif fv == 'annotated_pa':
        verdict = 'structural_wall'     # 结构性墙（哥德尔型）
        label = '结构性墙（哥德尔型）——P-A 注解，不宣称判定'
    elif thesis and antithesis:
        verdict = 'creatable'           # 可创生
        label = '可创生——对立交汇可产生第三态候选（供人评估）'
    else:
        verdict = 'decidable_elsewhere'  # 引擎给不出更细——诚实
        label = '未落入自指谱系——可交经典层/人工判（诚实：不硬套）'

    diagnosis = {'label': label, 'mu': steps[0]['detail'].get('mu'),
                 'grade': annotation.get('LV'),
                 'drill': fv, 'tension': steps[3]['detail'].get('tension')}

    return {'verdict': verdict, 'diagnosis': diagnosis,
            'annotation': annotation, 'steps': steps,
            'boundary': '五选一是诊断不是判决（只诊断不决策）。共振带自指'
                        '≠判真值。真墙/结构性墙是合法输出（不宣称绕停机/'
                        '哥德尔）。可选步（2.5/2.6）缺输入则 skip——诚实'
                        '标注，不假装跑过。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('撞墙处理管线 A · 自测（第 2 层编排）')
    print('=' * 62)

    # 1) 说谎者 → 共振带自指
    r1 = run({'wall': '这句话是假的'})
    assert r1['verdict'] == 'resonance_selfref', r1
    assert r1['annotation'].get('LV') == 'P-A', r1
    assert len(r1['steps']) == 6, r1
    print(f"✅ 说谎者句 → {r1['verdict']}（{r1['diagnosis']['label']}）")
    print(f"   注解卡 LV={r1['annotation'].get('LV')}，"
          f"μ={r1['diagnosis'].get('mu')}")

    # 2) 哥德尔句 → 结构性墙
    r2 = run({'wall': '本句不可证'})
    assert r2['verdict'] == 'structural_wall', r2
    print(f"✅ 哥德尔句 → {r2['verdict']}（P-A 注解，不宣称判定）")

    # 3) 对立立场 → 可创生
    r3 = run({'thesis': '要快', 'antithesis': '要稳'})
    assert r3['verdict'] == 'creatable', r3
    assert r3['steps'][5]['status'] == 'run', r3
    print(f"✅ 要快 vs 要稳 → {r3['verdict']}（第三态候选已生成）")

    # 4) 带事件 → 旁路也跑
    r4 = run({'wall': '这句话是假的',
              'events': ['建模', '发现矛盾', '继续']})
    assert r4['steps'][4]['status'] == 'run', r4
    print(f"✅ 带主线程事件 → 旁路步 status=run")

    # 5) 边界：无线索
    r5 = run({})
    assert r5['verdict'] == 'input_pending', r5
    print('✅ 无线索 → input_pending（诚实拦截）')

    print('=' * 62)
    print('撞墙处理管线 A 自测：全部通过 ✅')
    print('=' * 62)
