# -*- coding: utf-8 -*-
"""bisimulation.py — 双模拟检查：两个状态是不是"行为上分不开"（第 3 层按痛点接入）

概念来源：**外部经典共识**——Milner 的双模拟与分区细化、van Glabbeek 的行为等价谱系，
**归借鉴区**（落落三问：借什么=同标号逐步匹配的等价关系与它的分划算法；为什么=本仓
`mu_calculus` 能写"反复/最终/从此以后"这类过程性质，但**没有一件能判"两个系统/两个状态
是不是同一个东西"**——双模拟正是 μ 演算的不变式；怎么记账=标注来源归借鉴区，不混原创区）。

本构件做什么（一句话）：
    给一个**有限显式迁移系统**（状态 + 动作标号的迁移），算**最大双模拟**（最粗的那个分划，
    同块就是"行为上分不开"），判两个状态等不等价并给**可核的见证**，给定关系时判它**是不是**
    双模拟，并给出**商系统**（同块合并后的迁移）。

怎么算的（白话）：
    ① **分区细化（固定点）**：先把所有状态放一块；然后每个状态算一个"签名"＝
       ⟨当前它在哪一块，每个动作能到的**后继块集合**⟩（集合语义，所以非确定性天然处理得对），
       按签名重新分块；块数不再增加就停，此时同块 = 双模拟。**每轮的块数留痕**，
       一眼能看出"是不是只跑了一轮就停"。
    ② **等价判定**：两态同块 ⟺ 双模拟。
    ③ **不等价的见证**：从分划史里找出**第一个把它俩分开的轮次**、那个**动作标号**、
       两侧各自的后继块；再沿着"严格更早分开"的后继对**往下走**，得到一条
       **可核的区分序列**（s 能走、t 要么走不了、要么走到不等价的地方）。
       诚实：这条序列**不保证最短**，也不构造通用区分**公式**（那要指数级构造）。
    ④ **关系检查**：给定一个关系，逐对查"同标号的后继能不能配对上"（双向），
       配不上就报**第一处违规**。
    ⑤ **商系统**：把同块合并，块到块的迁移按动作去重——交给下游用。

统一接口：
    run(inputs: dict) -> dict
    输入:
        lts: dict——{状态: [[动作, 目标], ...]}（动作是字符串；目标没在键里也算状态，只是没有出边）
        mode: 'partition'（默认，算最大双模拟分划）|'pair'（判两态）|'check_relation'（判给定关系）
        s1, s2: 状态名（mode='pair' 时必需）
        relation: list[[状态, 状态], ...]（mode='check_relation' 时必需）
    输出:
        verdict: 'partitioned' | 'equivalent' | 'not_equivalent'
                 | 'relation_holds' | 'relation_fails'
                 | 'input_pending' | 'parse_error' | 'size_limit' | 'internal_error'
        n_states: int——状态数（含只作目标出现的状态）
        n_transitions: int——去重后的迁移条数
        n_actions: int——用到的动作标号数
        n_blocks: int?——最大双模拟的块数
        blocks: dict?——{状态: 块号}
        block_members: list?——每块里的状态（按块的确定顺序）
        rounds: list?——留痕：每一轮的块数
        equivalent: bool?——mode='pair' 时的结论
        witness: dict?——不等价／违规时的见证（轮次 · 标号 · 两侧后继块 · 区分序列）
        quotient: dict?——商系统 {块号: [[动作, 目标块号], ...]}
        detail: dict——口径与中间量
        boundary: str——诚实边界
    诚实边界：
        只做**强双模拟**（同标号逐步匹配、非确定性用集合语义）；**不做**弱双模拟/τ 等价、
        不做 up-to 技术、不做概率/加权/符号双模拟；系统必须**有限且显式列出**、动作名是字符串；
        状态数与迁移数有上限，超了报 `size_limit` **不硬跑**；
        不等价的见证是**可逐步核对的样例**（缺哪条边 / 哪一轮因哪个标号分开 / 一条区分序列），
        但**不保证最短、也不构造通用区分公式**；
        与 `mu_calculus` 的分工：它算"公式在哪些状态上成立"，本件判"两个状态是不是同一个行为"——
        两者可互验（不变式），但**不是一件事**；只诊断不决策。
"""

