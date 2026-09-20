# -*- coding: utf-8 -*-
"""
monadic_fol.py — 一元谓词一阶逻辑（monadic FOL）判定 · 第 1 层经典构件
================================================================
概念来源：经典共识（Löwenheim 1915 / 表列法经典结果）——**只留一元谓词**，
一阶逻辑立刻从半可判定变成可判定；这是「可判定片段」的教科书入口。
公式卡：docs/formulas/monadic_fol.md

本构件做什么（一句话）：
    判定一个**闭的一元谓词公式**是否有效：谓词只作用在一个变量上（P(x)、Q(x)…），
    用「有限域展开」——经典结论：k 个一元谓词的公式若可满足，则在规模 ≤ 2^k 的
    域上可满足；于是枚举小域上的所有谓词外延与所有赋值，穷尽即可判定。

语法（工程子集，够用且能说清边界）：
    atom    := P(x)（一元谓词；变量统一用 x）
    formula := atom | ¬formula | (formula ∧|∨|→|↔ formula)
             | ∀x formula | ∃x formula | (formula)
    只接受**闭公式**（量词绑住所有出现）。

诚实边界：
    - **谓词数 k ≤ 2 时是完备判定**（域取到 2^k = 4 就够）：给 valid / invalid（含反模型）；
    - k = 3 时域要到 8，枚举量爆炸：此时只做**小域搜索**——找到模型报 satisfiable（是真的），
      找不到报 undecided（**搜索不完备 ≠ 不可满足**，不许当反例用）；
    - k > 3 直接报 size_limit（不假装能算）；
    - 二元以上谓词、函数符号、自由变量一律 parse_error（本构件只管一元片段）。
"""

PORTS = {
    'in': {'formula': 'str?', 'mode': 'str?'},
    'out': {'verdict': 'str', 'explanation': 'str', 'countermodel': 'dict?',
            'predicates': 'list', 'domain_size': 'int?', 'boundary': 'str'},
}

import itertools
import re
import sys

BOUNDARY = ('一元谓词片段（monadic）判定：k ≤ 2 完备（域取到 2^k），k = 3 只做小域搜索'
            '（找不到模型报 undecided——搜索不完备 ≠ 不可满足），k > 3 报 size_limit。'
            '本构件不管二元谓词/函数符号/自由变量（那属于半可判定的全域）。'
            '只诊断不决策。')

_TOKEN = re.compile(r'\s*(∀|∃|¬|∧|∨|→|↔|\(|\)|[A-Z][A-Za-z0-9_]*(?:\(x\))?|x)')


def _tokenize(s):
    out, i = [], 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            raise ValueError('无法识别的字符：%r' % s[i:i + 8])
        out.append(m.group(1))
        i = m.end()
    return out


# ── 递归下降解析（带优先级；量词绑定其后的一元式，与常见写法一致）
def _parse(tokens):
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def iff():
        left = impl()
        while peek() == '↔':
            take()
            left = ('↔', left, impl())
        return left

    def impl():
        left = disj()
        if peek() == '→':
            take()
            return ('→', left, impl())      # 右结合
        return left

    def disj():
        left = conj()
        while peek() == '∨':
            take()
            left = ('∨', left, conj())
        return left

    def conj():
        left = unary()
        while peek() == '∧':
            take()
            left = ('∧', left, unary())
        return left

    def unary():
        t = peek()
        if t == '¬':
            take()
            return ('¬', unary())
        if t in ('∀', '∃'):
            take()
            if take() != 'x':
                raise ValueError('量词后面必须跟变量 x')
            return (t, unary())
        if t == '(':
            take()
            inner = iff()
            if take() != ')':
                raise ValueError('括号没闭合')
            return inner
        if t == 'x':
            raise ValueError('本构件只判定闭公式——不允许自由变量 x')
        if t and t.endswith('(x)'):
            take()
            return ('atom', t[:-3])
        raise ValueError('看不懂的记号：%r' % t)

    ast = iff()
    if pos[0] != len(tokens):
        raise ValueError('公式解析完还有多余记号：%r' % tokens[pos[0]:])
    return ast


def _paren_free(s):
    """给裸的量词体补括号提示用（不参与解析，仅文档/纠错）——保留占位。"""
    return s


def _preds(ast, acc=None):
    acc = set() if acc is None else acc
    if ast[0] == 'atom':
        acc.add(ast[1])
    for sub in ast[1:]:
        if isinstance(sub, tuple):
            _preds(sub, acc)
    return acc


