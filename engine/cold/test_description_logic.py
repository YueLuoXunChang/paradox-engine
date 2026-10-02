# -*- coding: utf-8 -*-
"""
test_description_logic.py — 正式测试：描述逻辑 ALC（概念可满足 / 包含 / 等价 / 分类）
================================================================================
用例依据：ALC 的表列判定（Baader & Sattler 2000 的规则集与阻塞终止性、
Horrocks-Sattler-Tobies 1999 的 ALC 表列定理）。四件事分开测：

  ① **交出的模型是不是真模型**：构件报"可满足"时会交一棵规范模型（节点标号 + 角色边
     + blocked 标记）。本文件**另写一套语义核算器**把模型还原成解释——blocked 节点按
     祖先顶上、标号里的原子给真值、后继按边给——再用**另写的概念求值函数**核算
     "根满足被测概念、每个元素满足本体公理"。表列要是偷偷漏掉了某条约束，这里会当场
     露馅（不靠构件自己的判定逻辑复核自己）。
  ② **判"不可满足"不许冤枉**：判"不可满足"是确定结论，方向最危险。本文件内置一个
     **穷举有穷解释**的对拍器（论域 ≤2，独立实现的一阶语义），固定用例逐条核对：
     表列说撞车，穷举就不该找出模型。
  ③ **标准等式对不对**：∃R.(A⊔B) ≡ ∃R.A ⊔ ∃R.B、∀R.(A⊓B) ≡ ∀R.A ⊓ ∀R.B、
     ¬∃R.A ≡ ∀R.¬A、德摩根，以及"不出存在要求"的 ∀R.A ⊑ ∃R.A 不成立这些经典事实。
  ④ **纪律与边界**：循环本体必须收口（子集阻塞）、出处标在边界里、坏输入诚实拦截、
     节点上限超了报 size_limit 不硬跑、不越界假装做 ABox。

运行：python engine/cold/test_description_logic.py
"""
import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold import description_logic as dl  # noqa: E402

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


# ══════════════════════════════════════════════════════════════
# 一、另写一套：把交出的模型当解释来核算（语义自检，不碰构件的表列）
# ══════════════════════════════════════════════════════════════

def _parse(text):
    return dl._nnf(dl._parse_concept(text))


def _as_model(res, formula, tbox):
    """
    核算构件交出的模型：返回 (是否真是模型, 说明)。
    formula 是被测的那条概念（可满足用 concept，包含用 sub⊓¬super，相交用 sub⊓super）。
    """
    if res['verdict'] not in ('satisfiable', 'not_subsumed', 'not_disjoint'):
        return False, '这条判定不交模型'
    m = res['model']
    if not m or not m['nodes']:
        return False, '模型是空的'
    ids = [n['id'] for n in m['nodes']]
    if len(set(ids)) != len(ids):
        return False, '节点 id 重复'
    label = {}
    for n in m['nodes']:
        try:
            label[n['id']] = set(_parse(c) for c in n['concepts'])
        except Exception as e:  # noqa: BLE001——模型里的标号必须能读回来
            return False, '标号读不回来（%s）' % e
    kids, parent = {i: [] for i in ids}, {i: None for i in ids}
    for e in m['edges']:
        if e['from'] not in label or e['to'] not in label:
            return False, '边指向不存在的节点'
        kids[e['from']].append((e['to'], e['role']))
        parent[e['to']] = e['from']

    def ancestors(i):
        p, out = parent[i], []
        while p is not None:
            out.append(p)
            p = parent[p]
        return out

    # blocked 的节点必须真有祖先把它装下（否则这标记是瞎写）
    alias = {}
    for n in m['nodes']:
        i = n['id']
        if not n['blocked']:
            alias[i] = i
            continue
        cand = [a for a in ancestors(i) if label[i] <= label[a]]
        if not cand:
            return False, '节点 %s 标 blocked 但没有装得下它的祖先' % i
        alias[i] = alias[cand[0]]

    def rep(i):
        seen = set()
        while alias[i] != i:
            if i in seen:
                return None
            seen.add(i)
            i = alias[i]
        return i

    elems = sorted({rep(i) for i in ids})
    succ = {e: [] for e in elems}
    for i in ids:
        r = rep(i)
        if r is None:
            return False, '阻塞回接成环'
        for (c, role) in kids[i]:
            if rep(c) is None:
                return False, '阻塞回接成环'
            if (rep(c), role) not in succ[r]:
                succ[r].append((rep(c), role))
    atoms = {e: set() for e in elems}
    for i in ids:
        e = rep(i)
        for c in label[i]:
            if c[0] == 'lit' and not c[2]:
                atoms[e].add(c[1])
    # 标号里说 ¬A 的元素，取的代表元素上就不许有 A
    for i in ids:
        e = rep(i)
        for c in label[i]:
            if c[0] == 'lit' and c[2] and c[1] in atoms[e]:
                return False, '元素 %s 同时要 A 与 ¬A' % e
    if not elems or rep(0) is None:
        return False, '根没落到元素上'

    def value(node):
        k = node[0]
        if k == 'top':
            return set(elems)
        if k == 'bot':
            return set()
        if k == 'lit':
            return {e for e in elems
                    if (node[1] in atoms[e]) != bool(node[2])}
        if k == 'and':
            return value(node[1]) & value(node[2])
        if k == 'or':
            return value(node[1]) | value(node[2])
        if k == 'ex':
            return {e for e in elems
                    if any(r == node[1] and y in value(node[2])
                           for (y, r) in succ[e])}
        if k == 'all':
            return {e for e in elems
                    if all(y in value(node[2])
                           for (y, r) in succ[e] if r == node[1])}
        return set()

    root = rep(0)
    if root not in value(_parse(formula)):
        return False, '根元素不满足被测概念'
    for line in (tbox or []):
        if '⊑' in line:
            a, _, b = line.partition('⊑')
        else:
            a, _, b = line.partition('≡')
            if not value(_parse(a)) <= value(_parse(b)):
                return False, '公理 %s 的左到右不成立' % line
        if not value(_parse(a)) <= value(_parse(b)):
            return False, '公理 %s 不成立' % line
    return True, '模型成立（%d 个元素）' % len(elems)


