# -*- coding: utf-8 -*-
"""
asp.py — 答案集程序（ASP / 稳定模型语义）· 第 3 层按痛点接入
================================================================
概念来源：**外部经典共识**——Gelfond & Lifschitz 1988 的稳定模型语义（reduct 定义）、
Gelfond & Kahl 2014 的知识表示综述、Egly-Nieuwenborgh-Vermeir 的论证框架 ASP 编码。
**归借鉴区**（落落三问：借什么=「规则 + 否定即失败（not）+ 约束」这套写法与"答案集"
这个结论形态；为什么=引擎已经有默认逻辑（Reiter 扩展）与 Dung 稳定语义，但**没有那套
大家真在用的写法**——"看了规则就知道结论怎么来的"；而 ASP 的**推导依据**能逐条列出来
（哪个原子靠哪条规则撑住），正好接上本仓"结论必须可复核"的纪律；怎么记账=标注来源归
借鉴区，不混原创区）。

本构件做什么（一句话）：
    给一套**规则**（事实 · 带"否定即失败"的规则 · 完整性约束），算出它**自洽的结论集合**
    （答案集 / answer set）——可能一个、可能多个、也可能**一个都没有**（那说明这套规则
    自相矛盾，本构件照实说），并给每个原子**写明它是靠哪条规则撑住的**。

语言（正规则程序 normal program 这个工程子集，够用且边界清楚）：
    规则   := 头 :- 体 .         （体内逗号分隔；字面 = 原子 | not 原子）
    事实   := 原子 .             （等于「头 :- 空体」）
    约束   := :- 体 .            （体成立就不许——用来写"这些不能同时成立"）
    原子名 := 字母/数字/下划线/汉字组成的词（不含空格、逗号、点、冒号横杠）
    not 也认 `!` 与 `¬`；每条规则以 `.` 收尾。

怎么算的（白话，reduct 两步）：
    猜一个结论集合 X，然后①把 X 当"世界"来化简规则：规则体里 `not a` 若 a 已在 X 里
    这条规则就作废，`not a` 若 a 不在 X 里就把这个字面删掉；②化简后的规则（只剩正字面了）
    从空集出发一遍遍推，得到**最小模型**。X 恰好等于这个最小模型 → X 就是一个答案集。
    这就是 Gelfond-Lifschitz 的 reduct 定义；约束成立时才留得下这个 X。
    本构件把推导链一并交出（每个原子靠哪条规则），结论不是黑箱。

诚实边界：
    - **只做正规则程序**（normal rules + not + 约束）：**不做**选择规则（choice）、
      基数约束（#count 那类）、聚合、优化（#minimize）、以及带变量的规则（本构件是
      命题层面，不替使用者做 grounding）；
    - 原子数有上限（超了报 size_limit——答案集是逐个候选核出来的，不硬跑）；
    - 结论是**相对这套规则**的：答案集多、少、没有，都照实报，不替使用者挑一个；
    - 只诊断不决策：不替使用者定规则该怎么写、也不说哪个答案集"更对"。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'solve'（默认，算全部答案集）|'query'（问某个原子）
        program: str——规则文本（多条用 `.` 分隔或换行）
        query: str——query 模式要问的原子名
    输出:
        verdict: str——'solved'|'no_answer_set'|'in_all'|'in_some'|'in_none'
                        |'parse_error'|'input_pending'|'size_limit'|'internal_error'
        answer_sets: list——每个答案集：原子列表 + 每个原子的推导依据
        count: int——答案集个数
        query: dict?——query 模式的结果（原子 / in_all|in_some|in_none）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'program': 'str?', 'query': 'str?'},
    'out': {'verdict': 'str', 'answer_sets': 'list', 'count': 'int',
            'query': 'dict?', 'boundary': 'str'},
}

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BOUNDARY = ('答案集程序 ASP（外部共识：Gelfond & Lifschitz 1988 的稳定模型语义 / '
            'Gelfond & Kahl 2014 的知识表示综述，借鉴区）：算"规则 + 否定即失败 + '
            '约束"这套写法下的**自洽结论集合**（答案集），并给出每个原子的推导依据。'
            '**只做正规则程序**——不做选择规则、基数约束、聚合、优化，也不做带变量规则的 '
            'grounding（本构件是命题层面）；原子数有上限，超了报 size_limit 不硬跑。'
            '答案集可能一个、多个或**一个都没有**（没有就是这套规则自相矛盾），都照实报；'
            '结论是**相对这套规则**的，不替使用者挑"哪个答案集更对"。'
            '只诊断不决策：不替使用者定规则该怎么写。')

MAX_ATOMS = 16        # 原子数上限（答案集是逐个候选核出来的，2^n 不硬跑）
MAX_RULES = 400       # 规则条数上限
MAX_LISTED = 64       # 最多列出多少个答案集（超了只报个数）

_KEYWORDS = ('not',)
_NAME = re.compile(r'^[\w\u4e00-\u9fff]+$', re.UNICODE)


class _ParseError(ValueError):
    pass


class _TooBig(Exception):
    pass


# ══════════════════════════════════════════════════════════════
# 一、程序：解析
# ══════════════════════════════════════════════════════════════

def _split_statements(text):
    """按「.」切规则——原子名里不许有点，所以切法是干净的。"""
    out = []
    for chunk in text.replace('\r\n', '\n').replace('\n', ' ').split('.'):
        s = chunk.strip()
        if s:
            out.append(s)
    return out


def _parse_literal(tok):
    t = tok.strip()
    if not t:
        raise _ParseError('规则体里有空的字面')
    neg = False
    while True:
        low = t.lower()
        if low.startswith('not '):
            neg = not neg
            t = t[4:].strip()
            continue
        if t.startswith('!') or t.startswith('¬'):
            neg = not neg
            t = t[1:].strip()
            continue
        break
    if not _NAME.match(t):
        raise _ParseError('原子名不合法：%r（只能是字母/数字/下划线/汉字组成的词）' % t)
    return (t, neg)


def _parse_program(text):
    """规则文本 → (规则列表, 约束列表, 原子集合)。
    规则 = (头, [(原子, 是否 not), ...])；约束 = [(原子, 是否 not), ...]"""
    rules, cons, atoms = [], [], set()
    stmts = _split_statements(text)
    if len(stmts) > MAX_RULES:
        raise _TooBig('规则条数 %d 超过上限 %d' % (len(stmts), MAX_RULES))
    for st in stmts:
        if st.startswith(':-'):
            body_txt = st[2:].strip()
            if not body_txt:
                raise _ParseError('约束不能是空的（:- . 没有意义）：%r' % st)
            body = [_parse_literal(x) for x in body_txt.split(',')]
            cons.append(body)
            for a, _n in body:
                atoms.add(a)
            continue
        if ':-' in st:
            head_txt, _, body_txt = st.partition(':-')
            if not body_txt.strip():
                raise _ParseError('「:-」后面不能空着（想要事实就直接写「头.」）：%r'
                                  % st)
        else:
            head_txt, body_txt = st, ''
        head = _parse_literal(head_txt)
        if head[1]:
            raise _ParseError('规则头不能写 not：%r' % st)
        if not _NAME.match(head[0]):
            raise _ParseError('规则头不合法：%r' % head_txt)
        body = []
        if body_txt.strip():
            body = [_parse_literal(x) for x in body_txt.strip().split(',')]
        for a, _n in [head] + body:
            atoms.add(a)
        rules.append((head[0], body))
    if len(atoms) > MAX_ATOMS:
        raise _TooBig('原子数 %d 超过上限 %d（答案集是逐个候选核出来的，不硬跑）'
                      % (len(atoms), MAX_ATOMS))
    return rules, cons, atoms


def _fmt_rule(head, pos):
    """把推导依据还原成规则文本（依据来自化简后的正体，所以只可能是正字面）。"""
    if not pos:
        return '%s.' % head
    return '%s :- %s.' % (head, ', '.join(pos))


# ══════════════════════════════════════════════════════════════
# 二、稳定模型：reduct + 最小模型
# ══════════════════════════════════════════════════════════════

def _reduct(rules, X):
    """GL 化简：not a 而 a ∈ X 的规则作废；not a 而 a ∉ X 的字面删掉。"""
    out = []
    for head, body in rules:
        keep, pos = True, []
        for a, neg in body:
            if neg:
                if a in X:
                    keep = False
                    break
            else:
                pos.append(a)
        if keep:
            out.append((head, pos))
    return out


def _least_model(definite, atoms):
    """正程序（已经全是正字面）的最小模型：从空集起反复推，直到不动。
    返回 (模型集合, {原子: 撑住它的那条规则})。"""
    model, why = set(), {}
    changed = True
    while changed:
        changed = False
        for head, pos in definite:
            if head in model:
                continue
            if all(p in model for p in pos):
                model.add(head)
                why[head] = (head, pos)
                changed = True
    return model, why


def _constraint_violated(cons, X):
    """约束体在 X 上成立 → 这个候选不算答案集。"""
    for body in cons:
        ok = True
        for a, neg in body:
            if neg:
                if a in X:
                    ok = False
                    break
            elif a not in X:
                ok = False
                break
        if ok:
            return body
    return None


def _stable_sets(atoms, rules, cons):
    """逐个候选核：X 是答案集 ⟺ 约束都不破 且 X == 化简后的最小模型。"""
    names = sorted(atoms)
    out = []
    for bits in range(1 << len(names)):
        X = frozenset(names[i] for i in range(len(names)) if bits >> i & 1)
        if _constraint_violated(cons, X):
            continue
        lm, why = _least_model(_reduct(rules, X), atoms)
        if lm == X:
            out.append({'atoms': sorted(X),
                        'support': {a: _fmt_rule(*why[a]) for a in sorted(X)}})
    return out


# ══════════════════════════════════════════════════════════════
# 三、对外推理
# ══════════════════════════════════════════════════════════════

def _out(verdict, boundary=BOUNDARY, **kw):
    out = {'verdict': verdict, 'answer_sets': [], 'count': 0, 'query': None,
           'boundary': boundary}
    out.update(kw)
    return out


def run(inputs):
    """
    做什么：算答案集 / 问某个原子在答案集里的地位。

    返回 dict（见模块 docstring）。"""
    if not isinstance(inputs, dict):
        return _out('input_pending', 'inputs 必须是 dict')
    mode = inputs.get('mode') or 'solve'
    if mode not in ('solve', 'query'):
        return _out('input_pending',
                    'mode 应为 solve/query，得到 %r' % (mode,))
    text = inputs.get('program')
    if not isinstance(text, str) or not text.strip():
        return _out('input_pending',
                    '需要 program（规则文本，如 "p :- not q. q :- not p."）'
                    '——诚实拦截')
    try:
        rules, cons, atoms = _parse_program(text)
    except _TooBig as e:
        return _out('size_limit', '%s——%s，不硬跑' % (e, BOUNDARY))
    except _ParseError as e:
        return _out('parse_error', str(e))
    if not atoms:
        return _out('input_pending', '程序里一个原子都没有——诚实拦截')
    if not rules and not cons:
        return _out('input_pending', '程序里一条规则都没有——诚实拦截')

    try:
        sets = _stable_sets(atoms, rules, cons)
    except Exception as e:  # noqa: BLE001——真出意外如实报
        return _out('internal_error', '算答案集出意外（%s: %s）'
                    % (type(e).__name__, e))
    shown = sets[:MAX_LISTED]
    note = ''
    if len(sets) > MAX_LISTED:
        note = '（答案集 %d 个，这里只列出前 %d 个）' % (len(sets), MAX_LISTED)

    if mode == 'query':
        q = inputs.get('query')
        if not isinstance(q, str) or not q.strip():
            return _out('input_pending', 'query 模式需要 query（要问的原子名）')
        q = q.strip()
        if q not in atoms:
            return _out('input_pending',
                        '原子 %r 没在这套规则里出现过——诚实拦截（不隐式补）' % q)
        if not sets:
            return _out('in_none',
                        answer_sets=[], count=0,
                        query={'atom': q, 'in': 'none', 'why': '一个答案集都没有'},
                        boundary='问「%s」：这套规则**压根没有答案集**（自相矛盾），'
                                 '所以谈不上它在不在。%s' % (q, BOUNDARY))
        inside = [bool(s['atoms'] and q in s['atoms']) for s in sets]
        if all(inside):
            where = 'in_all'
            why = '每个答案集里都有它（怀疑论口径：可以下这个结论）'
        elif any(inside):
            where = 'in_some'
            why = ('只在 %d/%d 个答案集里有它（轻信论口径：能撑住，但另一套结论同样自洽）'
                   % (sum(inside), len(sets)))
        else:
            where = 'in_none'
            why = '每个答案集里都没有它'
        return _out(where, answer_sets=shown, count=len(sets),
                    query={'atom': q, 'in': where.replace('in_', ''), 'why': why},
                    boundary='问「%s」：%s。%s%s' % (q, why, note, BOUNDARY))

    if not sets:
        return _out('no_answer_set', answer_sets=[], count=0,
                    boundary='这套规则**一个答案集都没有**——按稳定模型语义，'
                             '它不是"算不出来"，而是"它要求的结论互相打架，'
                             '没有任何自洽的结论集合"（约束或多条规则互相顶住了）。'
                             '这是确定结论：%d 个原子、%d 条规则全核过了。%s'
                    % (len(atoms), len(rules) + len(cons), BOUNDARY))
    return _out('solved', answer_sets=shown, count=len(sets),
                boundary='算出 %d 个答案集%s；每个原子都写了它是靠哪条规则撑住的'
                         '（可复核）。答案集多不代表哪个"更对"——本构件不替使用者挑。%s'
                % (len(sets), note, BOUNDARY))


# ============================================================
# 自测
# ============================================================
def _selftest():
    print('=' * 70)
    print('答案集程序（ASP）构件 · 自测')
    print('=' * 70)

    r = run({'program': 'p :- not q. q :- not p.'})
    assert r['verdict'] == 'solved' and r['count'] == 2, r
    assert r['answer_sets'][0]['atoms'] == ['p'], r['answer_sets']
    print('✅ 经典二选一：p :- not q. q :- not p. → 两个答案集 {p} 与 {q}')

    r = run({'program': 'p :- not p.'})
    assert r['verdict'] == 'no_answer_set', r
    print('✅ 自相矛盾的正规规则（p :- not p.）→ 一个答案集都没有（确定结论）')

    r = run({'program': 'p :- q. q :- p.'})
    assert r['verdict'] == 'solved' and r['count'] == 1 \
        and r['answer_sets'][0]['atoms'] == [], r
    print('✅ 没有基础的环（p :- q. q :- p.）→ 空集是唯一答案集')

    r = run({'program': 'p :- not q. q.'})
    assert r['count'] == 1 and r['answer_sets'][0]['atoms'] == ['q'], r
    print('✅ 否定即失败看事实：p :- not q. q. → {q}（p 被 q 顶掉）')

    r = run({'program': 'a. b :- a. c :- b, not d.'})
    assert r['count'] == 1 and r['answer_sets'][0]['atoms'] == ['a', 'b', 'c'], r
    sup = r['answer_sets'][0]['support']
    assert sup['a'] == 'a.' and sup['b'] == 'b :- a.', sup
    print('✅ 推导依据逐条给出：%s' % sup)

    r = run({'program': 'a. b. :- a, b.'})
    assert r['verdict'] == 'no_answer_set', r
    print('✅ 完整性约束：a. b. :- a, b. → 约束被破，没有答案集')

    r = run({'mode': 'query', 'program': 'p :- not q. q :- not p.', 'query': 'p'})
    assert r['verdict'] == 'in_some' and '轻信论' in r['boundary'], r
    r = run({'mode': 'query', 'program': 'a. b :- a.', 'query': 'b'})
    assert r['verdict'] == 'in_all', r
    r = run({'mode': 'query', 'program': 'a.', 'query': 'b'})
    assert r['verdict'] == 'input_pending', r
    print('✅ 问某个原子：只在部分答案集成立 → in_some；每个都成立 → in_all；'
          '没出现过的原子 → input_pending')

    r = run({'program': '赢 :- not 输. 输 :- not 赢.'})
    assert r['count'] == 2, r
    print('✅ 原子名认汉字（赢 :- not 输. 输 :- not 赢. → 两个答案集）')

    assert run({'program': 'p :- '})['verdict'] == 'parse_error'
    assert run({'program': ':- .'})['verdict'] == 'parse_error'
    assert run({})['verdict'] == 'input_pending'
    assert run({'program': 'p', 'mode': 'xxx'})['verdict'] == 'input_pending'
    print('✅ 边界：写坏的规则/空程序/坏 mode → parse_error / input_pending（不猜）')

    print('=' * 70)
    print('答案集程序（ASP）构件自测：全部通过 ✅')
    print('=' * 70)


if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass
    _selftest()
