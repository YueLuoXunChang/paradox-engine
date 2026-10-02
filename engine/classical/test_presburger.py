# -*- coding: utf-8 -*-
"""
test_presburger.py — 正式测试：Presburger 算术判定（整数 + 加法 + 常数乘）
用例依据：可判定片段地图里「Presburger 算术」条目（Presburger 1929 可判定）
+ 量词消元判定的行为契约（结论 / 等价式 / 拒绝 / 规模上限）。
运行：python engine/classical/test_presburger.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical.presburger import (MAX_B, MAX_COEF, MAX_INPUT,  # noqa: E402
                                         MAX_MOD, MAX_QE, run)

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


def v(formula, mode=None):
    return run({'formula': formula} if mode is None
               else {'formula': formula, 'mode': mode})


print("Presburger 算术判定 · 正式测试")
print("=" * 60)

# ── 一、结论对不对（拿已知答案的式子核对）
check("恒真：∀x ∃y (y+y=x ∨ y+y+1=x)——每个整数非偶即奇",
      v('∀x ∃y (y + y = x ∨ y + y + 1 = x)')['verdict'] == 'true')
check("非恒真：∀x ∃y (y+y=x)——奇数没有整数半",
      v('∀x ∃y (y + y = x)')['verdict'] == 'false')
check("无解：∃x (2*x = 3)——左边永远偶数",
      v('∃x (2*x = 3)')['verdict'] == 'false')
check("有解：∃x (x < 5 ∧ x > 3)",
      v('∃x (x < 5 ∧ x > 3)')['verdict'] == 'true')
check("恒真：∀x ∀y (x < y → x+1 ≤ y)——整数上没有夹在中间的",
      v('∀x ∀y (x < y → x + 1 ≤ y)')['verdict'] == 'true')
check("非恒真：∀x ∀y (x < y → ∃z (x < z ∧ z < y))——同上，反着问也不成立",
      v('∀x ∀y (x < y → ∃z (x < z ∧ z < y))')['verdict'] == 'false')
check("自然数写法（量词变量自带 n ≥ 0）：∀n ∃m (n ≥ 0 → 奇偶覆盖)",
      v('∀n ∃m (n ≥ 0 → (m ≥ 0 ∧ (n = 2*m ∨ n = 2*m + 1)))')['verdict']
      == 'true')

# ── 二、系数统一与界的开闭（消元最容易错的地方）
check("系数 2 的窗口：∃x (2*x ≥ 3 ∧ 2*x ≤ 4) —— x=2 在窗口里",
      v('∃x (2*x ≥ 3 ∧ 2*x ≤ 4)')['verdict'] == 'true')
check("系数 2 的空窗口：∃x (2*x > 4 ∧ 2*x < 6) —— 2x=5 取不到",
      v('∃x (2*x > 4 ∧ 2*x < 6)')['verdict'] == 'false')
check("系数 3 的空窗口：∃x (3*x ≥ 1 ∧ 3*x ≤ 2)",
      v('∃x (3*x ≥ 1 ∧ 3*x ≤ 2)')['verdict'] == 'false')
check("空区间：∃x (x ≥ 1 ∧ x ≤ 0)",
      v('∃x (x ≥ 1 ∧ x ≤ 0)')['verdict'] == 'false')
check("严格与不严格的差别：∃x (x > 0 ∧ x < 1) 与 ∃x (x ≥ 0 ∧ x ≤ 1)",
      v('∃x (x > 0 ∧ x < 1)')['verdict'] == 'false'
      and v('∃x (x ≥ 0 ∧ x ≤ 1)')['verdict'] == 'true')

# ── 三、整除（同余）：要一起成立才算数
check("同余打架：∃x (2 | x ∧ 2 | x + 1)",
      v('∃x (2 | x ∧ 2 | x + 1)')['verdict'] == 'false')
check("同余凑得上：∃x (2 | x ∧ 3 | x + 1 ∧ 5 | x + 3)",
      v('∃x (2 | x ∧ 3 | x + 1 ∧ 5 | x + 3)')['verdict'] == 'true')
check("否定整除：∀x (2 | x ∨ 2 | x + 1) 与 ∃x (¬(2|x) ∧ ¬(2|x+1))",
      v('∀x (2 | x ∨ 2 | x + 1)')['verdict'] == 'true'
      and v('∃x (¬(2 | x) ∧ ¬(2 | x + 1))')['verdict'] == 'false')
check("带系数的整除：∃x (6 | 2*x) 等价于 3 | x",
      v('∃x (6 | 2*x)')['verdict'] == 'true'
      and v('∃x (6 | 2*x ∧ ¬(3 | x))')['verdict'] == 'false')

# ── 四、输出契约（结论之外，诊断信息要齐、要能复核）
r = v('x + y = 0')
check("非恒真时给出反例指派（可复核）",
      r['verdict'] == 'false' and r.get('counterexample')
      and len(r['counterexample']) == 2, str(r.get('counterexample')))
r2 = v('x + y = 2*y', 'satisfiable')
check("判有解时给出一个见证指派",
      r2['verdict'] == 'true' and r2.get('witness'), str(r2.get('witness')))
r3 = v('x + y = 0')
check("消元后的等价式随结论一起给出（白箱，人看得懂）",
      r3['verdict'] == 'false' and r3['equivalent'] == 'x + y = 0'
      and r3['free_variables'] == ['x', 'y'] and r3['quantifiers'] == 0,
      str(r3))
r4 = v('∀x ∃y (y + y = x)')
check("结论都带边界声明与量词计数",
      'boundary' in r4 and r4['quantifiers'] == 2 and r4['free_variables'] == [],
      str(r4))

# ── 五、拒绝与诚实上限（不假装能算）
check("变量乘变量 → parse_error（那是 PA，不可判定，划出去）",
      v('∃x (x * x = 4)')['verdict'] == 'parse_error')
check("整除号左边写变量 → parse_error（不是 Presburger 的写法）",
      v('∃x (x | 3)')['verdict'] == 'parse_error')
# ── 五·补、口径锚：每条上限都**成对**钉住（硬核度① 判据轴）
#    成对＝边界之内算得出、边界之外拦得住。只钉一边等于不知道边界在哪：
#    "拦得住"不能证明"该拦的才拦"。输入一律用常量构造，不写字面量——
#    改了常量测试跟着动，测试守的边界就是这个数本身。
check("模数边界之内（= MAX_MOD）算得出",
      v('∃x (%d | x)' % MAX_MOD)['verdict'] == 'true')
check("模数边界之外（MAX_MOD + 1）→ size_limit（诚实说不算，不当成结论）",
      v('∃x (%d | x)' % (MAX_MOD + 1))['verdict'] == 'size_limit')
check("系数边界之内（= MAX_COEF）算得出",
      v('∃x (%d*x = 1)' % MAX_COEF)['verdict'] == 'false')
check("系数边界之外（MAX_COEF + 1）→ size_limit",
      v('∃x (%d*x = 1)' % (MAX_COEF + 1))['verdict'] == 'size_limit')
check("周期边界之内（两个小模数，lcm 很小）算得出",
      v('∃x (3 | x ∧ 5 | x)')['verdict'] == 'true')
r_bigB = v('∃x (199 | x ∧ 197 | x)')
check("周期边界之外 → size_limit，且说明里点的是候选周期上限",
      r_bigB['verdict'] == 'size_limit'
      and '候选周期' in (r_bigB.get('explanation') or ''))
check("口径锚：那条输入的周期乘积确实超 MAX_B（互素，lcm＝乘积）",
      199 * 197 > MAX_B > 0)
ql_in = ' '.join('∃x%d' % i for i in range(MAX_QE)) + ' (x0 = x0)'
ql_out = ' '.join('∃x%d' % i for i in range(MAX_QE + 1)) + ' (x0 = x0)'
check("量词层数边界之内（= MAX_QE 层）算得出", v(ql_in)['verdict'] == 'true')
check("量词层数边界之外（MAX_QE + 1 层）→ size_limit",
      v(ql_out)['verdict'] == 'size_limit')
f_long = ' ∧ '.join(['x = 1'] * (MAX_INPUT // 5 + 50))
check("公式串边界之外 → size_limit（串长确实超过 MAX_INPUT）",
      len(f_long) > MAX_INPUT and v(f_long)['verdict'] == 'size_limit')
check("会爆分支的式子 → 老实报 size_limit（先前这里会卡死不返回）",
      v('(((5 | x) ↔ (2*x + y ≠ -2*x)) → ((x ≤ y) ∧ (3*x + y ≤ y)))')['verdict']
      == 'size_limit')
check("缺 formula → input_pending；坏 mode → input_pending",
      run({})['verdict'] == 'input_pending'
      and v('x = x', '随便')['verdict'] == 'input_pending')

# ── 六、与可判定地图对得上（地图不能再说"引擎未实现"）
from engine.classical.decidability_map import FRAGMENTS  # noqa: E402
check("地图条目已翻正：presburger 指向本构件且是真跑",
      FRAGMENTS['presburger']['engine_component'] == 'classical.presburger',
      str(FRAGMENTS['presburger']['engine_component']))

print("=" * 60)
print(f"结果: {PASS}/35 通过")
raise SystemExit(0 if PASS == 35 else 1)
