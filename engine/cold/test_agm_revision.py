# -*- coding: utf-8 -*-
"""
test_agm_revision.py — 正式测试：AGM 信念修正 · 非单调推理（第 3 层 3.3）
用例依据：AGM 三公理（成功性/包含性/一致性）逐条可验 + Reiter 默认逻辑的
         可废止性 + 内部规格（T5 知识更新痛点：新信息来了旧结论还成立吗）
运行：python engine/cold/test_agm_revision.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from agm_revision import PORTS, run  # noqa: E402
from engine.classical.propositional import run as pl  # noqa: E402

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


def sat(formulas):
    """独立复算：formulas 全体可同时为真吗（不信构件自报，另算一遍）。"""
    if not formulas:
        return True
    conj = '∧'.join(f'({f})' for f in formulas)
    return pl({'formula': conj, 'mode': 'satisfiable'}).get('verdict') \
        == 'satisfiable'


print("AGM 信念修正 · 非单调推理 · 正式测试")
print("=" * 60)

# ── 用例A：一致 → 直接扩张（AGM 扩张操作）
ra = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': 'Q'})
check("A1 一致 → consistent（直接扩张）", ra['verdict'] == 'consistent', ra)
check("A2 无信念被放弃", ra['dropped'] == [], ra)
check("A3 旧信念全保留", ra['kept'] == ['P→Q', 'P'], ra)
check("A4 边界声明 AGM 扩张操作", '扩张' in ra['boundary'], ra['boundary'])

# ── 用例B：不一致 → 最小放弃收缩（AGM 修正）
rb = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
check("B1 不一致 → revised", rb['verdict'] == 'revised', rb)
check("B2 最小性：只放弃 1 条（非 2 条）", len(rb['dropped']) == 1, rb)
check("B3 新信息进入信念集", '¬Q' in rb['kept'], rb)
check("B4 修正后整体一致（独立复算 satisfiable）", sat(rb['kept']), rb)
check("B5 规模守恒 |B'|=|B|-1+1", len(rb['kept']) == 2, rb)

# ── 用例C：AGM 三公理逐条验证
check("C1 成功性：φ ∈ B'", '¬Q' in rb['kept'], rb)
check("C2 包含性：B'-{φ} ⊆ B",
      set(rb['kept']) - {'¬Q'} <= {'P→Q', 'P'}, rb)
check("C3 一致性：B' 一致", sat(rb['kept']), rb)
check("C4 边界如实声明三公理", '三公理' in rb['boundary'], rb['boundary'])

# ── 用例D：优先级（entrenchment 信念度）决定放弃对象
rd = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
          'priorities': {'P→Q': 1, 'P': 10}})
check("D1 信念度低者先弃 → 放弃 P→Q", rd['dropped'] == ['P→Q'], rd)
check("D2 高信念度的 P 被保住", 'P' in rd['kept'], rd)
rd2 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
           'priorities': {'P→Q': 10, 'P': 1}})
check("D3 优先级反转 → 改为放弃 P", rd2['dropped'] == ['P'], rd2)
rd3 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
check("D4 无优先级时结果确定（可复现）",
      rd3['dropped'] == rb['dropped'], (rd3, rb))
check("D5 未定优先级不是任意乱弃，而是同规模候选中择一",
      len(rd3['dropped']) == 1, rd3)

# ── 用例E：旧信念集自身就不一致
re_ = run({'mode': 'revise', 'beliefs': ['P', '¬P'], 'new_info': 'Q'})
check("E1 旧信念自相矛盾也算不一致 → revised",
      re_['verdict'] == 'revised', re_)
check("E2 仍按最小放弃（恰弃 1 条）", len(re_['dropped']) == 1, re_)
check("E3 收缩后一致", sat(re_['kept']), re_)

# ── 用例F：多步修正（黑天鹅：撤销旧结论后继续用新信念）
rf1 = run({'mode': 'revise', 'beliefs': ['P→Q', 'P'], 'new_info': '¬Q'})
rf2 = run({'mode': 'revise', 'beliefs': rf1['kept'], 'new_info': 'R'})
check("F1 第二步（已含 ¬Q）再收新信息 → 一致扩张",
      rf2['verdict'] == 'consistent', rf2)
check("F2 争议信念不再复活（¬Q 始终在）",
      '¬Q' in rf2['kept'], rf2)
check("F3 链式可用：kept 可直接喂回 run", isinstance(rf2['kept'], list), rf2)

# ── 用例G：非单调默认推理（可废止）
rg = run({'mode': 'default', 'defaults': [('鸟', '会飞')], 'facts': ['鸟']})
check("G1 前提满足且无例外 → holds",
      rg['conclusions'][0]['status'] == 'holds', rg)
check("G2 结论表含默认规则原文",
      rg['conclusions'][0]['default'] == '鸟 ⇒ 会飞', rg)
check("G3 理由字段非空（白箱）",
      bool(rg['conclusions'][0]['reason']), rg)
rg2 = run({'mode': 'default', 'defaults': [('鸟', '会飞')],
           'facts': ['鸟', '鸟(企鹅)'], 'exceptions': ['鸟(企鹅)']})
check("G4 例外命中 → blocked（可废止，非矛盾）",
      rg2['conclusions'][0]['status'] == 'blocked', rg2)
check("G5 阻断理由写明命中的例外",
      '企鹅' in rg2['conclusions'][0]['reason'], rg2)
rg3 = run({'mode': 'default', 'defaults': [('鸟', '会飞')], 'facts': ['石头']})
check("G6 前提未满足 → not_applicable",
      rg3['conclusions'][0]['status'] == 'not_applicable', rg3)
rg4 = run({'mode': 'default',
           'defaults': [('鸟', '会飞'), ('企鹅', '会游泳')],
           'facts': ['鸟', '企鹅'], 'exceptions': []})
check("G7 多默认规则各自判定", len(rg4['conclusions']) == 2, rg4)
check("G8 默认推理不给绝对真值（标可废止）",
      '可废止' in rg4['boundary'], rg4['boundary'])

# ── 用例H：边界与诚实拦截
check("H1 坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("H2 缺新信息 → input_pending",
      run({'mode': 'revise', 'beliefs': ['P']})['verdict']
      == 'input_pending')
check("H3 空信念集 → input_pending",
      run({'mode': 'revise', 'beliefs': [], 'new_info': 'Q'})['verdict']
      == 'input_pending')
check("H4 mode=default 缺 defaults → input_pending",
      run({'mode': 'default'})['verdict'] == 'input_pending')
rh = run({'mode': 'revise', 'beliefs': [f'P{i}' for i in range(15)],
          'new_info': 'Q', 'max_beliefs': 12})
check("H5 超规模上限 → size_limit", rh['verdict'] == 'size_limit', rh)
check("H6 超限时不硬给结果（kept/dropped 空）",
      rh['kept'] == [] and rh['dropped'] == [], rh)
rh2 = run({'mode': 'revise', 'beliefs': [f'P{i}' for i in range(12)],
           'new_info': 'Q', 'max_beliefs': 12})
check("H7 信念数恰在上限内 → 不被 size_limit 挡住",
      rh2['verdict'] != 'size_limit', rh2)
check("H8 原子数超经典层枚举上限(10) → undecided（算不动 ≠ 不一致）",
      rh2['verdict'] == 'undecided', rh2)
check("H9 算不动时不乱弃信念（dropped 空）", rh2['dropped'] == [], rh2)
check("H10 算不动时声明原因",
      '算不动' in rh2['boundary'], rh2['boundary'])
check("H11 新信息自身不可满足 → new_info_unsatisfiable（不硬凑）",
      run({'mode': 'revise', 'beliefs': ['P'], 'new_info': 'Q∧¬Q'})
      ['verdict'] == 'new_info_unsatisfiable')
check("H12 边界声明含枚举计数（白箱）",
      '枚举' in rb['boundary'], rb['boundary'])

# ── 用例I：接口契约
check("I1 PORTS 声明 in/out", 'in' in PORTS and 'out' in PORTS, PORTS)
check("I2 PORTS.out 声明 verdict/kept/dropped",
      {'verdict', 'kept', 'dropped'} <= set(PORTS['out']), PORTS)
check("I3 run 返回字段齐全",
      {'verdict', 'kept', 'dropped', 'conclusions', 'boundary'}
      <= set(rb), sorted(rb))
check("I4 mode 缺省走 revise（beliefs+new_info 即可）",
      run({'beliefs': ['P→Q', 'P'], 'new_info': 'Q'})['verdict']
      == 'consistent')

print("=" * 60)
print(f"结果: {PASS}/48 通过")
raise SystemExit(0 if PASS == 48 else 1)
