# -*- coding: utf-8 -*-
"""
test_intuitionistic_logic.py — 正式测试：直觉主义逻辑（第 3 层 3.5）
用例依据：详规 §5.1（无排中律——"没构造出来就不算真"）+ Kripke 1959 语义 +
         BHK 解释 + 诚实边界（算不动≠有效、非单调模型拒算）
运行：python engine/cold/test_intuitionistic_logic.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from intuitionistic_logic import PORTS, run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("直觉主义逻辑 · 构造性立场 · 正式测试")
print("=" * 60)

# ── 用例A：Kripke 求值（直觉主义联结词语义）
_CHAIN2 = {'worlds': ['w0', 'w1'], 'order': [('w0', 'w1')]}
ra = run(dict(_CHAIN2, mode='evaluate', formula='P∨¬P',
              valuation={'P': ['w1']}, world='w0'))
check("A1 2 节点链模型里 P∨¬P 在 w0 为假", ra['value'] is False, ra)
check("A2 verdict=evaluated", ra['verdict'] == 'evaluated', ra)
check("A3 同一模型在 w1（P 为真处）P∨¬P 为真",
      run(dict(_CHAIN2, mode='evaluate', formula='P∨¬P',
               valuation={'P': ['w1']}, world='w1'))['value'] is True)
check("A4 ¬ 语义看所有后继：¬P 在 w0 为假（w1 处 P 真）",
      run(dict(_CHAIN2, mode='evaluate', formula='¬P',
               valuation={'P': ['w1']}, world='w0'))['value'] is False)
check("A5 ∧：P∧Q 在 w0 为假（Q 只在 w1 真）",
      run(dict(_CHAIN2, mode='evaluate', formula='P∧Q',
               valuation={'P': ['w0', 'w1'], 'Q': ['w1']},
               world='w0'))['value'] is False)
check("A6 ∧：P∧Q 在 w1 为真",
      run(dict(_CHAIN2, mode='evaluate', formula='P∧Q',
               valuation={'P': ['w0', 'w1'], 'Q': ['w1']},
               world='w1'))['value'] is True)
check("A7 → 语义看所有后继：P→Q 在 w0 为真",
      run(dict(_CHAIN2, mode='evaluate', formula='P→Q',
               valuation={'P': ['w1'], 'Q': ['w1']},
               world='w0'))['value'] is True)
check("A8 缺省 world 取首个节点",
      run({'mode': 'evaluate', 'formula': 'P', 'valuation': {'P': ['w0']},
           'worlds': ['w0'], 'order': []})['value'] is True)
check("A9 非单调赋值 → model_invalid（拒算，不冒充合法模型）",
      run(dict(_CHAIN2, mode='evaluate', formula='P',
               valuation={'P': ['w0']}, world='w0'))['verdict']
      == 'model_invalid')
check("A10 缺 worlds → input_pending",
      run({'mode': 'evaluate', 'formula': 'P'})['verdict']
      == 'input_pending')
check("A11 坏公式 → parse_pending",
      run(dict(_CHAIN2, mode='evaluate', formula='P∧',
               valuation={'P': ['w0']}))['verdict'] == 'parse_pending')
check("A12 world 不在节点集 → input_pending",
      run(dict(_CHAIN2, mode='evaluate', formula='P',
               valuation={'P': ['w0', 'w1']}, world='w9'))['verdict']
      == 'input_pending')

# ── 用例B：反模型搜索（排中律等经典定理在构造性立场不成立）
rb = run({'mode': 'countermodel', 'formula': 'P∨¬P'})
check("B1 排中律 → refuted（非直觉主义有效）",
      rb['verdict'] == 'refuted', rb)
check("B2 反模型 2 个节点", len(rb['countermodel']['worlds']) == 2, rb)
check("B3 反模型字段齐全（节点/序/赋值/反例节点）",
      {'worlds', 'order', 'valuation', 'refuted_at'} <= set(rb['countermodel']),
      sorted(rb['countermodel']))
check("B4 白箱交叉验证：把反模型喂回求值 → 该节点确为假",
      run({'mode': 'evaluate', 'formula': 'P∨¬P',
           'worlds': rb['countermodel']['worlds'],
           'order': rb['countermodel']['order'],
           'valuation': rb['countermodel']['valuation'],
           'world': rb['countermodel']['refuted_at']})['value'] is False)
check("B5 反模型本身合法（赋值单调，求值不报 model_invalid）",
      run({'mode': 'evaluate', 'formula': 'P→P',
           'worlds': rb['countermodel']['worlds'],
           'order': rb['countermodel']['order'],
           'valuation': rb['countermodel']['valuation'],
           'world': rb['countermodel']['refuted_at']})['verdict']
      == 'evaluated')
check("B6 双重否定消去 ¬¬P→P → refuted",
      run({'mode': 'countermodel', 'formula': '¬¬P→P'})['verdict']
      == 'refuted')
check("B7 Peirce 律 ((P→Q)→P)→P → refuted",
      run({'mode': 'countermodel',
           'formula': '((P→Q)→P)→P'})['verdict'] == 'refuted')
check("B8 De Morgan 无效侧 ¬(P∧Q)→(¬P∨¬Q) → refuted",
      run({'mode': 'countermodel',
           'formula': '¬(P∧Q)→(¬P∨¬Q)'})['verdict'] == 'refuted')
check("B9 爆炸律 P→(Q→P) → valid（直觉主义有效）",
      run({'mode': 'countermodel', 'formula': 'P→(Q→P)'})['verdict']
      == 'valid')
check("B10 De Morgan 有效侧 ¬(P∨Q)→(¬P∧¬Q) → valid",
      run({'mode': 'countermodel',
           'formula': '¬(P∨Q)→(¬P∧¬Q)'})['verdict'] == 'valid')
check("B11 P∧Q→P → valid",
      run({'mode': 'countermodel', 'formula': 'P∧Q→P'})['verdict']
      == 'valid')
check("B12 valid 时不给反模型（countermodel=None）",
      run({'mode': 'countermodel', 'formula': 'P∧Q→P'})['countermodel']
      is None)
check("B13 有界搜索（max_worlds=2，需 3 节点的反例）→ not_found_in_limit",
      run({'mode': 'countermodel', 'formula': '¬(P∧Q)→(¬P∨¬Q)',
           'max_worlds': 2})['verdict'] == 'not_found_in_limit')
check("B14 限内未找到时 value 留空（不冒充有效）",
      run({'mode': 'countermodel', 'formula': '¬(P∧Q)→(¬P∨¬Q)',
           'max_worlds': 2})['value'] is None)
check("B15 原子数超算力 → size_limit（不完备就不硬搜）",
      run({'mode': 'countermodel',
           'formula': 'P1∧P2∧P3∧P4'})['verdict'] == 'size_limit')
check("B16 缺 formula → input_pending",
      run({'mode': 'countermodel'})['verdict'] == 'input_pending')
check("B17 坏公式 → parse_pending",
      run({'mode': 'countermodel', 'formula': '∧P'})['verdict']
      == 'parse_pending')
_vb = run({'mode': 'countermodel', 'formula': 'P∧Q→P'})
check("B18 valid 的边界声明给出完备界依据（2^n 有限模型性质）",
      ('2^' in _vb['boundary'] or '完备界' in _vb['boundary']),
      _vb['boundary'])

# ── 用例C：经典 vs 直觉主义对照表
rc = run({'mode': 'compare'})
check("C1 compare → compared", rc['verdict'] == 'compared', rc)
check("C2 缺省 6 行标志性公式", len(rc['comparison']) == 6, rc)
check("C3 每行字段齐全",
      all({'label', 'formula', 'intuitionistic_nd', 'kripke',
           'classical_kind'} <= set(r) for r in rc['comparison']))
_lem = rc['comparison'][0]
check("C4 排中律：经典 tautology 但直觉主义 refuted",
      _lem['classical_kind'] == 'tautology' and _lem['kripke'] == 'refuted',
      _lem)
_dm = [r for r in rc['comparison'] if r['formula'] == '¬(P∨Q)→(¬P∧¬Q)'][0]
check("C5 De Morgan 有效侧：直觉主义 valid（不是全盘否定经典）",
      _dm['kripke'] == 'valid', _dm)
_exp = [r for r in rc['comparison'] if r['formula'] == 'P→(Q→P)'][0]
check("C6 爆炸律：两系统都 valid",
      _exp['kripke'] == 'valid' and _exp['intuitionistic_nd'] == 'proved',
      _exp)
_rc2 = run({'mode': 'compare', 'formulas': [('自定义 P∨¬P', 'P∨¬P')]})
check("C7 支持自定义公式列表", len(_rc2['comparison']) == 1, _rc2)
check("C8 对照表边界声明标注借鉴来源",
      '借鉴' in rc['boundary'], rc['boundary'])

# ── 用例D：接口契约
check("D1 PORTS 声明 in/out", 'in' in PORTS and 'out' in PORTS, PORTS)
check("D2 PORTS.out 声明 verdict/countermodel",
      {'verdict', 'countermodel', 'comparison'} <= set(PORTS['out']), PORTS)
check("D3 run 返回字段齐全",
      {'verdict', 'value', 'countermodel', 'comparison', 'boundary'}
      <= set(rb), sorted(rb))
check("D4 坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("D5 mode 缺省走 countermodel",
      run({'formula': 'P∨¬P'})['verdict'] == 'refuted')

print("=" * 60)
print(f"结果: {PASS}/43 通过")
raise SystemExit(0 if PASS == 43 else 1)
