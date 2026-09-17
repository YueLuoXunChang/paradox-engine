# -*- coding: utf-8 -*-
"""
test_relevance_logic.py — 正式测试：相干逻辑（第 3 层 3.4 论证相关性）
用例依据：详规 §4.2 判定结构（相干检查 → 再走经典有效性）+ §4.3 应用
         （T2 增强：真冲突 vs 话术冲突）+ 诚实边界（算不动不冒充结论）
运行：python engine/cold/test_relevance_logic.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from relevance_logic import PORTS, run  # noqa: E402
from engine.classical import propositional as pl  # noqa: E402

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


print("相干逻辑 · 论证相关性 · 正式测试")
print("=" * 60)

# ── 用例A：相干 + 有效
ra = run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})
check("A1 相干且有效 → relevant_valid",
      ra['verdict'] == 'relevant_valid', ra)
check("A2 共享原子恰为结论用到的 Q", ra['shared_atoms'] == ['Q'], ra)
check("A3 前提原子集完整 {P,Q}", ra['premise_atoms'] == ['P', 'Q'], ra)
check("A4 结论原子集 {Q}", ra['conclusion_atoms'] == ['Q'], ra)
check("A5 经典有效性为 True", ra['classically_valid'] is True, ra)
check("A6 边界声明点明共享原子", '共享' in ra['boundary'], ra['boundary'])

# ── 用例B：形式有效但不相干（详规 §4.2 原文例子）
rb = run({'premises': ['P'], 'conclusion': 'Q∨¬Q'})
check("B1 P ⊢ Q∨¬Q → irrelevant_valid",
      rb['verdict'] == 'irrelevant_valid', rb)
check("B2 无共享原子", rb['shared_atoms'] == [], rb)
check("B3 经典层自身判 valid（对比证据）",
      pl.run({'mode': 'validity', 'premises': ['P'],
              'conclusion': 'Q∨¬Q'})['verdict'] == 'valid')
check("B4 边界点明空洞/不相干",
      ('空洞' in rb['boundary'] or '不相干' in rb['boundary']),
      rb['boundary'])
rb2 = run({'premises': ['A'], 'conclusion': 'B∨¬B'})
check("B5 A ⊢ B∨¬B 同样被判不相干有效",
      rb2['verdict'] == 'irrelevant_valid', rb2)

# ── 用例C：爆炸例（T2 动机：不一致前提推出任意结论）
rc = run({'premises': ['P', '¬P'], 'conclusion': 'Q'})
check("C1 矛盾前提推出无关结论 → irrelevant_valid",
      rc['verdict'] == 'irrelevant_valid', rc)
check("C2 无共享原子", rc['shared_atoms'] == [], rc)
check("C3 经典层判 valid（爆炸有效）",
      pl.run({'mode': 'validity', 'premises': ['P', '¬P'],
              'conclusion': 'Q'})['verdict'] == 'valid')
check("C4 边界说明经典层形式有效",
      '形式有效' in rc['boundary'], rc['boundary'])

# ── 用例D：相干但无效（相干检查不能替代有效性）
rd = run({'premises': ['P'], 'conclusion': 'P∧Q'})
check("D1 共享原子但经典无效 → relevant_invalid",
      rd['verdict'] == 'relevant_invalid', rd)
check("D2 给出反例指派", bool(rd['counterexample']), rd)
check("D3 边界含反例说明", '反例' in rd['boundary'], rd['boundary'])

# ── 用例E：链式相干
re_ = run({'premises': ['P→Q', 'Q→R'], 'conclusion': 'P→R'})
check("E1 传递链相干有效 → relevant_valid",
      re_['verdict'] == 'relevant_valid', re_)
check("E2 共享原子含 P 与 R", set(re_['shared_atoms']) == {'P', 'R'}, re_)

# ── 用例F：冲突定性（真冲突 vs 话术冲突，详规 §4.3）
rf1 = run({'mode': 'conflict', 'prop_a': 'P', 'prop_b': '¬P'})
check("F1 P vs ¬P → real_conflict（真冲突）",
      rf1['verdict'] == 'real_conflict', rf1)
check("F2 真冲突必有共享原子",
      rf1['shared_atoms'] == ['P'], rf1)
rf2 = run({'mode': 'conflict', 'prop_a': 'P→Q', 'prop_b': 'P∧¬Q'})
check("F3 P→Q vs P∧¬Q → real_conflict",
      rf2['verdict'] == 'real_conflict', rf2)
rf3 = run({'mode': 'conflict', 'prop_a': 'P∧¬P', 'prop_b': 'Q∧¬Q'})
check("F4 两个不相干的矛盾 → hollow_conflict（话术冲突）",
      rf3['verdict'] == 'hollow_conflict', rf3)
check("F5 话术冲突零共享原子", rf3['shared_atoms'] == [], rf3)
check("F6 边界点明话术冲突判据",
      '话术冲突' in rf3['boundary'], rf3['boundary'])
check("F7 可同真 → no_conflict",
      run({'mode': 'conflict', 'prop_a': 'P',
           'prop_b': 'Q'})['verdict'] == 'no_conflict')
check("F8 同一命题不构成冲突",
      run({'mode': 'conflict', 'prop_a': 'P',
           'prop_b': 'P'})['verdict'] == 'no_conflict')

# ── 用例G：边界与诚实拦截
check("G1 空输入 → input_pending", run({})['verdict'] == 'input_pending')
check("G2 空前提集 → input_pending",
      run({'premises': [], 'conclusion': 'Q'})['verdict'] == 'input_pending')
check("G3 缺结论 → input_pending",
      run({'premises': ['P']})['verdict'] == 'input_pending')
check("G4 坏前提公式 → parse_pending",
      run({'premises': ['P∧'], 'conclusion': 'Q'})['verdict']
      == 'parse_pending')
check("G5 坏结论公式 → parse_pending",
      run({'premises': ['P'], 'conclusion': '∨Q'})['verdict']
      == 'parse_pending')
check("G6 坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("G7 conflict 缺 prop_b → input_pending",
      run({'mode': 'conflict', 'prop_a': 'P'})['verdict']
      == 'input_pending')
check("G8 conflict 坏 prop_a → parse_pending",
      run({'mode': 'conflict', 'prop_a': 'P∧', 'prop_b': 'Q'})['verdict']
      == 'parse_pending')
rg9 = run({'premises': [f'P{i}' for i in range(12)], 'conclusion': 'P0'})
check("G9 原子超经典层枚举上限 → undecided（算不动不冒充结论）",
      rg9['verdict'] == 'undecided', rg9)
check("G10 算不动时 classically_valid 留空（None）",
      rg9['classically_valid'] is None, rg9)
check("G11 算不动时相干检查仍给出（语法级不过期）",
      rg9['shared_atoms'] == ['P0'], rg9)

# ── 用例H：接口契约
check("H1 PORTS 声明 in/out", 'in' in PORTS and 'out' in PORTS, PORTS)
check("H2 PORTS.out 声明 verdict/shared_atoms",
      {'verdict', 'shared_atoms'} <= set(PORTS['out']), PORTS)
check("H3 run 返回字段齐全",
      {'verdict', 'shared_atoms', 'premise_atoms', 'conclusion_atoms',
       'classically_valid', 'boundary'} <= set(ra), sorted(ra))
check("H4 mode 缺省走 relevance",
      run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})['verdict']
      == 'relevant_valid')

print("=" * 60)
print(f"结果: {PASS}/43 通过")
raise SystemExit(0 if PASS == 43 else 1)
