# -*- coding: utf-8 -*-
"""
session.py — 多轮状态构件（第 0 层总控外围，工作台件）
================================================================
概念来源：轨 C（生态接口：多轮状态）+ 诊断工作台姿态（人拿一批材料来，
一条一条看，跨轮次累积——单次问答记不住前文）。

本构件做什么（一句话）：
    把逐条诊断与信念修正**记在一个会话文件里**——每加一条材料就落一次诊断，
    给出新信息就用 AGM 修正已有信念，随时可看当前状态汇总。

四个 action：
    add     给一段材料 → 跑总控五步 → 追加一条轮次记录（判类/复杂度/路由/
            五步结论/真跑了哪些构件；撞墙管线真跑时另记墙清单）
    revise  给一条新信息 → 用 AGM 最小放弃修正会话里的信念集 → 记这次修正
            （保留什么、放弃什么、新信息进了没有）
    state   看当前状态：轮次、题型分布、墙清单、信念集、修正历史
    reset   清空这个会话（文件保留，记录清零）

状态文件：调用方给的 path 上的一个 JSON（默认不写任何路径——必须显式给，
    免得悄悄在别人仓库里落文件）。写入用「临时文件 + 替换」，写一半断电也
    不会得到半个 JSON。

诚实边界：
    - 本构件只**记录**引擎自己的输出，不二次加工、不补结论（只诊断不决策更
      不替人记事）；
    - 新信息与旧信念冲突时，结论以 AGM 构件为准：它说不可满足就不写进信念集，
      它说算不动（undecided）就标算不动（**算不动 ≠ 不一致**，不许当不一致用）；
    - 状态文件损坏 / 不是 JSON / 不是对象 → 诚实报错，**不覆盖**原文件；
    - 会话是工作台账，不是知识库：文件里的信念集只代表"这个会话里记过的"。
"""

PORTS = {
    'in': {'action': 'str', 'path': 'str?', 'text': 'str?', 'new_info': 'str?',
           'beliefs': 'list?', 'structured': 'dict?', 'text_file': 'str?',
           'split': 'str?', 'max_segs': 'int?', 'max_seg_chars': 'int?',
           'out_file': 'str?', 'overwrite': 'bool?', 'scene_id': 'str?',
           'turn': 'int?', 'clues': 'bool?'},
    'out': {'verdict': 'str', 'state': 'dict', 'turn': 'dict?',
            'revision': 'dict?', 'imported': 'dict?', 'markdown': 'str?',
            'reviews': 'list?', 'overview': 'dict?',
            'boundary': 'str'},
}

import io
import json
import os
import re
import sys
import tempfile
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

try:
    from engine.control.controller import run as controller_run
    from engine.cold.agm_revision import run as agm_run
except ImportError:  # 直接运行时按平级导入
    sys.path.insert(0, _HERE)
    sys.path.insert(0, os.path.join(_REPO, 'engine', 'cold'))
    from controller import run as controller_run  # noqa: E402
    from agm_revision import run as agm_run  # noqa: E402

BOUNDARY = ('会话是工作台账：只记录引擎自己的输出（判类/五步结论/AGM 修正结果），'
            '不补结论、不替人记事；算不动 ≠ 不一致。引擎只诊断不决策。')

# 撞墙族构件：真跑了才记进墙清单（没跑就没有，不假装）
WALL_FAMILY = ('wall_pipeline', 'boundary_paradox', 'selfref_fixpoint',
               'counterpoint_gen')

# 构件输出里值得落账的标量字段（都是引擎自己产出的，不另做解释）
_DETAIL_KEYS = ('verdict', 'mu', 'grade', 'drill', 'converges',
                'selfref_type', 'tension', 'mode')


def _detail(out):
    """从构件输出里抽标量字段（含 diagnosis 里的五选一诊断 label）。"""
    d = {}
    for k in _DETAIL_KEYS:
        v = out.get(k)
        if v is not None and isinstance(v, (str, int, float, bool)):
            d[k] = v
    diag = out.get('diagnosis')
    if isinstance(diag, dict):
        if isinstance(diag.get('label'), str):
            d['diagnosis_label'] = diag['label']
        for k in ('mu', 'grade', 'drill', 'tension'):
            v = diag.get(k)
            if v is not None and isinstance(v, (str, int, float, bool)):
                d.setdefault(k, v)
    return d

def _empty():
    """空会话（每次新建，避免默认值里的列表被多处共享）。"""
    return {'created': None, 'updated': None, 'turns': [], 'walls': [],
            'beliefs': [], 'revisions': [], 'reviews': [],
            'snapshots': []}


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _normalize(data):
    """把读到的 JSON 归一成会话结构：类型不对的字段回落到空值（不猜内容）。"""
    state = _empty()
    if isinstance(data.get('created'), str):
        state['created'] = data['created']
    if isinstance(data.get('updated'), str):
        state['updated'] = data['updated']
    for k in ('turns', 'walls', 'beliefs', 'revisions', 'reviews',
              'snapshots'):
        v = data.get(k)
        if isinstance(v, list):
            state[k] = v
    return state


def _load(path):
    """读会话文件；不存在→None；路径非法→IsADirectoryError；
    内容损坏→ValueError（都由调用方诚实报错，绝不覆盖原文件）。"""
    if not os.path.exists(path):
        return None
    if os.path.isdir(path):
        raise IsADirectoryError('path 是目录，不是会话文件：%s' % path)
    with io.open(path, encoding='utf-8') as fh:
        raw = fh.read()
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError('会话文件不是合法 JSON（不覆盖原文件）：%s' % exc)
    if not isinstance(data, dict):
        raise ValueError('会话文件顶层不是对象（不覆盖原文件）')
    return _normalize(data)


def _write_text(path, text, overwrite=False):
    """写文本（临时文件 + 替换）。目标已存在且没开 overwrite → 拒绝覆盖。"""
    if os.path.isdir(path):
        raise IsADirectoryError('导出路径是目录，不是文件：%s' % path)
    if os.path.exists(path) and not overwrite:
        raise FileExistsError('导出目标已存在（没开覆盖就不动它）：%s' % path)
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.session-', suffix='.tmp')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _save(path, state):
    """临时文件 + 替换：写一半中断也不会留下半个 JSON。"""
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.session-', suffix='.tmp')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(state, ensure_ascii=False, indent=2))
            fh.write('\n')
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _result(verdict, state, **extra):
    out = {'verdict': verdict, 'state': state, 'boundary': BOUNDARY}
    out.update(extra)
    return out


def _summary(state):
    """状态汇总（给 state action 与 CLI 看）。"""
    per_type = {}
    for t in state['turns']:
        per_type[t['type']] = per_type.get(t['type'], 0) + 1
    walls = [w for w in state['walls']]
    return {
        'turns': len(state['turns']),
        'turn_list': list(state['turns']),
        'per_type': dict(sorted(per_type.items())),
        'wall_events': walls,
        'wall_count': len(walls),
        'beliefs': state['beliefs'],
        'revisions': state['revisions'],
        'reviews': len(state['reviews']),
        'snapshots': len(state['snapshots']),
        'review_list': list(state['reviews']),
        'created': state['created'],
        'updated': state['updated'],
    }


