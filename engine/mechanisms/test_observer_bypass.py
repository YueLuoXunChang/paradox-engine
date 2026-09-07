# -*- coding: utf-8 -*-
"""
test_observer_bypass.py — 正式测试：悖论全程自反旁路（第 2 层 2.5）
用例依据：内部规格 §五（主链不停/并行观察/检测点注解注入/架构级免疫）
运行：python engine/mechanisms/test_observer_bypass.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from observer_bypass import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("悖论全程自反旁路 · 正式测试")
print("=" * 60)

# ── 用例1：主链不阻塞 + 旁路发现
events = ['读取需求', '建模 A 方案', '发现需求冲突', '继续建模 B 方案',
          '产出模型']
r = run({'main_events': events})
check("→ observed", r['verdict'] == 'observed', str(r))
check("主线程完整跑完 5 步（不阻塞）", r['main_ran'] == 5, str(r))
check("发现矛盾（位置 2）", len(r['findings']) == 1
      and r['findings'][0]['at'] == 2, str(r))
check("发现类型 paradox", r['findings'][0]['type'] == 'paradox', str(r))
check("注解随行（8 字段语义）",
      r['findings'][0]['annotation']['LV'] == 'P-B'
      and r['findings'][0]['annotation']['ST'] == '活跃', str(r))
check("注入发生在检测点", r['injected_at'] == [2], str(r))
check("边界：不消除矛盾不替主线程决策",
      '不' in r['boundary'] and '决策' in r['boundary'], r['boundary'])
check("边界：标注启发式非完备", '启发' in r['boundary'], r['boundary'])

# ── 用例2：相邻步对立（启发）
r = run({'main_events': ['要快', '不要快']})
check("相邻步对立 → 1 处发现", len(r['findings']) == 1, str(r))
check("对立类型 conflict", r['findings'][0]['type'] == 'conflict', str(r))
check("对立发现注解含双方", r['findings'][0]['annotation']['A'] == '要快'
      and r['findings'][0]['annotation']['notA'] == '不要快', str(r))

# ── 用例3：干净主线程 → 零发现但照跑
r = run({'main_events': ['读取', '建模', '产出']})
check("干净序列 main_ran=3", r['main_ran'] == 3, str(r))
check("干净序列零发现", len(r['findings']) == 0, str(r))

# ── 用例4：自定义 detect
r = run({'main_events': ['a', 'b', 'c'],
         'detect': lambda ev: {'type': 'selfref', 'A': ev,
                               'note': '自定义'} if ev == 'b' else None})
check("自定义 detect 命中 b", len(r['findings']) == 1
      and r['findings'][0]['at'] == 1, str(r))
check("自定义类型 selfref", r['findings'][0]['type'] == 'selfref', str(r))

# ── 用例5：use_advice=False（发现但不注入）
r = run({'main_events': ['发现矛盾', '继续'],
         'use_advice': False})
check("不注入：injected_at 空", r['injected_at'] == [], str(r))
check("不注入：findings 无 injected 键",
      'injected' not in r['findings'][0], str(r))

# ── 用例6：detect 抛错 → 诚实记录不崩主链
r = run({'main_events': ['x', 'y'],
         'detect': lambda ev: (_ for _ in ()).throw(RuntimeError('boom'))})
check("detect 异常 → 记录 detect_error", r['findings']
      and r['findings'][0]['type'] == 'detect_error', str(r))
check("主链仍完整跑完", r['main_ran'] == 2, str(r))

# ── 用例7：诚实边界
check("缺主线程 → input_pending", run({})['verdict'] == 'input_pending')
check("空列表 → input_pending", run({'main_events': []})
      ['verdict'] == 'input_pending')
check("非列表 → input_pending",
      run({'main_events': 'notalist'})['verdict'] == 'input_pending')

print("=" * 60)
print(f"结果: {PASS}/22 通过")
raise SystemExit(0 if PASS == 22 else 1)
