# -*- coding: utf-8 -*-
"""test_criticality.py — 临界诊断的正式测试（含独立 oracle 与三条拒绝路径）

独立验证的设计（照 logic-verification 的规矩：至少两条彼此独立的路 + 变异验收）：
  · **oracle A**：测试里**另写一份 Hill 估计**（不 import 构件内部），在精确 Pareto 样本上
    与构件的 alpha_mle 对拍——两条独立实现互相验。
  · **oracle B**：用**逆变换**造已知 α 的精确 Pareto 样本（S = U^(-1/α)），
    看构件能不能把 α 复现出来（可证伪的"已知答案"）。
  · **第三条路**：指数分布 / 对数正态 / 双幂律混合——都**不该**被放过（拒绝也是结果）。
  · 边界与坏输入：样本不足、非正数、超上限、mode 不认、x_min 越界、取值太单一。
  · 确定性：同输入两次必须逐字段相同（自举要固定种子）。
  · **外部验证方**（不落在本文件里）：外部协作者另写的 oracle 夹具，在同一份合成样本上对拍，
    换算口径后逐位相等；跑法在仓库外（私有路径不进公开仓），本文件**只点名验证方**。
"""

import math
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import criticality as C                                  # noqa: E402

PASS = 0
try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

TOTAL = 0


def check(label, cond, detail=''):
    global PASS, TOTAL
    TOTAL += 1
    if cond:
        PASS += 1
        print(f'  ✅ {label}')
    else:
        print(f'  ❌ {label}  {detail}')


def pareto(alpha, n, seed=0):
    """逆变换采样：S = U^(-1/α) ⇒ CCDF(S≥s) = s^(-α)（精确幂律）。"""
    rng = random.Random(seed)
    return [(1.0 - rng.random()) ** (-1.0 / alpha) for _ in range(n)]


def hill_independent(sizes):
    """测试侧独立实现（不 import 构件内部）：α̂ = n / Σ ln(x_i / x_min)。"""
    xmin = min(sizes)
    tail = [x for x in sizes if x >= xmin]
    return len(tail) / sum(math.log(x / xmin) for x in tail)


print('一、oracle A：两条独立实现互对（Pareto 精确样本）')
for a_true in (1.8, 2.5):
    s = pareto(a_true, 2500, seed=11)
    r = C.run({'sizes': s, 'n_boot': 0})
    mine = hill_independent(s)
    check(f'α={a_true} 构件 Hill 与测试侧独立实现一致（差 <0.01）',
          r['alpha_mle'] is not None and abs(r['alpha_mle'] - mine) < 0.01,
          f"{r['alpha_mle']} vs {mine}")

print('二、oracle B：已知答案的复现（把 α 算回来）')
for a_true in (1.5, 2.0, 2.5, 3.0):
    r = C.run({'sizes': pareto(a_true, 3000, seed=a_true), 'n_boot': 0})
    check(f'α={a_true} 复现（|Δ|<0.15）且 verdict=diagnosed',
          r['verdict'] == 'diagnosed' and abs(r['alpha_ccdf'] - a_true) < 0.15,
          f"{r['verdict']} α̂={r['alpha_ccdf']}")

print('三、三态与阈值距离的自洽')
r_sup = C.run({'sizes': pareto(1.6, 3000, seed=2), 'n_boot': 0})
r_cri = C.run({'sizes': pareto(2.05, 3000, seed=3), 'n_boot': 0})
r_sub = C.run({'sizes': pareto(2.8, 3000, seed=4), 'n_boot': 0})
check('α≈1.6 → 超临界且距离为负', r_sup['regime'] == 'supercritical'
      and r_sup['distance_to_threshold'] < 0, r_sup.get('regime'))
check('α≈2.05 → 临界且 |距离|≤容差', r_cri['regime'] == 'critical'
      and abs(r_cri['distance_to_threshold']) <= 0.25, r_cri.get('regime'))
check('α≈2.8 → 次临界且距离为正', r_sub['regime'] == 'subcritical'
      and r_sub['distance_to_threshold'] > 0, r_sub.get('regime'))
