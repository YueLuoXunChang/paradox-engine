# -*- coding: utf-8 -*-
"""
test_lambda_calculus.py — 正式测试：λ 演算构件（经典逻辑层 1.6）
用例依据：内部规格七·补D + docs/formulas/lambda_calculus.md
运行：python engine/classical/test_lambda_calculus.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_calculus import run, parse_term, normalize, to_string  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("λ 演算构件 · 正式测试")
print("=" * 60)

# ── 用例1：β 归约基本
check("恒等应用 (λx.x)(λy.y) → 正规形 λy.y",
      run({'expr': '(λx.x)(λy.y)'})['normal_form'] == 'λy.y')
check("两次应用 (λx.λy.x)(λy.y)(λz.z) → 正规形 λy.y（返回第一个参数）",
      run({'expr': '(λx.λy.x)(λy.y)(λz.z)'})['normal_form'] == 'λy.y')

# ── 用例2：Ω 自应用无范式（诚实不卡死）
r = run({'mode': 'self_apply'})
check("Ω 自应用 → step_limit（无 β 正规形，诚实报步数上限）",
      r['verdict'] == 'step_limit', str(r))
check("Ω 前几步是自应用链（项含 x 应用自身）",
      len(r['beta_steps']) >= 1
      and ('x)x' in str(r['beta_steps'][0])
           or 'x x' in str(r['beta_steps'][0])
           or '(x' in str(r['beta_steps'][0])),
      str(r))

# ── 用例3：邱奇编码 succ
check("邱奇 succ(0) → 1",
      run({'mode': 'church', 'church_arg': 0})['church_number'] == 1)
check("邱奇 succ(2) → 3",
      run({'mode': 'church', 'church_arg': 2})['church_number'] == 3)
check("邱奇 succ(7) → 8",
      run({'mode': 'church', 'church_arg': 7})['church_number'] == 8)

# ── 用例4：Y 递归有界（阶乘）
check("阶乘 0! = 1",
      run({'mode': 'factorial', 'fact_n': 0})['factorial_value'] == 1)
check("阶乘 5! = 120",
      run({'mode': 'factorial', 'fact_n': 5})['factorial_value'] == 120)
r = run({'mode': 'factorial', 'fact_n': 5})
check("阶乘输出标注有界展开",
      '有界' in r['boundary'], r['boundary'])

# ── 用例5：捕获避免（α 换名）——(λx.λy.x) y 中 y 不被绑定 y 捕获
node = parse_term('(λx.λy.x) y')
# (λx.λy.x) y → β: [x:=y] λy.x —— 替换的自由 y 会被 λy 捕获，
# 引擎做 α 换名 → λy1.y（y 保持自由）——这是正确的捕获避免
v, nf, steps = normalize(node, 100)
nf_s = to_string(nf) if nf else None
check("(λx.λy.x) y → 捕获避免（α 换名，自由 y 不被绑）",
      v == 'normalized' and nf_s != 'λy.y' and nf_s.startswith('λ'),
      f"verdict={v} nf={nf_s}（λy.y 会错捕自由 y；λy1.y 才是对的）")

# ── 用例6：诚实边界
check("残缺项 λx. → parse_error",
      run({'expr': 'λx.'})['verdict'] == 'parse_error')
check("缺项 → expr_pending",
      run({})['verdict'] == 'expr_pending')
check("church 缺参数 → arg_pending",
      run({'mode': 'church'})['verdict'] == 'arg_pending')
check("church 超范围 → parse_error",
      run({'mode': 'church', 'church_arg': 100})['verdict'] == 'parse_error')
check("factorial 超范围 → parse_error",
      run({'mode': 'factorial', 'fact_n': 50})['verdict'] == 'parse_error')

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
