# -*- coding: utf-8 -*-
"""
test_counterpoint_gen.py — 正式测试：对位创生第三态（第 2 层 2.6）
用例依据：内部规格 41 §六（对立交汇/三型耦合/第三态候选+依据 + 诚实边界）
运行：python engine/mechanisms/test_counterpoint_gen.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from counterpoint_gen import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("对位创生第三态 · 正式测试")
print("=" * 60)

# ── 用例1：反向耦合（自动探测）——要快 vs 要稳（41 走查例）
r = run({'thesis': '要快', 'antithesis': '要稳'})
check("要快 vs 要稳 → third_state", r['verdict'] == 'third_state', str(r))
check("自动判 reverse", r['coupling'] == 'reverse', str(r))
check("第三态给 label", bool(r['third_state']['label']), str(r))
check("类型：振荡→共振带新意义",
      '共振带' in r['third_state']['type_note'], str(r))
check("生成依据 4 步白箱", len(r['derivation']) == 4, str(r))
check("依据含两立场", any('要快' in d for d in r['derivation'])
      and any('要稳' in d for d in r['derivation']), str(r))
check("边界：候选不是正确答案",
      '候选' in r['boundary'] and '不决策' in r['boundary'], r['boundary'])
check("边界：矛盾仍在（创生≠消灭）", '矛盾仍在' in r['boundary'],
      r['boundary'])

# ── 用例2：自由 vs 秩序（反义对 → 反向）
r = run({'thesis': '自由', 'antithesis': '秩序'})
check("自由 vs 秩序 → reverse", r['coupling'] == 'reverse', str(r))
check("自由×秩序给候选",
      r['verdict'] == 'third_state' and bool(r['third_state']['label']),
      str(r))

# ── 用例3：显式 same → 两全快速收敛
r = run({'thesis': '要快', 'antithesis': '要省时', 'coupling': 'same',
         'dimensions': ['时间']})
check("显式 same → 保持 same", r['coupling'] == 'same', str(r))
check("same 类型：快速收敛（两全）",
      '快速收敛' in r['third_state']['type_note'], str(r))
check("same 依据提到合并特征",
      any('合并' in d for d in r['derivation']), str(r))

# ── 用例4：跨维度交叉 → cross（自动探测）
r = run({'thesis': '要快', 'antithesis': '要便宜',
         'dimensions': ['时间', '成本']})
check("要快 vs 要便宜 → cross", r['coupling'] == 'cross', str(r))
check("cross 类型：部分收敛+部分振荡",
      '部分收敛' in r['third_state']['type_note'], str(r))
check("cross 依据提到桥结构",
      any('桥' in d for d in r['derivation']), str(r))
check("维度进候选生成依据", any('时间' in d and '成本' in d
      for d in r['derivation']), str(r))

# ── 用例5：诚实边界
check("缺 antithesis → input_pending",
      run({'thesis': '要快'})['verdict'] == 'input_pending')
check("缺双方 → input_pending", run({})['verdict'] == 'input_pending')
check("坏 coupling → input_pending",
      run({'thesis': 'A', 'antithesis': 'B',
           'coupling': 'xx'})['verdict'] == 'input_pending')
check("input_pending 带诚实声明", '不硬' in run({})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/21 通过")
raise SystemExit(0 if PASS == 21 else 1)
