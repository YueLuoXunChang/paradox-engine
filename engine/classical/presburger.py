# -*- coding: utf-8 -*-
"""
presburger.py — Presburger 算术判定（整数 + 加法 + 常数乘）· 第 1 层经典构件
================================================================
概念来源：Presburger 1929——算术里**只留加法和常数乘**，判定性就保住了；
一旦允许变量乘变量（皮亚诺算术 PA）立刻掉进不可判（见可判定片段地图）。
本构件是**借鉴实现**（落落三问：借什么=Presburger 可判定这件事与量词消去的做法；
为什么=引擎的分层主张要"能算的算清"，而此前这类算术只能说"可判但引擎没做"，
地图上那条一直是 engine_available=False——挂着不算数；怎么记账=来源标在 docstring
与地图条目，归借鉴区）。

本构件做什么（一句话）：
    判定一个 Presburger 公式在整数上是不是**恒真**（默认），或**有没有解**：
    解析 → 化成否定范式 → 一个量词一个量词地消掉 → 得到不带量词的等价式 → 直接求值。
    能答的就是这类问题：∀x∃y(y+y=x ∨ y+y+1=x)（真——每个整数非偶即奇）、
    ∃x(2x=3)（假——左边永远是偶数）、∃x(3|x ∧ 3|x+1)（假——同余条件打架）。

语法（够用且边界清楚）：
    项    := 整数 | 变量 | 项 + 项 | 项 - 项 | 常数 * 项 | ( 项 )（"2x" 这种紧挨着也认）
    原子  := 项 (= ≠ < ≤ > ≥) 项 ｜ 常数 | 项（整除，如 3 | x + 1）
    公式  := 原子 | ¬公式 | 公式 ∧|∨|→|↔ 公式 | ∀变量 公式 | ∃变量 公式 | ( 公式 )
    量词也认 forall / exists 写法；变量名可多字母。

怎么算的（白话，Cooper 消元的路子）：
    消 ∃x 时先把这一层公式拆成若干"与支"（每支是若干原子的合取），再逐支处理——
    看这一支给 x 下了什么界：
      · 没有下界（只有 x ≤ … 这种上界）：x 往负方向走多远都行，上界自然满足，
        剩下要操心的只有整除条件能不能**同时**成立；于是检查一个周期内有没有
        合适的 x 就够（有 → 这一支成立，其实是"足够负的地方有解"）；
      · 有下界：取最小的那个解。把 x 减一个周期，若还成立就与"最小"矛盾，
        所以它失败一定输在下界上——于是这个最小解必然落在"某个下界 + 一个周期以内"，
        把这段区间里的候选值逐个代回去，代完 x 就没了。
    每消一层都得到同值的无量词公式；全部消完后公式里只剩常数，求值即结论。

诚实边界：
    - 只在**整数**上判（自然数版 = 给每个量词变量再加一条 x ≥ 0，这种写法本构件认）；
    - **没有乘法**：变量乘变量、变量当指数一律 parse_error（那是 PA，不可判定，别混进来）；
    - 规模有上限（消元系数 / 周期 / 分支数）：超了报 size_limit——**不假装能算**；
    - 最坏复杂度超指数（Fischer-Rabin 1974 的下界），本构件只适合小式子，不是快速判定器；
    - 只诊断不决策：给的是"这条式子在整数这套语义下真/假"，不替使用者判断现实对不对。
"""

PORTS = {
    'in': {'formula': 'str', 'mode': 'str?'},
    'out': {'verdict': 'str', 'explanation': 'str', 'equivalent': 'str?',
            'counterexample': 'dict?', 'witness': 'dict?',
            'free_variables': 'list', 'quantifiers': 'int', 'boundary': 'str'},
}

import math
import re
import sys

BOUNDARY = ('Presburger 算术（整数 + 加法 + 常数乘）判定：解析 → 否定范式 → 量词消去'
            '（Cooper 式测试集 + 足够负情形）→ 无量词等价式求值。'
            '在规模上限内给 true/false 结论；超上限报 size_limit（不假装能算）。'
            '没有乘法——变量乘变量属 PA，不可判定，本构件直接 parse_error 划出去。'
            '最坏复杂度超指数，只适合小式子。只诊断不决策。')

