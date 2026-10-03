# -*- coding: utf-8 -*-
"""
review_marks.py — 场景复核落笔（把人的复核判断写回场景表）
================================================================
概念来源：轨 B 应用化（场景库目录化 + 复核纪律「人验证引擎」）。

本文件做什么（一句话）：
    把人工复核结论写回 engine/scenarios/scenarios.py 的目标场景条目——
    作者跑 --review 看完「期望 vs 实际」后，用 --mark 落笔记录，不必手改
    Python 源码（手改容易碰坏字面量、也容易把行尾改回 CRLF）。

写回什么（只碰这两个字段）：
    checked: bool —— 是否已人工复核
    review:  str —— 复核记录，形如 '正确（2026-09-07）：期望与实际一致'

结论取值：
    ok       → checked=True  记录「正确」
    wrong    → checked=True  记录「误判-待修」（已复核，但判定与期望不符）
    edge     → checked=True  记录「边界情况」（判类存疑，人工裁定保留）
    pending  → checked=False 清除 review 记录（回到待复核）

诚实边界：
    - 这里只记录**人的判断**，引擎不替人下结论（只诊断不决策）；
    - 场景 id 不存在、结论取值非法、找不到 checked 字段 → 诚实报错，
      文件一个字节都不改；
    - 只改目标场景那一段，其余字节原样保留（含 LF 行尾）。
"""

import io
import os
import re
import datetime

# 结论取值 → 复核记录里的中文说法
VERDICTS = {
    'ok': '正确',
    'wrong': '误判-待修',
    'edge': '边界情况',
}

_HERE = os.path.dirname(os.path.abspath(__file__))
SCENES_PATH = os.path.join(_HERE, 'scenarios.py')

_CHECKED_RE = re.compile(r"(\n[ \t]*)'checked':[ \t]*(True|False),[ \t]*(#[^\n]*)?")
_REVIEW_RE = re.compile(r"\n[ \t]*'review':[^\n]*")

PORTS = {
    'in': {'scene_id': 'str（场景 id，如 S05）', 'verdict': "str（'ok'|'wrong'|'edge'）",
           'note': 'str?', 'path': 'str?（缺省改 engine/scenarios/scenarios.py）',
           'when': 'str?（复核时间戳文本）'},
    'out': {'ok': 'bool', 'changed': 'bool', 'scene': 'str?', 'verdict': 'str?',
            'checked': 'bool?', 'error': 'str?', 'review': 'str?',
            'boundary': 'str（只有写入路径带；只读视图只返回数据本身）'},
}
BOUNDARY = (
    '本件只改场景表里的**复核标记字段**（`checked` / `review`），不动场景正文与判据；'
    '写入是**原地改写同一个文件**，改前请确认在干净工作区（或已有备份）；'
    '替换处数与预期不符时**直接拦下不猜**（`checked 字段替换数异常`）。'
    '两个只读视图（`marks` / `review_state`）只返回数据本身，不塞 boundary 键——'
    '硬塞会把标记结构改形，读的人反而要绕一层。'
)


def _error(msg, scene_id=None):
    return {'ok': False, 'changed': False, 'scene': scene_id,
            'verdict': None, 'checked': None, 'error': msg,
            'boundary': BOUNDARY}


def _block_range(text, scene_id):
    """目标场景在源码里的字符区间 [start, end)；找不到返回 None。"""
    anchor = "'id': '%s'," % scene_id
    i = text.find(anchor)
    if i < 0:
        return None, anchor
    j = text.find('\n    {\n', i)
    if j < 0:
        j = len(text)
    return (i, j), anchor


def _quote(value):
    """写成 Python 单引号字面量（转义反斜杠与单引号）。"""
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"


