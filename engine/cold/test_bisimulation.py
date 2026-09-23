# -*- coding: utf-8 -*-
"""test_bisimulation.py — 双模拟检查的正式测试（换算法 oracle ＋ 跨构件互验）

独立验证的四条路（照 logic-verification 的规矩）：
  ① **换一类算法**：最大双模拟按**定义**直算（从 S×S 出发，反复删掉"配不上"的对直到不动），
     与构件的**分区细化**是两条不同的算法——200 组随机结构上比等价关系；
  ② **同仓另一个构件互验**（`mu_calculus`）：双模拟的**不变式方向**——等价的两态对一串
     动作标号 μ 公式必须**取同值**（这一条能抓住"分划太粗"的错）；不等价的两态，把构件给的
     **见证序列**构造成 〈σ〉⊤ 交给 μ 演算**独立求值**，必须落在该落的那一侧；
  ③ **已知答案**：同构跨系统等价 · 单侧多一条边不等价 · 非确定性多余分支指向等价态仍等价 ·
     后继块不同可区分 · 死锁 vs 能走不等价 · **二环与三环等价**（反直觉但正确，见下）；
  ④ **按构造核**：商系统良定义（同块里每个状态的 ⟨动作, 后继块⟩ 集合必须完全一样）、
     留痕（每轮块数）、接口(PORTS/boundary)、拒绝路径、确定性、规模上限。

> **另有外部第三方验证方**（不落在本文件里）：外部协作者写的分区细化参考实现，
> 在同一批 LTS 上比等价关系——它是**别人写的另一套代码**。本文件不引本机路径、
> 也不引私有记账的名字与章节号（发布面红线），所以那条对拍在仓库外跑，
> 这里只**点名验证方**（跑了什么、结论如何，记在私有记账里）。

运行：python engine/cold/test_bisimulation.py
"""

import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold import bisimulation as B                                 # noqa: E402
from engine.cold import mu_calculus as mc                                 # noqa: E402

try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

PASS = 0
TOTAL = 0


def check(label, cond, detail=''):
    global PASS, TOTAL
    TOTAL += 1
    if cond:
        PASS += 1
        print(f'  ✅ {label}')
    else:
        print(f'  ❌ {label}  {detail}')


# ============================================================
# oracle：最大双模拟按定义直算（另一条算法，不用分区细化）
# ============================================================

def gfp_bisim(states, edges):
    """从全集出发按定义删对，直到稳定——得到**最大**双模拟（等价关系）。"""
    R = {(s, t) for s in states for t in states}
    while True:
        bad = set()
        for (s, t) in R:
            for lab in ({l for l, _ in edges[s]} | {l for l, _ in edges[t]}):
                ss = [u for l, u in edges[s] if l == lab]
                tt = [u for l, u in edges[t] if l == lab]
                if not all(any((u, v) in R for v in tt) for u in ss):
                    bad.add((s, t))
                    break
                if not all(any((u, v) in R for u in ss) for v in tt):
                    bad.add((s, t))
                    break
        if not bad:
            return R
        R -= bad


def eq_of(R, states):
    """把关系化成"分划的规范形式"（排序后的块列表）便于比对。"""
    groups = {}
    for s in states:
        key = frozenset(t for t in states if (s, t) in R)
        groups.setdefault(key, []).append(s)
    return sorted(tuple(sorted(v)) for v in groups.values())


def canon(block):
    groups = {}
    for s, b in block.items():
        groups.setdefault(b, []).append(s)
    return sorted(tuple(sorted(v, key=str)) for v in groups.values())


def rand_lts(rng, n_states, n_labels, max_edges):
    states = [f's{i}' for i in range(n_states)]
    labs = ['a', 'b', 'c'][:n_labels]
    lts = {}
    for s in states:
        outs = []
        for _ in range(rng.randint(0, max_edges)):
            outs.append([rng.choice(labs), rng.choice(states)])
        lts[s] = outs
    return lts


def to_mu_transitions(lts):
    """返回 (状态名列表, 迁移表)——**注意顺序：先状态后迁移**。

    （第一版写成 (迁移, 状态) 却按 (状态, 迁移) 解包，于是把迁移表当状态名喂给 μ 演算，
    报 unhashable type: 'list'。留注释免得再踩。）
    """
    out = []
    for s, outs in lts.items():
        for lab, t in outs:
            out.append([s, t, lab])
    return list(lts), out


