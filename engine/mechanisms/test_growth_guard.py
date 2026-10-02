# -*- coding: utf-8 -*-
"""test_growth_guard.py — 增长护栏的正式测试（含独立复算与拒绝路径）

独立验证的设计（照 logic-verification 的规矩：至少两条彼此独立的路 + 变异验收）：
  · **oracle A（越界轮的整数闭式）**：用**纯整数**循环（不碰构件内部）算出"第几轮越界"，
    另外用 log 闭式 floor(log_r(B/n0))+1 在**整数幂**案例上再对一次——两条路都比构件的
    `policies['raw']['exceeded_at']`。
  · **oracle B（三件套独立复算）**：在测试里**另写一份**限幅 / 增益 / 滞后的推演
    （同样的口径、不同的写法：if 分支代替 min/max、显式上限检查、手写状态机），
    逐轮对拍完整 trace——不是只比最后一个数。
  · **oracle C（恒等与性质）**：预算极大时三策略必须**逐轮等于**参照系；任何策略都不得
    超过预算、也不得比参照系长得更快；增长时轨迹非减。
  · **oracle D（抖动计数的独立复算）**：用"数状态跳变"的另一条写法复算单/双阈值开关次数，
    并含一个手算案例（7 → 1）。
  · **拒绝路径**：点太少 / 缺预算 / 缺输入 / 轮数超限 / 阈值反了 / 负数 / 全零序列。
  · **确定性**：同输入两次逐字段相同（本件无随机数，必须严格一致）。
  · **外部验证方**（不落在本文件里）：外部协作者另写的参考实现，对照本件的模型边界
    （正是它查出本件缺"步长限幅"这一件）；跑法在仓库外（私有路径不进公开仓），
    本文件**只点名验证方**。
"""

import ast as _ast
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import growth_guard as G                                  # noqa: E402

try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

PASS = 0
TOTAL = 0


def check(label, cond, detail=''):
    global PASS, TOTAL
    TOTAL += 1
    if cond:
        PASS += 1
        print(f'  ✅ {label}')
    else:
        print(f'  ❌ {label}  {detail}')


# ============================================================
# oracle A：越界轮（纯整数循环 + log 闭式）
# ============================================================

def exceed_round_integer(start, rate_int, budget):
    """纯整数循环：第几轮第一次超过预算（与构件完全无关的一条路）。"""
    n, k = int(start), 0
    while n <= budget:
        n *= rate_int
        k += 1
        if k > 5000:
            return None
    return k


def exceed_round_log(start, rate, budget):
    """闭式：最小的 k 使 start·r^k > B，即 floor(log_r(B/start)) + 1。"""
    return int(math.floor(math.log(budget / start, rate))) + 1


print('一、越界轮：两条独立路 vs 构件')
cases = [(100, 2, 1000), (1, 2, 64), (3, 3, 100), (7, 5, 5000)]
ok_int = all(G.run({'n0': s, 'rate': float(r), 'budget': b, 'steps': 60}
                   )['policies']['raw']['exceeded_at'] == exceed_round_integer(s, r, b)
             for s, r, b in cases)
check('整数循环算出的越界轮 == 构件报的越界轮（4 组）', ok_int)
ok_log = all(exceed_round_log(s, r, b) == exceed_round_integer(s, r, b)
             for s, r, b in [(1, 2, 64), (1, 2, 1024), (2, 4, 128)])
check('log 闭式 == 整数循环（整数幂案例，两条独立路互验）', ok_log)

# 参照系轨迹必须就是"逐轮乘倍数"——独立复算
raw_ind = []
n = 100
for _ in range(12):
    n = int(n * 2)
    raw_ind.append(n)
raw_got = G.run({'n0': 100, 'rate': 2.0, 'budget': 10 ** 9, 'steps': 12})['policies']['raw']['trace']
check('参照系轨迹 == 独立复算的逐轮乘倍数', raw_got == raw_ind, f'{raw_got} vs {raw_ind}')

# ============================================================
# oracle B：三件套的独立复算（同样的口径、不同的写法）
# ============================================================

def sim_clamp_ind(start, rate, budget, steps):
    out, n = [], int(start)
    for _ in range(steps):
        nxt = int(math.floor(n * rate))
        if nxt > budget:
            nxt = budget
        n = nxt
        out.append(n)
    return out


