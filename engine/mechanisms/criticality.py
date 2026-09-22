# -*- coding: utf-8 -*-
"""criticality.py — 临界诊断：事件规模序列是否处于无标度区间（第 2 层机制）

概念来源：外部共识（幂律分布 / 自相似统计 / Hill 估计），归借鉴区。
本构件做什么（一句话）：
    给一串「事件规模」（悖论密度、绞杀事件规模、级联长度……），判它**是否落在无标度区间**，
    落在的话给**指数**与**三态**（次临界 / 临界 / 超临界），并给**距阈值的相对距离**与
    **自举稳定性**（抽样噪声下的分位）——即"离临界多远、这个判断有多稳"。

怎么算的（白话）：
    ① 幂律的无标度签名是「互补累积分布」在对数坐标下成一条直线：
       P(S≥s) ∝ s^(-α)。所以取各取值点的 (log s, log CCDF) 做一元线性回归，斜率取负得 α_回归。
    ② 换一条**独立的路**再算一遍：Hill 最大似然 α = 1 + n / Σ ln(s_i / s_min)，
       两条路**互相验**；差得太多就报「两估计不一致」，不硬给结论。
    ③ 直线**直不直**用 R² 卡（默认 ≥ 0.90），不直就报「不呈无标度」，也不给三态。
    ④ 三态按 α 与阈值 α_c（默认 2.0）比：低于阈值−容差＝超临界、高于阈值+容差＝次临界、
       之间＝临界。**阈值是参数，不是体系结论**（换了定义域/口径就要重定，见诚实边界）。
    ⑤ 稳定性用**自举**（有放回重采样）算 α 的分布，报当前 α 在其中的分位——
       分位极端说明这个估计本身抖，别当成硬结论用。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'diagnose'|'compare'（默认 diagnose）
        sizes: list[float]——事件规模序列（正数）；compare 模式用 sizes 与 sizes_b
        alpha_critical: float?——临界阈值（默认 2.0）
        tol: float?——判"临界"两侧的容差（默认 0.25）
        x_min: float?——幂律下界（默认取样本最小值）
        n_boot: int?——自举次数（默认 200，取 0 可关）
        seed: int?——自举随机种子（默认 0，保证**同输入同输出**）
    输出:
        verdict: 'diagnosed'（给了三态）|'not_scale_free'（不呈无标度，不给三态）
                 |'estimator_disagree'（两条路算的不一致）
                 |'input_pending' |'size_limit' |'internal_error'
        n: int——样本数
        x_min: float——实际用的下界
        alpha_ccdf: float?——回归路（CCDF 斜率）指数
        alpha_mle: float?——Hill 路指数
        alpha_pdf: float?——**回归路**换算成"概率密度指数"（= alpha_ccdf + 1，防口径误读）。
                   **注意是哪条路**：Hill 路的密度口径是 `alpha_mle + 1`，两条路会差一个估计差
                   （抽样下常见 0.0x）——拿这个字段去和别人的 MLE 密度指数直接比，会误判成
                   "两份实现不一致"（本仓真的被这样比过一次，2026-09-22 外部对拍时）。
        r2: float?——CCDF 直线拟合优度
        scale_free: bool——是否通过无标度门槛
        regime: 'supercritical'|'critical'|'subcritical'|None
        distance_to_threshold: float?——(α−α_c)/α_c，带符号的相对距离（正=更陡=更次临界）
        criticality_percentile: float?——α 在自举分布中的分位（稳定性）
        boundary: str——诚实边界
    诚实边界：
        只做**形状与指数**的诊断；样本太少 / 直线不直 / 两条路不一致 → **直接报，不硬给三态**；
        阈值与容差是**参数**（默认值只是常用约定），换口径要重定；
        **不做模型族检验**（幂律 vs 对数正态的正式比较要外部库），只用拟合优度门槛挡；
        **只诊断不决策**：不替使用者定"该不该停/该不该继续"。
"""

import math
import random

BOUNDARY = ('临界诊断（第 2 层机制，概念来源：外部共识的幂律/自相似统计，归借鉴区）：'
            '只判"这串事件规模的形状是否无标度、指数多大、离阈值多远"，'
            '样本不足 / 拟合不直 / 两条估计路不一致时**如实报，不编数也不硬给三态**；'
            '阈值与容差是参数（默认值只是常用约定，不是体系结论）；'
            '不做模型族检验，也**只诊断不决策**——不替使用者定该不该停。')

