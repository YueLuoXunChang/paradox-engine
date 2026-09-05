# -*- coding: utf-8 -*-
"""
test_modal.py — 正式测试：模态逻辑构件（经典逻辑层 1.4）
用例依据：docs/ROADMAP 阶段1（概念来源：经典模态 Kripke 语义）
运行：python engine/classical/test_modal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modal import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("模态逻辑构件 · 正式测试")
print("=" * 60)

W = ['w1', 'w2']
A = {'w1': ['w2'], 'w2': ['w2']}  # w1→w2, w2 自反

# ── 用例1：□ / ◇ 基本语义
check("□p @w1（可达 w2 中 p 真）→ true",
      run({'worlds': W, 'access': A, 'system': 'K',
           'assign': {'p': ['w1', 'w2']}, 'formula': '□p',
           'world': 'w1'})['verdict'] == 'true')
check("◇p @w1（w2 p 真）→ true",
      run({'worlds': W, 'access': A, 'system': 'K',
           'assign': {'p': ['w2']}, 'formula': '◇p',
           'world': 'w1'})['verdict'] == 'true')
check("□p @w1（可达 w2 无 p）→ false",
      run({'worlds': W, 'access': A, 'system': 'K',
           'assign': {}, 'formula': '□p', 'world': 'w1'})['verdict'] == 'false')

# ── 用例2：系统差异（经典例：□p→◇p 在 K 不成立、在 T 成立）
check("□p→◇p 在 K（w0 无可达）→ false",
      run({'worlds': ['w0'], 'access': {'w0': []}, 'system': 'K',
           'assign': {}, 'formula': '□p→◇p',
           'world': 'w0'})['verdict'] == 'false')
check("□p→◇p 在 T（自反 + p@w0）→ true",
      run({'worlds': ['w0'], 'access': {'w0': ['w0']}, 'system': 'T',
           'assign': {'p': ['w0']}, 'formula': '□p→◇p',
           'world': 'w0'})['verdict'] == 'true')

# ── 用例3：系统标注（白箱）
S4W = ['w1', 'w2']
S4A = {'w1': ['w1', 'w2'], 'w2': ['w2']}  # 自反+传递
r = run({'worlds': S4W, 'access': S4A, 'system': 'S4',
         'assign': {'p': ['w1', 'w2']}, 'formula': '□p', 'world': 'w1'})
check("S4 自检通过（自反+传递成立）→ true",
      r['verdict'] == 'true', str(r))
r = run({'worlds': W, 'access': A, 'system': 'K',
         'assign': {'p': ['w1']}, 'formula': '□p', 'world': 'w1'})
check("输出标注系统（boundary 含 K）",
      'K' in r['boundary'], str(r))

# ── 用例4：框架条件自检
check("T 系统缺自反 → system_mismatch",
      run({'worlds': ['w0'], 'access': {'w0': []}, 'system': 'T',
           'assign': {}, 'formula': '□p',
           'world': 'w0'})['verdict'] == 'system_mismatch')
check("S4 缺传递 → system_mismatch",
      run({'worlds': ['w0', 'w1', 'w2'],
           'access': {'w0': ['w0', 'w1'], 'w1': ['w1', 'w2'],
                      'w2': ['w2']},
           'system': 'S4', 'assign': {}, 'formula': '□p',
           'world': 'w0'})['verdict'] == 'system_mismatch')

# ── 用例5：复合公式
check("□p∧◇q（w2 p,q 真）→ true",
      run({'worlds': W, 'access': A, 'system': 'K',
           'assign': {'p': ['w2'], 'q': ['w2']}, 'formula': '□p∧◇q',
           'world': 'w1'})['verdict'] == 'true')

# ── 用例6：诚实边界
check("非法系统 Q → parse_error",
      run({'worlds': W, 'formula': '□p', 'system': 'Q'})['verdict'] == 'parse_error')
check("解析错误 → parse_error",
      run({'worlds': W, 'access': A, 'system': 'K',
           'formula': '□('})['verdict'] == 'parse_error')
check("缺公式 → formula_pending",
      run({'worlds': W})['verdict'] == 'formula_pending')
check("基准世界不在世界集 → world_missing",
      run({'worlds': W, 'access': A, 'system': 'K',
           'formula': '□p', 'world': 'wx'})['verdict'] == 'world_missing')

print("=" * 60)
print(f"结果: {PASS}/14 通过")
raise SystemExit(0 if PASS == 14 else 1)