# ══════════════════════════════════════════════════════════════
# 二、另写一套：穷举有穷解释（论域 ≤2）——专门压"判不可满足"这个危险方向
# ══════════════════════════════════════════════════════════════

def _fo_value(node, dom, atoms, role):
    """一阶语义下这个概念为真的元素集合（自己写的求值，与表列无关）。"""
    k = node[0]
    if k == 'top':
        return set(dom)
    if k == 'bot':
        return set()
    if k == 'lit':
        return {x for x in dom if (x in atoms[node[1]]) != bool(node[2])}
    if k == 'and':
        return _fo_value(node[1], dom, atoms, role) & _fo_value(
            node[2], dom, atoms, role)
    if k == 'or':
        return _fo_value(node[1], dom, atoms, role) | _fo_value(
            node[2], dom, atoms, role)
    if k == 'ex':
        s = _fo_value(node[2], dom, atoms, role)
        return {x for x in dom if any((x, y) in role for y in s)}
    if k == 'all':
        s = _fo_value(node[2], dom, atoms, role)
        return {x for x in dom if all((x, y) not in role or y in s
                                      for y in dom)}
    return set()


def _fo_sat(concept, tbox, names, maxn=2):
    """穷举论域 1..maxn 的全部解释，看有没有模型。"""
    parsed = []
    for line in tbox:
        a, _, b = line.partition('⊑')
        parsed.append((dl._nnf(dl._parse_concept(a)),
                       dl._nnf(dl._parse_concept(b))))
    tbox = parsed
    for n in range(1, maxn + 1):
        dom = list(range(n))
        pairs = sorted(itertools.product(dom, repeat=2))
        subs = [list(itertools.chain.from_iterable(
            itertools.combinations(dom, r) for r in range(n + 1)))] * len(names)
        for combo in itertools.product(*subs):
            atoms = {nm: set(s) for nm, s in zip(names, combo)}
            for bits in range(1 << len(pairs)):
                role = {pairs[i] for i in range(len(pairs)) if bits >> i & 1}
                if not all(_fo_value(a, dom, atoms, role)
                           <= _fo_value(b, dom, atoms, role)
                           for a, b in tbox):
                    continue
                if _fo_value(concept, dom, atoms, role):
                    return True
    return False


# ══════════════════════════════════════════════════════════════
# 三、基本判定 + 模型自检
# ══════════════════════════════════════════════════════════════
print('=' * 70)
print('描述逻辑 ALC · 正式测试')
print('=' * 70)

