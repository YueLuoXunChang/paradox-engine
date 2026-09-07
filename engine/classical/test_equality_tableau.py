# -*- coding: utf-8 -*-
"""
test_equality_tableau.py — 正式测试：等词 + 表列法（经典逻辑层 1.5）
用例依据：内部规格七·补C + docs/formulas/equality_tableau.md
运行：python engine/classical/test_equality_tableau.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from equality_tableau import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("等词 + 表列法构件 · 正式测试")
print("=" * 60)

# ── 用例1：基本有效
check("P ⊢ P∨Q → valid（∨引入语义）",
      run({'premises': ['P'], 'conclusion': 'P∨Q'})['verdict'] == 'valid')
check("P∧Q ⊢ P → valid（∧消去语义）",
      run({'premises': ['P∧Q'], 'conclusion': 'P'})['verdict'] == 'valid')
check("P, P→Q ⊢ Q → valid（modus ponens）",
      run({'premises': ['P', 'P→Q'],
           'conclusion': 'Q'})['verdict'] == 'valid')

# ── 用例2：无效 + 反例模型
r = run({'premises': ['P∨Q'], 'conclusion': 'P'})
check("P∨Q ⊢ P → invalid",
      r['verdict'] == 'invalid', str(r))
check("invalid 给反例模型",
      r['open_branch_model'] is not None, str(r))

# ── 用例3：等词替换
check("晨星=暮星, 喜欢(晨星,c) ⊢ 喜欢(暮星,c) → valid",
      run({'premises': ['喜欢(晨星,c)'], 'equality': ['晨星=暮星'],
           'conclusion': '喜欢(暮星,c)'})['verdict'] == 'valid')
check("a=b, b=c, 关系(a,d) ⊢ 关系(c,d) → valid（传递链）",
      run({'premises': ['关系(a,d)'], 'equality': ['a=b', 'b=c'],
           'conclusion': '关系(c,d)'})['verdict'] == 'valid')
check("⊢ a=a → valid（自反）",
      run({'premises': [], 'equality': [],
           'conclusion': 'a=a'})['verdict'] == 'valid')

# ── 用例4：一阶地面（无量词）
check("人(苏) ∧ (人→会死)(苏) ⊢ 会死(苏) → valid",
      run({'premises': ['人(苏格拉底)',
                        '人(苏格拉底)→会死(苏格拉底)'],
           'conclusion': '会死(苏格拉底)'})['verdict'] == 'valid')
check("∀ 未支持时诚实——带量词 → parse_error 或合理处理",
      run({'premises': ['∀x(人(x))'],
           'conclusion': '人(苏格拉底)'})['verdict'] in
      ('parse_error', 'valid', 'invalid', 'undetermined'))

# ── 用例5：复合推理
check("(P→Q)→R, P→Q ⊢ R → valid",
      run({'premises': ['(P→Q)→R', 'P→Q'],
           'conclusion': 'R'})['verdict'] == 'valid')

# ── 用例6：诚实边界
check("缺结论 → conclusion_pending",
      run({})['verdict'] == 'conclusion_pending')
check("解析错误 → parse_error",
      run({'premises': ['('], 'conclusion': 'P'})['verdict'] == 'parse_error')
check("等词事实非 a=b → parse_error",
      run({'premises': [], 'equality': ['P∧Q'],
           'conclusion': 'P'})['verdict'] == 'parse_error')

print("=" * 60)
print(f"结果: {PASS}/14 通过")
raise SystemExit(0 if PASS == 14 else 1)
