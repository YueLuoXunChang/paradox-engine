# -*- coding: utf-8 -*-
"""
controller.py — 总控五步流水线（判类→判复杂度→切路→执行→判输出）
========================================================================
概念来源：《总架构与路由》——总控五步 = 引擎"大脑"。
本构件把判类器（engine/control/classifier.py 步1/2/3）+ 各层真实构件
（第 1 层经典 / 第 2 层悖论）串成一条可跑流水线，并做步 5 输出判定
（完整性/一致性/置信度/边界性/充分度 五查）。

本构件做什么（一句话）：
    输入一段问题文本（可带结构化线索）→ 判类 → 判复杂度 → 切路 →
    按路由管线真跑构件 → 五查判输出 → 中文诊断报告 + 结构化对象。

执行映射（pipeline 名字 → 真实构件）：
    propositional.validity / propositional.consistency / first_order.query
    / paradox_measure.mu1/mu2/mu4 / paradox_annotate / selfref_fixpoint /
    boundary_paradox / counterpoint_gen / wall_pipeline / converge_check
    / nd_propositional / ltl / modal
    映射不到（骨架/冷门/Dung 等未实现层）→ 诚实标 'not_built'。

诚实边界：
    - 从自然语言到逻辑式的自动提取超出本引擎范围——执行步需要结构化
      线索（structured）才能真正跑构件；没有就诚实报"缺结构化输入，
      建议给 premises/conclusion/A/B/expr 等"，不假装跑；
    - 步 5 五查是质量判定（完整性/一致性/置信度/边界性/充分度），
      不下"你该怎么做"的结论（只诊断不决策）；
    - 判类 confidence=low → 步 5 强制提示"分类存疑"；
    - L1 跑完发现隐含复杂 → 提示"可能低估，建议升档"（双向防错）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        text: str——问题文本（必填，给判类/复杂度）
        structured: dict——结构化线索（可选）：
            T1: {premises: [...], conclusion: str}
            T2: {A: str, B: str}
            T6: {sentence: str}
            T7: {thesis: str, antithesis: str}
            T9: {query: str}（示例）
        debug: bool——是否带 trace 全量（默认 False）
    输出:
        verdict: str——'done'（至少一个构件真跑）| 'classified_only'
                      （只判类未执行）| 'input_pending'
        classification: dict——步1-3 结果
        execution: list——每构件执行结果 {step, component, status,
                    output 摘要}
        output_check: dict——步5 五查结果
        report: str——中文诊断报告（给人看）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'text': 'str?', 'structured': 'dict?', 'debug': 'bool?'},
    'out': {'verdict': 'str', 'classification': 'dict', 'execution': 'list',
            'output_check': 'dict', 'report': 'str', 'boundary': 'str'},
}

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))   # paradox-engine 根
for _p in (_HERE, _REPO, os.path.join(_REPO, 'engine', 'classical'),
           os.path.join(_REPO, 'engine', 'mechanisms')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 双模式导入：pip 安装后走 engine. 前缀；直接运行本文件走平级
try:
    from engine.control.classifier import run as classify  # noqa: E402
except ImportError:
    from classifier import run as classify  # noqa: E402


# ══════════════════════════════════════════════════════════════
# 执行映射：pipeline 构件名 → (模块导入, 输入构造函数)
# 输入构造函数(structured) -> dict 或 None（None=缺结构化输入）
# ══════════════════════════════════════════════════════════════

def _builders():
    import importlib

    def get(mod):
        # mod 形如 'classical.propositional' / 'mechanisms.paradox_measure'
        # repo 根已在 sys.path → engine.classical.propositional
        return importlib.import_module(f'engine.{mod}')

    def need(struct, keys, hint):
        if not struct:
            return None, hint
        missing = [k for k in keys if k not in struct]
        if missing:
            return None, f'缺结构化输入 {missing}（{hint}）'
        return struct, None

    builders = {}

    def b_prop_validity(struct):
        d, hint = need(struct, ['premises', 'conclusion'],
                       'T1 需 premises/conclusion')
        if d is None:
            return None, hint
        if not d['premises']:
            # 空前提 = 直接判 conclusion 自身（重言/矛盾/偶真）
            return {'formula': d['conclusion']}, None
        return {'premises': d['premises'], 'conclusion': d['conclusion'],
                'mode': 'validity'}, None

    def b_prop_consistency(struct):
        d, hint = need(struct, ['formula'], '需 formula 命题公式')
        if d is None:
            return None, hint
        return {'formula': d['formula'], 'mode': 'consistency'}, None

    def b_fol_query(struct):
        d, hint = need(struct, ['facts', 'rules', 'query'],
                       'T9/T1-L2 需 facts/rules/query')
        if d is None:
            return None, hint
        return {'facts': d['facts'], 'rules': d['rules'],
                'query': d['query']}, None

    def b_mu1(struct):
        d, hint = need(struct, ['wA', 'wNotA'],
                       '需 wA/wNotA 证据权重')
        if d is None:
            return None, hint
        return {'mode': 'mu1', 'wA': d['wA'], 'wNotA': d['wNotA']}, None

    def b_mu2(struct):
        return {'mode': 'mu2'}, None

    def b_annotate(struct):
        d, hint = need(struct, ['A', 'B'],
                       '需 A/¬A 两方（T2 用）')
        if d is None:
            return None, hint
        return {'paradox': {'A': d['A'], 'notA': d['B'],
                            'pos': '总控执行层',
                            'src': 'runtime',
                            'effect': '下游决策',
                            'note': '总控 T2 自动注解'},
                'source': 'runtime', 'impact': 'global',
                'eliminable': True}, None

    def b_selfref(struct):
        d, hint = need(struct, ['sentence'],
                       'T6 需 sentence（liar/godel/truth_teller 或句子）')
        if d is None:
            return None, hint
        s = d['sentence']
        known = {'liar': 'liar', 'godel': 'godel',
                 'truth_teller': 'truth_teller',
                 '这句话是假的': 'liar', '本句不可证': 'godel',
                 '本句为真': 'truth_teller'}
        if s in known:
            return {'mode': 'sentence', 'sentence': known[s]}, None
        return {'mode': 'iterate',
                'f': lambda x: not x if isinstance(x, bool) else 1 - x,
                'state0': False}, None

    def b_boundary(struct):
        d, hint = need(struct, ['wall_name'],
                       '需 wall_name（墙名）')
        if d is None:
            return None, hint
        return {'wall_name': d['wall_name'],
                'inside': d.get('inside', '可判定'),
                'outside': d.get('outside', '不可判定')}, None

    def b_counterpoint(struct):
        d, hint = need(struct, ['thesis', 'antithesis'],
                       'T7 需 thesis/antithesis')
        if d is None:
            return None, hint
        return {'thesis': d['thesis'], 'antithesis': d['antithesis']}, None

    def b_wall(struct):
        d, hint = need(struct, ['wall'], '需 wall（疑似墙描述）')
        if d is None:
            return None, hint
        return {'wall': d['wall'],
                'thesis': d.get('thesis'), 'antithesis': d.get('antithesis'),
                'events': d.get('events')}, None

    def b_converge(struct):
        d, hint = need(struct, ['f', 'err_fn'], '需 f/err_fn 函数')
        if d is None:
            return None, hint
        return {'branch': d.get('branch', 'finite'),
                'f': d['f'], 'err_fn': d['err_fn'],
                'x0': d.get('x0', 0.0)}, None

    def b_belnap(struct):
        d, hint = need(struct, ['formula'], '需 formula 命题公式（四值求值）')
        if d is None:
            return None, hint
        return {'formula': d['formula'], 'assign': d.get('assign') or {}}, None

    def b_dung(struct):
        d, hint = need(struct, ['arguments', 'attacks'],
                       '需 arguments/attacks（论证+攻击图）')
        if d is None:
            return None, hint
        return {'arguments': d['arguments'], 'attacks': d['attacks']}, None

    def b_mtmp(struct):
        d, hint = need(struct, ['mode'], '骨架需 mode（point/thread/'
                       'topology/op）')
        if d is None:
            return None, hint
        base = dict(d)
        return base, None

    builders.update({
        'propositional.validity': ('classical.propositional',
                                   b_prop_validity),
        'propositional.consistency': ('classical.propositional',
                                      b_prop_consistency),
        'first_order.query': ('classical.first_order', b_fol_query),
        'paradox_measure.mu1': ('mechanisms.paradox_measure', b_mu1),
        'paradox_measure.mu2': ('mechanisms.paradox_measure', b_mu2),
        'paradox_measure.mu4': ('mechanisms.paradox_measure',
                                lambda s: ({'mode': 'mu4', 'wA': 5,
                                            'wNotA': 5}, None)),
        'paradox_annotate': ('mechanisms.paradox_annotate', b_annotate),
        'selfref_fixpoint': ('mechanisms.selfref_fixpoint', b_selfref),
        'boundary_paradox': ('mechanisms.boundary_paradox', b_boundary),
        'counterpoint_gen': ('mechanisms.counterpoint_gen', b_counterpoint),
        'wall_pipeline': ('mechanisms.wall_pipeline', b_wall),
        'converge_check': ('mechanisms.converge_check', b_converge),
        'converge_check.finite': ('mechanisms.converge_check', b_converge),
        'belnap_four': ('cold.belnap_four', b_belnap),
        'dung': ('cold.dung_framework', b_dung),
        'skeleton': ('skeleton.mtmp', b_mtmp),
        'mtmp': ('skeleton.mtmp', b_mtmp),
    })
    return builders, get


# ══════════════════════════════════════════════════════════════
# 步 5 输出五查
# ══════════════════════════════════════════════════════════════

def _output_check(classification, execution, text_len):
    checks = {}

    # ① 完整性：管线有多少构件真跑/缺结构/未实现
    total = len(execution)
    ran = sum(1 for e in execution if e['status'] == 'run')
    missing = sum(1 for e in execution if e['status'] == 'missing_input')
    not_built = sum(1 for e in execution if e['status'] == 'not_built')
    checks['completeness'] = {
        'note': f'管线 {total} 件：真跑 {ran} / 缺结构化输入 {missing} / '
                f'未实现层 {not_built}',
        'ok': ran > 0}

    # ② 一致性：μ 与注解分级交叉校验（真跑过的结果里看）
    mu_val = None
    grade_val = None
    for e in execution:
        if e['status'] == 'run':
            out = e.get('output') or {}
            if out.get('mu') is not None:
                mu_val = out['mu']
            if out.get('grade'):
                grade_val = out['grade']
    consistent = True
    if mu_val is not None and grade_val is not None:
        # μ≈1 时结构性矛盾应 ≥P-B；μ<0.3 不该有 P-A
        if mu_val > 0.8 and grade_val not in ('P-A', 'P-B'):
            consistent = False
        if mu_val < 0.3 and grade_val == 'P-A':
            consistent = False
    checks['consistency'] = {
        'note': (f'交叉校验 μ={mu_val}, grade={grade_val} → '
                 f'{"一致" if consistent else "不一致"}'),
        'ok': consistent}

    # ③ 置信度：判类 low → 强制提示
    conf = classification.get('confidence')
    checks['confidence'] = {
        'note': f'判类置信度 {conf}' +
                ('——分类存疑，输出仅供参考' if conf == 'low' else ''),
        'ok': conf != 'low'}

    # ④ 边界性：未实现/未识别题型是否诚实标注
    bounded = (not_built > 0) or (
        classification.get('main_type') == 'T12')
    checks['boundary'] = {
        'note': ('已标注未实现层/未识别题型' if bounded
                 else '未触发边界标注（无未实现层参与）'),
        'ok': True}

    # ⑤ 充分度：L1 却文本较长/信号多 → 可能低估；L3 却短 → 可能过重
    level = classification.get('level')
    if level == 'L1' and text_len > 40:
        checks['adequacy'] = {'note': 'L1 但文本较长——可能低估，'
                                      '建议升档复核', 'ok': False}
    elif level == 'L3' and text_len < 20:
        checks['adequacy'] = {'note': 'L3 但文本较短——可能过重，'
                                      '可考虑轻量道', 'ok': False}
    else:
        checks['adequacy'] = {'note': f'{level} 与输入规模匹配', 'ok': True}

    return checks


def run(inputs):
    """
    做什么：跑总控五步流水线。

    返回 dict（见模块 docstring）。"""
    text = inputs.get('text')
    if not text or not isinstance(text, str):
        return {'verdict': 'input_pending', 'classification': None,
                'execution': [], 'output_check': None, 'report': '',
                'boundary': '需给 text（问题文本）——诚实：空文本不硬跑'}
    structured = inputs.get('structured') or {}
    debug = inputs.get('debug', False)

    # ── 步 1-3：判类 → 复杂度 → 路由（复用 classifier）
    cl = classify({'text': text, 'debug': debug})
    classification = {'main_type': cl['main_type'],
                      'main_name': cl['main_name'],
                      'types': cl['types'],
                      'confidence': cl['confidence'],
                      'level': cl['level'],
                      'complexity': cl['complexity'],
                      'route': cl['route']}

    # ── 步 4：执行（按路由管线逐个真跑；映射不到 → not_built）
    builders, get = _builders()
    pipeline = cl['route']['pipeline']
    execution = []
    for comp in pipeline:
        if comp not in builders:
            execution.append({'step': len(execution) + 1,
                              'component': comp,
                              'status': 'not_built',
                              'note': f'{comp} 未实现层/未映射——诚实跳过'})
            continue
        mod_name, builder = builders[comp]
        try:
            mod = get(mod_name)
            run_fn = mod.run
        except Exception as e:
            execution.append({'step': len(execution) + 1,
                              'component': comp, 'status': 'not_built',
                              'note': f'模块导入失败：{e}'})
            continue
        args, hint = builder(structured)
        if args is None:
            execution.append({'step': len(execution) + 1,
                              'component': comp, 'status': 'missing_input',
                              'note': hint})
            continue
        try:
            out = run_fn(args)
        except Exception as e:
            execution.append({'step': len(execution) + 1,
                              'component': comp, 'status': 'error',
                              'note': f'执行异常：{e}'})
            continue
        execution.append({'step': len(execution) + 1, 'component': comp,
                          'status': 'run', 'output': out,
                          'note': 'OK'})

    # ── 步 5：五查
    checks = _output_check(classification, execution, len(text))

    ran_count = sum(1 for e in execution if e['status'] == 'run')
    verdict = 'done' if ran_count > 0 else 'classified_only'

    # ── 报告（给人看，中文）
    main_t = classification['main_type']
    main_n = classification['main_name']
    lv = classification['level']
    rep = [f'【类型】{main_t} {main_n} · 复杂度 {lv}'
           f' · 路由 {classification["route"]["route_id"]}',
           f'【路由依据】{classification["route"]["reason"]}',
           f'【执行】{checks["completeness"]["note"]}']
    for e in execution:
        if e['status'] == 'run':
            out = e.get('output') or {}
            brief = {k: v for k, v in out.items()
                     if k in ('verdict', 'mu', 'grade', 'converges',
                              'inferred', 'coupling', 'diagnosis',
                              'tension')}
            rep.append(f'  ✓ {e["component"]}: {brief}')
        else:
            rep.append(f'  · {e["component"]}: {e["note"]}')
    rep.append(f'【五查】' + '；'.join(
        f"{k}:{'✅' if v['ok'] else '⚠️'}({v['note']})"
        for k, v in checks.items()))
    if classification['confidence'] == 'low':
        rep.append('【提示】判类置信度低——分类存疑，仅供参考')
    if classification['main_type'] == 'T12':
        rep.append('【提示】未识别出明确题型，仅做了基础检查')
    rep.append('【边界】引擎只诊断不决策：怎么处理由使用者判断；'
               '自指/不可判定处引擎不宣称判定真值')
    report = '\n'.join(rep)

    return {'verdict': verdict, 'classification': classification,
            'execution': execution, 'output_check': checks,
            'report': report,
            'boundary': '总控执行需结构化线索才能真跑构件（自然语言→逻辑式'
                        '自动提取不在本引擎范围——诚实标注）。五查是质量'
                        '判定不下决策。分类存疑/未识别题型/未实现层均诚实'
                        '提示。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('总控五步流水线 · 自测')
    print('=' * 62)

    # 1) 38 走查一：产品需求打架（T2-L2 端到端，真跑 μ+注解）
    r1 = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项'
                      '（12周）',
              'structured': {'A': '尽快上线(3周)',
                             'B': '完整覆盖合规(12周)',
                             'wA': 5, 'wNotA': 5}})
    assert r1['verdict'] == 'done', r1
    assert r1['classification']['main_type'] == 'T2', r1
    ran = [e for e in r1['execution'] if e['status'] == 'run']
    assert any('paradox_measure' in e['component'] for e in ran), ran
    assert any('paradox_annotate' in e['component'] for e in ran), ran
    assert '【类型】' in r1['report'] and '【五查】' in r1['report'], r1
    print(f"✅ 需求打架 → {r1['classification']['route']['route_id']} "
          f"真跑 {len(ran)} 件")
    print(f"   report 首行: {r1['report'].splitlines()[0]}")

    # 2) 38 走查三：排中律（T1-L1 单机制——最小充分）
    r2 = run({'text': '今天下雨或没下雨',
              'structured': {'premises': [], 'conclusion': 'P∨¬P'}})
    assert r2['verdict'] == 'done', r2
    ran2 = [e for e in r2['execution'] if e['status'] == 'run']
    assert len(ran2) == 1 and 'propositional' in ran2[0]['component'], r2
    print(f"✅ 排中律 → L1 单机制直出（{len(ran2)} 件——最小充分）")

    # 3) 说谎者（T6-L2 selfref_fixpoint 真跑）
    r3 = run({'text': '这句话是假的',
              'structured': {'sentence': '这句话是假的'}})
    assert r3['verdict'] == 'done', r3
    ran3 = [e for e in r3['execution'] if e['status'] == 'run']
    assert any('selfref' in e['component'] for e in ran3), r3
    print(f"✅ 说谎者句 → selfref_fixpoint 真跑（{r3['classification']['route']['route_id']}）")

    # 4) 未给结构化 → 诚实缺输入（classified_only）
    r4 = run({'text': '产品既要快又要稳'})
    assert r4['verdict'] == 'classified_only', r4
    assert any(e['status'] == 'missing_input' for e in r4['execution']), r4
    print('✅ 无结构化线索 → 诚实 missing_input（不假装跑）')

    # 5) 未分类 → T12 诚实
    r5 = run({'text': '随便写点什么'})
    assert r5['classification']['main_type'] == 'T12', r5
    assert '未识别' in r5['report'], r5
    print('✅ 无信号 → T12 未识别提示')

    # 6) 边界：空文本
    r6 = run({})
    assert r6['verdict'] == 'input_pending', r6
    print('✅ 空文本 → input_pending（诚实拦截）')

    print('=' * 62)
    print('总控五步流水线自测：全部通过 ✅')
    print('=' * 62)
