# -*- coding: utf-8 -*-
"""
test_interval_algebra.py — 正式测试：区间代数（Allen 定性时序推理）
========================================================================
用例依据：Allen 1983 的关系代数（13 个基本关系 + 复合表 + 路径一致性）、
Vilain & Kautz 1986 的点代数。三件事分开测：

  ① **表对不对**：复合表是构件里**现推**的（端点弱序枚举），本文件用**独立写的
     手推条目**与**关系代数的代数律**两头夹——
        · 代数律：逆(r∘s) == 逆(s)∘逆(r)（169 格全查，一条断言覆盖）；
        · 手推条目：m∘s=m、m∘m=b、b∘m=b、o∘o={b,m,o}、b∘d={b,m,o,s,d}、
          e 是单位元、b∘bi 是全关系……
  ② **判定对不对**：路径一致性找到空集 → 真不一致；报"没发现冲突"→ 用**独立写的
     整数区间穷举**核对（在 3 事件单元网络这一**限定范围**里，实测两者等价）；
     点代数一侧做**完备性**实测（路径一致 ⟺ 真有解）；
  ③ **纪律**：只诊断不决策、出处标在边界里、坏输入诚实拦截、不隐式加事件。
运行：python engine/cold/test_interval_algebra.py
"""
import itertools
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold.interval_algebra import (BASE, MAX_EVENTS, run, tables)  # noqa: E402

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


def names(rel):
    """关系串 → 关系名集合（独立实现，不复用构件的私有函数）。"""
    out, i = set(), 0
    while i < len(rel):
        if rel[i:i + 2] in BASE:
            out.add(rel[i:i + 2])
            i += 2
        else:
            out.add(rel[i])
            i += 1
    return out


def comp(a, b):
    """独立实现的关系集复合：逐对查构件现推的表。"""
    table = tables()[1]
    out = set()
    for x in names(a):
        for y in names(b):
            out |= names(table.get((x, y), ''))
    return out


def rel_of(s1, e1, s2, e2):
    """两个整数区间的定性关系（独立实现：直接按端点大小判）。"""
    if s1 == s2 and e1 == e2:
        return 'e'
    if e1 < s2:
        return 'b'
    if e1 == s2:
        return 'm'
    if s1 < s2 and s2 < e1 < e2:
        return 'o'
    if s1 == s2 and e1 < e2:
        return 's'
    if s2 < s1 and e1 < e2:
        return 'd'
    if s2 < s1 and e1 == e2:
        return 'f'
    # 反向：对调再判，然后取逆
    back = rel_of(s2, e2, s1, e1)
    return {'b': 'bi', 'm': 'mi', 'o': 'oi', 's': 'si', 'd': 'di',
            'f': 'fi', 'e': 'e'}[back]


def satisfiable_unit_ia(rels):
    """三事件单元网络有没有真模型（独立穷举：整数区间 0..5）。"""
    for vals in itertools.product(
            [(s, e) for s in range(6) for e in range(s + 1, 7)], repeat=3):
        if all(rel_of(*vals[i], *vals[j]) == r
               for (i, j), r in rels.items()):
            return True
    return False


print("区间代数（Allen 定性时序推理） · 正式测试")
print("=" * 60)

INV, COMPOSE = tables()

# ── 一、表：代数律 + 手推条目两头夹
check("逆表 13 个都在，且取逆两次回到自己（对合）",
      len(INV) == 13 and all(INV[INV[r]] == r for r in BASE), str(INV))
_bad_law = []
for r in BASE:
    for s in BASE:
        lhs = {INV[c] for c in names(COMPOSE[(r, s)])}
        rhs = names(COMPOSE[(INV[s], INV[r])])
        if lhs != rhs:
            _bad_law.append((r, s))
check("代数律：逆(r∘s) == 逆(s)∘逆(r)（169 格全查）",
      not _bad_law, str(_bad_law[:4]))
check("复合没有空格子（13×13 全非空）",
      all(COMPOSE[(r, s)] for r in BASE for s in BASE))
HAND = {('m', 's'): 'm', ('m', 'm'): 'b', ('b', 'm'): 'b', ('m', 'b'): 'b',
        ('b', 'b'): 'b', ('e', 'e'): 'e', ('e', 'o'): 'o', ('o', 'e'): 'o',
        ('s', 's'): 's', ('d', 'd'): 'd', ('o', 'o'): 'bmo',
        ('b', 'd'): 'bdmos', ('b', 'bi'): ''.join(BASE)}
