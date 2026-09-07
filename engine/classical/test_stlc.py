# -*- coding: utf-8 -*-
"""
test_stlc.py — 正式测试：简单类型 λ（STLC，经典逻辑层 1.9）
用例依据：内部规格七·补F + docs/formulas/stlc.md
运行：python engine/classical/test_stlc.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stlc import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("简单类型 λ（STLC）构件 · 正式测试")
print("=" * 60)

# ── 用例1：类型推导
check("λx:A.x : A→A → typed",
      run({'expr': 'λx:A.x'})['verdict'] == 'typed')
r = run({'expr': 'λx:A.x'})
check("推断类型 = A→A",
      r['inferred'] == '(A→A)', str(r))
check("K 组合子 λx:A.λy:B.x → typed",
      run({'expr': 'λx:A.λy:B.x'})['verdict'] == 'typed')

# ── 用例2：应用
check("(λx:A.x) c（c:A）→ typed : A",
      run({'expr': '(λx:A.x) c',
           'context': {'c': 'A'}})['inferred'] == 'A')
check("组合应用 (λx:A.λy:B.x) c d（c:A,d:B）→ A",
      run({'expr': '(λx:A.λy:B.x) c d',
           'context': {'c': 'A', 'd': 'B'}})['inferred'] == 'A')

# ── 用例3：类型错误拦截（核心——拦自应用）
check("λx:A.x x → type_error（STLC 拦自应用）",
      run({'expr': 'λx:A.x x'})['verdict'] == 'type_error')
check("参数类型不匹配 → type_error",
      run({'expr': '(λx:A.x) c',
           'context': {'c': 'B'}})['verdict'] == 'type_error')
check("缺类型标注 λx.x → type_error",
      run({'expr': 'λx.x'})['verdict'] == 'type_error')

# ── 用例4：expected 校验
check("expected 匹配 → typed",
      run({'expr': 'λx:A.x',
           'expected': 'A→A'})['verdict'] == 'typed')
check("expected 不匹配 → type_error",
      run({'expr': 'λx:A.x',
           'expected': 'A→B'})['verdict'] == 'type_error')

# ── 用例5：推导白箱
r = run({'expr': 'λx:A.x'})
check("typed 给推导树",
      isinstance(r['derivation'], list) and len(r['derivation']) >= 1,
      str(r))
check("推导每步带规则",
      all('rule' in s for s in r['derivation']), str(r))

# ── 用例6：诚实边界
check("缺项 → expr_pending",
      run({})['verdict'] == 'expr_pending')
check("残缺项 → parse_error 或 type_error（诚实）",
      run({'expr': 'λx:A.'})['verdict'] in ('parse_error', 'type_error'))
check("未声明变量 → type_error",
      run({'expr': '(λx:A.x) y'})['verdict'] in ('type_error', 'parse_error'))

print("=" * 60)
print(f"结果: {PASS}/15 通过")
raise SystemExit(0 if PASS == 15 else 1)
