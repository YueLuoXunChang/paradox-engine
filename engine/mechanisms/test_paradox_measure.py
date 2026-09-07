# -*- coding: utf-8 -*-
"""
test_paradox_measure.py — 正式测试：悖论测度 μ（核心机制）
用例依据：公式卡 paradox_measure.md（P1 完全悖论/P2 无悖论/P8 熵边界等）
+ 2026-09-06 补：非法 mode 诚实拦截（作者 8/31 审 μ₂ 丢 else 分支教训——
  分支不能静默落默认，改了不知道）。
运行：python engine/mechanisms/test_paradox_measure.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paradox_measure import run, choose_branch, _mu1, _mu2, _mu3, _mu4  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def near(a, b, tol=1e-9):
    return abs(a - b) < tol


print("悖论测度 μ · 正式测试")
print("=" * 60)

# ── 用例1：mu1 证据权重（P1 完全悖论 / 无悖论）
r = run({'mode': 'mu1', 'wA': 5, 'wNotA': 5})
check("mu1 五五开 → μ=1（完全悖论）", near(r['mu'], 1.0), str(r))
r = run({'mode': 'mu1', 'wA': 10, 'wNotA': 0})
check("mu1 一边倒 → μ=0（无悖论）", near(r['mu'], 0.0), str(r))
r = run({'mode': 'mu1', 'wA': 0, 'wNotA': 0})
check("mu1 双无证据 → μ=1（不可判定视作悖论）", near(r['mu'], 1.0), str(r))
r = run({'mode': 'mu1', 'wA': 7, 'wNotA': 3})
check("mu1 中间值 7:3 → μ=0.6", near(r['mu'], 0.6), str(r))
check("mu1 输出 branch=mu1", r['branch'] == 'mu1', str(r))

# ── 用例2：mu2 自指（作者点名的分支——直判 1）
r = run({'mode': 'mu2'})
check("mu2 自指 → μ=1", near(r['mu'], 1.0), str(r))
check("mu2 无需输入也直判 1", run({'mode': 'mu2'})['mu'] == 1.0, str(r))

# ── 用例3：mu3 层级
r = run({'mode': 'mu3', 'tau_L1': 1, 'tau_L2': 0})
check("mu3 层差 1-0 → μ=1", near(r['mu'], 1.0), str(r))
r = run({'mode': 'mu3', 'tau_L1': 0.3, 'tau_L2': 0.1})
check("mu3 层差 0.3-0.1 → μ=0.2", near(r['mu'], 0.2), str(r))

# ── 用例4：mu4 熵（P8 边界）
r = run({'mode': 'mu4', 'wA': 5, 'wNotA': 5})
check("mu4 五五开 → μ=1（最大熵）", near(r['mu'], 1.0), str(r))
r = run({'mode': 'mu4', 'wA': 10, 'wNotA': 0})
check("mu4 一边倒 → μ=0（零熵）", near(r['mu'], 0.0), str(r))
r = run({'mode': 'mu4', 'wA': 5, 'wNotA': 0})
check("mu4 p→1 边界 → μ=0（EPS 偏移不误伤）", near(r['mu'], 0.0), str(r))
r = run({'mode': 'mu4', 'wA': 0, 'wNotA': 5})
check("mu4 p→0 边界 → μ=0", near(r['mu'], 0.0), str(r))
r = run({'mode': 'mu4', 'wA': 5, 'wNotA': 0.001})
check("mu4 近一边倒 → μ≈0（小）", r['mu'] < 0.01, str(r))

# ── 用例5：自动路由（choose_branch 优先级）
check("自指 → mu2", choose_branch(is_self_ref=True) == 'mu2')
check("层级 → mu3", choose_branch(has_layers=True) == 'mu3')
check("熵 → mu4", choose_branch(need_entropy=True) == 'mu4')
check("默认 → mu1", choose_branch() == 'mu1')
check("自指优先于层级", choose_branch(True, True, True) == 'mu2')
r = run({'proposition': 'A∧¬A', 'is_self_ref': True})
check("run 无 mode 自动路由 → mu2", r['branch'] == 'mu2' and r['mu'] == 1.0,
      str(r))
check("proposition 透传", r['proposition'] == 'A∧¬A', str(r))

# ── 用例6：非法 mode 诚实拦截（2026-09-06 补——不静默落 mu1）
r = run({'mode': 'mu22'})
check("拼错 mode → 不静默走 mu1", r.get('error') is not None, str(r))
check("非法 mode μ=None", r['mu'] is None, str(r))
check("非法 mode 带诚实提示", '诚实拦截' in r.get('error', ''), str(r))

# ── 用例7：mu3 缺 tau 诚实拦截
r = run({'mode': 'mu3'})
check("mu3 缺 tau → 不硬算", r.get('error') is not None, str(r))
check("mu3 缺 tau μ=None", r['mu'] is None, str(r))

# ── 用例8：μ 范围性质（所有分支 ∈ [0,1]）
for mode, kw in [('mu1', {'wA': 3, 'wNotA': 7}),
                 ('mu2', {}), ('mu3', {'tau_L1': 0.8, 'tau_L2': 0.2}),
                 ('mu4', {'wA': 5, 'wNotA': 3})]:
    r = run({'mode': mode, **kw})
    check(f"{mode} μ∈[0,1]", r['mu'] is not None and 0 <= r['mu'] <= 1,
          str(r))

print("=" * 60)
print(f"结果: {PASS}/30 通过")
raise SystemExit(0 if PASS == 30 else 1)