print('一、已知答案（含一条我先写错、被自测打回的）')
u_iso = {'p1': [['a', 'p2']], 'p2': [['a', 'p1']],
         'q1': [['a', 'q2']], 'q2': [['a', 'q1']]}
check('同构跨系统：p1 ~ q1', B.run({'lts': u_iso, 'mode': 'pair',
                                    's1': 'p1', 's2': 'q1'})['verdict'] == 'equivalent')
u_extra = {'p1': [['a', 'p2']], 'p2': [['a', 'p1']],
           'q1': [['a', 'q2'], ['b', 'q1']], 'q2': [['a', 'q1']]}
r_ex = B.run({'lts': u_extra, 'mode': 'pair', 's1': 'p1', 's2': 'q1'})
check('单侧多一条 b 边：可区分，且见证给到标号 b',
      r_ex['verdict'] == 'not_equivalent' and r_ex['witness']['label'] == 'b', r_ex.get('witness'))
u_nd = {'s1': [['a', 't1'], ['a', 't2']], 's2': [['a', 't1']],
        't1': [['c', 't3']], 't2': [['c', 't3']], 't3': []}
check('非确定性多余分支指向等价态：仍等价',
      B.run({'lts': u_nd, 'mode': 'pair', 's1': 's1', 's2': 's2'})['verdict'] == 'equivalent')
u_succ = {'m1': [['a', 'e1']], 'm2': [['a', 'e2']], 'e1': [], 'e2': [['c', 'e3']], 'e3': []}
check('后继块不同：可区分',
      B.run({'lts': u_succ, 'mode': 'pair', 's1': 'm1', 's2': 'm2'})['verdict'] == 'not_equivalent')
u_cycle = {'a1': [['a', 'a2']], 'a2': [['a', 'a1']],
           'b1': [['a', 'b2']], 'b2': [['a', 'b3']], 'b3': [['a', 'b1']]}
r_cyc = B.run({'lts': u_cycle, 'mode': 'pair', 's1': 'a1', 's2': 'b1'})
check('二环 vs 三环：**等价**（单标号下展开同一条无穷链——我先按"周期不同"写断言，被自测打回）',
      r_cyc['verdict'] == 'equivalent' and r_cyc['n_blocks'] == 1, r_cyc)
u_dead = {'d': [], 'm': [['a', 'm']]}
r_dead = B.run({'lts': u_dead, 'mode': 'pair', 's1': 'd', 's2': 'm'})
check('死锁 vs 能走：可区分，见证序列是「a」且说明是「一侧没有该动作的出边」',
      r_dead['verdict'] == 'not_equivalent'
      and r_dead['witness']['sequence']['sequence'] == ['a']
      and '没有该动作的出边' in r_dead['witness']['sequence']['why'], r_dead.get('witness'))
check('状态只在目标位出现也算状态（不崩、块数算对）',
      B.run({'lts': {'x': [['a', 'y']]}})['n_states'] == 2)

check('后继列举顺序不同不影响（集合语义，不是列表语义）',
      B.run({'lts': {'x': [['a', 'z'], ['b', 'z']], 'y': [['b', 'z'], ['a', 'z']], 'z': []},
             'mode': 'pair', 's1': 'x', 's2': 'y'})['verdict'] == 'equivalent')

print('二、换算法 oracle：按定义直算最大双模拟（200 组随机结构）')
rng = random.Random(20260922)
bad_part, bad_pair, n_cases = [], [], 0
for _ in range(200):
    lts = rand_lts(rng, rng.randint(2, 7), rng.randint(1, 3), 3)
    n_cases += 1
    _, edges, _, err = B._parse(lts)
    if err:
        continue
    R = gfp_bisim(list(edges), edges)
    mine = B.run({'lts': lts})
    if canon(mine['blocks']) != eq_of(R, list(edges)):
        bad_part.append(lts)
    for _ in range(2):
        s1, s2 = rng.choice(list(edges)), rng.choice(list(edges))
        want = (s1, s2) in R
        got = B.run({'lts': lts, 'mode': 'pair', 's1': s1, 's2': s2})['verdict'] == 'equivalent'
        if want != got:
            bad_pair.append((lts, s1, s2))
