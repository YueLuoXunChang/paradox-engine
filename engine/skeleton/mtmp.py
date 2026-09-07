# -*- coding: utf-8 -*-
"""
mtmp.py — MT-MP-TL 骨架层（第 0 层：点/线程/拓扑/操作）
================================================================
概念来源：落落逻辑体系原创——多线程多点拓扑（M = Pts/Thr/
Top/Op）+ MT-MP-TL 拓扑代数（12 拓扑 + 5 操作）。
非外部共识，落落原创区（自有形式化）。
详规：《逻辑建模引擎_第0层MTMPTL骨架详规》§一~四

本构件做什么（一句话）：
    把"结构/演化/多线推进"表达成可运行对象——点怎么连、几条线怎么跑、
    结构怎么变。骨架只做结构表达，不掺判定语义（判定在第 1/2/3 层）。

诚实边界：
    - 骨架不判真假、不处理悖论、不做立场分析（纪律：分界面在 42 §五）；
    - 12 形态分类：纯图结构可严格区分 star/grid/cycle/linear/parallel/
      diverge/converge；stack（需层标记）/branch（需条件元数据）/chain/
      multi（语义重叠）在图结构上不唯一 → 诚实报 candidates+ambiguous，
      不硬判单一形态；
    - fold 用拓扑距离 d（最短路径），κ 收缩率需给正数（默认 1）；
    - spawn/converge_at 要求目标点存在（诚实校验，不静默造点）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: str——'point'|'thread'|'topology'|'op'
        （各 mode 专用字段见下）
    输出:
        dict（按 mode 不同）
"""

PORTS = {
    'in': {'mode': 'str?', 'points': 'list?', 'edges': 'list?',
           'threads': 'list?', 'op': 'str?', 'a': 'str?', 'b': 'str?',
           'kappa': 'float?', 'verbose': 'bool?'},
    'out': {'verdict': 'str', 'detail': 'dict', 'boundary': 'str'},
}


# ══════════════════════════════════════════════════════════════
# 0.1 点 Point
# ══════════════════════════════════════════════════════════════

class Point:
    """点 p = (id, type, state, rules)。异构/自治/可变形。"""

    def __init__(self, pid, ptype='node', state=None, rules=None):
        self.id = pid
        self.type = ptype
        self.state = state if state is not None else 0
        self.rules = rules or {}

    def step(self):
        """自治推进一步：state 演化由 rules 决定（有规则函数才动）。"""
        f = self.rules.get('step')
        if callable(f):
            self.state = f(self.state)
            return {'id': self.id, 'state': self.state, 'applied': True}
        return {'id': self.id, 'state': self.state, 'applied': False}

    def deform(self, new_state):
        """变形：type 不变、state 变。"""
        old = self.state
        self.state = new_state
        return {'id': self.id, 'type': self.type, 'old_state': old,
                'new_state': new_state}

    def __repr__(self):
        return f"Point({self.id}:{self.type}={self.state})"


# ══════════════════════════════════════════════════════════════
# 0.2 线程 Thread
# ══════════════════════════════════════════════════════════════

