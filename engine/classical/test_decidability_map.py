# -*- coding: utf-8 -*-
"""
test_decidability_map.py — 正式测试：算术层级 · 可判定片段地图（阶段 7）
用例依据：蓝图 轨 A·A1（算术层级借数学底座，标注来源）+ 墙的精确地图
         验收：自测 + 正式 + 公式卡（docstring）+ 与 1.6/1.7/2.3 接线演示
运行：python engine/classical/test_decidability_map.py
"""
import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from decidability_map import (  # noqa: E402
    DECIDABLE, FRAGMENTS, HIERARCHY, SEMI, UNDECIDABLE, run)

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("可判定片段地图 · 正式测试")
print("=" * 60)

# ── 用例A：可判片段（Δ1）
ra = run({'mode': 'lookup', 'system': 'propositional'})
check("A1 命题逻辑 → found", ra['verdict'] == 'found', ra)
check("A2 判定性=可判定", ra['entry']['decidability'] == DECIDABLE, ra)
check("A3 层级=Δ1", ra['entry']['hierarchy'] == 'Δ1', ra)
check("A4 标注引用来源（Cook 1971）", '1971' in ra['entry']['source'], ra)
check("A5 引擎有对应构件且可用",
      ra['entry']['engine_available'] is True, ra)
check("A6 复杂度栏给出公认结论（NP 完全）",
      'NP' in (ra['entry']['complexity'] or ''), ra)
check("A7 附中文判定性说明", '可判定' in ra['entry']['decidability_cn'], ra)

# ── 用例B：不可判片段（停机 / PA / 二阶 / 任意框架）
rb = run({'mode': 'lookup', 'system': 'halting'})
check("B1 停机问题 → 不可判定",
      rb['entry']['decidability'] == UNDECIDABLE, rb)
check("B2 停机层级标 Σ1 完全", 'Σ1 完全' in rb['entry']['hierarchy'], rb)
check("B3 出处标 Turing 1936", 'Turing 1936' in rb['entry']['source'], rb)
check("B4 引擎侧诚实说明（演示非判定器）",
      '不是判定器' in rb['entry']['engine_note'], rb)
rp = run({'mode': 'lookup', 'system': 'full_arithmetic'})
check("B5 PA → 不可判定（Gödel 1931）",
      rp['entry']['decidability'] == UNDECIDABLE
      and '1931' in rp['entry']['source'], rp)
check("B6 PA 引擎侧明确划界（不碰）",
      '不碰' in rp['entry']['engine_note'], rp)
rs = run({'mode': 'lookup', 'system': 'second_order'})
check("B7 二阶逻辑 → 不可判定",
      rs['entry']['decidability'] == UNDECIDABLE, rs)
rm = run({'mode': 'lookup', 'system': 'modal_all_frames'})
check("B8 任意框架模态 → 不可判定（Thomason 1975）",
      rm['entry']['decidability'] == UNDECIDABLE, rm)
check("B9 具名框架模态 → 可判（对照：语法同、量化范围不同）",
      run({'mode': 'lookup',
           'system': 'modal_k_s4_s5'})['entry']['decidability']
      == DECIDABLE)

# ── 用例C：半可判定（只一侧可枚举）
rr = run({'mode': 'lookup', 'system': 'resolution'})
check("C1 一阶归结 → 半可判定", rr['entry']['decidability'] == SEMI, rr)
check("C2 半可判定给出诚实说明（证不出来不等于可满足）",
      '不等于' in rr['entry']['engine_note'], rr)
rf = run({'mode': 'lookup', 'system': 'first_order'})
check("C3 一般一阶逻辑 → 不可判定（Church/Turing 1936）",
      rf['entry']['decidability'] == UNDECIDABLE
      and '1936' in rf['entry']['source'], rf)
check("C4 引擎只做有限论域片段（诚实）",
      '有限论域' in rf['entry']['engine_note'], rf)

# ── 用例D：未实现片段诚实标注（不假装能算）
rd = run({'mode': 'lookup', 'system': 'presburger'})
check("D1 Presburger 可判定但引擎未实现",
      rd['entry']['decidability'] == DECIDABLE
      and rd['entry']['engine_available'] is False, rd)
check("D2 未实现条目给出「未实现」说明",
      '未实现' in rd['entry']['engine_note'], rd)
check("D3 地图里未实现条目 ≥3（诚实空白）",
      sum(1 for e in FRAGMENTS.values()
          if e.get('engine_component') is None) >= 3,
      str(sum(1 for e in FRAGMENTS.values()
              if e.get('engine_component') is None)))

# ── 用例E：算术层级
re_ = run({'mode': 'hierarchy', 'level': 'Σ1'})
check("E1 Σ1 → level_found", re_['verdict'] == 'level_found', re_)
check("E2 Σ1 定义含「枚举」", '枚举' in re_['level']['definition'], re_)
check("E3 Σ1 完全问题含停机",
      any('停机' in p for p in re_['level']['complete_problems']), re_)
check("E4 Σ1 引擎承诺=只在枚举到「是」时给结论",
      '只在枚举到' in re_['level']['engine_promise'], re_)
