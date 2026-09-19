# -*- coding: utf-8 -*-
"""
clue_suggester.py — 结构化线索建议（第 0 层总控外围，工作台件）
================================================================
概念来源：诊断工作台姿态的**第 0 米摩擦**——总控执行需要结构化线索才真跑构件，
而线索要人手写 JSON；人得先看懂 PORTS 才能用，门槛卡在最前面。

本文件做什么（一句话）：
    看一段中文材料，按**实际路由**列出每个构件要什么，能从不改字的原文里指出来的
    就给出建议（连依据一起给），指不出来的照实说"需人给"——然后把可用部分拼成
    一条**可粘贴**的命令，人不改就不生效。

建议的依据（都是文本层面，不产生逻辑式）：
    A / B（矛盾两方）   ← 命中「既要…又要…」「一方面…另一方面…」这类句式
    wall / wall_name    ← 由上面 A/B 拼成的一句话描述
    thesis / antithesis ← 同上（对位创生要的正是两方）
    sentence（自指类型）← 命中「这句话是假的 / 真话者 / 哥德尔」这类自指短语

诚实边界：
    - 建议是**启发式**，每项都带 why 与 is_guess=True，**要人确认**；
    - **不产生逻辑式**：premises/conclusion/formula/facts/rules/query 一律列进
      need_human（自然语言→逻辑式不在本引擎范围）；
    - **不给人下判断的值**：证据权重 wA/wNotA 这类"这是多少"的量，不替人估；
    - 建议**不自动应用**：本构件只返回文本与片段，写不写进 --structured 由人决定。
"""

PORTS = {
    'in': {'text': 'str?'},
    'out': {'verdict': 'str', 'route': 'str?', 'components': 'list',
            'paste': 'dict', 'boundary': 'str'},
}

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

try:
    from engine.control.classifier import run as classifier_run
    from engine.control.controller import ADAPTER_SPECS
except ImportError:  # 直接运行时按平级导入
    sys.path.insert(0, _HERE)
    from classifier import run as classifier_run  # noqa: E402
    from controller import ADAPTER_SPECS  # noqa: E402

BOUNDARY = (
    '建议是启发式、要人确认：每项都写了依据；引擎**不产生逻辑式**（premises/'
    'conclusion/formula/facts/rules/query 一律需人给），也不替人估证据权重；'
    '建议不会自动应用——拼好的片段由人决定用不用。引擎只诊断不决策。')

# 建议不出来的键：写清为什么（这些是"命题内容"或"人的判断"，不是文本模式）
NEED_HUMAN_REASON = {
    'premises': '命题式（引擎不抽公式）',
    'conclusion': '命题式（引擎不抽公式）',
    'formula': '命题式（引擎不抽公式）',
    'facts': '命题式（引擎不抽公式）',
    'rules': '命题式（引擎不抽公式）',
    'query': '命题式（引擎不抽公式）',
    'defaults': '默认规则（人的判断）',
    'exceptions': '例外（人的判断）',
    'new_info': '新信息（人的判断）',
    'beliefs': '信念集（人的判断）',
    'wA': '证据权重是人的判断，引擎不替人估',
    'wNotA': '证据权重是人的判断，引擎不替人估',
    'A': '矛盾两方要用原文里的话（没命中句式时需人给）',
    'B': '矛盾两方要用原文里的话（没命中句式时需人给）',
    'wall': '墙的描述需人给（没命中句式时）',
    'wall_name': '墙名需人给（没命中句式时）',
    'thesis': '正题需人给（没命中句式时）',
    'antithesis': '反题需人给（没命中句式时）',
    'sentence': '自指句类型需人给（没命中自指短语时）',
}

_PAIR_PATTERNS = (
    (r'既要(.{1,20}?)又要(.{1,20}?)(?:[，。；,;]|$)', '命中「既要…又要…」句式'),
    (r'一方面(.{1,20}?)[，,]?\s*另一方面(.{1,20}?)(?:[，。；,;]|$)',
     '命中「一方面…另一方面…」句式'),
    (r'既想(.{1,20}?)又想(.{1,20}?)(?:[，。；,;]|$)', '命中「既想…又想…」句式'),
)

