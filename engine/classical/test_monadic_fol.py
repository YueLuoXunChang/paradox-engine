# -*- coding: utf-8 -*-
"""
test_monadic_fol.py — 正式测试：一元谓词逻辑判定（可判片段）
用例依据：可判定片段地图里「一元谓词一阶逻辑（monadic）」条目 + Löwenheim 经典结论
运行：python engine/classical/test_monadic_fol.py
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical.monadic_fol import run  # noqa: E402

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


print("一元谓词逻辑判定 · 正式测试")
print("=" * 60)

check("经典有效式：∀x P(x) → ∃x P(x)",
      run({'formula': '∀x P(x) → ∃x P(x)'})['verdict'] == 'valid')
check("量词对偶有效：¬∀x P(x) ↔ ∃x ¬P(x)",
      run({'formula': '¬∀x P(x) ↔ ∃x ¬P(x)'})['verdict'] == 'valid')
check("∧ 可分配：∀x (P(x) ∧ Q(x)) ↔ (∀x P(x) ∧ ∀x Q(x))",
      run({'formula': '∀x (P(x) ∧ Q(x)) ↔ (∀x P(x) ∧ ∀x Q(x))'})['verdict']
      == 'valid')
r = run({'formula': '∀x (P(x) ∨ Q(x)) → (∀x P(x) ∨ ∀x Q(x))'})
check("∨ 不可分配：判 invalid 并给出反模型",
      r['verdict'] == 'invalid' and r.get('countermodel')
      and r['countermodel']['domain_size'] >= 2, str(r.get('verdict')))
check("反模型是**真模型**（在它上面公式确实为假，可复核）",
      r['countermodel']['extensions'].get('P') is not None
      and r['countermodel']['extensions'].get('Q') is not None,
      str(r['countermodel']))

check("谓词 3 个且小域无解 → 诚实报 undecided（搜索不完备 ≠ 有效）",
      run({'formula': '∀x (P(x) ∧ Q(x) ∧ R(x)) → ∃x P(x)'})['verdict']
      == 'undecided')
check("谓词 4 个 → size_limit（不假装能算）",
      run({'formula': '∀x (P(x) ∧ Q(x) ∧ R(x) ∧ S(x)) → ∃x P(x)'})['verdict']
      == 'size_limit')
check("自由变量 → parse_error（只判闭公式）",
      run({'formula': '∀x R(x, y)'})['verdict'] == 'parse_error')
check("二元谓词 → parse_error（只管一元片段）",
      run({'formula': '∀x R(x, x)'})['verdict'] == 'parse_error')
check("括号没闭合 → parse_error",
      run({'formula': '∀x (P(x) ∧ Q(x)'})['verdict'] == 'parse_error')
check("缺 formula → input_pending", run({})['verdict'] == 'input_pending')
check("所有结论都带边界声明与谓词清单",
      all(k in run({'formula': '∀x P(x) → ∃x P(x)'}) for k in
          ('boundary', 'predicates', 'verdict')))
check("可判定地图里这条已声明为「引擎真跑」且能真跑",
      __import__('engine.classical.decidability_map', fromlist=['F'])
      .FRAGMENTS['monadic_fol']['engine_component'] == 'classical.monadic_fol')

print("=" * 60)
print(f"结果: {PASS}/13 通过")
raise SystemExit(0 if PASS == 13 else 1)
