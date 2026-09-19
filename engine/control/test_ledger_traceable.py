# -*- coding: utf-8 -*-
"""
test_ledger_traceable.py — 不变式：台账里的每个数字都能在会话 JSON 里找到来源
================================================================
为什么要有这条：台账是给人看/给作者存档的 Markdown。它由代码拼字符串生成——
**拼错一个数、多打一行、把两个来源串了，人看不出来**。这里把"台账不会自己长
数字"焊死：逐项拿台账与生成它的会话 JSON 对照。

对账的项：
    逐条诊断条数 = turns 数 · 墙事件行数 = walls 数 · 修正史条数 = revisions 数 ·
    复核记录行数 = reviews 数 · 快照行数 = snapshots 数 ·
    台账里出现的题型 ⊆ JSON 里出现过的题型 ·
    轮次号不越界 · 「挂在轮次 N」的 N 必须真存在 ·
    材料原文能在 JSON 里找到

运行：python engine/control/test_ledger_traceable.py
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.control.session import run as session_run  # noqa: E402

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


def section(md, title):
    """取 Markdown 里某个二级标题下的内容。"""
    m = re.search(r'^## %s.*?$(.*?)(?=^## |\Z)' % re.escape(title), md,
                  re.S | re.M)
    return m.group(1) if m else ''


def rows(block):
    """表格数据行（排除表头与分隔行）。"""
    out = []
    for line in block.split('\n'):
        s = line.strip()
        if s.startswith('|') and not re.match(r'^\|[\s:|-]+\|$', s):
            out.append(s)
    return [r for r in out if not r.startswith('| #') and '场景' not in r[:8]
            and '轮次' not in r[:8]][:]


TXT_A = '产品既要三周上线又要十二周合规，销售和研发各执一词'
TXT_B = '这句话是假的，反复震荡'
TXT_T5 = '原来以为这个方案要十二周，现在发现三周就行'
TXT_FILL = '帮我看看这个怎么办才好'

print("台账可核对性 · 不变式检查")
print("=" * 60)

d = tempfile.mkdtemp(prefix='pe_trace_')
try:
    p = os.path.join(d, '会话.json')
    session_run({'action': 'add', 'path': p, 'text': TXT_A, 'clues': True})
    session_run({'action': 'add', 'path': p, 'text': TXT_B,
                 'structured': {'sentence': 'liar'}})
    session_run({'action': 'add', 'path': p, 'text': TXT_T5})
    session_run({'action': 'add', 'path': p, 'text': TXT_FILL})
    session_run({'action': 'revise', 'path': p, 'beliefs': ['P→Q', 'P'],
                 'new_info': '¬Q', 'turn': 3})
    session_run({'action': 'review', 'path': p, 'scene_id': 'S13'})
    session_run({'action': 'progress', 'path': p})
    state = json.loads(io.open(p, encoding='utf-8').read())
    md = session_run({'action': 'report', 'path': p})['markdown']

    turns = state['turns']
    walls = state['walls']
    revs = state['revisions']
    revs_list = state['reviews']
    snaps = state['snapshots']

    check("前置：会话里四类记录都有（否则本用例空跑）",
          turns and walls and revs and revs_list and snaps,
          'turns=%d walls=%d revs=%d reviews=%d snaps=%d'
          % (len(turns), len(walls), len(revs), len(revs_list), len(snaps)))

    # ── 逐条诊断
    detail_block = section(md, '逐条诊断')
    heads = re.findall(r'^### (\d+)\. ', detail_block, re.M)
    check("台账逐条数 = 会话轮次数",
          len(heads) == len(turns), '%d vs %d' % (len(heads), len(turns)))
    check("台账轮次号与会话一致（顺序也对）",
          heads == [str(t['i']) for t in turns], str(heads))
    check("台账里的材料原文都能在会话里找到",
          all(t['text'].split('\n')[0][:20] in md for t in turns),
          str([t['text'][:12] for t in turns]))

    # ── 题型不凭空出现
    allowed_types = {t['type'] for t in turns}
    for r in revs_list:
        allowed_types |= {r['expect'].split('-')[0], r['actual'].split('-')[0]}
    md_types = set(re.findall(r'\bT\d{1,2}\b', md))
    check("台账里的题型都来自会话记录（没有凭空冒出的题型）",
          md_types <= allowed_types,
          '多出: %s' % sorted(md_types - allowed_types))

    # ── 墙事件
    wall_block = section(md, '墙事件')
    wall_rows = rows(wall_block)
    check("台账墙事件行数 = 会话墙事件数",
          len(wall_rows) == len(walls), '%d vs %d' % (len(wall_rows),
                                                      len(walls)))
    check("墙事件里的构件名与 verdict 都来自会话",
          all(w['component'] in md and (w.get('component_verdict') or '') in md
              for w in walls), str(walls))

    # ── 修正史
    rev_block = section(md, '信念修正史')
    rev_items = re.findall(r'^- 第 (\d+) 次', rev_block, re.M)
    check("台账修正史条数 = 会话修正数",
          len(rev_items) == len(revs), '%d vs %d' % (len(rev_items), len(revs)))
    linked = re.findall(r'挂在轮次 (\d+)', rev_block)
    turn_ids = {t['i'] for t in turns}
    check("「挂在轮次 N」的 N 都真存在",
          all(int(n) in turn_ids for n in linked) and
          sorted(int(n) for n in linked) == sorted(
              r['source_turn'] for r in revs if r.get('source_turn')),
          str(linked))

    # ── 复核记录
    revw_block = section(md, '场景复核记录')
    revw_rows = rows(revw_block)
    check("台账复核记录行数 = 会话复核记录数",
          len(revw_rows) == len(revs_list), '%d vs %d' % (len(revw_rows),
                                                          len(revs_list)))
    check("复核记录里的场景 id 都来自会话",
          all(r['scene'] in revw_block for r in revs_list),
          str([r['scene'] for r in revs_list]))

    # ── 快照
    snap_block = section(md, '复核进度快照')
    snap_items = re.findall(r'^- \d{4}-\d\d-\d\d .*#(\d+)', snap_block, re.M)
    check("台账快照条数 = 会话快照数",
          len(snap_items) == len(snaps), '%d vs %d' % (len(snap_items),
                                                       len(snaps)))
    check("台账快照里的已复核/待复核数与 JSON 一致",
          all(('已复核 %d / 待复核 %d' % (s['checked'], s['unchecked']))
              in snap_block for s in snaps), snap_block[:200])

    # ── 规模行
    scale = re.search(r'^- 规模：轮次 (\d+) · 墙事件 (\d+) · 信念 (\d+) 条 · '
                      r'修正 (\d+) 次 · 复核记录 (\d+) 条',
                      md, re.M)
    check("台账规模行五个数字与会话一一对应",
          bool(scale) and (int(scale.group(1)), int(scale.group(2)),
                           int(scale.group(3)), int(scale.group(4)),
                           int(scale.group(5)))
          == (len(turns), len(walls), len(state['beliefs']), len(revs),
              len(revs_list)),
          scale.group(0) if scale else '规模行没找到')

    # ── 反向：会话里有的，台账不该漏
    check("会话里每条材料都在台账里出现过（没漏记）",
          all(t['text'].split('\n')[0][:16] in md for t in turns))
    check("台账出现过的轮次号不越界",
          all(int(n) <= len(turns) for n in
              re.findall(r'^### (\d+)\. ', detail_block, re.M) + linked + [1]),
          str(heads))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
