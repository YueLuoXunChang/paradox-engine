# -*- coding: utf-8 -*-
"""
test_truth_revision.py — 正式测试：Gupta-Belnap 真值修正
用例依据：ROADMAP 阶段 7（共振带收敛的学界锚点）+ 外部借鉴标注
运行：python engine/cold/test_truth_revision.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from truth_revision import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("Gupta-Belnap 真值修正 · 正式测试")
print("=" * 60)

# ── 用例1：demo 说谎者（教科书核心结论）
r = run({'mode': 'demo'})
check("demo → demo", r['verdict'] == 'demo', str(r))
s = r['detail']['systems']['liar']
check("说谎者 → periodic", s['verdict'] == 'periodic', str(s))
check("说谎者周期 = 2", s['period'] == 2, str(s))
check("说谎者 note 标注学界共识",
      '学界' in s['note'] or '教科书' in s['note'], s['note'])

# ── 用例2：demo 良性（稳定）
s = r['detail']['systems']['benign']
check("良性 → stable", s['verdict'] == 'stable', str(s))
check("良性定点 Q 真", s['fixed_value'].get('Q') is True, str(s))

# ── 用例3：demo 互指环（多句系统——修正理论价值）
s = r['detail']['systems']['ring']
check("互指环 → periodic 或 stable",
      s['verdict'] in ('periodic', 'stable'), str(s))
check("互指环周期 ≥1", (s.get('period') or 1) >= 1, str(s))

# ── 用例4：custom 说谎者
r = run({'mode': 'custom',
         'sentences': {'A': lambda a: not a.get('A', False)},
         'start': {'A': False}, 'max_steps': 20})
check("custom 说谎者 periodic", r['verdict'] == 'periodic', str(r))
check("custom 周期 2", r['detail']['period'] == 2, str(r))
check("custom 带 note", bool(r['detail'].get('note')), str(r))

# ── 用例5：custom 稳定系统
r = run({'mode': 'custom', 'sentences': {'A': lambda a: True}})
check("A⟺真 → stable", r['verdict'] == 'stable', str(r))
check("定点给出", r['detail'].get('fixed_value') is not None, str(r))

# ── 用例6：多句 custom（2 句互指）
r = run({'mode': 'custom',
         'sentences': {'P': lambda a: not a.get('Q', False),
                       'Q': lambda a: a.get('P', False)}})
check("双句系统有判定", r['verdict'] in ('stable', 'periodic', 'unstable'),
      str(r))

# ── 用例7：边界
check("坏 mode → input_pending", run({'mode': 'xx'})['verdict']
      == 'input_pending')
check("custom 缺句 → input_pending",
      run({'mode': 'custom'})['verdict'] == 'input_pending')
check("非 callable → input_pending",
      run({'mode': 'custom',
           'sentences': {'A': 42}})['verdict'] == 'input_pending')
check("边界声明借鉴来源（Gupta-Belnap 外部共识）",
      'Gupta-Belnap' in run({'mode': 'demo'})['boundary'])
check("边界声明振荡≠判真值",
      '≠判定真值' in run({'mode': 'demo'})['boundary']
      or '无稳定真值' in run({'mode': 'demo'})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/19 通过")
raise SystemExit(0 if PASS == 19 else 1)
