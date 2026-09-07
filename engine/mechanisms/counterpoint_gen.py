# -*- coding: utf-8 -*-
"""
counterpoint_gen.py — 对位创生第三态构件（第 2 层悖论创生 2.6，建模发动机）
=============================================================================
概念来源：落落逻辑体系原创——对位创生公理（交汇产生第三态）
+ 双悖论闭环（双悖论驱动）+ 汇入镜像层剥（边界
缝隙汇入）。非外部共识，落落原创区。
详规：《逻辑建模引擎_第2层悖论创生详规》§六
组合：管线 A"创生"步（40 组合方案 §三 A，可选/建模用）

本构件做什么（一句话）：
    对立对 (A, ¬A) 交汇——不判谁对、不消除——产生第三态 C：
    不可从 A 或 ¬A 单维推导的新结构候选 + 生成依据（白箱）。

第三态类型判定（41 §6.2）：
    ├── 同向耦合 → 快速收敛（"两全"）
    ├── 反向耦合 → 振荡 → 共振带中产生新意义
    └── 交叉耦合 → 部分收敛 + 部分振荡

诚实边界：
    - 第三态是"候选 + 依据"，不是"正确答案"——供人参考，只诊断不决策；
    - 引擎无法凭空创造语义新结构——第三态候选 = 结构运算（合并特征/
      换层视角/取互补），语义价值由使用者评估（不自夸"发明"）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        thesis: str——立场 A（如 '要快'）
        antithesis: str——立场 ¬A（如 '要稳'）
        coupling: str——'same'|'reverse'|'cross'（同向/反向/交叉耦合，
                       缺省 auto 探测）
        dimensions: list[str]——交汇维度名（用于结构化第三态，可省）
    输出:
        verdict: str——'third_state'|'input_pending'
        coupling: str——判定/给定的耦合类型
        third_state: dict——{label, basis, type_note, convergence}
        derivation: list[str]——生成依据（白箱）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'thesis': 'str?', 'antithesis': 'str?', 'coupling': 'str?',
           'dimensions': 'list?'},
    'out': {'verdict': 'str', 'coupling': 'str', 'third_state': 'dict',
            'derivation': 'list', 'boundary': 'str'},
}

_VALID_COUPLING = {'same', 'reverse', 'cross'}


def _probe_coupling(thesis, antithesis):
    """
    耦合类型自动探测（工程约定）：
    立场词共有成分高（同一对象不同侧重）→ 同向（可两全）；
    立场互为否定词（快 vs 慢 / 有 vs 无 / 大 vs 小 同根反义）→ 反向（振荡）；
    立场来自不同维度域（快[时间] vs 便宜[成本]）→ 交叉（部分收敛）。
    """
    negation_pairs = [('快', '慢'), ('快', '稳'), ('大', '小'), ('有', '无'),
                      ('高', '低'), ('多', '少'), ('强', '弱'), ('进', '退'),
                      ('新', '旧'), ('自由', '秩序'), ('效率', '公平')]
    t, a = thesis.strip(), antithesis.strip()
    for x, y in negation_pairs:
        if (x in t and y in a) or (y in t and x in a):
            return 'reverse'
    # 同向：两立场不是反义（缺省启发：都正向、无互否词）
    return 'cross'


def _build_third_state(thesis, antithesis, coupling, dimensions):
    """
    结构运算生成第三态候选（白箱：给出依据，不冒充语义发明）。

    三种耦合 → 三种生成策略：
      same    → 合并特征（两全候选：取双方共同目标维度）
      reverse → 换层/分域（振荡中找新意义：把对立放到不同层/域共存）
      cross   → 交汇桥（部分收敛：在交叉点上造"桥结构"候选）
    """
    dims = dimensions or ['目标']
    derivation = []
    if coupling == 'same':
        label = f"{thesis}与{antithesis}的统一态候选"
        basis = (f"同向耦合：'{thesis}'与'{antithesis}'不互斥，"
                 f"可合并为同一目标的两面")
        convergence = '快速收敛（两全）'
        derivation = [f'① 立场 A：{thesis}', f'② 立场 ¬A：{antithesis}',
                      f'③ 同向耦合 → 合并特征（维度：{"、".join(dims)}）',
                      '④ 候选 = 双方共同目标的结构化表达（供人评估）']
    elif coupling == 'reverse':
        label = f"{thesis}×{antithesis}的分域共生态候选"
        basis = (f"反向耦合：'{thesis}'与'{antithesis}'直接对立，"
                 f"振荡（共振带）——把对立放到不同层/域可共存")
        convergence = '振荡 → 共振带中产生新意义'
        derivation = [f'① 立场 A：{thesis}', f'② 立场 ¬A：{antithesis}',
                      '③ 反向耦合 → 每层选边会振荡',
                      f'④ 候选 = 分域共生（维度分层：{"、".join(dims)}'
                      '各取所宜）——共振带本身是新意义来源']
    else:  # cross
        label = f"{thesis}↔{antithesis}的交汇桥候选"
        basis = (f"交叉耦合：'{thesis}'与'{antithesis}'来自不同维度域，"
                 f"部分收敛+部分振荡——在交点上造桥")
        convergence = '部分收敛 + 部分振荡'
        derivation = [f'① 立场 A：{thesis}', f'② 立场 ¬A：{antithesis}',
                      '③ 交叉耦合 → 各维度独立判，冲突点造桥',
                      f'④ 候选 = 桥结构（维度：{"、".join(dims)}——'
                      '各自成立域分开，交汇点给新连接）']
    return {'label': label, 'basis': basis,
            'type_note': convergence, 'derivation': derivation}


def run(inputs):
    """
    做什么：对立交汇 → 第三态候选（生成依据白箱，只诊断不决策）。

    返回 dict（见模块 docstring）。"""
    thesis = inputs.get('thesis')
    antithesis = inputs.get('antithesis')
    if not thesis or not antithesis:
        return {'verdict': 'input_pending', 'coupling': None,
                'third_state': None, 'derivation': [],
                'boundary': '需给 thesis（立场 A）与 antithesis（立场 ¬A）'
                            '——诚实：缺一方不硬造第三态'}
    coupling = inputs.get('coupling')
    if coupling is None:
        coupling = _probe_coupling(thesis, antithesis)
    if coupling not in _VALID_COUPLING:
        return {'verdict': 'input_pending', 'coupling': None,
                'third_state': None, 'derivation': [],
                'boundary': f"coupling 应为 same/reverse/cross，得到 "
                            f"{coupling!r}（诚实拦截）"}
    dimensions = inputs.get('dimensions') or []
    third = _build_third_state(thesis, antithesis, coupling, dimensions)
    return {'verdict': 'third_state', 'coupling': coupling,
            'third_state': {'label': third['label'],
                            'basis': third['basis'],
                            'type_note': third['type_note']},
            'derivation': third['derivation'],
            'boundary': '第三态是候选+依据，不是正确答案——供人参考，'
                        '只诊断不决策。引擎给结构运算候选，语义价值由'
                        '使用者评估（不冒充发明）。矛盾仍在——创生是'
                        '给它出口，不是消灭它。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('对位创生第三态构件 · 自测（第 2 层 2.6）')
    print('=' * 62)

    # 1) 反向耦合（自动探测）：要快 vs 要稳 → 分域共生态
    r1 = run({'thesis': '要快', 'antithesis': '要稳'})
    assert r1['verdict'] == 'third_state', r1
    assert r1['coupling'] == 'reverse', r1
    assert r1['third_state']['label'], r1
    assert len(r1['derivation']) == 4, r1
    print(f"✅ 要快 vs 要稳 → 自动判 coupling={r1['coupling']}")
    print(f"   第三态候选：{r1['third_state']['label']}")
    print(f"   类型：{r1['third_state']['type_note']}")

    # 2) 自由 vs 秩序（反义对，41 走查例）→ 反向
    r2 = run({'thesis': '自由', 'antithesis': '秩序'})
    assert r2['coupling'] == 'reverse', r2
    print(f"✅ 自由 vs 秩序 → coupling={r2['coupling']}（共振带产生新意义）")

    # 3) 显式 same：要快 vs 要省时（同向）→ 两全
    r3 = run({'thesis': '要快', 'antithesis': '要省时',
              'coupling': 'same', 'dimensions': ['时间']})
    assert r3['coupling'] == 'same', r3
    assert '快速收敛' in r3['third_state']['type_note'], r3
    print(f"✅ 要快 vs 要省时（显式 same）→ {r3['third_state']['type_note']}")

    # 4) 交叉耦合：要快[时间] vs 要便宜[成本]
    r4 = run({'thesis': '要快', 'antithesis': '要便宜',
              'dimensions': ['时间', '成本']})
    assert r4['coupling'] == 'cross', r4
    assert '部分收敛' in r4['third_state']['type_note'], r4
    print(f"✅ 要快 vs 要便宜（跨维度）→ 自动判 coupling={r4['coupling']}")

    # 5) 边界：缺立场 / 坏 coupling
    r5 = run({'thesis': '要快'})
    assert r5['verdict'] == 'input_pending', r5
    r6 = run({'thesis': 'A', 'antithesis': 'B', 'coupling': 'xx'})
    assert r6['verdict'] == 'input_pending', r6
    print('✅ 缺立场/坏 coupling → input_pending（诚实拦截）')

    print('=' * 62)
    print('对位创生第三态构件自测：全部通过 ✅')
    print('=' * 62)