def _clues(text):
    """跑线索建议，压成能落账的小结构；跑不了就照实记 None。"""
    try:
        from engine.control.clue_suggester import run as suggest
    except ImportError:
        try:
            sys.path.insert(0, _HERE)
            from clue_suggester import run as suggest  # noqa: E402
        except ImportError as exc:
            return {'verdict': 'unavailable', 'why': '建议器读不到（%s）'
                                            % exc, 'ready': {},
                    'need_human': []}
    r = suggest({'text': text})
    ready, need = {}, []
    for c in r['components']:
        for s in c['ready']:
            ready.setdefault(s['key'], s['value'])
        for x in c['need_human']:
            if x['key'] not in need:
                need.append(x['key'])
    return {'verdict': r['verdict'], 'ready': ready,
            'need_human': need, 'note': '启发式建议，要人确认；'
                                        '引擎不产生逻辑式，也不自动应用'}


def _add(state, text, structured=None, clues=False):
    inputs = {'text': text}
    if structured:
        inputs['structured'] = structured
    r = controller_run(inputs)
    cls = r.get('classification') or {}
    route = cls.get('route') or {}
    execution = []
    for e in (r.get('execution') or []):
        out = e.get('output') if isinstance(e.get('output'), dict) else {}
        execution.append({'step': e.get('step'), 'component': e.get('component'),
                          'status': e.get('status'),
                          'verdict': out.get('verdict'),    # 真跑的构件才有
                          'note': e.get('note') or '',
                          'detail': _detail(out) if out else {}})
    i = len(state['turns']) + 1
    turn = {
        'i': i, 'text': text, 'type': cls.get('main_type'),
        'type_name': cls.get('main_name'), 'level': cls.get('level'),
        'route': route.get('route_id'), 'confidence': cls.get('confidence'),
        'verdict': r.get('verdict'), 'execution': execution, 'when': _now(),
    }
    if clues:
        turn['clues'] = _clues(text)   # 建议而已，落账不等于落库
    state['turns'].append(turn)
    for e in execution:
        # 撞墙族构件**真跑了**才记（没跑就没有，不假装）
        if (e['status'] == 'run'
                and e['component'] in WALL_FAMILY):
            det = e.get('detail') or {}
            state['walls'].append({'i': i, 'text': text,
                                   'component': e['component'],
                                   'component_verdict': e['verdict'],
                                   'diagnosis_label': det.get(
                                       'diagnosis_label'),
                                   'mu': det.get('mu'),
                                   'grade': det.get('grade')})
    return turn


def _revise(state, new_info, beliefs=None, turn=None):
    from_state = beliefs is None
    old = list(state['beliefs'] if from_state else beliefs)
    if not old:
        return None, {'verdict': 'input_pending',
                      'boundary': '会话里还没有信念集：先用 add 记材料，'
                                  '或直接给 beliefs（旧的信念列表）——不硬推'}
    r = agm_run({'mode': 'revise', 'beliefs': old, 'new_info': new_info})
    if r['verdict'] == 'revised':
        state['beliefs'] = list(r['kept'])          # kept 已含 new_info
    elif r['verdict'] == 'consistent':
        state['beliefs'] = old + ([new_info] if new_info not in old else [])
    # 其余情形（new_info_unsatisfiable / undecided / size_limit）信念集不动
    rec = {
        'i': len(state['revisions']) + 1, 'new_info': new_info,
        'source_turn': turn,          # 这次修正挂在第几条材料上（可空）
        'verdict': r['verdict'], 'kept': r['kept'], 'dropped': r['dropped'],
        'beliefs_before': old,          # 真正参与这次修正的集合（可追溯）
        'beliefs_source': '会话' if from_state else '本次传入',
        'beliefs_after': list(state['beliefs']),
        'boundary': r.get('boundary'), 'when': _now(),
    }
    state['revisions'].append(rec)
    return rec, r


def _split_material(raw, mode='para'):
    """把一整篇材料切成段：para=按空行分段（默认）；line=按行。

    返回 (segments, skipped_empty)——只丢掉**空白**段，其余一律保留
    （宁可多切，也不悄悄替作者删内容）。
    """
    if mode == 'line':
        parts = raw.split('\n')
    else:
        parts = re.split(r'\n[ \t]*\n', raw)
    segs, empty = [], 0
    for p in parts:
        s = p.strip()
        if not s:
            empty += 1
            continue
        segs.append(s)
    return segs, empty


def _add_file(state, text_file, mode='para', max_segs=200,
              max_seg_chars=2000, clues=False):
    """整篇材料逐段诊断并记账；返回 (导入明细, 未处理明细) 或 (None, 错误)。"""
    if not isinstance(text_file, str) or not text_file.strip():
        return None, {'verdict': 'input_pending',
                      'boundary': 'add_file 需要 text_file（材料文件路径）'}
    if not os.path.exists(text_file):
        return None, {'verdict': 'input_pending',
                      'boundary': '材料文件不存在：%s' % text_file}
    if os.path.isdir(text_file):
        return None, {'verdict': 'input_pending',
                      'boundary': 'text_file 是目录，不是材料文件：%s'
                                  % text_file}
    if mode not in ('para', 'line'):
        return None, {'verdict': 'input_pending',
                      'boundary': "split 应为 para/line，得到 %r——诚实拦截"
                                  % (mode,)}
    try:
        # utf-8-sig：材料文件带 BOM 时不要把它当成正文第一个字
        with io.open(text_file, encoding='utf-8-sig') as fh:
            raw = fh.read()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        return None, {'verdict': 'input_pending',
                      'boundary': '读材料失败（要 UTF-8 文本）：%s' % exc}
    segs, empty = _split_material(raw, mode)
    if not segs:
        return None, {'verdict': 'file_empty',
                      'boundary': '材料里没有非空段落：%s' % text_file}

    imported, skipped = [], []
    for k, s in enumerate(segs):
        if len(imported) >= max_segs:
            skipped.append({'seg': k + 1, 'reason': 'max_segs',
                            'chars': len(s),
                            'head': s[:24]})
            continue
        if len(s) > max_seg_chars:
            skipped.append({'seg': k + 1, 'reason': 'too_long',
                            'chars': len(s), 'head': s[:24]})
            continue
        turn = _add(state, s, None, clues)
        imported.append({'i': turn['i'], 'seg': k + 1, 'chars': len(s),
                         'head': s[:24], 'type': turn['type'],
                         'level': turn['level'], 'verdict': turn['verdict']})
    return {'imported': imported, 'skipped': skipped,
            'skipped_empty_blocks': empty, 'segments': len(segs)}, None