# 消元过程里的规模上限（超了就诚实报 size_limit，不当成结论）
MAX_COEF = 32        # 同一个变量的系数统一后的上限（lcm 出来的值）
MAX_MOD = 200        # 整除模数上限
MAX_B = 256          # 候选周期（lcm(a, 各模数)）上限
MAX_DISJ = 2048      # DNF 与消元中间结果的分支数上限
MAX_WORK = 60000     # 整次判定的候选代入总次数上限（只卡分支数不够——会卡在这儿）
MAX_QE = 24          # 量词消去步数上限
MAX_INPUT = 4000     # 公式串长度上限（防手滑粘进来一大段）

# 自由变量反例/见证的小范围搜索（只用于"给个例子看"，不是判定依据）
SEARCH_VARS_MAX = 3
SEARCH_RANGE = (-3, 4)

_C = ''              # 线性式里常数项的键


class _TooBig(Exception):
    """超出本构件的规模上限——诚实报 size_limit，不硬算。"""


def _spend(budget):
    """记一次「候选代入」的开销；整次判定有总上限，超了就老实说不算。
    只卡分支数不够——分支内的循环照样能把时间吃光（这里踩过）。"""
    budget[1] -= 1
    if budget[1] < 0:
        raise _TooBig('消元工作量超过上限 %d 次候选代入' % MAX_WORK)


# ══════════════════════════════════════════════════════════════
# 一、线性式：{变量: 系数, '': 常数}
#     Presburger 只允许常数乘，所以式子永远保持线性——这正是它可判的原因。
# ══════════════════════════════════════════════════════════════

def _trim(lin):
    """去掉系数为 0 的项；常数键始终保留（便于判常数式）。"""
    out = {k: v for k, v in lin.items() if v}
    out.setdefault(_C, 0)
    return out


def _lin_const(v):
    return {_C: int(v)}


def _lin_var(name):
    return {name: 1, _C: 0}


