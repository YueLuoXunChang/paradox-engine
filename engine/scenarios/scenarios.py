# -*- coding: utf-8 -*-
"""
scenarios.py — 场景库（真实输入 + 期望诊断 + 复核状态）
================================================================
概念来源：45 蓝图轨 B（应用化——场景库目录化：每场景 = 输入文本 +
期望诊断 + 实际输出 + 人工复核标记）+ 回测纪律（判类误判回馈闭环：
场景判错的 → 修信号表 → 回归，T1'是'教训制度化）。

本文件做什么（一句话）：
    收集真实中文问题场景，记录每个场景的期望诊断（判类/复杂度/路由），
    跑引擎对比"实际 vs 期望"——是人验证引擎、也是语料回馈判类器的
    双向工具。

场景字段：
    id: 唯一标识
    title: 场景名
    text: 输入文本（真实中文问题）
    expect_type: 期望主判类（T1-T12）
    expect_level: 期望复杂度（L1/L2/L3）或 None（不校验）
    expect_route: 期望路由 id（如 'R2-L2'）或 None
    structured: dict 或 None——给 controller 的结构化线索（可跑真构件）
    note: 复核备注（人工标记：正确/误判-待修/边界情况）
    checked: bool——是否已人工复核

诚实边界：
    - 期望值是"当前共识"不是"金标准"——场景可随引擎能力演进修正
      （改 expect 需在 note 记录理由）；
    - checked=False 表示尚未人工复核——场景库的价值随复核增长；
    - 场景只做诊断对照，不做决策。
"""

PORTS = {
    'in': {'action': 'str?', 'scene_id': 'str?'},
    'out': {'verdict': 'str', 'scenes': 'list', 'report': 'list',
            'boundary': 'str'},
}

# ══════════════════════════════════════════════════════════════
# 场景注册表（核心）
# ══════════════════════════════════════════════════════════════

SCENES = [
    {
        'id': 'S01',
        'title': '产品需求冲突（销售 vs 研发）',
        'text': ('销售坚持"三周内必须上线抢占市场"，研发坚持"合规审查'
                 '十二周一步不能少"——既要抢占市场，又要完整合规，两边'
                 '都觉得对方在拖后腿。'),
        'expect_type': 'T2', 'expect_level': 'L2', 'expect_route': 'R2-L2',
        'structured': {'A': '抢占市场(3周)', 'B': '完整合规(12周)',
                       'wA': 5, 'wNotA': 5},
        'note': '论证矛盾典型——既要又要 + 冲突词',
        'checked': True,
    },
    {
        'id': 'S02',
        'title': '说谎者句',
        'text': '这句话是假的',
        'expect_type': 'T6', 'expect_level': 'L2',
        'expect_route': 'R6-L2',
        'structured': {'sentence': '这句话是假的'},
        'note': '自指典型——mu2 直判 + 递归修正三态',
        'checked': True,
    },
    {
        'id': 'S03',
        'title': '癌耐药演化建模（学科题）',
        'text': ('肿瘤在靶向药下如何演化出耐药，能否建模其多线路径，'
                 '以及"杀灭敏感株却选择出耐药株"算不算悖论？'),
        'expect_type': 'T9', 'expect_level': 'L3', 'expect_route': 'R9-L3',
        'structured': None,
        'note': '学科题目典型——实体多+演化+悖论扫描',
        'checked': True,
    },
    {
        'id': 'S04',
        'title': '自由 vs 秩序（对立交汇）',
        'text': '要自由还是要秩序，能不能兼得',
        'expect_type': 'T7', 'expect_level': 'L1',
        'expect_route': 'R7-L1',
        'structured': {'wA': 5, 'wNotA': 5},
        'note': '对立交汇——反义对自动判 reverse',
        'checked': True,
    },
    {
        'id': 'S05',
        'title': '天鹅知识更新（黑天鹅）',
        'text': '原来以为所有天鹅都是白的，现在发现澳大利亚有黑天鹅，旧结论还成立吗',
        'expect_type': 'T5', 'expect_level': 'L1', 'expect_route': 'R5-L1',
        'structured': None,
        'note': '知识更新——原来以为/现在发现',
        'checked': False,  # 待人工复核
    },
    {
        'id': 'S06',
        'title': '感冒药疗效（假设检验）',
        'text': '广告说这个感冒药有效率 95%，这个说法靠不靠谱',
        'expect_type': 'T11', 'expect_level': 'L1',
        'expect_route': 'R11-L1',
        'structured': None,
        'note': '假设检验——有效率+靠不靠谱',
        'checked': False,  # 待人工复核
    },
    {
        'id': 'S07',
        'title': '同情与共情（定义辨析）',
        'text': '同情和共情是不是一回事，边界在哪里',
        'expect_type': 'T10', 'expect_level': 'L1',
        'expect_route': 'R10-L1',
        'structured': None,
        'note': '定义辨析——是不是一回事+边界',
        'checked': False,  # 待人工复核
    },
]