def _scene_rows(scene_id='all'):
    """跑场景对照并收集复核依据（与 CLI --review 同一套口径：期望 vs 实际 +
    判类命中信号）。返回 (rows, 错误)。"""
    try:
        from engine.scenarios.scenarios import SCENES, run as scenes_run
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        try:
            from scenarios import SCENES, run as scenes_run  # noqa: E402
        except ImportError as exc:
            return None, '场景库读不到（%s）——诚实拦截，不假装复核过' % exc
    try:
        from engine.control.classifier import run as classifier_run
    except ImportError as exc:
        return None, '判类器读不到（%s）' % exc
    ids = [s['id'] for s in SCENES]
    if scene_id not in (None, '', 'all'):
        if scene_id not in ids:
            return None, ('场景 %s 不存在——可用：%s（或 all=全部）'
                          % (scene_id, '、'.join(ids)))
    smap = {s['id']: s for s in SCENES}
    results = scenes_run({'action': 'run',
                          'scene_id': None if scene_id in (None, '', 'all')
                          else scene_id})['scenes']
    rows = []
    for x in results:
        s = smap[x['id']]
        c = classifier_run({'text': s['text']})
        rows.append({
            'scene': x['id'], 'title': x['title'],
            'expect': '%s-%s' % (s['expect_type'], s['expect_level']),
            'actual': '%s-%s' % (x['actual_type'], x['actual_level']),
            'passed': bool(x['passed']), 'diffs': x['diffs'],
            'signals': c['types'][0]['signals'] if c['types'] else [],
            'confidence': c['confidence'],
            'ran': sum(1 for e in (x.get('execution') or [])
                       if e.get('status') == 'run'),
        })
    return rows, None


def _add_reviews(state, scene_id='all'):
    """把场景复核依据记进会话（只记引擎输出，不替作者下结论）。"""
    rows, err = _scene_rows(scene_id)
    if rows is None:
        return None, err
    recs = []
    for row in rows:
        rec = dict(row)
        rec['i'] = len(state['reviews']) + len(recs) + 1
        rec['when'] = _now()
        recs.append(rec)
    state['reviews'].extend(recs)
    return recs, None


def _review_mark_of(scene_id):
    """读场景当前的复核标记（读不到就如实说读不到，不编）。"""
    try:
        from engine.scenarios.scenarios import SCENES
    except ImportError:
        try:
            sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
            from scenarios import SCENES  # noqa: E402
        except ImportError:
            return None
    for s in SCENES:
        if s['id'] == scene_id:
            return {'checked': bool(s.get('checked')),
                    'review': s.get('review') or ''}
    return None


OVERVIEW_BOUNDARY = (
    '汇总只对**引擎自己产出的标签**做计数与分组（判类/复杂度/置信度/构件状态），'
    '不做相似度聚类、不推断材料同源、不替人下结论；低置信度就是低置信度，'
    '照样列出来给人看。')


T5_BOUNDARY = (
    '引擎**不抽公式**：自然语言→逻辑式自动提取不在本引擎范围。判成 T5（知识更新）'
    '的轮次只说明「这段材料像新旧断言冲突」，要进信念集仍得人把命题式给出来'
    '（`--revise "¬Q" --turn N`），修正走 AGM 构件。')


def _clue_stats(state):
    """线索建议落账统计：多少条有建议、还欠哪些键（只统计）。"""
    ready, need, pending = {}, {}, []
    for t in state['turns']:
        c = t.get('clues')
        if not c:
            continue
        for k, v in (c.get('ready') or {}).items():
            ready[k] = ready.get(k, 0) + 1
        for k in (c.get('need_human') or []):
            need[k] = need.get(k, 0) + 1
        if c.get('need_human'):
            pending.append(t['i'])
    return {'turns_with_clues': sum(1 for t in state['turns']
                                     if t.get('clues')),
            'ready_keys': dict(sorted(ready.items())),
            'need_human_keys': dict(sorted(need.items())),
            'turns_pending_clues': pending,
            'note': '线索建议只是建议：落账不等于落库，'
                    '要真跑构件仍得把它写进 --structured'}


def _t5_link(state):
    """T5 材料与信念集的对接情况（只报事实，不替人补内容）。"""
    t5 = [t['i'] for t in state['turns'] if t['type'] == 'T5']
    linked = {}
    for r in state['revisions']:
        st = r.get('source_turn')
        if st:
            linked.setdefault(st, []).append(r['i'])
    return {
        't5_turns': t5,
        'linked': {str(k): v for k, v in sorted(linked.items())},
        't5_linked': [i for i in t5 if i in linked],
        't5_pending': [i for i in t5 if i not in linked],
        'boundary': T5_BOUNDARY,
    }


def _overview(state):
    """批次汇总：按引擎自己的标签分组计数（只统计，不判断）。"""
    per_type, by_type, levels = {}, {}, {}
    conf, ran, not_ran, walls = {}, {}, {}, {}
    lows = []
    for t in state['turns']:
        per_type[t['type']] = per_type.get(t['type'], 0) + 1
        by_type.setdefault(t['type'], []).append(t['i'])
        lv = t.get('level') or '—'
        levels[lv] = levels.get(lv, 0) + 1
        c = t.get('confidence') or '—'
        conf[c] = conf.get(c, 0) + 1
        if c == 'low':
            lows.append(t['i'])
        for e in t['execution']:
            if e['status'] == 'run':
                ran[e['component']] = ran.get(e['component'], 0) + 1
            else:
                key = '%s：%s' % (e['status'], (e.get('note') or '')[:40])
                not_ran[key] = not_ran.get(key, 0) + 1
    for w in state['walls']:
        key = '%s → %s' % (w['component'],
                           w.get('component_verdict') or '—')
        walls[key] = walls.get(key, 0) + 1
    return {
        'turns': len(state['turns']),
        'per_type': dict(sorted(per_type.items())),
        'by_type': {k: v for k, v in sorted(by_type.items())},
        'levels': dict(sorted(levels.items())),
        'confidence': dict(sorted(conf.items())),
        'low_confidence_turns': lows,
        'components_ran': dict(sorted(ran.items())),
        'not_ran_reasons': dict(sorted(not_ran.items())),
        'walls': dict(sorted(walls.items())),
        'reviews': len(state['reviews']),
        'snapshots': len(state['snapshots']),
        'beliefs': len(state['beliefs']),
        'revisions': len(state['revisions']),
        'clues': _clue_stats(state),
        't5': _t5_link(state),
        'boundary': OVERVIEW_BOUNDARY,
    }


