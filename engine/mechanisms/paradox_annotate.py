"""
paradox_annotate.py — 悖论注解机制（核心机制）
===============================================
概念来源：落落逻辑体系 · 悖论注解机制
公式卡：formulas/paradox_annotate.md

机制语义：
    检测到悖论（A∧¬A共存）后不解决、不消除，只生成结构化注解卡片（8字段），
    记录悖论的来源、级别、影响范围，供系统后续参考。

核心公式：
    grade(来源, 影响, 可消除) ∈ {P-A, P-B, P-C}
        来源: axiom→A(结构性), runtime→B(运行期), observer→C(观察者)
        影响: global(全局) → 升级一级
        可消除: 无法消除 → 保持或升级一级
    Annotation = (ID, LV, POS, SRC, CT, EF, ST, AN)  8字段
        ID = 悖论_P-{级别}_{序号:03d}
"""

PORTS = {
    'in': {
        'paradox': 'dict?',  # {A, notA, pos, src, effect, note} 悖论对象（run 默认空）
        'source': 'str?',    # 'axiom'|'runtime'|'observer'（run 默认 'runtime'）
        'impact': 'str?',    # 'local'|'global'（默认 local）
        'eliminable': 'bool?',  # 是否可消除（默认 True）
        'seq': 'int?',       # 序号（ID 唯一性用，默认自增）
    },
    'out': {
        'annotation': 'dict',  # 8字段注解卡片
        'grade': 'str',        # 'P-A'|'P-B'|'P-C'
    }
}

# 级别序：A=0, B=1, C=2（P-A 最高级，P-C 最低）
_LEVEL_ORDER = {'P-A': 0, 'P-B': 1, 'P-C': 2}
_SOURCE_TO_BASE = {'axiom': 'P-A', 'runtime': 'P-B', 'observer': 'P-C'}


def _upgrade(grade):
    """级别升级一级（P-C → P-B，P-B → P-A，P-A 保持）。"""
    if grade == 'P-A':
        return 'P-A'
    return {0: 'P-A', 1: 'P-B', 2: 'P-C'}[_LEVEL_ORDER[grade] - 1]


def grade(source, impact='local', eliminable=True):
    """
    做什么：悖论分级（公式源 §2.1 分级判断流程）。

    规则：
        ① 来源定基础级: axiom→P-A, runtime→P-B, observer→P-C
        ② 影响全局(global) → 升级一级
        ③ 无法消除(eliminable=False) → 升级一级（底层冲突更严重）

    参数:
        source: str, 'axiom'|'runtime'|'observer'
        impact: str, 'local'|'global'
        eliminable: bool, 是否可消除

    返回:
        str: 'P-A'|'P-B'|'P-C'
    """
    g = _SOURCE_TO_BASE[source]
    if impact == 'global':
        g = _upgrade(g)
    if not eliminable:
        g = _upgrade(g)
    return g


def annotate(paradox, source, impact='local', eliminable=True, seq=None):
    """
    做什么：生成 8 字段悖论注解卡片（公式源 §2.2 模板）。

    字段: ID/LV/POS/SRC/CT/EF/ST/AN
        ID: 悖论_P-{级}_{序号:03d}
        LV: P-A/P-B/P-C
        POS: 位置（系统+层级+点位）
        SRC: 来源（触发链）
        CT: 内容（A和¬A及共存形式）
        EF: 影响（下游系统）
        ST: 状态（默认'活跃'）
        AN: 注解（自由文本）

    参数:
        paradox: dict, 悖论对象 {A, notA, pos, src, effect, note}
        source: str, 'axiom'|'runtime'|'observer'
        impact: str, 'local'|'global'
        eliminable: bool
        seq: int 或 None, 序号（None 用模块计数器自增）

    返回:
        dict: 8字段注解卡片
    """
    global _seq_counter
    if seq is None:
        _seq_counter += 1
        seq = _seq_counter

    g = grade(source, impact, eliminable)
    return {
        'ID': f"悖论_{g}_{seq:03d}",
        'LV': g,
        'POS': paradox.get('pos', ''),
        'SRC': paradox.get('src', ''),
        'CT': f"A={paradox.get('A','')}, ¬A={paradox.get('notA','')}, 共存形式={paradox.get('coexist','')}",
        'EF': paradox.get('effect', ''),
        'ST': '活跃',
        'AN': paradox.get('note', ''),
    }