r = dl.run({'mode': 'satisfiable', 'concept': 'A ⊓ ¬A'})
check('自相矛盾 → 不可满足', r['verdict'] == 'unsatisfiable', r)

r = dl.run({'mode': 'satisfiable', 'concept': '⊤'})
check('⊤ 可满足', r['verdict'] == 'satisfiable', r)
check('⊥ 不可满足',
      dl.run({'mode': 'satisfiable', 'concept': '⊥'})['verdict']
      == 'unsatisfiable')

r = dl.run({'mode': 'satisfiable', 'concept': 'A ⊓ ∃R.(B ⊓ ¬C)'})
check('A ⊓ ∃R.(B ⊓ ¬C) 可满足', r['verdict'] == 'satisfiable', r)
ok, why = _as_model(r, 'A ⊓ ∃R.(B ⊓ ¬C)', [])
check('★交出的模型用另写语义器核算成立', ok, why)

check('∀R.A ⊓ ∃R.¬A → 不可满足（∀ 与 ∃ 撞车）',
      dl.run({'mode': 'satisfiable',
              'concept': '∀R.A ⊓ ∃R.¬A'})['verdict'] == 'unsatisfiable')
check('∀R.⊥ ⊓ ∃R.⊤ → 不可满足',
      dl.run({'mode': 'satisfiable',
              'concept': '∀R.⊥ ⊓ ∃R.⊤'})['verdict'] == 'unsatisfiable')
check('∀R.⊥ → 可满足（没有 R 后继就空真）',
      dl.run({'mode': 'satisfiable', 'concept': '∀R.⊥'})['verdict']
      == 'satisfiable')


# ══════════════════════════════════════════════════════════════
# 四、标准等式（ALC 经典事实）
# ══════════════════════════════════════════════════════════════
def equiv(a, b, tbox=None):
    return dl.run({'mode': 'equivalent', 'c1': a, 'c2': b,
                   'tbox': tbox})['verdict'] == 'equivalent'


def subsumes(a, b, tbox=None):
    return dl.run({'mode': 'subsumption', 'sub': a, 'super': b,
                   'tbox': tbox})['verdict'] == 'subsumed'


check('∃R.(A ⊔ B) ≡ ∃R.A ⊔ ∃R.B', equiv('∃R.(A ⊔ B)', '∃R.A ⊔ ∃R.B'))
check('∀R.(A ⊓ B) ≡ ∀R.A ⊓ ∀R.B', equiv('∀R.(A ⊓ B)', '∀R.A ⊓ ∀R.B'))
check('¬∃R.A ≡ ∀R.¬A', equiv('¬∃R.A', '∀R.¬A'))
check('¬(A ⊓ B) ≡ ¬A ⊔ ¬B（德摩根）', equiv('¬(A ⊓ B)', '¬A ⊔ ¬B'))
check('A ≡ ¬¬A', equiv('A', '¬¬A'))
check('A ⊓ B ⊑ A，且 A ⊑ A ⊔ B',
      subsumes('A ⊓ B', 'A') and subsumes('A', 'A ⊔ B'))
check('∃R.A ⊔ ∃R.B ⊑ ∃R.(A ⊔ B)',
      subsumes('∃R.A ⊔ ∃R.B', '∃R.(A ⊔ B)'))
check('A ⊑ B 不成立（无本体）',
      dl.run({'mode': 'subsumption', 'sub': 'A',
              'super': 'B'})['verdict'] == 'not_subsumed')
r = dl.run({'mode': 'subsumption', 'sub': 'A', 'super': 'B'})
ok, why = _as_model(r, 'A ⊓ ¬B', [])
check('★不包含时交出的反例模型用语义器核算成立', ok, why)
check('∀R.A ⊑ ∃R.A 不成立（∀ 不出存在要求）',
      dl.run({'mode': 'subsumption', 'sub': '∀R.A',
              'super': '∃R.A'})['verdict'] == 'not_subsumed')
check('∃R.A ⊑ ∀R.A 不成立',
      dl.run({'mode': 'subsumption', 'sub': '∃R.A',
              'super': '∀R.A'})['verdict'] == 'not_subsumed')
check('A ≡ B 不成立（无本体）',
      dl.run({'mode': 'equivalent', 'c1': 'A',
              'c2': 'B'})['verdict'] == 'not_equivalent')


