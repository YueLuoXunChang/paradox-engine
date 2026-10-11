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
check("未声明变量 → type_error（**不再容忍 parse_error**："
      "参数带括号的解析 bug 已修，这条该干净地判类型错）",
      run({'expr': '(λx:A.x) y'})['verdict'] == 'type_error')

# ── 三个解析 bug 的回归（跨构件对拍撞出来的，2026-10-02）
# ① 分词器把 `→` 当 2 个单位前进（Unicode 索引）→ 标注里写不出箭头类型；
# ② `t in '.:(),→'` 是字符串包含判断，而 `'('` 在这个串里 →
#    "参数以括号开头"的应用解析中断；
# ③ `parse_type` 切词时括号没与原子分开 → 构件自己打印的 (A→A) 写法抄回
#    expected 反而判类型错。
check("① 标注里能写箭头类型：λf:A→A.f → ((A→A)→(A→A))",
      run({'expr': 'λf:A→A.f'})['verdict'] == 'typed'
      and run({'expr': 'λf:A→A.f'})['inferred'] == '((A→A)→(A→A))',
      run({'expr': 'λf:A→A.f'}))
check("② 参数可以以括号开头：(λx:A.x) (λx:A.x) 是类型错（不是解析错）",
      run({'expr': '(λx:A.x) (λx:A.x)'})['verdict'] == 'type_error',
      run({'expr': '(λx:A.x) (λx:A.x)'}))
check("③ 括号写法与不带的等价（构件自己就打印括号写法，用户会照抄）",
      run({'expr': 'λx:A.x', 'expected': '(A→A)'})['verdict'] == 'typed'
      and run({'expr': 'λx:A.x', 'expected': 'A→A'})['verdict'] == 'typed'
      and run({'expr': 'λx:A.x', 'expected': '((A→A))'})['verdict'] == 'typed')

print("=" * 60)
print(f"结果: {PASS}/18 通过")
raise SystemExit(0 if PASS == 18 else 1)