def _lin_add(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return _trim(out)


def _lin_neg(a):
    return _trim({k: -v for k, v in a.items()})


def _lin_sub(a, b):
    return _lin_add(a, _lin_neg(b))


def _lin_scale(a, k):
    return _trim({kk: v * k for kk, v in a.items()})


def _lin_div(a, g):
    """整除以公因子 g（调用前保证 g 整除所有系数）。"""
    return _trim({kk: v // g for kk, v in a.items()})


def _is_const(a):
    return all(k == _C for k in a)


def _const_val(a):
    return a.get(_C, 0)


def _lin_without(a, var):
    out = {k: v for k, v in a.items() if k != var}
    out.setdefault(_C, 0)
    return out


def _lin_common(a):
    """所有系数（含常数）的最大公因数，用于约简。"""
    g = 0
    for v in a.values():
        g = math.gcd(g, abs(v))
    return g


def _lin_vars(a):
    return {k for k in a if k != _C}


# 两张翻转表别看错（踩过）：取反是「≤ 变 >」，乘负数是「≤ 变 ≥」——弄混会差一个端点
_FLIP = {'=': '=', '≠': '≠', '<': '>', '≤': '≥', '>': '<', '≥': '≤'}   # 乘负数
_NEG = {'=': '≠', '≠': '=', '<': '≥', '≤': '>', '>': '≤', '≥': '<'}    # 逻辑取反


# ══════════════════════════════════════════════════════════════
# 二、原子与公式的构造（顺手化简，免得式子越滚越大）
# ══════════════════════════════════════════════════════════════

def _simp(at, reduce=True):
    """化简原子：公因子约掉、常数式直接算真假、模数 1 的整除恒真。

    reduce=False 时不约公因子——消元把 x 的系数统一成 a 之后不能再约，
    否则系数又被约回去，代入候选值时就会拿错倍数（这里踩过）。
    """
    kind = at[0]
    if kind == 'rel':
        lin, op = at[1], at[2]
        if reduce:
            g = _lin_common(lin)
            if g > 1:
                lin = _lin_div(lin, g)
        if _is_const(lin):
            cv = _const_val(lin)
            ok = {'=': cv == 0, '≠': cv != 0, '<': cv < 0,
                  '≤': cv <= 0, '>': cv > 0, '≥': cv >= 0}[op]
            return ('true',) if ok else ('false',)
        return ('rel', lin, op)
    if kind == 'div':
        m, lin = at[1], at[2]
        if reduce:
            g = 0
            for v in lin.values():
                g = math.gcd(g, abs(v))
            g = math.gcd(g, m)
            if g > 1:
                m //= g
                lin = _lin_div(lin, g)
        if m <= 0:
            raise ValueError('整除号左边要是正整数')
        if m == 1:
            return ('true',)
        if m > MAX_MOD:
            raise _TooBig('整除模数 %d 超过上限 %d' % (m, MAX_MOD))
        if _is_const(lin):
            return ('true',) if _const_val(lin) % m == 0 else ('false',)
        return ('div', m, lin)
    return at


def _mk_and(parts):
    flat = []
    for p in parts:
        if p[0] == 'false':
            return ('false',)
        if p[0] == 'true':
            continue
        if p[0] == 'and':
            flat.extend(p[1])
        else:
            flat.append(p)
        if len(flat) > MAX_DISJ:
            raise _TooBig('合取的项数超过上限 %d' % MAX_DISJ)
    if not flat:
        return ('true',)
    if len(flat) == 1:
        return flat[0]
    return ('and', flat)


def _mk_or(parts):
    flat = []
    for p in parts:
        if p[0] == 'true':
            return ('true',)
        if p[0] == 'false':
            continue
        if p[0] == 'or':
            flat.extend(p[1])
        else:
            flat.append(p)
        # 展平之后才算总账：只卡「传进来的支数」是拦不住的——
        # 每个支自己可能是一大串或，展平出来是支数×支数（踩过：卡死不返回）
        if len(flat) > MAX_DISJ:
            raise _TooBig('析取的项数超过上限 %d' % MAX_DISJ)
    if not flat:
        return ('false',)
    if len(flat) == 1:
        return flat[0]
    return ('or', flat)


# ══════════════════════════════════════════════════════════════
# 三、解析（递归下降；中文记号与 ASCII 写法都认）
# ══════════════════════════════════════════════════════════════

_TOKEN = re.compile(
    r'\s*(<=|>=|!=|≤|≥|≠|↔|→|&&|\|\||[<>=|&!~¬∧∨∀∃()+\-*]'
    r'|[A-Za-z_][A-Za-z0-9_]*|\d+)')
_REL_TOK = {'=': '=', '!=': '≠', '≠': '≠', '<': '<', '<=': '≤', '≤': '≤',
            '>': '>', '>=': '≥', '≥': '≥'}
_AND_TOK = ('∧', '&&', '&')
_OR_TOK = ('∨', '||')
_NOT_TOK = ('¬', '!', '~')
_QUANT_TOK = ('∀', '∃')
_KEYWORD_QUANT = {'forall': '∀', 'exists': '∃', 'all': '∀', 'any': '∃'}
_VAR_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            raise ValueError('无法识别的字符：%r' % s[i:i + 8])
        out.append(m.group(1))
        i = m.end()
    return out


def _parse(tokens):
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def is_var(t):
        return t is not None and bool(_VAR_RE.match(t)) \
            and t not in _KEYWORD_QUANT

    # ── 公式层
    def iff():
        left = impl()
        while peek() == '↔':
            take()
            left = ('iff', left, impl())
        return left

    def impl():
        left = disj()
        if peek() == '→':
            take()
            return ('imp', left, impl())        # 右结合
        return left

    def disj():
        left = conj()
        while peek() in _OR_TOK:
            take()
            left = ('or', left, conj())
        return left

    def conj():
        left = unary()
        while peek() in _AND_TOK:
            take()
            left = ('and', left, unary())
        return left

    def unary():
        t = peek()
        if t in _NOT_TOK:
            take()
            return ('not', unary())
        if t in _QUANT_TOK or t in _KEYWORD_QUANT:
            q = take()
            if q in _KEYWORD_QUANT:
                q = _KEYWORD_QUANT[q]
            name = take()
            if not is_var(name):
                raise ValueError('量词后面要跟一个变量名，得到 %r' % (name,))
            return ('forall' if q == '∀' else 'exists', name, unary())
        if t == '(':
            take()
            inner = iff()
            if take() != ')':
                raise ValueError('括号没闭合')
            return inner
        return atom()

    def atom():
        left = arith()
        t = peek()
        if t in _REL_TOK:
            take()
            right = arith()
            return ('rel', left, right, _REL_TOK[t])
        if t == '|':
            take()
            right = arith()
            if not _is_const(left):
                raise ValueError('整除号左边要写常数（如 3 | x + 1）——'
                                 '变量当除数不属于 Presburger')
            m = _const_val(left)
            if m < 1:
                raise ValueError('整除号左边的常数要 ≥ 1，得到 %d' % m)
            return ('div', m, right)
        raise ValueError('这里要是一个关系式（= ≠ < ≤ > ≥ 或整除 |），'
                         '得到 %r' % (t,))

    # ── 项层（线性式）
    def arith():
        sign = 1
        if peek() in ('+', '-'):
            sign = -1 if take() == '-' else 1
        left = term()
        if sign < 0:
            left = _lin_neg(left)
        while peek() in ('+', '-'):
            op = take()
            right = term()
            left = _lin_add(left, right) if op == '+' else _lin_sub(left, right)
        return left

    def term():
        left = factor()
        while True:
            t = peek()
            if t == '*':
                take()
                left = _mul(left, factor())
            elif is_var(t) or t == '(':
                left = _mul(left, factor())      # 隐式乘法：2x、2(x+1) 这类写法
            else:
                return left

    def factor():
        t = take()
        if t is None:
            raise ValueError('式子在这里断了（少了一项）')
        if t == '(':
            inner = arith()
            if take() != ')':
                raise ValueError('括号没闭合')
            return inner
        if t == '-':
            return _lin_neg(factor())
        if re.match(r'^\d+$', t):
            return _lin_const(int(t))
        if _VAR_RE.match(t) and t not in _KEYWORD_QUANT:
            return _lin_var(t)
        raise ValueError('看不懂的记号：%r' % t)

    def _mul(a, b):
        if _is_const(a):
            return _lin_scale(b, _const_val(a))
        if _is_const(b):
            return _lin_scale(a, _const_val(b))
        raise ValueError('Presburger 没有变量乘变量（那是 PA，不可判定）——'
                         '这里出现了两个非常数项相乘')

    ast = iff()
    if pos[0] != len(tokens):
        raise ValueError('公式解析完还有多余记号：%r' % tokens[pos[0]:])
    return _build(ast)


def _build(node):
    """把解析树翻成内部公式（原子统一成『线性式 ⋈ 0』与整除）。"""
    k = node[0]
    if k == 'rel':
        return _simp(('rel', _lin_sub(node[1], node[2]), node[3]))
    if k == 'div':
        return _simp(('div', node[1], node[2]))
    if k == 'not':
        return ('not', _build(node[1]))
    if k in ('and', 'or', 'imp', 'iff'):
        a, b = _build(node[1]), _build(node[2])
        if k == 'and':
            return _mk_and([a, b])
        if k == 'or':
            return _mk_or([a, b])
        if k == 'imp':                       # A → B 等价于 ¬A ∨ B
            return _mk_or([('not', a), b])
        return _mk_or([_mk_and([a, b]), _mk_and([('not', a), ('not', b)])])
    if k in ('forall', 'exists'):
        return (k, node[1], _build(node[2]))
    raise ValueError('解析树里有不认识的节点：%r' % (k,))


# ══════════════════════════════════════════════════════════════
# 四、否定范式（把 ¬ 压到原子上；¬整除 在这里拆开）
# ══════════════════════════════════════════════════════════════

def _nnf(f, neg=False):
    k = f[0]
    if k == 'not':
        return _nnf(f[1], not neg)
    if k == 'true':
        return ('false',) if neg else f
    if k == 'false':
        return ('true',) if neg else f
    if k == 'rel':
        return _simp(('rel', f[1], _NEG[f[2]] if neg else f[2]))
    if k == 'div':
        if not neg:
            return _simp(f)
        # m ∤ t  ⟺  t 落在 1..m-1 这些余数类里（每类写成一次整除）
        m, lin = f[1], f[2]
        if m == 1:
            return ('false',)
        if m - 1 > MAX_DISJ:
            raise _TooBig('¬整除要拆成 %d 支，超过上限 %d' % (m - 1, MAX_DISJ))
        return _mk_or([_simp(('div', m, _lin_sub(lin, _lin_const(r))))
                       for r in range(1, m)])
    if k in ('and', 'or'):
        keep = (k == 'and') != neg           # 德摩根：两边都要翻
        subs = [_nnf(s, neg) for s in f[1]]
        return _mk_and(subs) if keep else _mk_or(subs)
    if k in ('forall', 'exists'):
        if k == 'forall':
            blk = 'exists' if neg else 'forall'
        else:
            blk = 'forall' if neg else 'exists'
        return (blk, f[1], _nnf(f[2], neg))
    raise ValueError('否定范式遇到不认识的节点：%r' % (k,))


def _count_quant(f):
    k = f[0]
    if k in ('forall', 'exists'):
        return 1 + _count_quant(f[2])
    if k in ('and', 'or'):
        return sum(_count_quant(s) for s in f[1])
    if k == 'not':
        return _count_quant(f[1])
    return 0


def _free_vars(f, bound=None):
    bound = set() if bound is None else bound
    k = f[0]
    if k == 'rel':
        return _lin_vars(f[1]) - bound
    if k == 'div':
        return _lin_vars(f[2]) - bound
    if k == 'not':
        return _free_vars(f[1], bound)
    if k in ('and', 'or'):
        out = set()
        for s in f[1]:
            out |= _free_vars(s, bound)
        return out
    if k in ('forall', 'exists'):
        return _free_vars(f[2], bound | {f[1]})
    return set()


# ══════════════════════════════════════════════════════════════
# 五、DNF 与量词消去
# ══════════════════════════════════════════════════════════════

def _to_dnf(f, budget):
    """化成析取范式：返回「若干与支」，每支是原子列表。空列表 = 假。

    上限**边生成边查**：只在整个笛卡尔积拼完后再查，中间那一下照样能把时间吃光
    （踩过——一个随机式子直接卡住不返回）。
    """
    k = f[0]
    if k == 'true':
        return [[]]
    if k == 'false':
        return []
    if k in ('rel', 'div'):
        return [[f]]
    if k == 'and':
        out = [[]]
        for s in f[1]:
            sub = _to_dnf(s, budget)
            if not sub:
                return []
            nxt = []
            for a in out:
                for b in sub:
                    _spend(budget)
                    nxt.append(a + b)
                    if len(nxt) > MAX_DISJ:
                        raise _TooBig('合取展开到 %d 支，超过上限 %d'
                                      % (len(nxt), MAX_DISJ))
            out = nxt
        return out
    if k == 'or':
        out = []
        for s in f[1]:
            for one in _to_dnf(s, budget):
                _spend(budget)
                out.append(one)
                if len(out) > MAX_DISJ:
                    raise _TooBig('析取展开到 %d 支，超过上限 %d'
                                  % (len(out), MAX_DISJ))
        return out
    raise ValueError('DNF 遇到不认识的节点：%r' % (k,))


def _expand_conj(atoms):
    """把等号/不等号拆成界：a = 0 拆成 a ≤ 0 且 a ≥ 0；a ≠ 0 拆成 a < 0 或 a > 0。
    消元只看「上界 / 下界」，所以这一步得先做——不然等式的解会被当成"没有下界"。"""
    out = [[]]
    for at in atoms:
        if at[0] == 'rel' and at[2] == '=':
            for c in out:
                c.append(_simp(('rel', at[1], '≤')))
                c.append(_simp(('rel', at[1], '≥')))
        elif at[0] == 'rel' and at[2] == '≠':
            nxt = []
            for c in out:
                nxt.append(c + [_simp(('rel', at[1], '<'))])
                nxt.append(c + [_simp(('rel', at[1], '>'))])
            if len(nxt) > MAX_DISJ:
                raise _TooBig('不等号展开到 %d 支，超过上限 %d'
                              % (len(nxt), MAX_DISJ))
            out = nxt
        else:
            for c in out:
                c.append(at)
    return out


def _elim(var, qf, budget):
    """消掉 ∃var：对每个与支各消一次，结果取或。"""
    qf = _nnf(qf)
    out = []
    for conj in _to_dnf(qf, budget):
        for sub in _expand_conj(conj):
            out.append(_elim_conj(var, sub, budget))
            if len(out) > MAX_DISJ:
                raise _TooBig('消元中间结果到 %d 支，超过上限 %d'
                              % (len(out), MAX_DISJ))
    return _mk_or(out)


def _elim_conj(var, atoms, budget):
    """消掉一个与支里的 ∃var（Cooper 式：看下界，取最小解所在的窗口）。"""
    atoms = [_simp(a) for a in atoms]
    if any(a[0] == 'false' for a in atoms):
        return ('false',)
    atoms = [a for a in atoms if a[0] != 'true']
    xa, rest = [], []
    for at in atoms:
        lin = at[1] if at[0] == 'rel' else at[2]
        (xa if lin.get(var) else rest).append(at)
    if not xa:
        return _mk_and(rest)                  # x 压根不出现：这支与 x 无关

    # ① 把 x 的系数统一成同一个常数 a（消元要按同一个步长看 x）
    a = 1
    for at in xa:
        lin = at[1] if at[0] == 'rel' else at[2]
        c = abs(lin[var])
        a = a * c // math.gcd(a, c)
    if a > MAX_COEF:
        raise _TooBig('x 的系数统一后到 %d，超过上限 %d' % (a, MAX_COEF))

    norm = []
    for at in xa:
        one = _norm_x(at, var, a)
        if one[0] == 'false':
            return ('false',)
        if one[0] != 'true':
            norm.append(one)
    xa = norm
    if not xa:
        return _mk_and(rest)

    # ② 周期 B：候选值要同时是 a 与各整除模数的倍数
    B = a
    for at in xa:
        if at[0] == 'div':
            B = B * at[1] // math.gcd(B, at[1])
    if B > MAX_B:
        raise _TooBig('候选周期到 %d，超过上限 %d' % (B, MAX_B))

    lbs = [at for at in xa if at[0] == 'rel' and at[2] in ('>', '≥')]
    if not lbs:
        return _elim_inf(var, a, B, xa, rest, budget)

    # ③ 有下界：最小解落在「某个下界 + 一个周期以内」
    out = []
    for at in lbs:
        t = _lin_without(at[1], var)          # 下界里与 x 无关的那部分
        lo, hi = ((0, a - 1) if at[2] == '≥' else (1, a))
        for mcon in range(lo, hi + 1):
            cond = _simp(('div', a, _lin_sub(t, _lin_const(mcon))))
            for i in range(B):
                _spend(budget)
                W = _lin_add(_lin_sub(_lin_const(mcon), t), _lin_const(a * i))
                subs = [_subst_x(one, var, W) for one in xa]
                out.append(_mk_and([cond] + subs + rest))
                if len(out) > MAX_DISJ:
                    raise _TooBig('消元中间结果到 %d 支，超过上限 %d'
                                  % (len(out), MAX_DISJ))
    return _mk_or(out)


def _norm_x(at, var, a):
    """把原子里的 x 系数统一成 a（乘正数保关系；系数为负时关系取反）。"""
    lin = at[1] if at[0] == 'rel' else at[2]
    c = lin[var]
    k = a // abs(c)
    scale = k if c > 0 else -k
    if at[0] == 'rel':
        return _simp(('rel', _lin_scale(lin, scale),
                      at[2] if c > 0 else _FLIP[at[2]]), reduce=False)
    # 整除：m | (c·x + t) 等价于 k·m | k·(c·x + t)
    return ('div', at[1] * k, _lin_scale(lin, scale))


def _subst_x(at, var, W):
    """原子里的 a·x 用 W 代掉（代完之后这个原子就不含 x 了）。"""
    lin = at[1] if at[0] == 'rel' else at[2]
    new = _lin_add(_lin_without(lin, var), W)
    if at[0] == 'rel':
        return _simp(('rel', new, at[2]))
    return _simp(('div', at[1], new))


def _elim_inf(var, a, B, xa, rest, budget):
    """没有下界的情形：x 往足够负处走，上界全满足，只剩整除条件要同时能成立。"""
    divs = [at for at in xa if at[0] == 'div']
    if not divs:
        return _mk_and(rest)
    parts = []
    for k in range(B):
        _spend(budget)
        conj = []
        for at in divs:
            t = _lin_without(at[2], var)
            conj.append(_simp(('div', at[1], _lin_add(t, _lin_const(a * k)))))
        parts.append(_mk_and(conj + rest))
        if len(parts) > MAX_DISJ:
            raise _TooBig('消元中间结果到 %d 支，超过上限 %d'
                          % (len(parts), MAX_DISJ))
    return _mk_or(parts)


def _qe(f, budget):
    """自底向上消掉所有量词；返回与 f 同值的无量词公式。"""
    k = f[0]
    if k in ('true', 'false', 'rel', 'div'):
        return f
    if k == 'not':
        return _nnf(('not', _qe(f[1], budget)))
    if k in ('and', 'or'):
        subs = [_qe(s, budget) for s in f[1]]
        return _mk_and(subs) if k == 'and' else _mk_or(subs)
    if k in ('forall', 'exists'):
        budget[0] -= 1
        if budget[0] < 0:
            raise _TooBig('量词超过 %d 层，不硬算' % MAX_QE)
        body = _qe(f[2], budget)
        if k == 'exists':
            return _elim(f[1], body, budget)
        # ∀x φ 等价于 ¬∃x ¬φ：先取反、消掉、再取反
        return _nnf(('not', _elim(f[1], _nnf(('not', body)), budget)))
    raise ValueError('量词消去遇到不认识的节点：%r' % (k,))


# ══════════════════════════════════════════════════════════════
# 六、求值（无量词、无自由变量时只剩常数）
# ══════════════════════════════════════════════════════════════

def _value(lin, env):
    out = lin.get(_C, 0)
    for k, c in lin.items():
        if k != _C:
            out += c * env[k]
    return out


def _eval_qf(f, env=None):
    env = {} if env is None else env
    k = f[0]
    if k == 'true':
        return True
    if k == 'false':
        return False
    if k == 'rel':
        cv = _value(f[1], env)
        return {'=': cv == 0, '≠': cv != 0, '<': cv < 0,
                '≤': cv <= 0, '>': cv > 0, '≥': cv >= 0}[f[2]]
    if k == 'div':
        return _value(f[2], env) % f[1] == 0
    if k == 'and':
        return all(_eval_qf(s, env) for s in f[1])
    if k == 'or':
        return any(_eval_qf(s, env) for s in f[1])
    raise ValueError('求值遇到带量词的节点：%r' % (k,))


# ══════════════════════════════════════════════════════════════
# 七、渲染（把消元后的等价式写给人看）
# ══════════════════════════════════════════════════════════════

def _fmt_lin(lin):
    parts = []
    for name in sorted(k for k in lin if k != _C):
        c = lin[name]
        parts.append(('%d*%s' % (c, name)) if abs(c) != 1
                     else ('%s%s' % ('-' if c < 0 else '', name)))
    cv = lin.get(_C, 0)
    if cv or not parts:
        parts.append(str(cv))
    out = parts[0]
    for p in parts[1:]:
        out += (' - ' + p[1:]) if p.startswith('-') else (' + ' + p)
    return out


def _fmt(f):
    k = f[0]
    if k == 'true':
        return '真'
    if k == 'false':
        return '假'
    if k == 'rel':
        return '%s %s 0' % (_fmt_lin(f[1]), f[2])
    if k == 'div':
        return '%d | (%s)' % (f[1], _fmt_lin(f[2]))
    if k == 'and':
        return '(' + ' ∧ '.join(_fmt(s) for s in f[1]) + ')'
    if k == 'or':
        return '(' + ' ∨ '.join(_fmt(s) for s in f[1]) + ')'
    return '?'


# ══════════════════════════════════════════════════════════════
# 八、对外接口
# ══════════════════════════════════════════════════════════════

def _pending(msg):
    return {'verdict': 'input_pending', 'explanation': msg, 'equivalent': None,
            'free_variables': [], 'quantifiers': 0, 'boundary': BOUNDARY}


def _search_example(qf, free, want):
    """小范围搜一组自由变量取值，让 qf 等于 want。只用来"给个例子看"。"""
    if not free or len(free) > SEARCH_VARS_MAX:
        return None
    lo, hi = SEARCH_RANGE
    names = sorted(free)
    span = hi - lo
    for n in range(span ** len(names)):
        env, rest = {}, n
        for name in names:
            env[name] = lo + rest % span
            rest //= span
        try:
            if _eval_qf(qf, env) is want:
                return env
        except KeyError:                      # 自由变量没认全（不该发生）
            return None
    return None


def run(inputs):
    """
    做什么：判定一个 Presburger 公式在整数上是否恒真（默认）或有解。

    返回 dict（PORTS['out']）：verdict ∈ true / false / input_pending /
    parse_error / size_limit / internal_error。缺参数给 input_pending。
    """
    if not isinstance(inputs, dict):
        return _pending('inputs 必须是 dict')
    formula = inputs.get('formula')
    if not isinstance(formula, str) or not formula.strip():
        return _pending('需要 formula，例如 "∀x ∃y (y + y = x ∨ y + y + 1 = x)"；'
                        'mode 可省（默认判恒真），也可给 satisfiable（判有没有解）')
    if len(formula) > MAX_INPUT:
        return {'verdict': 'size_limit',
                'explanation': '公式串 %d 字超过上限 %d——不硬算'
                               % (len(formula), MAX_INPUT),
                'equivalent': None, 'free_variables': [], 'quantifiers': 0,
                'boundary': BOUNDARY}
    mode = inputs.get('mode') or 'validity'
    if mode not in ('validity', 'satisfiable'):
        return _pending('mode 只能是 validity（判恒真，默认）或 satisfiable'
                        '（判有没有解），得到 %r' % (mode,))

    try:
        ast = _parse(_tokenize(formula.strip()))
    except ValueError as e:
        return {'verdict': 'parse_error', 'explanation': str(e),
                'equivalent': None, 'free_variables': [], 'quantifiers': 0,
                'boundary': BOUNDARY}
    except _TooBig as e:                       # 公式本身就太大（解析时就在拼树）
        return {'verdict': 'size_limit', 'explanation': '%s——不硬算' % e,
                'equivalent': None, 'free_variables': [], 'quantifiers': 0,
                'boundary': BOUNDARY}

    n_quant = _count_quant(ast)
    free_all = sorted(_free_vars(ast))
    budget = [MAX_QE, MAX_WORK]                # [还能消几个量词, 还能代几次候选值]
    try:
        qf = _qe(_nnf(ast), budget)             # 先消掉公式自带的量词
        target = qf
        for name in sorted(_free_vars(qf)):     # 自由变量按模式补上量词
            target = (('forall' if mode == 'validity' else 'exists'), name, target)
        res = _qe(target, budget)
        if _free_vars(res):
            raise ValueError('消元后还剩自由变量 %s' % sorted(_free_vars(res)))
        val = _eval_qf(res)
    except _TooBig as e:
        return {'verdict': 'size_limit',
                'explanation': '%s——本构件不硬算（规模上限是诚实的，'
                               '不是判定结论）' % e,
                'equivalent': None, 'free_variables': free_all,
                'quantifiers': n_quant, 'boundary': BOUNDARY}
    except Exception as e:  # noqa: BLE001——真出意外就如实报，不假装有结论
        return {'verdict': 'internal_error',
                'explanation': '%s: %s' % (type(e).__name__, e),
                'equivalent': None, 'free_variables': free_all,
                'quantifiers': n_quant, 'boundary': BOUNDARY}

    out = {'verdict': 'true' if val else 'false',
           'equivalent': _fmt(qf),
           'free_variables': free_all,
           'quantifiers': n_quant,
           'boundary': BOUNDARY}

    def _show(ex):
        return '，例如 ' + '、'.join('%s=%d' % kv for kv in sorted(ex.items()))

    if mode == 'validity':
        if val:
            out['explanation'] = ('在整数上恒真（%d 个自由变量怎么取值都成立）；'
                                  '消去量词后等价式为 %s'
                                  % (len(free_all), _fmt(qf)))
        else:
            ex = _search_example(qf, set(free_all), False)
            out['explanation'] = ('不是恒真：存在整数取值使它为假'
                                  + (_show(ex) if ex else
                                     '（反例没在小范围搜到，但结论由消元给出）'))
            if ex:
                out['counterexample'] = ex
    else:
        if val:
            ex = _search_example(qf, set(free_all), True)
            out['explanation'] = ('在整数上有解；消去量词后等价式为 %s%s'
                                  % (_fmt(qf), _show(ex) if ex else ''))
            if ex:
                out['witness'] = ex
        else:
            out['explanation'] = ('在整数上无解（同余与不等条件凑不到一起）；'
                                  '消去量词后等价式为 %s' % _fmt(qf))
    return out


def _selftest():
    ok = run({'formula': '∀x ∃y (y + y = x ∨ y + y + 1 = x)'})
    assert ok['verdict'] == 'true', ok
    bad = run({'formula': '∃x (2 * x = 3)'})
    assert bad['verdict'] == 'false', bad
    nd = run({'formula': '∃x (2 | x ∧ 2 | x + 1)'})
    assert nd['verdict'] == 'false', nd
    pe = run({'formula': '∃x (x * x = 4)'})
    assert pe['verdict'] == 'parse_error', pe
    print('✅ Presburger 判定自测：奇偶覆盖为真 / 2x=3 为假 / 同余打架为假 / '
          '变量乘变量被拦下')


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    _selftest()