# ══════════════════════════════════════════════════════════════
# 五、本体（TBox）推理
# ══════════════════════════════════════════════════════════════
T = ['Woman ≡ Person ⊓ Female', 'Man ≡ Person ⊓ ¬Woman',
     'Lecturer ≡ Person ⊓ ∃teaches.Course']

check('本体下 Woman ⊑ Person', subsumes('Woman', 'Person', T))
check('本体下 Person ⊑ Woman 不成立（有反例模型）',
      dl.run({'mode': 'subsumption', 'sub': 'Person', 'super': 'Woman',
              'tbox': T})['verdict'] == 'not_subsumed')
check('A ⊑ B、B ⊑ C ⇒ A ⊑ C（链条）',
      subsumes('A', 'C', ['A ⊑ B', 'B ⊑ C']))
check('A ⊑ B、B ⊑ C ⇏ C ⊑ A',
      dl.run({'mode': 'subsumption', 'sub': 'C', 'super': 'A',
              'tbox': ['A ⊑ B', 'B ⊑ C']})['verdict'] == 'not_subsumed')
check('A ⊑ B、B ⊑ ¬A ⇒ A 不可满足',
      dl.run({'mode': 'satisfiable', 'concept': 'A',
              'tbox': ['A ⊑ B', 'B ⊑ ¬A']})['verdict'] == 'unsatisfiable')
check('⊤ ⊑ A ⇒ ¬A 不可满足',
      dl.run({'mode': 'satisfiable', 'concept': '¬A',
              'tbox': ['⊤ ⊑ A']})['verdict'] == 'unsatisfiable')
check('A ≡ B ⇒ A 与 ¬B 不相交',
      dl.run({'mode': 'disjoint', 'sub': 'A', 'super': '¬B',
              'tbox': ['A ≡ B']})['verdict'] == 'disjoint')
check('本体把 ∃ 收束进 ∀：A ⊑ ∃R.B 下 A ⊓ ∀R.¬B 不可满足',
      dl.run({'mode': 'satisfiable', 'concept': 'A ⊓ ∀R.¬B',
              'tbox': ['A ⊑ ∃R.B']})['verdict'] == 'unsatisfiable')


# ══════════════════════════════════════════════════════════════
# 六、循环本体必须收口（子集阻塞）
# ══════════════════════════════════════════════════════════════
r = dl.run({'mode': 'satisfiable', 'concept': 'A', 'tbox': ['A ≡ ∃R.A']})
check('A ≡ ∃R.A（要无限模型）也判得出来：可满足',
      r['verdict'] == 'satisfiable', r)
check('★循环本体的模型靠阻塞收口（有 blocked 节点，不是无限展开）',
      any(n['blocked'] for n in r['model']['nodes']), r['model'])
ok, why = _as_model(r, 'A', ['A ≡ ∃R.A'])
check('★循环本体的模型用语义器核算仍成立（阻塞没吃掉约束）', ok, why)

r = dl.run({'mode': 'satisfiable', 'concept': 'A',
            'tbox': ['A ≡ ∃R.B', 'B ≡ ∃R.A']})
check('互相循环 A ≡ ∃R.B、B ≡ ∃R.A 也收口', r['verdict'] == 'satisfiable', r)
check('互相循环的模型也过语义核算',
      _as_model(r, 'A', ['A ≡ ∃R.B', 'B ≡ ∃R.A'])[0])

r = dl.run({'mode': 'satisfiable', 'concept': 'A',
            'tbox': ['A ≡ ∃R.A ⊓ B']})
check('A ≡ ∃R.A ⊓ B 收口且可满足', r['verdict'] == 'satisfiable', r)
ok, why = _as_model(r, 'A', ['A ≡ ∃R.A ⊓ B'])
check('★该模型语义核算成立', ok, why)

check('循环 + 夹心：A ≡ ∃R.A、A ⊑ B、B ⊑ C 仍收口',
      dl.run({'mode': 'satisfiable', 'concept': 'A',
              'tbox': ['A ≡ ∃R.A', 'A ⊑ B',
                       'B ⊑ C']})['verdict'] == 'satisfiable')
check('A ⊑ ∃R.A 下 A ⊓ ∀R.¬A 不可满足（循环里照样查得出撞车）',
      dl.run({'mode': 'satisfiable', 'concept': 'A ⊓ ∀R.¬A',
              'tbox': ['A ⊑ ∃R.A']})['verdict'] == 'unsatisfiable')