_SENTENCE_PATTERNS = (
    (r'这句话是假的|本句为假|说谎者|我是假的', 'liar', '命中「这句话是假的」类自指'),
    (r'这句话是真的|本句为真|真话者', 'truth_teller', '命中「这句话是真的」类自指'),
    (r'哥德尔|不可证明|不可证', 'godel', '命中「哥德尔/不可证明」说法'),
)


def _suggest_ab(text):
    for pat, why in _PAIR_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip(), m.group(2).strip(), why
    return None, None, None


def _suggest_sentence(text):
    for pat, val, why in _SENTENCE_PATTERNS:
        if re.search(pat, text):
            return val, why
    return None, None


def _sugg(component, key, value, why):
    return {'component': component, 'key': key, 'value': value, 'why': why,
            'is_guess': True}


def run(inputs):
    """
    做什么：给一段文本，按实际路由列出每个构件要什么结构化线索——能建议的给
            建议（带依据），给不出的说清为什么；再拼一条可粘贴的命令。

    返回 dict（PORTS['out']）：verdict + route + components（逐构件）+ paste +
    boundary。文本缺失/类型不对 → verdict='input_pending'，不硬猜。
    """
    if not isinstance(inputs, dict):
        return {'verdict': 'input_pending', 'route': None, 'components': [],
                'paste': {}, 'boundary': BOUNDARY}
    text = inputs.get('text')
    if not isinstance(text, str) or not text.strip():
        return {'verdict': 'input_pending', 'route': None, 'components': [],
                'paste': {}, 'boundary': BOUNDARY}
    text = text.strip()

    cls = classifier_run({'text': text})
    route = cls['route']
    a, b, ab_why = _suggest_ab(text)
    sent, sent_why = _suggest_sentence(text)

    components, paste = [], {}
    for comp in route['pipeline']:
        spec = ADAPTER_SPECS.get(comp)
        if spec is None:
            components.append({'component': comp, 'hint': '未映射构件',
                               'ready': [], 'need_human': [], 'has_defaults':
                               False})
            continue
        _mod, keys, hint, defaults, _hook = spec
        ready, need = [], []
        for k in keys:
            if k == 'A' and a:
                ready.append(_sugg(comp, 'A', a, ab_why))
            elif k == 'B' and b:
                ready.append(_sugg(comp, 'B', b, ab_why))
            elif k == 'thesis' and a:
                ready.append(_sugg(comp, 'thesis', a, ab_why))
            elif k == 'antithesis' and b:
                ready.append(_sugg(comp, 'antithesis', b, ab_why))
            elif k in ('wall', 'wall_name') and a and b:
                ready.append(_sugg(comp, k, '%s 与 %s 同时要求' % (a, b),
                                   '由命中句式的两方拼出（照原文用词）'))
            elif k == 'sentence' and sent:
                ready.append(_sugg(comp, 'sentence', sent, sent_why))
            else:
                need.append({'key': k,
                             'reason': NEED_HUMAN_REASON.get(
                                 k, '需人给（引擎不猜）')})
        if ready:
            paste[comp] = {s['key']: s['value'] for s in ready}
        components.append({'component': comp, 'hint': hint, 'ready': ready,
                           'need_human': need,
                           'has_defaults': bool(defaults)})

    verdict = 'suggested' if any(c['ready'] for c in components) else \
        'no_suggestion'
    return {'verdict': verdict, 'route': route['route_id'],
            'pipeline': route['pipeline'], 'components': components,
            'paste': paste, 'text': text, 'boundary': BOUNDARY}


def _selftest():
    r = run({'text': '产品既要三周上线又要十二周合规，销售和研发各执一词'})
    assert r['verdict'] == 'suggested', r
    keys = [s['key'] for c in r['components'] for s in c['ready']]
    assert 'A' in keys and 'B' in keys, r
    assert all(s['is_guess'] and s['why'] for c in r['components']
               for s in c['ready']), r
    assert run({'text': 5})['verdict'] == 'input_pending'
    r2 = run({'text': '自由与秩序能不能兼得'})
    assert r2['verdict'] in ('suggested', 'no_suggestion'), r2
    assert any(x['key'] == 'wA' for c in r2['components']
               for x in c['need_human']), r2
    print('✅ 建议器自测：句式建议、权重不替人估、参数拦截都走通')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    _selftest()
