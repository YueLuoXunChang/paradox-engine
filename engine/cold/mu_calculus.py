# -*- coding: utf-8 -*-
"""
mu_calculus.py — 模态 μ 演算（不动点逻辑）· 第 3 层按痛点接入
================================================================
概念来源：**外部经典共识**——Kozen 1983 的 μ 演算（最小/最大不动点）、
Knaster–Tarski 不动点定理、Emerson & Jutla 1988/1993（模态 μ 演算的模型检查与
交替深度层级）。**归借鉴区**（落落三问：借什么=μ/ν 两个不动点算子和模态 ⟨a⟩/[a]；
为什么=引擎已经会 CTL（`model_check`）也会"自指不动点"（第 2 层机制），但**没有一件
把"反复、最终、从此以后"这类过程性质写成能算的不动点**——CTL 的路径量子是写死的，
表达不了交替更深的性质；怎么记账=标注来源归借鉴区，不混原创区）。

本构件做什么（一句话）：
    给一个**有限迁移系统**（状态 + 迁移 + 每个状态上的原子命题）和一个
    **μ 演算公式**，算出公式在哪些状态上成立：不动点 μ（最小）/ ν（最大）
    按"从空集往上加 / 从全集往下砍"一步步迭代到收敛，**每一步留痕**（可复核）。

语言（工程子集，够用且边界清楚）：
    原子   := 命题名（如 `win`）| ⊤ | ⊥
    一元   := !φ（也认 ¬）| <>φ（也认 ◇，任一后继）| []φ（也认 □，所有后继）
              | <a>φ（只看动作 a 的后继）| [a]φ（只看动作 a）
              | μX.φ | νX.φ（也认 mu X.φ / nu X.φ，X 是指针变量）
    二元   := φ & ψ（也认 ∧）| φ | ψ（也认 ∨）| φ -> ψ
    优先级：不动点/! /模态最紧 → & → | → ->。
    迁移   := [从, 到]（动作名默认 `-`）| [从, 到, 动作名]

怎么算的（白话）：
    每个公式的"意思"是一个**状态集合**（在这个状态上成立的那些状态）。原子查标号、
    并交差照常、`<>φ` 是"起码有一个后继落在 φ 里"、`[]φ` 是"每个后继都落在 φ 里"。
    不动点这样算：μX.φ 从**空集**出发反复代进去（X := φ 算出的集合），
    集合只会越加越多，加到不动了就停——那是**最小**解；νX.φ 从**全集**出发往下砍，
    砍到不动停——那是**最大**解。有限状态保证几步就收敛（最多 |S| 步）。
    留痕里写清每个不动点迭代了几步、每步多大——结论不是"我说成立"，是能看过程。

为什么它比 CTL 多一口（说清楚，不吹）：
    CTL 的 E/A 路径量子是**写死**的（EX/AX/EF/AF/EG/AG/EU/AU 八个），
    μ 演算用 μ/ν 加模态**自己拼**——上面八个都能翻成 μ 演算式子（本构件内置这张表，
    `mode='ctl'` 就是"先翻译再求值"），而**交替更深的性质 CTL 写不出来**
    （Emerson-Jutla 的交替深度层级；本构件不证这件事，只标来源）。

诚实边界：
    - **只做"给定有限结构上的求值/检查"（model checking）**：公式在**这个系统**上
      成立吗——不是逻辑普遍有效，更**不做"这公式有没有模型"的可满足性判定**
      （那是自动机 + EXPTIME 的活，本构件不碰，也不假装）；
    - 结构必须**有限、状态声明齐、迁移两端都是已声明状态**；状态数有上限；
    - 不动点变量必须**正出现**（在偶数层否定之下）——负出现（如 μX.¬X）**没有
      不动点语义**（迭代会来回跳），本构件诚实拦下并把**振荡过程**摆出来说明；
    - 同一变量名不许重复绑定（不做遮蔽）；该变量必须真的出现在它自己的作用域里；
    - 只诊断不决策：给的是"按这套语义算出来什么"，不替使用者定系统该不该这么建。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'evaluate'（默认）|'check'|'ctl'|'compare'
        formula: str——μ 演算公式（evaluate/check 用）
        states: list[str]——状态名
        transitions: list——[[从,到], [从,到,动作], ...]
        labels: dict——{状态: [原子命题]}
        init: list[str]?——检查哪些状态（缺省全部；check 用）
        c1 / c2: str?——compare 的两条公式
        ctl: str?——ctl 模式要翻译并求值的 CTL 公式
    输出:
        verdict: str——'evaluated'|'holds'|'fails'|'same'|'different'
                        |'parse_error'|'input_pending'|'non_monotone'
                        |'size_limit'|'internal_error'
        holds_in: list[str]——成立的状态
        fails_in: list[str]——不成立的状态
        truth: dict?——每个状态的真值（evaluate 模式）
        translation: str?——ctl 模式翻出来的 μ 演算式子（可复制去复用）
        fixpoints: list——每个不动点迭代了几步、每步多大（白箱）
        compare: dict?——compare 模式的差异状态
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'formula': 'str?', 'ctl': 'str?', 'c1': 'str?',
           'c2': 'str?', 'states': 'list?', 'transitions': 'list?',
           'labels': 'dict?', 'init': 'list?'},
    'out': {'verdict': 'str', 'holds_in': 'list', 'fails_in': 'list',
            'truth': 'dict?', 'translation': 'str?', 'fixpoints': 'list',
            'compare': 'dict?', 'boundary': 'str'},
}

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BOUNDARY = ('模态 μ 演算（外部共识：Kozen 1983 的不动点算子 · Knaster-Tarski 不动点定理 · '
            'Emerson & Jutla 1988/1993 的模型检查与交替深度，借鉴区）：'
            '在**给定有限迁移系统**上求公式成立的状态集，μ 从空集往上、ν 从全集往下迭代到'
            '收敛，每步留痕。**只做给定结构上的求值与检查（model checking）**——'
            '不是逻辑普遍有效，**更不做"公式有没有模型"的可满足性判定**（那是自动机 + '
            'EXPTIME 的活，本构件不碰）。不动点变量必须正出现（负出现没有不动点语义，'
            '会诚实拦下并摆出振荡过程）；状态数有上限，超了报 size_limit 不硬跑。'
            'CTL 的八个路径量子都能翻成 μ 演算式子（内置翻译表，`mode=ctl` 可复核）；'
            '交替更深的性质 CTL 写不出来（Emerson-Jutla），本构件不证这件事、只标来源。'
            '只诊断不决策：不替使用者定系统该怎么建。')

MAX_STATES = 200          # 状态数上限（诚实边界：超了报 size_limit）
MAX_WORK = 400000         # 护栏：求值工作量上限（迭代步数 × 状态数，防双指数爆掉）——内部兜底，不作判据阈值
MAX_FIXPOINTS_TRACE = 40  # 参数：留痕最多记几条不动点（展示截断，不影响判定）
MAX_OSC_SHOWN = 6         # 参数：非单调时摆出几步振荡过程（展示截断，不影响判定）

_TRUE = ('⊤', 'top', 'True', 'true')
_FALSE = ('⊥', 'bot', 'False', 'false')
_KEYWORDS = ('mu', 'nu', 'μ', 'ν')

# 记号：<> [] <a> [a] ◇ □ μ ν ¬ ∧ ∨ 与 ASCII 写法都认
_TOKEN = re.compile(r'''\s*(->|<>|\[\]|◇|□|<[A-Za-z_][A-Za-z0-9_]*>'''
                    r'''|\[[A-Za-z_][A-Za-z0-9_]*\]'''
                    r'''|[()!¬&|∧∨.]|μ|ν|mu|nu|[A-Za-z_][A-Za-z0-9_]*|⊤|⊥)''')


class _ParseError(ValueError):
    pass


class _NonMonotone(ValueError):
    def __init__(self, msg, osc=None):
        ValueError.__init__(self, msg)
        self.osc = osc or []


class _TooBig(Exception):
    pass


# ══════════════════════════════════════════════════════════════
# 一、公式：解析 → 语法树
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


def _parse(text):
    """μ 演算公式 → 语法树。括号里/公式尾不收多余记号。"""
    if not isinstance(text, str) or not text.strip():
        raise _ParseError('公式不能为空')
    toks = _tokenize(text.strip())
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def is_name(t):
        return (isinstance(t, str) and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t)
                and t not in _KEYWORDS)

    def impl():
        left = disj()
        if peek() == '->':
            take()
            return ('imp', left, impl())
        return left

    def disj():
        left = conj()
        while peek() in ('|', '∨'):
            take()
            left = ('or', left, conj())
        return left

    def conj():
        left = unary()
        while peek() in ('&', '∧'):
            take()
            left = ('and', left, unary())
        return left

    def unary():
        t = peek()
        if t in ('!', '¬'):
            take()
            return ('not', unary())
        if t in _KEYWORDS:
            take()
            kind = 'mu' if t in ('mu', 'μ') else 'nu'
            var = take()
            if not is_name(var):
                raise _ParseError('%s 后面要跟一个变量名（如 %sX.φ），得到 %r'
                                  % (t, 'μ' if kind == 'mu' else 'ν', var))
            if peek() != '.':
                raise _ParseError('%s%s 后面要跟「.」（作用域），得到 %r'
                                  % (t, var, peek()))
            take()
            return (kind, var, unary())
        if t in ('<>', '◇'):
            take()
            return ('dia', None, unary())
        if t in ('[]', '□'):
            take()
            return ('box', None, unary())
        if isinstance(t, str) and t.startswith('<') and t.endswith('>'):
            take()
            return ('dia', t[1:-1], unary())
        if isinstance(t, str) and t.startswith('[') and t.endswith(']'):
            take()
            return ('box', t[1:-1], unary())
        if t == '(':
            take()
            inner = impl()
            if take() != ')':
                raise _ParseError('括号没闭合')
            return inner
        if t in _TRUE:
            take()
            return ('true',)
        if t in _FALSE:
            take()
            return ('false',)
        if is_name(t):
            take()
            return ('atom', t)
        raise _ParseError('看不懂的记号：%r' % (t,))

    ast = impl()
    if pos[0] != len(toks):
        raise _ParseError('公式解析完还有多余记号：%r' % toks[pos[0]:])
    return ast


def _fmt(node):
    """语法树 → 公式文本（翻译结果与留痕都用它，保证可复制复用）。"""
    k = node[0]
    if k == 'atom':
        return node[1]
    if k == 'true':
        return '⊤'
    if k == 'false':
        return '⊥'
    if k == 'not':
        return '!' + _fmt(node[1])
    if k == 'and':
        return '(%s & %s)' % (_fmt(node[1]), _fmt(node[2]))
    if k == 'or':
        return '(%s | %s)' % (_fmt(node[1]), _fmt(node[2]))
    if k == 'imp':
        return '(%s -> %s)' % (_fmt(node[1]), _fmt(node[2]))
    if k == 'dia':
        return ('<%s>' % node[1] if node[1] else '<>') + _fmt(node[2])
    if k == 'box':
        return ('[%s]' % node[1] if node[1] else '[]') + _fmt(node[2])
    if k in ('mu', 'nu'):
        return '%s%s.%s' % ('μ' if k == 'mu' else 'ν', node[1], _fmt(node[2]))
    return '?'


def _vars(node, out=None):
    """公式里出现的所有绑定变量名（含绑定位置）。"""
    out = set() if out is None else out
    k = node[0]
    if k in ('mu', 'nu'):
        out.add(node[1])
        _vars(node[2], out)
    elif k in ('not', 'dia', 'box'):
        _vars(node[1] if k != 'not' else node[1], out)
    elif k in ('and', 'or', 'imp'):
        _vars(node[1], out)
        _vars(node[2], out)
    return out


def _atoms(node, out=None):
    """公式里出现的原子命题名（不含绑定变量）。"""
    out = set() if out is None else out
    k = node[0]
    if k == 'atom':
        out.add(node[1])
    elif k in ('mu', 'nu'):
        _atoms(node[2], out)
    elif k in ('not', 'dia', 'box'):
        _atoms(node[1], out)
    elif k in ('and', 'or', 'imp'):
        _atoms(node[1], out)
        _atoms(node[2], out)
    return out


def _binders(node, out=None, stack=None):
    """(变量名, 是否 μ, 绑定它的那个节点) 列表——用来查重绑与"变量没用到"。"""
    out = [] if out is None else out
    stack = [] if stack is None else stack
    k = node[0]
    if k in ('mu', 'nu'):
        out.append((node[1], k == 'mu', node, tuple(stack)))
        _binders(node[2], out, stack + [node[1]])
    elif k == 'not':
        _binders(node[1], out, stack)
    elif k in ('dia', 'box'):
        _binders(node[2], out, stack)
    elif k in ('and', 'or', 'imp'):
        _binders(node[1], out, stack)
        _binders(node[2], out, stack)
    return out


def _positive(node, var, neg=False):
    """var 在这个子树里是不是**正出现**（偶数层否定之下）。"""
    k = node[0]
    if k == 'atom':
        return node[1] != var or not neg
    if k in ('true', 'false'):
        return True
    if k == 'not':
        return _positive(node[1], var, not neg)
    if k in ('and', 'or', 'imp'):
        return _positive(node[1], var, neg) and _positive(node[2], var, neg)
    if k in ('dia', 'box'):
        return _positive(node[2], var, neg)
    if k in ('mu', 'nu'):
        if node[1] == var:
            return True            # 被内层重新绑定（本构件禁重绑，兜底）
        return _positive(node[2], var, neg)
    return True


# ══════════════════════════════════════════════════════════════
# 二、求值：状态集合语义 + 不动点迭代
# ══════════════════════════════════════════════════════════════

def _succ_index(states, transitions):
    """迁移表 → {动作: {状态: [后继]}}，另给"任一动作的后继"。"""
    by_act = {}
    for pair in transitions:
        if not isinstance(pair, (list, tuple)) or len(pair) not in (2, 3):
            raise _ParseError('迁移要写成 [从, 到] 或 [从, 到, 动作名]，'
                              '得到 %r' % (pair,))
        src, dst = pair[0], pair[1]
        act = '-' if len(pair) == 2 else pair[2]
        if src not in states or dst not in states:
            raise _ParseError('迁移两端都得是已声明的状态：%r' % (pair,))
        if not isinstance(act, str) or not act.strip():
            raise _ParseError('动作名要是非空字符串：%r' % (pair,))
        by_act.setdefault(act, {}).setdefault(src, []).append(dst)
    return by_act


class _Evaluator(object):
    """在给定结构上算公式的状态集合；顺手记不动点留痕与工作量。"""

    def __init__(self, states, by_act, labels):
        self.S = frozenset(states)
        self.by_act = by_act
        self.labels = labels
        self.work = [0]
        self.trace = []
        self.trace_dropped = [0]

    # ── 后继查询
    def succ(self, s, act):
        if act is None:                      # <> / []：任一动作的后继并起来
            out = []
            for m in self.by_act.values():
                out.extend(m.get(s, ()))
            return out
        return self.by_act.get(act, {}).get(s, [])

    def spend(self, n=1):
        self.work[0] += n
        if self.work[0] > MAX_WORK:
            raise _TooBig('求值工作量超过上限 %d（不动点嵌套太深或结构太大）'
                          % MAX_WORK)

    # ── 主求值
    def eval(self, node, env):
        k = node[0]
        self.spend()
        if k == 'atom':
            if node[1] in env:
                return env[node[1]]
            return frozenset(s for s in self.S if node[1] in self.labels.get(s, ()))
        if k == 'true':
            return self.S
        if k == 'false':
            return frozenset()
        if k == 'not':
            return self.S - self.eval(node[1], env)
        if k == 'and':
            return self.eval(node[1], env) & self.eval(node[2], env)
        if k == 'or':
            return self.eval(node[1], env) | self.eval(node[2], env)
        if k == 'imp':
            return (self.S - self.eval(node[1], env)) | self.eval(node[2], env)
        if k == 'dia':
            inner = self.eval(node[2], env)
            return frozenset(s for s in self.S
                             if any(t in inner for t in self.succ(s, node[1])))
        if k == 'box':
            inner = self.eval(node[2], env)
            return frozenset(s for s in self.S
                             if all(t in inner for t in self.succ(s, node[1])))
        if k in ('mu', 'nu'):
            return self._fixpoint(node, env)
        raise _ParseError('看不懂的节点：%r' % (k,))

    # ── 不动点：μ 从空集往上、ν 从全集往下，迭代到收敛
    def _fixpoint(self, node, env):
        kind, var, body = node
        if not _positive(body, var):
            raise _NonMonotone(
                '%s%s 里的 %s 出现在否定之下（非单调）——不动点语义要求'
                '变量**正出现**；非单调时"最小/最大解"根本没有意义'
                '（迭代会来回跳，不会收敛）'
                % ('μ' if kind == 'mu' else 'ν', var, var),
                self._oscillation(var, body, env))
        cur = frozenset() if kind == 'mu' else self.S
        sizes = [len(cur)]
        limit = len(self.S) + 2          # 有限状态最多 |S| 步收敛，多留两步兜底
        for step in range(limit):
            self.spend(len(self.S))
            nxt = self.eval(body, dict(env, **{var: cur}))
            sizes.append(len(nxt))
            if nxt == cur:
                self._record(kind, var, step, sizes)
                return cur
            # μ 只会往上加、ν 只会往下砍（单调性保证），跳出去就是真出了意外
            if kind == 'mu' and not (cur <= nxt):
                raise _TooBig('μ%s 的迭代没有单调上升（不该发生）：%s → %s'
                              % (var, sorted(cur), sorted(nxt)))
            if kind == 'nu' and not (nxt <= cur):
                raise _TooBig('ν%s 的迭代没有单调下降（不该发生）：%s → %s'
                              % (var, sorted(cur), sorted(nxt)))
            cur = nxt
        raise _TooBig('%s%s 迭代 %d 步仍未收敛（不该发生）'
                      % ('μ' if kind == 'mu' else 'ν', var, limit))

    def _record(self, kind, var, steps, sizes):
        if len(self.trace) < MAX_FIXPOINTS_TRACE:
            self.trace.append({'var': var, 'kind': 'μ' if kind == 'mu' else 'ν',
                               'steps': steps, 'sizes': sizes})
        else:
            self.trace_dropped[0] += 1

    def _oscillation(self, var, body, env):
        """非单调时把迭代过程摆出来（凭什么说它不会收敛）。"""
        cur = frozenset()
        seq = [len(cur)]
        for _ in range(MAX_OSC_SHOWN):
            nxt = self.eval(body, dict(env, **{var: cur}))
            seq.append(len(nxt))
            if nxt == cur:
                break
            cur = nxt
        return seq


# ══════════════════════════════════════════════════════════════
# 三、CTL → μ 演算：把八个路径量子翻译成不动点式子
# ══════════════════════════════════════════════════════════════

def _ctl_translate(node, fresh):
    """
    CTL 语法树（来自 classical.model_check 的解析器）→ μ 演算公式文本。

    表（标准翻译，E/A 与 <> / [] 对应）：
        EX φ = <>φ            AX φ = []φ
        EF φ = μX.(φ ∨ <>X)   AF φ = μX.(φ ∨ []X)
        EG φ = νX.(φ ∧ <>X)   AG φ = νX.(φ ∧ []X)
        E[φ U ψ] = μX.(ψ ∨ (φ ∧ <>X))
        A[φ U ψ] = μX.(ψ ∨ (φ ∧ []X))
    """
    k = node[0]
    if k in ('atom',):
        return node[1]
    if k == '!':
        return '!(%s)' % _ctl_translate(node[1], fresh)
    if k in ('&', '|', '->'):
        sym = {'&': '&', '|': '|', '->': '->'}[k]
        return '(%s %s %s)' % (_ctl_translate(node[1], fresh), sym,
                               _ctl_translate(node[2], fresh))
    if k in ('EX', 'AX'):
        return ('<>' if k == 'EX' else '[]') + '(%s)' % _ctl_translate(
            node[1], fresh)
    if k in ('EF', 'AF', 'EG', 'AG'):
        nxt = fresh()
        inner = _ctl_translate(node[1], fresh)
        if k == 'EF':
            return 'μ%s.(%s | <>%s)' % (nxt, inner, nxt)
        if k == 'AF':
            return 'μ%s.(%s | []%s)' % (nxt, inner, nxt)
        if k == 'EG':
            return 'ν%s.(%s & <>%s)' % (nxt, inner, nxt)
        return 'ν%s.(%s & []%s)' % (nxt, inner, nxt)
    if k in ('E[U]', 'A[U]'):
        nxt = fresh()
        p = _ctl_translate(node[1], fresh)
        q = _ctl_translate(node[2], fresh)
        modal = '<>' if k == 'E[U]' else '[]'
        return 'μ%s.(%s | (%s & %s%s))' % (nxt, q, p, modal, nxt)
    raise _ParseError('CTL 语法树里看不懂的节点：%r' % (k,))


# ══════════════════════════════════════════════════════════════
# 四、对外推理
# ══════════════════════════════════════════════════════════════

def _out(verdict, boundary=BOUNDARY, **kw):
    out = {'verdict': verdict, 'holds_in': [], 'fails_in': [], 'truth': None,
           'translation': None, 'fixpoints': [], 'compare': None,
           'boundary': boundary}
    out.update(kw)
    return out


def _structure(inputs):
    """把输入里的结构取出来，出问题就抛 _ParseError 让上层诚实报。"""
    states = inputs.get('states')
    if not isinstance(states, list) or not states:
        raise _ParseError('需要 states（状态名列表）')
    if len(set(states)) != len(states):
        raise _ParseError('状态名不能重复：%r' % (states,))
    if len(states) > MAX_STATES:
        raise _TooBig('状态数 %d 超过上限 %d' % (len(states), MAX_STATES))
    trans = inputs.get('transitions')
    if trans is None:
        trans = []
    if not isinstance(trans, list):
        raise _ParseError('transitions 必须是列表（[从,到] 或 [从,到,动作]）')
    by_act = _succ_index(set(states), trans)
    labels = inputs.get('labels') or {}
    if not isinstance(labels, dict):
        raise _ParseError('labels 必须是 {状态: [原子命题]} 的 dict')
    for s, ps in labels.items():
        if s not in set(states):
            raise _ParseError('labels 里有未声明的状态：%r' % (s,))
        if not isinstance(ps, list):
            raise _ParseError('labels[%r] 要是命题名列表' % (s,))
    return list(states), by_act, labels


def run(inputs):
    """
    做什么：μ 演算求值 / 检查 / CTL 翻译求值 / 两式对照。

    返回 dict（见模块 docstring）。"""
    if not isinstance(inputs, dict):
        return _out('input_pending', 'inputs 必须是 dict')
    mode = inputs.get('mode') or 'evaluate'
    if mode not in ('evaluate', 'check', 'ctl', 'compare'):
        return _out('input_pending',
                    'mode 应为 evaluate/check/ctl/compare，得到 %r' % (mode,))

    try:
        states, by_act, labels = _structure(inputs)
    except _TooBig as e:
        return _out('size_limit', '%s——%s，不硬跑' % (e, BOUNDARY))
    except _ParseError as e:
        return _out('input_pending', str(e))
    except ValueError as e:
        return _out('parse_error', str(e))

    # ── ctl：先把 CTL 公式翻成 μ 演算式子，再照常求值（翻译结果一并交出）
    translation = None
    if mode == 'ctl':
        ctl_text = inputs.get('ctl')
        if not isinstance(ctl_text, str) or not ctl_text.strip():
            return _out('input_pending',
                        'ctl 模式需要 ctl（CTL 公式，如 AG !(c1 & c2)）——诚实拦截')
        try:
            from engine.classical.model_check import _parse as _ctl_parse
            from engine.classical.model_check import _tokenize as _ctl_tokens
            ctl_ast = _ctl_parse(_ctl_tokens(ctl_text.strip()))
        except ImportError:
            return _out('internal_error', '拿不到 CTL 构件的解析器（model_check）')
        except ValueError as e:
            return _out('parse_error', 'CTL 公式解析不了：%s' % e)
        counter = [0]

        def fresh():
            counter[0] += 1
            return 'X%d' % counter[0]

        try:
            translation = _ctl_translate(ctl_ast, fresh)
            ast = _parse(translation)
        except _ParseError as e:
            return _out('internal_error', 'CTL 翻译出了岔子：%s' % e)
        text = translation
    else:
        text = inputs.get('formula') if mode != 'compare' else None
        if mode == 'compare':
            c1, c2 = inputs.get('c1'), inputs.get('c2')
            if not isinstance(c1, str) or not isinstance(c2, str):
                return _out('input_pending', 'compare 需要 c1 与 c2 两条公式')
            try:
                ast1, ast2 = _parse(c1), _parse(c2)
            except _ParseError as e:
                return _out('parse_error', str(e))
            return _compare(states, by_act, labels, ast1, ast2, c1, c2)
        if not isinstance(text, str) or not text.strip():
            return _out('input_pending',
                        '%s 需要 formula（μ 演算公式，如 νX.(P & <>X)）——诚实拦截'
                        % mode)
        try:
            ast = _parse(text)
        except _ParseError as e:
            return _out('parse_error', str(e))

    # 变量体检：不许重绑、必须真的用在自己的作用域里
    bad = _check_binders(ast)
    if bad:
        return _out('parse_error', bad)

    ev = _Evaluator(states, by_act, labels)
    try:
        truth = ev.eval(ast, {})
    except _NonMonotone as e:
        note = ('%s。迭代过程（大小）：%s——所以本构件不硬算，报 non_monotone。%s'
                % (e, ' → '.join(str(x) for x in e.osc), BOUNDARY))
        return _out('non_monotone', boundary=note)
    except _TooBig as e:
        return _out('size_limit', '%s——%s，不硬跑' % (e, BOUNDARY))
    except _ParseError as e:
        return _out('parse_error', str(e))
    except Exception as e:  # noqa: BLE001——真出意外如实报
        return _out('internal_error', '求值出意外（%s: %s）' % (type(e).__name__, e))

    truthd = {s: (s in truth) for s in states}
    if mode == 'ctl':
        note = ('CTL 公式「%s」翻成 μ 演算式子：**%s**（翻译表：EX=<>、AX=[]、'
                'EF=μX.(φ∨<>X)、AF=μX.(φ∨[]X)、EG=νX.(φ∧<>X)、AG=νX.(φ∧[]X)、'
                'EU/AU 同形换模态）。下面是这条 μ 式子在这个系统上的求值结果。%s'
                % (inputs.get('ctl'), translation, BOUNDARY))
        return _out('evaluated', holds_in=[s for s in states if truthd[s]],
                    fails_in=[s for s in states if not truthd[s]], truth=truthd,
                    translation=translation, fixpoints=ev.trace,
                    boundary=note)

    if mode == 'check':
        init = inputs.get('init') or states
        if not isinstance(init, list) or any(s not in set(states) for s in init):
            return _out('input_pending', 'init 必须是已声明状态的子集')
        holds = [s for s in init if truthd[s]]
        fails = [s for s in init if not truthd[s]]
        return _out('holds' if not fails else 'fails', holds_in=holds,
                    fails_in=fails, truth=truthd, fixpoints=ev.trace,
                    boundary='在给定系统上：式子「%s」对 %d 个待查状态里 %d 个成立、'
                             '%d 个不成立。这是**相对这个结构**的结论，不是逻辑'
                             '普遍有效。%s' % (text, len(init), len(holds),
                                          len(fails), BOUNDARY))
    return _out('evaluated', holds_in=[s for s in states if truthd[s]],
                fails_in=[s for s in states if not truthd[s]], truth=truthd,
                fixpoints=ev.trace)


def _check_binders(ast):
    """变量体检：重绑、未出现在自己作用域里——都会让式子名不副实。"""
    bound = _binders(ast)
    seen = {}
    for var, _is_mu, node, outer in bound:
        if var in outer:
            return ('变量 %s 被重复绑定（内层 %s 遮住了外层）——本构件不做遮蔽，'
                    '换个名字' % (var, _fmt(node)))
        if var in seen:
            return '变量 %s 绑了不止一次' % var
        seen[var] = True
        if not _uses(node[2], var):
            return ('%s 在它自己的作用域里一次都没出现（%s）——空绑定会让式子'
                    '看起来有不动点其实没有' % (var, _fmt(node)))
    return None


def _uses(node, var):
    k = node[0]
    if k == 'atom':
        return node[1] == var
    if k in ('true', 'false'):
        return False
    if k == 'not':
        return _uses(node[1], var)
    if k in ('and', 'or', 'imp'):
        return _uses(node[1], var) or _uses(node[2], var)
    if k in ('dia', 'box'):
        return _uses(node[2], var)
    if k in ('mu', 'nu'):
        return node[1] != var and _uses(node[2], var)
    return False


def _compare(states, by_act, labels, ast1, ast2, c1, c2):
    """两条式子在这个系统上是不是同一个状态集合（差别在哪，逐个点出来）。"""
    ev = _Evaluator(states, by_act, labels)
    try:
        t1 = ev.eval(ast1, {})
        t2 = ev.eval(ast2, {})
    except _NonMonotone as e:
        return _out('non_monotone', boundary='%s。%s' % (e, BOUNDARY))
    except _TooBig as e:
        return _out('size_limit', '%s——%s，不硬跑' % (e, BOUNDARY))
    only1 = sorted(set(states) & (t1 - t2))
    only2 = sorted(set(states) & (t2 - t1))
    same = not only1 and not only2
    return _out('same' if same else 'different',
                holds_in=sorted(t1), fails_in=sorted(set(states) - t1),
                truth={s: (s in t1) for s in states}, fixpoints=ev.trace,
                compare={'only_in_c1': only1, 'only_in_c2': only2},
                boundary=('两条式子在这个系统上**一样**（同一个状态集合）；'
                          '注意这只是**在这个结构上**一样，不等于逻辑等价。%s'
                          % BOUNDARY) if same else
                         ('两条式子在这个系统上**不一样**：只在「%s」里成立的状态 '
                          '%s；只在「%s」里成立的状态 %s。%s'
                          % (c1, only1 or '（无）', c2, only2 or '（无）',
                             BOUNDARY)))


# ============================================================
# 自测
# ============================================================
def _selftest():
    print('=' * 70)
    print('模态 μ 演算构件 · 自测')
    print('=' * 70)

    # 一条 5 个状态的链 s0→s1→s2→s3→s4，只有 s4 带原子 p
    CHAIN = {'states': ['s%d' % i for i in range(5)],
             'transitions': [['s0', 's1'], ['s1', 's2'], ['s2', 's3'],
                             ['s3', 's4']],
             'labels': {'s4': ['p']}}

    r = run(dict(CHAIN, mode='evaluate', formula='μX.(p | <>X)'))
    assert r['verdict'] == 'evaluated', r
    assert r['holds_in'] == ['s0', 's1', 's2', 's3', 's4'], r
    print('✅ EF p（μX.(p ∨ <>X)）在链上处处成立——最小不动点从空集往上加')

    r = run(dict(CHAIN, mode='evaluate', formula='μX.(p | X)'))
    assert r['holds_in'] == ['s4'], r
    r = run(dict(CHAIN, mode='evaluate', formula='νX.(p | X)'))
    assert r['holds_in'] == ['s0', 's1', 's2', 's3', 's4'], r
    print('✅ μ 与 ν 差在哪：μX.(p ∨ X) 只有 s4；νX.(p ∨ X) 是全部——'
          '同一个式子，两个不动点（"最少要"与"最大容得下"）')

    r = run(dict(CHAIN, mode='evaluate', formula='μX.p'))
    assert r['verdict'] == 'parse_error', r
    print('✅ 空绑定（μX.p）诚实拦下：绑了 X 却在作用域里没用它——'
          '多半是变量名写错了')

    r = run(dict(CHAIN, mode='evaluate', formula='νX.(p & <>X)'))
    assert r['holds_in'] == [], r
    print('✅ EG p（νX.(p ∧ <>X)）在只到 s4 就断的链上没有状态成立')

    CY = {'states': ['a', 'b', 'c'], 'transitions': [['a', 'b'], ['b', 'a'],
                                                     ['c', 'c']],
          'labels': {'a': ['p'], 'b': ['p']}}
    r = run(dict(CY, mode='evaluate', formula='νX.(p & <>X)'))
    assert r['holds_in'] == ['a', 'b'], r
    print('✅ EG p 在 a↔b 环上成立（c 上没有 p，进不来）')

    # 留痕：链上 EF 从最远的 s4 往回要走 5 轮（距离 4，加上收敛那一轮）
    r = run(dict(CHAIN, mode='evaluate', formula='μX.(p | <>X)'))
    fp = r['fixpoints'][0]
    assert fp['kind'] == 'μ' and fp['steps'] == 5, fp
    print('✅ 不动点留痕：链上 μX.(p ∨ <>X) 迭代 %d 轮收敛（每轮多大 %s）'
          % (fp['steps'], fp['sizes']))

    # 非单调：μX.!X 迭代来回跳
    r = run(dict(CHAIN, mode='evaluate', formula='μX.!X'))
    assert r['verdict'] == 'non_monotone', r
    assert '迭代过程' in r['boundary'], r['boundary']
    print('✅ 非单调（μX.!X）诚实拦下，并摆出振荡过程：%s'
          % r['boundary'][:46])

    # CTL 翻译 + 与 CTL 构件对拍
    r = run(dict(CHAIN, mode='ctl', ctl='EF p'))
    assert r['translation'] == 'μX1.(p | <>X1)', r['translation']
    assert r['holds_in'] == ['s0', 's1', 's2', 's3', 's4'], r
    from engine.classical.model_check import run as _ctl_run
    ref = _ctl_run({'states': CHAIN['states'],
                    'transitions': CHAIN['transitions'],
                    'labels': CHAIN['labels'], 'formula': 'EF p'})
    assert ref['verdict'] == 'holds' and sorted(ref['holds_in']) == \
        sorted(r['holds_in']), (ref, r)
    print('✅ CTL 翻译：EF p → %s，结论与 CTL 构件一致' % r['translation'])

    # 多动作：<a> / [a] 只看该动作的边
    MA = {'states': ['x', 'y'], 'transitions': [['x', 'y', 'a'], ['y', 'y', 'b']],
          'labels': {'y': ['q']}}
    r = run(dict(MA, mode='evaluate', formula='<a>q'))
    assert r['holds_in'] == ['x'], r
    r = run(dict(MA, mode='evaluate', formula='<b>q'))
    assert r['holds_in'] == ['y'], r
    r = run(dict(MA, mode='evaluate', formula='[b]q'))
    assert r['holds_in'] == ['x', 'y'], r
    print('✅ 多动作：<a>q 只在 x、<b>q 只在 y；[b]q 在 x 也成立'
          '（x 没有 b 后继——全称算子空真，与 CTL 构件的死锁约定一致）')

    # 边界：坏公式 / 未绑定变量 / 状态没声明
    assert run(dict(CHAIN, mode='evaluate', formula='μX'))['verdict'] \
        == 'parse_error'
    assert run(dict(CHAIN, mode='evaluate', formula='<>'))['verdict'] \
        == 'parse_error'
    assert run({'mode': 'evaluate', 'formula': 'p'})['verdict'] \
        == 'input_pending'
    assert run(dict(CHAIN, mode='evaluate',
                    formula='p q'))['verdict'] == 'parse_error'
    print('✅ 边界：写坏的公式/缺结构 → parse_error / input_pending（不猜）')

    print('=' * 70)
    print('模态 μ 演算构件自测：全部通过 ✅')
    print('=' * 70)


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass
    _selftest()