def mark_scene(scene_id, verdict, note='', path=None, when=None):
    """把复核结论写回场景表；返回结构化结果（不抛异常）。"""
    path = path or SCENES_PATH
    if not isinstance(scene_id, str) or not scene_id.strip():
        return _error('必须给场景 id（如 S05）——不接受空值')
    if scene_id.strip() == 'all':
        return _error('落笔一次只能记一个场景——不接受 all（复核是逐个看的）',
                      scene_id)
    if verdict not in VERDICTS and verdict != 'pending':
        return _error('结论取值非法：%r——可用 ok / wrong / edge / pending'
                      % (verdict,), scene_id)
    if not isinstance(note, str):
        return _error('复核备注必须是字符串（当前 %s）' % type(note).__name__,
                      scene_id)
    note = note.strip().replace('\n', ' ')
    scene_id = scene_id.strip()

    try:
        with io.open(path, encoding='utf-8', newline='') as fh:
            text = fh.read()
    except (IOError, OSError) as exc:
        return _error('读场景表失败：%s' % exc, scene_id)

    rng, anchor = _block_range(text, scene_id)
    if rng is None:
        ids = re.findall(r"'id': '([A-Z0-9]+)'", text)
        return _error('场景 %s 不存在——可用：%s'
                      % (scene_id, '、'.join(ids) or '（空）'), scene_id)
    start, end = rng
    block = text[start:end]
    if not _CHECKED_RE.search(block):
        return _error('场景 %s 的条目里找不到 checked 字段——不猜，直接拦下'
                      % scene_id, scene_id)

    checked = verdict != 'pending'
    if checked:
        day = when or datetime.date.today().isoformat()
        value = '%s（%s）' % (VERDICTS[verdict], day)
        if note:
            value += '：' + note
        review_line = "\n        'review': %s," % _quote(value)
    else:
        review_line = ''

    # 先清掉旧 review 行，再写 checked，最后把新 review 行插在 checked 之前
    new_block = _REVIEW_RE.sub('', block)
    new_block, n = _CHECKED_RE.subn(
        (lambda m: "%s'checked': %s," % (m.group(1), 'True' if checked else 'False')),
        new_block)
    if n != 1:
        return _error('checked 字段替换数异常（%d 处）——不猜，直接拦下' % n,
                      scene_id)
    if review_line:
        new_block = _CHECKED_RE.sub(
            (lambda m: review_line + m.group(0)), new_block)
    new_text = text[:start] + new_block + text[end:]

    if new_text == text:
        return {'ok': True, 'changed': False, 'scene': scene_id,
                'verdict': verdict, 'checked': checked, 'error': None,
                'boundary': BOUNDARY}

    try:
        with io.open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(new_text)
    except (IOError, OSError) as exc:
        return _error('写场景表失败：%s' % exc, scene_id)

    return {'ok': True, 'changed': True, 'scene': scene_id, 'verdict': verdict,
            'checked': checked, 'error': None, 'review': review_line.strip()
            or '（清除复核记录）', 'boundary': BOUNDARY}


def marks(path=None):
    """每个场景当前的复核标记：{id: {'checked': bool, 'review': str}}。

    只读——用于进度快照/看板这类"读现状"的地方，不碰文件。
    """
    path = path or SCENES_PATH
    with io.open(path, encoding='utf-8', newline='') as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"'id': '([A-Z0-9]+)',", text):
        sid = m.group(1)
        j = text.find('\n    {\n', m.start())
        block = text[m.start():j if j > 0 else len(text)]
        cm = _CHECKED_RE.search(block)
        checked = bool(cm) and cm.group(2) == 'True'
        rm = re.search(r"'review': '([^'\n]*)'", block)
        out[sid] = {'checked': checked, 'review': rm.group(1) if rm else ''}
    return out


def review_state(path=None):
    """当前复核分布：{'ok': n, 'wrong': n, 'edge': n, 'pending': n}。"""
    path = path or SCENES_PATH
    with io.open(path, encoding='utf-8', newline='') as fh:
        text = fh.read()
    state = {'ok': 0, 'wrong': 0, 'edge': 0, 'pending': 0}
    for block in re.split(r"\n    \{\n", text)[1:]:
        if not _CHECKED_RE.search(block):
            continue
        if 'False' in _CHECKED_RE.search(block).group(2):
            state['pending'] += 1
            continue
        marked = None
        for key, label in VERDICTS.items():
            if ("'review': '" + label) in block:
                marked = key
                break
        state[marked or 'ok'] += 1
    return state


if __name__ == '__main__':
    try:
        sys_stdout = __import__('sys').stdout
        if hasattr(sys_stdout, 'reconfigure'):
            sys_stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    st = review_state()
    print('场景表复核分布：正确 %d / 误判-待修 %d / 边界情况 %d / 待复核 %d'
          % (st['ok'], st['wrong'], st['edge'], st['pending']))
    print('落笔：python engine/scenarios/review_marks.py 只读；'
          '写回请用 paradox-engine --mark S05 --verdict ok')
