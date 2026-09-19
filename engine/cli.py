# -*- coding: utf-8 -*-
"""
cli.py — paradox-engine 命令行入口（AI 挂载层 · 阶段 6 扩展）
================================================================
用法：
    python -m engine.cli --text "产品既要快又要稳"          # 中文诊断报告
    python -m engine.cli --text "..." --json                 # 结构化 JSON
    python -m engine.cli --file 输入.txt                     # 从文件读文本
    python -m engine.cli --demo                              # 完整演示（demo.py）
    python -m engine.cli --scenarios                         # 列场景库（含复核状态）
    python -m engine.cli --scene S01                         # 跑单场景：期望 vs 实际
    python -m engine.cli --scene all --json                  # 全部场景，结构化输出
    python -m engine.cli --review                            # 复核模式：期望 vs 实际
    python -m engine.cli --mark S05 --verdict ok             # 复核落笔（写回场景表）
    python -m engine.cli --session 会话.json --add "文本"     # 多轮会话：记一条
    python -m engine.cli --session 会话.json --session-state  # 看会话汇总
    paradox-engine --text "..."                              # 安装后 console 命令

做什么：
    把总控五步流水线接到命令行——传一段问题文本，输出中文诊断报告
    （或 JSON），给人看 / 给脚本用 / 给 AI 管道用。

诚实边界：
    - 需要结构化线索才能真跑构件的场景，缺线索会诚实报"缺结构化输入"
      （与 controller 一致，不伪造）；
    - 只诊断不决策：报告结尾带边界声明。
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from engine._console import ensure_utf8_console
except ImportError:  # 直接以脚本方式跑（engine/ 在 path 上）时的退路
    from _console import ensure_utf8_console


def _load_controller():
    try:
        from engine.control.controller import run as controller
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'control'))
        from controller import run as controller
    return controller


def build_parser():
    p = argparse.ArgumentParser(
        prog='paradox-engine',
        description='悖论/矛盾检测引擎：给一段文本 → 判类→复杂度→切路→'
                    '执行→判输出（只诊断不决策）',
        epilog='概念原创：月落寻常 · AI 协作实现 · MPL-2.0')
    p.add_argument('--text', type=str, default=None, help='问题文本')
    p.add_argument('--file', type=str, default=None,
                   help='从文件读取问题文本')
    p.add_argument('--json', action='store_true',
                   help='输出结构化 JSON（默认给人看的中文报告）')
    p.add_argument('--demo', action='store_true',
                   help='跑完整演示 demo.py（步数见脚本自身输出）')
    p.add_argument('--tools', action='store_true',
                   help='列出全部可用工具（function-calling schema）')
    p.add_argument('--structured', type=str, default=None,
                   help='结构化线索 JSON（如 {"A":"要快","B":"要稳"}，'
                        '给 T2 用）')
    p.add_argument('--scenarios', action='store_true',
                   help='列出场景库（真实中文场景 + 期望诊断 + 复核状态）')
    p.add_argument('--scene', type=str, default=None, metavar='ID',
                   help='跑指定场景（如 S01；all=全部），输出期望 vs 实际 '
                        '+ 实际跑了哪些构件；可与 --json 同用')
    p.add_argument('--explain', action='store_true',
                   help='输出判类依据（主型/副型得分与命中信号、复杂度构成、'
                        '路由依据）——把「为什么这么判」摆出来')
    p.add_argument('--review', action='store_true',
                   help='场景复核模式：逐场景给期望 vs 实际 + 命中信号 + '
                        '可粘贴的复核结论行（配 --scene 单个或 all）')
    p.add_argument('--stats', action='store_true',
                   help='场景库统计：各题型场景数 / 对照通过数 / 复核进度')
    p.add_argument('--mark', type=str, default=None, metavar='ID',
                   help='复核落笔：把结论写回场景表（如 --mark S05；'
                        '配 --verdict 与 --note）——作者不必手改源码')
    p.add_argument('--verdict', type=str, default='ok',
                   choices=['ok', 'wrong', 'edge', 'pending'],
                   help='配合 --mark 的结论：ok=正确 / wrong=误判-待修 / '
                        'edge=边界情况 / pending=退回待复核（默认 ok）')
    p.add_argument('--note', type=str, default='',
                   help='配合 --mark 的复核备注（一句话，写进场景表）')
    p.add_argument('--session', type=str, default=None, metavar='FILE',
                   help='多轮会话文件：逐条材料累积诊断，跨命令记住前文'
                        '（配 --add / --revise / --state / --reset）')
    p.add_argument('--add', type=str, default=None, metavar='文本',
                   help='配合 --session：给一段材料跑诊断并记进会话')
    p.add_argument('--add-file', type=str, default=None, metavar='文件',
                   dest='add_file',
                   help='配合 --session：整篇材料（UTF-8 文本）逐段诊断并记账——'
                        'para=按空行分段（默认）、line=按行')
    p.add_argument('--split', type=str, default='para', choices=['para', 'line'],
                   help='配合 --add-file 的分段方式（默认 para）')
    p.add_argument('--max-segs', type=int, default=200, dest='max_segs',
                   metavar='N', help='配合 --add-file：一次最多导入多少段'
                                     '（默认 200；超出的照实报，不静默丢）')
    p.add_argument('--structured-json', type=str, default=None,
                   metavar='JSON', dest='structured_json',
                   help='配合 --session --add：结构化线索（如 {"sentence":'
                        '"liar"}），有它构件才真跑')
    p.add_argument('--revise', type=str, default=None, metavar='新信息',
                   help='配合 --session：用新信息修正会话里的信念集'
                        '（AGM 最小放弃）')
    p.add_argument('--beliefs', type=str, default=None, metavar='P,Q',
                   help='配合 --session --revise：逗号分隔的旧信念集'
                        '（不给就用会话里已有的）')
    p.add_argument('--session-state', action='store_true',
                   dest='session_state',
                   help='配合 --session：看当前会话汇总（轮次/题型分布/'
                        '墙清单/信念集/修正历史）')
    p.add_argument('--session-reset', action='store_true',
                   dest='session_reset',
                   help='配合 --session：清空这个会话（文件保留）')
    p.add_argument('--export', type=str, default=None, metavar='文件',
                   help='配合 --session：把会话导成 Markdown 台账（给 "-" '
                        '则只打印）；目标已存在时默认不覆盖')
    p.add_argument('--export-overwrite', action='store_true',
                   dest='export_overwrite',
                   help='配合 --export：允许覆盖已存在的台账文件')
    return p


def _load_classifier():
    try:
        from engine.control.classifier import run as classifier
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'control'))
        from classifier import run as classifier
    return classifier


def _scene_map():
    """场景 id → 场景 dict（复核/解释用）。"""
    try:
        from engine.scenarios.scenarios import SCENES
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        from scenarios import SCENES
    return {s['id']: s for s in SCENES}


def explain_block(text):
    """判类依据（白箱）：主型/副型得分与命中信号 + 复杂度构成 + 路由依据。

    数据全部取自 classifier 本来的白箱输出，本函数只排版——不新增判断逻辑
    （否则就成了"解释用的第二套判类"，那才是真的坑）。
    """
    cl = _load_classifier()
    r = cl({'text': text, 'debug': True})
    lines = ['【判类依据】（启发式信号表打分，非语言学完备分析）']
    for i, t in enumerate(r['types']):
        tag = '主型' if i == 0 else '副型'
        lines.append(f"  {tag} {t['type']} {t['name']}（{t['score']} 分）"
                     f" ← 命中：{'、'.join(t['signals'])}")
    cx = r['complexity']
    flags = ('加分项：' + '、'.join(cx['flags'])) if cx['flags'] else '无加分项'
    lines.append(f"  复杂度 {r['level']}（分 {cx['score']}）："
                 f"实体≈{cx['entity_est']} / 关系≈{cx['relation_est']}；{flags}")
    lines.append(f"  路由 {r['route']['route_id']} ← {r['route']['reason']}"
                 f"（管线 {'、'.join(r['route']['pipeline'])}）")
    lines.append(f"  置信度 {r['confidence']}"
                 + ('（低——分类存疑，仅供参考）'
                    if r['confidence'] == 'low' else ''))
    return '\n'.join(lines)


def review_scenes(json_out, scene_id=None):
    """场景复核：期望 vs 实际 + 判类命中信号 + 可粘贴的复核结论行。"""
    scenes = _scene_map()
    if scene_id and scene_id != 'all' and scene_id not in scenes:
        msg = (f"场景 {scene_id!r} 不存在——可用："
               + '、'.join(scenes) + '（或 all=全部）')
        print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
              if json_out else msg)
        return 2
    try:
        from engine.scenarios.scenarios import run as scenes_run
    except ImportError:
        from scenarios import run as scenes_run
    ids = None if (scene_id is None or scene_id == 'all') else [scene_id]
    results = scenes_run({'action': 'run',
                          'scene_id': ids[0] if ids else None})['scenes']
    cl = _load_classifier()
    rows = []
    for x in results:
        s = scenes[x['id']]
        c = cl({'text': s['text']})
        rows.append({
            'id': x['id'], 'title': x['title'],
            'expect': f"{s['expect_type']}-{s['expect_level']}",
            'actual': f"{x['actual_type']}-{x['actual_level']}",
            'passed': x['passed'],
            'signals': c['types'][0]['signals'] if c['types'] else [],
            'confidence': c['confidence'],
            'checked': s.get('checked', False),
            'diffs': x['diffs'],
        })
    if json_out:
        print(json.dumps({'reviewed': len(rows), 'rows': rows},
                         ensure_ascii=False, indent=2))
        return 0
    n_ok = sum(1 for r in rows if r['passed'])
    print(f"场景复核 {len(rows)} 个（✅ 判定符合期望 {n_ok} / ⚠️ 需人看 "
          f"{len(rows) - n_ok}）")
    for r in rows:
        print(f"  {r['id']} {'✅' if r['passed'] else '⚠️'} 期望 {r['expect']}"
              f" / 实际 {r['actual']}")
        print(f"      输入：{scenes[r['id']]['text'][:44]}")
        if r['signals']:
            print(f"      判类命中：{'、'.join(r['signals'])}"
                  f"（置信度 {r['confidence']}）")
        for d in r['diffs']:
            print(f"      差异：{d}")
        print(f"      复核状态：{'已复核' if r['checked'] else '待复核'}"
              f"——看完落笔：paradox-engine --mark {r['id']} --verdict ok"
              f"（wrong=误判待修 / edge=边界情况）")
    print("  说明：复核是人的判断，引擎只把依据摆出来（只诊断不决策）。")
    return 0


def scenes_stats(json_out):
    """场景库统计：各题型场景数 / 对照通过数 / 复核进度。"""
    from collections import Counter
    scenes = _scene_map()
    try:
        from engine.scenarios.scenarios import run as scenes_run
    except ImportError:
        from scenarios import run as scenes_run
    per_type = Counter(s['expect_type'] for s in scenes.values())
    results = scenes_run({'action': 'run'})['scenes']
    passed = sum(1 for r in results if r['passed'])
    checked = sum(1 for s in scenes.values() if s.get('checked'))
    per_type_passed = Counter(r['expect_type'] for r in results
                              if r['passed'])
    try:
        from engine.scenarios.review_marks import review_state
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        from review_marks import review_state
    state = review_state()
    if json_out:
        print(json.dumps({
            'scenes': len(scenes), 'passed': passed, 'checked': checked,
            'unchecked': len(scenes) - checked,
            'review_state': state,
            'per_type': dict(sorted(per_type.items())),
            'per_type_passed': dict(sorted(per_type_passed.items())),
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"场景库统计：{len(scenes)} 个场景 / 对照通过 {passed}"
          f" / 已复核 {checked} / 待复核 {len(scenes) - checked}")
    print(f"  复核分布：正确 {state['ok']} / 误判-待修 {state['wrong']}"
          f" / 边界情况 {state['edge']} / 待复核 {state['pending']}")
    print("  各题型场景数（括号内为对照通过数）：")
    row = []
    for t in sorted(per_type):
        row.append(f"{t}:{per_type[t]}({per_type_passed.get(t, 0)})")
        if len(row) == 6:
            print('    ' + '  '.join(row))
            row = []
    if row:
        print('    ' + '  '.join(row))
    print("  判类误判率口径：待复核场景全部复核后，「⚠️ 数 / 场景数」才是"
          "可报的误判率（当前复核未完成，故不报数）。")
    return 0


def _run_scenarios(json_out, scene_id=None, explain=False):
    """场景库：列清单 / 跑对照。返回退出码。"""
    try:
        from engine.scenarios.scenarios import SCENES, run as scenes_run
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        from scenarios import SCENES, run as scenes_run

    if scene_id is None:
        r = scenes_run({'action': 'list'})
        if json_out:
            print(json.dumps({'scenes': r['scenes'],
                              'count': len(r['scenes']),
                              'boundary': r['boundary']},
                             ensure_ascii=False, indent=2))
            return 0
        checked = sum(1 for s in r['scenes'] if s['checked'])
        print(f"场景库 {len(r['scenes'])} 个（已复核 {checked} / 待复核 "
              f"{len(r['scenes']) - checked}）：")
        for s in r['scenes']:
            mark = '✅' if s['checked'] else '⏳'
            lvl = s['expect_level'] or '-'
            print(f"  {mark} {s['id']} [{s['expect_type']}-{lvl}] "
                  f"{s['title']}")
            print(f"      {s['text'][:46]}")
        print(f"  {r['boundary']}")
        print("  跑对照：paradox-engine --scene S01（或 all）")
        return 0

    ids = None if scene_id == 'all' else [scene_id]
    if ids is not None and scene_id not in {s['id'] for s in SCENES}:
        # 诚实拦截：不存在的场景不能报"0/0 通过"（那是假通过）
        msg = (f"场景 {scene_id!r} 不存在——可用："
               + '、'.join(s['id'] for s in SCENES) + '（或 all=全部）')
        if json_out:
            print(json.dumps({'error': msg, 'available':
                              [s['id'] for s in SCENES]},
                             ensure_ascii=False, indent=2))
        else:
            print(msg)
        return 2
    r = scenes_run({'action': 'run', 'scene_id': None if ids is None
                    else ids[0]})
    results = r['scenes']
    report = r['report']
    if json_out:
        print(json.dumps({'total': report['total'],
                          'passed': report['passed'],
                          'failed': [x['id'] for x in report['failed']],
                          'scenes': results,
                          'boundary': r['boundary']},
                         ensure_ascii=False, indent=2))
        return 0 if report['passed'] == report['total'] else 1
    print(f"场景对照 {report['passed']}/{report['total']} 通过")
    for x in results:
        mark = '✅' if x['passed'] else '⚠️'
        print(f"  {mark} {x['id']} {x['title']}")
        print(f"      期望 {x['expect_type']} / 实际 {x['actual_type']}"
              f"-{x['actual_level']}（路由 {x['actual_route']}）")
        ran = [e for e in x.get('execution', []) if e['status'] == 'run']
        miss = [e for e in x.get('execution', [])
                if e['status'] != 'run']
        if ran:
            print("      真跑：" + '、'.join(
                f"{e['component']}→{e['verdict']}" for e in ran))
        if miss:
            print("      未跑（缺结构化输入，诚实报缺）：" + '、'.join(
                e['component'] for e in miss))
        for d in x['diffs']:
            print(f"      差异：{d}")
    print(f"  {r['boundary']}")
    if explain:
        smap = _scene_map()
        for x in results:
            if x['id'] in smap:
                print()
                print(f"—— {x['id']} 的判类依据 ——")
                print(explain_block(smap[x['id']]['text']))
    return 0 if report['passed'] == report['total'] else 1


def mark_scenes(json_out, scene_id, verdict='ok', note=''):
    """复核落笔：把人的判断写回场景表（引擎不替人下结论）。"""
    try:
        from engine.scenarios.review_marks import mark_scene, review_state
    except ImportError:
        sys.path.insert(0, os.path.join(_REPO, 'engine', 'scenarios'))
        from review_marks import mark_scene, review_state
    r = mark_scene(scene_id, verdict, note)
    if not r['ok']:
        print(json.dumps(r, ensure_ascii=False, indent=2) if json_out else
              '复核落笔失败：' + r['error'])
        return 2
    st = review_state()

    def _line(res, state):
        label = {'ok': '正确', 'wrong': '误判-待修', 'edge': '边界情况',
                 'pending': '退回待复核'}[res['verdict']]
        head = (f"复核落笔 {res['scene']} → {label}"
                + (f"（{res['review'].strip()}）" if res.get('review') else ''))
        if not res['changed']:
            head += '——场景表本来就是这个状态，未改动'
        return (head + f"\n  当前复核分布：正确 {state['ok']} / 误判-待修 "
                f"{state['wrong']} / 边界情况 {state['edge']} / 待复核 "
                f"{state['pending']}")

    if json_out:
        out = dict(r)
        out['state'] = st
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(_line(r, st))
        print('  复核是人的判断：引擎只把依据摆出来（只诊断不决策）；'
              '写回的只有 checked 与 review 两个字段。')
    return 0


def mark_guard_error(args, json_out):
    """--verdict / --note 必须配 --mark（否则就是空落笔，诚实拦下）。"""
    if args.mark:
        return None
    given = [n for n, v in (('--verdict', args.verdict != 'ok'),
                            ('--note', bool(args.note))) if v]
    if not given:
        return None
    msg = ('%s 必须配 --mark ID 才有意义（例如 --mark S05 --verdict ok）'
           % ' 与 '.join(given))
    print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
          if json_out else msg)
    return 2


def session_cmd(args):
    """多轮会话：add 记一条 / revise 修正信念 / state 看汇总 / reset 清空。"""
    try:
        from engine.control.session import run as session_run
    except ImportError:
        from session import run as session_run
    if args.session_state:
        action = 'state'
    elif args.session_reset:
        action = 'reset'
    elif args.export is not None:
        action = 'report'
    elif args.add_file is not None:
        action = 'add_file'
    elif args.add is not None:
        action = 'add'
    elif args.revise is not None:
        action = 'revise'
    else:
        msg = ('--session 要配一个动作：--add 文本 / --add-file 文件 / '
               '--revise 新信息 / --session-state / --session-reset')
        print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
              if args.json else msg)
        return 2
    inputs = {'action': action, 'path': args.session}
    if action == 'report':
        inputs['out_file'] = args.export
        inputs['overwrite'] = args.export_overwrite
    if action == 'add_file':
        inputs['text_file'] = args.add_file
        inputs['split'] = args.split
        inputs['max_segs'] = args.max_segs
    if action == 'add':
        inputs['text'] = args.add
        if args.structured_json:
            if args.structured:
                msg = '--structured-json 与 --structured 只能给一个'
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
                      if args.json else msg)
                return 2
            try:
                inputs['structured'] = json.loads(args.structured_json)
            except ValueError as e:
                msg = f'--structured-json 解析失败：{e}'
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
                      if args.json else msg)
                return 2
        elif args.structured:
            try:
                inputs['structured'] = json.loads(args.structured)
            except ValueError as e:
                msg = f'--structured 解析失败：{e}'
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
                      if args.json else msg)
                return 2
    if action == 'revise':
        inputs['new_info'] = args.revise
        if args.beliefs:
            inputs['beliefs'] = [b.strip() for b in args.beliefs.split(',')
                                 if b.strip()]
    r = session_run(inputs)
    st = r['state']
    if action == 'report':
        md = r.get('markdown') or ''
        if r['verdict'] == 'report_ready':
            print(md if not args.json else json.dumps(
                {'verdict': r['verdict'], 'bytes': len(md), 'state': st,
                 'boundary': r['boundary']}, ensure_ascii=False, indent=2))
            return 0
        msg = r.get('explanation') or r['verdict']
        if r['verdict'] in ('report_written',):
            print(json.dumps(r, ensure_ascii=False, indent=2) if args.json
                  else '台账：' + msg)
            return 0
        if r['verdict'] == 'nothing_to_report':
            print(json.dumps(r, ensure_ascii=False, indent=2) if args.json
                  else '没导出：' + msg)
            return 2
        print(json.dumps(r, ensure_ascii=False, indent=2) if args.json
              else '没导出：' + msg)
        return 2
    if r['verdict'] in ('input_pending', 'state_corrupt', 'path_invalid',
                        'empty_session'):
        msg = r.get('explanation') or ('%s：%s' % (r['verdict'], st))
        print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else
              '会话没动：' + msg)
        return 2
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    if action == 'add':
        t = r['turn']
        print(f"记下第 {t['i']} 条：{t['text'][:40]}")
        print(f"  判类 {t['type']} {t['type_name']} · 复杂度 {t['level']}"
              f" · 路由 {t['route']} · 五步结论 {t['verdict']}")
        ran = [e for e in t['execution'] if e['status'] == 'run']
        pend = [e for e in t['execution'] if e['status'] != 'run']
        print(f"  执行：真跑 {len(ran)} 件"
              + (f"（{'、'.join(e['component'] for e in ran)}）" if ran else '')
              + f" / 没跑 {len(pend)} 件（缺结构化线索的照实标）")
    elif action == 'add_file':
        imp = r['imported']
        print(f"材料导入：{r['explanation']}")
        for it in imp['imported']:
            print(f"  {it['i']}. [{it['type']}-{it['level']}] "
                  f"{it['head']}（{it['verdict']}）")
        for sk in imp['skipped']:
            print(f"  未处理 第{sk['seg']}段（{sk['reason']}，"
                  f"{sk['chars']} 字）：{sk['head']}")
    elif action == 'revise':
        rev = r['revision']
        print(f"信念修正（{rev['verdict']}）：{rev['new_info'][:40]}")
        print(f"  保留 {rev['kept']} / 放弃 {rev['dropped']}"
              f"（旧集合来自{rev['beliefs_source']}）")
    elif action == 'reset':
        print('会话已清空（文件保留）。')
    else:
        print('会话当前状态：')
        for t in st['turn_list']:
            print(f"  {t['i']}. [{t['type']}-{t['level']}] {t['text'][:36]}"
                  f"（{t['verdict']}）")
        for e in st['wall_events']:
            print(f"  墙事件 {e['i']}：{e['component']}"
                  f" → {e['component_verdict']}")
    print(f"  当前会话：轮次 {st['turns']} · 题型分布 {st['per_type']}"
          f" · 墙清单 {st['wall_count']} 条 · 信念 {len(st['beliefs'])} 条"
          f" · 修正 {len(st['revisions'])} 次")
    print('  ' + r['boundary'])
    return 0


def session_guard_error(args, json_out):
    """--session 的动作参数必须配 --session（否则不知道记哪儿）。"""
    if args.session:
        return None
    given = [n for n, v in (
        ('--add', args.add is not None),
        ('--add-file', args.add_file is not None),
        ('--revise', args.revise is not None),
        ('--export', args.export is not None),
        ('--beliefs', bool(args.beliefs)),
        ('--session-state', args.session_state),
        ('--session-reset', args.session_reset)) if v]
    if not given:
        return None
    msg = ('%s 必须配 --session FILE（会话记在哪个文件）——'
           '不会悄悄在别处落文件' % ' 与 '.join(given))
    print(json.dumps({'error': msg}, ensure_ascii=False, indent=2)
          if json_out else msg)
    return 2


def main(argv=None):
    ensure_utf8_console()   # Windows GBK 控制台：报告含 ⚠/✅，先自愈编码
    args = build_parser().parse_args(argv)

    guard = mark_guard_error(args, args.json)
    if guard is not None:
        return guard
    guard = session_guard_error(args, args.json)
    if guard is not None:
        return guard

    if args.session:
        return session_cmd(args)

    if args.mark:
        return mark_scenes(args.json, args.mark, args.verdict, args.note)

    if args.stats:
        return scenes_stats(args.json)

    if args.review:
        return review_scenes(args.json, args.scene)

    if args.scenarios:
        return _run_scenarios(args.json)

    if args.scene:
        return _run_scenarios(args.json, args.scene, args.explain)

    if args.demo:
        demo_path = os.path.join(_REPO, 'demo.py')
        os.system(f'python "{demo_path}"')
        return 0

    if args.tools:
        try:
            from engine.ai.tools import tools
        except ImportError:
            sys.path.insert(0, os.path.join(_REPO, 'engine', 'ai'))
            from tools import tools
        tl = tools()
        print(f'可用工具 {len(tl)} 件：')
        for t in tl:
            fn = t['function']
            print(f'  · {fn["name"]}：{fn["description"]}')
        return 0

    # 取文本
    text = args.text
    if args.file:
        try:
            with open(args.file, encoding='utf-8') as fh:
                text = fh.read().strip()
        except OSError as e:
            print(f'读文件失败：{e}')
            return 2
    if not text:
        print('需给文本：--text "..." 或 --file 输入.txt'
              '（或 --demo / --tools）')
        return 2

    # 结构化线索
    structured = None
    if args.structured:
        try:
            structured = json.loads(args.structured)
        except json.JSONDecodeError as e:
            print(f'--structured JSON 解析失败：{e}')
            return 2

    controller = _load_controller()
    r = controller({'text': text, 'structured': structured or {}})

    if args.json:
        # 结构化输出：classification + execution + output_check + report
        print(json.dumps({
            'main_type': r['classification']['main_type'],
            'main_name': r['classification']['main_name'],
            'level': r['classification']['level'],
            'route_id': r['classification']['route']['route_id'],
            'confidence': r['classification']['confidence'],
            'verdict': r['verdict'],
            'output_check': r['output_check'],
            'execution': [
                {'component': e['component'], 'status': e['status'],
                 'note': e.get('note')}
                for e in r['execution']
            ],
            'report': r['report'],
        }, ensure_ascii=False, indent=2))
    else:
        print(r['report'])
        if args.explain:
            print()
            print(explain_block(text))

    return 0


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    raise SystemExit(main())
