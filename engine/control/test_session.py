# -*- coding: utf-8 -*-
"""
test_session.py — 正式测试：多轮状态构件（会话台账）
用例依据：轨 C 多轮状态 + 诚实边界（只记录引擎输出，不补结论）
         + 仓库纪律「测试不许改动被跟踪文件」
运行：python engine/control/test_session.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.control.session import run as session_run  # noqa: E402
from engine.control.controller import run as ctl  # noqa: E402
from engine.cold.agm_revision import run as agm  # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def sha(path):
    import hashlib
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def text_of(path):
    with io.open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


TXT_WALL = '这句话是假的，反复震荡，越绕越深'
TXT_CONFLICT = '产品既要三周上线又要十二周合规，销售和研发各执一词'
TXT_PLAIN = '帮我看看这个怎么办才好'
# 走到 T9-L3（撞墙管线路由）的语料：学科密集 + 关系多 + 证据冲突 + 对立
TXT_T5_A = '原来以为这个方案要十二周，现在发现三周就行'
TXT_T5_B = '原来以为产量越高越好，现在发现成本会反超'
TXT_WALL_PIPE = ('这道题要求建模：先说清机制与理论模型，再讨论系统演化与多条通路，'
                 '为什么产量导致成本上升，库存导致资金占用，广告导致需求波动，'
                 '汇率促进出口，税率抑制投资，监管抑制加急，审计隶属法务，'
                 '这条通路隶属主系统，另有一条通路隶属备用模型；'
                 '报告说这套模型有效，另一份报告说无效，数据互相矛盾；'
                 '方案既要三周上线，又要十二周合规')

print("多轮状态 · 正式测试")
print("=" * 60)

d = tempfile.mkdtemp(prefix='pe_session_test_')
p = os.path.join(d, 's.json')
p2 = os.path.join(d, 's2.json')
try:
    # ── 用例1：空会话与缺参（诚实拦截，不落文件）
    r = session_run({'action': 'state', 'path': p})
    check("会话文件不存在时 state → empty_session",
          r['verdict'] == 'empty_session', r['verdict'])
    check("空会话不偷偷建文件", not os.path.exists(p))
    check("缺 path → input_pending（不在别处落文件）",
          session_run({'action': 'add', 'text': 'x'})['verdict'] == 'input_pending')
    check("action 非法 → input_pending",
          session_run({'action': 'wat', 'path': p})['verdict'] == 'input_pending')
    check("inputs 不是 dict → input_pending",
          session_run('x')['verdict'] == 'input_pending')

    # ── 用例2：add 记轮次（记录的是引擎自己的输出，不二次加工）
    r1 = session_run({'action': 'add', 'path': p, 'text': TXT_CONFLICT})
    direct = ctl({'text': TXT_CONFLICT})
    check("add → turn_added", r1['verdict'] == 'turn_added', str(r1['verdict']))
    check("轮次里的判类与总控直接跑一致（不编造）",
          r1['turn']['type'] == direct['classification']['main_type']
          and r1['turn']['level'] == direct['classification']['level']
          and r1['turn']['route'] == direct['classification']['route']['route_id'],
          str(r1['turn']))
    check("轮次记了五步结论（verdict 原样）",
          r1['turn']['verdict'] == direct['verdict'], r1['turn']['verdict'])
    check("会话文件已生成且是合法 JSON",
          os.path.exists(p) and isinstance(json.loads(text_of(p)), dict))
    check("会话文件行尾 LF（无 CR）", '\r' not in text_of(p))
    check("created / updated 都写上了",
          bool(json.loads(text_of(p))['created'])
          and bool(json.loads(text_of(p))['updated']))
    check("写盘不留临时文件",
          not [f for f in os.listdir(d) if f.startswith('.session-')])

    # ── 用例3：坏输入不弄脏会话
    check("text 非字符串 → input_pending",
          session_run({'action': 'add', 'path': p, 'text': 5})['verdict']
          == 'input_pending')
    check("text 空串 → input_pending",
          session_run({'action': 'add', 'path': p, 'text': '   '})['verdict']
          == 'input_pending')
    check("structured 非 dict → input_pending",
          session_run({'action': 'add', 'path': p, 'text': 'x',
                       'structured': []})['verdict'] == 'input_pending')
    check("坏输入后轮次数没变（仍是 1）",
          session_run({'action': 'state', 'path': p})['state']['turns'] == 1)

    # ── 用例4：多轮累积与题型分布
    r2 = session_run({'action': 'add', 'path': p, 'text': TXT_PLAIN})
    st = session_run({'action': 'add', 'path': p, 'text': TXT_WALL})['state']
    check("三轮累积、顺序保持（i=1,2,3）",
          [t['i'] for t in json.loads(text_of(p))['turns']] == [1, 2, 3],
          str(st['per_type']))
    check("题型分布与实际判类一致",
          sum(st['per_type'].values()) == 3, str(st['per_type']))
    check("轮次 verdict 与控制器口径一致（第二轮 classified_only 之类原样）",
          r2['turn']['verdict'] == ctl({'text': TXT_PLAIN})['verdict'])

    # ── 用例5：撞墙族构件真跑了才进墙清单
    check("只给文本、构件没真跑 → 墙清单为空（不假装）",
          st['wall_count'] == 0, str(st['wall_events']))
    r5 = session_run({'action': 'add', 'path': p, 'text': TXT_WALL,
                      'structured': {'sentence': 'liar'}})
    ev = r5['state']['wall_events']
    check("给了结构化线索、自指构件真跑 → 记进墙清单",
          r5['state']['wall_count'] == 1 and ev[0]['component']
          == 'selfref_fixpoint', str(ev))
    check("墙清单记的是构件自己的 verdict（不是引擎替它编的）",
          ev[0]['component_verdict'] == (ctl({'text': TXT_WALL, 'structured':
                                              {'sentence': 'liar'}})['execution'][0]
                                         ['output']['verdict']), str(ev))

    # ── 用例6：revise 用 AGM 修正信念（结论以 AGM 构件为准）
    check("会话里没信念集时 revise → input_pending（不硬推）",
          session_run({'action': 'revise', 'path': p,
                       'new_info': '¬Q'})['verdict'] == 'input_pending')
    ref = agm({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
    r6 = session_run({'action': 'revise', 'path': p, 'beliefs': ['P→Q', 'P'],
                      'new_info': '¬Q'})
    check("revise → belief_revised，结论与 AGM 直接跑一致",
          r6['verdict'] == 'belief_revised'
          and r6['revision']['dropped'] == ref['dropped']
          and r6['revision']['kept'] == ref['kept'],
          str(r6['revision']))
    check("修正后会话信念集 = AGM 的 kept（含新信息）",
          session_run({'action': 'state', 'path': p})['state']['beliefs']
          == ref['kept'])
    check("修正历史记了 before/after（可追溯）",
          r6['revision']['beliefs_before'] == ['P→Q', 'P']
          and r6['revision']['beliefs_after'] == ref['kept'],
          str(r6['revision']))

    unsat = agm({'mode': 'revise', 'beliefs': ['P'], 'new_info': '¬(P∨¬P)'})
    check("不可满足的新信息 → AGM 说不可满足（作为对照）",
          unsat['verdict'] == 'new_info_unsatisfiable', unsat['verdict'])
    before_beliefs = session_run({'action': 'state', 'path': p})['state']['beliefs']
    r7 = session_run({'action': 'revise', 'path': p, 'beliefs': ['P'],
                      'new_info': '¬(P∨¬P)'})
    check("不可满足的新信息不写进信念集（原信念不动）",
          r7['verdict'] == 'belief_revised'
          and r7['revision']['beliefs_after'] == before_beliefs,
          str(r7['revision']))

    # ── 用例7：两个会话互不串
    session_run({'action': 'add', 'path': p2, 'text': TXT_PLAIN})
    check("两个会话文件各记各的（不共享状态）",
          session_run({'action': 'state', 'path': p2})['state']['turns'] == 1
          and session_run({'action': 'state', 'path': p})['state']['turns'] == 4)

    # ── 用例8：reset 清空但文件留着
    r8 = session_run({'action': 'reset', 'path': p})
    check("reset → reset_done，轮次/信念/修正都归零",
          r8['verdict'] == 'reset_done' and r8['state']['turns'] == 0
          and r8['state']['beliefs'] == [] and r8['state']['revisions'] == [])
    check("reset 后文件仍在且是合法 JSON",
          os.path.exists(p) and isinstance(json.loads(text_of(p)), dict))

    # ── 用例9：损坏文件绝不覆盖
    bad = os.path.join(d, 'bad.json')
    with io.open(bad, 'w', encoding='utf-8') as fh:
        fh.write('{ 这不是 JSON')
    before_bad = text_of(bad)
    r9 = session_run({'action': 'add', 'path': bad, 'text': 'x'})
    check("会话文件损坏 → state_corrupt（不覆盖原文件）",
          r9['verdict'] == 'state_corrupt' and text_of(bad) == before_bad,
          r9['verdict'])
    with io.open(bad, 'w', encoding='utf-8') as fh:
        fh.write('[1, 2, 3]')
    check("顶层不是对象 → state_corrupt",
          session_run({'action': 'add', 'path': bad, 'text': 'x'})['verdict']
          == 'state_corrupt')
    check("path 是目录 → path_invalid（不砸栈）",
          session_run({'action': 'add', 'path': d, 'text': 'x'})['verdict']
          == 'path_invalid')

    # ── 用例10：边界声明与端口
    check("每次返回都带边界声明（只诊断不决策）",
          '只诊断不决策' in r8['boundary'] and '算不动' in r8['boundary'])

    # ── 用例11：整篇材料逐段导入（工作台实际用法）
    mat = os.path.join(d, '材料.md')
    with io.open(mat, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write(TXT_CONFLICT + '\n\n')
        fh.write('   \n\n')                 # 空白段：只报数，不当正文
        fh.write(TXT_WALL + '\n\n')
        fh.write(TXT_PLAIN + '\n')          # 末尾换行不算一段
    pi = os.path.join(d, 'imp.json')
    ri = session_run({'action': 'add_file', 'path': pi, 'text_file': mat})
    check("导入 → turns_added（3 段）",
          ri['verdict'] == 'turns_added'
          and len(ri['imported']['imported']) == 3, ri.get('explanation'))
    check("空白段只报数，不当成一段（不静默丢也不假装）",
          ri['imported']['skipped'] == []
          and ri['imported']['skipped_empty_blocks'] == 1,
          str(ri['imported']))
    seg = ri['imported']['imported'][0]
    direct_mat = ctl({'text': TXT_CONFLICT})
    check("导入的判类与总控直接跑一致（不编造）",
          seg['type'] == direct_mat['classification']['main_type']
          and seg['level'] == direct_mat['classification']['level'],
          str(seg))
    check("带 BOM 的材料文件不把 BOM 当正文",
          not seg['head'].startswith('\ufeff'), repr(seg['head'][:6]))
    check("导入的轮次按顺序接在会话里（i=1,2,3）",
          [t['i'] for t in json.loads(text_of(pi))['turns']] == [1, 2, 3])

    # ── 用例12：超限照实报（不静默截断）
    rlim = session_run({'action': 'add_file', 'path': pi, 'text_file': mat,
                        'max_segs': 1})
    check("超过 max_segs → turns_added_partial（说明没处理多少段）",
          rlim['verdict'] == 'turns_added_partial'
          and len(rlim['imported']['skipped']) >= 1
          and '没有静默截断' in rlim['explanation'], rlim.get('explanation'))
    rlong = session_run({'action': 'add_file', 'path': pi, 'text_file': mat,
                         'max_seg_chars': 5})
    check("超过 max_seg_chars → 该段标 too_long 且不写进会话",
          all(s['reason'] == 'too_long'
              for s in rlong['imported']['skipped'])
          and len(rlong['imported']['skipped']) == 3,
          str(rlong['imported']['skipped']))
    check("按行分段也认（split=line）",
          session_run({'action': 'add_file', 'path': pi, 'text_file': mat,
                       'split': 'line'})['verdict']
          in ('turns_added', 'turns_added_partial'))

    # ── 用例13：导入的坏输入全部诚实拦截（会话不动）
    turns_before = session_run({'action': 'state',
                                'path': pi})['state']['turns']
    for label, extra in (
            ('材料文件不存在', {'text_file': os.path.join(d, '没有这个.md')}),
            ('材料路径是目录', {'text_file': d}),
            ('split 非法', {'text_file': mat, 'split': 'xx'}),
            ('max_segs 为 0', {'text_file': mat, 'max_segs': 0}),
            ('max_segs 是字符串', {'text_file': mat, 'max_segs': '3'}),
            ('max_seg_chars 负数', {'text_file': mat, 'max_seg_chars': -1})):
        rr = session_run(dict({'action': 'add_file', 'path': pi}, **extra))
        check(f"导入拦截：{label} → input_pending",
              rr['verdict'] == 'input_pending', str(rr.get('explanation'))[:60])
    check("六次坏导入后会话轮次数没变（没被弄脏）",
          session_run({'action': 'state',
                       'path': pi})['state']['turns'] == turns_before)
    empty = os.path.join(d, '空.md')
    with io.open(empty, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n\n   \n')
    check("全空白材料 → file_empty（不假装导入 0 段成功）",
          session_run({'action': 'add_file', 'path': pi,
                       'text_file': empty})['verdict'] == 'file_empty')

    # ── 用例14：台账导出（Markdown）
    pr = os.path.join(d, '台账源.json')
    session_run({'action': 'add', 'path': pr, 'text': TXT_CONFLICT})
    session_run({'action': 'add', 'path': pr, 'text': TXT_WALL,
                 'structured': {'sentence': 'liar'}})
    session_run({'action': 'revise', 'path': pr, 'beliefs': ['P→Q', 'P'],
                 'new_info': '¬Q'})
    rr = session_run({'action': 'report', 'path': pr})
    md = rr.get('markdown') or ''
    check("不写文件时 → report_ready 且带台账文本",
          rr['verdict'] == 'report_ready' and md.startswith('# 诊断台账'),
          rr['verdict'])
    check("台账里有每一条轮次（编号 + 判类 + 原文）",
          '### 1. T2' in md and '### 2. T6' in md and TXT_CONFLICT in md,
          md[:120])
    check("台账规模数字与会话汇总一致",
          ('轮次 2' in md) and ('墙事件 1' in md)
          and rr['state']['turns'] == 2 and rr['state']['wall_count'] == 1)
    note0 = json.loads(text_of(pr))['turns'][0]['execution'][0]['note']
    check("台账照实写「没跑」及原因（就是会话里记的那句，不美化）",
          '没跑' in md and note0 and note0 in md, repr(note0[:60]))
    check("台账有墙事件表（构件自己的 verdict）",
          '墙事件' in md and 'liar_cycle' in md)
    check("台账有信念集与修正史（含 before→after）",
          '当前信念集' in md and '信念修正史' in md and '修正前' in md)
    check("台账带边界声明（只诊断不决策）", '只诊断不决策' in md)

    tout = os.path.join(d, '台账.md')
    rw = session_run({'action': 'report', 'path': pr, 'out_file': tout})
    check("导出到文件 → report_written",
          rw['verdict'] == 'report_written' and os.path.exists(tout),
          rw['verdict'])
    body = text_of(tout)
    check("写出的是同一份台账且行尾 LF",
          body.startswith('# 诊断台账') and '\r' not in body)
    check("写文件不留临时文件",
          not [f for f in os.listdir(d) if f.startswith('.session-')])
    again = session_run({'action': 'report', 'path': pr, 'out_file': tout})
    check("目标已存在且没开覆盖 → file_exists（不动原文件）",
          again['verdict'] == 'file_exists' and text_of(tout) == body,
          again['verdict'])
    ro = session_run({'action': 'report', 'path': pr, 'out_file': tout,
                      'overwrite': True})
    # 台账里有「导出时间」，跨秒重写整份字节必然不同——比内容（去掉时间行）
    def _no_time(s):
        return '\n'.join(l for l in s.split('\n')
                          if not l.startswith('- 导出时间'))
    check("开了覆盖才重写（report_written，除时间行外内容一致）",
          ro['verdict'] == 'report_written'
          and _no_time(text_of(tout)) == _no_time(body),
          ro['verdict'])
    check("重写后的台账仍带同一批轮次",
          '### 1. T2' in text_of(tout) and '### 2. T6' in text_of(tout))
    same = session_run({'action': 'report', 'path': pr, 'out_file': pr})
    check("导出目标 = 会话文件本身 → 拦下（别把台账源删了）",
          same['verdict'] == 'input_pending'
          and session_run({'action': 'state',
                           'path': pr})['state']['turns'] == 2,
          same['verdict'])
    check("导出目标是目录 → path_invalid",
          session_run({'action': 'report', 'path': pr,
                       'out_file': d})['verdict'] == 'path_invalid')
    check("out_file 非字符串 → input_pending",
          session_run({'action': 'report', 'path': pr,
                       'out_file': 5})['verdict'] == 'input_pending')
    pempty = os.path.join(d, '空会话.json')
    check("空会话 → nothing_to_report（不编内容）",
          session_run({'action': 'report',
                       'path': pempty})['verdict'] == 'nothing_to_report')
    corrupt = os.path.join(d, '坏会话.json')
    with io.open(corrupt, 'w', encoding='utf-8') as fh:
        fh.write('{ 坏')
    outbad = os.path.join(d, '不该出现.md')
    rbad = session_run({'action': 'report', 'path': corrupt,
                        'out_file': outbad})
    check("会话损坏 → state_corrupt 且不产出台账文件",
          rbad['verdict'] == 'state_corrupt' and not os.path.exists(outbad),
          rbad['verdict'])

    # ── 用例15：撞墙族构件的诊断也落账（T9-L3 真跑撞墙管线那种）
    from engine.control.classifier import run as cl
    from engine.mechanisms.wall_pipeline import run as wall_direct
    pw = os.path.join(d, '墙.json')
    struct = {'wall': '既要三周上线又要十二周合规', 'thesis': '要快',
              'antithesis': '要稳', 'events': ['快', '稳', '快', '稳']}
    cw = cl({'text': TXT_WALL_PIPE})
    check("构造的语料确实走到撞墙管线路由（否则本用例没意义）",
          'wall_pipeline' in cw['route']['pipeline'], str(cw['route']))
    rw2 = session_run({'action': 'add', 'path': pw, 'text': TXT_WALL_PIPE,
                       'structured': struct})
    wl = rw2['state']['wall_events']
    check("撞墙管线真跑 → 墙事件里带五选一诊断 label",
          len(wl) == 1 and wl[0]['component'] == 'wall_pipeline'
          and bool(wl[0].get('diagnosis_label')), str(wl))
    direct = wall_direct(struct)
    check("五选一诊断与会话里记的一致（直接跑构件对照，不编）",
          wl[0]['diagnosis_label'] == direct['diagnosis']['label']
          and wl[0]['component_verdict'] == direct['verdict'], str(wl[0]))
    ex = [e for e in rw2['turn']['execution']
          if e['component'] == 'wall_pipeline'][0]
    check("构件输出里的标量字段落账（mu/grade/drill）",
          ex['detail'].get('mu') == direct['diagnosis']['mu']
          and ex['detail'].get('grade') == direct['diagnosis']['grade']
          and ex['detail'].get('drill') == direct['diagnosis']['drill'],
          str(ex['detail']))
    check("落账字段只来自构件输出（不无中生有）",
          set(ex['detail']) <= (set(direct) | set(direct['diagnosis'])
                                | {'diagnosis_label'}),
          str(sorted(ex['detail'])))
    mdw = session_run({'action': 'report', 'path': pw})['markdown']
    check("台账墙事件表带五选一诊断列",
          '五选一诊断' in mdw and direct['diagnosis']['label'] in mdw)
    check("台账管线段写出 mu/grade 且不倒着重复 verdict",
          ('mu=%s' % direct['diagnosis']['mu']) in mdw
          and 'verdict=resonance' not in mdw, mdw[-400:])
    rself = session_run({'action': 'add', 'path': pw, 'text': TXT_WALL,
                         'structured': {'sentence': 'liar'}})
    se = [w for w in rself['state']['wall_events']
          if w['component'] == 'selfref_fixpoint']
    check("别的撞墙族构件（自指不动点）也记自己的 verdict",
          bool(se) and se[0]['component_verdict'] == 'liar_cycle', str(se))
    check("没跑构件的 detail 是空的（不给没跑的东西编字段）",
          all(e['detail'] == {} for e in rself['turn']['execution']
              if e['status'] != 'run'))

    # ── 用例16：场景复核依据记进会话（结论仍是人的判断）
    from engine.scenarios.scenarios import SCENES, run as scenes_run
    scen_path = os.path.join(_REPO, 'engine', 'scenarios', 'scenarios.py')
    scen_before = sha(scen_path)
    prv = os.path.join(d, '复核.json')
    r1r = session_run({'action': 'review', 'path': prv, 'scene_id': 'S13'})
    check("复核单场景 → reviews_added（1 条）",
          r1r['verdict'] == 'reviews_added' and len(r1r['reviews']) == 1,
          r1r.get('explanation'))
    rec = r1r['reviews'][0]
    s13 = [s for s in SCENES if s['id'] == 'S13'][0]
    direct13 = scenes_run({'action': 'run', 'scene_id': 'S13'})['scenes'][0]
    check("记的期望/实际与场景库直接跑一致（不编）",
          rec['scene'] == 'S13'
          and rec['expect'] == '%s-%s' % (s13['expect_type'],
                                          s13['expect_level'])
          and rec['actual'] == '%s-%s' % (direct13['actual_type'],
                                          direct13['actual_level'])
          and rec['passed'] == bool(direct13['passed']), str(rec))
    c13 = cl({'text': s13['text']})
    check("记的命中信号与判类器直跑一致",
          rec['signals'] == (c13['types'][0]['signals'] if c13['types']
                             else []), str(rec['signals']))
    rall = session_run({'action': 'review', 'path': prv, 'scene_id': 'all'})
    check("复核全部 → 记录数 = 场景数（25）",
          rall['verdict'] == 'reviews_added'
          and len(rall['reviews']) == len(SCENES), str(len(rall['reviews'])))
    check("两条复核记录都落进会话文件（可回看）",
          len(json.loads(text_of(prv))['reviews']) == 1 + len(SCENES))
    check("会话汇总里带上复核条数",
          rall['state']['reviews'] == 1 + len(SCENES))

    turns_before2 = len(json.loads(text_of(prv))['reviews'])
    for label, sid in (('未知场景', 'S99'), ('类型错', 5), ('空串场景 id', '')):
        rr2 = session_run({'action': 'review', 'path': prv, 'scene_id': sid})
        ok = (rr2['verdict'] == 'reviews_added' if sid == '' else
              rr2['verdict'] == 'input_pending')
        check(f"复核拦截：{label} → {'空串按 all' if sid == '' else 'input_pending'}",
              ok, rr2['verdict'])
    check("拦截与空串按 all 之后记录数自洽",
          len(json.loads(text_of(prv))['reviews'])
          == turns_before2 + len(SCENES), 'see above')

    # 复核记录不等于替作者落笔：场景表必须一个字节都没动
    check("复核记录不改场景表（checked 一个字都没替作者写）",
          sha(scen_path) == scen_before)

    ponly = os.path.join(d, '只有复核.json')
    session_run({'action': 'review', 'path': ponly, 'scene_id': 'S01'})
    rmd = session_run({'action': 'report', 'path': ponly})
    check("只有复核记录的会话也能导台账（不算空会话）",
          rmd['verdict'] == 'report_ready'
          and '场景复核记录' in rmd['markdown'], rmd['verdict'])
    check("台账复核段带「当前复核标记」一栏（读场景表当前状态）",
          '当前复核标记' in rmd['markdown']
          and ('待复核' in rmd['markdown']
               or '已复核' in rmd['markdown']))
    check("台账规模行写出复核记录条数",
          '复核记录 1 条' in rmd['markdown'],
          [l for l in rmd['markdown'].split('\n')
           if l.startswith('- 规模')][:1])
    rst = session_run({'action': 'reset', 'path': ponly})
    check("reset 连复核记录一起清",
          rst['verdict'] == 'reset_done' and rst['state']['reviews'] == 0,
          str(rst['state']['reviews']))
    check("清空后会话文件仍是合法 JSON",
          isinstance(json.loads(text_of(ponly)), dict))

    # ── 用例17：批次汇总（只统计引擎自己的标签，不判断）
    pov = os.path.join(d, '汇总.json')
    check("空会话 → empty_session（没东西可汇总就不编）",
          session_run({'action': 'overview',
                       'path': pov})['verdict'] == 'empty_session')
    session_run({'action': 'add', 'path': pov, 'text': TXT_CONFLICT})
    session_run({'action': 'add', 'path': pov, 'text': TXT_WALL,
                 'structured': {'sentence': 'liar'}})
    session_run({'action': 'add', 'path': pov, 'text': TXT_PLAIN})
    session_run({'action': 'review', 'path': pov, 'scene_id': 'S05'})
    sha_before_ov = sha(pov)
    ro = session_run({'action': 'overview', 'path': pov})
    ov = ro['overview']
    check("汇总 → verdict=overview 且轮次数与状态一致",
          ro['verdict'] == 'overview' and ov['turns'] == 3
          and ov['turns'] == ro['state']['turns'], str(ov['turns']))
    turns_json = json.loads(text_of(pov))['turns']
    check("判类分布/分组与实际轮次一一对应",
          ov['per_type'] == ro['state']['per_type']
          and all(ov['by_type'][k] == [t['i'] for t in turns_json
                                       if t['type'] == k]
                  for k in ov['per_type']), str(ov['by_type']))
    check("复杂度分布与各轮次 level 一致",
          sum(ov['levels'].values()) == 3
          and ov['levels'] == {lv: sum(1 for t in turns_json
                                       if t['level'] == lv)
                               for lv in {t['level'] for t in turns_json}},
          str(ov['levels']))
    conf_direct = {}
    for t in turns_json:
        c = cl({'text': t['text']})['confidence']
        conf_direct[c] = conf_direct.get(c, 0) + 1
    check("置信度分布与判类器直跑一致（不编）",
          ov['confidence'] == conf_direct, str(ov['confidence']))
    check("置信度低的轮次单独列出来（不掩盖存疑）",
          ov['low_confidence_turns'] == [t['i'] for t in turns_json
                                         if t['confidence'] == 'low'],
          str(ov['low_confidence_turns']))
    ran_direct = {}
    for t in turns_json:
        for e in t['execution']:
            if e['status'] == 'run':
                ran_direct[e['component']] = ran_direct.get(e['component'], 0) + 1
    check("真跑构件计数与会话记录一致",
          ov['components_ran'] == ran_direct, str(ov['components_ran']))
    notes = [e.get('note') or '' for t in turns_json for e in t['execution']]
    check("「没跑的原因」全部来自引擎自己的说明（不无中生有）",
          bool(ov['not_ran_reasons']) and all(
              any(k.split('：', 1)[1] in n for n in notes)
              for k in ov['not_ran_reasons']), str(ov['not_ran_reasons']))
    check("墙事件按构件+verdict 归组",
          ov['walls'] and all('→' in k for k in ov['walls']),
          str(ov['walls']))
    check("复核记录条数也进汇总", ov['reviews'] == 1, str(ov['reviews']))
    check("汇总声明不做相似度聚类（边界摆明）",
          '不做相似度聚类' in ov['boundary']
          and '不替人下结论' in ov['boundary'])
    check("汇总只读：会话文件一个字节没动", sha(pov) == sha_before_ov)
    mdo = session_run({'action': 'report', 'path': pov})['markdown']
    check("台账里有批次汇总段且数字与汇总一致",
          '## 批次汇总' in mdo and ('- 轮次 3' in mdo)
          and ('判类分布' in mdo))
    check("台账汇总段写出真跑构件与没跑原因",
          '真跑过构件' in mdo and '没跑的原因' in mdo)
    st_corrupt = os.path.join(d, '坏2.json')
    with io.open(st_corrupt, 'w', encoding='utf-8') as fh:
        fh.write('{ 坏')
    check("会话损坏 → 汇总也诚实报 state_corrupt",
          session_run({'action': 'overview',
                       'path': st_corrupt})['verdict'] == 'state_corrupt')

    # ── 用例18：T5（知识更新）材料与信念集对接（引擎不抽公式）
    pt5 = os.path.join(d, 't5.json')
    session_run({'action': 'add', 'path': pt5, 'text': TXT_T5_A})
    session_run({'action': 'add', 'path': pt5, 'text': TXT_CONFLICT})
    session_run({'action': 'add', 'path': pt5, 'text': TXT_T5_B})
    turns_t5 = json.loads(text_of(pt5))['turns']
    check("构造语料确实被判成 T5（否则本用例没意义）",
          [t['type'] for t in turns_t5] == ['T5', 'T2', 'T5'],
          str([t['type'] for t in turns_t5]))
    ov_t5 = session_run({'action': 'overview', 'path': pt5})['overview']['t5']
    check("汇总列出 T5 材料轮次", ov_t5['t5_turns'] == [1, 3],
          str(ov_t5['t5_turns']))
    check("未挂信念集时全部记「欠命题式」",
          ov_t5['t5_pending'] == [1, 3] and ov_t5['t5_linked'] == [],
          str(ov_t5))
    check("边界写明引擎不抽公式（自然语言→逻辑式不在范围）",
          '不抽公式' in ov_t5['boundary'] and '不在本引擎范围' in ov_t5['boundary'])
    rv1 = session_run({'action': 'revise', 'path': pt5, 'beliefs': ['P→Q', 'P'],
                       'new_info': '¬Q', 'turn': 1})
    check("revise 可挂到指定轮次（source_turn 记下）",
          rv1['verdict'] == 'belief_revised'
          and rv1['revision']['source_turn'] == 1, str(rv1['revision']))
    ov_t5b = session_run({'action': 'overview', 'path': pt5})['overview']['t5']
    check("挂上后汇总显示已接 / 还欠",
          ov_t5b['t5_linked'] == [1] and ov_t5b['t5_pending'] == [3]
          and ov_t5b['linked'] == {'1': [1]}, str(ov_t5b))
    rv2 = session_run({'action': 'revise', 'path': pt5, 'beliefs': ['P→Q', 'P'],
                       'new_info': '¬Q', 'turn': 99})
    check("挂到不存在的轮次 → 拦下且不加修正记录",
          rv2['verdict'] == 'input_pending'
          and len(json.loads(text_of(pt5))['revisions']) == 1,
          rv2.get('explanation'))
    for label, tv in (('字符串', '1'), ('布尔', True), ('小数', 1.5)):
        rr3 = session_run({'action': 'revise', 'path': pt5, 'new_info': 'X',
                           'turn': tv})
        check(f"turn 类型错（{label}）→ input_pending",
              rr3['verdict'] == 'input_pending', rr3.get('explanation')[:40])
    rv3 = session_run({'action': 'revise', 'path': pt5, 'beliefs': ['P→Q', 'P'],
                       'new_info': '¬Q'})
    check("不挂轮次的修正照样能用（source_turn 为空）",
          rv3['verdict'] == 'belief_revised'
          and not rv3['revision'].get('source_turn'), str(rv3['revision']))
    check("挂轮次不改材料记录（轮次内容一字不动）",
          json.loads(text_of(pt5))['turns'] == turns_t5)
    session_run({'action': 'revise', 'path': pt5, 'beliefs': ['P→Q', 'P'],
                 'new_info': '¬Q', 'turn': 3})
    ov_t5c = session_run({'action': 'overview', 'path': pt5})['overview']['t5']
    check("两条 T5 都挂上后不再欠命题式",
          ov_t5c['t5_linked'] == [1, 3] and ov_t5c['t5_pending'] == [],
          str(ov_t5c))
    md5 = session_run({'action': 'report', 'path': pt5})['markdown']
    check("台账写出 T5 材料与已接/还欠",
          'T5（知识更新）材料' in md5 and '已接信念集' in md5
          and '还欠命题式' in md5)
    check("台账修正史写出「挂在轮次 N」",
          '挂在轮次 1' in md5, md5[md5.find('## 信念修正史'):][:160])
    rst5 = session_run({'action': 'reset', 'path': pt5})
    check("reset 之后 T5 对接状态一起清（不残留挂靠）",
          len(rst5['state']['revisions']) == 0
          and session_run({'action': 'overview', 'path': pt5})['overview']
          ['t5']['t5_linked'] == [])
    # ── 用例19：线索建议落账（建议只是建议，不自动应用）
    pcl = os.path.join(d, '线索.json')
    r_cl = session_run({'action': 'add', 'path': pcl, 'text': TXT_CONFLICT,
                        'clues': True})
    cl = r_cl['turn'].get('clues') or {}
    check("--clues 时轮次记下线索建议",
          r_cl['verdict'] == 'turn_added' and cl.get('verdict') == 'suggested',
          str(cl))
    check("可直接用的键来自原文（A/B 都在材料里）",
          cl['ready'].get('A') in TXT_CONFLICT
          and cl['ready'].get('B') in TXT_CONFLICT, str(cl.get('ready')))
    check("还欠人给的键记下了（wA/wNotA）",
          set(cl.get('need_human') or []) == {'wA', 'wNotA'},
          str(cl.get('need_human')))
    check("线索条目写明「要人确认 + 不自动应用」",
          '要人确认' in cl.get('note', '')
          and '不自动应用' in cl.get('note', ''), cl.get('note'))
    r_no = session_run({'action': 'add', 'path': pcl, 'text': TXT_PLAIN})
    check("不给 clues 就不跑建议器（默认不额外算）",
          'clues' not in r_no['turn'], str(sorted(r_no['turn'])))
    session_run({'action': 'add', 'path': pcl, 'text': TXT_WALL,
                 'structured': {'sentence': 'liar'}, 'clues': True})
    ov_cl = session_run({'action': 'overview', 'path': pcl})['overview']['clues']
    check("汇总统计有建议的轮次数",
          ov_cl['turns_with_clues'] == 2, str(ov_cl['turns_with_clues']))
    check("汇总按键统计「可直接用」与「还欠人给」",
          ov_cl['ready_keys'].get('A') == 1
          and ov_cl['need_human_keys'].get('wA') == 1, str(ov_cl))
    check("汇总列出仍欠线索的轮次（只统计）",
          ov_cl['turns_pending_clues'] == [1], str(ov_cl['turns_pending_clues']))
    check("汇总写明落账不等于落库",
          '落账不等于落库' in ov_cl['note'], ov_cl['note'])
    md_cl = session_run({'action': 'report', 'path': pcl})['markdown']
    check("台账逐条段写出建议值（标注是建议）",
          '线索建议（suggested）' in md_cl and "A = '三周上线'" in md_cl,
          md_cl[-300:])
    check("台账逐条段写出需人给的键", '需人给：wA、wNotA' in md_cl)
    check("台账汇总段写出线索统计",
          '线索建议：2 条轮次有建议' in md_cl, md_cl[:600])
    check("线索落账不改引擎行为：没跑件数照旧为 3（没自动用建议）",
          len([e for e in r_cl['turn']['execution']
               if e['status'] == 'run']) == 0, str(r_cl['turn']['execution']))
    check("clues 传非真值也不报错（按假处理）",
          session_run({'action': 'add', 'path': pcl, 'text': TXT_PLAIN,
                       'clues': 0})['verdict'] == 'turn_added')
    # ── 用例20：欠线索工作单（只拼装，不猜值）
    pws = os.path.join(d, '工作单.json')
    session_run({'action': 'add', 'path': pws, 'text': TXT_CONFLICT,
                 'clues': True})
    session_run({'action': 'add', 'path': pws, 'text': TXT_WALL,
                 'structured': {'sentence': 'liar'}, 'clues': True})
    session_run({'action': 'add', 'path': pws, 'text': TXT_PLAIN})
    sha_ws = sha(pws)
    rws = session_run({'action': 'worksheet', 'path': pws})
    mws = rws.get('markdown') or ''
    check("有欠线索轮次 → 生成工作单",
          rws['verdict'] == 'worksheet' and mws.startswith('# 欠线索工作单'),
          rws['verdict'])
    check("列出待填轮次（编号 + 判类 + 材料原文）",
          '轮次 1 · T2' in mws and TXT_CONFLICT in mws, mws[:400])
    check("可直接用的照抄原文（A/B 是材料里的词）",
          "A='三周上线'" in mws and "B='十二周合规'" in mws, mws[:600])
    check("欠的键留成 <待填> 空位",
          'wA=<待填>' in mws and 'wNotA=<待填>' in mws, mws[:600])
    check("不给欠的键编数（wA/wNotA 只有待填空位、没有数字）",
          '"wA": 5' not in mws and '"wA": "5"' not in mws
          and mws.count('<待填>') >= 4, mws[-500:])
    check("还没跑建议器的轮次单独列出",
          '还没跑建议器' in mws and '轮次：3' in mws, mws[-700:])
    check("线索已齐的轮次也标出来",
          '线索已齐' in mws and '轮次：2' in mws, mws[-400:])
    check("表头数字与统计一致",
          rws['stats']['pending'] == 1 and rws['stats']['no_clues'] == 1
          and rws['stats']['ready_only'] == 1, str(rws['stats']))
    check("工作单只读：会话文件 sha256 未变", sha(pws) == sha_ws)
    wout = os.path.join(d, '工作单.md')
    rw2 = session_run({'action': 'worksheet', 'path': pws, 'out_file': wout})
    check("工作单可写文件",
          rw2['verdict'] == 'worksheet_written' and os.path.exists(wout),
          rw2['verdict'])
    ws_body = text_of(wout)
    check("写出的工作单 LF 且含待填空位",
          '\r' not in ws_body and '<待填>' in ws_body)
    check("写文件不留临时文件",
          not [f for f in os.listdir(d) if f.startswith('.session-')])
    again_ws = session_run({'action': 'worksheet', 'path': pws,
                            'out_file': wout})
    check("目标已存在且没开覆盖 → file_exists 且文件未变",
          again_ws['verdict'] == 'file_exists' and text_of(wout) == ws_body,
          again_ws['verdict'])
    check("导出目标 = 会话文件本身 → 拦下",
          session_run({'action': 'worksheet', 'path': pws,
                       'out_file': pws})['verdict'] == 'input_pending')
    check("导出目标是目录 → path_invalid",
          session_run({'action': 'worksheet', 'path': pws,
                       'out_file': d})['verdict'] == 'path_invalid')
    check("out_file 非字符串 → input_pending",
          session_run({'action': 'worksheet', 'path': pws,
                       'out_file': 5})['verdict'] == 'input_pending')
    ponly2 = os.path.join(d, '只有复核2.json')
    session_run({'action': 'review', 'path': ponly2, 'scene_id': 'S05'})
    check("没有欠线索也没有未跑建议器 → nothing_to_do（不生成空单）",
          session_run({'action': 'worksheet',
                       'path': ponly2})['verdict'] == 'nothing_to_do')
    check("工作单边界写明「只拼装、不猜值」",
          '不猜值' in mws and '由人决定' in mws, mws[-300:])
    # ── 用例21：复核进度快照（只读现状 + 与上次对比）
    from engine.scenarios.review_marks import review_state as _rstate
    from engine.control.controller import ADAPTER_SPECS as _AS  # noqa: F401
    ppr = os.path.join(d, '进度.json')
    r1p = session_run({'action': 'progress', 'path': ppr})
    snap = r1p['snapshot']
    check("首次快照 → snapshot_taken 且计数与场景表实际一致",
          r1p['verdict'] == 'snapshot_taken'
          and snap['checked'] == _rstate()['ok'] + _rstate()['wrong']
          + _rstate()['edge'], str(snap['checked']))
    check("快照列出待复核场景 id（与场景表一致）",
          len(snap['pending_ids']) == _rstate()['pending'],
          str(len(snap['pending_ids'])))
    check("首次快照不编 delta（写明是第 1 次）",
          snap['delta_checked'] is None and '第 1 次' in r1p['explanation'],
          r1p['explanation'])
    r2p = session_run({'action': 'progress', 'path': ppr})
    check("第二次快照给出 delta（场景表没动就是 +0）",
          r2p['snapshot']['delta_checked'] == 0
          and r2p['snapshot']['newly_checked'] == []
          and r2p['snapshot']['newly_reverted'] == [],
          str(r2p['snapshot']))
    check("快照序列落进会话（可对比历史）",
          len(json.loads(text_of(ppr))['snapshots']) == 2)
    scen_snapshot = os.path.join(d, '假场景表.py')
    shutil.copyfile(os.path.join(_REPO, 'engine', 'scenarios',
                                 'scenarios.py'), scen_snapshot)
    from engine.scenarios.review_marks import mark_scene as _mark
    _mark('S05', 'ok', path=scen_snapshot)
    r3p = session_run({'action': 'progress', 'path': ppr,
                       'registry_path': scen_snapshot})
    check("换了场景表副本后：比出「新复核 S05」",
          r3p['snapshot']['newly_checked'] == ['S05']
          and r3p['snapshot']['delta_checked'] == 1,
          str(r3p['snapshot']))
    _mark('S05', 'pending', path=scen_snapshot)
    r4p = session_run({'action': 'progress', 'path': ppr,
                       'registry_path': scen_snapshot})
    check("退回待复核也认出来（newly_reverted）",
          r4p['snapshot']['newly_reverted'] == ['S05']
          and r4p['snapshot']['delta_checked'] == -1, str(r4p['snapshot']))
    check("快照只读：真场景表 sha256 未变",
          sha(scen_snapshot) != '' and
          sha(os.path.join(_REPO, 'engine', 'scenarios',
                           'scenarios.py')) == scen_before)
    bad_reg = os.path.join(d, '不是场景表.txt')
    with io.open(bad_reg, 'w', encoding='utf-8') as fh:
        fh.write('这不是场景表')
    check("场景表读不到 → registry_unreadable（不编进度）",
          session_run({'action': 'progress', 'path': ppr,
                       'registry_path': bad_reg})['verdict']
          == 'registry_unreadable')
    md_p = session_run({'action': 'report', 'path': ppr})['markdown']
    check("台账有复核进度快照段（含 delta 与仍待复核）",
          '## 复核进度快照' in md_p and '较上次' in md_p
          and '仍待复核' in md_p)
    check("台账快照段写明落笔仍是作者的判断",
          '落笔仍是作者的判断' in md_p)
    check("只有快照的会话也能导台账（不算空会话）",
          session_run({'action': 'report', 'path': ppr})['verdict']
          == 'report_ready')
    # ── 用例22：一页简报（只汇总已记下的东西）
    pbr = os.path.join(d, '简报.json')
    session_run({'action': 'add', 'path': pbr, 'text': TXT_CONFLICT,
                 'clues': True})
    session_run({'action': 'add', 'path': pbr, 'text': TXT_T5_A,
                 'clues': True})
    session_run({'action': 'progress', 'path': pbr})
    sha_br = sha(pbr)
    rb = session_run({'action': 'brief', 'path': pbr})
    mb = rb.get('markdown') or ''
    check("简报可生成且有标题",
          rb['verdict'] == 'brief' and mb.startswith('# 诊断简报'), rb['verdict'])
    for sec in ('## 这批材料', '## 欠什么', '## 复核到哪了', '## 下一步',
                '## 边界'):
        check(f"简报含「{sec}」段", sec in mb)
    ov_br = session_run({'action': 'overview', 'path': pbr})['overview']
    check("简报的判类分布与汇总一致",
          all(('%s %d 条' % kv) in mb for kv in ov_br['per_type'].items()),
          mb[:400])
    check("简报写出欠线索与仍欠轮次",
          '线索还欠' in mb and '仍欠的轮次' in mb, mb[:600])
    check("简报写出 T5 还欠命题式",
          'T5（知识更新）还欠命题式' in mb, mb[:700])
    check("简报写出复核进度与仍待复核",
          '已复核' in mb and '仍待复核' in mb)
    check("简报把「只有你能做」与「引擎能做」分开列",
          '只有你能做' in mb and '引擎能做' in mb and '--mark' in mb)
    check("简报不替人决定：写明引擎不猜数、不抽公式",
          '引擎不猜数' in mb and '引擎不抽公式' in mb)
    check("简报只读：会话文件 sha256 未变", sha(pbr) == sha_br)
    bout = os.path.join(d, '简报.md')
    rb2 = session_run({'action': 'brief', 'path': pbr, 'out_file': bout})
    check("简报可写文件且 LF",
          rb2['verdict'] == 'brief_written' and os.path.exists(bout)
          and '\r' not in text_of(bout), rb2['verdict'])
    check("目标已存在且没开覆盖 → file_exists 且文件未变",
          session_run({'action': 'brief', 'path': pbr,
                       'out_file': bout})['verdict'] == 'file_exists'
          and text_of(bout).startswith('# 诊断简报'))
    check("导出目标 = 会话文件本身 → 拦下",
          session_run({'action': 'brief', 'path': pbr,
                       'out_file': pbr})['verdict'] == 'input_pending')
    check("空会话 → nothing_to_report（不给空白简报）",
          session_run({'action': 'brief',
                       'path': os.path.join(d, '空简报.json')})['verdict']
          == 'nothing_to_report')
    # ── 用例23：会话 vs 场景表对账（只报差异，两边都不改）
    prc = os.path.join(d, '对账.json')
    check("会话里没记过依据 → nothing_to_compare（没得对账）",
          session_run({'action': 'reconcile',
                       'path': prc})['verdict'] == 'nothing_to_compare')
    session_run({'action': 'review', 'path': prc, 'scene_id': 'S13'})
    session_run({'action': 'review', 'path': prc, 'scene_id': 'S01'})
    sha_rc = sha(prc)
    rrc = session_run({'action': 'reconcile', 'path': prc})
    mrc = rrc.get('markdown') or ''
    check("对账可生成且带标题",
          rrc['verdict'] == 'reconciled' and mrc.startswith('# 复核对账'),
          rrc['verdict'])
    check("「记了依据但还没落笔」列出 S13 并给落笔命令",
          rrc['stats']['not_marked'] == 1 and 'S13' in mrc
          and '--mark S13' in mrc, str(rrc['stats']))
    check("S01 已落笔且会话有依据 → 不算「未落笔」",
          'S01：引擎' not in mrc, mrc[:400])
    check("「已落笔但没依据存档」列出老标记的场景",
          rrc['stats']['no_evidence'] >= 3 and 'S02：' in mrc,
          str(rrc['stats']['no_evidence']))
    check("场景表没有 review 文本时不算「方向相反」（不硬判）",
          rrc['stats']['disagree'] == 0, str(rrc['stats']))
    check("对账只读：会话文件 sha256 未变", sha(prc) == sha_rc)
    check("对账只读：场景表 sha256 未变",
          sha(os.path.join(_REPO, 'engine', 'scenarios',
                           'scenarios.py')) == scen_before)
    check("对账边界写明两边都不改、谁对由人定",
          '两边都不改' in mrc and '谁对由人定' in mrc, mrc[-200:])

    # 场景表副本：把 S13 标成「误判-待修」，会话里它是对照通过 → 方向相反
    reg2 = os.path.join(d, '场景表副本.py')
    shutil.copyfile(os.path.join(_REPO, 'engine', 'scenarios',
                                 'scenarios.py'), reg2)
    _mark('S13', 'wrong', 'engine 说对，我改的是期望值', path=reg2)
    rrc2 = session_run({'action': 'reconcile', 'path': prc,
                        'registry_path': reg2})
    md2 = rrc2.get('markdown') or ''
    check("方向相反会被列出（引擎对照通过 / 你标了误判）",
          rrc2['stats']['disagree'] == 1 and 'S13' in md2
          and '常见原因是改的是期望值' in md2, str(rrc2['stats']))
    _mark('S13', 'ok', path=reg2)
    rrc3 = session_run({'action': 'reconcile', 'path': prc,
                        'registry_path': reg2})
    check("标回「正确」后方向相反归零",
          rrc3['stats']['disagree'] == 0, str(rrc3['stats']))
    # 另一头：会话记的是「对照不符」，场景表标「正确」
    st_rc = json.loads(text_of(prc))
    st_rc['reviews'][0]['passed'] = False
    with io.open(prc, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(st_rc, ensure_ascii=False, indent=2))
    rrc4 = session_run({'action': 'reconcile', 'path': prc,
                        'registry_path': reg2})
    check("另一头也认：引擎对照不符 / 你标了正确",
          rrc4['stats']['disagree'] == 1
          and '对照不符' in (rrc4.get('markdown') or ''), str(rrc4['stats']))
    bad_reg2 = os.path.join(d, '不是场景表2.txt')
    with io.open(bad_reg2, 'w', encoding='utf-8') as fh:
        fh.write('不是场景表')
    check("场景表读不到 → registry_unreadable（不编对账）",
          session_run({'action': 'reconcile', 'path': prc,
                       'registry_path': bad_reg2})['verdict']
          == 'registry_unreadable')
    rout = os.path.join(d, '对账.md')
    rrc5 = session_run({'action': 'reconcile', 'path': prc,
                        'out_file': rout})
    check("对账可写文件且 LF",
          rrc5['verdict'] == 'reconciled_written' and os.path.exists(rout)
          and '\r' not in text_of(rout), rrc5['verdict'])
    check("目标已存在且没开覆盖 → file_exists",
          session_run({'action': 'reconcile', 'path': prc,
                       'out_file': rout})['verdict'] == 'file_exists')
    check("导出目标 = 会话文件本身 → 拦下",
          session_run({'action': 'reconcile', 'path': prc,
                       'out_file': prc})['verdict'] == 'input_pending')
    check("导出目标是目录 → path_invalid",
          session_run({'action': 'reconcile', 'path': prc,
                       'out_file': d})['verdict'] == 'path_invalid')
    check("out_file 非字符串 → input_pending",
          session_run({'action': 'reconcile', 'path': prc,
                       'out_file': 5})['verdict'] == 'input_pending')
    # ── 用例24：材料分批与续跑（大材料别一口气闷着）
    pk = os.path.join(d, '分批材料.md')
    with io.open(pk, 'w', encoding='utf-8', newline='\n') as fh:
        for i in range(1, 6):
            fh.write('第 %d 段：产品既要快又要稳' % i + '\n\n')
    pch = os.path.join(d, '分批.json')
    r1 = session_run({'action': 'add_file', 'path': pch, 'text_file': pk,
                      'max_segs': 2})
    imp1 = r1['imported']
    check("第一块导入 2 段、并给出续跑起点 3",
          len(imp1['imported']) == 2 and imp1['next_seg'] == 3,
          str(imp1.get('next_seg')))
    check("被 max_segs 挡下的段**不算处理过**（否则续跑会漏段）",
          [x['seg'] for x in imp1['skipped']] == [3, 4, 5]
          and imp1['next_seg'] == 3, str(imp1))
    r2 = session_run({'action': 'add_file', 'path': pch, 'text_file': pk,
                      'max_segs': 2, 'start_seg': imp1['next_seg']})
    check("按续跑起点接着导（第 3–4 段）",
          [x['seg'] for x in r2['imported']['imported']] == [3, 4]
          and r2['imported']['next_seg'] == 5, str(r2['imported']))
    r3 = session_run({'action': 'add_file', 'path': pch, 'text_file': pk,
                      'max_segs': 2, 'start_seg': 5})
    check("最后一块导完，不再给续跑起点",
          len(r3['imported']['imported']) == 1
          and r3['imported']['next_seg'] is None, str(r3['imported']))
    check("三段接续后会话轮次 = 5（一段没漏、没重复）",
          session_run({'action': 'state', 'path': pch})['state']['turns'] == 5)
    check("起点越界 → nothing_to_add（不假装导入成功）",
          session_run({'action': 'add_file', 'path': pch, 'text_file': pk,
                       'start_seg': 99})['verdict'] == 'nothing_to_add')
    for bad in (0, -1, 'x', True):
        check(f"起点非法（{bad!r}）→ input_pending",
              session_run({'action': 'add_file', 'path': pch,
                           'text_file': pk,
                           'start_seg': bad})['verdict'] == 'input_pending')
    st_imp = json.loads(text_of(pch))
    check("导入历史落了账（文件/起点/导入数/续跑起点）",
          len(st_imp['imports']) == 4      # 三次真导 + 一次起点越界的空尝试
          and st_imp['imports'][0]['file'] == '分批材料.md'
          and st_imp['imports'][0]['start_seg'] == 1
          and st_imp['imports'][0]['next_seg'] == 3, str(st_imp['imports'][0]))
    check("起点越界那次也照实记（导入 0 段），不假装没发生",
          st_imp['imports'][-1]['imported'] == 0
          and st_imp['imports'][-1]['start_seg'] == 99,
          str(st_imp['imports'][-1]))
    check("会话汇总里带导入次数",
          session_run({'action': 'state',
                       'path': pch})['state']['imports'] == 4)
    md_k = session_run({'action': 'report', 'path': pch})['markdown']
    check("台账有材料导入历史段且行数 = 导入次数记载数",
          '## 材料导入历史' in md_k
          and len([l for l in md_k.split('\n')
                   if l.startswith('| ') and '分批材料.md' in l]) == 4,
          md_k[md_k.find('## 材料导入历史'):][:200])
    check("台账写明未处理原因与续跑命令",
          '--from-seg' in md_k and '不会被静默丢掉' in md_k)
    # 单段过长：永久处理不了的那段不拦着续跑
    plong = os.path.join(d, '超长段.md')
    with io.open(plong, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('A' * 60 + '\n\n' + '产品既要快又要稳' + '\n')
    pl = os.path.join(d, '超长.json')
    rl = session_run({'action': 'add_file', 'path': pl, 'text_file': plong,
                      'max_seg_chars': 10})
    check("超长段永久跳过，续跑起点不被它挡住",
          rl['imported']['next_seg'] is None
          and rl['imported']['blocked_segs'] == [1], str(rl['imported']))
    session_run({'action': 'reset', 'path': pch})
    check("reset 连导入历史一起清",
          json.loads(text_of(pch))['imports'] == [])
    # ── 用例25：简报整合导入与续跑（有未处理段就给出续跑命令）
    pbi = os.path.join(d, '简报导入.json')
    session_run({'action': 'add_file', 'path': pbi, 'text_file': pk,
                 'max_segs': 2})
    rb1 = session_run({'action': 'brief', 'path': pbi})
    mb1 = rb1.get('markdown') or ''
    check("简报有「材料导入与续跑」段",
          '## 材料导入与续跑' in mb1, mb1[:500])
    check("简报列出文件名与按记录累计导入段数",
          '分批材料.md' in mb1 and '累计导入 2 段' in mb1, mb1[:700])
    check("一句话状态标出待续跑文件数",
          '待续跑文件 1 个' in mb1, mb1[:300])
    check("有未处理段 → 给出带 --from-seg 的续跑命令",
          '--from-seg 3' in mb1 and '--chunk 20' in mb1, mb1[:800])
    check("简报写明未处理段不会被静默丢掉",
          '不会被静默丢掉' in mb1)
    session_run({'action': 'add_file', 'path': pbi, 'text_file': pk,
                 'max_segs': 5, 'start_seg': 3})
    rb2 = session_run({'action': 'brief', 'path': pbi})
    mb2 = rb2.get('markdown') or ''
    check("导完之后不再给续跑命令，改为明说已处理过",
          '--from-seg' not in mb2 and '都处理过了' in mb2, mb2[:800])
    check("同一文件多条记录 → 累计导入段数按记录相加（2+3=5）",
          '累计导入 5 段' in mb2, mb2[:800])
    check("导完后一句话状态不再标待续跑",
          '待续跑文件' not in mb2, mb2[:300])
    sha_bi = sha(pbi)
    session_run({'action': 'brief', 'path': pbi})
    check("简报只读：会话文件 sha256 未变", sha(pbi) == sha_bi)
    pno = os.path.join(d, '无导入简报.json')
    session_run({'action': 'add', 'path': pno, 'text': TXT_CONFLICT})
    mb3 = session_run({'action': 'brief', 'path': pno})['markdown']
    check("没导过材料的会话不硬塞导入段（没记录就不写）",
          '材料导入与续跑' not in mb3, mb3[:400])
    # ── 用例26：四个导出动作的坏路径口径必须一致（去重后仍是一套契约）
    pdup = os.path.join(d, '四导出.json')
    session_run({'action': 'add', 'path': pdup, 'text': TXT_CONFLICT})
    session_run({'action': 'review', 'path': pdup, 'scene_id': 'S13'})
    session_run({'action': 'progress', 'path': pdup})
    acts = ['report', 'worksheet', 'brief', 'reconcile']
    same_target = {a: session_run({'action': a, 'path': pdup,
                                   'out_file': pdup})['verdict'] for a in acts}
    check("四个导出动作：目标=会话文件时结论一致（都是 input_pending）",
          set(same_target.values()) == {'input_pending'}, str(same_target))
    same_dir = {a: session_run({'action': a, 'path': pdup,
                                'out_file': d})['verdict'] for a in acts}
    check("四个导出动作：目标是目录时结论一致（都是 path_invalid）",
          set(same_dir.values()) == {'path_invalid'}, str(same_dir))
    same_bad = {a: session_run({'action': a, 'path': pdup,
                                'out_file': 5})['verdict'] for a in acts}
    check("四个导出动作：out_file 非字符串时结论一致（都是 input_pending）",
          set(same_bad.values()) == {'input_pending'}, str(same_bad))
    writ = {}
    for a in acts:
        out = os.path.join(d, '四导出-%s.md' % a)
        writ[a] = session_run({'action': a, 'path': pdup,
                               'out_file': out})['verdict']
        again = session_run({'action': a, 'path': pdup,
                             'out_file': out})['verdict']
        writ[a] = (writ[a], again)
    check("四个导出动作：都能写出文件，且二次导出都不覆盖（file_exists）",
          all(v[0].endswith('_written') and v[1] == 'file_exists'
              for v in writ.values()), str(writ))
    # ── 用例27：隐私导出（材料原文可隐去，便于把台账给别人看）
    prd = os.path.join(d, '隐私.json')
    session_run({'action': 'add', 'path': prd, 'text': TXT_CONFLICT})
    session_run({'action': 'add', 'path': prd, 'text': '这句话是假的'})
    full_md = session_run({'action': 'report', 'path': prd})['markdown']
    red_md = session_run({'action': 'report', 'path': prd,
                          'redact': True})['markdown']
    check("普通台账带材料原文（对照组）", TXT_CONFLICT in full_md)
    check("隐私导出：长材料原文不出现，只留字数与开头",
          TXT_CONFLICT not in red_md and '已隐去' in red_md
          and '开头「产品既要三周上线…' in red_md, red_md[:400])
    check("隐私导出：短材料连开头也隐（否则短材料等于没隐）",
          '这句话是假的' not in red_md and '材料偏短' in red_md, red_md[:600])
    check("隐私导出头部标注（看得出一份台账被隐过）",
          '隐私导出' in red_md, red_md[:200])
    check("隐私导出仍保留结构与判断（轮次/判类/执行）",
          '### 1. T2' in red_md and '### 2. T6' in red_md
          and '| 1 |' in red_md)
    check("隐私导出与普通导出的规模数字一致（只是隐了原文）",
          ('轮次 2' in red_md) and ('轮次 2' in full_md))
    sha_rd = sha(prd)
    session_run({'action': 'report', 'path': prd, 'redact': True})
    check("隐私导出只读：会话文件 sha256 未变", sha(prd) == sha_rd)
    out_rd = os.path.join(d, '隐私台账.md')
    r_rd = session_run({'action': 'report', 'path': prd, 'out_file': out_rd,
                        'redact': True})
    check("隐私导出能写文件且内容确实隐过",
          r_rd['verdict'] == 'report_written'
          and TXT_CONFLICT not in text_of(out_rd), r_rd['verdict'])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/243 通过")
raise SystemExit(0 if PASS == 243 else 1)
