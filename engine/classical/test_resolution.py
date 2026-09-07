# -*- coding: utf-8 -*-
"""
test_resolution.py — 正式测试：一阶归结构件（经典逻辑层 1.4）
用例依据：内部规格七·补B + docs/formulas/resolution.md
运行：python engine/classical/test_resolution.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolution import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("一阶归结构件 · 正式测试")
print("=" * 60)

# ── 用例1：三段论（∀ + 事实 → 结论）
check("∀x(人→会死), 人(苏) ⊢ 会死(苏) → proved",
      run({'premises': ['∀x(人(x)→会死(x))'],
           'facts': ['人(苏格拉底)'],
           'conclusion': '会死(苏格拉底)'})['verdict'] == 'proved')

# ── 用例2：不可推出（关键正确性——常量不作变量）
check("无 人(柏拉图) 前提 ⊢ 会死(柏拉图) → not_proved",
      run({'premises': ['∀x(人(x)→会死(x))'],
           'facts': ['人(苏格拉底)'],
           'conclusion': '会死(柏拉图)'})['verdict'] == 'not_proved')

# ── 用例3：传递链（多步归结）
check("∀x(人→会死), ∀x(会死→腐烂), 人(苏) ⊢ 腐烂(苏) → proved",
      run({'premises': ['∀x(人(x)→会死(x))',
                        '∀x(会死(x)→腐烂(x))'],
           'facts': ['人(苏格拉底)'],
           'conclusion': '腐烂(苏格拉底)'})['verdict'] == 'proved')

# ── 用例4：命题级重言
check("⊢ P∨¬P → proved",
      run({'conclusion': 'P∨¬P'})['verdict'] == 'proved')

# ── 用例5：Skolem 化（∃ 消去）
r = run({'premises': ['∃x(鸟(x))'], 'facts': [],
        'conclusion': '∃y(鸟(y))'})
check("∃x鸟(x) ⊢ ∃y鸟(y) → proved",
      r['verdict'] == 'proved', str(r))
check("Skolem 常量被记录（白箱）",
      len(r['skolem_used']) >= 1, str(r))

# ── 用例6：归结链白箱
r = run({'premises': ['∀x(人(x)→会死(x))'],
         'facts': ['人(苏格拉底)'],
         'conclusion': '会死(苏格拉底)'})
check("proved 给归结链",
      isinstance(r['resolution_chain'], list)
      and len(r['resolution_chain']) >= 1, str(r))
check("归结链每步含 mgu",
      all('mgu' in s for s in r['resolution_chain']), str(r))

# ── 用例7：诚实边界
check("缺结论 → conclusion_pending",
      run({'conclusion': ''})['verdict'] == 'conclusion_pending')
check("解析错误 → parse_error",
      run({'premises': ['∀x('], 'conclusion': 'P'})['verdict'] == 'parse_error')

print("=" * 60)
print(f"结果: {PASS}/10 通过")
raise SystemExit(0 if PASS == 10 else 1)
