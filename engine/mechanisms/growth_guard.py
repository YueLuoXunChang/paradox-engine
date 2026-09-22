# -*- coding: utf-8 -*-
"""growth_guard.py — 增长护栏：迭代产物的限幅 / 增益调度 / 滞后补偿（第 2 层机制）

概念来源：控制论共识（限幅器 · 增益调度 · 双阈值迟滞），归借鉴区。
本仓的落地动机：递归修正管线需要一个**可算**的口径来回答"会不会指数级数据爆炸、
护栏压不压得住、压住的代价多大"——本仓此前只有"跑之前先拒"的硬上限（`size_limit` 那个
verdict 词）和收敛诊断（`converge_check` 判的是序列收不收敛，不管每轮产物有多大）。

本构件做什么（一句话）：
    给一串「每轮产物规模」的**实测值**与一个预算上限，算三件事：
    ① 增长是几何爆炸还是平稳（增长率、几轮越界）；
    ② 三件套各自的压制效果与**代价**（累计截断量 / 每轮最大跳变 / 开关抖动次数）；
    ③ 若不想截断，K 轮内需要多大预算。

怎么算的（白话）：
    ① 增长率取相邻两轮比值的**几何平均**（比算术平均稳），再按容差分三态：
       增长 / 平稳 / 收缩。
    ② **限幅**：n ← min(⌊r·n⌋, B)。必然保界——但每轮把超出预算的部分**整块砍掉**，
       代价用「累计截断量」与「每轮最大跳变」量出来（砍掉的可能是推导结果；
       本件只报代价，**不判该不该砍**）。
    ③ **增益调度**：**只在真要撞预算时才收窄**。取增益
       g = max(g_min, 1 − n/B)，n ← min(B, ⌊n + g·(r−1)·n⌋)：
       这一步不威胁预算就原样长（g 不参与），威胁到了才按 g 收窄——贴近预算时 g 降到地板，
       于是不是"一步顶到上限"，而是**逐步逼近**。代价是靠地板爬、到得更慢。
    ④ **滞后补偿**：单阈值会在阈值附近**来回开关**（抖动）。双阈值（高的进、低的出）
       把开关次数压下来。本件对**实测序列**分别数两种阈值的开关次数并给降幅——
       这是量出来的，不是假设出来的。
    ⑤ 每种策略的每轮轨迹都留痕（`trace`），便于逐轮复核。

统一接口：
    run(inputs: dict) -> dict
    输入:
        sizes: list[int]?——实测每轮产物规模（建议 ≥3 个点；非负整数）
        n0: int? / rate: float?——没有实测序列时，直接给起点与每轮倍数
        budget: int——预算上限 B（>0，必需）
        steps: int?——向前推演轮数（默认 20，上限 200）
        mode: str?——'compare'（默认，含三件套推演）|'watch'（只做实测层诊断）
        gain_min: float?——增益地板（默认 0.1）
        high_ratio: float?——滞后上阈（占预算比，默认 0.9）
        low_ratio: float?——滞后下阈（占预算比，默认 0.6，须小于上阈）
    输出:
        verdict: 'bounded_no_guard'（实测增长率≤1，不护栏也有界）
                 |'guard_engaged'（在增长，给了三件套的压制效果与代价）
                 |'observed_exceeded'（实测里已经越过预算）
                 |'insufficient_data'（点太少，判不了增长率）
                 |'input_pending'（缺预算或既没序列也没起点+倍数）
                 |'parse_error'（类型/取值不合法）/ 'size_limit'（超上限不硬跑）
                 |'internal_error'
        n_points: int——实际用的实测点数（0 表示走的是 n0+rate）
        growth: dict?——{ratio, kind, n_pairs, observed_max, observed_max_at}
        budget: int?——实际用的预算
        policies: dict?——各策略的 {trace, max_size, final_size, exceeded_at,
                        switches, max_jump, cut_total}
                        **口径**：`cut_total` = 累计截断量 = Σ(这一轮**想长的** − **实际放行的**)，
                        逐轮跟"当前实际状态"比（不是跟"不上护栏的原始轨迹"比）——
                        后者会越比越大且没有意义：状态一旦被顶在预算上，就不在原始轨迹上了。
                        `max_jump` 把"起点到自己第一轮"这一跳也算进去（各策略起点必须同源）。
        chatter: dict?——实测序列上单/双阈值的开关次数与降幅
        recommendation: dict?——{no_cut_budget, cut_needed, rounds_to_budget_*}
        detail: dict——口径与中间量（含"消掉了多少点/走了哪条路"这类诚实说明）
        boundary: str——诚实边界
    诚实边界：
        **这是对给定增长模型的推演，不是对真实递归的证明**——增长率来自实测（或调用方给的），
        真增长只有真跑才知道；限幅与增益都是**有损**的，本件只算"压不压得住、代价多大"，
        **不判"丢掉的那部分要紧不要紧"**；阈值 / 增益地板 / 轮数上限都是**参数**（默认值只是
        常用约定，换口径要重定）；与 `converge_check`（判收敛）、`criticality`（判规模分布形状）
        是**三件不同的事**，别互相顶替；**只诊断不决策**。
"""

