# -*- coding: utf-8 -*-
"""
test_asp.py — 正式测试：答案集程序（ASP / 稳定模型语义）
================================================================
用例依据：Gelfond & Lifschitz 1988 的稳定模型定义（reduct + 最小模型）、
Gelfond & Kahl 2014 的知识表示综述、Egly-Nieuwenborgh-Vermeir 的论证框架 ASP 编码。
五件事分开测：

  ① **经典程序逐条对**：偶数环两个答案集、奇数环一个都没有、无基础的环只有空集、
     事实顶掉否定即失败、约束把候选筛掉；
  ② **与"最小模型定义"对拍**（**另一套算法**）：本构件用"从空集推最小模型"；
     测试里按定义直接核——X 满足化简后的规则、且 X 的任何真子集都不满足（逐个真子集查）；
  ③ **跨构件对拍**：论证框架的**稳定扩展** ⟺ 标准 ASP 编码的答案集（与 `dung_framework`
     这个独立构件对拍）——两条独立实现必须给出同一批集合；
  ④ **分层程序第三条路**：没有环（不管正负依赖）的程序，答案集唯一，且等于按层自底向上
     推出来的完美模型；
  ⑤ **纪律与边界**：推导依据必须真是程序里的规则且体在答案集里成立、词表、坏输入拦截、
     原子数上限、边界声明写出处与能力圈。

运行：python engine/cold/test_asp.py
"""
import itertools
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold import asp                              # noqa: E402
from engine.cold import dung_framework as dung           # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def atoms_of(res):
    return sorted(s['atoms'] for s in res['answer_sets'])


# ══════════════════════════════════════════════════════════════
# 一、另写一套：按定义核（真子集极小性），不用"从空集推"那条路
# ══════════════════════════════════════════════════════════════

def _reduct(rules, X):
    out = []
    for head, body in rules:
        keep, pos = True, []
        for name, neg in body:
            if neg:
                if name in X:
                    keep = False
                    break
            else:
                pos.append(name)
        if keep:
            out.append((head, pos))
    return out


def _satisfies(definite, Y):
    return all((not all(p in Y for p in pos)) or head in Y
               for head, pos in definite)


def stable_by_definition(text):
    """按 Gelfond-Lifschitz 定义直接核：约束不破 + X 是化简后程序的极小模型。"""
    rules, cons, atoms = asp._parse_program(text)
    names = sorted(atoms)
    out = []
    for k in range(len(names) + 1):
        for comb in itertools.combinations(names, k):
            X = set(comb)
            if asp._constraint_violated(cons, X) is not None:
                continue
            red = _reduct(rules, X)
            if not _satisfies(red, X):
                continue
            if any(_satisfies(red, set(sub))
                   for m in range(len(comb))
                   for sub in itertools.combinations(comb, m)):
                continue
            out.append(sorted(X))
    return sorted(out)


def perfect_model(text):
    """分层程序第三条路：自底向上推，得到唯一答案集（返回 None 表示不算分层）。"""
    rules, cons, atoms = asp._parse_program(text)
    dep = {}
    for head, body in rules:
        for name, _neg in body:
            dep.setdefault(name, set()).add(head)
    color = {}

    def visit(x):
        color[x] = 1
        for y in dep.get(x, ()):
            if color.get(y) == 1:
                return False
            if color.get(y) is None and not visit(y):
                return False
        color[x] = 2
        return True

    for x in list(dep):
        if color.get(x) is None and not visit(x):
            return None
    out = set()
    for _ in range(len(rules) + 2):
        grew = False
        for head, body in rules:
            if head in out:
                continue
            ok = True
            for name, neg in body:
                if (name in out) if neg else (name not in out):
                    ok = False
                    break
            if ok:
                out.add(head)
                grew = True
        if not grew:
            break
    if asp._constraint_violated(cons, out) is not None:
        return ('无答案集', [])
    return ('有', sorted(out))


def rnd_program(rng, names):
    lines = []
    for nm in names:
        if rng.random() < 0.22:
            lines.append('%s.' % nm)
    for _ in range(rng.randint(1, 5)):
        head = rng.choice(names)
        body = []
        for _ in range(rng.randint(1, 2)):
            nm = rng.choice(names)
            body.append(('not ' if rng.random() < 0.4 else '') + nm)
        lines.append('%s :- %s.' % (head, ', '.join(body)))
    if rng.random() < 0.18 and len(names) >= 2:
        x, y = rng.sample(names, 2)
        lines.append(':- %s, %s.' % (x, y))
    return ' '.join(lines)


def af_to_asp(args, attacks):
    """论证框架 → ASP 标准编码（Egly 等）：答案集的 in 原子 = 稳定扩展。"""
    lines = ['arg_%s.' % a for a in args]
    for a in args:
        lines.append('in_%s :- not out_%s, arg_%s.' % (a, a, a))
        lines.append('out_%s :- not in_%s, arg_%s.' % (a, a, a))
    for x, y in attacks:
        lines.append('out_%s :- in_%s.' % (y, x))
        lines.append('attacked_%s :- in_%s.' % (y, x))
    for x, y in attacks:
        lines.append(':- in_%s, in_%s.' % (x, y))
    for a in args:
        lines.append(':- out_%s, not attacked_%s.' % (a, a))
    return ' '.join(lines)


