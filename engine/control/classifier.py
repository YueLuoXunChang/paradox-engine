# -*- coding: utf-8 -*-
"""
classifier.py — 判类器 + 复杂度分级器 + 路由表（总控步 1/2/3，引擎神经系统）
==============================================================================
概念来源：任务指标《44_逻辑建模引擎_判类器复杂度详规》+《38 总架构与路由》
（38 步 1 判类 / 步 2 判复杂度 / 步 3 切路 落码）——落落体系规划文档。
详规：44（信号表/权重/打分公式/ROUTE 接口）+ 38（12 题型定义/三档复杂度/
路由白箱）。本构件把"怎么认题、怎么决定走轻量道还是全量道"变成可跑规则。

本构件做什么（一句话）：
    输入一段问题文本 → 输出：题型（主型+副型+置信度）→ 复杂度档（L1/L2/L3）
    → 路由管线（本型本档该用哪些构件，带 reason 白箱）。

诚实边界：
    - 分类/复杂度是**启发式打分**（中文关键词信号），不是语言学完备分析——
      标注"启发式，非完备"；
    - 命中 0 型 → T12 未分类（诚实返回，不硬塞题型）；
    - 多型接近 → 主型取最高，副型列出（不假装单一）；
    - confidence low → 输出标"分类存疑"（由上层步 5 决定是否提示）；
    - 复杂度中的实体/关系计数是工程估计（顿号/关系词启发），标"估计值"。

统一接口：
    run(inputs: dict) -> dict
    输入:
        text: str——待判题文本（必填）
        debug: bool——是否在输出里带全型得分明细（默认 False）
    输出:
        verdict: str——'classified' | 'input_pending'
        main_type: str——T1..T12
        main_name: str——题型中文名
        types: list[dict]——{type, name, score, signals}（主型在前）
        confidence: str——'high'|'medium'|'low'
        complexity: dict——{entity_est, relation_est, score, level, flags}
        level: str——'L1'|'L2'|'L3'
        route: dict——{route_id, pipeline, reason}
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'text': 'str?', 'debug': 'bool?'},
    'out': {'verdict': 'str', 'main_type': 'str', 'main_name': 'str',
            'types': 'list', 'confidence': 'str', 'complexity': 'dict',
            'level': 'str', 'route': 'dict', 'boundary': 'str'},
}

# ══════════════════════════════════════════════════════════════
# 一、题型信号表（44 §1.1——中文关键词/结构 → 题型 → 权重）
# 每型：name 中文名 + signals 信号（命中一条 +weight 一次）
# ══════════════════════════════════════════════════════════════

TYPE_DEFS = {
    'T1': {'name': '命题真值', 'weight': 2, 'signals': [
        '所有', '都', '任何', '所以', '因此', '是', '比较', '更', '结论',
        '推理', '或', '真假', '成立', '恒真', '对不对']},
    'T2': {'name': '论证矛盾', 'weight': 3, 'signals': [
        '既要', '又要', '一方面', '另一方面', '但是', '矛盾', '打架',
        '冲突', '不一致', '既想', '又想', '两难', '自相矛盾']},
    'T3': {'name': '关系结构', 'weight': 3, 'signals': [
        '支持', '反对', '依赖', '包含', '攻击', '信任', '关系', '相连',
        '指向', '影响', '关联']},
    'T4': {'name': '演化过程', 'weight': 3, 'signals': [
        '每', '多久', '逐渐', '最终', '越来越', '每次', '减半', '加倍',
        '演化', '发展', '推移', '过程', '变化', '增长', '衰减']},
    'T5': {'name': '知识更新', 'weight': 3, 'signals': [
        '原来以为', '现在发现', '打破了', '例外', '黑天鹅', '证伪',
        '推翻', '新发现', '旧结论', '更新']},
    'T6': {'name': '自指/深层', 'weight': 4, 'signals': [
        '这句话', '本命题', '这个定义', '不是真的', '不可证', '无法判定',
        '自身', '自己', '自指', '说谎者', '本句', '递归']},
    'T7': {'name': '对立交汇', 'weight': 3, 'signals': [
        '自由', '秩序', '个体', '集体', '要快', '要稳', '结合', '融合',
        '催生', '兼得', '对立', '交汇', '效率', '公平']},
    'T8': {'name': '证据冲突', 'weight': 3, 'signals': [
        '证据', '检测', '数据显示', '但表现', '阳性', '阴性', '实测',
        '报告说', '相互矛盾的数据']},
    'T9': {'name': '学科题目', 'weight': 4, 'signals': [
        '建模', '机制', '如何', '原因', '耐药', '演化出', '通路',
        '系统', '理论', '模型', '假设机制']},
    'T10': {'name': '定义辨析', 'weight': 2, 'signals': [
        '区别', '不同', '是不是一回事', '边界', '定义', '辨析',
        '什么算', '算不算']},
    'T11': {'name': '假设检验', 'weight': 2, 'signals': [
        '有效率', '可能性', '概率', '信不信', '靠不靠谱', '要不要信',
        '可靠', '置信', '显著']},
}

# 实体/关系提取用词（复杂度估计）
_REL_VERBS = ('支持', '反对', '依赖', '包含', '攻击', '信任', '指向',
              '影响', '导致', '促进', '抑制', '关联', '隶属')
_ENTITY_SEP = ('和', '与', '、', '，', ',', '及')
_STOP_NOUNS = ('这个', '那个', '我们', '你们', '他们', '问题', '情况',
               '东西', '时候', '方面', '部分', '内容')


def _classify(text):
    """题型计分（44 §1.1：命中信号 += weight 一次/信号去重）。"""
    hits = []
    for tid, spec in TYPE_DEFS.items():
        score = 0
        matched = []
        for sig in spec['signals']:
            if sig in text:
                score += spec['weight']
                matched.append(sig)
        if matched:
            hits.append({'type': tid, 'name': spec['name'],
                         'score': score, 'signals': matched})
    hits.sort(key=lambda h: (-h['score'], h['type']))
    return hits


def _confidence(hits):
    """置信度：主型显著高于次型 → high；接近 → medium；仅 1 型低分 → low。"""
    if not hits:
        return 'low'
    top = hits[0]['score']
    if len(hits) == 1:
        return 'low' if top <= 4 else 'medium'
    second = hits[1]['score']
    if top - second >= 4:
        return 'high'
    if top - second >= 2:
        return 'medium'
    return 'low'


_CLAUSE_SEP = ('既要', '又要', '一方面', '另一方面', '还是', '或者',
               '不仅', '而且', '但是', '但', '同时')


def _count_entities(text):
    """实体数估计（工程估计，诚实标注）：
    第一层按并列/转折连接词切分（既要X，又要Y → 2 段），
    第二层按 顿号/和/与/逗号/括号 切分计数。"""
    parts = [text]
    for sep in _CLAUSE_SEP:
        nxt = []
        for p in parts:
            if sep in p:
                nxt.extend([s for s in p.split(sep) if s.strip()])
            else:
                nxt.append(p)
        parts = nxt
    count = 0
    for p in parts:
        for s in p.replace('，', ' ').replace('、', ' ').replace(',', ' ') \
                 .replace('（', ' ').replace('）', ' ').split():
            if s.strip():
                count += 1
    return max(1, count)


def _count_relations(text):
    """关系数估计（工程估计）：关系动词出现次数。"""
    return sum(1 for v in _REL_VERBS for _ in range(text.count(v)))


def _complexity(text, hits):
    """复杂度打分（44 §2.1 / 38 §3.2）。返回 dict。"""
    n = _count_entities(text)
    m = _count_relations(text)
    entity_tier = 1 if n <= 3 else (2 if n <= 10 else 3)
    relation_tier = 1 if m <= 2 else (2 if m <= 8 else 3)
    score = entity_tier + relation_tier

    flags = []
    tids = {h['type'] for h in hits}
    # 结构加分（38 §3.2）
    if 'T4' in tids:
        score += 1
        flags.append('演化+1')
    if 'T6' in tids:
        score += 2
        flags.append('自指+2')
    if 'T8' in tids:
        score += 1
        flags.append('多源证据+1')
    if 'T7' in tids or 'T2' in tids:
        score += 1
        flags.append('对立+1')
    # 量词嵌套/嵌套层：启发——含"∀/所有…所有…/…的…的"深嵌套
    if text.count('所有') >= 2 or '∀' in text:
        score += 1
        flags.append('量词嵌套+1')

    level = 'L1' if score <= 3 else ('L2' if score <= 7 else 'L3')

    # 题型修正（38 §4.1 落码）：T9 学科题目"罕见 L1"——术语密集即建模
    # 全量候选。命中 ≥4 学科信号（术语密集+多实体结构）→ L3；
    # 命中 3 → L2。诚实标注为规则修正，非打分公式产物。
    t9_hits = sum(1 for h in hits if h['type'] == 'T9'
                  for _ in h['signals'])
    if 'T9' in tids and t9_hits >= 4:
        level = 'L3'
        flags.append('T9学科密集→L3（38 §4.1 规则）')
    elif 'T9' in tids and t9_hits == 3:
        if level == 'L1':
            level = 'L2'
        flags.append('T9学科信号3→L2（38 §4.1 规则）')

    return {'entity_est': n, 'relation_est': m, 'entity_tier': entity_tier,
            'relation_tier': relation_tier, 'score': score, 'level': level,
            'flags': flags}


# ══════════════════════════════════════════════════════════════
# 二、路由表（44 §3 / 38 §4.1 落码——题型×复杂度 → 管线，带 reason 白箱）
# ══════════════════════════════════════════════════════════════

ROUTE = {
    ('T1', 'L1'): (['propositional.validity'], '命题单机制判有效性（最小充分）'),
    ('T1', 'L2'): (['propositional.validity', 'first_order.query'],
                   '加一阶量词展开'),
    ('T1', 'L3'): (['first_order.query', 'nd_propositional'],
                   '复杂断言集走一阶+证明'),
    ('T2', 'L1'): (['paradox_measure.mu1'], '单对矛盾测 μ（轻量）'),
    ('T2', 'L2'): (['paradox_measure.mu1', 'paradox_annotate'],
                   'μ + 注解卡（冲突定位）'),
    ('T2', 'L3'): (['wall_pipeline'], '撞墙管线五选一（含立场分析）'),
    ('T3', 'L1'): (['propositional.consistency'], '简单关系一致性检查'),
    ('T3', 'L2'): (['first_order.query'], '关系推理（传递/对称）'),
    ('T3', 'L3'): (['first_order.query', 'skeleton'], '拓扑形态（需骨架层）'),
    ('T4', 'L1'): (['converge_check.finite'], '一步递推检查'),
    ('T4', 'L2'): (['converge_check'], '收敛判定四分支'),
    ('T4', 'L3'): (['ltl', 'converge_check', 'skeleton'],
                   '时序 LTL + 收敛 + 多线骨架'),
    ('T5', 'L1'): (['propositional.consistency'], '新旧断言对比'),
    ('T5', 'L2'): (['paradox_measure.mu1'], '新信息冲突测 μ'),
    ('T5', 'L3'): (['wall_pipeline'], '信念更新撞墙走五选一'),
    ('T6', 'L1'): (['paradox_measure.mu2'], '自指直判 μ=1'),
    ('T6', 'L2'): (['selfref_fixpoint'], '递归修正三态观察'),
    ('T6', 'L3'): (['selfref_fixpoint', 'boundary_paradox', 'counterpoint_gen'],
                   '共振带 + 边界诊断 + 创生'),
    ('T7', 'L1'): (['paradox_measure.mu1'], '对立对共存检查'),
    ('T7', 'L2'): (['counterpoint_gen'], '第三态生成（共振/桥）'),
    ('T7', 'L3'): (['counterpoint_gen', 'wall_pipeline'],
                   '第三态 + 撞墙管线全编排'),
    ('T8', 'L1'): (['paradox_measure.mu1'], '两证据权重对比'),
    ('T8', 'L2'): (['paradox_measure.mu4'], '证据冲突熵测度'),
    ('T8', 'L3'): (['wall_pipeline'], '证据冲突上卷撞墙管线'),
    ('T9', 'L1'): (['first_order.query'], '罕见——最小谓词建模'),
    ('T9', 'L2'): (['first_order.query', 'propositional.validity'],
                   '谓词建模 + 关键量检验'),
    ('T9', 'L3'): (['first_order.query', 'ltl', 'wall_pipeline'],
                   '本体化 + 演化 + 悖论扫描（全管线）'),
    ('T10', 'L1'): (['propositional.consistency'], '概念对一致性检查'),
    ('T10', 'L2'): (['first_order.query'], '谓词刻画两概念'),
    ('T10', 'L3'): (['first_order.query', 'boundary_paradox'],
                    '本体对齐 + 边界诊断'),
    ('T11', 'L1'): (['propositional.validity'], '单概率断言检查'),
    ('T11', 'L2'): (['converge_check.finite'], '权重迭代校验'),
    ('T11', 'L3'): (['wall_pipeline'], '假设检验遇冲突走管线'),
    ('T12', 'L1'): (['propositional.consistency'], '未分类——通用最小管线'),
    ('T12', 'L2'): (['propositional.consistency'], '同 L1（不升档，诚实标注）'),
    ('T12', 'L3'): (['propositional.consistency'], '同 L1（不升档，诚实标注）'),
}

_TYPE_NAME = {tid: spec['name'] for tid, spec in TYPE_DEFS.items()}
_TYPE_NAME['T12'] = '未分类'


def run(inputs):
    """
    做什么：判类（步1）→ 复杂度（步2）→ 路由（步3），总控入口。

    返回 dict（见模块 docstring）。"""
    text = inputs.get('text')
    if not text or not isinstance(text, str):
        return {'verdict': 'input_pending', 'main_type': None,
                'main_name': None, 'types': [], 'confidence': None,
                'complexity': None, 'level': None, 'route': None,
                'boundary': '需给 text（待判问题文本）——诚实：空文本不硬判'}
    debug = inputs.get('debug', False)

    # 步1 判类
    hits = _classify(text)
    if not hits:
        main_type = 'T12'
    else:
        main_type = hits[0]['type']
    confidence = _confidence(hits)
    main_name = _TYPE_NAME[main_type]

    # 步2 复杂度（含 T12 未分类——仍估复杂度走最小管线）
    cx = _complexity(text, hits)
    level = cx['level']

    # 步3 路由
    pipeline, reason = ROUTE.get((main_type, level),
                                 ROUTE[('T12', 'L1')])
    route = {'route_id': f'R{main_type[1:]}-{level}',
             'pipeline': pipeline, 'reason': reason,
             'needs_skeleton': 'skeleton' in pipeline,
             'needs_cold_logic': 'dung' in pipeline}

    # 输出题型明细（主型在前）
    out_types = []
    for h in hits:
        entry = {'type': h['type'], 'name': h['name'], 'score': h['score'],
                 'signals': h['signals'][:5]}
        out_types.append(entry)
    if not out_types:
        out_types = [{'type': 'T12', 'name': '未分类', 'score': 0,
                      'signals': []}]

    boundary = ('判类/复杂度是启发式打分（中文关键词信号表），非语言学'
                '完备分析。T12 未分类 → 通用最小管线并诚实标注。多型接近'
                '→ 副型已列出。复杂度实体/关系数为工程估计。分类存疑'
                '（confidence=low）时上层应提示。')
    if debug:
        boundary += f' 全型得分：{[(h["type"], h["score"]) for h in hits]}'

    return {'verdict': 'classified', 'main_type': main_type,
            'main_name': main_name, 'types': out_types,
            'confidence': confidence, 'complexity': cx, 'level': level,
            'route': route, 'boundary': boundary}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('判类器 + 复杂度 + 路由 · 自测（总控步 1/2/3）')
    print('=' * 62)

    # 1) 排中律（38 走查三，T1-L1——验证不被复杂化）
    r1 = run({'text': '今天下雨或没下雨'})
    assert r1['main_type'] == 'T1', r1
    assert r1['level'] == 'L1', r1
    assert 'propositional.validity' in r1['route']['pipeline'], r1
    print(f"✅ 排中律 → {r1['main_type']}({r1['main_name']}) "
          f"{r1['level']} → {r1['route']['pipeline']}")

    # 2) 产品需求打架（38 走查一，T2-L2）
    r2 = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）'})
    assert r2['main_type'] == 'T2', r2
    assert r2['level'] == 'L2', r2
    assert r2['route']['route_id'] == 'R2-L2', r2
    print(f"✅ 需求打架 → {r2['main_type']} {r2['level']} → "
          f"{r2['route']['pipeline']}")

    # 3) 说谎者（T6——自指）
    r3 = run({'text': '这句话是假的'})
    assert r3['main_type'] == 'T6', r3
    print(f"✅ 说谎者句 → {r3['main_type']}({r3['main_name']}) "
          f"{r3['level']} → {r3['route']['pipeline']}")

    # 4) 对立交汇（T7）
    r4 = run({'text': '要自由还是要秩序，能不能兼得'})
    assert r4['main_type'] == 'T7', r4
    print(f"✅ 自由×秩序 → {r4['main_type']}({r4['main_name']}) "
          f"{r4['level']} → {r4['route']['pipeline']}")

    # 5) 学科题目（T9-L3）
    r5 = run({'text': '肿瘤在靶向药下如何演化出耐药，能否建模其多线路径'})
    assert r5['main_type'] == 'T9', r5
    assert r5['level'] == 'L3', r5
    print(f"✅ 耐药演化 → {r5['main_type']} {r5['level']} → "
          f"{r5['route']['pipeline']}")

    # 6) 边界：空文本 / 未分类
    r6 = run({})
    assert r6['verdict'] == 'input_pending', r6
    r7 = run({'text': '随便写点什么没有信号'})
    assert r7['main_type'] == 'T12', r7
    print(f"✅ 空文本→input_pending；无信号→T12 未分类（诚实）")

    print('=' * 62)
    print('判类器 + 复杂度 + 路由自测：全部通过 ✅')
    print('=' * 62)