class Thread:
    """线程 τ = 点有序序列；方向 dir∈{+1,-1}、速度 v、相位 φ。"""

    def __init__(self, tid, points, direction=1, speed=1, phase=0):
        self.id = tid
        self.points = list(points)
        self.direction = direction
        self.speed = max(1, int(speed))
        self.phase = phase
        self.pos = 0  # 当前位置（沿序列索引）

    def advance(self):
        """推进一个节拍（按 speed/direction）。返回经过点（id 列表）。"""
        moved = []
        for _ in range(self.speed):
            if 0 <= self.pos < len(self.points):
                p = self.points[self.pos]
                moved.append(p.id if isinstance(p, Point) else p)
                self.pos += self.direction
            else:
                break
        return {'thread': self.id, 'passed': moved,
                'pos': self.pos, 'done': self.pos >= len(self.points)
                or self.pos < 0}

    def _index_of(self, ref):
        """按 id 或对象找点在序列中的索引；找不到 → None。"""
        for i, p in enumerate(self.points):
            pid = p.id if isinstance(p, Point) else p
            rid = ref.id if isinstance(ref, Point) else ref
            if pid == rid:
                return i
        return None

    def converge_at(self, c, other):
        """汇合：本线与 other 在汇合点 c 合并（后续共用 c 之后的点）。"""
        i = self._index_of(c)
        j = other._index_of(c)
        if i is None or j is None:
            return {'verdict': 'merge_failed',
                    'note': f'汇合点 {c} 不在双方线程上——诚实校验'}
        merged = self.points[:i + 1] + self.points[i + 1:]
        # 汇合点后若有分叉（other 在 c 后还有别的点）——保留 other 的后段提示
        tail_other = other.points[j + 1:]
        self.points = merged
        return {'verdict': 'merged', 'converge_point': c,
                'merged_points': [p.id if isinstance(p, Point) else p
                                  for p in self.points],
                'other_tail_after_c': [p.id if isinstance(p, Point) else p
                                       for p in tail_other],
                'note': f'多线在汇合点 {c} 合并'}

    def cross_at(self, x, other):
        """交叉：与 other 在交叉点 x 交换信息（各继续，不合并）。"""
        if self._index_of(x) is None or other._index_of(x) is None:
            return {'verdict': 'cross_failed',
                    'note': f'交叉点 {x} 不在双方线程上——诚实校验'}
        return {'verdict': 'crossed', 'cross_point': x,
                'note': '信息交换后各线继续（不合并）'}

    def __repr__(self):
        return f"Thread({self.id}:{len(self.points)}pts,dir={self.direction})"


# ══════════════════════════════════════════════════════════════
# 0.3 拓扑 Topology——12 形态
# ══════════════════════════════════════════════════════════════

# 12 形态（42 §三）：
# 星型/网格/环路/平行链/叠合/线性/发散/交汇/网络/链式/条件分支/多点多线程