PORTS = {
    'in': {'mode': 'str?', 'sizes': 'list', 'sizes_b': 'list?',
           'alpha_critical': 'float?', 'tol': 'float?', 'x_min': 'float?',
           'n_boot': 'int?', 'seed': 'int?'},
    'out': {'verdict': 'str', 'n': 'int', 'x_min': 'float?',
            'alpha_ccdf': 'float?', 'alpha_mle': 'float?', 'alpha_pdf': 'float?',
            'r2': 'float?', 'scale_free': 'bool', 'regime': 'str?',
            'distance_to_threshold': 'float?', 'criticality_percentile': 'float?',
            'boundary': 'str', 'detail': 'dict', 'compare': 'dict?'},
}

MIN_N = 8            # 少于此数不判（样本不足）
MIN_DISTINCT = 5     # 不同取值少于此数，回归没有意义
MAX_N = 5000         # 超过则 size_limit（不硬跑）
R2_GATE = 0.90       # 无标度门槛
MAX_BOOT = 1000      # 自举次数上限（超过就按上限来，并在 detail 里说明）


def _hill(sizes, x_min):
    """Hill 最大似然估计（独立于回归那条路）。

    **口径**：这里估的是**互补累积分布**的指数 α（CCDF ∝ s^(-α)）——
    Pareto 下 E[ln(S/x_min)] = 1/α，故 α̂ = n / Σ ln(s_i / x_min)。
    （写成 `1 + n/Σln` 是**密度指数**口径，两者差 1，别混；
    本构件对外一律用 CCDF 口径，并在输出里给 alpha_pdf 防误读——
    **那个 alpha_pdf 是回归路换算的（alpha_ccdf + 1）**，不是这条 Hill 路；
    Hill 路的密度口径应为 `alpha_mle + 1`。两条路各有一个换算，别混用，
    也别拿其中一个去和别人的 MLE 密度指数直接比（会差一个估计差）。）
    """
    tail = [s for s in sizes if s >= x_min]
    n = len(tail)
    if n < 2:
        return None, 0
    denom = sum(math.log(s / x_min) for s in tail)
    if denom <= 0:
        return None, n
    return n / denom, n


def _ccdf_regression(sizes, x_min):
    """在 log-log 上对互补累积分布做一元回归，返回 (α_回归, R², 点数)。

    CCDF(s) = P(S≥s)。幂律下 CCDF ∝ s^(-α) ⇒ 斜率 = -α。
    只取 0 < CCDF < 1 的点（端点不参与），至少 MIN_DISTINCT 个。
    """
    n = len(sizes)
    uniq = sorted(set(s for s in sizes if s >= x_min))
    xs, ys = [], []
    for v in uniq:
        c = sum(1 for s in sizes if s >= v) / n
        if 0.0 < c < 1.0 and v > 0:
            xs.append(math.log10(v))
            ys.append(math.log10(c))
    if len(xs) < MIN_DISTINCT:
        return None, None, len(xs)
    k = len(xs)
    mx = sum(xs) / k
    my = sum(ys) / k
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0:
        return None, None, k
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
    return -slope, r2, k


def _bootstrap_percentile(sizes, x_min, alpha_point, n_boot, seed):
    """自举：有放回重采样，看 α 的抽样分布里当前值落在什么分位。"""
    if n_boot <= 0:
        return None, 0
    pool = [s for s in sizes if s >= x_min]
    if len(pool) < MIN_N:
        return None, 0
    rng = random.Random(seed)
    alphas = []
    for _ in range(n_boot):
        sample = [pool[rng.randrange(len(pool))] for _ in range(len(pool))]
        a, _m = _hill(sample, x_min)
        if a is not None:
            alphas.append(a)
    if not alphas:
        return None, 0
    lo = sum(1 for a in alphas if a < alpha_point)
    return lo / len(alphas), len(alphas)


def _fail(verdict, boundary, **kw):
    out = {'verdict': verdict, 'n': kw.get('n', 0), 'x_min': kw.get('x_min'),
           'alpha_ccdf': None, 'alpha_mle': None, 'alpha_pdf': None, 'r2': None,
           'scale_free': False, 'regime': None, 'distance_to_threshold': None,
           'criticality_percentile': None, 'boundary': boundary, 'detail': kw}
    return out


