# -*- coding: utf-8 -*-
"""
test_many_valued.py — 正式测试：多值逻辑（Kleene 强三值 K3 · Łukasiewicz 三值 Ł3）
用例依据：两套三值的真值表与设计值口径（Kleene 1952 / Łukasiewicz 1920 标准结果）：
  · K3 的 → 是 max(1−a, b)；Ł3 的 → 是 min(1, 1−a+b)，其余联结词两套相同；
  · K3 **没有重言式**（全 ½ 指派下一切皆 ½）；Ł3 有重言式但没有排中律；
  · "公式是重言式"与"推理有效"不是一回事，本文件专门钉一条。
运行：python engine/cold/test_many_valued.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold.many_valued import run  # noqa: E402

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


def v(formula, logic='k3', **kw):
    return run(dict(formula=formula, logic=logic, **kw))


print("多值逻辑（K3 / Ł3） · 正式测试")
print("=" * 60)

# ── 一、求值：未知会传播
check("未知传播：P ∧ Q（只知道 P 真）→ ½",
      v('P ∧ Q', assignment={'P': 1})['value'] == 0.5,
      str(v('P ∧ Q', assignment={'P': 1})))
check("未知传播：P ∨ Q（只知道 P 真）→ 1（真的一侧够定结论）",
      v('P ∨ Q', assignment={'P': 1})['value'] == 1.0)
check("没给取值的原子按 ½ 算，并在边界里说明",
      v('P → Q', assignment={'P': 1})['value'] == 0.5
      and '未知' in v('P → Q', assignment={'P': 1})['boundary'])
check("取值写法都认（1/0/½、T/F/U、真/假/未知）且结果一致",
      v('P', assignment={'P': 'U'})['value'] == 0.5
      and v('P', assignment={'P': 'F'})['value'] == 0.0
      and v('P', assignment={'P': '真'})['value'] == 1.0)

# ── 二、两套三值的差别只在蕴含
check("同一个 ½→½：K3 得 ½、Ł3 得 1（两套只差在蕴含——最容易被混为一谈的点）",
      v('P → P', assignment={'P': '½'})['value'] == 0.5
      and v('P → P', logic='l3', assignment={'P': '½'})['value'] == 1.0)
check("两套对 ¬ 一致：¬½ = ½",
      v('¬P', assignment={'P': '½'})['value'] == 0.5
      and v('¬P', logic='l3', assignment={'P': '½'})['value'] == 0.5)
check("两套对 ∧ / ∨ 一致：都是 min / max",
      v('P ∧ Q', assignment={'P': '½', 'Q': 0})['value'] == 0.0
      and v('P ∨ Q', logic='l3', assignment={'P': '½', 'Q': 0})['value'] == 0.5)

# ── 三、K3 没有重言式（这条最容易反直觉）
r = v('P → P')
check("K3 里连 P → P 都不是重言式，并给出反例 P = ½",
      r['verdict'] == 'not_tautology' and r['counterexample'] == {'P': '½'},
      str(r))
check("K3 里排中律、不矛盾律同样不成立",
      v('P ∨ ¬P')['verdict'] == 'not_tautology'
      and v('¬(P ∧ ¬P)')['verdict'] == 'not_tautology')

# ── 四、Ł3：有重言式，但没有排中律
check("Ł3 里 P → P 是重言式（与 K3 对照）",
      v('P → P', logic='l3')['verdict'] == 'tautology')
check("Ł3 里排中律不成立，反例 P = ½",
      v('P ∨ ¬P', logic='l3')['verdict'] == 'not_tautology'
      and v('P ∨ ¬P', logic='l3')['counterexample'] == {'P': '½'})
check("Ł3 里双重否定消去成立、K3 里不成立",
      v('¬¬P → P', logic='l3')['verdict'] == 'tautology'
      and v('¬¬P → P', logic='k3')['verdict'] == 'not_tautology')
check("Ł3 的特征式 (P→Q) ∨ (Q→P) 是重言式（K3 里不是）",
      v('(P → Q) ∨ (Q → P)', logic='l3')['verdict'] == 'tautology'
      and v('(P → Q) ∨ (Q → P)', logic='k3')['verdict'] == 'not_tautology')

# ── 五、"公式是重言式" ≠ "推理有效"（一条专门钉住，免得读的人混）
mp_formula_k3 = v('(P ∧ (P → Q)) → Q')
mp_formula_l3 = v('(P ∧ (P → Q)) → Q', logic='l3')
mp_infer_k3 = run({'mode': 'validity', 'logic': 'k3', 'premises': ['P', 'P → Q'],
                   'conclusion': 'Q'})
mp_infer_l3 = run({'mode': 'validity', 'logic': 'l3', 'premises': ['P', 'P → Q'],
                   'conclusion': 'Q'})
check("肯定前件的**公式形式**在两套三值里都不是重言式",
      mp_formula_k3['verdict'] == 'not_tautology'
      and mp_formula_l3['verdict'] == 'not_tautology',
      str((mp_formula_k3['verdict'], mp_formula_l3['verdict'])))
check("肯定前件的**推理形式**在两套三值里都有效（两者不是一回事）",
      mp_infer_k3['verdict'] == 'valid' and mp_infer_l3['verdict'] == 'valid',
      str((mp_infer_k3['verdict'], mp_infer_l3['verdict'])))

# ── 六、推理判定：反例是"前提全真而结论不真"的指派（自查一遍）
bad = run({'mode': 'validity', 'logic': 'k3', 'premises': ['P → Q'],
           'conclusion': 'P'})
check("无效推理给反例指派，且该指派下前提确实为 1、结论确实不为 1",
      bad['verdict'] == 'invalid' and bad['counterexample']
      and v('P → Q', assignment=bad['counterexample'])['value'] == 1.0
      and v('P', assignment=bad['counterexample'])['value'] != 1.0,
      str(bad['counterexample']))

# ── 七、三套对照表
tbl = {x['formula']: x for x in run({'mode': 'compare'})['table']}
check("对照表覆盖代表公式（排中律/同一律/不矛盾律/特征式/双重否定/肯定前件）",
      len(tbl) == 6 and 'P ∨ ¬P' in tbl and '(P ∧ (P → Q)) → Q' in tbl,
      str(sorted(tbl)))
check("对照表：六个式子在经典二值下都是重言式",
      all(x['classical'] for x in tbl.values()),
      str({k: x['classical'] for k, x in tbl.items()}))
check("对照表：K3 一列全是假（K3 本就没有重言式，与定理一致）",
      not any(x['k3'] for x in tbl.values()),
      str({k: x['k3'] for k, x in tbl.items()}))
check("对照表：Ł3 一列分出两组（成立：同一律/特征式/双重否定；不成立：排中律/不矛盾律/肯定前件式）",
      {k for k, x in tbl.items() if x['l3']}
      == {'P → P', '(P → Q) ∨ (Q → P)', '¬¬P → P'},
      str({k: x['l3'] for k, x in tbl.items()}))

# ── 八、诚实边界
check("坏公式 → parse_error", v('P ∨')['verdict'] == 'parse_error')
check("坏 logic → input_pending（只认 k3/l3）",
      run({'formula': 'P', 'logic': 'x'})['verdict'] == 'input_pending')
check("坏取值（2）→ input_pending（取值只认 1/0/½）",
      v('P', assignment={'P': 2})['verdict'] == 'input_pending')
check("缺 formula / 缺参 → input_pending",
      run({})['verdict'] == 'input_pending'
      and run({'mode': 'validity', 'premises': ['P']})['verdict']
      == 'input_pending')
check("原子数超上限 → size_limit（3^n 不硬枚举）",
      v(' ∧ '.join('P%d' % i for i in range(9)))['verdict'] == 'size_limit')

# ── 九、输出契约与出处交代
r = v('P ∨ ¬P', logic='l3')
check("结论带边界声明：写明设计值、两套差别、以及与 Belnap 四值不是一回事",
      '设计值' in r['boundary'] and 'Belnap' in r['boundary']
      and '不决策' in r['boundary'], str(r['boundary'][:80]))
check("求值结论带 atoms 清单",
      v('P ∧ Q', assignment={'P': 1})['atoms'] == ['P', 'Q'])

print("=" * 60)
print(f"结果: {PASS}/27 通过")
raise SystemExit(0 if PASS == 27 else 1)