MAX_STATES = 300      # 状态数上限（超了 size_limit，不硬跑）
MAX_TRANS = 4000      # 迁移条数上限（判据阈值：测试里成对钉住 4000/4200 两侧）
MAX_ROUNDS = 400      # 护栏：细化轮数兜底——**实际不可达**（块数最多等于状态数，
                      # 而状态数已被 MAX_STATES 300 先兜住），留着只作保险，不作判据阈值

BOUNDARY = ('双模拟检查（第 3 层机制，概念来源：外部共识的 Milner 双模拟与分区细化，归借鉴区）：'
            '只判**强双模拟**（同标号逐步匹配、非确定性集合语义）——不做弱双模拟/τ 等价、'
            '不做 up-to、不做概率加权；系统必须有限显式且动作名是字符串，超规模如实报 size_limit；'
            '不等价的见证是可逐步核对的样例（缺边／分开的轮次与标号／一条区分序列），'
            '**不保证最短、也不给通用区分公式**；只诊断不决策。')

PORTS = {
    'in': {'lts': 'dict', 'mode': 'str?', 's1': 'any?', 's2': 'any?', 'relation': 'list?'},
    'out': {'verdict': 'str', 'n_states': 'int', 'n_transitions': 'int', 'n_actions': 'int',
            'n_blocks': 'int?', 'blocks': 'dict?', 'block_members': 'list?', 'rounds': 'list?',
            'equivalent': 'bool?', 'witness': 'dict?', 'quotient': 'dict?',
            'detail': 'dict', 'boundary': 'str'},
}


def _reply(verdict, **kw):
    """统一返回：PORTS.out 的键一个不少（可选键给 None），错误路径也带 boundary/detail。"""
    out = {'verdict': verdict, 'n_states': kw.pop('n_states', 0),
           'n_transitions': kw.pop('n_transitions', 0), 'n_actions': kw.pop('n_actions', 0),
           'n_blocks': kw.pop('n_blocks', None), 'blocks': kw.pop('blocks', None),
           'block_members': kw.pop('block_members', None), 'rounds': kw.pop('rounds', None),
           'equivalent': kw.pop('equivalent', None), 'witness': kw.pop('witness', None),
           'quotient': kw.pop('quotient', None), 'detail': kw.pop('detail', {}),
           'boundary': BOUNDARY}
    out.update(kw)
    return out


def _ok_state(x):
    """状态名：字符串或整数（bool 不算），要能进字典。"""
    return (isinstance(x, str) or (isinstance(x, int) and not isinstance(x, bool)))


def _parse(lts):
    """规范化 LTS：补上"只作目标出现"的状态、去重迁移、收集动作。"""
    states = set()
    edges = {}
    n_raw = 0
    for src, outs in lts.items():
        if not _ok_state(src):
            return None, None, None, '状态名只认字符串/整数：%r' % (src,)
        if not isinstance(outs, (list, tuple)):
            return None, None, None, '状态 %r 的出边必须是列表' % (src,)
        states.add(src)
        seen = []
        for e in outs:
            if not isinstance(e, (list, tuple)) or len(e) != 2:
                return None, None, None, '出边要写成 [动作, 目标]：%r' % (e,)
            lab, tgt = e[0], e[1]
            if not isinstance(lab, str) or not lab:
                return None, None, None, '动作名必须是非空字符串：%r' % (lab,)
            if not _ok_state(tgt):
                return None, None, None, '目标状态名只认字符串/整数：%r' % (tgt,)
            n_raw += 1
            states.add(tgt)
            if (lab, tgt) not in seen:
                seen.append((lab, tgt))
        edges[src] = seen
    for s in states:
        edges.setdefault(s, [])
    if len(states) > MAX_STATES:
        return None, None, None, ('超上限：状态 %d 个 > %d（不硬跑）'
                                  % (len(states), MAX_STATES))
    total = sum(len(v) for v in edges.values())
    if total > MAX_TRANS:
        return None, None, None, ('超上限：迁移 %d 条 > %d（不硬跑）'
                                  % (total, MAX_TRANS))
    acts = sorted({lab for v in edges.values() for lab, _ in v})
    return states, edges, acts, None