def sim_gain_ind(start, rate, budget, steps, gain_min):
    """增益：不威胁预算就原样长，威胁到了按 g 收窄；用 if 而不是 min/max 写。"""
    out, n = [], int(start)
    for _ in range(steps):
        nxt = int(math.floor(n * rate))
        if nxt > budget:
            head = 1.0 - n / budget
            if head < gain_min:
                head = gain_min
            if head > 1.0:
                head = 1.0
            nxt = int(math.floor(n + head * (rate - 1.0) * n))
        if nxt > budget:
            nxt = budget
        if nxt < 0:
            nxt = 0
        n = nxt
        out.append(n)
    return out


def sim_hyst_ind(start, rate, budget, steps, gain_min, high, low):
    """滞后：手写状态机（介入位 + 两个阈值），介入时用增益地板长。"""
    out, n, on = [], int(start), False
    for _ in range(steps):
        if on is False and n >= high:
            on = True
        elif on is True and n <= low:
            on = False
        mult = rate if on is False else 1.0 + gain_min * (rate - 1.0)
        nxt = int(math.floor(n * mult))
        if nxt > budget:
            nxt = budget
        if nxt < 0:
            nxt = 0
        n = nxt
        out.append(n)
    return out


print('二、三件套：构件 vs 独立复算（逐轮轨迹）')
p = G.run({'n0': 400, 'rate': 2.0, 'budget': 1000, 'steps': 8})['policies']
check('限幅轨迹逐轮一致', p['clamp']['trace'] == sim_clamp_ind(400, 2.0, 1000, 8),
      p['clamp']['trace'])
check('增益轨迹逐轮一致', p['gain']['trace'] == sim_gain_ind(400, 2.0, 1000, 8, G.DEFAULT_GAIN_MIN),
      p['gain']['trace'])
check('滞后轨迹逐轮一致',
      p['hysteresis']['trace'] == sim_hyst_ind(400, 2.0, 1000, 8, G.DEFAULT_GAIN_MIN, 900, 600),
      p['hysteresis']['trace'])

rnd = random.Random(20260922)
rand_cases = [(rnd.randint(1, 500), rnd.uniform(1.05, 4.0), rnd.randint(50, 100000),
               rnd.randint(3, 40), rnd.uniform(0.05, 0.5)) for _ in range(120)]
mismatch = []
for start, rate, budget, steps, gmin in rand_cases:
    q = G.run({'n0': start, 'rate': rate, 'budget': budget, 'steps': steps,
               'gain_min': gmin})['policies']
    if q['clamp']['trace'] != sim_clamp_ind(start, rate, budget, steps):
        mismatch.append(('clamp', start, rate, budget))
    if q['gain']['trace'] != sim_gain_ind(start, rate, budget, steps, gmin):
        mismatch.append(('gain', start, rate, budget, gmin))
    hi, lo = G.DEFAULT_HIGH * budget, G.DEFAULT_LOW * budget
    if q['hysteresis']['trace'] != sim_hyst_ind(start, rate, budget, steps, gmin, hi, lo):
        mismatch.append(('hyst', start, rate, budget, gmin))
check('120 组随机输入：三策略全量轨迹逐轮一致', not mismatch, mismatch[:3])

# ============================================================
# oracle C：恒等与性质
# ============================================================

print('三、护栏的基本性质（随机 200 组）')
fuzz = [(rnd.randint(1, 2000), rnd.uniform(1.1, 5.0), rnd.randint(10, 10 ** 6),
         rnd.randint(2, 30)) for _ in range(200)]
over, faster, empty = [], [], []
for start, rate, budget, steps in fuzz:
    q = G.run({'n0': start, 'rate': rate, 'budget': budget, 'steps': steps})['policies']
    for name in ('clamp', 'gain', 'hysteresis'):
        tr = q[name]['trace']
        if len(tr) != steps or any(v > budget or v < 0 for v in tr):
            over.append((name, start, rate, budget))
    for k in range(steps):
        if q['clamp']['trace'][k] > q['raw']['trace'][k] or \
                q['gain']['trace'][k] > q['raw']['trace'][k] or \
                q['hysteresis']['trace'][k] > q['raw']['trace'][k]:
            faster.append((start, rate, budget, k))