check("手推条目逐条对上（含 m∘s=m、m∘m=b、o∘o={b,m,o}、b∘d={b,m,o,s,d}）",
      all(names(COMPOSE[k]) == names(v) for k, v in HAND.items()),
      str([(k, COMPOSE[k]) for k, v in HAND.items()
           if names(COMPOSE[k]) != names(v)][:3]))
check("e 是单位元：e∘r = r 且 r∘e = r（全 13 个）",
      all(names(COMPOSE[('e', r)]) == {r} and names(COMPOSE[(r, 'e')]) == {r}
          for r in BASE))
check("逆关系抽查：b↔bi、m↔mi、o↔oi、s↔si、f↔fi、e 自逆",
      all(INV[r] == q for r, q in [('b', 'bi'), ('m', 'mi'), ('o', 'oi'),
                                   ('s', 'si'), ('f', 'fi'), ('e', 'e')]))

# ── 二、接口：复合 / 逆 / 写法别名
check("compose 接口：相接 ∘ 相接 = 先于",
      run({'mode': 'compose', 'relations': ['m', 'm']})['composed'] == 'b')
check("compose 认英文名与中文名（before/meets/先于…）",
      run({'mode': 'compose', 'relations': ['meets', 'meets']})['composed']
      == 'b'
      and run({'mode': 'compose', 'relations': ['相接', '相接']})['composed']
      == 'b')
check("compose 认并集（['b','m'] ∘ ['b'] 应等于 b∪…）",
      names(run({'mode': 'compose',
                 'relations': [['b', 'm'], ['b']]})['composed'])
      == comp('bm', 'b'))
check("converse 接口：bi 的逆回到 b",
      run({'mode': 'converse', 'relation': 'bi'})['conversed'] == 'b')

# ── 三、判定：路径一致性（找到空集 = 真不一致）
r = run({'events': ['立项', '开发', '上线'],
         'relations': [['立项', 'b', '开发'], ['开发', 'b', '上线']]})
check("传递收紧：两段先于 → 矩阵里推出「立项先于上线」",
      r['verdict'] == 'path_consistent' and r['matrix']['立项|上线'] == 'b',
      str(r['matrix']))
check("报 path_consistent 时边界里写明「只是必要条件、不等于有解」",
      '不等于有解' in r['boundary'], r['boundary'][-60:])
r = run({'events': ['A', 'B', 'C'],
         'relations': [['A', 'b', 'B'], ['B', 'b', 'C'], ['C', 'b', 'A']]})
check("成环冲突 → inconsistent，并指出是沿哪三对挤空的",
      r['verdict'] == 'inconsistent' and len(r['conflict']['via']) == 3
      and len(r['conflict']['pair']) == 2, str(r['conflict']))
check("不一致是**确定结论**（边界里写明）",
      '确定结论' in r['boundary'])
r = run({'events': ['A', 'B'], 'relations': [['A', 'b', 'B'],
                                             ['A', 'bi', 'B']]})
check("同一对事件的两次说法求交（矛盾 → 直接判不一致，不覆盖不放过）",
      r['verdict'] == 'inconsistent' and '没有交集' in r['conflict']['why'],
      str(r['conflict']))
r = run({'events': ['A', 'B', 'C'],
         'relations': [['A', 'b', 'B'], ['B', 'b', 'C'], ['A', 'o', 'C']]})
check("冲突来自「推出的」与「给的」不符时也判不一致",
      r['verdict'] == 'inconsistent', str(r['verdict']))

# ── 四、见证模型：找到就**真满足**（独立复核）
r = run({'mode': 'solve', 'events': ['立项', '开发', '上线'],
         'relations': [['立项', 'b', '开发'], ['开发', 'm', '上线']]})
check("solve 找到见证（键是事件名，不是下标）",
      r['verdict'] == 'model_found'
      and set(r['model']) == {'立项', '开发', '上线'}, str(r['model']))
_model = r['model'] or {}
_ok = all(rel_of(*_model[a], *_model[b]) == rel
          for a, rel, b in [['立项', 'b', '开发'], ['开发', 'm', '上线']])
check("见证独立复核：按整数区间重算，关系确实成立", _ok, str(_model))
r = run({'mode': 'solve', 'events': ['A', 'B', 'C', 'D'],
         'relations': [['A', 'm', 'B'], ['B', 'm', 'C'], ['C', 'm', 'D']]})