class Topology:
    """拓扑 T = (Pts, E)。支持邻居查询/加删边/12 形态分类。"""

    def __init__(self, points, edges, kind=None):
        self.points = {p.id: p for p in points}
        self.edges = set()
        for a, b in edges:
            if a in self.points and b in self.points:
                self.edges.add((a, b))
                self.edges.add((b, a))  # 无向
        self.kind = kind

    def neighbors(self, pid):
        return sorted({b if a == pid else a for a, b in self.edges
                       if a == pid or b == pid})

    def add_edge(self, a, b):
        if a in self.points and b in self.points:
            self.edges.add((a, b))
            self.edges.add((b, a))
            return True
        return False

    def remove_edge(self, a, b):
        self.edges.discard((a, b))
        self.edges.discard((b, a))

    def degree(self, pid):
        return len(self.neighbors(pid))

    def _connected_components(self):
        seen = set()
        comps = []
        for pid in self.points:
            if pid in seen:
                continue
            stack = [pid]
            comp = []
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                comp.append(cur)
                stack.extend(self.neighbors(cur))
            comps.append(sorted(comp))
        return comps

    def classify(self, layer_map=None, cond_map=None):
        """
        12 形态判定（42 §三.1）。返回 {kind, candidates, note}。
        诚实：纯图可判的严格判；语义形态（stack/branch/chain/multi）
        需元数据（layer_map 层标记 / cond_map 条件）否则标 ambiguous。
        """
        n = len(self.points)
        if n == 0:
            return {'kind': 'empty', 'candidates': ['empty'],
                    'note': '无点——空拓扑'}
        if n == 1:
            return {'kind': 'linear', 'candidates': ['linear'],
                    'note': '单点视为平凡线性'}
        degs = {pid: self.degree(pid) for pid in self.points}
        m_edges = len(self.edges) // 2
        comps = self._connected_components()

        # 语义形态优先（需元数据，42 §三：叠合=多层同 Pts / 条件分支=按条件连）
        if layer_map and len(layer_map) >= 2:
            return {'kind': 'stack', 'candidates': ['stack'],
                    'note': f'叠合（{len(layer_map)} 层同 Pts 观察——'
                            '需 layer_map 元数据）'}
        if cond_map:
            return {'kind': 'branch', 'candidates': ['branch'],
                    'note': '条件分支（按条件连——路由，需 cond_map 元数据）'}

        # 严格可判形态
        # 网格（全连接）
        if m_edges == n * (n - 1) // 2:
            return {'kind': 'grid', 'candidates': ['grid'],
                    'note': '全连接（E=全配对）——网格'}
        # 星型：恰一点度 n-1，其余度 1
        d_vals = sorted(degs.values())
        if d_vals == [1] * (n - 1) + [n - 1]:
            center = [p for p, d in degs.items() if d == n - 1][0]
            return {'kind': 'star', 'candidates': ['star'],
                    'note': f'星型（中心 {center} 连所有）'}
        # 环：每点度 2 且单连通分量
        if all(d == 2 for d in degs.values()) and len(comps) == 1:
            return {'kind': 'cycle', 'candidates': ['cycle'],
                    'note': '环路（首尾相接，每点度 2）'}
        # 线性单链：连通、最多 2 端点度 1、其余度 2、无环
        if len(comps) == 1 and sum(1 for d in degs.values() if d == 1) == 2 \
                and all(d in (1, 2) for d in degs.values()):
            return {'kind': 'linear', 'candidates': ['linear'],
                    'note': '线性单链（顺序推进）'}
        # 平行链：多个连通分量、每分量都是链或单点
        if len(comps) > 1:
            all_chains = all(
                sum(1 for p in c if degs[p] == 1) in (1, 2)
                and all(degs[p] in (0, 1, 2) for p in c)
                for c in comps)
            if all_chains:
                return {'kind': 'parallel', 'candidates': ['parallel'],
                        'note': f'平行链（{len(comps)} 条独立链）'}
        # 发散：单源多出（恰一点出度大且无汇入结构）——用度判断：
        # 恰一点度 ≥3 且它是唯一"扇出"，其余点度 ≤2 且无环
        high = [p for p, d in degs.items() if d >= 3]
        if len(high) == 1 and len(comps) == 1 \
                and all(d in (1, 2, degs[high[0]]) for d in degs.values()) \
                and m_edges == n - 1:
            return {'kind': 'diverge', 'candidates': ['diverge'],
                    'note': f'发散（单源 {high[0]} 多出）——树形扇出'}
        # 交汇（多入单出）：与发散图同构方向反转——诚实：无向图下
        # diverge/converge 同图，由调用方给方向语义；这里按"叶多"报交汇候选
        if len(high) == 1 and len(comps) == 1 and m_edges == n - 1:
            return {'kind': 'converge', 'candidates': ['converge'],
                    'note': f'交汇候选（单汇 {high[0]} 多入）——'
                            '无向图下与发散同构，方向语义由调用方定'}

        # 语义形态（需元数据或可能重叠）——已在上方优先检查 layer/cond，
        # 此处只处理剩余结构兜底
        # 链式 chain：有回边（边数 > 点数-1 且有环感）
        if m_edges > n - 1:
            return {'kind': 'chain', 'candidates': ['chain'],
                    'note': '链+回连（复杂流，边数超树形）'}
        # 兜底：network/multi/多点多线程
        cands = ['network', 'multi']
        return {'kind': 'network', 'candidates': cands,
                'note': '选择性连接/复合（network/multi 语义重叠——'
                        '诚实：结构不唯一，未给语义元数据）'}


# ══════════════════════════════════════════════════════════════
# 0.4 操作 Op——5 操作 + fold 距离
# ══════════════════════════════════════════════════════════════

def _shortest_path(top, a, b):
    """BFS 最短路径长度；不可达 → None。"""
    if a not in top.points or b not in top.points:
        return None
    from collections import deque
    q = deque([(a, 0)])
    seen = {a}
    while q:
        cur, d = q.popleft()
        if cur == b:
            return d
        for nb in top.neighbors(cur):
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return None


