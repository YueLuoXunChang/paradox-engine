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


def text_of(path):
    with io.open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


TXT_WALL = '这句话是假的，反复震荡，越绕越深'
TXT_CONFLICT = '产品既要三周上线又要十二周合规，销售和研发各执一词'
TXT_PLAIN = '帮我看看这个怎么办才好'

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
    check("开了覆盖才重写（report_written）",
          ro['verdict'] == 'report_written' and text_of(tout) == body)
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
finally:
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/68 通过")
raise SystemExit(0 if PASS == 68 else 1)
