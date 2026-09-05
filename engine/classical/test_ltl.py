# -*- coding: utf-8 -*-
"""
test_ltl.py — 正式测试：时序逻辑 LTL 构件（经典逻辑层 1.3）
用例依据：docs/ROADMAP 阶段1（概念来源：经典 LTL 语义）
运行：python engine/classical/test_ltl.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ltl import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("时序逻辑 LTL 构件 · 正式测试")
print("=" * 60)

# 健康→故障→恢复 路径
PATH = [{'up'}, {'down'}, {'recovering'}, {'up'}]

# ── 用例1：G（一直）
check("G(¬down) 含 down → violated@1",
      run({'path': PATH, 'formula': 'G(¬down)'})['verdict'] == 'violated')
r = run({'path': PATH, 'formula': 'G(¬down)'})
check("violation_index = 1（down 首次出现）",
      r['violation_index'] == 1, str(r))
check("G(up∨down∨recovering) 全覆盖 → holds",
      run({'path': PATH,
           'formula': 'G(up∨down∨recovering)'})['verdict'] == 'holds')

# ── 用例2：F（最终）
check("F(recovering) 恢复过 → holds",
      run({'path': PATH, 'formula': 'F(recovering)'})['verdict'] == 'holds')
check("F(维护) 从未出现 → violated（有界路径未满足）",
      run({'path': PATH, 'formula': 'F(维护)'})['verdict'] == 'violated')

# ── 用例3：X（下一状态）
check("X(down) s0 后是 down → holds",
      run({'path': PATH, 'formula': 'X(down)'})['verdict'] == 'holds')
check("X(维护) 下一状态无 → violated",
      run({'path': PATH, 'formula': 'X(维护)'})['verdict'] == 'violated')

# ── 用例4：U（直到）
check("up U recovering：s0 up 但 s1 down 违约 → violated",
      run({'path': PATH, 'formula': 'up U recovering'})['verdict'] == 'violated')
PATH2 = [{'up'}, {'up'}, {'recovering'}]
check("up U recovering（up 直到 recovering 前持续）→ holds",
      run({'path': PATH2, 'formula': 'up U recovering'})['verdict'] == 'holds')

# ── 用例5：复合公式
check("G(up∨down∨recovering) ∧ F(up) → holds",
      run({'path': PATH,
           'formula': 'G(up∨down∨recovering)∧F(up)'})['verdict'] == 'holds')
check("¬(F(down)∧G(¬recovering))? 含 down 且恢复了 → 若 F(down) 真、"
      "G(¬recovering) 假 → 整体真",
      run({'path': PATH,
           'formula': '¬(F(down)∧G(¬recovering))'})['verdict'] == 'holds')

# ── 用例6：诚实边界
check("残缺公式 → parse_error",
      run({'path': PATH, 'formula': 'G('})['verdict'] == 'parse_error')
check("空路径 → empty_path",
      run({'path': [], 'formula': 'G(up)'})['verdict'] == 'empty_path')
check("缺公式 → formula_pending",
      run({'path': PATH})['verdict'] == 'formula_pending')

print("=" * 60)
print(f"结果: {PASS}/14 通过")
raise SystemExit(0 if PASS == 14 else 1)