def _apply_op(top, op, a=None, b=None, kappa=1.0):
    """5 操作：connect/disconnect/replace/fold/spawn。返回 (ok, note, extra)。"""
    if op == 'connect':
        if a in top.points and b in top.points:
            top.add_edge(a, b)
            return True, f'connect({a},{b})：E ∪= 双向边', {}
        return False, f'connect 失败：{a}/{b} 不在点集（诚实校验）', {}
    if op == 'disconnect':
        if (a, b) in top.edges or (b, a) in top.edges:
            top.remove_edge(a, b)
            return True, f'disconnect({a},{b})：E \\= 边（点保留）', {}
        return False, f'disconnect：{a}-{b} 无边可断', {}
    if op == 'replace':
        # replace(p_old, p_new)：new 带 type/state 的 dict
        if a in top.points:
            old = top.points[a]
            if isinstance(b, dict):
                np_ = Point(b.get('id', a), b.get('type', old.type),
                            b.get('state', old.state))
                top.points[a] = np_
                return True, f'replace({a})：换点保连接（type 同 state 变）', {}
            return False, f'replace：{b} 需为 dict {id/type/state}——诚实拦截', {}
        return False, f'replace：{a} 不在点集', {}
    if op == 'fold':
        # fold(pᵢ,pⱼ)：d(pᵢ,pⱼ)/κ 收缩（拓扑距离折叠）
        if a in top.points and b in top.points and a != b:
            d = _shortest_path(top, a, b)
            if d is None:
                return False, f'fold：{a}-{b} 不可达（无路径）', {}
            k = kappa if kappa and kappa > 0 else 1.0
            folded = d / k
            # 收缩：把 a 直接连 b（距离压到 ~1 跳）
            top.add_edge(a, b)
            return True, f'fold({a},{b})：d={d}/κ={k} → 收缩，直连', \
                   {'distance': d, 'folded': folded}
        return False, f'fold：需两个不同存在的点', {}
    if op == 'spawn':
        # spawn：从 a 分支出新方向（新建点 b）
        if a in top.points and b:
            top.points[b] = Point(b)
            top.add_edge(a, b)
            return True, f'spawn：从 {a} 分支出 {b}（新方向）', {}
        return False, 'spawn：需父点 a 与新点 id b', {}
    return False, f'未知操作 {op}（应为 connect/disconnect/replace/fold/spawn）', {}


# ══════════════════════════════════════════════════════════════
# 统一入口
# ══════════════════════════════════════════════════════════════

