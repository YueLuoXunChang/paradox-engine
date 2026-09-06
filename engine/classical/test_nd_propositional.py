# -*- coding: utf-8 -*-
"""
test_nd_propositional.py — 正式测试：命题自然演绎（经典逻辑层 1.2）
用例依据：任务指标 39 详规七·补A + docs/formulas/nd_propositional.md
运行：python engine/classical/test_nd_propositional.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nd_propositional import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("命题自然演绎构件 · 正式测试")
print("=" * 60)

# ── 用例1：基本推理可证
check("P→Q, P ⊢ Q → proved（→消去）",
      run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})['verdict'] == 'proved')
check("P→Q, Q→R, P ⊢ R → proved（传递）",
      run({'premises': ['P→Q', 'Q→R', 'P'],
           'conclusion': 'R'})['verdict'] == 'proved')
check("P∧Q ⊢ P → proved（∧消去）",
      run({'premises': ['P∧Q'], 'conclusion': 'P'})['verdict'] == 'proved')
check("P, Q ⊢ P∧Q → proved（∧引入）",
      run({'premises': ['P', 'Q'], 'conclusion': 'P∧Q'})['verdict'] == 'proved')

# ── 用例2：无前提可证（→引入链）
check("⊢ P→P → proved",
      run({'premises': [], 'conclusion': 'P→P'})['verdict'] == 'proved')
check("⊢ (P→Q)→((Q→R)→(P→R)) → proved",
      run({'premises': [],
           'conclusion': '(P→Q)→((Q→R)→(P→R))'})['verdict'] == 'proved')

# ── 用例3：∨ 推理
check("P∨Q, ¬P ⊢ Q → proved（∨消去）",
      run({'premises': ['P∨Q', '¬P'], 'conclusion': 'Q'})['verdict'] == 'proved')
check("P ⊢ P∨Q → proved（∨引入）",
      run({'premises': ['P'], 'conclusion': 'P∨Q'})['verdict'] == 'proved')

# ── 用例4：证明树白箱
r = run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})
check("proved 给证明树",
      isinstance(r['proof_tree'], list) and len(r['proof_tree']) >= 1, str(r))
check("证明树每步带规则名",
      all('rule' in s for s in r['proof_tree']), str(r))

# ── 用例5：经典 vs 直觉主义（¬¬消去）
check("经典 ¬¬P ⊢ P → proved",
      run({'premises': ['¬¬P'], 'conclusion': 'P'})['verdict'] == 'proved')
check("直觉主义 ¬¬P ⊢ P → not_proved（无 ¬¬消去）",
      run({'premises': ['¬¬P'], 'conclusion': 'P',
           'system': 'intuitionistic'})['verdict'] == 'not_proved')
check("直觉主义标注系统",
      run({'premises': ['¬¬P'], 'conclusion': 'P',
           'system': 'intuitionistic'})['system'] == 'intuitionistic')

# ── 用例6：诚实边界
check("缺结论 → conclusion_pending",
      run({})['verdict'] == 'conclusion_pending')
check("非法系统 → parse_error",
      run({'conclusion': 'P', 'system': 'Q'})['verdict'] == 'parse_error')
check("解析错误 → parse_error",
      run({'conclusion': 'P→'})['verdict'] == 'parse_error')

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