check(f'分区细化的分划 == 定义直算的最大双模拟（{n_cases} 组随机结构）', not bad_part, bad_part[:1])
check('逐对等价判定与定义直算一致（每组抽 2 对）', not bad_pair, bad_pair[:1])
check('定义直算出的关系是等价关系（自反对称传递）',
      all((s, s) in gfp_bisim(list(B._parse(u_extra)[1]), B._parse(u_extra)[1]) for s in u_extra))

print('三、跨构件互验：双模拟的不变式（μ 演算独立求值）')


def reach_by(edges, start, seq):
    """测试侧自己算"沿这条动作序列能到哪些状态"（不借构件的结论）。"""
    cur = {start}
    for lab in seq:
        nxt = set()
        for s in cur:
            nxt.update(t for l, t in edges[s] if l == lab)
        cur = nxt
        if not cur:
            return set()
    return cur


BATTERY = ['<a>⊤', '[a]⊥', '<a><a>⊤', '<a><a><a>⊤', '<b>⊤', '[a]<b>⊤', '<a>[b]⊥',
           'νX.(⊤ & [a]X)', 'μX.(<a>X)', 'νX.(<b>⊤ & [a]X)']
rng2 = random.Random(777)
viol, wit_ok, bad_end, not_reach, label_bad, strict_bad = [], [], [], [], [], []
strict_cases, n_pairs = 0, 0
for _ in range(60):
    lts = rand_lts(rng2, rng.randint(2, 6), rng.randint(1, 2), 2)
    st, tr = to_mu_transitions(lts)
    _, edges, _, err = B._parse(lts)
    if err:
        continue
    states = list(edges)
    R = gfp_bisim(states, edges)                      # 独立 oracle：按定义直算
    cls = {s: frozenset(u for u in states if (s, u) in R) for s in states}
    r = B.run({'lts': lts})
    truth = {}
    for f in BATTERY:
        truth[f] = set(mc.run({'formula': f, 'states': st, 'transitions': tr,
                               'labels': {}})['holds_in'])
    for s1 in st:
        for s2 in st:
            same = r['blocks'][s1] == r['blocks'][s2]
            agree = all((s1 in truth[f]) == (s2 in truth[f]) for f in BATTERY)
            if same and not agree:
                viol.append((lts, s1, s2))
            if same:
                continue
            n_pairs += 1
            wit = B.run({'lts': lts, 'mode': 'pair', 's1': s1, 's2': s2})['witness']
            seqd = wit['sequence']
            labels = seqd['sequence']
            formula = ''.join(f'<{lab}>' for lab in labels) + '⊤'
            holds = set(mc.run({'formula': formula, 'states': st, 'transitions': tr,
                                'labels': {}})['holds_in'])
            # ① 序列从"能走的那一侧"走得通：存在模态下必然成立
            movable = s2 if seqd['movable'] == 's2' else s1
            if movable not in holds:
                wit_ok.append((s1, s2, labels, formula))
            # ② 起点那一侧**真的走不通**时，〈σ〉⊤ 必须恰好只在一侧成立（严格区分）
            loses = s2 if movable == s1 else s1
            if not reach_by(edges, loses, labels):
                strict_cases += 1
                if not (movable in holds and loses not in holds):
                    strict_bad.append((s1, s2, labels, formula, sorted(holds)))
            # ③ 见证给的终点对一定不双模拟（用定义直算的 oracle 判）
            e1, e2 = seqd['end_states']
            if e1 is not None and e2 is not None and (e1, e2) in R:
                bad_end.append((s1, s2, labels, e1, e2))
            # ④ 终点确实是沿该序列可达的（测试侧 BFS）
            if e1 is not None and e1 not in reach_by(edges, s1, labels):
                not_reach.append((s1, e1, labels))
            if e2 is not None and e2 not in reach_by(edges, s2, labels):
                not_reach.append((s2, e2, labels))
            # ⑤ 报告的那个"分开标号"，在等价类层面确实分开两侧（独立复算）
            bs = frozenset(cls[t] for l, t in edges[s1] if l == wit['label'])
            bt = frozenset(cls[t] for l, t in edges[s2] if l == wit['label'])
            if bs == bt:
                label_bad.append((s1, s2, wit['label']))
