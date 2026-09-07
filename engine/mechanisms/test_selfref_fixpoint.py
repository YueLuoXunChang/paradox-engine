# -*- coding: utf-8 -*-
"""
test_selfref_fixpoint.py — 正式测试：递归修正 × 自指检测（第 2 层 2.3）
用例依据：内部规格 41 §三（共振带三态 + 诚实边界）
运行：python engine/mechanisms/test_selfref_fixpoint.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfref_fixpoint import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("递归修正 × 自指检测 · 正式测试")
print("=" * 60)

# ── 用例1：说谎者（核心——自指悖论态/共振带）
r = run({'mode': 'sentence', 'sentence': 'liar'})
check("说谎者 → liar_cycle", r['verdict'] == 'liar_cycle', str(r))
check("说谎者周期 = 2（真/假翻转）", r['detail']['period'] == 2, str(r))
check("说谎者给注解卡",
      r['annotation'] is not None and r['annotation']['LV'] == 'P-A', str(r))
check("边界声明：不判真值", '不判' in r['boundary'], r['boundary'])

# ── 用例2：本句为真（不动点但无信息）
r = run({'mode': 'sentence', 'sentence': 'truth_teller'})
check("本句为真 → fixed_point", r['verdict'] == 'fixed_point', str(r))
check("诚实标注不动点不唯一", '不唯一' in r['detail']['note'], str(r))

# ── 用例3：哥德尔句（结构性 P-A，不假装跑）
r = run({'mode': 'sentence', 'sentence': 'godel'})
check("哥德尔句 → annotated_pa", r['verdict'] == 'annotated_pa', str(r))
check("哥德尔注解 P-A", r['annotation']['LV'] == 'P-A', str(r))
check("边界声明：不宣称判定（不推翻定理）",
      '不宣称判定' in r['boundary'], r['boundary'])

# ── 用例4：自定义修正——收敛不动点（良性自指）
r = run({'mode': 'iterate', 'f': lambda x: x / 2, 'state0': 1.0})
check("f(x)=x/2 → fixed_point", r['verdict'] == 'fixed_point', str(r))
check("定点白箱给出收敛值", 'fixed_value' in r['detail'], str(r))
check("定点注解 LV=P-B（良性运行态）", r['annotation']['LV'] == 'P-B', str(r))

# ── 用例5：自定义修正——数值共振带
r = run({'mode': 'iterate', 'f': lambda x: 1 - x, 'state0': 0.2})
check("f(x)=1-x → resonance_band", r['verdict'] == 'resonance_band', str(r))
check("共振带周期 = 2", r['detail']['period'] == 2, str(r))
check("共振带给振荡范围", r['detail']['range'] is not None, str(r))
check("共振带边界：判振荡模式不判真值",
      '不判真值' in r['boundary'], r['boundary'])

# ── 用例6：自定义修正——发散（真墙）
r = run({'mode': 'iterate', 'f': lambda x: 2 * x, 'state0': 1.0,
         'max_steps': 200})
check("f(x)=2x → diverge", r['verdict'] == 'diverge', str(r))
check("发散边界：标记真墙不硬钻", '不硬钻' in r['boundary'], r['boundary'])

# ── 用例7：诚实边界
check("缺 mode → input_pending", run({})['verdict'] == 'input_pending')
check("未知预设 → input_pending",
      run({'mode': 'sentence', 'sentence': 'xx'})['verdict']
      == 'input_pending')
check("iterate 缺 f → input_pending",
      run({'mode': 'iterate'})['verdict'] == 'input_pending')
check("修正函数抛错 → parse_error（诚实拦截）",
      run({'mode': 'iterate', 'f': lambda x: 1 / 0, 'state0': 1.0})
      ['verdict'] == 'parse_error')
r = run({'mode': 'iterate', 'f': lambda x: (x + 1) % 7, 'state0': 0,
         'max_steps': 5})
check("窗口不足 → undetermined 或周期（诚实不硬判发散）",
      r['verdict'] in ('undetermined', 'resonance_band', 'liar_cycle'),
      str(r))

print("=" * 60)
print(f"结果: {PASS}/23 通过")
raise SystemExit(0 if PASS == 23 else 1)
