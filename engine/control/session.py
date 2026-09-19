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
           'beliefs': 'list?', 'structured': 'dict?'},
    'out': {'verdict': 'str', 'state': 'dict', 'turn': 'dict?',
            'revision': 'dict?', 'boundary': 'str'},
}

import io
import json
import os
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

def _empty():
    """空会话（每次新建，避免默认值里的列表被多处共享）。"""
    return {'created': None, 'updated': None, 'turns': [], 'walls': [],
            'beliefs': [], 'revisions': []}


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _normalize(data):
    """把读到的 JSON 归一成会话结构：类型不对的字段回落到空值（不猜内容）。"""
    state = _empty()
    if isinstance(data.get('created'), str):
        state['created'] = data['created']
    if isinstance(data.get('updated'), str):
        state['updated'] = data['updated']
    for k in ('turns', 'walls', 'beliefs', 'revisions'):
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
        'created': state['created'],
        'updated': state['updated'],
    }


def _add(state, text, structured=None):
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
                          'verdict': out.get('verdict')})   # 真跑的构件才有
    i = len(state['turns']) + 1
    turn = {
        'i': i, 'text': text, 'type': cls.get('main_type'),
        'type_name': cls.get('main_name'), 'level': cls.get('level'),
        'route': route.get('route_id'), 'confidence': cls.get('confidence'),
        'verdict': r.get('verdict'), 'execution': execution, 'when': _now(),
    }
    state['turns'].append(turn)
    for e in execution:
        # 撞墙族构件**真跑了**才记（没跑就没有，不假装）
        if (e['status'] == 'run'
                and e['component'] in WALL_FAMILY):
            state['walls'].append({'i': i, 'text': text,
                                   'component': e['component'],
                                   'component_verdict': e['verdict']})
    return turn


def _revise(state, new_info, beliefs=None):
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
        'verdict': r['verdict'], 'kept': r['kept'], 'dropped': r['dropped'],
        'beliefs_before': old,          # 真正参与这次修正的集合（可追溯）
        'beliefs_source': '会话' if from_state else '本次传入',
        'beliefs_after': list(state['beliefs']),
        'boundary': r.get('boundary'), 'when': _now(),
    }
    state['revisions'].append(rec)
    return rec, r


def run(inputs):
    """
    做什么：多轮会话——add 记一条诊断 / revise 用新信息修正信念 / state 看汇总
            / reset 清空。

    返回 dict（PORTS['out']）：verdict + state（汇总）+ 可选的 turn/revision +
    boundary。缺参数或状态文件损坏时 verdict='input_pending'/'state_corrupt'
    并给 explanation，不硬做。
    """
    if not isinstance(inputs, dict):
        return _result('input_pending', _summary(_empty()),
                       explanation='inputs 必须是 dict，得到 %s'
                                   % type(inputs).__name__)
    action = inputs.get('action')
    path = inputs.get('path')
    if action not in ('add', 'revise', 'state', 'reset'):
        return _result('input_pending', _summary(_empty()),
                       explanation='action 应为 add/revise/state/reset，'
                                   '得到 %r——诚实拦截' % (action,))
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

    if action == 'reset':
        n = (len(state['turns']), len(state['beliefs']),
             len(state['revisions']))
        state['turns'], state['walls'] = [], []
        state['beliefs'], state['revisions'] = [], []
        state['updated'] = _now()
        _save(path, state)
        return _result('reset_done', _summary(state),
                       explanation='已清空 %d 条轮次 / %d 条信念 / %d 条修正'
                                   '记录（文件保留）' % n)

    if action == 'add':
        text = inputs.get('text')
        if not isinstance(text, str) or not text.strip():
            return _result('input_pending', _summary(state),
                           explanation='add 需要 text（要诊断的材料文本）'
                                       '——不接受空值')
        structured = inputs.get('structured')
        if structured is not None and not isinstance(structured, dict):
            return _result('input_pending', _summary(state),
                           explanation='structured 必须是 dict（结构化线索），'
                                       '得到 %s' % type(structured).__name__)
        turn = _add(state, text.strip(), structured)
        state['updated'] = _now()
        _save(path, state)
        return _result('turn_added', _summary(state), turn=turn)

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
    rec, r = _revise(state, new_info.strip(), beliefs)
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