def _overview_md(ov):
    """汇总的 Markdown 版（台账用）。"""
    L = ['## 批次汇总（只统计引擎自己的标签）', '']
    L.append('- 轮次 %d · 复核记录 %d 条 · 信念 %d 条 · 修正 %d 次'
             % (ov['turns'], ov['reviews'], ov['beliefs'], ov['revisions']))
    if ov['per_type']:
        L.append('- 判类分布：' + ' · '.join(
            '%s %d 条（轮次 %s）' % (k, v, '、'.join(str(i) for i in
                                                   ov['by_type'][k]))
            for k, v in ov['per_type'].items()))
    if ov['levels']:
        L.append('- 复杂度分布：' + ' · '.join(
            '%s %d 条' % kv for kv in ov['levels'].items()))
    if ov['confidence']:
        L.append('- 判类置信度：' + ' · '.join(
            '%s %d 条' % kv for kv in ov['confidence'].items()))
    if ov['low_confidence_turns']:
        L.append('- 置信度低（分类存疑，建议人看）：轮次 %s'
                 % '、'.join(str(i) for i in ov['low_confidence_turns']))
    if ov['components_ran']:
        L.append('- 真跑过构件：' + ' · '.join(
            '%s ×%d' % kv for kv in ov['components_ran'].items()))
    if ov['not_ran_reasons']:
        L.append('- 没跑的原因（引擎自己给的说明，按原文归组）：')
        for k, v in ov['not_ran_reasons'].items():
            L.append('  - ×%d %s' % (v, k))
    if ov['walls']:
        L.append('- 墙事件：' + ' · '.join('%s ×%d' % kv
                                       for kv in ov['walls'].items()))
    cl = ov.get('clues') or {}
    if cl.get('turns_with_clues'):
        L.append('- 线索建议：%d 条轮次有建议' % cl['turns_with_clues'])
        if cl.get('ready_keys'):
            L.append('  - 可直接用：' + ' · '.join(
                '%s×%d' % kv for kv in cl['ready_keys'].items()))
        if cl.get('need_human_keys'):
            L.append('  - 还欠人给：' + ' · '.join(
                '%s×%d' % kv for kv in cl['need_human_keys'].items()))
        if cl.get('turns_pending_clues'):
            L.append('  - 仍欠线索的轮次：%s'
                     % '、'.join(str(i) for i in
                                 cl['turns_pending_clues']))
        L.append('  - %s' % cl['note'])
    t5 = ov.get('t5') or {}
    if t5.get('t5_turns'):
        L.append('- T5（知识更新）材料：轮次 %s'
                 % '、'.join(str(i) for i in t5['t5_turns']))
        L.append('  - 已接信念集：%s'
                 % ('、'.join(str(i) for i in t5['t5_linked']) or '无'))
        L.append('  - 还欠命题式：%s'
                 % ('、'.join(str(i) for i in t5['t5_pending']) or '无'))
        L.append('  - %s' % t5['boundary'])
    L.append('- %s' % ov['boundary'])
    L.append('')
    return L


WORKSHEET_BOUNDARY = (
    '工作单只做**拼装**：能建议的照抄原文，欠的键留成 `<待填>` 空位——'
    '引擎不猜值、不填数、不产生逻辑式；填完后要不要真跑由人决定。')


def _registry_snapshot(registry_path=None):
    """读场景表当前复核状态（只读）。读不到就诚实抛，不编。"""
    try:
        from engine.scenarios.review_marks import marks, review_state
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        from review_marks import marks, review_state  # noqa: E402
    mk = marks(registry_path)
    if not mk:
        raise ValueError('场景表里没解析到任何场景（0 个）'
                         '——不像场景表，不编进度')
    return {'total': len(mk), 'checked': sum(1 for v in mk.values()
                                             if v['checked']),
            'unchecked': sum(1 for v in mk.values() if not v['checked']),
            'distribution': review_state(registry_path),
            'pending_ids': [k for k, v in mk.items() if not v['checked']],
            'checked_ids': [k for k, v in mk.items() if v['checked']]}


def _progress(state, registry_path=None):
    """记一次复核进度快照，并与上一次快照比出「这次新复核了哪些 / 退回了哪些」。"""
    snap = _registry_snapshot(registry_path)
    prev = state['snapshots'][-1] if state['snapshots'] else None
    if prev:
        was = set(prev.get('checked_ids') or [])
        now = set(snap['checked_ids'])
        snap['newly_checked'] = sorted(now - was)
        snap['newly_reverted'] = sorted(was - now)
        snap['delta_checked'] = snap['checked'] - prev['checked']
    else:
        snap['newly_checked'] = []
        snap['newly_reverted'] = []
        snap['delta_checked'] = None
    snap['i'] = len(state['snapshots']) + 1
    snap['when'] = _now()
    state['snapshots'].append(snap)
    return snap


BRIEF_ENGINE_CAN = (
    '--suggest 看线索建议', '--pending 生成欠线索工作单',
    '--overview 看批次汇总', '--export 导台账', '--progress 记复核进度快照',
    '--review --board 看复核看板')
BRIEF_HUMAN_ONLY = (
    '把工作单里的 <待填> 换成你的值（引擎不猜数）',
    'T5（知识更新）材料的命题式（引擎不抽公式）',
    '逐条落笔：--mark S05 --verdict ok|wrong|edge',
    '是否推远端 / 打 tag / 定 LICENSE 口径')


