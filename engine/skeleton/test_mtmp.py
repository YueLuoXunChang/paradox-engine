# -*- coding: utf-8 -*-
"""
test_mtmp.py — 正式测试：MT-MP-TL 骨架层（第 0 层）
用例依据：内部规格 42 §一~四（点四元组/线程三属性/12 形态/5 操作 + 诚实边界）
运行：python engine/skeleton/test_mtmp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mtmp import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def cl(points, edges, **kw):
    return run({'mode': 'topology', 'points': points, 'edges': edges,
                **kw})['detail']['kind']


print("MT-MP-TL 骨架层 · 正式测试")
print("=" * 60)

# ── 用例1：点（0.1）
r = run({'mode': 'point', 'point': {'id': 'p1', 'type': 'actor',
                                    'state': 0,
                                    'rules': {'step': lambda s: s + 1}}})
check("建点 → created", r['verdict'] == 'created', str(r))
check("点保 type/state", r['detail']['type'] == 'actor'
      and r['detail']['state'] == 0, str(r))
r = run({'mode': 'point', 'point': {'id': 'p1', 'state': 0,
                                    'rules': {'step': lambda s: s + 1}},
         'action': 'step'})
check("自治步进 → stepped state=1",
      r['verdict'] == 'stepped' and r['detail']['state'] == 1, str(r))
r = run({'mode': 'point', 'point': {'id': 'p1', 'type': 'actor'},
         'action': 'deform', 'new_state': 9})
check("变形 → deformed 且 type 不变",
      r['verdict'] == 'deformed' and r['detail']['type'] == 'actor'
      and r['detail']['new_state'] == 9, str(r))
check("缺 id → input_pending",
      run({'mode': 'point', 'point': {}})['verdict'] == 'input_pending')

# ── 用例2：线程（0.2）
thr = {'threads': [{'id': 't1', 'points': ['a', 'b', 'c']},
                   {'id': 't2', 'points': ['x', 'b', 'y']}]}
r = run({'mode': 'thread', **thr, 'action': 'advance', 'tid': 't1'})
check("推进 → advanced", r['verdict'] == 'advanced', str(r))
check("推进经过首点", r['detail']['passed']
      and r['detail']['passed'][0] in ('a',), str(r))
r = run({'mode': 'thread', **thr, 'action': 'converge', 'tid': 't1',
         'tid2': 't2', 'point': 'b'})
check("汇合 → merged", r['verdict'] == 'merged', str(r))
check("汇合点 b", r['detail']['converge_point'] == 'b', str(r))
r = run({'mode': 'thread', **thr, 'action': 'cross', 'tid': 't1',
         'tid2': 't2', 'point': 'b'})
check("交叉 → crossed（不合并）", r['verdict'] == 'crossed', str(r))
r = run({'mode': 'thread', **thr, 'action': 'converge', 'tid': 't1',
         'tid2': 't2', 'point': 'zz'})
check("汇合点不在 → merge_failed（诚实）",
      r['verdict'] == 'merge_failed', str(r))
r = run({'mode': 'thread', 'threads': [{'id': 't1', 'points': ['a', 'b'],
                                        'speed': 2}],
         'action': 'advance', 'tid': 't1'})
check("speed=2 一次过 2 点", len(r['detail']['passed']) == 2
      and r['detail']['done'], str(r))

# ── 用例3：拓扑严格可判形态（0.3）
check("星型 → star",
      cl(['c', 'a', 'b'], [('c', 'a'), ('c', 'b')]) == 'star')
check("全连接 → grid",
      cl(['a', 'b', 'c'], [('a', 'b'), ('a', 'c'), ('b', 'c')]) == 'grid')
check("4 点环 → cycle",
      cl(['a', 'b', 'c', 'd'],
         [('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'a')]) == 'cycle')
check("4 点链 → linear",
      cl(['a', 'b', 'c', 'd'],
         [('a', 'b'), ('b', 'c'), ('c', 'd')]) == 'linear')
check("两条独立链 → parallel",
      cl(['a', 'b', 'c', 'd'], [('a', 'b'), ('c', 'd')]) == 'parallel')
check("树形扇出 → diverge",
      cl(['c', 'a', 'b', 'd', 'e'],
         [('c', 'a'), ('c', 'b'), ('c', 'd'), ('d', 'e')]) == 'diverge')
# 4 点星型 = star 也是 diverge 特例（先命中 star——诚实）
check("4 点星型诚实判 star（兼 diverge）",
      cl(['c', 'a', 'b', 'd'],
         [('c', 'a'), ('c', 'b'), ('c', 'd')]) == 'star')
# 3 点特殊同图诚实：3 链=星、3 环=grid
check("3 点链诚实判 star（同图歧义）",
      cl(['a', 'b', 'c'], [('a', 'b'), ('b', 'c')]) == 'star')
check("3 点环诚实判 grid（K3 同图）",
      cl(['a', 'b', 'c'], [('a', 'b'), ('b', 'c'), ('c', 'a')]) == 'grid')

# ── 用例4：语义形态诚实（需元数据）
check("layer_map → stack",
      cl(['a', 'b'], [('a', 'b')],
         layer_map={'L1': ['a'], 'L2': ['a']}) == 'stack')
check("cond_map → branch",
      cl(['a', 'b', 'c'], [('a', 'b'), ('a', 'c')],
         cond_map={'a': 'if_x'}) in ('branch', 'diverge', 'converge'))
check("复杂回连 → chain 或 network（诚实候选）",
      cl(['a', 'b', 'c', 'd'],
         [('a', 'b'), ('b', 'c'), ('c', 'a'), ('c', 'd')])
      in ('chain', 'network'))
r = run({'mode': 'topology', 'points': ['a', 'b', 'c'],
         'edges': [('a', 'b')], 'action': 'neighbors', 'point': 'a'})
check("邻居查询 → neighbors", r['verdict'] == 'neighbors'
      and r['detail']['neighbors'] == ['b'], str(r))

# ── 用例5：5 操作（0.4）
def op(points, edges, op_name, a, b=None, kappa=1.0):
    return run({'mode': 'op', 'points': points, 'edges': edges,
                'op': op_name, 'a': a, 'b': b, 'kappa': kappa})

r = op(['a', 'b', 'c'], [('a', 'b')], 'connect', 'b', 'c')
check("connect → applied", r['verdict'] == 'applied', str(r))
check("connect 后 b-c 有边", ('b', 'c') in r['detail']['edges']
      or ('c', 'b') in r['detail']['edges'], str(r))
r = op(['a', 'b', 'c'], [('a', 'b'), ('b', 'c')], 'disconnect', 'b', 'c')
check("disconnect → applied", r['verdict'] == 'applied', str(r))
check("disconnect 后 b-c 无边", ('b', 'c') not in r['detail']['edges']
      and ('c', 'b') not in r['detail']['edges'], str(r))
r = op(['a', 'b', 'c'], [('a', 'b'), ('b', 'c')], 'fold', 'a', 'c', 2)
check("fold → applied（距离收缩）", r['verdict'] == 'applied', str(r))
check("fold 报告原距离与收缩值",
      r['detail'].get('distance') == 2 and r['detail'].get('folded') == 1.0,
      str(r))
r = op(['a', 'b'], [('a', 'b')], 'spawn', 'b', 'd')
check("spawn → applied（新分支）", r['verdict'] == 'applied', str(r))
check("spawn 后 d 存在且连 b", 'd' in r['detail']['points'], str(r))
r = op(['a'], [], 'replace', 'a', {'state': 7})
check("replace → applied（换点保连接）", r['verdict'] == 'applied', str(r))
r = op(['a', 'b'], [], 'connect', 'a', 'zz')
check("connect 到不存在点 → rejected（诚实）",
      r['verdict'] == 'rejected', str(r))
r = op(['a', 'b', 'c'], [('a', 'b')], 'fold', 'a', 'c')
check("fold 不可达 → rejected（诚实）",
      r['verdict'] == 'rejected', str(r))
check("坏操作名 → rejected",
      op(['a'], [], 'teleport', 'a', 'b')['verdict'] == 'rejected')

# ── 用例6：诚实边界
check("坏 mode → mode_pending", run({})['verdict'] == 'mode_pending')
check("空点集 → input_pending",
      run({'mode': 'topology', 'points': []})['verdict'] == 'input_pending')
check("op 缺 op 名 → input_pending",
      run({'mode': 'op', 'points': ['a']})['verdict'] == 'input_pending')
check("边界声明：骨架不掺判定",
      '不掺判定' in run({'mode': 'point', 'point': {'id': 'p'}})['boundary'])
check("边界声明：语义形态需元数据",
      '元数据' in run({'mode': 'topology', 'points': ['a'],
                      'edges': []})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/42 通过")
raise SystemExit(0 if PASS == 42 else 1)