# ══════════════════════════════════════════════════════════════
# 场景运行器
# ══════════════════════════════════════════════════════════════


def _get_controller():
    import os
    import sys
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _REPO = os.path.dirname(os.path.dirname(_HERE))
    for _p in (_HERE, _REPO):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from engine.control.controller import run as controller
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'control'))
        from controller import run as controller
    return controller


def run_scene(scene):
    """跑单个场景：判类/复杂度/路由 vs 期望。返回对照结果 dict。"""
    controller = _get_controller()
    r = controller({'text': scene['text'],
                    'structured': scene.get('structured') or {}})
    cl = r['classification']
    actual_type = cl['main_type']
    actual_level = cl['level']
    actual_route = cl['route']['route_id']

    diffs = []
    if actual_type != scene['expect_type']:
        diffs.append(f"判类: 期望 {scene['expect_type']} ≠ 实际 {actual_type}")
    if (scene.get('expect_level') is not None
            and actual_level != scene['expect_level']):
        diffs.append(f"复杂度: 期望 {scene['expect_level']} "
                     f"≠ 实际 {actual_level}")
    if (scene.get('expect_route') is not None
            and actual_route != scene['expect_route']):
        diffs.append(f"路由: 期望 {scene['expect_route']} "
                     f"≠ 实际 {actual_route}")

    return {
        'id': scene['id'], 'title': scene['title'],
        'actual_type': actual_type, 'actual_level': actual_level,
        'actual_route': actual_route,
        'expect_type': scene['expect_type'],
        'checked': scene.get('checked', False),
        'passed': len(diffs) == 0, 'diffs': diffs,
        'report': r['report'],
    }


def run_all(scene_ids=None):
    """跑全部（或指定）场景，返回对照报告。"""
    scenes = [s for s in SCENES
              if scene_ids is None or s['id'] in scene_ids]
    return [run_scene(s) for s in scenes]


def run(inputs):
    """
    做什么：场景库统一入口。
    action='list' → 场景清单；action='run' → 跑全部/指定场景；action='run_one'。
    """
    action = inputs.get('action', 'list')
    if action == 'list':
        return {'verdict': 'listed',
                'scenes': [{'id': s['id'], 'title': s['title'],
                            'text': s['text'],
                            'expect_type': s['expect_type'],
                            'expect_level': s['expect_level'],
                            'expect_route': s['expect_route'],
                            'checked': s.get('checked', False)}
                           for s in SCENES],
                'report': [],
                'boundary': '场景清单：期望值是当前共识非金标准，'
                            '改需在 note 记录理由；checked=False 待人工复核。'}
    if action in ('run', 'run_all'):
        sid = inputs.get('scene_id')
        ids = [sid] if sid else None
        results = run_all(ids)
        passed = sum(1 for r_ in results if r_['passed'])
        return {'verdict': 'ran',
                'scenes': results,
                'report': {
                    'total': len(results), 'passed': passed,
                    'failed': [r_ for r_ in results if not r_['passed']]},
                'boundary': '场景对照=诊断差异报告，不是判决（只诊断不决策）。'}
    return {'verdict': 'input_pending', 'scenes': [], 'report': [],
            'boundary': f"action 应为 list/run，得到 {action!r}——诚实拦截"}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('场景库 · 自测')
    print('=' * 62)

    r1 = run({'action': 'list'})
    assert r1['verdict'] == 'listed' and len(r1['scenes']) == len(SCENES), r1
    print(f"✅ 场景清单 {len(r1['scenes'])} 个")

    r2 = run({'action': 'run'})
    assert r2['verdict'] == 'ran', r2
    total = r2['report']['total']
    passed = r2['report']['passed']
    print(f"✅ 全场景跑：{passed}/{total} 对照通过")
    for f in r2['report']['failed']:
        print(f"   ⚠️ {f['id']} {f['title']}: {'; '.join(f['diffs'])}")

    # 单场景
    r3 = run({'action': 'run', 'scene_id': 'S01'})
    assert r3['verdict'] == 'ran' and len(r3['scenes']) == 1, r3
    assert r3['scenes'][0]['id'] == 'S01', r3
    print(f"✅ 单场景 S01 对照: "
          f"{'通过' if r3['scenes'][0]['passed'] else '有差异'}")

    # 边界
    r4 = run({'action': 'xx'})
    assert r4['verdict'] == 'input_pending', r4
    print('✅ 坏 action → input_pending')

    print('=' * 62)
    print('场景库自测：全部通过 ✅')
    print('=' * 62)