def _brief_md(state, session_path=None):
    """一页简报：把会话里已有的记录汇总成"现在什么状态、下一步能干什么"。"""
    ov = _overview(state)
    cl = ov.get('clues') or {}
    t5 = ov.get('t5') or {}
    snaps = state['snapshots']
    last = snaps[-1] if snaps else None
    L = ['# 诊断简报（paradox-engine）', '']
    L.append('- 生成时间：%s' % _now())
    if session_path:
        L.append('- 会话文件：`%s`' % session_path)
    L.append('- 一句话状态：轮次 %d · 欠线索 %d 条 · 待复核 %d 个 · '
             '复核快照 %d 次'
             % (ov['turns'], len(cl.get('turns_pending_clues') or []),
                (last or {}).get('unchecked', 0), len(snaps)))
    L.append('')
    L.append('## 这批材料（引擎判出来的）')
    L.append('')
    if not state['turns']:
        L.append('- 还没有材料轮次。')
    else:
        L.append('- 判类分布：%s'
                 % ' · '.join('%s %d 条' % kv
                              for kv in ov['per_type'].items()))
        if ov['levels']:
            L.append('- 复杂度：%s' % ' · '.join('%s %d 条' % kv
                                             for kv in ov['levels'].items()))
        if ov['low_confidence_turns']:
            L.append('- 判类置信度低（建议人看）：轮次 %s'
                     % '、'.join(str(i) for i in ov['low_confidence_turns']))
        if ov['components_ran']:
            L.append('- 真跑过构件：%s'
                     % ' · '.join('%s ×%d' % kv
                                  for kv in ov['components_ran'].items()))
        if ov['walls']:
            L.append('- 墙事件：%s' % ' · '.join('%s ×%d' % kv
                                              for kv in ov['walls'].items()))
    L.append('')
    L.append('## 欠什么（需人给的）')
    L.append('')
    owed = False
    if cl.get('need_human_keys'):
        owed = True
        L.append('- 线索还欠：%s（仍欠的轮次 %s）'
                 % (' · '.join('%s×%d' % kv
                               for kv in cl['need_human_keys'].items()),
                    '、'.join(str(i) for i in
                              cl.get('turns_pending_clues') or []) or '无'))
    if t5.get('t5_pending'):
        owed = True
        L.append('- T5（知识更新）还欠命题式：轮次 %s'
                 % '、'.join(str(i) for i in t5['t5_pending']))
    if not owed:
        L.append('- 目前没有欠项（或者还没跑过 --clues：那就先跑一次）。')
    L.append('')
    L.append('## 复核到哪了')
    L.append('')
    if last:
        d = last.get('delta_checked')
        L.append('- 最近一次快照（%s）：已复核 %d / 待复核 %d%s'
                 % (last['when'], last['checked'], last['unchecked'],
                    '（第 1 次）' if d is None else '（较上次 %+d）' % d))
        if last.get('newly_checked'):
            L.append('- 上次之后新复核：%s' % '、'.join(last['newly_checked']))
        if last.get('pending_ids'):
            L.append('- 仍待复核：%s' % '、'.join(last['pending_ids']))
    else:
        L.append('- 还没记过快照——`--progress` 记一次，之后能看出进度变化。')
    if state['reviews']:
        L.append('- 会话里已记 %d 条复核依据（`--review` 落的）。'
                 % len(state['reviews']))
    L.append('')
    L.append('## 下一步')
    L.append('')
    L.append('- 引擎能做：%s' % ' · '.join(BRIEF_ENGINE_CAN))
    L.append('- 只有你能做：')
    for h in BRIEF_HUMAN_ONLY:
        L.append('  - %s' % h)
    L.append('')
    L.append('## 边界')
    L.append('')
    L.append('- %s' % BOUNDARY)
    L.append('- 简报只汇总会话里已记下的东西：不推断材料同源、不替人下结论；'
             '上面"只有你能做"那几件引擎不会代做。')
    L.append('')
    return '\n'.join(L)


def _worksheet(state):
    """欠线索工作单：把待补的轮次拼成可粘贴清单（值由人填）。"""
    pending, no_clues, ready_only = [], [], []
    for t in state['turns']:
        cl = t.get('clues')
        if not cl:
            no_clues.append(t)
            continue
        need = list(cl.get('need_human') or [])
        if need:
            pending.append((t, cl, need))
        elif cl.get('ready'):
            ready_only.append(t)
    if not pending and not no_clues:
        return None, {'pending': 0, 'no_clues': 0, 'ready_only':
                      len(ready_only)}

    L = ['# 欠线索工作单（paradox-engine 会话）', '']
    L.append('- 生成时间：%s' % _now())
    L.append('- 待你填的轮次：%d 条 · 还没跑建议器的轮次：%d 条 · '
             '线索已齐的轮次：%d 条'
             % (len(pending), len(no_clues), len(ready_only)))
    L.append('')
    if pending:
        L.append('## 待你填（可直接用的照抄原文，欠的键留空）')
        L.append('')
    for t, cl, need in pending:
        L.append('### 轮次 %d · %s %s（%s/%s）'
                 % (t['i'], t['type'], t.get('type_name') or '',
                    t['level'], t['route']))
        L.append('')
        L.append('- 材料原文：%s' % t['text'].replace('\n', ' '))
        if cl.get('ready'):
            L.append('- 可直接用（建议，照原文用词）：%s'
                     % '、'.join('%s=%r' % kv
                                for kv in cl['ready'].items()))
        L.append('- 待你填：%s'
                 % '、'.join('%s=<待填>' % k for k in need))
        merged = dict(cl.get('ready') or {})
        for k in need:
            merged[k] = '<待填>'
        L.append('- 填好后可粘贴（把 <待填> 换成你的值）：')
        L.append('')
        L.append('  `paradox-engine --text %s --structured %s`'
                 % (json.dumps(t['text'], ensure_ascii=False),
                    json.dumps(json.dumps(merged, ensure_ascii=False),
                               ensure_ascii=False)))
        L.append('')
    if no_clues:
        L.append('## 还没跑建议器（可加 --clues 补）')
        L.append('')
        L.append('- 轮次：%s'
                 % '、'.join(str(t['i']) for t in no_clues))
        L.append('')
        L.append('  `paradox-engine --session 会话文件 --add "材料" --clues`'
                 '（或对已有会话重新导材料时带 --clues）')
        L.append('')
    if ready_only:
        L.append('## 线索已齐（可直接照 --suggest 的建议跑）')
        L.append('')
        L.append('- 轮次：%s' % '、'.join(str(t['i']) for t in ready_only))
        L.append('')
    L.append('## 边界')
    L.append('')
    L.append('- %s' % WORKSHEET_BOUNDARY)
    L.append('')
    return '\n'.join(L), {'pending': len(pending), 'no_clues': len(no_clues),
                          'ready_only': len(ready_only)}