check('任何策略都不越预算、不出现负数、轮数正确', not over, over[:3])
check('任何一轮都不比参照系长得更快（护栏只减速）', not faster, faster[:3])

big = G.run({'n0': 37, 'rate': 2.5, 'budget': 10 ** 15, 'steps': 15})['policies']
check('预算极大（形同不介入）：三策略逐轮等于参照系',
      big['clamp']['trace'] == big['raw']['trace']
      and big['gain']['trace'] == big['raw']['trace']
      and big['hysteresis']['trace'] == big['raw']['trace'])

mono = G.run({'n0': 5, 'rate': 1.7, 'budget': 10 ** 6, 'steps': 20})['policies']
check('增长时各策略轨迹非减',
      all(all(t[i] <= t[i + 1] for i in range(len(t) - 1))
          for t in (mono['raw']['trace'], mono['clamp']['trace'],
                    mono['gain']['trace'], mono['hysteresis']['trace'])))

def clamp_cut_independent(start, rate, budget, steps):
    """独立复算「累计截断量」：口径 = Σ(这一轮想长的 − 实际放行的)，逐轮跟当前实际状态比。

    （**别**写成 Σ max(0, 原始轨迹 − 预算)——那是另一个量，会越比越大且没有意义：
    状态一旦被顶在预算上，就不在原始轨迹上了。这条我先写错过一次，留在这里当尺子。）
    """
    n, cut = int(start), 0
    for _ in range(steps):
        want = int(math.floor(n * rate))
        admitted = want if want <= budget else budget
        cut += want - admitted
        n = admitted
    return cut


cut_one = G.run({'n0': 100, 'rate': 2.0, 'budget': 1000, 'steps': 10})['policies']
check('限幅的累计截断量 == 独立复算 Σ(想长的 − 实际放行的)',
      cut_one['clamp']['cut_total'] == clamp_cut_independent(100, 2.0, 1000, 10),
      f"{cut_one['clamp']['cut_total']} vs {clamp_cut_independent(100, 2.0, 1000, 10)}")

# ============================================================
# oracle D：抖动计数（独立复算 + 手算案例）
# ============================================================

print('四、滞后带：开关抖动')


def count_switches_by_transitions(values, high, low):
    """另一条写法：先算出每轮状态，再数状态变化次数（构件是边走边数）。"""
    states, on = [], False
    for v in values:
        if on is False and v >= high:
            on = True
        elif on is True and v <= low:
            on = False
        states.append(on)
    return sum(1 for i in range(1, len(states)) if states[i] != states[i - 1]) + (1 if states and states[0] else 0)


def count_single_by_transitions(values, thr):
    states = [v >= thr for v in values]
    return sum(1 for i in range(1, len(states)) if states[i] != states[i - 1]) + (1 if states and states[0] else 0)


wob = [880, 950, 700, 930, 650, 960, 720, 940]
rc = G.run({'sizes': wob, 'budget': 1000, 'mode': 'watch'})['chatter']
check('手算案例：单阈值开关 7 次 · 双阈值 1 次（滞后带压住抖动）',
      rc['single_threshold_switches'] == 7 and rc['two_threshold_switches'] == 1,
      rc)
check('开关次数与独立复算一致（<计数> 换了写法）',
      rc['single_threshold_switches'] == count_single_by_transitions(wob, 900)
      and rc['two_threshold_switches'] == count_switches_by_transitions(wob, 900, 600), rc)

# **必须有一个"真的会发生退出"的案例**：上面那串值始终没掉到下阈以下，退出分支一次没走，
# 于是"只数进入不数退出"这种错会被漏掉（变异验收当场指出了这个盲区）。
release_case = [950, 700, 500, 950]      # 进(950) → 带内不动(700) → 退(500) → 再进(950)
rc_r = G.run({'sizes': release_case, 'budget': 1000, 'mode': 'watch'})['chatter']
check('含"退出"的案例：双阈值开关 3 次（进1·退1·再进1，退出必须也计数）',
      rc_r['two_threshold_switches'] == 3
      and rc_r['two_threshold_switches'] == count_switches_by_transitions(release_case, 900, 600),
      rc_r)

