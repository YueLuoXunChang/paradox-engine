# -*- coding: utf-8 -*-
"""
test_wall_pipeline.py — 正式测试：撞墙处理管线 A（第 2 层编排）
用例依据：内部规格 §七（五选一诊断 + 各步白箱 + 诚实边界）
运行：python engine/mechanisms/test_wall_pipeline.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wall_pipeline import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("撞墙处理管线 A · 正式测试")
print("=" * 60)

# ── 用例1：说谎者句 → 共振带自指（核心卖点）
r = run({'wall': '这句话是假的'})
check("说谎者 → resonance_selfref", r['verdict'] == 'resonance_selfref',
      str(r))
check("诊断带 label", bool(r['diagnosis']['label']), str(r))
check("注解 P-A（结构性自指）", r['annotation'].get('LV') == 'P-A', str(r))
check("测墙 μ=1.0（mu2 自指直判）",
      abs(r['diagnosis'].get('mu', 0) - 1.0) < 1e-9, str(r))
check("6 步管线白箱齐全", len(r['steps']) == 6, str(r))
check("2.1 测墙 status=run", r['steps'][0]['status'] == 'run', str(r))
check("2.3 钻墙给出共振带态",
      r['steps'][2]['detail'].get('verdict') in
      ('resonance_band', 'liar_cycle'), str(r))
check("2.4 看墙给张力",
      isinstance(r['steps'][3]['detail'].get('tension'), float), str(r))
check("可选步 2.5/2.6 skip（诚实标注）",
      r['steps'][4]['status'] == 'skip' and r['steps'][5]['status'] == 'skip',
      str(r))
check("边界：五选一是诊断不决策", '诊断' in r['boundary']
      and '不决策' in r['boundary'], r['boundary'])
check("边界：共振带≠判真值", '≠判真值' in r['boundary'], r['boundary'])

# ── 用例2：哥德尔句 → 结构性墙
r = run({'wall': '本句不可证'})
check("哥德尔 → structural_wall", r['verdict'] == 'structural_wall', str(r))
check("哥德尔注解 P-A", r['annotation'].get('LV') == 'P-A', str(r))
check("边界：不宣称判定（不推翻定理）",
      '不宣称' in r['boundary'], r['boundary'])

# ── 用例3：对立立场 → 可创生
r = run({'thesis': '要快', 'antithesis': '要稳'})
check("对立 → creatable", r['verdict'] == 'creatable', str(r))
check("2.6 创生 status=run", r['steps'][5]['status'] == 'run', str(r))
check("2.6 给第三态候选 label",
      bool(r['steps'][5]['detail'].get('third_state')), str(r))
check("2.3 钻墙 skip（无自指文本）",
      r['steps'][2]['status'] == 'skip', str(r))

# ── 用例4：带事件 → 旁路也跑
r = run({'wall': '这句话是假的', 'events': ['建模', '发现矛盾', '继续']})
check("2.5 旁路 status=run", r['steps'][4]['status'] == 'run', str(r))
check("旁路 main_ran=3", r['steps'][4]['detail'].get('main_ran') == 3,
      str(r))

# ── 用例5：自定义修正发散句（墙描述不含预设自指词 → iterate 默认翻转）
r = run({'wall': '某过程持续放大'})
check("非预设自指 → 仍走管线给诊断",
      r['verdict'] in ('resonance_selfref', 'benign_selfref',
                       'divergent_wall', 'decidable_elsewhere'), str(r))

# ── 用例6：诚实边界
check("无线索 → input_pending", run({})['verdict'] == 'input_pending')
check("input_pending 声明诚实", '不硬判' in run({})['boundary'])
check("只给 wall 不给对立 → 2.6 skip",
      run({'wall': '这句话是假的'})['steps'][5]['status'] == 'skip')

print("=" * 60)
print(f"结果: {PASS}/24 通过")
raise SystemExit(0 if PASS == 24 else 1)