for name, r in (('超临界', r_sup), ('临界', r_cri), ('次临界', r_sub)):
    # 与构件同一口径：容差是对 α 的**绝对**容差，换算成相对距离要除 αc
    rel = 0.25 / 2.0
    d = r['distance_to_threshold']
    if d < -rel:
        got = -1
    elif d > rel:
        got = 1
    else:
        got = 0
    want_sign = {'supercritical': -1, 'critical': 0, 'subcritical': 1}[r['regime']]
    check(f'{name}：距离符号与三态一致（|距离|≥{rel} 才算不临界）', got == want_sign,
          f"{d}")

print('四、口径防误读：alpha_pdf = alpha_ccdf + 1')
r = C.run({'sizes': pareto(2.2, 2000, seed=9), 'n_boot': 0})
check('alpha_pdf 恰为 α_ccdf+1（差 <1e-3）',
      abs(r['alpha_pdf'] - (r['alpha_ccdf'] + 1)) < 1e-3,
      f"{r['alpha_pdf']} vs {r['alpha_ccdf']}")

print('五、拒绝路径（不该放过的东西）')
rng = random.Random(5)
expo = [-math.log(1.0 - rng.random()) for _ in range(3000)]
check('指数分布 → 不判无标度', C.run({'sizes': expo, 'n_boot': 0})['verdict']
      in ('not_scale_free', 'estimator_disagree'),
      C.run({'sizes': expo, 'n_boot': 0})['verdict'])
rng2 = random.Random(6)
logn = [math.exp(rng2.gauss(0, 2.0)) for _ in range(3000)]
check('对数正态(σ=2) → 不判无标度', C.run({'sizes': logn, 'n_boot': 0})['verdict']
      in ('not_scale_free', 'estimator_disagree'),
      C.run({'sizes': logn, 'n_boot': 0})['verdict'])
mix = pareto(1.4, 1500, seed=7) + [x * 60 for x in pareto(3.5, 1500, seed=8)]
rmix = C.run({'sizes': mix, 'n_boot': 0})
check('双幂律混合 → 拒绝（not_scale_free 或 estimator_disagree）',
      rmix['verdict'] in ('not_scale_free', 'estimator_disagree'), rmix['verdict'])
check('被拒时不给三态（regime is None）', rmix['regime'] is None, rmix.get('regime'))
flat = [3.0] * 30
check('全等取值 → not_scale_free', C.run({'sizes': flat})['verdict'] == 'not_scale_free')

# 逼到「两估计互验」那一步：最小值处堆权重 → Hill 被抬高、回归几乎不动、R² 仍很高。
# （没有这条，互验门槛被拆掉也测不出来——变异验收第一轮就是这么漏的。）
base = []
_rng_tie = random.Random(2)          # 注意：RNG 必须建一次，写在推导式里会每轮重置
for _ in range(2000):
    base.append(10.0 * (1.0 - _rng_tie.random()) ** (-1.0 / 2.5))
ties = base + [10.0] * int(len(base) * 0.2)
rt = C.run({'sizes': ties, 'n_boot': 0})
check('最小值堆权重 → estimator_disagree（互验门槛真被走到）',
      rt['verdict'] == 'estimator_disagree',
      f"{rt['verdict']} α_reg={rt['alpha_ccdf']} α_mle={rt['alpha_mle']} R²={rt['r2']}")
check('互验不一致时 R² 仍然很高（证明它过了直不直那关、是卡在互验）',
      rt['r2'] is not None and rt['r2'] > C.R2_GATE, rt['r2'])
rt2 = C.run({'sizes': ties, 'n_boot': 0, 'alpha_critical': 2.0, 'tol': 0.25})
check('互验不一致时**不给**三态', rt2['regime'] is None)