# ══════════════════════════════════════════════════════════════
# 七、不相交 / 分类
# ══════════════════════════════════════════════════════════════
check('A 与 ¬A 不相交',
      dl.run({'mode': 'disjoint', 'sub': 'A',
              'super': '¬A'})['verdict'] == 'disjoint')
check('男人与女人不相交（本体下）',
      dl.run({'mode': 'disjoint', 'sub': 'Man', 'super': 'Woman',
              'tbox': T})['verdict'] == 'disjoint')
r = dl.run({'mode': 'disjoint', 'sub': 'A', 'super': 'B'})
check('A 与 B 不是不相交', r['verdict'] == 'not_disjoint', r)
ok, why = _as_model(r, 'A ⊓ B', [])
check('★不相交判否时，交出的模型（A⊓B 成立）过语义核算', ok, why)

r = dl.run({'mode': 'classify', 'tbox': T})
cls = r['classify'] or {}
check('分类：判定成立且原子齐全',
      r['verdict'] == 'classified'
      and cls.get('atoms') == ['Course', 'Female', 'Lecturer', 'Man',
                               'Person', 'Woman'], r)
check('分类：等价类各自独立（这组公理下没有互相等价的）',
      cls.get('equivalence_classes') == [['Course'], ['Female'], ['Lecturer'],
                                         ['Man'], ['Person'], ['Woman']], cls)
check('分类：严格包含含 Woman⊑Person、Woman⊑Female、Man⊑Person、Lecturer⊑Person',
      {tuple(x) for x in cls.get('strict_subsumptions', [])}
      == {('Woman', 'Person'), ('Woman', 'Female'), ('Man', 'Person'),
          ('Lecturer', 'Person')}, cls)
check('分类：原子超 8 个 → size_limit（不硬跑）',
      dl.run({'mode': 'classify',
              'tbox': ['A0 ⊑ A1', 'A1 ⊑ A2', 'A2 ⊑ A3', 'A3 ⊑ A4',
                       'A4 ⊑ A5', 'A5 ⊑ A6', 'A6 ⊑ A7',
                       'A7 ⊑ A8']})['verdict'] == 'size_limit')


# ══════════════════════════════════════════════════════════════
# 八、穷举解释对拍（判"不可满足"不许冤枉）
# ══════════════════════════════════════════════════════════════
PAIRS = [
    ('A ⊓ ¬A', []),
    ('∀R.A ⊓ ∃R.¬A', []),
    ('A ⊓ ∃R.B', []),
    ('∃R.(A ⊓ B) ⊓ ∀R.¬A', []),
    ('¬A ⊓ ∀R.A', ['⊤ ⊑ ∃R.A']),
    ('A ⊓ ∀R.¬B', ['A ⊑ ∃R.B']),
    ('B ⊓ ∀R.¬A', ['B ⊑ ∃R.A']),
    ('A ⊓ ¬B', ['A ⊑ B']),
    ('A ⊓ ¬C', ['A ⊑ B', 'B ⊑ C']),
    ('A ⊓ ∃R.(B ⊓ ¬C)', ['A ⊑ ∃R.B']),
]
bad = []
for text, tbox in PAIRS:
    r = dl.run({'mode': 'satisfiable', 'concept': text, 'tbox': tbox})
    names = sorted({'A', 'B', 'C'} if 'C' in text or any('C' in t for t in tbox)
                   else {'A', 'B'})
    got = _fo_sat(_parse(text), tbox, names, maxn=2)
    if r['verdict'] == 'unsatisfiable' and got:
        bad.append((text, tbox))
    if r['verdict'] == 'satisfiable' and not got:
        bad.append((text, tbox, '论域≤2 没找到模型'))
check('★10 条用例与穷举解释（论域 ≤2）不打架', not bad, bad)


# ══════════════════════════════════════════════════════════════
# 九、纪律与边界
# ══════════════════════════════════════════════════════════════
V = ('satisfiable', 'unsatisfiable', 'subsumed', 'not_subsumed', 'equivalent',
     'not_equivalent', 'disjoint', 'not_disjoint', 'classified',
     'parse_error', 'input_pending', 'size_limit', 'internal_error')