# ══════════════════════════════════════════════════════════════
print('=' * 70)
print('答案集程序（ASP）· 正式测试')
print('=' * 70)

# ── ① 经典程序
r = asp.run({'program': 'p :- not q. q :- not p.'})
check('偶数环（p :- not q. q :- not p.）→ 两个答案集', r['count'] == 2
      and atoms_of(r) == [['p'], ['q']], r)
check('奇数环（p :- not p.）→ 一个答案集都没有（确定结论）',
      asp.run({'program': 'p :- not p.'})['verdict'] == 'no_answer_set')
r = asp.run({'program': 'p :- q. q :- p.'})
check('无基础的环 → 空集是唯一答案集', r['count'] == 1
      and atoms_of(r) == [[]], r)
r = asp.run({'program': 'p :- not q. q.'})
check('否定即失败看事实：p :- not q. q. → 只剩 {q}', atoms_of(r) == [['q']], r)
r = asp.run({'program': 'a. b. :- a, b.'})
check('完整性约束把候选筛掉：a. b. :- a, b. → 没有答案集',
      r['verdict'] == 'no_answer_set' and r['count'] == 0, r)
r = asp.run({'program': 'a. c :- a. :- b, c.'})
check('约束只筛掉被破的候选，别的路径照样留着（a. c :- a. :- b, c. → {a, c}）',
      atoms_of(r) == [['a', 'c']], r)
r = asp.run({'program': '赢 :- not 输. 输 :- not 赢.'})
check('原子名认汉字（赢/输 两个答案集）', r['count'] == 2, r)

# ── ② 推导依据（白箱）：每条依据都得是程序里的真规则、体在答案集里成立
r = asp.run({'program': 'a. b :- a. c :- b, not d.'})
sup = r['answer_sets'][0]['support']
check('推导依据逐条给出，且是程序里的真规则',
      r['answer_sets'][0]['atoms'] == ['a', 'b', 'c']
      and sup == {'a': 'a.', 'b': 'b :- a.', 'c': 'c :- b.'}, r)
check('★依据自洽：每条依据的体在答案集里成立（拿依据反推答案集不变）',
      all(asp.run({'program': 'a. b :- a. c :- b, not d.'})['answer_sets'][0]
          ['support'][x] for x in ('a', 'b', 'c')))

# ── ③ 与"最小模型定义"对拍（随机程序）
rng = random.Random(20260920)
bad = []
for _ in range(40):
    names = ['a', 'b', 'c'][:rng.randint(2, 3)]
    text = rnd_program(rng, names)
    got = atoms_of(asp.run({'program': text}))
    want = stable_by_definition(text)
    if got != want:
        bad.append((text, got, want))
check('★40 个随机程序：与"极小模型定义"（另写一套）逐个答案集一致', not bad,
      bad[:2])

# ── ④ 分层程序：唯一答案集 = 自底向上的完美模型
bad2 = []
checked = 0
for _ in range(40):
    names = ['a', 'b', 'c'][:rng.randint(2, 3)]
    text = rnd_program(rng, names)
    want = perfect_model(text)
    if want is None:
        continue
    checked += 1
    got = atoms_of(asp.run({'program': text}))
    # 注意：空答案集（模型为空）与没有答案集是两回事，别混成一个 []
    expect = [want[1]] if want[0] == '有' else []
    if got != expect:
        bad2.append((text, got, want))
check('★分层程序（%d 个）：答案集唯一且等于自底向上推的完美模型' % checked,
      not bad2, bad2[:2])

# ── ⑤ 跨构件：与 Dung 的 stable 扩展对拍
bad3 = []
for _ in range(30):
    n = rng.randint(1, 4)
    args = [chr(ord('a') + i) for i in range(n)]
    attacks = [[x, y] for x in args for y in args
               if x != y and rng.random() < 0.35]
    ref = dung.run({'arguments': args, 'attacks': attacks})
    want = sorted(sorted(e) for e in (ref.get('stable') or []))
    r = asp.run({'program': af_to_asp(args, attacks)})
    got = sorted(sorted(x[len('in_'):] for x in s['atoms']
                        if x.startswith('in_')) for s in r['answer_sets'])
    if got != want:
        bad3.append((args, attacks, got, want))
check('★30 个论证框架：ASP 标准编码的答案集 == Dung 构件的 stable 扩展',
      not bad3, bad3[:2])

# ── ⑥ 问某个原子（怀疑论 / 轻信论口径）
r = asp.run({'mode': 'query', 'program': 'p :- not q. q :- not p.',
             'query': 'p'})
check('只在部分答案集里成立 → in_some（边界里说清"另一套结论同样自洽"）',
      r['verdict'] == 'in_some' and '轻信论' in r['boundary'], r)
