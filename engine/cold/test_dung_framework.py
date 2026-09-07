# -*- coding: utf-8 -*-
"""
test_dung_framework.py — 正式测试：Dung 论证框架（第 3 层 3.2）
用例依据：内部规格 §二（grounded/preferred/可接受/争议集）+ Dung 1995 标准
运行：python engine/cold/test_dung_framework.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dung_framework import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("Dung 论证框架 · 正式测试")
print("=" * 60)

# ── 用例1：链 a→b, b→c（Dung 教材例）
r = run({'arguments': ['a', 'b', 'c'],
         'attacks': [('a', 'b'), ('b', 'c')]})
check("链 → evaluated", r['verdict'] == 'evaluated', str(r))
check("grounded = [a, c]（无争议迭代）", r['grounded'] == ['a', 'c'],
      str(r))
check("preferred 含 [a,c]（极大可接受）", ['a', 'c'] in r['preferred'],
      str(r))
check("无争议集", r['conflict_pairs'] == [], str(r))

# ── 用例2：互攻 a↔b（争议核）
r = run({'arguments': ['a', 'b'], 'attacks': [('a', 'b'), ('b', 'a')]})
check("互攻 → grounded=[]（无无争议起点）", r['grounded'] == [], str(r))
check("争议集 = [a,b]", r['conflict_pairs'] == [['a', 'b']], str(r))
check("preferred 为单点（互斥可接受）",
      all(len(p) == 1 for p in r['preferred']) and len(r['preferred']) >= 1,
      str(r))

# ── 用例3：自攻 a→a
r = run({'arguments': ['a', 'b'], 'attacks': [('a', 'a'), ('b', 'a')]})
check("b 不被攻 → grounded 含 b", 'b' in r['grounded'], str(r))
check("a 自攻被排除 grounded", 'a' not in r['grounded'], str(r))

# ── 用例4：3-cycle（Dung 标准）
r = run({'arguments': ['a', 'b', 'c'],
         'attacks': [('a', 'b'), ('b', 'c'), ('c', 'a')]})
check("3-cycle grounded=[]", r['grounded'] == [], str(r))
check("3-cycle preferred=[[]]（唯一极大可接受=空）",
      r['preferred'] == [[]], str(r))

# ── 用例5：两链独立（无攻击交集）
r = run({'arguments': ['a', 'b', 'c', 'd'],
         'attacks': [('a', 'b'), ('c', 'd')]})
check("独立链 grounded=[a,c]（两链无争议头）",
      r['grounded'] == ['a', 'c'], str(r))
check("preferred 含 [a,c]", ['a', 'c'] in r['preferred'], str(r))

# ── 用例6：攻环 + 链（混合）
r = run({'arguments': ['a', 'b', 'c', 'd'],
         'attacks': [('a', 'b'), ('b', 'a'), ('c', 'd'), ('d', 'c'),
                     ('a', 'c')]})
check("grounded 不给 a/b/c/d 中环内者",
      all(x not in r['grounded'] for x in ('a', 'b', 'c', 'd')),
      str(r))
check("可接受集示例给（非空时）",
      isinstance(r['admissible_examples'], list), str(r))

# ── 用例7：可接受集防御性白箱
r = run({'arguments': ['a', 'b', 'c'],
         'attacks': [('a', 'b'), ('b', 'c'), ('a', 'c')]})
# a 不被攻；a 攻 b、c → {a} 可接受
check("{a} 在可接受示例中",
      any('a' in ex and len(ex) == 1 for ex in r['admissible_examples']),
      str(r))

# ── 用例8：诚实边界
check("论证<2 → input_pending",
      run({'arguments': ['a']})['verdict'] == 'input_pending')
check("攻击引用不存在 → input_pending",
      run({'arguments': ['a', 'b'],
           'attacks': [('a', 'x')]})['verdict'] == 'input_pending')
r = run({'arguments': [f'x{i}' for i in range(15)],
         'attacks': [('x0', 'x1')]})
check("超上限 → size_limit（诚实报告不硬跑）",
      r['verdict'] == 'size_limit', str(r))
check("边界声明借鉴来源（Dung 外部共识）", 'Dung' in
      run({'arguments': ['a', 'b'], 'attacks': [('a', 'b')]})['boundary'])
check("边界声明立场建议非判决", '不决策' in
      run({'arguments': ['a', 'b'], 'attacks': [('a', 'b')]})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/21 通过")
raise SystemExit(0 if PASS == 21 else 1)