def _eval(ast, dom, ext, env):
    """在给定域 dom、谓词外延 ext[P]（dom 的子集）与指派 env（x → 元素）下求值。"""
    k = ast[0]
    if k == 'atom':
        return env['x'] in ext[ast[1]]
    if k == '¬':
        return not _eval(ast[1], dom, ext, env)
    if k in ('∧', '∨', '→', '↔'):
        a = _eval(ast[1], dom, ext, env)
        b = _eval(ast[2], dom, ext, env)
        return {'∧': a and b, '∨': a or b, '→': (not a) or b,
                '↔': a == b}[k]
    if k in ('∀', '∃'):
        vals = []
        for d in dom:
            env['x'] = d
            vals.append(_eval(ast[1], dom, ext, env))
        return all(vals) if k == '∀' else any(vals)


def _satisfiable(ast, preds, n):
    """在规模 n 的域上穷举所有谓词外延，找模型；找到返回模型，否则 None。"""
    dom = tuple(range(n))
    subsets = [tuple(c) for r in range(n + 1)
               for c in itertools.combinations(dom, r)]
    for combo in itertools.product(subsets, repeat=len(preds)):
        ext = dict(zip(preds, combo))
        if _eval(ast, dom, ext, {'x': 0}):
            return {'domain_size': n,
                    'extensions': {p: list(ext[p]) for p in preds}}
    return None


def run(inputs):
    """
    做什么：判定闭的一元谓词公式是否有效（可满足性穷举 + 反证）。

    返回 dict（PORTS['out']）：verdict ∈ valid / invalid / satisfiable /
    undecided / size_limit / parse_error。缺参数给 input_pending。
    """
    if not isinstance(inputs, dict):
        return {'verdict': 'input_pending', 'explanation': 'inputs 必须是 dict',
                'predicates': [], 'boundary': BOUNDARY}
    f = inputs.get('formula')
    if not isinstance(f, str) or not f.strip():
        return {'verdict': 'input_pending',
                'explanation': '需要 formula（一元谓词闭公式，如 ∀x P(x) → ∃x P(x)）',
                'predicates': [], 'boundary': BOUNDARY}
    try:
        ast = _parse(_tokenize(f.strip()))
    except ValueError as e:
        return {'verdict': 'parse_error', 'explanation': str(e),
                'predicates': [], 'boundary': BOUNDARY}

    preds = sorted(_preds(ast))
    k = len(preds)
    base = {'predicates': preds, 'boundary': BOUNDARY}
    if k == 0:
        # 没有谓词：公式是真值常量，直接求值
        val = _eval(ast, (0,), {}, {'x': 0})
        return dict(base, verdict='valid' if val else 'invalid',
                    explanation='公式不含谓词（真值常量）：%s'
                                % ('恒真' if val else '恒假'))

    neg = ('¬', ast)
    if k <= 2:
        # 完备：域取到 2^k 足够（Löwenheim/表列法经典结论）
        for n in range(1, 2 ** k + 1):
            if _satisfiable(neg, preds, n) is None:
                continue
            model = _satisfiable(neg, preds, n)
            return dict(base, verdict='invalid', domain_size=n,
                        countermodel=model,
                        explanation='找到反模型（规模 %d 的域上有使公式为假的赋值）'
                                    '——所以不是有效式' % n)
        return dict(base, verdict='valid',
                    explanation='在 1..%d 的全部域上穷举谓词外延，'
                                '公式的否定不可满足 → 有效式' % (2 ** k))
    # k >= 3：搜索不完备，只报能确定的部分
    for n in (1, 2):
        model = _satisfiable(neg, preds, n)
        if model is not None:
            return dict(base, verdict='invalid', domain_size=n,
                        countermodel=model,
                        explanation='找到反模型（规模 %d）——不是有效式' % n)
    if k == 3:
        return dict(base, verdict='undecided',
                    explanation='谓词数 3 时完备判定需要域到 8（枚举量爆炸）——'
                                '小域上没找到反模型，**搜索不完备 ≠ 公式有效**')
    return dict(base, verdict='size_limit',
                explanation='谓词 %d 个：完备域要到 2^%d——超出本构件范围'
                            '（不假装能算）' % (k, k))


def _selftest():
    ok = run({'formula': '∀x P(x) → ∃x P(x)'})
    assert ok['verdict'] == 'valid', ok
    bad = run({'formula': '∀x (P(x) ∨ Q(x)) → (∀x P(x) ∨ ∀x Q(x))'})
    assert bad['verdict'] == 'invalid' and bad['countermodel'], bad
    pe = run({'formula': '∀x R(x,y)'})
    assert pe['verdict'] == 'parse_error', pe
    print('✅ 一元谓词判定自测：有效式 / 反模型 / 自由变量拦下')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    _selftest()
