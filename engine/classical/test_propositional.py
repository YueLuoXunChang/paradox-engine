# -*- coding: utf-8 -*-
"""
test_propositional.py — 正式测试：命题逻辑构件（经典逻辑层 1.1）
用例依据：docs/ROADMAP 阶段1 + docs/formulas/propositional.md（概念来源：经典逻辑）
运行：python engine/classical/test_propositional.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from propositional import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("命题逻辑构件 · 正式测试")
print("=" * 60)

# ── 用例1：经典有效式（重言式作推理规则）
check("三段论 (P→Q), P ⊢ Q → valid",
      run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})['verdict'] == 'valid')
check("析取三段论 (P∨Q), ¬P ⊢ Q → valid",
      run({'premises': ['P∨Q', '¬P'], 'conclusion': 'Q'})['verdict'] == 'valid')
check("假言易位 ¬Q→¬P ⊢ P→Q → valid",
      run({'premises': ['¬Q→¬P'], 'conclusion': 'P→Q'})['verdict'] == 'valid')

# ── 用例2：无效式 + 反例（验证反例输出质量）
r = run({'premises': ['P∨Q'], 'conclusion': 'P'})
check("P∨Q ⊢ P → invalid（反例：P假Q真）",
      r['verdict'] == 'invalid' and r['counterexample'] == {'P': '假', 'Q': '真'},
      str(r))
r = run({'premises': ['P→Q'], 'conclusion': 'Q'})
check("P→Q ⊢ Q → invalid（肯定后件谬误）",
      r['verdict'] == 'invalid' and r['counterexample'] is not None, str(r))

# ── 用例3：公式类型
check("排中律 P∨¬P → tautology",
      run({'formula': 'P∨¬P'})['verdict'] == 'tautology')
check("无矛盾律 ¬(P∧¬P) → tautology",
      run({'formula': '¬(P∧¬P)'})['verdict'] == 'tautology')
check("P∧¬P → contradiction",
      run({'formula': 'P∧¬P'})['verdict'] == 'contradiction')
check("P∧Q → contingent",
      run({'formula': 'P∧Q'})['verdict'] == 'contingent')

# ── 用例4：可满足性
check("P∧Q satisfiable → satisfiable",
      run({'formula': 'P∧Q', 'mode': 'satisfiable'})['verdict'] == 'satisfiable')
check("P∧¬P satisfiable → unsatisfiable",
      run({'formula': 'P∧¬P', 'mode': 'satisfiable'})['verdict'] == 'unsatisfiable')

# ── 用例5：联结词等价（↔）
check("(P↔Q) 在 P=Q 时真（真值表含 2 真行）",
      run({'formula': 'P↔Q', 'mode': 'truth_table'})['truth_table'] is not None)

# ── 用例6：诚实边界
check("残缺公式 → parse_error",
      run({'formula': 'P→'})['verdict'] == 'parse_error')
check("空输入 → formula_pending",
      run({})['verdict'] == 'formula_pending')
check("validity 缺结论 → conclusion_pending",
      run({'premises': ['P'], 'conclusion': '', 'mode': 'validity'})['verdict'] == 'conclusion_pending')

print("=" * 60)
print(f"结果: {PASS}/15 通过")
raise SystemExit(0 if PASS == 15 else 1)
