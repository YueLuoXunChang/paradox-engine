# -*- coding: utf-8 -*-
"""
description_logic.py — 描述逻辑 ALC（概念包含 / 本体推理）· 第 3 层按痛点接入
================================================================================
概念来源：**外部经典共识**——描述逻辑 ALC（Schmidt-Schauß & Smolka 1991；
表列算法与判定性见 Baader & Sattler 2000 "Tableau Algorithms for Description
Logics"、Horrocks-Sattler-Tobies 1999 的 ALC 表列判定定理）。归借鉴区
（落落三问：借什么=概念描述语言 ⟓⊓⊔¬∃∀⟔ 与"包含关系"这套推理；为什么=
第 3 类"关系结构"与第 10 类"定义辨析"现在只有**有限论域一阶展开**——
它能判"在这几个对象上成不成立"，**答不了"是不是所有 A 都是 B"这种概念层级**
（本体对齐、定义辨析要的正是后者）；怎么记账=标注来源归借鉴区，不混原创区）。

本构件做什么（一句话）：
    拿一个**概念描述**（A ⊓ ∃R.B 这种）与一套**本体公理**（A ⊑ B 这类包含关系），
    判：这个概念可不可满足 · 甲是不是包含于乙 · 甲乙等不等价 · 两个概念相不相交 ·
    以及把整张本体的**概念层级**算出来（谁是谁的子类、哪些互相等价）。

语言（ALC，够用且边界清楚）：
    概念 := 原子名 | ⊤（全） | ⊥（空）
          | 概念 ⊓ 概念（交，也认 & / ∧）| 概念 ⊔ 概念（并，也认 | / ∨）
          | ¬概念（也认 ! ）| ∃R.概念（存在，也认 exists R.C）| ∀R.概念（全称，也认 all R.C）
    本体 := 一行一条：'C ⊑ D'（包含）或 'C ≡ D'（等价，等于两条包含）

怎么算的（白话，表列法）：
    把"概念可满足吗"化成"表列展开会不会处处撞车"——从一个节点（装着待满足的概念）
    开始，逐条规则往下推：交就拆开、并就分两支、∃R.C 就造一个 R 后继并把 C 装进去、
    ∀R.C 就发给已有的每个 R 后继；分支里同时出现 A 与 ¬A（或 ⊥）就叫**撞车**，
    该支关闭。全部分支关闭 → 不可满足；有一支推到底没撞车 → 可满足，并把
    那棵树当作**规范模型**交出来（可复核）。
    本体公理用"内部化"处理：每条 C ⊑ D 变成 ¬C ⊔ D，装进每个节点 ✓。
    可能无限（如 A ≡ ∃R.A）时用**子集阻塞**：某节点的标号被祖先包含就停下不展开，
    于是必然有限步内终止（这一步不做，循环本体就会转不完——A ≡ ∃R.A 是必测例）。

诚实边界：
    - 只做 **ALC**：没有数量限制（≥n / ≤n）、没有角色层级/逆角色/传递角色、没有具体域
      （数字、字符串）——那些是更强的 DL，本构件不假装能做；
    - 只做**概念层**（TBox + 概念推理）：**不做 ABox**（"张三属于某概念"这类个体断言）；
    - 节点数有上限（超了报 size_limit，不硬跑）；原子概念多了不硬分类；
    - 只诊断不决策：给的是"按这套语言与公理推出来什么"，不替使用者定概念该不该这么划。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'satisfiable'（默认）|'subsumption'|'equivalent'|'disjoint'|'classify'
        concept: str——被查的概念（satisfiable 用）
        sub / super: str——包含的两端（subsumption / disjoint 用）
        c1 / c2: str——等价的两端（equivalent 用）
        tbox: list[str]——本体公理（如 ['A ⊑ B ⊓ C', 'D ≡ ∃R.E']）
        max_nodes: int——表列节点上限（默认 400）
    输出:
        verdict: str——'satisfiable'|'unsatisfiable'|'subsumed'|'not_subsumed'
                        |'equivalent'|'not_equivalent'|'disjoint'|'not_disjoint'
                        |'classified'|'parse_error'|'input_pending'|'size_limit'
                        |'internal_error'
        model: dict?——可满足时的规范模型（节点标号 + 角色边；blocked 表示回接祖先）
        clash: dict?——不可满足时：关闭了多少支、给一条撞车的例子
        classify: dict?——分类结果（等价类 + 严格包含关系）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'concept': 'str?', 'sub': 'str?', 'super': 'str?',
           'c1': 'str?', 'c2': 'str?', 'tbox': 'list?', 'max_nodes': 'int?'},
    'out': {'verdict': 'str', 'model': 'dict?', 'clash': 'dict?',
            'classify': 'dict?', 'boundary': 'str'},
}

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BOUNDARY = ('描述逻辑 ALC（外部共识：表列算法与判定性见 Baader & Sattler 2000 / '
            'Horrocks-Sattler-Tobies 1999，借鉴区）：判概念可满足、概念包含、'
            '等价、相交与本体分类。**只做 ALC**——没有数量限制（≥n/≤n）、'
            '没有角色层级/逆角色/传递角色、没有具体域；**只做概念层（TBox），'
            '不做 ABox 个体断言**。节点数有上限，超了报 size_limit 不硬跑。'
            '报"不可满足"是**确定结论**（表列全部分支关闭）；报"可满足"给规范模型'
            '（节点上的标号就是待满足的概念，blocked 节点表示回接到祖先）。'
            '只诊断不决策：不替使用者定概念该不该这么划。')

MAX_NODES = 400
MAX_ATOMS_CLASSIFY = 8
MAX_LABEL_SHOWN = 40    # 模型里每个节点最多列几个概念（截了会在 model 里标 truncated）
_KEYWORDS = ('exists', 'all', 'and', 'or', 'not', 'some', 'every')

# 记号：⊓ ⊔ ¬ ∃ ∀ ⊤ ⊥ 与 ASCII 写法都认
_TOKEN = re.compile(r'\s*(≡|⊑|⊓|⊔|∀|∃|¬|->|&&|\|\||[&|!()]|<=|>='
                    r'|\.|,|[A-Za-z_][A-Za-z0-9_]*|⊤|⊥|\u22a4|\u22a5)')
_AND = ('⊓', '&', '&&', '∧')
_OR = ('⊔', '|', '||', '∨')
_NOT = ('¬', '!')
_TOP = ('⊤', 'top', 'TOP', 'True')
_BOT = ('⊥', 'bot', 'BOT', 'False')


class _ParseError(ValueError):
    pass


# ══════════════════════════════════════════════════════════════
# 一、概念表达式：解析 → 语法树 → 否定范式（NNF）
# ══════════════════════════════════════════════════════════════

def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            raise _ParseError('无法识别的字符：%r' % s[i:i + 8])
        out.append(m.group(1))
        i = m.end()
    return out


def _parse_concept(text):
    """概念表达式 → 语法树（元组形态）。"""
    if not isinstance(text, str) or not text.strip():
        raise _ParseError('概念不能为空')
    toks = _tokenize(text.strip())
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def is_atom(t):
        return isinstance(t, str) and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t) \
            and t not in _KEYWORDS

    def union():
        left = inter()
        while peek() in _OR:
            take()
            left = ('or', left, inter())
        return left

    def inter():
        left = unary()
        while peek() in _AND:
            take()
            left = ('and', left, unary())
        return left

    def unary():
        t = peek()
        if t in _NOT:
            take()
            return ('not', unary())
        if t in ('∃', '∀', 'exists', 'all', 'some', 'every'):
            q = take()
            if q in ('∃', 'some'):
                kind = 'ex'
            elif q in ('∀', 'every'):
                kind = 'all'
            else:
                kind = 'ex' if q == 'exists' else 'all'
            role = take()
            if not is_atom(role):
                raise _ParseError('量词后面要跟角色名（如 ∃R.C），得到 %r' % (role,))
            if peek() == '.':
                take()
            return (kind, role, unary())
        if t == '(':
            take()
            inner = union()
            if take() != ')':
                raise _ParseError('括号没闭合')
            return inner
        if t in _TOP or t in _BOT:
            take()
            return ('top',) if t in _TOP else ('bot',)
        if is_atom(t):
            take()
            return ('atom', t)
        raise _ParseError('看不懂的记号：%r' % (t,))

    ast = union()
    if pos[0] != len(toks):
        raise _ParseError('表达式解析完还有多余记号：%r' % toks[pos[0]:])
    return ast


def _nnf(node, neg=False):
    """否定范式：¬ 只留在原子前面；⊤/⊥、⊓/⊔、∃/∀ 按对偶翻。"""
    k = node[0]
    if k == 'atom':
        return ('lit', node[1], neg)
    if k == 'top':
        return ('bot',) if neg else ('top',)
    if k == 'bot':
        return ('top',) if neg else ('bot',)
    if k == 'not':
        return _nnf(node[1], not neg)
    if k == 'and':
        a, b = _nnf(node[1], neg), _nnf(node[2], neg)
        return ('or', a, b) if neg else ('and', a, b)
    if k == 'or':
        a, b = _nnf(node[1], neg), _nnf(node[2], neg)
        return ('and', a, b) if neg else ('or', a, b)
    if k in ('ex', 'all'):
        other = 'all' if k == 'ex' else 'ex'
        return (other if neg else k, node[1], _nnf(node[2], neg))
    raise _ParseError('看不懂的节点：%r' % (k,))


def _fmt(node):
    k = node[0]
    if k == 'lit':
        return ('¬' if node[2] else '') + node[1]
    if k == 'top':
        return '⊤'
    if k == 'bot':
        return '⊥'
    if k == 'and':
        return '%s ⊓ %s' % (_fmt(node[1]), _fmt(node[2]))
    if k == 'or':
        return '%s ⊔ %s' % (_fmt(node[1]), _fmt(node[2]))
    if k == 'ex':
        return '∃%s.%s' % (node[1], _fmt(node[2]))
    if k == 'all':
        return '∀%s.%s' % (node[1], _fmt(node[2]))
    return '?'


def _atoms(node, out=None):
    out = set() if out is None else out
    k = node[0]
    if k == 'lit':
        out.add(node[1])
    elif k in ('and', 'or'):
        _atoms(node[1], out)
        _atoms(node[2], out)
    elif k in ('ex', 'all'):
        _atoms(node[2], out)
    return out


def _parse_tbox(tbox):
    """本体公理 → [(左, 右)] 两条：'C ⊑ D' 与 'C ≡ D'（等价拆成双向包含）。"""
    if not tbox:
        return []
    if not isinstance(tbox, (list, tuple)):
        raise _ParseError('tbox 应是公理字符串列表（如 ["A ⊑ B"]）')
    out = []
    for line in tbox:
        if not isinstance(line, str) or not line.strip():
            raise _ParseError('公理要是非空字符串，得到 %r' % (line,))
        text = line.strip()
        if '≡' in text:
            left, _, right = text.partition('≡')
            out.append((left, right))
            out.append((right, left))
        elif '⊑' in text:
            left, _, right = text.partition('⊑')
            out.append((left, right))
        elif '->' in text:
            left, _, right = text.partition('->')
            out.append((left, right))
        else:
            raise _ParseError('公理要写成「C ⊑ D」或「C ≡ D」（也认 ->）：%r' % line)
    return [(_parse_concept(a), _parse_concept(b)) for a, b in out]


# ══════════════════════════════════════════════════════════════
# 二、表列展开（ALC + 一般 TBox 内部化 + 子集阻塞）
# ══════════════════════════════════════════════════════════════

def _internalize(tbox):
    """内部化：每条 C ⊑ D 变成 ¬C ⊔ D，装进每个节点。"""
    return [('or', _nnf(c, neg=True), _nnf(d)) for c, d in tbox]


class _TooBig(Exception):
    pass


def _clash(label):
    """撞车检查：⊥ 在标号里，或同时出现 A 与 ¬A。"""
    if ('bot',) in label:
        return '⊥ 在标号里'
    for c in label:
        if c[0] == 'lit' and ('lit', c[1], not c[2]) in label:
            return '同时要求 %s 与 ¬%s' % (c[1], c[1])
    return None


def _blocked(label, anc_labels):
    """
    子集阻塞：本节点标号被某个祖先标号**装下**（label ⊆ 祖先标号）→ 不再为它造后继。

    方向不能反：阻塞等于"用祖先顶上这个节点"，祖先得满足本节点的**全部**要求，
    所以是 L(本) ⊆ L(祖先)。反过来的写法（L(本) ⊇ L(祖先)）没有这条依据——
    本节点比祖先多出来的要求没人替它满足，可能是假阻塞。
    """
    return any(label <= a for a in anc_labels)


def _expand(root_label, internal, max_nodes):
    """
    从一个根标号出发做表列展开。返回 (是否可满足, 模型或 None, 撞车信息)。

    做法：**纯递归**（每一支都在自己的标号副本上算，不共用可变状态）——
      ① ⊓ 拆到底（工作栈，嵌套的也要拆）；
      ② 撞车（⊥ 或 A/¬A 同现）就关闭这一支；
      ③ ⊔ 取一个分两支，各递归一次，哪支活着就用哪支（另一支整个丢掉，不留痕）；
      ④ 剩下的标号里只有原子与量词了：
         - 被祖先标号装下 → 阻塞，不再造后继（无限本体靠这个收口）；
         - 否则每个 ∃R.C 造一个后继，后继标号 = C ∪ 内部化公理 ∪ 本节点**全部** ∀R.· 的收束
           （量词规则在造后继时一次灌满，后面不会再改标号——所以不存在"标号后来长了、
           早先的分支选择要重来"的问题，这正是上一版原地改标号踩的坑）。
    节点数有上限（含跑死的支也计数），超了抛 _TooBig，由上层报 size_limit。
    """
    budget = [0]         # 造过的节点数（跑死的支也记，诚实）
    closed = []          # 关闭的分支上撞车的例子

    def solve(label, anc_labels, role):
        """
        把 label 这一支推到底。返回 (True, 节点树) 或 (False, None)。
        节点树 = {'label', 'blocked', 'role', 'children'}
        """
        if budget[0] >= max_nodes:
            raise _TooBig('节点数超过上限 %d' % max_nodes)
        budget[0] += 1
        # ① ⊓ 拆到底
        cur = set(label)
        stack = list(cur)
        while stack:
            c = stack.pop()
            if c[0] != 'and' or c not in cur:
                continue
            cur.discard(c)
            for part in (c[1], c[2]):
                if part not in cur:
                    cur.add(part)
                    stack.append(part)
        # ② 撞车
        why = _clash(cur)
        if why:
            closed.append({'on': [_fmt(c) for c in sorted(cur, key=_fmt)[:6]],
                           'why': why})
            return False, None
        # ③ ⊔ 分叉（第一个 ⊔ 的两支各试一次；拆完还有 ⊔ 就交给递归）
        ors = sorted([x for x in cur if x[0] == 'or'], key=_fmt)
        if ors:
            c = ors[0]
            for branch in (c[1], c[2]):
                ok, node = solve((cur - {c}) | {branch}, anc_labels, role)
                if ok:
                    return True, node
            return False, None
        # ④ 阻塞
        blocked = _blocked(cur, anc_labels)
        node = {'label': frozenset(cur), 'blocked': blocked, 'role': role,
                'children': []}
        if blocked:
            return True, node
        # ⑤ 造后继：∃ 的填充物 + 内部化公理 + 本节点所有同角色的 ∀ 收束
        kids = []
        for c in sorted([x for x in cur if x[0] == 'ex'], key=_fmt):
            sub = [c[2]] + list(internal)
            sub += [d[2] for d in cur if d[0] == 'all' and d[1] == c[1]]
            ok, child = solve(sub, anc_labels + [frozenset(cur)], c[1])
            if not ok:
                return False, None
            kids.append(child)
        node['children'] = kids
        return True, node

    ok, tree = solve(list(root_label) + list(internal), [], None)
    if not ok:
        return False, None, {'closed_branches': len(closed),
                             'example': (closed[-1] if closed else None),
                             'nodes_tried': budget[0]}
    model = {'nodes': [], 'edges': [], 'truncated': False}

    def walk(n, parent_id):
        nid = len(model['nodes'])
        concepts = [_fmt(c) for c in sorted(n['label'], key=_fmt)]
        if len(concepts) > MAX_LABEL_SHOWN:
            model['truncated'] = True     # 截了就说，不装作给全了
        model['nodes'].append({'id': nid,
                               'concepts': concepts[:MAX_LABEL_SHOWN],
                               'blocked': bool(n['blocked'])})
        if parent_id is not None:
            model['edges'].append({'from': parent_id, 'to': nid,
                                   'role': n['role']})
        for ch in n['children']:
            walk(ch, nid)

    walk(tree, None)
    return True, model, None


# ══════════════════════════════════════════════════════════════
# 三、对外推理
# ══════════════════════════════════════════════════════════════

def _out(verdict, boundary=BOUNDARY, **kw):
    out = {'verdict': verdict, 'model': None, 'clash': None, 'classify': None,
           'boundary': boundary}
    out.update(kw)
    return out


def run(inputs):
    """
    做什么：ALC 概念推理——可满足性 / 包含 / 等价 / 相交 / 本体分类。

    返回 dict（见模块 docstring）。"""
    if not isinstance(inputs, dict):
        return _out('input_pending', 'inputs 必须是 dict')
    mode = inputs.get('mode') or 'satisfiable'
    if mode not in ('satisfiable', 'subsumption', 'equivalent', 'disjoint',
                    'classify'):
        return _out('input_pending',
                    'mode 应为 satisfiable/subsumption/equivalent/disjoint/'
                    'classify，得到 %r' % (mode,))
    max_nodes = inputs.get('max_nodes', MAX_NODES)
    if not isinstance(max_nodes, int) or max_nodes < 10:
        return _out('input_pending', 'max_nodes 应是不小于 10 的整数')

    try:
        internal = _internalize(_parse_tbox(inputs.get('tbox')))
    except _ParseError as e:
        return _out('parse_error', '本体公理解析不了：%s' % e)

    if mode == 'satisfiable':
        text = inputs.get('concept')
        if not isinstance(text, str) or not text.strip():
            return _out('input_pending',
                        'satisfiable 需 concept（如 "A ⊓ ∃R.B"）——诚实拦截')
        try:
            c = _nnf(_parse_concept(text))
        except _ParseError as e:
            return _out('parse_error', str(e))
        return _answer_sat(c, internal, max_nodes, '概念「%s」' % text)

    if mode in ('subsumption', 'disjoint'):
        a_txt = inputs.get('sub')
        b_txt = inputs.get('super')
        if not isinstance(a_txt, str) or not isinstance(b_txt, str):
            return _out('input_pending',
                        '%s 需 sub 与 super（两端的概念表达式）——诚实拦截'
                        % mode)
        try:
            a = _nnf(_parse_concept(a_txt))
            b = _nnf(_parse_concept(b_txt))
        except _ParseError as e:
            return _out('parse_error', str(e))
        if mode == 'disjoint':
            # C 与 D 不相交 ⟺ C ⊓ D 不可满足
            return _answer_disjoint(a, b, internal, max_nodes, a_txt, b_txt)
        # C ⊑ D ⟺ C ⊓ ¬D 不可满足
        test = ('and', a, _nnf(_parse_concept(b_txt), neg=True))
        r = _answer_sat(test, internal, max_nodes,
                        '「%s 且非（%s）」' % (a_txt, b_txt), quiet=True)
        if r['verdict'] == 'unsatisfiable':
            return _out('subsumed',
                        '包含：**%s ⊑ %s 成立**（在本体下）——因为「%s 且非 %s」'
                        '不可满足，找不到反例。%s'
                        % (a_txt, b_txt, a_txt, b_txt, BOUNDARY))
        if r['verdict'] == 'satisfiable':
            return _out('not_subsumed', model=r['model'],
                        boundary='不包含：**%s ⊑ %s 不成立**——下面的模型里'
                                 '「%s 且非 %s」成立，就是反例（可复核）。%s'
                        % (a_txt, b_txt, a_txt, b_txt, BOUNDARY))
        return r

    if mode == 'equivalent':
        a_txt = inputs.get('c1')
        b_txt = inputs.get('c2')
        if not isinstance(a_txt, str) or not isinstance(b_txt, str):
            return _out('input_pending',
                        'equivalent 需 c1 与 c2——诚实拦截')
        try:
            a = _nnf(_parse_concept(a_txt))
            b = _nnf(_parse_concept(b_txt))
        except _ParseError as e:
            return _out('parse_error', str(e))
        r1 = _expand([('and', a, _nnf(_parse_concept(b_txt), neg=True))],
                     internal, max_nodes)
        r2 = _expand([('and', b, _nnf(_parse_concept(a_txt), neg=True))],
                     internal, max_nodes)
        if not r1[0] and not r2[0]:
            return _out('equivalent',
                        '等价：**%s ≡ %s 成立**（互相包含都在本体下成立）。%s'
                        % (a_txt, b_txt, BOUNDARY))
        return _out('not_equivalent', model=(r1[1] or r2[1]),
                    boundary='不等价：%s。%s'
                    % ('%s 不包含于 %s' % (a_txt, b_txt) if r1[0]
                       else '%s 不包含于 %s' % (b_txt, a_txt), BOUNDARY))

    # classify：把本体里的原子概念两两判包含，给等价类与严格层级
    atoms = set()
    for c in internal:
        _atoms(c, atoms)
    tbox_nodes = []
    try:
        for a, b in _parse_tbox(inputs.get('tbox')):
            tbox_nodes += [_nnf(a), _nnf(b)]
    except _ParseError as e:
        return _out('parse_error', str(e))
    for c in tbox_nodes:
        _atoms(c, atoms)
    if len(atoms) > MAX_ATOMS_CLASSIFY:
        return _out('size_limit',
                    '原子概念 %d 个 > 上限 %d——两两判定不硬跑（%s）'
                    % (len(atoms), MAX_ATOMS_CLASSIFY, '、'.join(sorted(atoms))))
    if not atoms:
        return _out('input_pending', 'classify 需 tbox（要有原子概念）——诚实拦截')
    names = sorted(atoms)
    subs = {}
    for x in names:
        for y in names:
            if x == y:
                continue
            test = ('and', ('lit', x, False), ('lit', y, True))
            subs[(x, y)] = not _expand([test], internal, max_nodes)[0]
    equiv = []
    seen = set()
    for x in names:
        if x in seen:
            continue
        cls = [y for y in names if y == x or (subs.get((x, y)) and subs.get((y, x)))]
        seen |= set(cls)
        equiv.append(sorted(cls))
    strict = sorted({(x, y) for (x, y), v in subs.items() if v
                     and not subs.get((y, x))})
    return _out('classified', classify={'atoms': names,
                                        'equivalence_classes': equiv,
                                        'strict_subsumptions':
                                            [list(x) for x in strict]},
                boundary='分类完成：%d 个原子概念 → %d 个等价类、%d 条严格包含。'
                         '（判定方式是两两问「可不可满足」，不是抽公式；'
                         '结果可复核。）%s'
                % (len(names), len(equiv), len(strict), BOUNDARY))


def _answer_sat(node, internal, max_nodes, label, quiet=False):
    try:
        ok, model, clash = _expand([node], internal, max_nodes)
    except _TooBig as e:
        return _out('size_limit', '%s——%s，不硬跑' % (e, BOUNDARY))
    except Exception as e:  # noqa: BLE001——真出意外如实报
        return _out('internal_error', '表列展开出意外（%s: %s）' % (
            type(e).__name__, e))
    if ok:
        note = ('（有的节点标号太长，模型里每条只列前 %d 个概念——model 里标了 '
                'truncated）' % MAX_LABEL_SHOWN) if model.get('truncated') else ''
        return _out('satisfiable', model=model,
                    boundary='可满足：%s 在给定本体下能成立——下面这棵树就是规范'
                             '模型（节点标号是它要满足的概念，blocked 表示回接到'
                             '祖先）。%s%s' % (label, note, BOUNDARY))
    return _out('unsatisfiable', clash=clash,
                boundary='不可满足：%s 在给定本体下处处撞车（表列全部分支关闭，'
                         '这是确定结论）；关掉 %s 支，撞车例子：%s。%s'
                % (label, clash['closed_branches'] if clash else '?',
                   (clash or {}).get('example', {}).get('why', '（无）'),
                   BOUNDARY))


def _answer_disjoint(a, b, internal, max_nodes, a_txt, b_txt):
    test = ('and', a, b)
    r = _answer_sat(test, internal, max_nodes,
                    '「%s 且 %s」' % (a_txt, b_txt), quiet=True)
    if r['verdict'] == 'unsatisfiable':
        return _out('disjoint',
                    '不相交：**%s 与 %s 没有公共个体**（同时在两边的概念不可满足）。%s'
                    % (a_txt, b_txt, BOUNDARY))
    if r['verdict'] == 'satisfiable':
        return _out('not_disjoint', model=r['model'],
                    boundary='不是不相交：下面的模型里有个体同时是 %s 和 %s'
                             '（可复核）。%s' % (a_txt, b_txt, BOUNDARY))
    return r


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
    print('描述逻辑 ALC 构件 · 自测')
    print('=' * 70)

    T = ['Woman ≡ Person ⊓ Female', 'Man ≡ Person ⊓ ¬Woman',
         'Lecturer ≡ Person ⊓ ∃teaches.Course']

    r1 = run({'mode': 'satisfiable', 'concept': 'A ⊓ ¬A'})
    assert r1['verdict'] == 'unsatisfiable', r1
    print('✅ 自相矛盾的概念：A ⊓ ¬A → 不可满足')

    r2 = run({'mode': 'subsumption', 'sub': 'Woman', 'super': 'Person',
              'tbox': T})
    assert r2['verdict'] == 'subsumed', r2
    print('✅ 本体下包含：Woman ⊑ Person（女人是人）')

    r3 = run({'mode': 'subsumption', 'sub': 'Person', 'super': 'Woman',
              'tbox': T})
    assert r3['verdict'] == 'not_subsumed' and r3['model'], r3
    print('✅ 反向不成立：Person ⊑ Woman 不成立，并给出反例模型')

    r4 = run({'mode': 'disjoint', 'sub': 'Man', 'super': 'Woman', 'tbox': T})
    assert r4['verdict'] == 'disjoint', r4
    print('✅ 不相交：男人与女人没有公共个体')

    r5 = run({'mode': 'satisfiable', 'concept': 'A',
              'tbox': ['A ≡ ∃R.A']})
    assert r5['verdict'] == 'satisfiable', r5
    print('✅ 循环本体（A ≡ ∃R.A 要无限模型）也能终止并判可满足——'
          '靠子集阻塞')

    r6 = run({'mode': 'subsumption', 'sub': '∃R.(A ⊔ B)',
              'super': '∃R.A ⊔ ∃R.B'})
    assert r6['verdict'] == 'subsumed', r6
    print('✅ 标准等价式之一：∃R.(A ⊔ B) ⊑ ∃R.A ⊔ ∃R.B')

    r7 = run({'mode': 'classify', 'tbox': T})
    assert r7['verdict'] == 'classified', r7
    print('✅ 本体分类：%d 个原子 → 等价类 %s'
          % (len(r7['classify']['atoms']),
             r7['classify']['equivalence_classes']))

    r8 = run({'mode': 'satisfiable', 'concept': 'A ⊓ ∃'})
    assert r8['verdict'] == 'parse_error', r8
    print('✅ 边界：写坏的概念 → parse_error（不猜）')

    print('=' * 70)
    print('描述逻辑 ALC 构件自测：全部通过 ✅')
    print('=' * 70)