def _report_md(state, session_path=None):
    """把会话导成 Markdown 台账：**只写记过的东西**，没跑的照实标。"""
    st = _summary(state)
    L = ['# 诊断台账（paradox-engine 会话）', '']
    L.append('- 导出时间：%s' % _now())
    if session_path:
        L.append('- 会话文件：`%s`' % session_path)
    L.append('- 规模：轮次 %d · 墙事件 %d · 信念 %d 条 · 修正 %d 次 · '
             '复核记录 %d 条'
             % (st['turns'], st['wall_count'], len(st['beliefs']),
                len(st['revisions']), len(state['reviews'])))
    if st['created']:
        L.append('- 会话建立：%s（末次更新 %s）' % (st['created'],
                                              st['updated'] or '—'))
    L.append('')
    if not state['turns']:
        L.append('> 这个会话里还没有轮次——空台账，不编内容。')
        L.append('')
    L.extend(_overview_md(_overview(state)))

    if st['per_type']:
        L.append('## 题型分布')
        L.append('')
        L.append('| 题型 | 条数 |')
        L.append('|:--|--:|')
        for t, n in st['per_type'].items():
            L.append('| %s | %d |' % (t, n))
        L.append('')

    if state['turns']:
        L.append('## 逐条诊断')
        L.append('')
        L.append('| # | 判类 | 复杂度 | 路由 | 五步结论 | 真跑/没跑 | 材料（开头） |')
        L.append('|--:|:--|:--|:--|:--|:--|:--|')
        for t in state['turns']:
            ran = sum(1 for e in t['execution'] if e['status'] == 'run')
            pend = len(t['execution']) - ran
            head = t['text'].replace('\n', ' ')[:30].replace('|', '\\|')
            L.append('| %d | %s %s | %s | %s | %s | %d/%d | %s |'
                     % (t['i'], t['type'], t.get('type_name') or '',
                        t['level'], t['route'], t['verdict'], ran, pend, head))
        L.append('')
        for t in state['turns']:
            L.append('### %d. %s %s（%s，%s）'
                     % (t['i'], t['type'], t.get('type_name') or '', t['level'],
                        t['route']))
            L.append('')
            L.append('- 五步结论：`%s`（判类置信度 %s）'
                     % (t['verdict'], t.get('confidence') or '—'))
            L.append('- 材料原文：')
            L.append('')
            for line in (t['text'] or '').split('\n'):
                L.append('  > %s' % line)
            L.append('')
            cl_t = t.get('clues')
            if cl_t:
                L.append('- 线索建议（%s）：' % cl_t.get('verdict'))
                for k, v in (cl_t.get('ready') or {}).items():
                    L.append('  - %s = %r（建议，照原文用词）' % (k, v))
                if cl_t.get('need_human'):
                    L.append('  - 需人给：%s'
                             % '、'.join(cl_t['need_human']))
                L.append('')
            if t['execution']:
                L.append('- 管线：')
                for e in t['execution']:
                    pieces = ['%s：%s' % (e['component'],
                                          '真跑' if e['status'] == 'run'
                                          else '没跑')]
                    if e.get('verdict'):
                        pieces.append('→ %s' % e['verdict'])
                    det = {k: v for k, v in (e.get('detail') or {}).items()
                           if k not in ('diagnosis_label', 'verdict')}
                    if det:
                        pieces.append('[' + ' '.join('%s=%s' % kv
                                                     for kv in det.items())
                                      + ']')
                    if e.get('note'):
                        pieces.append('（%s）' % e['note'])
                    L.append('  - ' + ' '.join(pieces))
                    label = (e.get('detail') or {}).get('diagnosis_label')
                    if label:
                        L.append('    - 五选一诊断：%s' % label)
                L.append('')

    if state['walls']:
        L.append('## 墙事件（撞墙族构件真跑过才记）')
        L.append('')
        L.append('| 轮次 | 构件 | 构件自己的 verdict | 五选一诊断 |')
        L.append('|--:|:--|:--|:--|')
        for w in state['walls']:
            L.append('| %s | %s | %s | %s |'
                     % (w['i'], w['component'],
                        w.get('component_verdict') or '—',
                        (w.get('diagnosis_label') or '—')
                        .replace('|', '\\|')))
        L.append('')

    if state['snapshots']:
        L.append('## 复核进度快照（每次一条，可与上次对比）')
        L.append('')
        for s in state['snapshots']:
            d = s.get('delta_checked')
            delta = '（第 1 次）' if d is None else '（较上次 %+d）' % d
            L.append('- %s #%d：已复核 %d / 待复核 %d %s'
                     % (s['when'], s['i'], s['checked'], s['unchecked'],
                        delta))
            if s.get('newly_checked'):
                L.append('  - 新复核：%s' % '、'.join(s['newly_checked']))
            if s.get('newly_reverted'):
                L.append('  - 退回待复核：%s' % '、'.join(s['newly_reverted']))
            if s.get('pending_ids'):
                L.append('  - 仍待复核：%s' % '、'.join(s['pending_ids']))
        L.append('')
        L.append('> 快照读的是场景表**当时**的状态，只记事实；'
                 '落笔仍是作者的判断（`--mark`）。')
        L.append('')

    if state['reviews']:
        L.append('## 场景复核记录（复核时的引擎依据）')
        L.append('')
        L.append('| # | 场景 | 期望 | 实际 | 对照 | 判类命中 | 真跑件数 | 当前复核标记 |')
        L.append('|--:|:--|:--|:--|:--|:--|--:|:--|')
        for r in state['reviews']:
            mark = _review_mark_of(r['scene'])
            if mark is None:
                mark_txt = '—（场景表读不到）'
            elif mark['checked']:
                mark_txt = '已复核：%s' % (mark['review'] or '（无记录）')
            else:
                mark_txt = '待复核'
            sig = '、'.join(r.get('signals') or []) or '—'
            L.append('| %d | %s %s | %s | %s | %s | %s | %d | %s |'
                     % (r['i'], r['scene'], r['title'].replace('|', '\\|'),
                        r['expect'], r['actual'],
                        '符合' if r['passed'] else '不符',
                        sig.replace('|', '\\|'), r.get('ran') or 0,
                        mark_txt.replace('|', '\\|')))
        L.append('')
        bad = [r for r in state['reviews'] if not r['passed']]
        if bad:
            L.append('判定与期望不符的场景（差异照实记，不改期望值）：')
            L.append('')
            for r in bad:
                for d in (r.get('diffs') or []):
                    L.append('- %s：%s' % (r['scene'], d))
            L.append('')
        L.append('> 标记一栏读的是场景表当前的复核状态；会话只记依据，'
                 '「正确 / 误判 / 边界」仍是人的判断（`--mark` 落笔）。')
        L.append('')

    if state['beliefs']:
        L.append('## 当前信念集')
        L.append('')
        for b in state['beliefs']:
            L.append('- %s' % b)
        L.append('')

    if state['revisions']:
        L.append('## 信念修正史')
        L.append('')
        for r in state['revisions']:
            src = ('（挂在轮次 %d）' % r['source_turn']
                   if r.get('source_turn') else '')
            L.append('- 第 %d 次（%s）：新信息「%s」%s'
                     % (r['i'], r['verdict'], r['new_info'], src))
            L.append('  - 保留 %s / 放弃 %s（旧集合来自%s）'
                     % (r['kept'], r['dropped'],
                        r.get('beliefs_source') or '—'))
            L.append('  - 修正前 %s → 修正后 %s'
                     % (r.get('beliefs_before'), r.get('beliefs_after')))
        L.append('')

    L.append('## 边界')
    L.append('')
    L.append('- ' + BOUNDARY)
    L.append('- 台账里每条都是引擎自己的输出（判类/五步结论/构件 verdict），'
             '没有二次加工；「没跑」就是没跑，原因照实记在管线里。')
    L.append('')
    return '\n'.join(L)