def run(inputs):
    """
    做什么：机制统一接口 run(inputs: dict) -> dict。

    输入:
        paradox: dict, {A, notA, pos, src, effect, note}
        source: str, 'axiom'|'runtime'|'observer'
        impact: str（默认 local）
        eliminable: bool（默认 True）
        seq: int 或 None

    返回:
        dict: {annotation, grade}
    """
    card = annotate(
        inputs.get('paradox', {}),
        inputs.get('source', 'runtime'),
        inputs.get('impact', 'local'),
        inputs.get('eliminable', True),
        inputs.get('seq'),
    )
    return {'annotation': card, 'grade': card['LV']}


_seq_counter = 0


# ============================================================
# 自测（公式卡 P1/P2/P4）
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("悖论注解机制 · 自测")
    print("=" * 60)

    # P1 三级完备：来源 ∈ {公理,运行,观察} ⟹ 级别 ∈ {A,B,C}
    assert grade('axiom') == 'P-A', "公理→P-A"
    assert grade('runtime') == 'P-B', "运行→P-B"
    assert grade('observer') == 'P-C', "观察→P-C"
    print("✅ P1 三级完备: axiom→P-A, runtime→P-B, observer→P-C")

    # 分级升级规则（公式源 §2.1）：全局升级 / 不可消除升级
    assert grade('observer', impact='global') == 'P-B', "C级+全局→B级"
    assert grade('runtime', impact='global') == 'P-A', "B级+全局→A级"
    assert grade('runtime', eliminable=False) == 'P-A', "B级+不可消除→A级"
    assert grade('axiom', impact='global') == 'P-A', "A级+全局→保持A级（顶）"
    print("✅ 分级升级: 全局升一级 / 不可消除升一级 / A级封顶")

    # P2 8字段完整：注解必含 ID/LV/POS/SRC/CT/EF/ST/AN
    card = annotate(
        {'A': '肝气郁结', 'notA': '肝火上炎', 'pos': '中医系统·木线程',
         'src': '患者同现肝郁与肝火', 'effect': '治疗策略矛盾',
         'coexist': '见人易怒独处抑郁', 'note': '情志相胜待评估'},
        'runtime', impact='local', eliminable=True, seq=1,
    )
    required = {'ID', 'LV', 'POS', 'SRC', 'CT', 'EF', 'ST', 'AN'}
    assert required <= set(card.keys()), f"P2: 缺字段 {required - set(card.keys())}"
    assert len(card) == 8, f"P2: 应恰 8 字段, 实际 {len(card)}"
    assert card['ID'] == '悖论_P-B_001', f"ID 格式: {card['ID']}"
    assert card['LV'] == 'P-B' and card['ST'] == '活跃'
    assert '肝气郁结' in card['CT'] and '肝火上炎' in card['CT'], "CT 应含 A/¬A"
    print(f"✅ P2 8字段完整: ID={card['ID']}, LV={card['LV']}, ST={card['ST']}")

    # P4 ID 唯一：悖论_P-{级}_{序号} 不重复
    ids = set()
    for i in range(1, 6):
        c = annotate({'A': f'A{i}', 'notA': f'N{i}'}, 'runtime', seq=i)
        assert c['ID'] not in ids, f"P4: ID 重复 {c['ID']}"
        ids.add(c['ID'])
    assert len(ids) == 5, "P4: 5 个注解 ID 应全唯一"
    print("✅ P4 ID 唯一: 悖论_P-B_001..005 不重复")

    # C1 不解决（设计约束，非断言性质）：注解不修改 A/¬A，只标记
    # （验证：卡片内容不改变原悖论，且状态为'活跃'而非'已解决'）
    assert card['CT'] != '' and card['ST'] == '活跃', "C1: 注解只标记不解决"
    print("✅ C1 设计约束: 注解只标记、不解决（原悖论内容原样记录）")

    # run() 统一接口
    r = run({'paradox': {'A': 'X', 'notA': '¬X'}, 'source': 'axiom',
             'impact': 'global', 'eliminable': False, 'seq': 99})
    assert r['grade'] == 'P-A' and r['annotation']['ID'] == '悖论_P-A_099'
    print(f"✅ run() 接口: 公理+全局+不可消除 → {r['grade']}")

    print("\n" + "=" * 60)
    print("悖论注解自测通过（P1/P2/P4 + 分级升级 + C1 + run 接口）✅")
    print("=" * 60)