def _refine(states, edges, keep_history=True):
    """分区细化到固定点。返回 (最终分块, 每轮分块史, 每轮块数留痕)。"""
    order = sorted(states, key=lambda s: (isinstance(s, str), str(s)))
    block = {s: 0 for s in order}
    history = [dict(block)]
    trace = [{'round': 0, 'blocks': 1}]
    while True:
        index = {}
        new = {}
        for s in order:
            sig = (block[s], frozenset((lab, block[t]) for lab, t in edges[s]))
            if sig not in index:
                index[sig] = len(index)
            new[s] = index[sig]
        if len(index) == len(set(block.values())):
            return new, history, trace
        block = new
        if keep_history:
            history.append(dict(block))
        trace.append({'round': len(trace), 'blocks': len(index)})
        if len(trace) > MAX_ROUNDS:
            return None, history, trace


def _members(block):
    groups = {}
    for s, b in block.items():
        groups.setdefault(b, []).append(s)
    return [sorted(v, key=lambda x: (isinstance(x, str), str(x))) for _, v in sorted(groups.items())]


def _quotient(edges, block):
    out = {}
    for s, outs in edges.items():
        b = block[s]
        acc = out.setdefault(b, [])
        for lab, t in outs:
            if (lab, block[t]) not in acc:
                acc.append((lab, block[t]))
    return {b: v for b, v in sorted(out.items())}


def _succ_blocks(edges, block, s, lab):
    return sorted({block[t] for l, t in edges[s] if l == lab})


def _witness(history, edges, s, t):
    """不等价的见证：第一个把 s、t 分开的轮次 + 那个标号 + 两侧后继块 + 一条区分序列。

    `sequence.end_states` 给的是这条序列**走到头的那一对状态**：它们一定**不双模拟**
    （由"轮次严格递减"保证：每一步都在更早的一轮分开过）——这一条是本件最硬的可核断言，
    测试里用另一条算法（按定义直算的最大双模拟）独立验。
    """
    for k in range(1, len(history)):
        prev, now = history[k - 1], history[k]
        if prev[s] == prev[t] and now[s] != now[t]:
            labels = sorted({l for l, _ in edges[s]} | {l for l, _ in edges[t]})
            for lab in labels:
                sb, tb = _succ_blocks(edges, prev, s, lab), _succ_blocks(edges, prev, t, lab)
                if sb != tb:
                    seq = _distinguish_seq(history, edges, s, t, limit=len(history))
                    return {'round': k, 'label': lab, 's_successor_blocks': sb,
                            't_successor_blocks': tb, 'sequence': seq,
                            'note': '这条序列**从起点那一侧走得通**（存在模态下必然成立）；'
                                    '另一侧要么走不了、要么走到与终点不等价的地方；'
                                    '序列**不保证最短**，也不给通用区分公式'}
    return None