rising = [100, 300, 500, 700, 950, 990, 995]
rc2 = G.run({'sizes': rising, 'budget': 1000, 'mode': 'watch'})['chatter']
check('严格递增序列：单阈值与双阈值开关次数相同（只有一次进入）',
      rc2['single_threshold_switches'] == rc2['two_threshold_switches'] == 1, rc2)

worst = []
for _ in range(30):
    vals = [rnd.randint(0, 1200) for _ in range(rnd.randint(4, 20))]
    c = G.run({'sizes': vals, 'budget': 1000, 'mode': 'watch'})['chatter']
    if c['two_threshold_switches'] > c['single_threshold_switches']:
        worst.append((vals, c))
check('30 组随机序列：双阈值开关次数从不超过单阈值', not worst, worst[:2])

# ============================================================
# 五、判词与拒绝路径
# ============================================================

print('五、判词与拒绝路径')
check('点太少 → insufficient_data',
      G.run({'sizes': [100, 200], 'budget': 1000})['verdict'] == 'insufficient_data')
check('缺预算 → parse_error',
      G.run({'sizes': [100, 200, 400]})['verdict'] == 'parse_error')
check('既没序列也没起点+倍数 → input_pending',
      G.run({'budget': 1000})['verdict'] == 'input_pending')
check('轮数超上限 → size_limit（不硬跑）',
      G.run({'sizes': [100, 200, 400], 'budget': 1000, 'steps': G.MAX_STEPS + 1})['verdict'] == 'size_limit')
check('阈值反了（下阈 ≥ 上阈）→ parse_error',
      G.run({'sizes': [100, 200, 400], 'budget': 1000,
             'low_ratio': 0.9, 'high_ratio': 0.6})['verdict'] == 'parse_error')
check('负数规模 → parse_error',
      G.run({'sizes': [100, -2, 400], 'budget': 1000})['verdict'] == 'parse_error')
check('非数值规模 → parse_error',
      G.run({'sizes': [100, 'x', 400], 'budget': 1000})['verdict'] == 'parse_error')
check('全零序列 → 不硬判增长率（insufficient_data，不崩）',
      G.run({'sizes': [0, 0, 0, 0], 'budget': 1000})['verdict'] == 'insufficient_data')
check('mode 不认 → parse_error',
      G.run({'sizes': [100, 200, 400], 'budget': 1000, 'mode': 'diag'})['verdict'] == 'parse_error')

rx = G.run({'sizes': [100, 200, 1500], 'budget': 1000})
check('实测已越预算 → observed_exceeded，且位置对',
      rx['verdict'] == 'observed_exceeded' and rx['detail']['observed_exceeded_at'] == 3, rx['detail'])
check('实测平稳 → bounded_no_guard',
      G.run({'sizes': [500, 500, 500], 'budget': 1000})['verdict'] == 'bounded_no_guard')
check('实测收缩 → bounded_no_guard（并给不截断预算）',
      G.run({'sizes': [800, 400, 200], 'budget': 1000})['verdict'] == 'bounded_no_guard')
check('在增长 → guard_engaged 且三件套都在',
      set(G.run({'sizes': [100, 200, 400], 'budget': 1000})['policies']) >=
      {'raw', 'clamp', 'gain', 'hysteresis'})
r_watch = G.run({'sizes': [100, 200, 400], 'budget': 1000, 'mode': 'watch'})
check('mode=watch 只给参照系（不推三件套）',
      r_watch['verdict'] == 'guard_engaged' and set(r_watch['policies']) == {'raw'})

# ============================================================
# 六、接口与边界
# ============================================================

print('六、接口、边界与确定性')
probes = [{'sizes': [100, 200, 400], 'budget': 1000},
          {'n0': 10, 'rate': 3.0, 'budget': 100},
          {'sizes': [100, 200], 'budget': 1000},
          {'budget': 1000},
          {'sizes': [100, -1, 2], 'budget': 1000},
          {'sizes': [100, 200, 400], 'budget': 1000, 'steps': G.MAX_STEPS + 5}]
check('每个返回点都带 boundary（字符串）',
      all(isinstance(G.run(x).get('boundary'), str) for x in probes))
out_ok = G.run({'sizes': [100, 200, 400], 'budget': 1000})
declared = set(G.PORTS['out'])
check('返回的键都在 PORTS.out 里声明（多返回少声明也是文档说谎）',
      set(out_ok) <= declared, sorted(set(out_ok) - declared))
