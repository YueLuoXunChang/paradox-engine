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

# ── 否定结合力（语义穷举对拍抓出来的真 bug，防复发）
# 崩因：`¬` 的操作数按 min_prec=4 解析，而 ∧ 的优先级正是 4 ——
# 于是 `¬P ∧ Q` 被解析成 `¬(P ∧ Q)`（注释写着"优先级最高"，实现却把 ∧ 吞了）。
# 随机抽样之所以没抓到：生成器给每个子式都加了括号，正好把这个 bug 遮住。
def _table(f):
    r = run({'formula': f, 'mode': 'truth_table'})
    return [(row['P'], row['Q'], row['_result']) for row in r['truth_table']]


check("¬ 绑得比 ∧ 紧：¬P ∧ Q 只在 Q 真且 P 假时为真",
      _table('¬P ∧ Q') == [(False, False, False), (False, True, True),
                           (True, False, False), (True, True, False)],
      _table('¬P ∧ Q'))
check("¬ 绑得比 ∨ 紧：¬P ∨ Q 等价于 P → Q",
      _table('¬P ∨ Q') == [(False, False, True), (False, True, True),
                           (True, False, False), (True, True, True)],
      _table('¬P ∨ Q'))
check("¬(P ∧ Q) 与 ¬P ∧ Q 不是同一个式子（别被旧解析混为一谈）",
      _table('¬(P ∧ Q)') != _table('¬P ∧ Q'))
check("¬ 作用域正确后：¬P ∧ Q 能推出 ¬P，也能推出 Q",
      run({'premises': ['¬P ∧ Q'], 'conclusion': '¬P',
           'mode': 'validity'})['verdict'] == 'valid'
      and run({'premises': ['¬P ∧ Q'], 'conclusion': 'Q',
               'mode': 'validity'})['verdict'] == 'valid')

print("=" * 60)
print(f"结果: {PASS}/19 通过")
raise SystemExit(0 if PASS == 19 else 1)