import math

BOUNDARY = ('增长护栏（第 2 层机制，概念来源：控制论共识的限幅/增益调度/双阈值迟滞，归借鉴区）：'
            '对**给定的增长模型**推演三件套的压制效果与代价（截断量 / 每轮最大跳变 / 开关抖动），'
            '并报"不截断需要多大预算"。**不是对真实递归的证明**（增长率得实测）；'
            '限幅与增益都是有损的，**只报代价不替使用者判该不该砍**；阈值与增益地板是参数；'
            '与收敛诊断、临界诊断是三件不同的事；**只诊断不决策**。')

PORTS = {
    'in': {'sizes': 'list?', 'n0': 'int?', 'rate': 'float?', 'budget': 'int?',
           'steps': 'int?', 'mode': 'str?', 'gain_min': 'float?',
           'high_ratio': 'float?', 'low_ratio': 'float?'},
    'out': {'verdict': 'str', 'n_points': 'int', 'growth': 'dict?', 'budget': 'int?',
            'policies': 'dict?', 'chatter': 'dict?', 'recommendation': 'dict?',
            'detail': 'dict', 'boundary': 'str'},
}

MIN_POINTS = 3        # 实测点少于这个数，判不了增长率
MAX_POINTS = 5000     # 超过就 size_limit（不硬跑）
MAX_STEPS = 200       # 推演轮数上限
DEFAULT_STEPS = 20
GROWTH_TOL = 0.02     # 与 1.0 比出来的容差：|r−1| ≤ 容差算"平稳"
DEFAULT_GAIN_MIN = 0.1
DEFAULT_HIGH = 0.9
DEFAULT_LOW = 0.6


def _bad(msg, **kw):
    """统一的诚实拦截：input_pending / parse_error / size_limit / internal_error。"""
    d = {'n_points': kw.pop('n_points', 0), 'growth': None, 'budget': kw.pop('budget', None),
         'policies': None, 'chatter': None, 'recommendation': None,
         'detail': dict(kw), 'boundary': BOUNDARY, 'verdict': msg}
    return d