def _distinguish_seq(history, edges, s, t, limit):
    """沿"严格更早分开"的后继对往下走，得到一条可核的区分序列。

    依据：若 (s,t) 在第 k 轮分开，则存在标号 lab 让两侧的**后继块集合**不同；
    集合不同 ⇒ 必能挑出一对 lab-后继 (s',t') 在第 ≤ k−1 轮就分开了。轮次严格递减 ⇒ 一定停。
    若某一步有一侧**没有**该动作的出边，序列就停在这个标号上（"对方走不了这条动作"）。
    """
    seq = []
    cur_s, cur_t = s, t
    for _ in range(limit):
        k = next((i for i, blk in enumerate(history) if blk[cur_s] != blk[cur_t]), None)
        if not k:                      # 0 = 一开始就同块；None = 一直是同块 → 没得走
            break
        prev = history[k - 1]
        moved = False
        for lab in sorted({l for l, _ in edges[cur_s]} | {l for l, _ in edges[cur_t]}):
            sb = sorted({prev[u] for l, u in edges[cur_s] if l == lab})
            tb = sorted({prev[u] for l, u in edges[cur_t] if l == lab})
            if sb == tb:
                continue
            seq.append(lab)
            s_next = [u for l, u in edges[cur_s] if l == lab]
            t_next = [u for l, u in edges[cur_t] if l == lab]
            if not s_next or not t_next:
                return {'sequence': seq,
                        'why': ('s' if not s_next else 't') + ' 在这个状态下没有该动作的出边',
                        'movable': 's2' if not s_next else 's1',
                        'dead_end_state': (cur_s if not s_next else cur_t),
                        'missing_label': lab,
                        'end_states': [s_next[0] if s_next else None,
                                       t_next[0] if t_next else None],
                        'note': '缺边说的是**这条路上的那个状态**，不是起点——所以 〈σ〉⊤ 不一定'
                                '只在一侧成立（存在模态走别的分支也能成立）；要严格区分得用带'
                                '全称模态的公式，本件不给通用构造'}
            best = None                 # 挑分开得最早的那对后继（序列更短）
            for u in s_next:
                for v in t_next:
                    kk = next((i for i, blk in enumerate(history) if blk[u] != blk[v]),
                              len(history))
                    if best is None or kk < best[0]:
                        best = (kk, u, v)
            if best is None:
                return {'sequence': seq, 'why': '后继全部落在同一块（不该发生）'}
            cur_s, cur_t = best[1], best[2]
            moved = True
            break
        if not moved:
            break
    return {'sequence': seq, 'why': '沿最早分开的后继对走到不能再分（终点两块不同）',
            'movable': 'both', 'end_states': [cur_s, cur_t],
            'note': '这一对终点（两侧各一个）**一定不双模拟**——轮次严格递减保证的，'
                    '可用另一条算法独立复算'}


def run(inputs):
    """按 mode 走：partition（分划）／pair（等价判定）／check_relation（关系检查）。"""
    if not isinstance(inputs, dict):
        return _reply('parse_error', detail={'reason': '输入必须是 dict'})
    lts = inputs.get('lts')
    if not isinstance(lts, dict) or not lts:
        return _reply('input_pending', detail={'reason': '需要 lts（{状态: [[动作, 目标], ...]}）'})
    mode = inputs.get('mode', 'partition')
    if mode not in ('partition', 'pair', 'check_relation'):
        return _reply('parse_error', detail={'reason': 'mode 只认 partition / pair / check_relation',
                                             'got': mode})
    states, edges, acts, err = _parse(lts)
    if err:
        bad = 'size_limit' if err.startswith('超上限') else 'parse_error'
        return _reply(bad, detail={'reason': err})
    n_st, n_tr, n_ac = len(states), sum(len(v) for v in edges.values()), len(acts)

    block, history, trace = _refine(states, edges)
    if block is None:
        return _reply('internal_error', n_states=n_st, n_transitions=n_tr, n_actions=n_ac,
                      rounds=trace, detail={'reason': '细化轮数超上限（不该发生）'})
    n_blocks = len(set(block.values()))
    core = {'n_states': n_st, 'n_transitions': n_tr, 'n_actions': n_ac,
            'n_blocks': n_blocks, 'blocks': block, 'block_members': _members(block),
            'rounds': trace, 'quotient': _quotient(edges, block)}

    if mode == 'partition':
        return _reply('partitioned', **core,
                      detail={'note': '同块 = 强双模拟；块数是最粗的那个分划（唯一）'})

    if mode == 'pair':
        s1, s2 = inputs.get('s1'), inputs.get('s2')
        if s1 is None or s2 is None:
            return _reply('input_pending', **core,
                          detail={'reason': 'mode=pair 需要 s1 与 s2'})
        if s1 not in block or s2 not in block:
            return _reply('parse_error', **core,
                          detail={'reason': '状态不在系统里', 's1': s1, 's2': s2})
        same = block[s1] == block[s2]
        wit = None if same else _witness(history, edges, s1, s2)
        return _reply('equivalent' if same else 'not_equivalent', **core,
                      equivalent=same, witness=wit,
                      detail={'s1': s1, 's2': s2,
                              'note': '同块就是强双模拟（含非确定性集合语义）'})

    rel = inputs.get('relation')
    if not isinstance(rel, (list, tuple)) or not rel:
        return _reply('input_pending', **core,
                      detail={'reason': 'mode=check_relation 需要 relation=[[s, t], ...]'})
    pairs = []
    for p in rel:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            return _reply('parse_error', **core, detail={'reason': '关系要写成 [[s, t], ...]'})
        if p[0] not in block or p[1] not in block:
            return _reply('parse_error', **core,
                          detail={'reason': '关系里有不在系统里的状态', 'pair': list(p)})
        pairs.append((p[0], p[1]))
    rset = set(pairs)
    for (s, t) in pairs:
        for lab in sorted({l for l, _ in edges[s]} | {l for l, _ in edges[t]}):
            s_outs = [u for l, u in edges[s] if l == lab]
            t_outs = [u for l, u in edges[t] if l == lab]
            for u in s_outs:
                if not any((u, v) in rset for v in t_outs):
                    return _reply('relation_fails', **core, witness={
                        'from': s, 'to': t, 'label': lab, 'side': 's→t',
                        's_successor': u, 't_successors': t_outs,
                        'note': 's 这条动作的后继在 t 侧配不上（关系不是双模拟）'},
                        detail={'checked_pairs': len(pairs)})
            for v in t_outs:
                if not any((u, v) in rset for u in s_outs):
                    return _reply('relation_fails', **core, witness={
                        'from': s, 'to': t, 'label': lab, 'side': 't→s',
                        't_successor': v, 's_successors': s_outs,
                        'note': 't 这条动作的后继在 s 侧配不上（关系不是双模拟）'},
                        detail={'checked_pairs': len(pairs)})
    return _reply('relation_holds', **core, detail={'checked_pairs': len(pairs)})