r2 = run({'mode': 'hierarchy', 'level': 'Π2'})
check("E5 Π2 完全问题含 Tot（处处停机）",
      any('Tot' in p for p in r2['level']['complete_problems']), r2)
check("E6 Δ1/Σ1/Π1/Σ2/Π2 五层齐全",
      {'Δ1', 'Σ1', 'Π1', 'Σ2', 'Π2'} <= set(HIERARCHY), sorted(HIERARCHY))
check("E7 每层都给出处（借鉴区标注）",
      all(HIERARCHY[k].get('source') for k in HIERARCHY))
check("E8 每层都声明引擎承诺（边界可查）",
      all(HIERARCHY[k].get('engine_promise') for k in HIERARCHY))

# ── 用例F：墙体地图
rf2 = run({'mode': 'map'})
check("F1 map → mapped", rf2['verdict'] == 'mapped', rf2)
check("F2 地图条目 ≥15 条", len(rf2['fragments']) >= 15,
      str(len(rf2['fragments'])))
check("F3 三类判定性都有条目",
      {DECIDABLE, SEMI, UNDECIDABLE}
      <= {e['decidability'] for e in rf2['fragments']},
      sorted({e['decidability'] for e in rf2['fragments']}))
check("F4 边界声明标明「参考文献表非判定过程」",
      '不是' in rf2['boundary'] and '判定过程' in rf2['boundary'],
      rf2['boundary'])

# ── 用例G：接线演示（1.6 λ / 1.7 图灵机 / 2.3 递归修正 + 可判片段）
rg = run({'mode': 'demo'})
check("G1 demo → demo", rg['verdict'] == 'demo', rg)
check("G2 演示 5 件全真跑（无一件跑不动）",
      all(x['verdict'] for x in rg['fragments']), rg['fragments'])
_demo = {x['component']: x for x in rg['fragments']}
check("G3 接线 1.6 λ 演算（自应用无范式/步数上限）",
      _demo['classical.lambda_calculus']['verdict'] in
      ('step_limit', 'normalized'), _demo['classical.lambda_calculus'])
check("G4 接线 1.7 图灵机（停机 → undecidable）",
      _demo['classical.turing_machine']['verdict'] == 'undecidable',
      _demo['classical.turing_machine'])
check("G5 接线 2.3 递归修正（说谎者振荡三态）",
      _demo['mechanisms.selfref_fixpoint']['verdict'] == 'liar_cycle',
      _demo['mechanisms.selfref_fixpoint'])
check("G6 可判片段（命题逻辑）真给结论 valid",
      _demo['classical.propositional']['verdict'] == 'valid',
      _demo['classical.propositional'])

# ── 用例H：不变式——表里声明的引擎构件必须真存在、真能跑
_bad = []
for key, e in FRAGMENTS.items():
    comp = e.get('engine_component')
    if comp is None:
        continue
    try:
        m = importlib.import_module(f'engine.{comp}')
        assert hasattr(m, 'run') and hasattr(m, 'PORTS'), comp
    except Exception as ex:  # noqa: BLE001
        _bad.append(f'{key}→{comp}: {ex}')
check("H1 表里每个 engine_component 都真存在且有 run/PORTS", not _bad,
      str(_bad))
check("H2 标为 available 的条目 ≥8（引擎覆盖面）",
      sum(1 for e in FRAGMENTS.values()
          if e.get('engine_component')) >= 8,
      str(sum(1 for e in FRAGMENTS.values() if e.get('engine_component'))))

# ── 用例I：诚实边界与接口契约
check("I1 坏 mode → input_pending",
      run({'mode': 'xx'})['verdict'] == 'input_pending')
check("I2 缺 system → input_pending（附可用键）",
      run({'mode': 'lookup'})['verdict'] == 'input_pending'
      and 'propositional' in run({'mode': 'lookup'})['boundary'])
check("I3 未知 system → unknown_system（不编造）",
      run({'mode': 'lookup', 'system': '玄学逻辑'})['verdict']
      == 'unknown_system')
check("I4 未知层级 → unknown_level",
      run({'mode': 'hierarchy', 'level': 'Σ9'})['verdict']
      == 'unknown_level')
check("I5 返回字段齐全",
      {'verdict', 'entry', 'level', 'fragments', 'boundary'}
      <= set(rf2), sorted(rf2))
check("I6 每条目 source 非空（借鉴区逐条标源）",
      all(e.get('source') for e in FRAGMENTS.values()),
      [k for k, e in FRAGMENTS.items() if not e.get('source')])
check("I7 每条目 engine_note 非空（引擎侧诚实说明）",
      all(e.get('engine_note') for e in FRAGMENTS.values()),
      [k for k, e in FRAGMENTS.items() if not e.get('engine_note')])
check("I8 PORTS 声明 in/out 且 out 含 entry/level",
      {'entry', 'level'} <= set(__import__('decidability_map').PORTS['out']))

print("=" * 60)
print(f"结果: {PASS}/51 通过")
raise SystemExit(0 if PASS == 51 else 1)
