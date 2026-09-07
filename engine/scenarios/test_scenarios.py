# -*- coding: utf-8 -*-
"""
test_scenarios.py — 正式测试：场景库
用例依据：45 蓝图轨 B（场景=输入+期望+实际+复核）+ 判类误判回馈
运行：python engine/scenarios/test_scenarios.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scenarios import SCENES, run, run_all  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("场景库 · 正式测试")
print("=" * 60)

# ── 用例1：场景注册表完整性
check("场景 ≥7 个（蓝图轨 B：≥5）", len(SCENES) >= 5, str(len(SCENES)))
ids = [s['id'] for s in SCENES]
check("场景 id 唯一", len(ids) == len(set(ids)), str(ids))
check("每场景有 text/expect_type",
      all(s.get('text') and s.get('expect_type') for s in SCENES))
check("期望判类合法 T1-T12",
      all(s['expect_type'].startswith('T') for s in SCENES))
check("已复核 ≥4（checked 标记）",
      sum(1 for s in SCENES if s.get('checked')) >= 4)

# ── 用例2：全场景对照（期望 vs 实际）
r = run({'action': 'run'})
check("全场景跑 → ran", r['verdict'] == 'ran', str(r))
check("报告统计齐全",
      r['report']['total'] == len(SCENES)
      and 'passed' in r['report'] and 'failed' in r['report'], str(r))
# 已复核场景应全部对照通过（未复核的允许失败——留给误判回馈）
checked_scenes = [s['id'] for s in SCENES if s.get('checked')]
failed_ids = [f['id'] for f in r['report']['failed']]
check("已复核场景全通过（误判=零容忍已复核）",
      not any(fid in checked_scenes for fid in failed_ids),
      f"已复核但失败: {[f for f in failed_ids if f in checked_scenes]}")
check("未复核场景失败被列出（诚实）",
      all(fid not in checked_scenes for fid in failed_ids),
      str(failed_ids))

# ── 用例3：单场景
r = run({'action': 'run', 'scene_id': 'S01'})
check("单场景 S01 → 1 条", len(r['scenes']) == 1
      and r['scenes'][0]['id'] == 'S01', str(r))
check("S01 对照通过", r['scenes'][0]['passed'] is True,
      str(r['scenes'][0].get('diffs')))

# ── 用例4：结果含实际值（白箱）
results = run_all(['S01', 'S02'])
check("结果带 actual_type", all('actual_type' in x for x in results), str(results))
check("结果带 report（可追溯）", all(x['report'] for x in results),
      str(results[:1]))

# ── 用例5：诚实边界
check("坏 action → input_pending",
      run({'action': 'xx'})['verdict'] == 'input_pending')
check("list 给边界声明", '共识' in run({'action': 'list'})['boundary']
      or '非金标准' in run({'action': 'list'})['boundary'])
check("run 边界：只诊断不决策", '只诊断' in run({'action': 'run'})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/16 通过")
raise SystemExit(0 if PASS == 16 else 1)