# ============================================================
# 自测（直接运行本文件）
# ============================================================

if __name__ == "__main__":
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass

    print("=" * 60)
    print("双模拟检查 · 自测")
    print("=" * 60)

    # 1) 两个同构的两态循环：跨系统双模拟
    u1 = {"p1": [["a", "p2"]], "p2": [["a", "p1"]],
          "q1": [["a", "q2"]], "q2": [["a", "q1"]]}
    r1 = run({'lts': u1, 'mode': 'pair', 's1': 'p1', 's2': 'q1'})
    assert r1['verdict'] == 'equivalent' and r1['equivalent'] is True, r1
    assert r1['n_blocks'] == 1, r1
    print(f"✅ 同构两态循环跨系统：等价（{r1['n_blocks']} 块，{r1['n_states']} 态）")

    # 2) 一侧多一条 b 边：可区分，且见证给到标号
    u2 = {"p1": [["a", "p2"]], "p2": [["a", "p1"]],
          "q1": [["a", "q2"], ["b", "q1"]], "q2": [["a", "q1"]]}
    r2 = run({'lts': u2, 'mode': 'pair', 's1': 'p1', 's2': 'q1'})
    assert r2['verdict'] == 'not_equivalent', r2
    assert r2['witness'] and r2['witness']['label'] == 'b', r2.get('witness')
    print(f"✅ 单侧多 b 边：不等价，见证给到标号 {r2['witness']['label']}"
          f"（第 {r2['witness']['round']} 轮）")

    # 3) 非确定性：多出来的分支指向等价态 → 仍等价（集合语义）
    u3 = {"s1": [["a", "t1"], ["a", "t2"]], "s2": [["a", "t1"]],
          "t1": [["c", "t3"]], "t2": [["c", "t3"]], "t3": []}
    r3 = run({'lts': u3, 'mode': 'pair', 's1': 's1', 's2': 's2'})
    assert r3['verdict'] == 'equivalent', r3
    print(f"✅ 非确定性（多余分支指向等价态）：等价（{r3['n_blocks']} 块）")

    # 4) 后继块不同 → 可区分
    u4 = {"m1": [["a", "e1"]], "m2": [["a", "e2"]], "e1": [], "e2": [["c", "e3"]], "e3": []}
    r4 = run({'lts': u4, 'mode': 'pair', 's1': 'm1', 's2': 'm2'})
    assert r4['verdict'] == 'not_equivalent', r4
    print(f"✅ 后继块不同：不等价（{r4['n_blocks']} 块）")

    # 5) 反直觉但正确的已知答案：二态环 vs 三态环 —— **等价**！
    #    单动作标号下两者的展开都是同一条无穷 a 链 ⇒ 双模拟；"周期"要靠原子命题/时间语义才分得出来。
    #    （我先按"周期不同就不等价"写断言，被自测当场打回——这正是"先验尺子"该干的活。）
    u5 = {"a1": [["a", "a2"]], "a2": [["a", "a1"]],
          "b1": [["a", "b2"]], "b2": [["a", "b3"]], "b3": [["a", "b1"]]}
    r5 = run({'lts': u5, 'mode': 'pair', 's1': 'a1', 's2': 'b1'})
    assert r5['verdict'] == 'equivalent' and r5['n_blocks'] == 1, r5
    print(f"✅ 二环 vs 三环：**等价**（单标号下展开同一条链；周期不在强双模拟里）")

    # 5b) 死锁 vs 能走：不等价，见证停在"对方走不了这条动作"
    u5b = {"d": [], "m": [["a", "m"]]}
    r5b = run({'lts': u5b, 'mode': 'pair', 's1': 'd', 's2': 'm'})
    assert r5b['verdict'] == 'not_equivalent', r5b
    seq5b = r5b['witness']['sequence']
    assert seq5b['sequence'] == ['a'] and '没有该动作的出边' in seq5b['why'], seq5b
    print(f"✅ 死锁 vs 能走：不等价，见证 {seq5b['sequence']}（{seq5b['why']}）")

    # 6) 分划模式 + 商系统
    r6 = run({'lts': u1})
    assert r6['verdict'] == 'partitioned' and r6['n_blocks'] == 1, r6
    assert list(r6['quotient'].values())[0] == [('a', 0)], r6['quotient']
    print(f"✅ 分划模式：{r6['n_blocks']} 块，商系统 {r6['quotient']}")

    # 7) 关系检查：正例（相同状态对）与负例（把不等价的两态配一起）
    r7a = run({'lts': u1, 'mode': 'check_relation', 'relation': [["p1", "q1"], ["p2", "q2"]]})
    assert r7a['verdict'] == 'relation_holds', r7a
    r7b = run({'lts': u2, 'mode': 'check_relation', 'relation': [["p1", "q1"], ["p2", "q2"]]})
    assert r7b['verdict'] == 'relation_fails' and r7b['witness']['label'] == 'b', r7b
    print(f"✅ 关系检查：正例放行；负例报第一处违规（标号 {r7b['witness']['label']}，"
          f"{r7b['witness']['side']}）")

    # 8) 留痕与拒绝路径
    assert r4['rounds'][0] == {'round': 0, 'blocks': 1} and len(r4['rounds']) >= 2, r4['rounds']
    assert r2['witness']['sequence']['sequence'] == ['b'], r2['witness']
    assert run({'lts': u1, 'mode': 'pair'})['verdict'] == 'input_pending'
    assert run({'lts': u1, 'mode': 'pair', 's1': 'p1', 's2': 'zzz'})['verdict'] == 'parse_error'
    assert run({'lts': u1, 'mode': 'nope'})['verdict'] == 'parse_error'
    assert run({'lts': {'x': [["a", "y"], ["a"]]}})['verdict'] == 'parse_error'
    big = {str(i): [[('a' if j % 2 else 'b'), str((i + 1) % (MAX_STATES + 50))]
                    for j in range(1)] for i in range(MAX_STATES + 50)}
    assert run({'lts': big})['verdict'] == 'size_limit', '超上限必须如实拒'
    print("✅ 留痕（每轮块数）+ 拒绝路径：缺参/坏边/mode 不认/超上限 全部如实报")

    print("=" * 60)
    print("双模拟检查自测：全部通过 ✅")
    print("=" * 60)