def run(inputs):
    """
    做什么：多轮会话——add 记一条诊断 / add_file 整篇材料逐段诊断 /
            revise 用新信息修正信念 / state 看汇总 / reset 清空。

    返回 dict（PORTS['out']）：verdict + state（汇总）+ 可选的 turn/revision/
    imported + boundary。缺参数或状态文件损坏时 verdict='input_pending'/
    'state_corrupt' 并给 explanation，不硬做。
    """
    if not isinstance(inputs, dict):
        return _result('input_pending', _summary(_empty()),
                       explanation='inputs 必须是 dict，得到 %s'
                                   % type(inputs).__name__)
    action = inputs.get('action')
    path = inputs.get('path')
    if action not in ('add', 'add_file', 'revise', 'state', 'reset',
                      'report', 'review', 'overview',
                      'worksheet', 'progress', 'brief'):
        return _result('input_pending', _summary(_empty()),
                       explanation='action 应为 add/add_file/revise/state/'
                                   'reset/report/review/overview/worksheet/progress，得到 %r——诚实拦截'
                                   % (action,))
    if not isinstance(path, str) or not path.strip():
        return _result('input_pending', _summary(_empty()),
                       explanation='必须给 path（会话文件路径）——不会悄悄'
                                   '在别处落文件，故诚实拦截')

    try:
        state = _load(path)
    except IsADirectoryError as exc:
        return _result('path_invalid', _summary(_empty()),
                       explanation=str(exc))
    except ValueError as exc:
        return _result('state_corrupt', _summary(_empty()),
                       explanation=str(exc))
    fresh = state is None
    if fresh:
        if action in ('state', 'reset'):
            if action == 'state':
                return _result('empty_session', _summary(_empty()),
                               explanation='会话文件还不存在：%s' % path)
            return _result('input_pending', _summary(_empty()),
                           explanation='会话还不存在，没有可清空的东西：%s'
                                       % path)
        state = _empty()
        state['created'] = _now()

    if action == 'state':
        return _result('state', _summary(state))

    if action == 'brief':
        out_file = inputs.get('out_file')
        if out_file is not None and not isinstance(out_file, str):
            return _result('input_pending', _summary(state),
                           explanation='out_file 必须是字符串路径（或 "-" '
                                       '表示只在结果里返回文本）')
        empty = not (state['turns'] or state['reviews'] or state['snapshots']
                     or state['beliefs'] or state['revisions'])
        md = _brief_md(state, path)
        if empty:
            return _result('nothing_to_report', _summary(state),
                           markdown=md,
                           explanation='会话是空的——简报会是一页空白，'
                                       '不编内容；先用 --add/--add-file 记材料、'
                                       '--review 记依据、--progress 记进度')
        if out_file in (None, '-'):
            return _result('brief', _summary(state), markdown=md,
                           explanation='简报已生成（%d 字），未写文件' % len(md))
        target = os.path.abspath(out_file)
        if target == os.path.abspath(path):
            return _result('input_pending', _summary(state),
                           explanation='导出目标不能是会话文件本身——诚实拦截')
        try:
            _write_text(target, md, bool(inputs.get('overwrite')))
        except IsADirectoryError as exc:
            return _result('path_invalid', _summary(state),
                           explanation=str(exc), markdown=md)
        except FileExistsError as exc:
            return _result('file_exists', _summary(state),
                           explanation=str(exc), markdown=md)
        except (IOError, OSError) as exc:
            return _result('input_pending', _summary(state),
                           explanation='写简报失败：%s' % exc, markdown=md)
        return _result('brief_written', _summary(state), markdown=md,
                       explanation='简报已写入 %s（%d 字）' % (target, len(md)))

    if action == 'progress':
        try:
            snap = _progress(state, inputs.get('registry_path'))
        except Exception as exc:  # noqa: BLE001  读不到场景表就诚实报
            return _result('registry_unreadable', _summary(state),
                           explanation='场景表读不到（%s）——不编进度' % exc)
        state['updated'] = _now()
        _save(path, state)
        if snap['delta_checked'] is None:
            note = ('第 1 次快照：已复核 %d / 待复核 %d（之后每次快照'
                    '会告诉你又复核了哪些）'
                    % (snap['checked'], snap['unchecked']))
        else:
            note = ('已复核 %d / 待复核 %d（较上次 %+d；新复核 %s；退回 %s）'
                    % (snap['checked'], snap['unchecked'],
                       snap['delta_checked'],
                       '、'.join(snap['newly_checked']) or '无',
                       '、'.join(snap['newly_reverted']) or '无'))
        return _result('snapshot_taken', _summary(state), snapshot=snap,
                       explanation=note)

    if action == 'worksheet':
        out_file = inputs.get('out_file')
        if out_file is not None and not isinstance(out_file, str):
            return _result('input_pending', _summary(state),
                           explanation='out_file 必须是字符串路径（或 "-" '
                                       '表示只在结果里返回文本）')
        md, stats = _worksheet(state)
        if md is None:
            return _result('nothing_to_do', _summary(state),
                           worksheet=None, stats=stats,
                           explanation='没有欠线索的轮次（也还有 %d 条没跑'
                                       '建议器）——不生成空工作单'
                                       % stats['no_clues'])
        if out_file in (None, '-'):
            return _result('worksheet', _summary(state), markdown=md,
                           stats=stats,
                           explanation='工作单已生成（待填 %d 条 / 未跑建议器 '
                                       '%d 条），未写文件'
                                       % (stats['pending'], stats['no_clues']))
        target = os.path.abspath(out_file)
        if target == os.path.abspath(path):
            return _result('input_pending', _summary(state),
                           explanation='导出目标不能是会话文件本身——诚实拦截')
        try:
            _write_text(target, md, bool(inputs.get('overwrite')))
        except IsADirectoryError as exc:
            return _result('path_invalid', _summary(state),
                           explanation=str(exc), markdown=md)
        except FileExistsError as exc:
            return _result('file_exists', _summary(state),
                           explanation=str(exc), markdown=md)
        except (IOError, OSError) as exc:
            return _result('input_pending', _summary(state),
                           explanation='写工作单失败：%s' % exc, markdown=md)
        return _result('worksheet_written', _summary(state), markdown=md,
                       stats=stats,
                       explanation='工作单已写入 %s（%d 字）'
                                   % (target, len(md)))

    if action == 'overview':
        ov = _overview(state)
        if not state['turns'] and not state['reviews']:
            return _result('empty_session', _summary(state),
                           overview=ov,
                           explanation='会话里还没有东西可汇总——'
                                       '先用 --add/--add-file 记材料，'
                                       '或 --review 记复核依据')
        return _result('overview', _summary(state), overview=ov)

    if action == 'reset':
        n = (len(state['turns']), len(state['beliefs']),
             len(state['revisions']), len(state['reviews']))
        state['turns'], state['walls'] = [], []
        state['beliefs'], state['revisions'] = [], []
        state['reviews'] = []
        state['updated'] = _now()
        _save(path, state)
        return _result('reset_done', _summary(state),
                       explanation='已清空 %d 条轮次 / %d 条信念 / %d 条修正 / '
                                   '%d 条复核记录（文件保留）' % n)

    if action == 'add':
        text = inputs.get('text')
        if not isinstance(text, str) or not text.strip():
            return _result('input_pending', _summary(state),
                           explanation='add 需要 text（要诊断的材料文本）'
                                       '——不接受空值')
        clues = bool(inputs.get('clues'))
        structured = inputs.get('structured')
        if structured is not None and not isinstance(structured, dict):
            return _result('input_pending', _summary(state),
                           explanation='structured 必须是 dict（结构化线索），'
                                       '得到 %s' % type(structured).__name__)
        turn = _add(state, text.strip(), structured, clues)
        state['updated'] = _now()
        _save(path, state)
        return _result('turn_added', _summary(state), turn=turn)

    if action == 'add_file':
        max_segs = inputs.get('max_segs', 200)
        max_chars = inputs.get('max_seg_chars', 2000)
        for name, v in (('max_segs', max_segs), ('max_seg_chars', max_chars)):
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                return _result('input_pending', _summary(state),
                               explanation='%s 必须是正整数，得到 %r'
                                           '——诚实拦截' % (name, v))
        res, err = _add_file(state, inputs.get('text_file'),
                             inputs.get('split') or 'para', max_segs,
                             max_chars, bool(inputs.get('clues')))
        if err is not None:
            return _result(err['verdict'], _summary(state),
                           explanation=err['boundary'])
        state['updated'] = _now()
        _save(path, state)
        skipped = res['skipped']
        verdict = 'turns_added' if not skipped else 'turns_added_partial'
        note = ('导入 %d 段（跳过空白段 %d）'
                % (len(res['imported']), res['skipped_empty_blocks']))
        if skipped:
            why = {}
            for s in skipped:
                why[s['reason']] = why.get(s['reason'], 0) + 1
            note += ('；未处理 %d 段（%s）——没有静默截断'
                     % (len(skipped),
                        '、'.join('%s×%d' % (k, v) for k, v in why.items())))
        return _result(verdict, _summary(state), imported=res,
                       explanation=note)

    if action == 'report':
        out_file = inputs.get('out_file')
        overwrite = inputs.get('overwrite', False)
        if out_file is not None and not isinstance(out_file, str):
            return _result('input_pending', _summary(state),
                           explanation='out_file 必须是字符串路径（或 "-" '
                                       '表示只在结果里返回文本）')
        md = _report_md(state, path)
        if not (state['turns'] or state['beliefs'] or state['revisions']
                or state['reviews'] or state['snapshots']):
            return _result('nothing_to_report', _summary(state),
                           markdown=md,
                           explanation='会话是空的——导出会得到空台账，'
                                       '不编内容；先用 --add / --add-file 记材料，'
                                       '或用 --review / --progress 记复核依据与进度')
        if out_file in (None, '-'):
            return _result('report_ready', _summary(state), markdown=md,
                           explanation='台账已生成（%d 字），未写文件'
                                       % len(md))
        target = os.path.abspath(out_file)
        if target == os.path.abspath(path):
            return _result('input_pending', _summary(state),
                           explanation='导出目标不能是会话文件本身（会把它'
                                       '覆盖掉）——诚实拦截')
        try:
            _write_text(target, md, bool(overwrite))
        except IsADirectoryError as exc:
            return _result('path_invalid', _summary(state),
                           explanation=str(exc), markdown=md)
        except FileExistsError as exc:
            return _result('file_exists', _summary(state),
                           explanation=str(exc), markdown=md)
        except (IOError, OSError) as exc:
            return _result('input_pending', _summary(state),
                           explanation='写台账失败：%s' % exc, markdown=md)
        return _result('report_written', _summary(state), markdown=md,
                       explanation='台账已写入 %s（%d 字）' % (target, len(md)))

    if action == 'review':
        scene_id = inputs.get('scene_id', 'all')
        if scene_id is not None and not isinstance(scene_id, str):
            return _result('input_pending', _summary(state),
                           explanation='scene_id 必须是字符串（如 S01 或 all），'
                                       '得到 %s' % type(scene_id).__name__)
        recs, err = _add_reviews(state, scene_id or 'all')
        if recs is None:
            return _result('input_pending', _summary(state), explanation=err)
        state['updated'] = _now()
        _save(path, state)
        n_ok = sum(1 for r in recs if r['passed'])
        return _result('reviews_added', _summary(state), reviews=recs,
                       explanation='记下 %d 个场景的复核依据（判定符合期望 %d / '
                                   '需人看 %d）——引擎只把依据摆出来，'
                                   '结论仍是人的判断'
                                   % (len(recs), n_ok, len(recs) - n_ok))

    # revise
    new_info = inputs.get('new_info')
    if not isinstance(new_info, str) or not new_info.strip():
        return _result('input_pending', _summary(state),
                       explanation='revise 需要 new_info（新信息文本）'
                                   '——不接受空值')
    beliefs = inputs.get('beliefs')
    if beliefs is not None and not isinstance(beliefs, list):
        return _result('input_pending', _summary(state),
                       explanation='beliefs 必须是列表，得到 %s'
                                   % type(beliefs).__name__)
    turn = inputs.get('turn')
    if turn is not None:
        if isinstance(turn, bool) or not isinstance(turn, int):
            return _result('input_pending', _summary(state),
                           explanation='turn 必须是轮次编号（整数），'
                                       '得到 %s' % type(turn).__name__)
        if not 1 <= turn <= len(state['turns']):
            return _result('input_pending', _summary(state),
                           explanation='轮次 %d 不存在（当前 1~%d）——'
                                       '不挂到不存在的材料上'
                                       % (turn, len(state['turns'])))
    rec, r = _revise(state, new_info.strip(), beliefs, turn)
    if rec is None:
        return _result('input_pending', _summary(state),
                       explanation=r['boundary'])
    state['updated'] = _now()
    _save(path, state)
    return _result('belief_revised', _summary(state), revision=rec)