def _diagnose(sizes, alpha_critical, tol, x_min, n_boot, seed, boundary):
    """单序列诊断（compare 模式也复用它）。"""
    n = len(sizes)
    if n < MIN_N:
        return _fail('input_pending', boundary, n=n,
                     why='样本不足（至少 %d 个事件规模才判）' % MIN_N,
                     min_n=MIN_N)
    if n > MAX_N:
        return _fail('size_limit', boundary, n=n,
                     why='样本超过上限 %d，不硬跑' % MAX_N, max_n=MAX_N)
    if any((not isinstance(s, (int, float))) or s <= 0 or math.isnan(s)
           for s in sizes):
        return _fail('input_pending', boundary, n=n,
                     why='事件规模必须是正数')
    if x_min is None:
        x_min = min(sizes)
    if x_min <= 0 or x_min > max(sizes):
        return _fail('input_pending', boundary, n=n, x_min=x_min,
                     why='x_min 必须落在 (0, max(sizes)] 内')
    distinct = len(set(sizes))
    if distinct < MIN_DISTINCT:
        return _fail('not_scale_free', boundary, n=n, x_min=x_min,
                     why='不同取值只有 %d 个，回归无意义（需要 ≥ %d）'
                         % (distinct, MIN_DISTINCT), distinct=distinct)

    a_reg, r2, pts = _ccdf_regression(sizes, x_min)
    a_mle, n_tail = _hill(sizes, x_min)

    if a_reg is None or a_mle is None or r2 is None:
        return _fail('not_scale_free', boundary, n=n, x_min=x_min,
                     why='回归退化为空（取值全等或点太少）', distinct=distinct)

    # 门槛一：直线直不直
    if r2 < R2_GATE:
        return {'verdict': 'not_scale_free', 'n': n, 'x_min': x_min,
                'alpha_ccdf': round(a_reg, 4), 'alpha_mle': round(a_mle, 4),
                'alpha_pdf': round(a_reg + 1, 4), 'r2': round(r2, 4),
                'scale_free': False, 'regime': None,
                'distance_to_threshold': None, 'criticality_percentile': None,
                'boundary': boundary,
                'detail': {'why': 'log-log 直线不够直（R² < %.2f）：不呈无标度，'
                                  '不给三态' % R2_GATE,
                           'r2_gate': R2_GATE, 'points': pts,
                           'n_tail': n_tail, 'distinct': distinct}}

    # 门槛二：两条路要能对话
    gap_tol = max(0.25, 0.15 * abs(a_reg))
    if abs(a_reg - a_mle) > gap_tol:
        return {'verdict': 'estimator_disagree', 'n': n, 'x_min': x_min,
                'alpha_ccdf': round(a_reg, 4), 'alpha_mle': round(a_mle, 4),
                'alpha_pdf': round(a_reg + 1, 4), 'r2': round(r2, 4),
                'scale_free': True, 'regime': None,
                'distance_to_threshold': None, 'criticality_percentile': None,
                'boundary': boundary,
                'detail': {'why': '回归与 Hill 两条估计差 %.3f，超过容差 %.2f：'
                                  '不硬给三态' % (abs(a_reg - a_mle), gap_tol),
                           'gap_tol': gap_tol, 'points': pts, 'n_tail': n_tail}}

    # 三态（阈值是参数）
    if a_reg < alpha_critical - tol:
        regime = 'supercritical'
    elif a_reg > alpha_critical + tol:
        regime = 'subcritical'
    else:
        regime = 'critical'
    dist = (a_reg - alpha_critical) / alpha_critical

    nb = min(int(n_boot), MAX_BOOT) if n_boot and n_boot > 0 else 0
    pct, n_eff = _bootstrap_percentile(sizes, x_min, a_mle, nb, int(seed))
    detail = {'points': pts, 'n_tail': n_tail, 'distinct': distinct,
              'alpha_critical': alpha_critical, 'tol': tol,
              'bootstrap_runs': n_eff,
              'note': '阈值/容差是参数（默认只是常用约定）；不做模型族检验；'
                      '只诊断不决策'}
    if n_boot and n_boot > MAX_BOOT:
        detail['bootstrap_clamped'] = MAX_BOOT
    return {'verdict': 'diagnosed', 'n': n, 'x_min': x_min,
            'alpha_ccdf': round(a_reg, 4), 'alpha_mle': round(a_mle, 4),
            'alpha_pdf': round(a_reg + 1, 4), 'r2': round(r2, 4),
            'scale_free': True, 'regime': regime,
            'distance_to_threshold': round(dist, 4),
            'criticality_percentile': (round(pct, 4) if pct is not None else None),
            'boundary': boundary, 'detail': detail}