def _ratio_geomean(values):
    """相邻两轮比值的几何平均。返回 (ratio, 用到的比对数)。

    只用 s_k>0 的相邻对；出现比值 ≤0（规模掉到 0）时几何平均没有意义，
    退回**中位比值**，并把这件事写进 detail（不假装算得出来）。
    """
    rs = []
    for a, b in zip(values[:-1], values[1:]):
        if a > 0:
            rs.append(b / a)
    if not rs:
        return None, 0
    if any(r <= 0 for r in rs):
        srt = sorted(rs)
        return srt[len(srt) // 2], len(rs)
    return math.exp(sum(math.log(r) for r in rs) / len(rs)), len(rs)


def _kind(ratio):
    if ratio is None:
        return None
    if ratio > 1.0 + GROWTH_TOL:
        return 'geometric_growth'
    if ratio < 1.0 - GROWTH_TOL:
        return 'shrinking'
    return 'flat'


def _trace_stats(trace, budget, start=None):
    """一条轨迹的摘要：最大/最终、几轮越界、每轮最大跳变、累计截断。

    「每轮最大跳变」把**起点到自己第一轮**这一跳也算进去——否则各策略的轨迹
    起点不同，跳变数没法公平比（起点必须同源）。
    """
    if not trace:
        return {'trace': [], 'max_size': None, 'final_size': None,
                'exceeded_at': None, 'max_jump': None, 'cut_total': 0}
    seq = ([int(start)] + list(trace)) if start is not None else list(trace)
    jumps = [abs(seq[i] - seq[i - 1]) for i in range(1, len(seq))]
    return {'trace': trace, 'max_size': max(trace), 'final_size': trace[-1],
            'exceeded_at': next((i + 1 for i, v in enumerate(trace) if v > budget), None),
            'max_jump': max(jumps) if jumps else 0, 'cut_total': 0}


def _sim_raw(n0, rate, budget, steps):
    """参照系：不上任何护栏，按倍数 r 长。"""
    n = int(n0)
    trace = []
    for _ in range(steps):
        n = int(math.floor(n * rate))
        trace.append(n)
    return dict(_trace_stats(trace, budget, n0), policy='raw')


def _sim_clamp(n0, rate, budget, steps):
    """限幅：每轮硬顶到预算。必然保界，代价是整块截断。"""
    n = int(n0)
    trace, cut = [], 0
    for _ in range(steps):
        want = int(math.floor(n * rate))
        n = min(want, budget)
        cut += max(0, want - n)
        trace.append(n)
    st = _trace_stats(trace, budget, n0)
    st['cut_total'] = cut
    st['policy'] = 'clamp'
    return st


def _sim_gain(n0, rate, budget, steps, gain_min):
    """增益调度：**只在真要撞预算时才收窄**。

    g = max(g_min, 1 − n/B)——离预算远时 g≈1（原样长），贴近预算时 g 渐降到地板。
    「不威胁预算就不动」这条很要紧：否则浮点余量会让它在无关轮次里也比参照系差 1，
    对拍会变成噪声。
    """
    n = int(n0)
    trace, cut = [], 0
    for _ in range(steps):
        want_raw = int(math.floor(n * rate))
        if want_raw <= budget:
            want = want_raw
        else:
            g = min(1.0, max(gain_min, 1.0 - n / budget)) if budget > 0 else gain_min
            want = int(math.floor(n + g * (rate - 1.0) * n))
        n = min(max(0, want), budget)
        cut += max(0, want - n)
        trace.append(n)
    st = _trace_stats(trace, budget, n0)
    st['cut_total'] = cut
    st['policy'] = 'gain'
    return st


def _hyst_states(values, high, low):
    """按双阈值给出每轮是否处于"介入"态，并数开关次数。

    进入：v ≥ high；退出：v ≤ low（low < high → 中间那段是**滞后带**，不改变状态）。
    """
    on = False
    states, switches = [], 0
    for v in values:
        if not on and v >= high:
            on = True
            switches += 1
        elif on and v <= low:
            on = False
            switches += 1
        states.append(on)
    return states, switches


def _single_states(values, thr):
    """单阈值对照：v ≥ thr 就算介入态（没有滞后带）。"""
    on = False
    states, switches = [], 0
    for v in values:
        new = v >= thr
        if new != on:
            switches += 1
        on = new
        states.append(on)
    return states, switches


def _sim_hysteresis(n0, rate, budget, steps, gain_min, high, low):
    """滞后补偿：介入时只按增益地板长（退出后恢复原倍率），双阈值决定进/退。"""
    n = int(n0)
    trace, cut, on, switches = [], 0, False, 0
    for _ in range(steps):
        if not on and n >= high:
            on = True
            switches += 1
        elif on and n <= low:
            on = False
            switches += 1
        eff_rate = 1.0 + gain_min * (rate - 1.0) if on else rate
        want = int(math.floor(n * eff_rate))
        n = min(max(0, want), budget)
        cut += max(0, want - n)
        trace.append(n)
    st = _trace_stats(trace, budget, n0)
    st['cut_total'] = cut
    st['switches'] = switches
    st['policy'] = 'hysteresis'
    return st


def run(inputs):
    """按上面的口径算增长率、三件套的压制效果与代价。"""
    if not isinstance(inputs, dict):
        return _bad('parse_error', reason='输入必须是 dict')

    sizes = inputs.get('sizes')
    n0 = inputs.get('n0')
    rate = inputs.get('rate')
    budget = inputs.get('budget')
    mode = inputs.get('mode', 'compare')
    steps = inputs.get('steps', DEFAULT_STEPS)
    gain_min = inputs.get('gain_min', DEFAULT_GAIN_MIN)
    high_ratio = inputs.get('high_ratio', DEFAULT_HIGH)
    low_ratio = inputs.get('low_ratio', DEFAULT_LOW)

    # ── 入参校验（先拦，不硬跑）────────────────────────────────────────
    if mode not in ('compare', 'watch'):
        return _bad('parse_error', reason='mode 只认 compare / watch', got=mode)
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        return _bad('parse_error', reason='budget 必须是正整数（预算上限）', got=budget)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        return _bad('parse_error', reason='steps 必须是正整数', got=steps)
    if steps > MAX_STEPS:
        return _bad('size_limit', reason='推演轮数超上限，不硬跑',
                    steps=steps, max_steps=MAX_STEPS)
    for name, val in (('gain_min', gain_min), ('high_ratio', high_ratio), ('low_ratio', low_ratio)):
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not (0.0 < float(val) <= 1.0):
            return _bad('parse_error', reason='%s 必须是 (0,1] 内的数' % name, got=val)
    if not (low_ratio < high_ratio):
        return _bad('parse_error', reason='滞后下阈必须小于上阈（否则没有滞后带）',
                    low_ratio=low_ratio, high_ratio=high_ratio)
    gain_min = float(gain_min)

    # ── 两条入口：实测序列 / 起点+倍数 ─────────────────────────────────
    detail = {}
    if sizes is not None:
        if not isinstance(sizes, (list, tuple)) or len(sizes) == 0:
            return _bad('parse_error', reason='sizes 必须是非空列表')
        if len(sizes) > MAX_POINTS:
            return _bad('size_limit', reason='实测点数超上限，不硬跑',
                        points=len(sizes), max_points=MAX_POINTS)
        vals = []
        for x in sizes:
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                return _bad('parse_error', reason='sizes 里有非数值', got=repr(x))
            if x < 0:
                return _bad('parse_error', reason='sizes 里有负数（规模不能为负）', got=x)
            vals.append(int(x))
        n_points = len(vals)
        ratio, n_pairs = _ratio_geomean(vals)
        observed_max = max(vals)
        observed_max_at = vals.index(observed_max) + 1
        if n_points < MIN_POINTS or n_pairs < 2 or ratio is None:
            return _bad('insufficient_data',
                        reason='实测点太少（少于 %d 个或凑不出两对比值）判不了增长率' % MIN_POINTS,
                        points=n_points, pairs=n_pairs, budget=budget, n_points=n_points)
        start = vals[-1]          # 从**当前这一轮**往前推
        detail['start_from'] = 'sizes[-1]'
        zeros = sum(1 for v in vals if v == 0)
        if zeros:
            detail['zero_points'] = zeros
    elif n0 is not None and rate is not None:
        if isinstance(n0, bool) or not isinstance(n0, int) or n0 < 0:
            return _bad('parse_error', reason='n0 必须是非负整数', got=n0)
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate < 0:
            return _bad('parse_error', reason='rate 必须是非负数', got=rate)
        n_points, n_pairs = 0, 0
        ratio = float(rate)
        vals = []
        observed_max = int(n0)
        observed_max_at = 0
        start = int(n0)
        detail['start_from'] = 'n0+rate（没有实测序列）'
    else:
        return _bad('input_pending',
                    reason='要么给 sizes（实测每轮规模），要么给 n0 与 rate', budget=budget)

    kind = _kind(ratio)
    growth = {'ratio': round(ratio, 6), 'kind': kind, 'n_pairs': n_pairs,
              'observed_max': observed_max, 'observed_max_at': observed_max_at}

    # ── 实测层：越界与开关抖动（用真实数据数，不假设）──────────────────
    chatter = None
    if vals:
        thr = high_ratio * budget
        _, sw_single = _single_states(vals, thr)
        _, sw_dual = _hyst_states(vals, high_ratio * budget, low_ratio * budget)
        chatter = {'single_threshold_switches': sw_single,
                   'two_threshold_switches': sw_dual,
                   'reduction': sw_single - sw_dual,
                   'threshold': thr, 'band': [low_ratio * budget, high_ratio * budget]}

    observed_exceeded_at = next((i + 1 for i, v in enumerate(vals) if v > budget), None)

    # ── 判词：实测已经越界 > 不增长 > 增长 ─────────────────────────────
    if observed_exceeded_at is not None:
        return {'verdict': 'observed_exceeded', 'n_points': n_points, 'growth': growth,
                'budget': budget, 'policies': None, 'chatter': chatter,
                'recommendation': {'no_cut_budget': observed_max,
                                   'cut_needed': observed_max - budget},
                'detail': dict(detail, observed_exceeded_at=observed_exceeded_at,
                               note='实测序列里已经越过预算——先把数据本身处理掉，再谈护栏参数'),
                'boundary': BOUNDARY}
    if kind in ('flat', 'shrinking'):
        rec = {'no_cut_budget': int(math.floor(start * (ratio ** steps))) if ratio else start,
               'cut_needed': None}
        return {'verdict': 'bounded_no_guard', 'n_points': n_points, 'growth': growth,
                'budget': budget, 'policies': None, 'chatter': chatter,
                'recommendation': rec,
                'detail': dict(detail, note='实测增长率≤1，按此推演不护栏也有界；'
                                            '这是对**给定增长模型**的推演，不是对真实递归的证明'),
                'boundary': BOUNDARY}

    # ── 推演层：三件套 + 参照系 ────────────────────────────────────────
    raw = _sim_raw(start, ratio, budget, steps)
    clamp = _sim_clamp(start, ratio, budget, steps)
    gain = _sim_gain(start, ratio, budget, steps, gain_min)
    hyst = _sim_hysteresis(start, ratio, budget, steps, gain_min,
                           high_ratio * budget, low_ratio * budget)
    policies = {'raw': raw, 'clamp': clamp, 'gain': gain, 'hysteresis': hyst}
    if mode == 'watch':
        policies = {'raw': raw}

    rec = {'no_cut_budget': raw['max_size'], 'cut_needed': max(0, raw['max_size'] - budget),
           'rounds_to_budget_clamp': clamp['exceeded_at'],
           'rounds_to_budget_gain': gain['exceeded_at'],
           'rounds_to_budget_hysteresis': hyst['exceeded_at'],
           'gain_min': gain_min, 'steps': steps}

    detail.update({'note': '限幅与增益都是**有损**的：本件只报"压不压得住、代价多大"，'
                           '不判砍掉的那部分要不要紧',
                   'ratio_source': '实测序列的相邻轮几何平均' if vals else '调用方给的 rate'})

    return {'verdict': 'guard_engaged', 'n_points': n_points, 'growth': growth,
            'budget': budget, 'policies': policies, 'chatter': chatter,
            'recommendation': rec, 'detail': detail, 'boundary': BOUNDARY}


# ============================================================
# 自测（直接运行本文件）
# ============================================================

if __name__ == "__main__":
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print("=" * 60)
    print("增长护栏 · 自测")
    print("=" * 60)

    # 1) 几何增长：2 倍长，预算 1000，从 100 起 → 10 轮内必然越界
    r1 = run({'sizes': [100, 200, 400], 'budget': 1000, 'steps': 10})
    assert r1['verdict'] == 'guard_engaged', r1
    assert abs(r1['growth']['ratio'] - 2.0) < 1e-9, r1['growth']
    assert r1['growth']['kind'] == 'geometric_growth', r1['growth']
    print(f"✅ 几何增长识别: r={r1['growth']['ratio']} kind={r1['growth']['kind']}")

    # 2) 限幅必保界，且截断量 > 0；参照系（无护栏）必越界
    assert r1['policies']['clamp']['max_size'] <= 1000, r1['policies']['clamp']
    assert r1['policies']['clamp']['cut_total'] > 0, r1['policies']['clamp']
    assert r1['policies']['raw']['exceeded_at'] is not None, r1['policies']['raw']
    print(f"✅ 限幅保界: max={r1['policies']['clamp']['max_size']} "
          f"截断={r1['policies']['clamp']['cut_total']} "
          f"（无护栏第 {r1['policies']['raw']['exceeded_at']} 轮越界）")

    # 3) 增益调度：不威胁预算时与参照系一致，威胁到了逐步逼近（不一步顶到上限）
    assert r1['policies']['gain']['max_jump'] <= r1['policies']['clamp']['max_jump'], \
        (r1['policies']['gain'], r1['policies']['clamp'])
    g_tr = r1['policies']['gain']['trace']
    c_tr = r1['policies']['clamp']['trace']
    assert len(set(g_tr)) > len(set(c_tr)), (g_tr, c_tr)
    print(f"✅ 增益调度逐步逼近: gain {g_tr[:4]}… vs clamp {c_tr[:4]}…"
          f"（最大跳变 {r1['policies']['gain']['max_jump']} ≤ {r1['policies']['clamp']['max_jump']}）")

    # 4) 滞后带：实测序列在阈值附近来回 → 双阈值开关次数必须不多于单阈值
    wob = [880, 950, 700, 930, 650, 960, 720, 940]   # 预算 1000、上阈 900、下阈 600
    r2 = run({'sizes': wob, 'budget': 1000, 'mode': 'watch'})
    ch = r2['chatter']
    assert ch['two_threshold_switches'] <= ch['single_threshold_switches'], ch
    assert ch['reduction'] >= 1, ch
    print(f"✅ 滞后压抖动: 单阈值开关 {ch['single_threshold_switches']} 次 → "
          f"双阈值 {ch['two_threshold_switches']} 次（少 {ch['reduction']} 次）")

    # 5) 不增长的序列：不护栏也有界
    r3 = run({'sizes': [500, 500, 500, 500], 'budget': 1000})
    assert r3['verdict'] == 'bounded_no_guard', r3
    print(f"✅ 平稳序列: {r3['verdict']}（r={r3['growth']['ratio']}）")

    # 6) 实测已经越界：先报越界，不装作能靠护栏救
    r4 = run({'sizes': [100, 200, 1500], 'budget': 1000})
    assert r4['verdict'] == 'observed_exceeded', r4
    assert r4['detail']['observed_exceeded_at'] == 3, r4['detail']
    print(f"✅ 实测越界: {r4['verdict']}（第 {r4['detail']['observed_exceeded_at']} 点）")

    # 7) 用 n0+rate 入口（没有实测序列也能算）
    r5 = run({'n0': 10, 'rate': 3.0, 'budget': 100000, 'steps': 12})
    assert r5['verdict'] == 'guard_engaged' and r5['n_points'] == 0, r5
    assert r5['policies']['clamp']['max_size'] <= 100000, r5['policies']['clamp']
    print(f"✅ 起点+倍率入口: r={r5['growth']['ratio']} steps=12 "
          f"max={r5['policies']['clamp']['max_size']}")

    # 8) 四条拒绝路径
    assert run({'sizes': [1, 2], 'budget': 10})['verdict'] == 'insufficient_data'
    assert run({'sizes': [1, 2, 3]})['verdict'] == 'parse_error'          # 缺预算
    assert run({'budget': 10})['verdict'] == 'input_pending'             # 缺序列也缺起点
    assert run({'sizes': [1, 2, 3], 'budget': 10, 'steps': 9999})['verdict'] == 'size_limit'
    assert run({'sizes': [1, 2, 3], 'budget': 10,
                'low_ratio': 0.9, 'high_ratio': 0.6})['verdict'] == 'parse_error'  # 阈值反了
    assert run({'sizes': [1, -2, 3], 'budget': 10})['verdict'] == 'parse_error'
    print("✅ 拒绝路径: 点太少/缺预算/缺输入/轮数超限/阈值反了/负数 全部如实报")

    # 9) 每轮轨迹都留痕（可逐轮复核）
    tr = r1['policies']['clamp']['trace']
    assert len(tr) == 10 and tr[-1] <= 1000, tr
    print(f"✅ 轨迹留痕: clamp trace={tr[:5]}…（共 {len(tr)} 轮）")

    print("=" * 60)
    print("增长护栏自测：全部通过 ✅")
    print("=" * 60)
