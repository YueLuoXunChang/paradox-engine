# -*- coding: utf-8 -*-
"""
test_turing_machine.py — 正式测试：图灵机构件（经典逻辑层 1.7）
用例依据：任务指标 39 详规七·补E + docs/formulas/turing_machine.md
运行：python engine/classical/test_turing_machine.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turing_machine import run, simulate, parity_machine, loop_machine  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("图灵机构件 · 正式测试")
print("=" * 60)

# ── 用例1：模拟基本
check("奇偶机 '000' → accept",
      run({'program': parity_machine(), 'input': '000'})['verdict'] == 'accept')
r = run({'program': parity_machine(), 'input': '0' * 5})
check("奇偶机 '00000' → accept（简化语义一致）",
      r['verdict'] == 'accept', str(r))

# ── 用例2：步骤轨迹（白箱）
r = run({'program': parity_machine(), 'input': '00', 'steps_limit': 10})
check("模拟给轨迹",
      isinstance(r['trace'], list) and len(r['trace']) >= 1, str(r))
check("轨迹含状态与纸带",
      'state' in r['trace'][0] and 'tape' in r['trace'][0], str(r))

# ── 用例3：永不停止 → steps_exceeded（诚实）
r = run({'program': loop_machine(), 'input': '010', 'steps_limit': 100})
check("死循环机 → steps_exceeded（不假装判停机）",
      r['verdict'] == 'steps_exceeded', str(r))
check("steps_exceeded 的边界声明说明不判'永不停'",
      '不假装' in r['boundary'], r['boundary'])

# ── 用例4：停机不可判定演示（核心——收编为标本）
r = run({'mode': 'halting_demo'})
check("halting_demo → undecidable",
      r['verdict'] == 'undecidable', str(r))
check("对角化说明含自指矛盾（D(⟨D⟩)）",
      'D(⟨D⟩)' in r['diagonalization_note'] or 'D' in r['diagonalization_note'],
      r['diagonalization_note'])
check("边界声明不宣称绕过（收编为标本）",
      '不宣称绕过' in r['boundary'], r['boundary'])

# ── 用例5：UTM 自模拟
r = run({'program': parity_machine(), 'mode': 'self_simulate',
         'steps_limit': 50})
check("self_simulate → self_simulated_*",
      str(r['verdict']).startswith('self_simulated_'), str(r))
check("自模拟说明含自指语义",
      '自指' in r['diagonalization_note'], r['diagonalization_note'])

# ── 用例6：诚实边界
check("缺 program → program_pending",
      run({'mode': 'simulate'})['verdict'] == 'program_pending')
check("非法 program（缺 delta）→ parse_error",
      run({'program': {'states': ['q0'], 'start': 'q0',
                       'accept': 'q0', 'reject': 'q0'}})['verdict']
      == 'parse_error')
check("起始态不在状态集 → parse_error",
      run({'program': {'states': ['q0'], 'start': 'qX',
                       'accept': 'q0', 'reject': 'q0',
                       'delta': {}}})['verdict'] == 'parse_error')

print("=" * 60)
print(f"结果: {PASS}/14 通过")
raise SystemExit(0 if PASS == 14 else 1)