required = [k for k, t in G.PORTS['out'].items() if not str(t).endswith('?')]
check('PORTS.out 的必返键一个不缺',
      all(k in out_ok for k in required), sorted(set(required) - set(out_ok)))
check('每个返回点都带 verdict 与 detail',
      all('verdict' in G.run(x) and isinstance(G.run(x)['detail'], dict) for x in probes))
a = json.dumps(G.run({'sizes': [100, 200, 400], 'budget': 1000}), sort_keys=True)
b = json.dumps(G.run({'sizes': [100, 200, 400], 'budget': 1000}), sort_keys=True)
check('同输入两次逐字段相同（无随机数，必须严格一致）', a == b)
check('steps 上界本身可用（不越界就照算）',
      G.run({'sizes': [100, 200, 400], 'budget': 10 ** 9, 'steps': G.MAX_STEPS})['verdict']
      == 'guard_engaged')
def imported_modules(path):
    """把文件里的 import 语句挖出来（静态看，不靠字符串搜索）。"""
    tree = _ast.parse(open(path, encoding='utf-8').read())
    names = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for al in node.names:
                names.add(al.name.split('.')[-1])
        elif isinstance(node, _ast.ImportFrom):
            if node.module:
                names.add(node.module.split('.')[-1])
            for al in node.names:
                names.add(al.name.split('.')[-1])
    return names


_gg_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'growth_guard.py')
_imports = imported_modules(_gg_src)
check('本件不 import 收敛诊断/临界诊断（三件事互不顶替）',
      not (_imports & {'converge_check', 'criticality', 'paradox_measure'}), sorted(_imports))
check('不截断预算 == 参照系最大值（对得上，不是另算一套）',
      G.run({'sizes': [100, 200, 400], 'budget': 1000,
             'steps': 6})['recommendation']['no_cut_budget']
      == G.run({'sizes': [100, 200, 400], 'budget': 1000,
                'steps': 6})['policies']['raw']['max_size'])

print('十、口径锚：判据阈值必须成对钉住边界（硬核度① 判据轴）')
# 成对＝边界之内算得出、边界之外拦得住。只钉一边等于不知道边界在哪：
# "拦得住"证明不了"该拦的才拦"。输入一律用常量构造，不写字面量。
check('点数边界之内（= MIN_POINTS 个点）判得出增长率',
      G.run({'sizes': [1.0, 2.0, 4.0], 'budget': 10 ** 6})['verdict']
      == 'guard_engaged')
check('点数不足（少于 MIN_POINTS）→ insufficient_data（不硬判增长率）',
      G.run({'sizes': [1.0, 2.0], 'budget': 10 ** 6})['verdict']
      == 'insufficient_data'
      and G.run({'sizes': [1.0, 2.0], 'budget': 10 ** 6})['growth'] is None)
_r_over = G.run({'sizes': [float(i) for i in range(1, G.MAX_POINTS + 3)],
                 'budget': 10 ** 9})
check('点数边界之外（超 MAX_POINTS）→ size_limit，且报出实际点数',
      _r_over['verdict'] == 'size_limit'
      and _r_over['detail'].get('max_points') == G.MAX_POINTS)
# 容差两侧：实测比值恰好落在 |r−1| ≤ GROWTH_TOL 内算"平稳"，
# 超出即判"增长"。注意本件的比值算了 **+1 平滑**（防除零），
# 所以构造 1.02 会报成 1.019804——断言判的是**三态**，不是那个小数。
def _series(r, n=3):
    xs = [100.0]
    for _ in range(n - 1):
        xs.append(xs[-1] * r)
    return xs


check('容差界内（比值 = 1 + GROWTH_TOL）算平稳',
      G.run({'sizes': _series(1 + G.GROWTH_TOL), 'budget': 10 ** 6,
             'mode': 'watch'})['growth']['kind'] == 'flat')
check('容差界外（比值 = 1 + 1.5×GROWTH_TOL）算增长',
      G.run({'sizes': _series(1 + G.GROWTH_TOL * 1.5), 'budget': 10 ** 6,
             'mode': 'watch'})['verdict'] == 'guard_engaged')

print(f'结果: {PASS}/44 通过')
raise SystemExit(0 if PASS == 44 else 1)
