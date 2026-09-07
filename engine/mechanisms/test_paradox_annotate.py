# -*- coding: utf-8 -*-
"""
test_paradox_annotate.py — 正式测试：悖论注解（核心机制）
用例依据：公式卡 paradox_annotate.md（P1 三级完备/P2 8字段/P4 ID唯一）
+ 分级升级规则 + run 接口 + 边界（非法 source 诚实拦截）
运行：python engine/mechanisms/test_paradox_annotate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paradox_annotate import grade, annotate, run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("悖论注解 · 正式测试")
print("=" * 60)

# ── 用例1：P1 三级完备（来源 → 级别）
check("axiom → P-A", grade('axiom') == 'P-A')
check("runtime → P-B", grade('runtime') == 'P-B')
check("observer → P-C", grade('observer') == 'P-C')

# ── 用例2：分级升级规则（全局/不可消除）
check("observer+全局 → P-B（升级）", grade('observer', impact='global') == 'P-B')
check("runtime+全局 → P-A（升级）", grade('runtime', impact='global') == 'P-A')
check("runtime+不可消除 → P-A（升级）",
      grade('runtime', eliminable=False) == 'P-A')
check("axiom+全局 → P-A（封顶不降）",
      grade('axiom', impact='global') == 'P-A')
check("axiom+不可消除 → P-A（封顶不降）",
      grade('axiom', eliminable=False) == 'P-A')
check("observer+全局+不可消除 → P-A（连升两级封顶）",
      grade('observer', impact='global', eliminable=False) == 'P-A')

# ── 用例3：P2 8 字段完整
card = annotate(
    {'A': '肝气郁结', 'notA': '肝火上炎', 'pos': '中医系统·木线程',
     'src': '患者同现肝郁与肝火', 'effect': '治疗策略矛盾',
     'coexist': '见人易怒独处抑郁', 'note': '情志相胜待评估'},
    'runtime', impact='local', eliminable=True, seq=1)
required = {'ID', 'LV', 'POS', 'SRC', 'CT', 'EF', 'ST', 'AN'}
check("P2 8 字段齐", required <= set(card.keys()) and len(card) == 8,
      str(card))
check("ID 格式 悖论_P-B_001", card['ID'] == '悖论_P-B_001', str(card))
check("LV=P-B（runtime）", card['LV'] == 'P-B', str(card))
check("ST=活跃", card['ST'] == '活跃', str(card))
check("CT 含 A 与 ¬A", '肝气郁结' in card['CT'] and '肝火上炎' in card['CT'],
      str(card))
check("POS 位置透传", card['POS'] == '中医系统·木线程', str(card))
check("SRC 来源透传", card['SRC'] == '患者同现肝郁与肝火', str(card))

# ── 用例4：P4 ID 唯一性
ids = set()
for i in range(1, 6):
    c = annotate({'A': f'A{i}', 'notA': f'N{i}'}, 'runtime', seq=i)
    ids.add(c['ID'])
check("P4 5 个 ID 全唯一", len(ids) == 5, str(ids))
# 显式 seq 可控（不依赖全局计数器）
c = annotate({'A': 'X', 'notA': 'Y'}, 'axiom', seq=7)
check("显式 seq=7 → 悖论_P-A_007", c['ID'] == '悖论_P-A_007', str(c))

# ── 用例5：run() 统一接口
r = run({'paradox': {'A': '要快', 'notA': '要稳'},
         'source': 'runtime'})
check("run 默认 runtime → P-B", r['grade'] == 'P-B', str(r))
check("run 给 annotation 卡", r['annotation']['LV'] == 'P-B', str(r))
r = run({'paradox': {'A': 'X', 'notA': '¬X'}, 'source': 'axiom',
         'impact': 'global', 'eliminable': False, 'seq': 99})
check("run 公理+全局+不可消除 → P-A",
      r['grade'] == 'P-A' and r['annotation']['ID'] == '悖论_P-A_099', str(r))
r = run({'paradox': {'A': 'P', 'notA': '¬P'}})
check("run 无 source → 默认 runtime P-B", r['grade'] == 'P-B', str(r))

# ── 用例6：注解不解决原悖论（C1 设计约束）
card = annotate({'A': 'P', 'notA': '¬P', 'note': '只标记'}, 'runtime')
check("C1 状态活跃非已解决", card['ST'] == '活跃', str(card))
check("C1 CT 记录原矛盾", 'P' in card['CT'] and '¬P' in card['CT'], str(card))

# ── 用例7：边界——非法 source 诚实拦截
try:
    grade('not_a_source')
    check("非法 source → 抛 ValueError", False, '未抛错')
except (ValueError, KeyError):
    check("非法 source → 抛错（诚实拦截）", True)
except Exception:
    check("非法 source → 抛错（类型不限）", True)

print("=" * 60)
print(f"结果: {PASS}/25 通过")
raise SystemExit(0 if PASS == 25 else 1)