def _selftest():
    import shutil
    d = tempfile.mkdtemp(prefix='pe_session_')
    p = os.path.join(d, 's.json')
    try:
        assert run({'action': 'state', 'path': p})['verdict'] == 'empty_session'
        r1 = run({'action': 'add', 'path': p, 'text': '这句话是假的'})
        assert r1['verdict'] == 'turn_added' and r1['turn']['type'] == 'T6', r1
        r2 = run({'action': 'add', 'path': p, 'text': '产品既要快又要稳'})
        assert r2['state']['turns'] == 2, r2['state']
        r3 = run({'action': 'revise', 'path': p,
                  'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
        assert r3['verdict'] == 'belief_revised', r3
        assert r3['revision']['dropped'] == ['P→Q'], r3['revision']
        r4 = run({'action': 'state', 'path': p})
        assert r4['state']['turns'] == 2 and r4['state']['beliefs'], r4
        r5 = run({'action': 'revise', 'path': p, 'new_info': '¬Q'})
        assert r5['verdict'] == 'belief_revised', r5
        r6 = run({'action': 'reset', 'path': p})
        assert r6['verdict'] == 'reset_done' and r6['state']['turns'] == 0
        print('✅ add 记轮次 / revise 修正信念 / state 汇总 / reset 清空')
        print('✅ 缺参、action 非法、path 缺失均诚实拦截')
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    _selftest()
