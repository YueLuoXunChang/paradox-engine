# -*- coding: utf-8 -*-
"""
test_boundary_paradox.py — 正式测试：边界悖论判定（第 2 层 2.4）
用例依据：内部规格 §四（边界态检测/张力/划设即撤销/重生路径 + 诚实边界）
运行：python engine/mechanisms/test_boundary_paradox.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from boundary_paradox import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("边界悖论判定 · 正式测试")
print("=" * 60)

# ── 用例1：停机问题之墙（结构性墙，钉死边界）
r = run({'wall_name': '停机问题之墙',
         'inside': '可判定 可计算 有限步',
         'outside': '不可判定 停机 无限', 'recursive_layer': 0})
check("结构性墙 → wall_exists", r['verdict'] == 'wall_exists', str(r))
check("划设即撤销：self_undermining=True",
      r['self_undermining'] is True, str(r))
check("框架层可撤：removable=True（换框架≠图灵可判）",
      r['removable'] is True, str(r))
check("张力 ∈ [0,1] 且给数值", isinstance(r['tension'], float)
      and 0 <= r['tension'] <= 1, str(r))
check("诊断给建议（≥4 条）", len(r['advice']) >= 4, str(r))
check("建议带重生路径（换框架/升维）",
      any('重生' in a or '升维' in a for a in r['advice']), str(r))
check("边界声明：不宣称绕停机/哥德尔",
      '不宣称' in r['boundary'], r['boundary'])
check("边界声明：张力为工程约定",
      '工程约定' in r['boundary'], r['boundary'])

# ── 用例2：张力单调（内外差异越大张力越高）
r_lo = run({'wall_name': '部门墙', 'inside': '研发 产品',
            'outside': '产品 研发'})
r_hi = run({'wall_name': '文化墙', 'inside': '研发 量化 代码',
            'outside': '市场 直觉 故事'})
check("内外接近 → 低张力", r_lo['tension'] < 0.3, str(r_lo))
check("内外差异大 → 高张力", r_hi['tension'] > 0.6, str(r_hi))
check("高张力建议含检测/重生",
      any('检测' in a or '重生' in a for a in r_hi['advice']), str(r_hi))

# ── 用例3：边界递归 B(B(S))
r = run({'mode': 'b_recurse', 'wall_name': '说谎者之墙'})
check("b_recurse → b_recurse", r['verdict'] == 'b_recurse', str(r))
check("递归标注自悖（划设动作本身在边界内/外）",
      any('自悖' in a or '边界' in a for a in r['advice']), str(r))
check("递归边界声明：不宣称最终边界",
      '最终边界' not in r['boundary'] or '不宣称' in r['boundary'],
      r['boundary'])

# ── 用例4：递归层标注
r = run({'wall_name': '哥德尔墙', 'inside': '可证', 'outside': '不可证',
         'recursive_layer': 3})
check("带递归层 → wall_exists", r['verdict'] == 'wall_exists', str(r))
check("建议提到递归层", any('递归层 3' in a for a in r['advice']), str(r))
check("升维建议层+1（3→4）",
      any('层 3 → 层 4' in a for a in r['advice']), str(r))

# ── 用例5：诚实边界
check("缺墙名 → input_pending", run({})['verdict'] == 'input_pending')
check("坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("无名之墙边界声明诚实",
      '不硬诊' in run({})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/20 通过")
raise SystemExit(0 if PASS == 20 else 1)