seen = set()
for inputs in [{'mode': 'satisfiable', 'concept': 'A ⊓'},
               {'mode': 'satisfiable'},
               {'mode': 'satisfiable', 'concept': 'A', 'tbox': ['A B']},
               {'mode': 'subsumption', 'super': 'A'},
               {'mode': 'equivalent', 'c2': 'A'},
               {'mode': 'classify'},
               {'mode': 'xxx'},
               {'mode': 'satisfiable', 'concept': '∃1.A'},
               {'mode': 'satisfiable', 'concept': 'A', 'max_nodes': 5},
               {'mode': 'satisfiable', 'concept': 'A', 'max_nodes': 60}]:
    seen.add(dl.run(inputs)['verdict'])
check('所有判定都落在文档写明的词表里', seen <= set(V), seen)
check('写坏的概念 → parse_error（不猜）',
      dl.run({'mode': 'satisfiable',
              'concept': 'A ⊓'})['verdict'] == 'parse_error')
check('坏角色名 / 坏公理写法 → parse_error（不猜）',
      dl.run({'mode': 'satisfiable',
              'concept': '∃1.A'})['verdict'] == 'parse_error'
      and dl.run({'mode': 'satisfiable', 'concept': 'A',
                  'tbox': ['A B']})['verdict'] == 'parse_error')
check('缺参 → input_pending（诚实拦截，不瞎补）',
      dl.run({'mode': 'satisfiable'})['verdict'] == 'input_pending'
      and dl.run({'mode': 'subsumption', 'super': 'A'})['verdict']
      == 'input_pending'
      and dl.run({'mode': 'equivalent', 'c2': 'A'})['verdict']
      == 'input_pending'
      and dl.run({'mode': 'classify'})['verdict'] == 'input_pending')
check('节点上限超了 → size_limit（不硬跑）',
      dl.run({'mode': 'satisfiable',
              'concept': '∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.A',
              'max_nodes': 10})['verdict'] == 'size_limit')
deep = dl.run({'mode': 'satisfiable',
               'concept': '∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.∃R.A'})
check('同一深度在默认上限内判得出来（不是一律报 size_limit）',
      deep['verdict'] == 'satisfiable'
      and len(deep['model']['nodes']) == 13, deep['verdict'])
b = dl.run({'mode': 'satisfiable', 'concept': 'A'})['boundary']
check('边界声明标出处与借鉴区（Baader & Sattler / Horrocks / 借鉴区）',
      'Baader & Sattler' in b and 'Horrocks' in b and '借鉴区' in b)
check('边界声明写清能力圈（只做 ALC、不做 ABox、不做数量限制）',
      '只做 ALC' in b and 'ABox' in b and '≥n' in b)
check('边界声明写清"只诊断不决策"', '只诊断不决策' in b)

# 模型标号太长时**明说截断**（不装作给全了——模型是拿来复核的凭据）
_long = dl.run({'mode': 'satisfiable', 'concept': 'A1',
                'tbox': ['⊤ ⊑ A%d' % i for i in range(1, 46)]})
check('★标号超长时模型标 truncated 并在边界里说清',
      _long['verdict'] == 'satisfiable'
      and _long['model'].get('truncated') is True
      and 'truncated' in _long['boundary'], _long['boundary'][:80])
_norm = dl.run({'mode': 'satisfiable', 'concept': 'A ⊓ ∃R.B'})
check('★普通模型不虚标 truncated（没截就不说截了）',
      _norm['model'].get('truncated') is False
      and 'truncated' not in _norm['boundary'])

print('九、口径锚：表列节点上限（硬核度① 判据轴）')
# 这一条钉的是"默认值就是那个常量"＋"参数本身有下限"，而不是靠硬造 400 层展开：
# 造不出超限输入时，硬凑一个假输入比不写更糟。显式给常量与缺省必须**行为一致**。
check('显式给 MAX_NODES 与缺省行为一致（默认值＝常量本身）',
      dl.run({'concept': 'C', 'max_nodes': dl.MAX_NODES})['verdict']
      == dl.run({'concept': 'C'})['verdict'])
check('上限低到参数下限（10）以下 → input_pending（拦参数本身，不硬跑）',
      dl.run({'concept': 'C', 'max_nodes': 2})['verdict'] == 'input_pending')

print('=' * 70)
print(f"结果: {PASS}/59 通过")
raise SystemExit(0 if PASS == 59 else 1)