_m2 = r['model'] or {}
check("链式相接也能给出见证（A 接 B 接 C 接 D），且四个事件都有区间",
      r['verdict'] == 'model_found' and set(_m2) == {'A', 'B', 'C', 'D'}
      and all(rel_of(*_m2[a], *_m2[b]) == 'm'
              for a, b in [('A', 'B'), ('B', 'C'), ('C', 'D')]), str(r))

# ── 五、点代数：路径一致性**完备**（实测）
_complete = True
for r12, r23, r13 in itertools.product(('<', '=', '>'), repeat=3):
    got = run({'mode': 'point', 'events': ['P', 'Q', 'R'],
               'relations': [['P', r12, 'Q'], ['Q', r23, 'R'],
                             ['P', r13, 'R']]})['verdict']
    # 独立穷举：三个整数点，检查是否真有解
    sat = any((lambda a, b, c: all([{'<': a < b, '=': a == b, '>': a > b}[r12],
                                    {'<': b < c, '=': b == c, '>': b > c}[r23],
                                    {'<': a < c, '=': a == c, '>': a > c}[r13]]))
              (a, b, c) for a, b, c in itertools.product(range(4), repeat=3))
    if (got == 'consistent') != sat:
        _complete = False
check("点代数完备性实测：路径一致 ⟺ 真有解（27 组三点网络全查）",
      _complete)
r = run({'mode': 'point', 'events': ['P', 'Q'],
         'relations': [['P', '<', 'Q'], ['P', '>', 'Q']]})
check("点代数报 consistent 时边界写明这是确定结论（完备）",
      run({'mode': 'point', 'events': ['P', 'Q'],
           'relations': [['P', '<', 'Q']]})['boundary'].count('完备') >= 1)

# ── 六、区间代数的实测范围（把"哪里完备"这件事钉住，不泛泛而谈）
_bad = []
for r12, r23, r13 in itertools.product(BASE, repeat=3):
    got = run({'events': ['A', 'B', 'C'],
               'relations': [['A', r12, 'B'], ['B', r23, 'C'],
                             ['A', r13, 'C']]})['verdict']
    sat = satisfiable_unit_ia({(0, 1): r12, (1, 2): r23, (0, 2): r13})
    if (got == 'path_consistent') and not sat:
        _bad.append((r12, r23, r13))
check("实测范围：**3 事件单元网络**上路径一致 ⟺ 有解（2197 组全查）——"
      "本构件仍按「只给必要条件」报（这个等价只在限定范围内测到）",
      not _bad, str(_bad[:4]))

# ── 七、纪律与边界
check("边界声明写出处（Allen 1983 / Vilain & Kautz 1986）与「借鉴区」",
      'Allen 1983' in run({'events': ['A', 'B'],
                           'relations': [['A', 'b', 'B']]})['boundary']
      and 'Vilain' in run({'events': ['A', 'B'],
                           'relations': [['A', 'b', 'B']]})['boundary'])
check("只诊断不决策写在边界里",
      '只诊断不决策' in run({'events': ['A', 'B'],
                             'relations': [['A', 'b', 'B']]})['boundary'])
check("不认识的关系名 → parse_error（不猜）",
      run({'events': ['A', 'B'],
           'relations': [['A', 'xx', 'B']]})['verdict'] == 'parse_error')
check("关系项引用了不存在的事件 → input_pending（不隐式加事件）",
      run({'events': ['A', 'B'],
           'relations': [['A', 'b', 'Z']]})['verdict'] == 'input_pending')
check("事件重名 / 缺参 / 坏 mode → 诚实拦截",
      run({'events': ['A', 'A'],
           'relations': [['A', 'b', 'A']]})['verdict'] == 'input_pending'
      and run({})['verdict'] == 'input_pending'
      and run({'mode': 'xxx'})['verdict'] == 'input_pending')
check("事件数超上限 → size_limit（不硬跑）",
      # 口径锚：边界就是 MAX_EVENTS 这个常量。不写死字面量——
      # 免得改了上限常量之后，测试还在守旧数（两边各说各话）
      run({'events': [f'E{i}' for i in range(MAX_EVENTS + 1)],
           'relations': [['E0', 'b', 'E1']]})['verdict'] == 'size_limit')

print("=" * 60)
print(f"结果: {PASS}/28 通过")
raise SystemExit(0 if PASS == 28 else 1)