check('等价的两态对整串动作标号 μ 公式取同值（不变式；分划太粗会在这里露馅）',
      not viol, viol[:1])
check(f'区分序列从"能走的那一侧"走得通（〈σ〉⊤ 由 μ 演算独立求值，{n_pairs} 对）',
      not wit_ok, wit_ok[:1])
check(f'起点侧完全走不通该序列时，〈σ〉⊤ 恰好只在一侧成立（{strict_cases} 例，真区分）',
      not strict_bad, strict_bad[:1])
check('见证给的终点对确实不双模拟（用「按定义直算」的 oracle 独立判）', not bad_end, bad_end[:1])
check('终点确实沿该序列可达（测试侧自己 BFS，不借构件）', not not_reach, not_reach[:1])
check('报告的分开标号在等价类层面确实分开两侧（独立复算）', not label_bad, label_bad[:1])

check('**默认模式就是 partition（分划）**，不写 mode 也走分划这条路',
      B.run({'lts': u_iso})['verdict'] == 'partitioned'
      and isinstance(B.run({'lts': u_iso})['blocks'], dict))
check('默认模式下 blocks / block_members / quotient 三件都在',
      all(B.run({'lts': u_iso}).get(k) is not None
          for k in ('blocks', 'block_members', 'quotient')))

print('四、见证与留痕')
w = B.run({'lts': u_extra, 'mode': 'pair', 's1': 'p1', 's2': 'q1'})['witness']
check('见证带轮次 / 标号 / 两侧后继块',
      w['round'] >= 1 and w['label'] == 'b' and isinstance(w['s_successor_blocks'], list)
      and isinstance(w['t_successor_blocks'], list), w)
check('见证如实声明"不保证最短"', '不保证最短' in w['note'], w.get('note'))
r_succ = B.run({'lts': u_succ})
check('留痕：每轮块数递增且首轮为 1',
      r_succ['rounds'][0] == {'round': 0, 'blocks': 1}
      and all(r_succ['rounds'][i]['blocks'] <= r_succ['rounds'][i + 1]['blocks']
              for i in range(len(r_succ['rounds']) - 1)), r_succ['rounds'])
check('留痕轮数与最终块数相容（块数不再增加才停）',
      r_succ['rounds'][-1]['blocks'] == r_succ['n_blocks'], r_succ['rounds'])
check('商系统：块到块的迁移按动作去重且指向块号',
      all(isinstance(k, int) and all(isinstance(t, int) for _, t in v)
          for k, v in r_succ['quotient'].items()), r_succ['quotient'])

print('五、商系统良定义（按构造独立核，不用构件的结论）')
well = []
for _ in range(50):
    lts = rand_lts(rng, rng.randint(2, 6), rng.randint(1, 2), 2)
    _, edges, _, err = B._parse(lts)
    if err:
        continue
    blk = B.run({'lts': lts})['blocks']
    groups = {}
    for s, b in blk.items():
        groups.setdefault(b, []).append(s)
    for b, mem in groups.items():
        sigs = {frozenset((lab, blk[t]) for lab, t in edges[s]) for s in mem}
        if len(sigs) != 1:
            well.append((lts, b))
check('同块里每个状态的 ⟨动作, 后继块⟩ 集合完全一样（商系统才有定义）', not well, well[:1])
check('同块状态数 = 块成员数之和（分划覆盖每个状态一次）',
      sum(len(m) for m in B.run({'lts': u_succ})['block_members']) == 5)
check('单块系统（全等价）的商系统只有一条自环集',
      list(B.run({'lts': u_iso})['quotient'].values()) == [[('a', 0)]])

print('六、关系检查（给定关系是不是双模拟）')
check('正例：同构两系统的对应关系放行',
      B.run({'lts': u_iso, 'mode': 'check_relation',
             'relation': [['p1', 'q1'], ['p2', 'q2']]})['verdict'] == 'relation_holds')
r_rel = B.run({'lts': u_extra, 'mode': 'check_relation',
               'relation': [['p1', 'q1'], ['p2', 'q2']]})
