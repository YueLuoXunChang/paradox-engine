# -*- coding: utf-8 -*-
"""
interval_algebra.py — 区间代数（Allen 定性时序推理）· 第 3 层按痛点接入
================================================================================
概念来源：**外部经典共识**——Allen, J.F. (1983) "Maintaining Knowledge about
Temporal Intervals"（13 个基本区间关系 + 复合表 + 路径一致性算法）；
点代数一侧见 Vilain & Kautz (1986)。归借鉴区（落落三问：借什么=定性时序关系
这套代数与路径一致性；为什么=第 4 类"演化过程"现在只有 LTL 与收敛判定——
LTL 问的是"性质沿路径成不成立"，**答不了"这两件事谁先谁后、谁包含谁"**这类
事件之间的定性关系；怎么记账=标注来源归借鉴区，不混原创区）。

本构件做什么（一句话）：
    拿一组事件与它们两两之间的**定性关系**（先于／相接／重叠／开始于／包含／
    结束于／同时 + 各自反向），判这组说法**自相矛盾吗**；矛盾就指出被挤空的那一对
    （以及是哪三对把它挤空的），没矛盾就找一组**具体的整数区间**当见证（可复核）。

13 个基本关系（`b m o s d f e` 与各自的逆）：
    b  先于（before）      X 结束 < Y 开始
    m  相接（meets）       X 结束 = Y 开始
    o  重叠（overlaps）    X 开始 < Y 开始 < X 结束 < Y 结束
    s  开始于（starts）    X 开始 = Y 开始，X 结束 < Y 结束
    d  包含于（during）    Y 开始 < X 开始，X 结束 < Y 结束
    f  结束于（finishes）  Y 开始 < X 开始，X 结束 = Y 结束
    e  同时（equals）      两端点都相等
    bi/mi/oi/si/di/fi 是上面 6 个的**反向**（b/m/o/s/d/f 的反向）

**表是推出来的，不是抄的**（这点很要紧）：13×13 的复合表不写在文件里，而是由
"每个关系=四个端点之间的一组序约束"**现场推导**（见 `tables()`，首次用到时算一次
并缓存）。推导里有个坑：Allen 的关系**允许端点重合**（m/s/f/e 都靠端点相等），
所以枚举的必须是"带并列的弱序"，只枚举严格全序会把带等号的关系全推没（踩过）。

两套语义、同一条算法（本构件把差别说清，别当成"同一件事的粗细版本"）：
    - **区间代数 IA**：路径一致性只给**必要条件**——挤出空集就能断定不一致，
      但"没挤空"只说明**没发现冲突**，不等于一定有解；所以默认报
      'path_consistent' 而不是"有解"，另有 `mode='solve'` 在有界预算里找见证模型
      （找到就是真有解，可复核）。
    - **点代数 PA**（`mode='point'`）：只有 <、=、> 三个关系，路径一致性对它是
      **完备**的——报 consistent 就是真有解、报 inconsistent 就是真无解。

诚实边界：
    - 只做**定性**关系：不给时长、不给时刻数值（要数值请用算术类构件，如 Presburger）；
    - 关系用并集表达（如 `['b','m']`＝"先于或相接"）✓；空集＝不一致；
    - 事件数上限 8；见证搜索**有界**：预算内没找到就报 not_found_in_budget
      （**不等于无解**）；
    - 只诊断不决策：给的是"这套时序说法自不自治"，不替人定事实。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'consistent'（默认）| 'solve' | 'point' | 'compose' | 'converse'
        events: list[str]——事件名（consistent/solve/point 用）
        relations: list——[[A, 关系, B], …]；关系可写 'b'/'before'/['b','m']
        relation / relations（converse、compose 用）
    输出:
        verdict: str——'path_consistent'|'inconsistent'|'model_found'
                        |'not_found_in_budget'|'composed'|'conversed'
                        |'input_pending'|'parse_error'|'size_limit'
        matrix: dict——收窄后的两两关系（'A|B' → 关系串）
        conflict: dict?——不一致时：哪一对被挤空、被哪三对挤的
        model: dict?——见证：事件 → [起, 止]（整数）
        composed / conversed: str?——复合 / 逆的结果
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'events': 'list?', 'relations': 'list?',
           'relation': 'str?'},
    'out': {'verdict': 'str', 'matrix': 'dict', 'conflict': 'dict?',
            'model': 'dict?', 'composed': 'str?', 'conversed': 'str?',
            'boundary': 'str'},
}

import itertools
import sys

BOUNDARY = ('区间代数（外部共识：Allen 1983 的关系代数与路径一致性；点代数见 '
            'Vilain & Kautz 1986。借鉴区）：**区间代数上路径一致性只给必要条件**——'
            '报 inconsistent 就是真不一致（找到了挤空的那一对）；报 '
            'path_consistent 只说明没发现冲突，不等于有解；要确定结论用 '
            'mode=solve 找见证（有界预算内找到的模型可复核）。点代数（mode=point）'
            '上路径一致性完备。只做定性关系、不给数值；见证搜索有界：'
            '没找到 ≠ 无解。只诊断不决策。')

BASE = ('b', 'm', 'o', 's', 'd', 'f', 'e',
        'bi', 'mi', 'oi', 'si', 'di', 'fi')
_ALL = frozenset(BASE)
REL_CN = {
    'b': '先于', 'm': '相接', 'o': '重叠', 's': '开始于', 'd': '包含于',
    'f': '结束于', 'e': '同时',
    'bi': '晚于', 'mi': '被相接', 'oi': '被重叠', 'si': '被开始',
    'di': '包含', 'fi': '被结束',
}
ALIASES = {
    'before': 'b', 'meets': 'm', 'overlaps': 'o', 'starts': 's',
    'during': 'd', 'finishes': 'f', 'equals': 'e',
    'after': 'bi', 'met_by': 'mi', 'overlapped_by': 'oi',
    'started_by': 'si', 'contains': 'di', 'finished_by': 'fi',
    '先于': 'b', '相接': 'm', '重叠': 'o', '开始于': 's', '包含于': 'd',
    '结束于': 'f', '同时': 'e', '晚于': 'bi', '后于': 'bi', '包含': 'di',
    '被包含': 'd', '等于': 'e',
}

# 每个基本关系 = 四个端点之间的一组序约束（端点名：区间字母 + -/+）
_ENDPOINT_SPEC = {
    'b':  (('X+', '<', 'Y-'),),
    'm':  (('X+', '=', 'Y-'),),
    'o':  (('X-', '<', 'Y-'), ('Y-', '<', 'X+'), ('X+', '<', 'Y+')),
    's':  (('X-', '=', 'Y-'), ('X+', '<', 'Y+')),
    'd':  (('Y-', '<', 'X-'), ('X+', '<', 'Y+')),
    'f':  (('Y-', '<', 'X-'), ('X+', '=', 'Y+')),
    'e':  (('X-', '=', 'Y-'), ('X+', '=', 'Y+')),
    'bi': (('Y+', '<', 'X-'),),
    'mi': (('Y+', '=', 'X-'),),
    'oi': (('Y-', '<', 'X-'), ('X-', '<', 'Y+'), ('Y+', '<', 'X+')),
    'si': (('Y-', '=', 'X-'), ('Y+', '<', 'X+')),
    'di': (('X-', '<', 'Y-'), ('Y+', '<', 'X+')),
    'fi': (('X-', '<', 'Y-'), ('X+', '=', 'Y+')),
}

# 点代数：三个关系，复合表就三行（完备片段）
_P_ORDER = ('<', '=', '>')
_P_REL_OF = {'before': '<', 'after': '>', 'equals': '=',
             '先于': '<', '晚于': '>', '同时': '=',
             '<': '<', '>': '>', '=': '='}
_P_COMPOSE = {('<', '<'): '<', ('<', '='): '<', ('<', '>'): '<=>',
              ('=', '<'): '<', ('=', '='): '=', ('=', '>'): '>',
              ('>', '<'): '<=>', ('>', '='): '>', ('>', '>'): '>'}
_P_CONVERSE = {'<': '>', '=': '=', '>': '<'}

MAX_EVENTS = 8
MAX_SOLVE_NODES = 200000   # 护栏：求一个模型的搜索节点兜底（内部工作量，不作判据阈值）
_TABLES = None          # 懒算的表缓存：(逆表, 复合表)


# ══════════════════════════════════════════════════════════════
# 一、从端点语义推导逆关系与复合表（首次用到时算一次）
# ══════════════════════════════════════════════════════════════

def _sub(cons, mp):
    """模板端点名（X-/X+…）→ 域端点名；mp 的键是模板**区间字母** X/Y/Z。"""
    return [(mp.get(a[0], a[0]) + a[1:], op, mp.get(b[0], b[0]) + b[1:])
            for a, op, b in cons]


def _weak_orders(prefixes):
    """端点名的所有弱序（可并列；每个区间内 起点 < 终点）。

    必须是弱序：m/s/f/e 这些关系要求端点**重合**，严格全序会让它们无处安放。
    """
    names = [p + s for p in prefixes for s in ('-', '+')]
    n = len(names)
    out = []
    for assign in itertools.product(range(n), repeat=n):
        used = sorted(set(assign))
        if used != list(range(len(used))):        # 只用初始段，避免重复
            continue
        pos = dict(zip(names, assign))
        for p in prefixes:
            if pos[p + '-'] >= pos[p + '+']:
                break
        else:
            out.append(pos)
    return out


def _holds(cons, pos):
    for a, op, b in cons:
        if op == '<' and not pos[a] < pos[b]:
            return False
        if op == '=' and pos[a] != pos[b]:
            return False
    return True


def _rel_between(pos, i, j):
    """在该弱序下，区间 i 与 j 是哪个基本关系（唯一）。"""
    mp = {'X': i, 'Y': j}
    for t in BASE:
        if _holds(_sub(_ENDPOINT_SPEC[t], mp), pos):
            return t
    return None


def tables():
    """返回 (逆表, 复合表)；首次调用时推导并缓存。

    推导方式：两区间枚举四个端点的弱序 → 逆；三区间枚举六个端点的弱序 → 复合。
    这样文件里不必手抄 169 格表（手抄正是最容易出错的一步）。
    """
    global _TABLES
    if _TABLES is not None:
        return _TABLES
    o2 = _weak_orders(['X', 'Y'])
    o3 = _weak_orders(['X', 'Y', 'Z'])
    inv = {}
    for r in BASE:
        for q in BASE:
            if all(_holds(_ENDPOINT_SPEC[r], p)
                   == _holds(_sub(_ENDPOINT_SPEC[q], {'X': 'Y', 'Y': 'X'}), p)
                   for p in o2):
                inv[r] = q
                break
    comp = {}
    for p in o3:
        rx = _rel_between(p, 'X', 'Y')
        if rx is None:
            continue
        sy = _rel_between(p, 'Y', 'Z')
        tz = _rel_between(p, 'X', 'Z')
        if sy is None or tz is None:
            continue
        comp.setdefault((rx, sy), set()).add(tz)
    comp = {k: ''.join(v for v in BASE if v in vs)
            for k, vs in comp.items()}
    _TABLES = (inv, comp)
    return _TABLES


# ══════════════════════════════════════════════════════════════
# 二、关系集运算（并集用按 BASE 序的字符串表示）
# ══════════════════════════════════════════════════════════════

def _parse_rel(text, point=False):
    """关系写法 → 关系串（并集）。认符号、英文名、中文名、以及列表。"""
    items = text if isinstance(text, (list, tuple)) else [text]
    out = []
    for it in items:
        if not isinstance(it, str):
            raise ValueError('关系要是字符串或字符串列表，得到 %r' % (it,))
        key = it.strip()
        if point:
            if key not in _P_REL_OF:
                raise ValueError('点代数只认 <、=、>（或 before/after/equals），'
                                 '得到 %r' % (it,))
            v = _P_REL_OF[key]
            for ch in v:                    # 点代数的关系就是单字符
                if ch not in out:
                    out.append(ch)
        else:
            v = key if key in _ALL else ALIASES.get(key.lower())
            if v is None:
                raise ValueError('不认识的关系 %r（可用：%s；也认 before/meets/… '
                                 '与中文名）' % (it, ' '.join(BASE)))
            for nm in _names(v):            # 按**关系名**拆（别按字符，踩过）
                if nm not in out:
                    out.append(nm)
    order = _P_ORDER if point else BASE
    return ''.join(x for x in order if x in out)


def _names(rel):
    """关系串（名拼接，如 'bdmos' 或 'mi'）→ 关系名列表。

    注意：单字名与双字名混在一起（'b' 与 'bi'），所以按 BASE 顺序**贪心**匹配；
    直接按字符遍历会得到 'i' 这种不存在的名字（踩过）。
    """
    out = []
    i = 0
    while i < len(rel):
        two = rel[i:i + 2]
        if len(two) == 2 and two in _ALL:
            out.append(two)
            i += 2
        elif rel[i] in _ALL:
            out.append(rel[i])
            i += 1
        else:
            raise ValueError('关系串里有不认识的关系：%r' % rel[i:])
    return out


def _split(rel, point=False):
    """关系串 → 关系名列表：点代数是单字符，区间代数是单/双字名拼接。"""
    if point:
        return [c for c in _P_ORDER if c in rel]
    return _names(rel)


def _conv_rel(rel, point=False):
    table = _P_CONVERSE if point else tables()[0]
    order = _P_ORDER if point else BASE
    if point:
        return ''.join(v for v in order if v in {table[c] for c in rel})
    return ''.join(v for v in order
                   if v in {table[c] for c in _names(rel)})


def _comp_rel(a, b, point=False):
    """两个关系集（名拼接串）的复合：逐对复合取并。"""
    if point:
        out = set()
        for x in a:
            for y in b:
                out |= set(_P_COMPOSE[(x, y)])
        return ''.join(v for v in _P_ORDER if v in out)
    comp = tables()[1]
    out = set()
    for x in _names(a):
        for y in _names(b):
            out |= set(_names(comp.get((x, y), '')))   # 按名拆，别按字符（踩过）
    return ''.join(v for v in BASE if v in out)


# ══════════════════════════════════════════════════════════════
# 三、路径一致性（Allen 1983）：R_ij ← R_ij ∩ (R_ik ∘ R_kj) 到不动点
# ══════════════════════════════════════════════════════════════

def _path_consistency(n, labels, point=False):
    """返回 (是否没挤出空集, 矩阵, 挤空记录)。"""
    full = ''.join(_P_ORDER) if point else ''.join(BASE)
    m = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                m[(i, j)] = '=' if point else 'e'
            elif (i, j) in labels:
                m[(i, j)] = labels[(i, j)]
            elif (j, i) in labels:
                m[(i, j)] = _conv_rel(labels[(j, i)], point)
            else:
                m[(i, j)] = full
    for i in range(n):                         # 一上来就空 = 给的约束自相矛盾
        for j in range(n):
            if i != j and not m[(i, j)]:
                return False, m, [{'pair': (i, j), 'via': (i, i, j)}]
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                for k in range(n):
                    if i == k or j == k:
                        continue
                    allow = set(_split(_comp_rel(m[(i, k)], m[(k, j)], point),
                                       point))
                    new = ''.join(x for x in _split(m[(i, j)], point)
                                  if x in allow)
                    if new != m[(i, j)]:
                        m[(i, j)] = new
                        changed = True
                        if not new:
                            return False, m, [{'pair': (i, j),
                                               'via': (i, k, j)}]
    return True, m, []


def _fmt_matrix(events, m):
    out = {}
    for i, a in enumerate(events):
        for j, b in enumerate(events):
            if i != j:
                out['%s|%s' % (a, b)] = m[(i, j)]
    return out


# ══════════════════════════════════════════════════════════════
# 四、见证模型：给每个事件一组整数区间，**真满足**所有关系才算数
# ══════════════════════════════════════════════════════════════

def _rel_of_points(s1, e1, s2, e2):
    """两个具体整数区间的定性关系（唯一）。"""
    if s1 < s2:
        if e1 < s2:
            return 'b'
        if e1 == s2:
            return 'm'
        if e1 < e2:
            return 'o'
        if e1 == e2:
            return 'f'
        return 'di' if s1 < s2 else None
    if s1 == s2:
        if e1 < e2:
            return 's'
        if e1 == e2:
            return 'e'
        return 'si'
    # s1 > s2：反向取逆
    back = _rel_of_points(s2, e2, s1, e1)
    return _conv_rel(back)


def _find_model(n, labels, names, budget=MAX_SOLVE_NODES):
    """回溯找一组整数区间。返回 (模型或 None, 用掉的节点数)。"""
    assigned = {}
    nodes = [0]
    span = 2 * n

    def allowed(i, j):
        if (i, j) in labels:
            return set(_names(labels[(i, j)]))
        if (j, i) in labels:
            return set(_names(_conv_rel(labels[(j, i)])))
        return set(BASE)

    def compatible(i, s, e):
        for j, (s2, e2) in assigned.items():
            if j == i:
                continue
            if _rel_of_points(s, e, s2, e2) not in allowed(i, j):
                return False
        return True

    def rec(idx):
        if idx == n:
            return True
        for s in range(span):
            for e in range(s + 1, span + 1):
                nodes[0] += 1
                if nodes[0] > budget:
                    return False
                if compatible(idx, s, e):
                    assigned[idx] = (s, e)
                    if rec(idx + 1):
                        return True
                    del assigned[idx]
        return False

    got = rec(0)
    return ({names[k]: list(v) for k, v in assigned.items()} if got else None,
            nodes[0])


# ══════════════════════════════════════════════════════════════
# 五、对外接口
# ══════════════════════════════════════════════════════════════

def _out(verdict, boundary, **kw):
    out = {'verdict': verdict, 'matrix': {}, 'conflict': None, 'model': None,
           'composed': None, 'conversed': None, 'boundary': boundary}
    out.update(kw)
    return out


def _pending(msg):
    return _out('input_pending', msg)


def run(inputs):
    """
    做什么：区间代数（Allen 定性时序推理）——复合/逆关系、路径一致性、
    以及有界预算内的见证模型。

    返回 dict（见模块 docstring）。"""
    if not isinstance(inputs, dict):
        return _pending('inputs 必须是 dict')
    mode = inputs.get('mode') or 'consistent'
    if mode not in ('consistent', 'solve', 'point', 'compose', 'converse'):
        return _pending('mode 应为 consistent/solve/point/compose/converse，'
                        '得到 %r' % (mode,))

    if mode in ('compose', 'converse'):
        try:
            if mode == 'converse':
                r = _parse_rel(inputs.get('relation'))
                if not r:
                    return _pending('converse 需 relation（关系名或关系集）')
                out = _conv_rel(r)
                return _out('conversed',
                            '逆关系：%s 的逆是 %s（%s）'
                            % (r, out, '、'.join(REL_CN[c]
                                                 for c in _names(out))),
                            conversed=out)
            rels = inputs.get('relations')
            if not isinstance(rels, (list, tuple)) or len(rels) != 2:
                return _pending('compose 需 relations=[关系1, 关系2]')
            a, b = _parse_rel(rels[0]), _parse_rel(rels[1])
            out = _comp_rel(a, b)
            note = ('；'.join('%s∘%s→%s' % (x, y, ''.join(tables()[1]
                                                        .get((x, y), '')))
                              for x in a for y in b))
            return _out('composed',
                        '复合：%s ∘ %s = %s（%s）——读作「X %s Y 且 Y %s Z ⟹ '
                        'X 与 Z 可能是 %s」。逐对：%s'
                        % (a, b, out or '（空集）',
                           '、'.join(REL_CN[c] for c in _names(out)) if out
                           else '不可能',
                           a, b, out or '（没有）', note),
                        composed=out)
        except ValueError as e:
            return _out('parse_error', str(e))

    point = (mode == 'point')
    events = inputs.get('events')
    rels = inputs.get('relations')
    if not isinstance(events, (list, tuple)) or not events:
        return _pending('需 events（事件名列表，如 ["立项","开发","上线"]）与 '
                        'relations（[[A, 关系, B], …]）——诚实拦截')
    if not all(isinstance(x, str) and x for x in events):
        return _pending('events 元素应为非空字符串（事件名）')
    if len(set(events)) != len(events):
        return _pending('events 有重名——同一事件不该出现两次')
    if len(events) > MAX_EVENTS:
        return _out('size_limit',
                    '事件 %d 个 > 上限 %d——路径一致性与见证搜索都不硬跑'
                    % (len(events), MAX_EVENTS))
    if not isinstance(rels, (list, tuple)) or not rels:
        return _pending('需 relations（如 [["立项","b","开发"], '
                        '["开发","m","上线"]]）——诚实拦截')
    idx = {e: i for i, e in enumerate(events)}
    labels = {}
    direct = None
    try:
        for item in rels:
            if not (isinstance(item, (list, tuple)) and len(item) == 3):
                return _pending('关系项应形如 [A, 关系, B]，得到 %r' % (item,))
            a, rel, b = item
            if a not in idx or b not in idx:
                return _pending('关系项 %r 引用了不在 events 里的事件——'
                                '诚实拦截（不隐式加事件）' % (item,))
            key = (idx[a], idx[b])
            got = _parse_rel(rel, point)
            if key in labels:
                # 同一对事件给两次说法 = **两条约束同时成立** → 求交（别覆盖，踩过）
                order = _P_ORDER if point else BASE
                old = set(labels[key] if point else _names(labels[key]))
                new = set(got if point else _names(got))
                keep = ''.join(x for x in order if x in (old & new))
                labels[key] = keep
                if not keep:
                    direct = {'pair': [a, b],
                              'why': '同一对事件的两次说法没有交集：%s 与 %s'
                                     '不可能同时成立' % (rel, a + '|' + b)}
            else:
                labels[key] = got
    except ValueError as e:
        return _out('parse_error', str(e))

    if direct:
        return _out('inconsistent',
                    BOUNDARY + '（判定：**不一致**——这是确定结论：直接给出的'
                    '两条说法就打架了）',
                    matrix={}, conflict=direct)

    ok, m, emptied = _path_consistency(len(events), labels, point)
    if not ok:
        e0 = emptied[-1]
        i, j = e0['pair']
        a, b, c = e0['via']
        name = lambda x: events[x]                     # noqa: E731
        return _out('inconsistent',
                    BOUNDARY + '（判定：**不一致**——这是确定结论，因为找到了'
                    '被挤空的那一对）',
                    matrix=_fmt_matrix(events, m),
                    conflict={'pair': [name(i), name(j)],
                              'via': [name(a), name(b), name(c)],
                              'why': '沿「%s → %s → %s」推不出任何可能关系，'
                                     '与已给的「%s 与 %s」冲突'
                                     % (name(a), name(b), name(c),
                                        name(i), name(j))})

    matrix = _fmt_matrix(events, m)
    if mode == 'consistent':
        return _out('path_consistent',
                    BOUNDARY + '（判定：**没发现冲突**——路径一致性在区间代数上'
                    '只是必要条件，不等于有解；要确定结论用 mode=solve 找见证）',
                    matrix=matrix)
    if mode == 'point':
        return _out('consistent',
                    BOUNDARY + '（判定：**一致**——点代数上路径一致性是完备的，'
                    '这就是确定结论）', matrix=matrix)

    model, nodes = _find_model(len(events), labels, events)
    if model is None:
        return _out('not_found_in_budget',
                    BOUNDARY + '（在 %d 个搜索节点内没找到见证——**不等于无解**，'
                    '只是本构件的预算到此为止）' % nodes, matrix=matrix)
    return _out('model_found',
                BOUNDARY + '（找到了见证：给每个事件一组整数区间，它们确实满足'
                '你给的全部关系——可复核）', matrix=matrix, model=model)


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 70)
    print('区间代数（Allen 定性时序推理）构件 · 自测')
    print('=' * 70)

    inv, comp = tables()
    assert inv['m'] == 'mi' and inv['e'] == 'e', inv
    print(f"✅ 表是现推的：逆关系 相接↔{inv['m']}、同时↔{inv['e']}")

    r1 = run({'mode': 'compose', 'relations': ['m', 'm']})
    assert r1['verdict'] == 'composed' and r1['composed'] == 'b', r1
    print(f"✅ 复合：相接 ∘ 相接 = {r1['composed']}（先于）——"
          'A 接 B、B 接 C ⟹ A 先于 C')

    r2 = run({'mode': 'converse', 'relation': 'm'})
    assert r2['conversed'] == 'mi', r2
    print(f"✅ 逆关系：相接的逆 = {r2['conversed']}（被相接）")

    r3 = run({'events': ['立项', '开发', '上线'],
              'relations': [['立项', 'b', '开发'], ['开发', 'b', '上线']]})
    assert r3['verdict'] == 'path_consistent', r3
    assert r3['matrix']['立项|上线'] == 'b', r3['matrix']
    print('✅ 传递：立项先于开发、开发先于上线 → 推出立项先于上线'
          f"（矩阵里 {r3['matrix']['立项|上线']}）")

    r4 = run({'events': ['A', 'B', 'C'],
              'relations': [['A', 'b', 'B'], ['B', 'b', 'C'], ['C', 'b', 'A']]})
    assert r4['verdict'] == 'inconsistent', r4
    print(f"✅ 成环冲突：A 先于 B、B 先于 C、C 先于 A → {r4['verdict']}"
          f"（挤空通过 {r4['conflict']['via']}）")

    r5 = run({'mode': 'solve', 'events': ['立项', '开发', '上线'],
              'relations': [['立项', 'b', '开发'], ['开发', 'm', '上线']]})
    assert r5['verdict'] == 'model_found', r5
    print(f"✅ 见证：{r5['model']}（整数区间，真满足给的关系）")

    r6 = run({'mode': 'solve', 'events': ['A', 'B'],
              'relations': [['A', 'b', 'B'], ['A', 'bi', 'B']]})
    assert r6['verdict'] == 'inconsistent', r6
    print(f"✅ 直接矛盾：A 先于 B 又说 A 晚于 B → {r6['verdict']}")

    r7 = run({'mode': 'point', 'events': ['P', 'Q'],
              'relations': [['P', '<', 'Q'], ['P', '>', 'Q']]})
    assert r7['verdict'] == 'inconsistent', r7
    print('✅ 点代数对照：P < Q 且 P > Q → 不一致（点代数上这是完备判定）')

    r8 = run({'events': ['A', 'B'], 'relations': [['A', 'x', 'B']]})
    assert r8['verdict'] == 'parse_error', r8
    print('✅ 边界：不认识的关系名 → parse_error（不猜）')

    print('=' * 70)
    print('区间代数构件自测：全部通过 ✅')
    print('=' * 70)