def run(inputs):
    """临界诊断入口。见模块 docstring 的接口说明。"""
    inputs = inputs or {}
    mode = inputs.get('mode', 'diagnose')
    sizes = inputs.get('sizes')
    alpha_c = inputs.get('alpha_critical', 2.0)
    tol = inputs.get('tol', 0.25)
    x_min = inputs.get('x_min')
    n_boot = inputs.get('n_boot', 200)
    seed = inputs.get('seed', 0)

    if mode not in ('diagnose', 'compare'):
        return _fail('input_pending', BOUNDARY, why='mode 只认 diagnose/compare')
    if not isinstance(sizes, (list, tuple)) or len(sizes) == 0:
        return _fail('input_pending', BOUNDARY,
                     why='需给 sizes（事件规模序列，正数列表）')
    try:
        alpha_c = float(alpha_c)
        tol = float(tol)
    except (TypeError, ValueError):
        return _fail('input_pending', BOUNDARY, why='alpha_critical/tol 必须是数')

    a = _diagnose(list(sizes), alpha_c, tol, x_min, n_boot, seed, BOUNDARY)
    if mode == 'compare':
        sizes_b = inputs.get('sizes_b')
        if not isinstance(sizes_b, (list, tuple)) or len(sizes_b) == 0:
            a['detail'] = dict(a.get('detail') or {},
                               compare_why='compare 模式还需 sizes_b')
            return a
        b = _diagnose(list(sizes_b), alpha_c, tol, x_min, n_boot, seed, BOUNDARY)
        # 只并置事实，不判"谁该停"
        cmp = {'a': {'verdict': a['verdict'], 'regime': a['regime'],
                     'alpha_ccdf': a['alpha_ccdf'],
                     'distance_to_threshold': a['distance_to_threshold'],
                     'criticality_percentile': a['criticality_percentile']},
               'b': {'verdict': b['verdict'], 'regime': b['regime'],
                     'alpha_ccdf': b['alpha_ccdf'],
                     'distance_to_threshold': b['distance_to_threshold'],
                     'criticality_percentile': b['criticality_percentile']},
               'note': '两条序列各自诊断，事实并置；谁更靠近阈值看 '
                       'distance_to_threshold 的绝对值，不做该不该停的建议'}
        da, db = a.get('distance_to_threshold'), b.get('distance_to_threshold')
        if da is not None and db is not None:
            cmp['comparable'] = True
            cmp['closer_to_threshold'] = 'a' if abs(da) <= abs(db) else 'b'
        else:
            # 有一条没给出三态（不呈无标度/估计不一致）→ 距离无从比，如实说
            cmp['comparable'] = False
            cmp['closer_to_threshold'] = None
            cmp['why'] = '至少一条序列未给出三态（%s / %s），距离不可比' \
                         % (a['verdict'], b['verdict'])
        a['compare'] = cmp
    return a


def _selftest():
    """自测：合成序列上必须复现指数、噪声序列必须被挡住。"""
    import random as _r

    def synth(alpha, n=4000, seed=1):
        rng = _r.Random(seed)
        # 逆变换：S = s_min · U^(-1/α)，U~Uniform(0,1) ⇒ CCDF ∝ s^(-α)
        return [1.0 * (1.0 - rng.random()) ** (-1.0 / alpha) for _ in range(n)]

    ok = 0
    tot = 0

    for true_alpha in (1.5, 2.0, 3.0):
        r = run({'sizes': synth(true_alpha), 'n_boot': 0})
        tot += 1
        got = r['alpha_ccdf']
        if r['verdict'] == 'diagnosed' and got is not None and \
                abs(got - true_alpha) < 0.15:
            ok += 1
        else:
            print('  ❌ α=%.1f 未复现：%s %s' % (true_alpha, r['verdict'], got))

    # 指数分布：不该判成无标度
    rng = _r.Random(7)
    expo = [-math.log(1.0 - rng.random()) for _ in range(4000)]
    r2 = run({'sizes': expo, 'n_boot': 0})
    tot += 1
    if r2['verdict'] in ('not_scale_free', 'estimator_disagree'):
        ok += 1
    else:
        print('  ❌ 指数分布被误判为无标度：%s' % r2)

    # 样本不足 / 非正数 / 超限
    for bad, want in (({'sizes': [1, 2, 3]}, 'input_pending'),
                      ({'sizes': [1, -2, 3, 4, 5, 6, 7, 8, 9, 10]}, 'input_pending'),
                      ({'sizes': list(range(1, MAX_N + 12))}, 'size_limit'),
                      ({'mode': 'nope', 'sizes': [1] * 20}, 'input_pending')):
        tot += 1
        got = run(bad)['verdict']
        if got == want:
            ok += 1
        else:
            print('  ❌ 坏输入应报 %s，实得 %s' % (want, got))

    # 同输入同输出（自举要可复现）
    s = synth(2.0, 500, seed=3)
    tot += 1
    if run({'sizes': s}) == run({'sizes': s}):
        ok += 1
    else:
        print('  ❌ 同输入两次结果不一致（自举未固定种子）')

    print('criticality 自测：%d/%d 通过' % (ok, tot))
    return ok == tot


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(0 if _selftest() else 1)