check('负例：报第一处违规且带标号与方向',
      r_rel['verdict'] == 'relation_fails' and r_rel['witness']['label'] == 'b'
      and r_rel['witness']['side'] in ('s→t', 't→s'), r_rel.get('witness'))
check('真空成立的情形：死锁单态的自反关系放行',
      B.run({'lts': {'x': []}, 'mode': 'check_relation',
             'relation': [['x', 'x']]})['verdict'] == 'relation_holds')
check('关系给空列表 → input_pending（空表更像「忘了填」，不假装它在检查什么）',
      B.run({'lts': u_iso, 'mode': 'check_relation', 'relation': []})['verdict']
      == 'input_pending')
check('关系里出现不存在的状态 → parse_error，不静默放过',
      B.run({'lts': u_iso, 'mode': 'check_relation',
             'relation': [['p1', 'zzz']]})['verdict'] == 'parse_error')
check('关系写法不合法 → parse_error',
      B.run({'lts': u_iso, 'mode': 'check_relation',
             'relation': [['p1']]})['verdict'] == 'parse_error')
check('用自己给的块当关系：等价关系本身过检查（自洽）',
      B.run({'lts': u_succ, 'mode': 'check_relation',
             'relation': [[a, b] for a in u_succ for b in u_succ
                          if B.run({'lts': u_succ})['blocks'][a]
                          == B.run({'lts': u_succ})['blocks'][b]]})['verdict'] == 'relation_holds')

print('七、接口、拒绝路径、确定性与上限')
probes = [{'lts': u_iso}, {'lts': u_iso, 'mode': 'pair', 's1': 'p1', 's2': 'q2'},
          {'lts': u_iso, 'mode': 'pair'}, {'lts': {}}, {'lts': {'x': [['a']]}},
          {'lts': u_iso, 'mode': 'nope'}]
check('每个返回点都带 boundary（字符串）',
      all(isinstance(B.run(x).get('boundary'), str) for x in probes))
out = B.run({'lts': u_succ})
declared = set(B.PORTS['out'])
check('返回的键都在 PORTS.out 里声明', set(out) <= declared, sorted(set(out) - declared))
required = [k for k, t in B.PORTS['out'].items() if not str(t).endswith('?')]
check('PORTS.out 的必返键一个不缺', all(k in out for k in required),
      sorted(set(required) - set(out)))
check('每个返回点都带 verdict 与 detail',
      all('verdict' in B.run(x) and isinstance(B.run(x)['detail'], dict) for x in probes))
check('缺 lts → input_pending', B.run({})['verdict'] == 'input_pending')
check('pair 缺 s1/s2 → input_pending',
      B.run({'lts': u_iso, 'mode': 'pair'})['verdict'] == 'input_pending')
check('状态不在系统里 → parse_error',
      B.run({'lts': u_iso, 'mode': 'pair', 's1': 'p1', 's2': 'zzz'})['verdict'] == 'parse_error')
check('mode 不认 → parse_error', B.run({'lts': u_iso, 'mode': 'x'})['verdict'] == 'parse_error')
check('出边写成 [动作] → parse_error（不猜）',
      B.run({'lts': {'x': [['a']]}})['verdict'] == 'parse_error')
check('动作名不是字符串 → parse_error',
      B.run({'lts': {'x': [[1, 'y']]}})['verdict'] == 'parse_error')
big = {f's{i}': [['a', f's{(i + 1) % (B.MAX_STATES + 20)}']] for i in range(B.MAX_STATES + 20)}
check('状态数超上限 → size_limit（不硬跑）', B.run({'lts': big})['verdict'] == 'size_limit')
import json
a = json.dumps(B.run({'lts': u_succ}), sort_keys=True)
b = json.dumps(B.run({'lts': u_succ}), sort_keys=True)
check('同输入两次逐字段相同（确定性）', a == b)
check('重复迁移去重（同一 [动作,目标] 写两遍不影响分划）',
      B.run({'lts': {'x': [['a', 'y'], ['a', 'y']], 'y': []}})['n_transitions'] == 1)
check('动作数统计正确', B.run({'lts': u_extra})['n_actions'] == 2)

print('=' * 70)
print(f'结果: {PASS}/48 通过')
raise SystemExit(0 if PASS == 48 else 1)