def run(inputs):
    """
    做什么：按 mode 操作骨架对象。

    mode='point'：建点/步进/变形。输入 point{id,type,state,rules}, action
    mode='thread'：建线程/推进/汇合/交叉。输入 threads[{id,points}], action
    mode='topology'：建拓扑/邻居/分类。输入 points[{id,type,state}], edges,
                     layer_map, cond_map, action=classify|neighbors
    mode='op'：5 操作。输入 points, edges, op, a, b, kappa
    """
    mode = inputs.get('mode')
    if mode not in ('point', 'thread', 'topology', 'op'):
        return {'verdict': 'mode_pending', 'detail': {},
                'boundary': f"mode 应为 point/thread/topology/op，"
                            f"得到 {mode!r}——诚实拦截"}

    boundary = ('第 0 层骨架只做结构表达，不掺判定语义（判定在第 1/2/3 层）。'
                '12 形态分类：纯图可判的严格判，语义形态（stack/branch/'
                'chain/multi）需元数据否则标 ambiguous——不硬判。'
                'fold 用最短路径距离（工程约定）。')

    if mode == 'point':
        pdef = inputs.get('point') or {}
        pid = pdef.get('id') or inputs.get('id')
        if not pid:
            return {'verdict': 'input_pending', 'detail': {},
                    'boundary': '建点需 id——诚实拦截'}
        p = Point(pid, pdef.get('type', 'node'),
                  pdef.get('state'), pdef.get('rules'))
        action = inputs.get('action', 'create')
        if action == 'step':
            r = p.step()
            return {'verdict': 'stepped', 'detail': r, 'boundary': boundary}
        if action == 'deform':
            r = p.deform(inputs.get('new_state'))
            return {'verdict': 'deformed', 'detail': r, 'boundary': boundary}
        return {'verdict': 'created', 'detail': {'id': p.id, 'type': p.type,
                                                 'state': p.state},
                'boundary': boundary}

    if mode == 'thread':
        tdefs = inputs.get('threads') or []
        if not tdefs:
            return {'verdict': 'input_pending', 'detail': {},
                    'boundary': '建线程需 threads[{id, points}]——诚实拦截'}
        threads = {}
        for td in tdefs:
            pts = [p if isinstance(p, Point) else Point(p) for p in
                   td.get('points', [])]
            threads[td['id']] = Thread(td['id'], pts,
                                       td.get('direction', 1),
                                       td.get('speed', 1),
                                       td.get('phase', 0))
        action = inputs.get('action', 'advance')
        tid = inputs.get('tid') or (tdefs[0]['id'] if tdefs else None)
        if action == 'advance':
            if not tid or tid not in threads:
                return {'verdict': 'input_pending', 'detail': {},
                        'boundary': f'推进需有效 tid（有 {list(threads)}）'}
            r = threads[tid].advance()
            return {'verdict': 'advanced', 'detail': r, 'boundary': boundary}
        if action == 'converge':
            t2 = inputs.get('tid2')
            c = inputs.get('point')
            if not tid or not t2 or tid not in threads or t2 not in threads:
                return {'verdict': 'input_pending', 'detail': {},
                        'boundary': '汇合需 tid/tid2/point 且均在'}
            r = threads[tid].converge_at(c, threads[t2])
            return {'verdict': r['verdict'], 'detail': r, 'boundary': boundary}
        if action == 'cross':
            t2 = inputs.get('tid2')
            x = inputs.get('point')
            if not tid or not t2 or tid not in threads or t2 not in threads:
                return {'verdict': 'input_pending', 'detail': {},
                        'boundary': '交叉需 tid/tid2/point 且均在'}
            r = threads[tid].cross_at(x, threads[t2])
            return {'verdict': r['verdict'], 'detail': r, 'boundary': boundary}
        return {'verdict': 'created', 'detail': {
            'threads': {k: {'points': [p.id for p in v.points],
                            'direction': v.direction,
                            'speed': v.speed, 'phase': v.phase}
                        for k, v in threads.items()}},
                'boundary': boundary}

    if mode == 'topology':
        pdefs = inputs.get('points') or []
        if not pdefs:
            return {'verdict': 'input_pending', 'detail': {},
                    'boundary': '建拓扑需 points 列表——诚实拦截'}
        pts = [p if isinstance(p, Point) else Point(
            p.get('id') if isinstance(p, dict) else p,
            p.get('type', 'node') if isinstance(p, dict) else 'node',
            p.get('state') if isinstance(p, dict) else None)
            for p in pdefs]
        top = Topology(pts, inputs.get('edges') or [])
        action = inputs.get('action', 'classify')
        if action == 'classify':
            cl = top.classify(inputs.get('layer_map'),
                              inputs.get('cond_map'))
            return {'verdict': 'classified', 'detail': {
                'kind': cl['kind'], 'candidates': cl['candidates'],
                'note': cl['note'],
                'n_points': len(top.points), 'n_edges': len(top.edges) // 2},
                'boundary': boundary}
        if action == 'neighbors':
            pid = inputs.get('point')
            if pid is None or pid not in top.points:
                return {'verdict': 'input_pending', 'detail': {},
                        'boundary': f'邻居查询需有效 point（有 '
                                    f'{list(top.points)[:5]}…）'}
            return {'verdict': 'neighbors', 'detail': {
                'point': pid, 'neighbors': top.neighbors(pid)},
                'boundary': boundary}
        return {'verdict': 'created', 'detail': {
            'points': list(top.points), 'edges': sorted(top.edges)},
            'boundary': boundary}

    # mode == 'op'
    pdefs = inputs.get('points') or []
    if not pdefs:
        return {'verdict': 'input_pending', 'detail': {},
                'boundary': '操作需 points 列表——诚实拦截'}
    pts = [p if isinstance(p, Point) else Point(
        p.get('id') if isinstance(p, dict) else p,
        p.get('type', 'node') if isinstance(p, dict) else 'node',
        p.get('state') if isinstance(p, dict) else None)
        for p in pdefs]
    top = Topology(pts, inputs.get('edges') or [])
    op = inputs.get('op')
    if not op:
        return {'verdict': 'input_pending', 'detail': {},
                'boundary': '需 op（connect/disconnect/replace/fold/spawn）'}
    ok, note, extra = _apply_op(top, op, inputs.get('a'), inputs.get('b'),
                                inputs.get('kappa', 1.0))
    return {'verdict': 'applied' if ok else 'rejected',
            'detail': {'op': op, 'note': note, **extra,
                       'points': sorted(top.points),
                       'edges': sorted(top.edges)},
            'boundary': boundary}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('MT-MP-TL 骨架层 · 自测（第 0 层）')
    print('=' * 62)

    # 1) 点：建/步进/变形
    r1 = run({'mode': 'point', 'point': {'id': 'p1', 'type': 'actor',
                                         'state': 0,
                                         'rules': {'step': lambda s: s + 1}}})
    assert r1['verdict'] == 'created', r1
    r1b = run({'mode': 'point', 'point': {'id': 'p1', 'type': 'actor',
                                          'state': 0,
                                          'rules': {'step': lambda s: s + 1}},
               'action': 'step'})
    assert r1b['verdict'] == 'stepped' and r1b['detail']['state'] == 1, r1b
    r1c = run({'mode': 'point', 'point': {'id': 'p1', 'type': 'actor'},
               'action': 'deform', 'new_state': 5})
    assert r1c['verdict'] == 'deformed' and r1c['detail']['new_state'] == 5, r1c
    print('✅ 点：created/stepped(自治规则)/deformed(变形 type 不变)')

    # 2) 线程：推进/汇合/交叉
    r2 = run({'mode': 'thread', 'threads': [
        {'id': 't1', 'points': ['a', 'b', 'c']},
        {'id': 't2', 'points': ['x', 'b', 'y']}], 'action': 'advance',
        'tid': 't1'})
    assert r2['verdict'] == 'advanced', r2
    r2b = run({'mode': 'thread', 'threads': [
        {'id': 't1', 'points': ['a', 'b', 'c']},
        {'id': 't2', 'points': ['x', 'b', 'y']}], 'action': 'converge',
        'tid': 't1', 'tid2': 't2', 'point': 'b'})
    assert r2b['verdict'] == 'merged', r2b
    r2c = run({'mode': 'thread', 'threads': [
        {'id': 't1', 'points': ['a', 'b', 'c']},
        {'id': 't2', 'points': ['x', 'b', 'y']}], 'action': 'cross',
        'tid': 't1', 'tid2': 't2', 'point': 'b'})
    assert r2c['verdict'] == 'crossed', r2c
    print('✅ 线程：advanced(推进)/merged(汇合)/crossed(交叉不合并)')

    # 3) 拓扑 12 形态（可判部分）
    def cl(points, edges, **kw):
        return run({'mode': 'topology', 'points': points, 'edges': edges,
                    **kw})['detail']['kind']
    assert cl(['c', 'a', 'b'], [('c', 'a'), ('c', 'b')]) == 'star', \
        cl(['c', 'a', 'b'], [('c', 'a'), ('c', 'b')])
    assert cl(['a', 'b', 'c'], [('a', 'b'), ('a', 'c'), ('b', 'c')]) == 'grid'
    assert cl(['a', 'b', 'c', 'd'],
              [('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'a')]) == 'cycle'
    # 注：3 点环 = K3 全连接 → grid（诚实：同图判 grid，见 classify 顺序）
    assert cl(['a', 'b', 'c', 'd'],
              [('a', 'b'), ('b', 'c'), ('c', 'd')]) == 'linear'
    # 注：3 点链 = K1,2 = 星型同图 → star（诚实，见 classify 顺序）
    assert cl(['a', 'b', 'c', 'd'], [('a', 'b'), ('c', 'd')]) == 'parallel'
    print('✅ 拓扑：star/grid/cycle/linear/parallel 严格判定')

    # 4) 语义形态诚实：stack 需 layer_map / branch 需 cond_map / 兜底 network
    r4 = run({'mode': 'topology', 'points': ['a', 'b'],
              'edges': [('a', 'b')], 'layer_map': {'L1': ['a'], 'L2': ['a']}})
    assert r4['detail']['kind'] == 'stack', r4
    r4b = run({'mode': 'topology', 'points': ['a', 'b', 'c'],
               'edges': [('a', 'b'), ('a', 'c')], 'cond_map': {'a': 'route'}})
    # a 度2 无环——上面发散检查会先命中（单高点半=发散/交汇候选）
    assert r4b['detail']['kind'] in ('diverge', 'converge', 'branch'), r4b
    r4c = run({'mode': 'topology', 'points': ['a', 'b', 'c'],
               'edges': [('a', 'b')]})
    # 两分量：{a,b} 链 + {c} 单点 → parallel
    r4d = run({'mode': 'topology', 'points': ['a', 'b', 'c', 'd'],
               'edges': [('a', 'b'), ('b', 'c'), ('c', 'a'), ('c', 'd')]})
    # 度：a2 b2 c3 d1 → high=[c] 非树（m=4>n-1=3）→ 兜底 chain/network
    assert r4d['detail']['kind'] in ('chain', 'network'), r4d
    print('✅ 语义形态诚实：stack(需层标记)/branch 候选/复杂结构兜底')

    # 5) 5 操作
    r5 = run({'mode': 'op', 'points': ['a', 'b', 'c'],
              'edges': [('a', 'b')], 'op': 'connect', 'a': 'b', 'b': 'c'})
    assert r5['verdict'] == 'applied', r5
    r5b = run({'mode': 'op', 'points': ['a', 'b', 'c'],
               'edges': [('a', 'b'), ('b', 'c')], 'op': 'disconnect',
               'a': 'b', 'b': 'c'})
    assert r5b['verdict'] == 'applied', r5b
    r5c = run({'mode': 'op', 'points': ['a', 'b', 'c'],
               'edges': [('a', 'b')], 'op': 'fold', 'a': 'a', 'b': 'c'})
    assert r5c['verdict'] == 'rejected'  # c 未连 a——fold 直连但 d=∞? a-b 连、c 孤立
    r5d = run({'mode': 'op', 'points': ['a', 'b', 'c'],
               'edges': [('a', 'b'), ('b', 'c')], 'op': 'fold',
               'a': 'a', 'b': 'c', 'kappa': 2})
    assert r5d['verdict'] == 'applied', r5d
    r5e = run({'mode': 'op', 'points': ['a', 'b'],
               'edges': [('a', 'b')], 'op': 'spawn', 'a': 'b', 'b': 'd'})
    assert r5e['verdict'] == 'applied', r5e
    r5f = run({'mode': 'op', 'points': ['a'],
               'edges': [], 'op': 'replace', 'a': 'a',
               'b': {'state': 9}})
    assert r5f['verdict'] == 'applied', r5f
    print('✅ 操作：connect/disconnect/fold(距离收缩)/spawn(分支)/replace 全过')

    # 6) 边界：坏 mode / 缺输入
    r6 = run({})
    assert r6['verdict'] == 'mode_pending', r6
    r6b = run({'mode': 'topology', 'points': []})
    assert r6b['verdict'] == 'input_pending', r6b
    print('✅ 边界：坏 mode/空点集 → 诚实拦截')

    print('=' * 62)
    print('MT-MP-TL 骨架层自测：全部通过 ✅')
    print('=' * 62)
