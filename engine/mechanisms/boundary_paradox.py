# -*- coding: utf-8 -*-
"""
boundary_paradox.py — 边界悖论判定构件（第 2 层悖论创生 2.4，看墙件）
=========================================================================
概念来源：落落逻辑体系原创——边界悖论公理（划设即撤销、
边界自悖、边界递归 B(B(S))）。非外部共识，落落原创区。
详规：《逻辑建模引擎_第2层悖论创生详规》§四
组合：管线 A"看墙"步（撞墙管线 A 编排）

本构件做什么（一句话）：
    把"可计算/可判定/领域"的墙当作**边界对象**诊断——墙存在吗？
    强度？张力？划设是否预设了可撤销？给边界操作建议（诊断），
    不宣称墙不存在。

与"绕图灵"的关系（钉死边界）：
    "可判定性之墙" = 边界。边界悖论公理说"划设即撤销、无不可撤销的墙"，
    但这不是"图灵机可判定了"——是：把墙当边界对象诊断（张力/可撤性/
    重生路径），不宣称墙不存在。边界重生 = 换框架（如升维到 oracle 层），
    每层有自己的墙（哥德尔复现）。

诚实边界：
    - 输出边界建议是**诊断**（划设/维护/检测/撤销/重生），不是执行动作
      （只诊断不决策）；
    - "可撤销"指框架层可换（升维/换公理），不是"图灵可判"；
    - 张力量化是工程约定（内外差异的度量），标"工程约定"不冒充定理。

统一接口：
    run(inputs: dict) -> dict
    输入:
        wall_name: str——墙的名字（如 '停机问题之墙'/'说谎者之墙'）
        domain: str——墙所在域描述（默认 ''）
        inside/outside: str——墙内/墙外描述（决定张力：差异越大张力越大）
        recursive_layer: int——递归层（默认 0；>0 表示这是第几层的墙，
                            每层有自己的墙）
        mode: str——'diagnose'（默认，看墙）| 'b_recurse'（边界递归演示
                    B(B(S))）
    输出:
        verdict: str——'wall_exists'|'no_wall'|'input_pending'
        tension: float——边界张力（0~1，工程约定）
        self_undermining: bool——划设即撤销检查
        removable: bool——框架层可撤性
        advice: list[str]——边界操作建议（诊断）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'wall_name': 'str?', 'domain': 'str?', 'inside': 'str?',
           'outside': 'str?', 'recursive_layer': 'int?', 'mode': 'str?'},
    'out': {'verdict': 'str', 'tension': 'float', 'self_undermining': 'bool',
            'removable': 'bool', 'advice': 'list', 'boundary': 'str'},
}


def _tension(inside, outside):
    """
    边界张力（工程约定，0~1）：内外描述差异越大，跨越压力越大。
    度量：共有词占比的补（1 - |common|/|union|）——完全不同 → 接近 1，
    几乎同语 → 接近 0。标工程约定，不冒充定理。
    """
    if not inside or not outside:
        return 0.5  # 信息不足取中值（诚实标注在 boundary）
    a = set(str(inside).replace('，', ' ').replace(',', ' ').split())
    b = set(str(outside).replace('，', ' ').replace(',', ' ').split())
    if not a or not b:
        return 0.5
    union = a | b
    if not union:
        return 0.5
    return round(1 - len(a & b) / len(union), 3)


def run(inputs):
    """
    做什么：诊断边界（墙）的状态并给边界操作建议（只诊断不决策）。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'diagnose')
    if mode not in ('diagnose', 'b_recurse'):
        return {'verdict': 'input_pending', 'tension': None,
                'self_undermining': None, 'removable': None, 'advice': [],
                'boundary': f"mode 应为 'diagnose'/'b_recurse'，得到 {mode!r}"
                            '（诚实：不硬跑未知模式）'}

    # ── 边界递归演示 B(B(S))：给一条边界，递归应用"边界"本身
    if mode == 'b_recurse':
        wall = inputs.get('wall_name') or '边界'
        return {'verdict': 'b_recurse', 'tension': None,
                'self_undermining': True, 'removable': True,
                'advice': [f'B(S)={wall}（划设）',
                           f'B(B(S))：{wall} 的边界也是边界（自悖——'
                           '划设边界的动作本身在边界内/外？）',
                           '每层递归都有自己的墙——不宣称最高层无墙'],
                'boundary': '边界递归 B(B(S)) 演示：边界划设动作本身'
                            '落入边界问题——引擎只标注递归结构，不宣称'
                            '某一层是"最终边界"。'}

    # ── 诊断模式：看墙
    wall_name = inputs.get('wall_name')
    if not wall_name:
        return {'verdict': 'input_pending', 'tension': None,
                'self_undermining': None, 'removable': None, 'advice': [],
                'boundary': '需给 wall_name（墙的名字）——诚实：无名之墙'
                            '不硬诊'}
    inside = inputs.get('inside') or ''
    outside = inputs.get('outside') or ''
    layer = inputs.get('recursive_layer', 0) or 0

    tension = _tension(inside, outside)
    # 划设即撤销检查：墙由"划设"产生 → 预设了可撤销（边界悖论公理）
    self_undermining = True  # 公理：所有划设都预设可撤销
    # 框架层可撤性：结构性墙（停机/哥德尔）框架内不可撤，但框架可换
    removable = True  # 换框架（升维）总是可能的——每层有自己的墙

    advice = [
        f'墙存在：{wall_name}（递归层 {layer}）——先承认它，不假装没有',
        f'张力 ≈ {tension}（内外差异的工程度量，非定理）'
        + ('：内外差异大，跨越压力高' if tension > 0.6
           else '：内外接近，张力不高'),
        '划设即撤销检查：该墙由划设产生 → 预设可撤销（框架层，非图灵层）',
        f'重生路径：换框架/升维（层 {layer} → 层 {layer + 1}）——'
        '每层有自己的墙（哥德尔复现），引擎不宣称顶层无墙',
    ]
    if tension < 0.3:
        advice.append('建议：维护（墙内墙外接近，先别急着撤）')
    elif tension > 0.7:
        advice.append('建议：检测/重生（张力过高——检查是否该换框架）')
    else:
        advice.append('建议：维护 + 检测（张力中等，保持观察）')

    return {'verdict': 'wall_exists', 'tension': tension,
            'self_undermining': self_undermining,
            'removable': removable, 'advice': advice,
            'boundary': '诊断输出是建议不是动作（只诊断不决策）。'
                        '"可撤销"= 框架层可换（升维/换公理），'
                        '不是"图灵机可判定了"——不宣称墙不存在，'
                        '不宣称绕停机/哥德尔。张力为工程约定。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('边界悖论判定构件 · 自测（第 2 层 2.4）')
    print('=' * 62)

    # 1) 停机问题之墙：高张力结构性墙
    r1 = run({'wall_name': '停机问题之墙',
              'inside': '可判定 可计算 有限步',
              'outside': '不可判定 停机 无限', 'recursive_layer': 0})
    assert r1['verdict'] == 'wall_exists', r1
    assert r1['self_undermining'] is True, r1
    assert r1['removable'] is True, r1
    assert 0 <= r1['tension'] <= 1, r1
    assert len(r1['advice']) >= 4, r1
    print(f"✅ 停机问题之墙 → {r1['verdict']}，张力 {r1['tension']}")
    print(f"   advice[0]: {r1['advice'][0]}")
    print(f"   boundary: {r1['boundary']}")

    # 2) 低张力墙（内外接近）
    r2 = run({'wall_name': '部门墙', 'inside': '研发 产品',
              'outside': '产品 研发'})
    assert r2['verdict'] == 'wall_exists' and r2['tension'] < 0.3, r2
    print(f"✅ 部门墙（内外接近）→ 张力 {r2['tension']}（低）")

    # 3) 边界递归 B(B(S))
    r3 = run({'mode': 'b_recurse', 'wall_name': '说谎者之墙'})
    assert r3['verdict'] == 'b_recurse', r3
    assert len(r3['advice']) == 3, r3
    print('✅ 边界递归 B(B(S)) → 自悖标注（划设动作本身在边界内/外？）')

    # 4) 边界：缺墙名 / 坏 mode
    r4 = run({})
    assert r4['verdict'] == 'input_pending', r4
    r5 = run({'mode': 'xx'})
    assert r5['verdict'] == 'input_pending', r5
    print('✅ 缺墙名/坏 mode → input_pending（诚实拦截）')

    print('=' * 62)
    print('边界悖论判定构件自测：全部通过 ✅')
    print('=' * 62)
