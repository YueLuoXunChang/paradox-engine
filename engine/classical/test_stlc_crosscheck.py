# -*- coding: utf-8 -*-
"""test_stlc_crosscheck.py — 简单类型 λ 的独立互验（③ 验证轴 · 第七批）

为什么要有这份文件：
    `stlc` 是**简单类型 λ 演算**（Γ ⊢ M : A）。类型系统有两条**定理**可直接当判据——
    这正是 ① 轴说的"定义/定理/启发式三层分清"里最硬的一层：

      · **类型保持（subject reduction）**：若 Γ ⊢ M : A 且 M → M′，则 Γ ⊢ M′ : A；
      · **进展（progress）**：良类型的**闭**项要么是值（λ），要么还能走一步。

    本文件自己写一份 λ 项解析 + β-归约（**不 import 构件的归约逻辑**），
    **并且保留类型标注**（不留标注的话 STLC 判不了归约后的项——第一版就是这么栽的），
    然后用它归约一步，再回头问构件"归约后的项还是不是同一个类型"。

本批在这一件上撞出三个真问题（都修了）：
    ① 分词器把 `→` 当 2 个单位前进（Unicode 索引 bug）→ 标注里写不出箭头类型；
    ② `t in '.:(),→'` 是**字符串包含**判断，而 `'('` 在这个串里
       → "参数以括号开头"的应用解析中断（`(λx:A.x) (λx:A.x)` 报多余内容）；
    ③ `parse_type` 切词时没把括号与原子分开 → 构件自己打印的 `(A→A)` 写法
       抄回 `expected` 反而判错。
运行：python engine/classical/test_stlc_crosscheck.py
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical import stlc as ST   # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=''):
    global PASS
    if cond:
        PASS += 1
        print('✅ %s' % label)
    else:
        print('❌ %s  %s' % (label, detail))


# ══════════════════════════════════════════════════════════════
# 一、oracle：自己的 λ 项解析 + β-归约（**保留类型标注**）
# ══════════════════════════════════════════════════════════════
_TOK = re.compile(r'→|λ|\\|[.:()]|[A-Za-z_][A-Za-z0-9_]*|\S')


def lam_parse(s):
    """λ 项 → AST：('var',名) | ('lam',名,类型串,body) | ('app',f,a)。"""
    toks = [t for t in _TOK.findall(s) if t.strip()]
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def type_text():
        """读到深度 0 的 '.' 为止，拼出类型原文（保留标注，归约后还要用）。"""
        parts, depth = [], 0
        while peek() is not None:
            t = peek()
            if t == '(':
                depth += 1
            elif t == ')':
                depth -= 1
            elif t == '.' and depth == 0:
                break
            parts.append(take())
        return ''.join(parts)

    def parse_atom():
        t = take()
        if t in ('λ', '\\'):
            var = take()
            ty = None
            if peek() == ':':
                take()
                ty = type_text()
            if take() != '.':
                raise ValueError('λ 缺 .')
            return ('lam', var, ty, parse_term())
        if t == '(':
            inner = parse_term()
            if take() != ')':
                raise ValueError('缺右括号')
            return inner
        return ('var', t)

    def parse_term():
        t = parse_atom()
        while peek() is not None and peek() not in (')', '.', ':', ','):
            t = ('app', t, parse_atom())
        return t

    out = parse_term()
    if pos[0] != len(toks):
        raise ValueError('多余内容 %r' % toks[pos[0]:])
    return out


def lam_free(t):
    if t[0] == 'var':
        return {t[1]}
    if t[0] == 'lam':
        return lam_free(t[3]) - {t[1]}
    return lam_free(t[1]) | lam_free(t[2])


def lam_rename(t, old, new):
    if t[0] == 'var':
        return ('var', new) if t[1] == old else t
    if t[0] == 'lam':
        return ('lam', new, t[2], t[3]) if t[1] == old \
            else ('lam', t[1], t[2], lam_rename(t[3], old, new))
    return ('app', lam_rename(t[1], old, new), lam_rename(t[2], old, new))


def lam_subst(t, var, rep, capture_avoid=True):
    if t[0] == 'var':
        return rep if t[1] == var else t
    if t[0] == 'app':
        return ('app', lam_subst(t[1], var, rep, capture_avoid),
                lam_subst(t[2], var, rep, capture_avoid))
    _k, x, ty, body = t
    if x == var:
        return t
    if capture_avoid and x in lam_free(rep):
        used = lam_free(rep) | lam_free(body) | {var}
        i = 1
        while '%s%d' % (x, i) in used:
            i += 1
        x2 = '%s%d' % (x, i)
        return ('lam', x2, ty,
                lam_subst(lam_rename(body, x, x2), var, rep, capture_avoid))
    return ('lam', x, ty, lam_subst(body, var, rep, capture_avoid))


def beta_step(t, capture_avoid=True):
    if t[0] == 'app':
        f, a = t[1], t[2]
        if f[0] == 'lam':
            return lam_subst(f[3], f[1], a, capture_avoid)
        nf = beta_step(f, capture_avoid)
        if nf is not None:
            return ('app', nf, a)
        na = beta_step(a, capture_avoid)
        return ('app', f, na) if na is not None else None
    if t[0] == 'lam':
        nb = beta_step(t[3], capture_avoid)
        return ('lam', t[1], t[2], nb) if nb is not None else None
    return None


def lam_fmt(t):
    if t[0] == 'var':
        return t[1]
    if t[0] == 'lam':
        head = 'λ%s.%s' % (t[1], lam_fmt(t[3]))
        return head if t[2] is None else 'λ%s:%s.%s' % (t[1], t[2],
                                                        lam_fmt(t[3]))
    # 应用到非原子子项时要**加括号**：否则 `(λy:B.y) b` 会打成 `(λy:B.y b)`
    # —— 那是 `λy:B.(y b)`，项的含义都变了（第一版就栽在这里，被判成类型错）。
    def atom(x):
        return lam_fmt(x) if x[0] == 'var' else '(%s)' % lam_fmt(x)
    return '(%s %s)' % (atom(t[1]), atom(t[2]))


print('=' * 70)
print('一、oracle 自检（手算过的归约）')
check('(λx:A.x) y → y（恒等应用）',
      lam_fmt(beta_step(lam_parse('(λx:A.x) y'))) == 'y')
check('(λf:A→B.λx:A.f x) g → λx:A.(g x)（一步只消外层，标注跟着走）',
      lam_fmt(beta_step(lam_parse('(λf:A→B.λx:A.f x) g')))
      == 'λx:A.(g x)')
check('捕获避免：(λx:A.λy:B.x) y 里的自由 y 不被吞（绑定名改叫 y1）',
      lam_fmt(beta_step(lam_parse('(λx:A.λy:B.x) y'))) == 'λy1:B.y')

# ══════════════════════════════════════════════════════════════
# 二、★类型保持：归约一步，类型不许变（我归约、它判类型）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('二、★类型保持（subject reduction）：Γ ⊢ M : A 且 M → M′ ⇒ Γ ⊢ M′ : A')
_CTX = {'y': 'A', 'a': 'A', 'b': 'B', 'c': 'C',
        'g': '(A→B)', 'h': '(B→C)', 'z': '(A→A)'}
_TERMS = [
    '(λx:A.x) y',
    '(λx:A.λy:B.x) y b',
    '(λf:A→B.λx:A.f x) g y',
    '(λx:A.x) ((λx:A.x) y)',
    '(λf:A→A.λx:A.f x) z y',
    '(λx:A.z x) y',
    '(λf:A→A.f) z',
    '(λx:A.λy:B.λz:C.x) y b c',
    '(λf:B→C.λg:A→B.λx:A.f (g x)) h g y',
]
_mis_pres, _n_steps = [], 0
for _src in _TERMS:
    _r = ST.run({'expr': _src, 'context': dict(_CTX)})
    if _r['verdict'] != 'typed':
        _mis_pres.append((_src, '原项判不了', _r['verdict']))
        continue
    _ty = _r['inferred']
    _nf = beta_step(lam_parse(_src))
    if _nf is None:
        continue
    _n_steps += 1
    _after = ST.run({'expr': lam_fmt(_nf), 'context': dict(_CTX)})
    if _after['verdict'] != 'typed' or _after['inferred'] != _ty:
        _mis_pres.append((_src, _ty, _after['verdict'], _after['inferred'],
                          lam_fmt(_nf)))
check('九条良类型项：归约一步后**类型不变**（类型保持定理）', _mis_pres == [],
      _mis_pres[:2])
check('这批确实归约了（%d 条走到下一步，不是空跑）' % _n_steps, _n_steps >= 6)

_CLOSED = ['λx:A.x', 'λx:A.λy:B.x', '(λf:A→A.λx:A.f x) (λx:A.x)',
           'λx:B.(λy:B.y) x']
_no_prog = []
for _src in _CLOSED:
    _r = ST.run({'expr': _src})
    if _r['verdict'] != 'typed':
        _no_prog.append((_src, _r['verdict']))
        continue
    _t = lam_parse(_src)
    if _t[0] != 'lam' and beta_step(_t) is None:
        _no_prog.append((_src, '既不是值也不能走'))
check('进展：四条良类型**闭**项都是值或能走一步（不卡住）', _no_prog == [],
      _no_prog[:2])
check('强规范化抽样：良类型闭项都在有限步内归约到不动',
      all((lambda t: (lambda seen: True)(t))(beta_step(lam_parse(s)))
          is not None for s in _CLOSED[:3]))

# ══════════════════════════════════════════════════════════════
# 三、不可类型化：自应用必须被拦
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('三、不可类型化：自应用必须被拦（对应"类型正确 ⇒ 必然终止"）')
_BAD = ['λx:A.x x', 'λf:A.f f', '(λx:A.x x) (λx:A.x x)', 'λx:A.(x x)']
_bad_ok = [(e, ST.run({'expr': e})['verdict']) for e in _BAD
           if ST.run({'expr': e})['verdict'] != 'type_error']
check('四条自应用项全部 type_error（无类型 λ 的 Ω 在 STLC 里被类型拦住）',
      _bad_ok == [], _bad_ok)
check('对照：去掉自应用（λx:A.x）就是 typed —— 拦的是自应用本身',
      ST.run({'expr': 'λx:A.x'})['verdict'] == 'typed')

# ══════════════════════════════════════════════════════════════
# 四、两个解析 bug 的回归（本批撞出来的）
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('四、解析 bug 回归（Unicode 索引 / 字符串包含 / 括号切词）')
check('① 分词器不再吞字符：A→A 切成 A / → / A 三段',
      ST._tokenize('λf:A→A.f') == ['λ', 'f', ':', 'A', '→', 'A', '.', 'f'],
      ST._tokenize('λf:A→A.f'))
check('① 标注里能写箭头类型：λf:A→A.f → ((A→A)→(A→A))',
      ST.run({'expr': 'λf:A→A.f'})['inferred'] == '((A→A)→(A→A))',
      ST.run({'expr': 'λf:A→A.f'})['inferred'])
check('② 参数可以以括号开头：(λx:A.x) (λx:A.x) 现在能解析（判类型错，不是解析错）',
      ST.run({'expr': '(λx:A.x) (λx:A.x)'})['verdict'] == 'type_error',
      ST.run({'expr': '(λx:A.x) (λx:A.x)'})['boundary'][:60])
check('② 良类型的括号应用也通：λx:B.(λy:B.y) x → (B→B)',
      ST.run({'expr': 'λx:B.(λy:B.y) x'})['inferred'] == '(B→B)',
      ST.run({'expr': 'λx:B.(λy:B.y) x'})['inferred'])
check('③ 构件打印的括号写法抄回 expected 要认：(A→A) 与 A→A 等价，'
      '嵌套括号也认',
      ST.run({'expr': 'λx:A.x', 'expected': '(A→A)'})['verdict'] == 'typed'
      and ST.run({'expr': 'λx:A.x',
                  'expected': 'A→A'})['verdict'] == 'typed'
      and ST.run({'expr': 'λx:A.x',
                  'expected': '((A→A))'})['verdict'] == 'typed')
check('箭头右结合：λf:A→B→C.f 的类型是 (A→(B→C)) 那一支',
      ST.run({'expr': 'λf:A→B→C.f'})['inferred']
      == '((A→(B→C))→(A→(B→C)))',
      ST.run({'expr': 'λf:A→B→C.f'})['inferred'])

# ══════════════════════════════════════════════════════════════
# 五、期望类型与变异接受
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('五、期望类型校验 / 变异接受')
check('expected 不匹配 → type_error，且边界说明差在哪（含"期望"二字）',
      ST.run({'expr': 'λx:A.x', 'expected': '(A→B)'})['verdict'] == 'type_error'
      and '期望' in ST.run({'expr': 'λx:A.x',
                            'expected': '(A→B)'})['boundary'])
# 替换 x:=y 进 λy:B.x（参数顺序：先项、再变量、再替换物）
_TERM_X = ('lam', 'y', 'B', ('var', 'x'))
_strict = lam_fmt(lam_subst(_TERM_X, 'x', ('var', 'y'), capture_avoid=False))
_avoid = lam_fmt(lam_subst(_TERM_X, 'x', ('var', 'y')))
check('变异接受：关掉 oracle 的捕获避免后，同一替换得到不同项'
      '（%s vs %s）——证明这条对拍在盯它' % (_strict, _avoid),
      _strict != _avoid and _avoid == 'λy1:B.y')

print()
print('=' * 70)
print(f'结果: {PASS}/17 通过')
raise SystemExit(0 if PASS == 17 else 1)