print('六、坏输入与边界')
for label, inp, want in (
        ('样本不足（3 个）', {'sizes': [1, 2, 3]}, 'input_pending'),
        ('含非正数', {'sizes': [1, -2] + list(range(3, 12))}, 'input_pending'),
        # 显式给正 x_min：把「非正数」这道守卫单独隔离出来测
        # （不给 x_min 时会被后面 x_min<=0 那道守卫兜住，测不出这一道）
        ('含非正数（显式正 x_min）',
         {'sizes': [1.0, -2.0, 3, 4, 5, 6, 7, 8, 9, 10], 'x_min': 1.0},
         'input_pending'),
        ('mode 不认', {'mode': 'xx', 'sizes': [1] * 20}, 'input_pending'),
        ('sizes 缺失', {'n_boot': 0}, 'input_pending'),
        ('x_min 越界', {'sizes': pareto(2.0, 100, 1), 'x_min': 1e9}, 'input_pending'),
        ('超样本上限', {'sizes': list(range(1, C.MAX_N + 20))}, 'size_limit')):
    got = C.run(inp)['verdict']
    check(f'{label} → {want}', got == want, got)
check('x_min=<最小值> 等价于默认', C.run({'sizes': pareto(2.0, 800, 3), 'n_boot': 0})['alpha_ccdf']
      == C.run({'sizes': pareto(2.0, 800, 3), 'n_boot': 0, 'x_min': None})['alpha_ccdf'])

print('七、自举：可复现且取值合法')
s = pareto(2.0, 800, seed=21)
r1, r2 = C.run({'sizes': s}), C.run({'sizes': s})
check('同输入两次结果逐字段相同（种子固定）', r1 == r2)
check('分位落在 [0,1]', r1['criticality_percentile'] is not None
      and 0.0 <= r1['criticality_percentile'] <= 1.0,
      r1['criticality_percentile'])
check('n_boot=0 → 不给分位（不编）', C.run({'sizes': s, 'n_boot': 0})['criticality_percentile'] is None)
check('n_boot 超上限被夹到 %d' % C.MAX_BOOT,
      C.run({'sizes': s, 'n_boot': 99999})['detail'].get('bootstrap_clamped') == C.MAX_BOOT)

print('八、compare 模式：只并置事实')
rc = C.run({'mode': 'compare', 'sizes': pareto(1.7, 1500, 1),
            'sizes_b': pareto(3.0, 1500, 2), 'n_boot': 0})
check('compare 给出 a/b 两侧与可比标记', rc['compare']['comparable'] is True
      and rc['compare']['closer_to_threshold'] in ('a', 'b'), rc['compare'])
check('compare 里 a=超临界、b=次临界（事实并置）',
      rc['compare']['a']['regime'] == 'supercritical'
      and rc['compare']['b']['regime'] == 'subcritical')
rc2 = C.run({'mode': 'compare', 'sizes': pareto(2.0, 1000, 3), 'sizes_b': 5})
check('compare 缺/坏 sizes_b → 不崩，逐条报', isinstance(rc2.get('detail'), dict))

print('九、PORTS 与边界'
      )
check('每个返回点都带 boundary', all(
    isinstance(C.run(x).get('boundary'), str)
    for x in ({'sizes': pareto(2.0, 100, 1)}, {'sizes': [1, 2]}, {'sizes': [1] * 30},
              {'mode': 'x', 'sizes': [1] * 20}, {'sizes': list(range(1, C.MAX_N + 20))})))
out = C.run({'sizes': pareto(2.0, 500, 2), 'n_boot': 0})
# 口径：PORTS 里 `?` 标在**类型串**上表示"可能为 None"，不是标在键名上
required = [k for k, t in C.PORTS['out'].items() if not str(t).endswith('?')]
check('输出键覆盖 PORTS.out 的必返项',
      all(k in out for k in required),
      f'缺 {sorted(set(required) - set(out))}')
missing_optional = [k for k, t in C.PORTS['out'].items() if str(t).endswith('?') and k not in out]
check('可选键缺席是允许的（PORTS 已标可空）', bool(missing_optional) is True,
      f'本模式下缺席的可选键：{missing_optional}')
rc_in = C.run({'mode': 'compare', 'sizes': pareto(2.0, 600, 4),
               'sizes_b': pareto(2.5, 600, 5), 'n_boot': 0})
check('compare 模式下 compare 键必须在', 'compare' in rc_in and isinstance(rc_in['compare'], dict))

print(f'结果: {PASS}/40 通过')
raise SystemExit(0 if PASS == 40 else 1)
