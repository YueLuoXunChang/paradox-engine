# -*- coding: utf-8 -*-
"""
corpus_stats.py — 语料统计（对照一致率 · 混淆矩阵 · 覆盖缺口 · 复核进度）
================================================================================
概念来源：轨 B（应用化）+ 判类误判回馈闭环——场景库 28 个场景跑出来的
"期望 vs 实际"一直只在 `--stats` 里报个总数；要把语料当**回馈信号**用，
得能看出"哪个型容易被判成哪个型"（混淆矩阵），以及"每型还差几个"（覆盖缺口）。
本构件为**工程件**（不是外部借鉴的逻辑语义，故不标借鉴区）。

本构件做什么（一句话）：
    把场景库的对照结果统计成三张表——**一致率**（逐型 + 总体）、
    **混淆矩阵**（期望型 × 实际型，只看不一致的格子，直接指向该修的信号表）、
    **覆盖缺口**（每型离目标个数还差几个），外加**复核进度**（哪些型还没人复核）。

三个口径必须分清（本构件存在的意义就是把它们分开，别混成一句话）：
    ① **对照一致率**（机械口径）：引擎实际判类 vs 场景里写的期望型——
       现在就能算，但它**不是误判率**：期望值是"当前共识"不是金标准，
       一致只说明"和当初写的期望一样"；
    ② **误判率**（人工复核口径）：要等人工复核（`--mark` 落笔）做完才报；
       复核没做完就**不报数**（沿用 `--stats` 的既有口径）——半截的复核
       拿来算率只会误导；
    ③ **覆盖缺口**：机械计数，只说明"还差几个场景"，不对场景质量下结论。

诚实边界：
    - **只统计不判定**：本构件不评价"引擎准不准"、不评价"场景好不好"，
      只给计数与比率；"这些数字说明什么"由人判；
    - **不替作者复核**：本构件只读场景表（不改一个字节），`checked` 与
      `review` 永远由作者落笔（有 sha256 不变式守着）；
    - 样本只有几十个场景，**不下对外结论**（不对外报"准确率 X%"）；
    - 误判率未完成复核时报 None 并说明原因，不拿"一致率"冒充。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'summary'|'matrix'|'coverage'|'review'（默认 summary）
        per_type_target: int——每型目标场景数（默认 5）
    输出:
        verdict: str——'summarized'|'mapped'|'covered'|'reviewed'
                        |'input_pending'|'engine_error'
        scenes: int——场景总数
        types: list——矩阵轴（T1..T12，出现新型会补进去）
        matrix: dict——{期望型: {实际型: 个数}}（只列非零格）
        agreement: dict——{'overall': {...}, 'by_type': {...}}
        confusions: list——不一致的格子（含涉及哪些场景），按次数排序
        coverage: dict——{'target', 'count', 'gap', 'total_gap', 'next_to_add'}
        review: dict——{'checked', 'pending', 'state', 'types_untouched',
                        'misclassification_rate', 'rate_note'}
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'per_type_target': 'int?'},
    'out': {'verdict': 'str', 'scenes': 'int', 'types': 'list',
            'matrix': 'dict', 'agreement': 'dict', 'confusions': 'list',
            'coverage': 'dict', 'review': 'dict', 'boundary': 'str'},
}

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TYPES = ['T%d' % i for i in range(1, 13)]      # 判类器的 12 个题型（矩阵轴）
DEFAULT_TARGET = 5                             # 每型目标场景数（路线图里"语料每型补到 5 个"那一项）
_MODES = ('summary', 'matrix', 'coverage', 'review')


def _scenes_module():
    """取场景库（源码仓与安装环境两种路径都认）。"""
    try:
        from engine.scenarios import scenarios as mod
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        import scenarios as mod
    return mod


def _review_state():
    """复核分布（沿用 review_marks 的既有口径）；读不到就诚实给 None。"""
    try:
        try:
            from engine.scenarios.review_marks import review_state
        except ImportError:
            sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
            from review_marks import review_state
        return review_state(), None
    except Exception as e:  # noqa: BLE001——读不到场景表源文件就如实说
        return None, f'复核分布读不到（{type(e).__name__}: {e}）'


def _stats_from(results, scenes, target, state=None, state_why=None, types=None):
    """从**对照结果**算统计（结果可注入：正式测试拿合成数据验矩阵，
    不必真跑控制器；也可在别处复用）。results 每项需有
    id / expect_type / actual_type / passed；scenes 是 {id: 场景}。"""
    types = list(types or TYPES)
    for r in results:                          # 出现 12 型之外的新型就补进轴里
        for t in (r['expect_type'], r['actual_type']):
            if t and t not in types:
                types.append(t)

    matrix, confusions, by_type = {}, {}, {}
    for t in types:
        by_type[t] = {'n': 0, 'match': 0, 'rate': None}
    conf_cells = {}
    for r in results:
        exp, act = r['expect_type'], r['actual_type']
        matrix.setdefault(exp, {})
        matrix[exp][act] = matrix[exp].get(act, 0) + 1
        by_type.setdefault(exp, {'n': 0, 'match': 0, 'rate': None})
        by_type[exp]['n'] += 1
        if exp == act:
            by_type[exp]['match'] += 1
        else:
            conf_cells.setdefault((exp, act), []).append(r['id'])
    for t, d in by_type.items():
        d['rate'] = round(d['match'] / d['n'], 4) if d['n'] else None
    confusions = [{'expect': e, 'actual': a, 'count': len(ids),
                   'scenes': sorted(ids)}
                  for (e, a), ids in conf_cells.items()]
    confusions.sort(key=lambda x: (-x['count'], x['expect'], x['actual']))

    n = len(results)
    match = sum(1 for r in results if r['passed'])
    agreement = {'overall': {'n': n, 'match': match,
                             'rate': round(match / n, 4) if n else None},
                 'by_type': by_type}

    count = {t: 0 for t in types}
    for r in results:
        count[r['expect_type']] = count.get(r['expect_type'], 0) + 1
    gap = {t: max(0, target - count.get(t, 0)) for t in types}
    next_to_add = sorted(({'type': t, 'gap': g} for t, g in gap.items()
                          if g > 0), key=lambda x: (-x['gap'], x['type']))
    coverage = {'target': target, 'count': count, 'gap': gap,
                'total_gap': sum(gap.values()), 'next_to_add': next_to_add}

    checked = sum(1 for r in results
                  if (scenes.get(r['id']) or {}).get('checked'))
    pending = n - checked
    untouched = [t for t in types if not any(
        r['expect_type'] == t and (scenes.get(r['id']) or {}).get('checked')
        for r in results)]
    if pending == 0 and n and state is not None:
        rate = round(state.get('wrong', 0) / n, 4)      # 人工复核口径
        note = ('全部场景已复核：误判率 = 误判-待修 / 场景数；'
                '这是**人工复核口径**，与上面的对照一致率不是一回事。')
    else:
        rate = None
        note = (f'复核未完成（已复核 {checked} / 待复核 {pending}），'
                f'故**不报数**——误判率是人工复核口径（`--mark` 落笔），'
                f'等复核做完再报；现在能给的只有对照一致率'
                f'（机械口径，且期望值是"当前共识"不是金标准）。')
        if state_why:
            note += f'（另：{state_why}）'
    review = {'checked': checked, 'pending': pending, 'state': state,
              'types_untouched': untouched,
              'misclassification_rate': rate, 'rate_note': note}

    return {'scenes': n, 'types': types, 'matrix': matrix,
            'agreement': agreement, 'confusions': confusions,
            'coverage': coverage, 'review': review}


def _build(target):
    """跑一遍场景库，拿对照结果（只读，不改场景表）并算统计。"""
    mod = _scenes_module()
    scenes = {s['id']: s for s in mod.SCENES}
    results = mod.run({'action': 'run'})['scenes']
    state, why = _review_state()
    return _stats_from(results, scenes, target, state, why)


def _boundary(mode, d):
    head = ('语料统计（工程件，不属借鉴区）：只统计不判定——给的是计数与比率，'
            '不评价"引擎准不准"或"场景好不好"。')
    detail = {
        'summary': ('三个口径分开报：①对照一致率＝引擎实际判类 vs 场景写的期望'
                    '（机械口径，**不是误判率**，期望值是"当前共识"不是金标准）；'
                    '②误判率＝人工复核口径，复核没做完就不报数；'
                    '③覆盖缺口＝还差几个场景，不对场景质量下结论。'),
        'matrix': ('混淆矩阵只指向"哪个型容易被判成哪个型"，用来定位该扩的信号表；'
                   '它不表示"判错了"——期望值本身也可能要改（改期望要在 note 记理由）。'),
        'coverage': ('覆盖缺口是机械计数（离每型目标几个）；补哪些场景、场景写成'
                     '什么样是人决定的事，本构件不代替。'),
        'review': ('复核进度只读场景表，**不替作者落笔**（checked / review 由作者'
                   '用 --mark 写）。'),
    }[mode]
    tail = (f'本构件只读不写（场景表一个字节不动）。样本 {d["scenes"]} 个场景，'
            f'规模不足以对外报数，别拿它下一般结论。只诊断不决策。')
    return f'{head}{detail}{tail}'


def _fail(msg):
    return {'verdict': 'input_pending', 'scenes': 0, 'types': [], 'matrix': {},
            'agreement': {}, 'confusions': [], 'coverage': {}, 'review': {},
            'boundary': msg}


def run(inputs):
    """
    做什么：场景库语料统计——一致率 / 混淆矩阵 / 覆盖缺口 / 复核进度。

    返回 dict（见模块 docstring）。
    """
    if not isinstance(inputs, dict):
        return _fail('inputs 必须是 dict')
    mode = inputs.get('mode') or 'summary'
    if mode not in _MODES:
        return _fail('mode 应为 summary/matrix/coverage/review，得到 %r' % (mode,))
    target = inputs.get('per_type_target', DEFAULT_TARGET)
    if not isinstance(target, int) or target < 1:
        return _fail('per_type_target 应是正整数（默认 %d），得到 %r'
                     % (DEFAULT_TARGET, target))
    try:
        d = _build(target)
    except Exception as e:  # noqa: BLE001——真出意外如实报，不假装有统计
        return {'verdict': 'engine_error', 'scenes': 0, 'types': [], 'matrix': {},
                'agreement': {}, 'confusions': [], 'coverage': {}, 'review': {},
                'boundary': '统计跑不动（%s: %s）——不假装有数'
                            % (type(e).__name__, e)}
    out = dict(d)
    out['verdict'] = {'summary': 'summarized', 'matrix': 'mapped',
                      'coverage': 'covered', 'review': 'reviewed'}[mode]
    out['boundary'] = _boundary(mode, d)
    if mode == 'matrix':
        out['agreement'], out['coverage'], out['review'] = {}, {}, {}
    elif mode == 'coverage':
        out['matrix'], out['agreement'], out['review'] = {}, {}, {}
    elif mode == 'review':
        out['matrix'], out['agreement'], out['coverage'] = {}, {}, {}
    return out


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 70)
    print('语料统计构件 · 自测（对照一致率 / 混淆矩阵 / 覆盖缺口 / 复核进度）')
    print('=' * 70)

    r = run({})
    assert r['verdict'] == 'summarized', r
    n = r['scenes']
    assert n >= 10, r
    # 矩阵行和 = 该期望型的场景数；总和 = 场景数
    assert sum(sum(v.values()) for v in r['matrix'].values()) == n, r['matrix']
    assert r['agreement']['overall']['n'] == n, r['agreement']
    print(f"✅ 统计跑通：{n} 个场景；一致 {r['agreement']['overall']['match']}"
          f"（比率 {r['agreement']['overall']['rate']}）")

    # 混淆矩阵与"不一致格子"数目自洽
    off = sum(sum(c for a, c in v.items() if a != e)
              for e, v in r['matrix'].items())
    assert off == sum(c['count'] for c in r['confusions']), (off, r['confusions'])
    assert n - r['agreement']['overall']['match'] == off, r['agreement']
    print(f"✅ 混淆矩阵自洽：不一致 {off} 格，逐格列出（含涉及场景）")

    # 覆盖缺口
    cov = r['coverage']
    assert cov['total_gap'] == sum(cov['gap'].values()), cov
    assert all(cov['gap'][t] == max(0, cov['target'] - cov['count'][t])
               for t in cov['count']), cov
    print(f"✅ 覆盖缺口：目标每型 {cov['target']} 个，还缺 {cov['total_gap']} 个；"
          f"最缺的 {cov['next_to_add'][0]['type']} 缺 {cov['next_to_add'][0]['gap']}")

    # 复核进度 + 误判率口径
    rv = r['review']
    assert rv['checked'] + rv['pending'] == n, rv
    if rv['pending']:
        assert rv['misclassification_rate'] is None and '不报数' in rv['rate_note']
        print(f"✅ 复核未完成（{rv['checked']}/{n}）→ 误判率不报数，"
              f"并说明原因（不拿一致率冒充）")
    else:
        assert rv['misclassification_rate'] is not None
        print(f"✅ 复核已完成 → 误判率（人工口径）= {rv['misclassification_rate']}")

    # 只统计不判定 / 不代签
    assert '只统计不判定' in r['boundary'] and '不替作者落笔' not in r['boundary']
    assert '不替作者落笔' in run({'mode': 'review'})['boundary']
    print('✅ 边界：只统计不判定、不替作者落笔、样本小不对外报数')

    assert run({'mode': 'xx'})['verdict'] == 'input_pending'
    assert run({'per_type_target': 0})['verdict'] == 'input_pending'
    print('✅ 边界：坏 mode / 坏目标数 → 诚实拦截')

    print('=' * 70)
    print('语料统计构件自测：全部通过 ✅')
    print('=' * 70)