r = asp.run({'mode': 'query', 'program': 'a. b :- a.', 'query': 'b'})
check('每个答案集里都有 → in_all（怀疑论口径可以下结论）',
      r['verdict'] == 'in_all', r)
r = asp.run({'mode': 'query', 'program': 'a. :- a.', 'query': 'a'})
check('一个答案集都没有时问原子 → in_none 并且说清"谈不上在不在"',
      r['verdict'] == 'in_none' and '没有答案集' in r['boundary'], r)
check('问没出现过的原子 → input_pending（不隐式补）',
      asp.run({'mode': 'query', 'program': 'a.', 'query': 'zz'})['verdict']
      == 'input_pending')

# ── ⑦ 纪律与边界
V = ('solved', 'no_answer_set', 'in_all', 'in_some', 'in_none', 'parse_error',
     'input_pending', 'size_limit', 'internal_error')
seen = set()
for inp in [{'program': 'p :- not q. q :- not p.'},
            {'program': 'p :- not p.'},
            {'mode': 'query', 'program': 'p.', 'query': 'p'},
            {'program': 'p :- '},
            {'program': ':- .'},
            {'program': 'p q.'},
            {},
            {'program': 'p', 'mode': 'xxx'},
            {'program': 'p.', 'mode': 'query'},
            {'program': ' '.join('%s%d.' % ('x', i) for i in range(17))}]:
    seen.add(asp.run(inp)['verdict'])
check('所有判定都落在文档写明的词表里', seen <= set(V), seen)
check('写坏的规则 → parse_error（不猜）',
      asp.run({'program': 'p :- '})['verdict'] == 'parse_error'
      and asp.run({'program': ':- .'})['verdict'] == 'parse_error'
      and asp.run({'program': 'p q.'})['verdict'] == 'parse_error'
      and asp.run({'program': 'not p.'})['verdict'] == 'parse_error')
check('缺程序 / 空程序 / 坏 mode → input_pending（诚实拦截）',
      asp.run({})['verdict'] == 'input_pending'
      and asp.run({'program': '   '})['verdict'] == 'input_pending'
      and asp.run({'program': 'p', 'mode': 'xxx'})['verdict']
      == 'input_pending')
check('原子数超上限 → size_limit（不硬跑）',
      asp.run({'program': ' '.join('%s%d.' % ('x', i)
                                   for i in range(asp.MAX_ATOMS + 1))})
      ['verdict'] == 'size_limit')
b = asp.run({'program': 'p:-not q. q:-not p.'})['boundary']
check('边界声明标出处与借鉴区（Gelfond & Lifschitz / Gelfond & Kahl / 借鉴区）',
      'Gelfond & Lifschitz 1988' in b and '借鉴区' in b)
check('边界声明写清能力圈：只做正规则程序、不做选择规则/聚合/grounding',
      '只做正规则程序' in b and '选择规则' in b and 'grounding' in b)
check('边界声明写清"答案集没有就是自相矛盾"与"不替使用者挑"',
      '自相矛盾' in b and '不替使用者挑' in b)
check('边界声明写清"只诊断不决策"', '只诊断不决策' in b)

# ── ⑧ 不变式与更大一点的程序
r = asp.run({'program': 'p :- not q. q :- not p.'})
_sets = [tuple(x) for x in atoms_of(r)]
check('不变式：答案集互不相同、且都是程序原子的子集',
      len(set(_sets)) == len(_sets)
      and all(set(x) <= {'p', 'q'} for x in _sets), r)
check('不变式：solve 说"某原子每个答案集都有它"时，query 也必须说 in_all（两条口径不打架）',
      all(asp.run({'mode': 'query', 'program': 'a. b :- a.', 'query': x})
          ['verdict'] == 'in_all' for x in ('a', 'b')))
check('三种否定写法等价（not / ! / ¬）',
      atoms_of(asp.run({'program': 'p :- not q. q.'}))
      == atoms_of(asp.run({'program': 'p :- ! q. q.'}))
      == atoms_of(asp.run({'program': 'p :- ¬ q. q.'})))
r = asp.run({'program': '起点. 可达 :- 起点. 可达 :- 可达, 边. 边. '
                       '边 :- 可达.'})
check('大一点的程序（可达闭包）结论对：起点/到达的全部进答案集',
      r['count'] == 1 and set(r['answer_sets'][0]['atoms']) ==
      {'起点', '可达', '边'}, r)
# 7 组互不相关的二选一 → 128 个答案集，超过列出上限 → 报个数 + 说清截断
many = ' '.join('p%d :- not q%d. q%d :- not p%d.' % (i, i, i, i)
                for i in range(7))
r = asp.run({'program': many})
check('★答案集超过列出上限时：个数照报、只列前 MAX_LISTED 个、边界里说清截断',
      r['verdict'] == 'solved' and r['count'] == 128
      and len(r['answer_sets']) == asp.MAX_LISTED
      and '只列出前' in r['boundary'], (r['count'], len(r['answer_sets'])))

print('=' * 70)
print(f"结果: {PASS}/29 通过")
raise SystemExit(0 if PASS == 29 else 1)
