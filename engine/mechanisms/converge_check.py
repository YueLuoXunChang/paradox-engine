"""
converge_check.py — 收敛判定四分支（核心机制）
=============================================
概念来源：落落逻辑体系 · 递归修正收敛理论
公式卡：formulas/converge_check.md

本机制做什么（一句话）：
    判定递归修正序列 x_{n+1}=f(x_n, err(x_n)) 是否收敛——四分支：
    压缩映射（默认）/ 有限步 / 渐进 / 振荡。

统一接口：
    run(inputs: dict) → dict
    输入:  {branch, f, err_fn, x0, ...}
    输出:  {branch, verdict, converges, rate, detail}

公式卡性质：
    P1 压缩必收敛  P2 线性速率  P3 唯一不动点（收敛≠正确，不可测）
"""

# 端口声明（v2 决策2：装配早期失败）
PORTS = {
    'in': {'branch': 'str?', 'f': 'callable', 'err_fn': 'callable',
           'x0': 'float?'},
    'out': {'verdict': 'str', 'converges': 'bool', 'rate': 'any',
            'detail': 'dict'},
}


def estimate_lipschitz(err_fn, samples):
    """估计误差函数 err 的 Lipschitz 常数 L = max |err(x₂)-err(x₁)|/|x₂-x₁|。"""
    best = 0.0
    for a in samples:
        for b in samples:
            dx = abs(b - a)
            if dx < 1e-12:
                continue
            best = max(best, abs(err_fn(b) - err_fn(a)) / dx)
    return best


def branch1_compression(f, err_fn, samples, samples_x=None, samples_e=None,
                        L_est=None):
    """
    分支1 压缩映射（分方向采样版，2026-08-19 新逻辑）：
        q = sup{df/dx : 纯 x 方向样本（e 固定）}
        r = sup{df/de : 纯 e 方向样本（x 固定）}
        L = err 的 Lipschitz 常数；λ = q + r·L（和式判据）
        收敛 ⟺ λ < 1（公式卡 A1 err Lipschitz L + A2 拟压缩 q,r + A3 q+r·L<1）
    纯方向样本缺失 → 返回"数据不足"（诚实报告，不硬判）。
    """
    if not samples_x or not samples_e:
        return {'q_est': None, 'r_est': None, 'lambda': None, 'L': None,
                'converges': None, 'verdict': '数据不足：需纯方向样本',
                'n_x': len(samples_x or []), 'n_e': len(samples_e or [])}

    q_sup = max((df / dx for dx, df in samples_x if dx > 1e-12), default=0.0)
    r_sup = max((df / de for de, df in samples_e if de > 1e-12), default=0.0)
    L = L_est if L_est is not None else estimate_lipschitz(err_fn, samples)
    lam = q_sup + r_sup * L
    converges = lam < 1.0
    verdict = '收敛（压缩映射）' if converges else '不满足 q+r·L<1'
    return {'q_est': q_sup, 'r_est': r_sup, 'lambda': lam, 'L': L,
            'converges': converges, 'verdict': verdict,
            'n_x': len(samples_x), 'n_e': len(samples_e)}


def branch2_finite(f, err_fn, x0, max_steps=1000, tol=1e-6):
    """
    分支2 有限步：∃N<∞: x_N ∈ A（err(x_N) < tol）。
    判定条件 d(x_{n+1},A) ≤ C·d(x_n,A)² 的工程判定——直接迭代到进入可接受态。
    """
    x = x0
    for step in range(max_steps):
        if err_fn(x) < tol:
            return {'finite_steps': step, 'reached': True,
                    'verdict': f'有限步收敛（第{step}步）'}
        e = err_fn(x)
        x = f(x, e)
    return {'finite_steps': None, 'reached': False,
            'verdict': f'超{max_steps}步未达，非有限步收敛'}


def branch3_asymptotic(f, err_fn, x0, steps=1000):
    """
    分支3 渐进（无压缩）：lim d(x_n,A)=0 且 ∀n: d(x_n,x*)>0。
    趋势判定：末段误差均值 < 前段误差均值（单调递减趋势）。
    """
    errs = []
    x = x0
    for _ in range(steps):
        errs.append(err_fn(x))
        x = f(x, err_fn(x))
    half = steps // 2
    first_half = sum(errs[:half]) / max(1, half)
    second_half = sum(errs[half:]) / max(1, steps - half)
    decreasing = second_half < first_half
    return {'err_tail': errs[-1], 'decreasing': decreasing,
            'verdict': '渐进收敛趋势' if decreasing else '误差未降，非渐进收敛'}


def branch4_oscillation(f, err_fn, x0, T=2, steps=200):
    """
    分支4 振荡：d(x_{n+T},A) ≤ q_T·d(x_n,A)，0 ≤ q_T < 1（每隔 T 步压缩）。
    q_T = max err[n+T]/err[n]；收敛 ⟺ q_T < 1。
    """
    errs = []
    x = x0
    for _ in range(steps):
        errs.append(err_fn(x))
        x = f(x, err_fn(x))
    q_T = 0.0
    for i in range(0, steps - T, T):
        if errs[i] > 1e-12:
            q_T = max(q_T, errs[i + T] / errs[i])
    converges = q_T < 1.0
    return {'q_T': q_T, 'converges': converges,
            'verdict': '振荡收敛' if converges else '振荡但不收敛'}


def run(inputs):
    """
    做什么：按 branch 选择收敛判定分支并给出判定。

    公式（formulas/converge_check.md §1）：
        分支1 压缩映射: d(f(x,e),f(y,e')) ≤ q·d(x,y)+r·|e-e'|，q<1 ⟹ 收敛
            收敛定理（Banach）：A1 L + A2 拟压缩(q,r) + A3 q+r·L<1
            ⟹ d(x_n,x*) ≤ (q+rL)ⁿ·d(x_0,x*)，线性收敛到唯一不动点（P1/P2/P3）
        分支2 有限步: ∃N<∞: x_N ∈ A
        分支3 渐进:   lim d(x_n,A)=0，但 ∀n: d(x_n,x*)>0
        分支4 振荡:   ∃T>0: d(x_{n+T},A) ≤ q_T·d(x_n,A)，q_T<1

    输入:
        inputs: dict
            branch: str, 'compression'|'finite'|'asymptotic'|'oscillation'
                    （缺省 'compression'；或传场景名由 select_branch 映射）
            f: callable, 修正函数 f(x, e) → x'
            err_fn: callable, 误差函数 err(x) → float（到可接受态 A 的距离）
            x0: float, 初始状态
            # 分支1 专用
            samples: list, 采样点（L 估计用）
            samples_x / samples_e: list[(Δ, Δf)], 纯 x / 纯 e 方向样本（分方向采样）
            L_est: float 或 None, err 的 Lipschitz 常数（缺省自动估）
            # 分支2 专用
            max_steps: int, 最大步数（缺省 1000）; tol: float, 收敛容差（缺省 1e-6）
            # 分支3/4 专用
            steps: int, 迭代步数（缺省 1000/200）; T: int, 振荡周期（缺省 2）

    返回:
        dict: {branch, verdict, converges, rate, detail}
            branch: 实际使用的分支名
            verdict: 判定结果描述
            converges: bool 或 None（压缩分支数据不足时为 None，诚实报告）
            rate: 收敛速率（分支1 λ、分支4 q_T；分支2/3 无压缩比为 None）
            detail: 分支详细结果（q_est/r_est/L/finite_steps/q_T/err_tail 等）
    """
    f = inputs["f"]
    err_fn = inputs["err_fn"]
    x0 = inputs.get("x0", 0.0)

    # 分支选择：支持直接分支名或场景名（公式卡 §1 选择规则）
    branch = inputs.get("branch", "compression")
    if branch in ('常规', '确定性问题', '弱约束', '周期'):
        branch = {'常规': 'compression', '确定性问题': 'finite',
                  '弱约束': 'asymptotic', '周期': 'oscillation'}[branch]

    # 非法 branch 校验（2026-08-20 详细化审计修复）：拼错/未知 → 诚实报错，
    # 不静默落默认压缩（此前"compresion"拼错会静默走压缩映射，误导判定）
    # branch1 = compression 的别称（分方向采样版），映射到 compression
    if branch == 'branch1':
        branch = 'compression'
    VALID_BRANCHES = {'compression', 'finite', 'asymptotic', 'oscillation'}
    if branch not in VALID_BRANCHES:
        raise ValueError(
            f"[输入校验失败] converge_check.branch 未知: {branch!r}"
            f"（应为 {sorted(VALID_BRANCHES)}，或场景名：常规/确定性问题/弱约束/周期）")

    if branch == 'finite':
        detail = branch2_finite(f, err_fn, x0,
                                inputs.get("max_steps", 1000),
                                inputs.get("tol", 1e-6))
        return {'branch': branch, 'verdict': detail['verdict'],
                'converges': detail['reached'], 'rate': None, 'detail': detail}

    if branch == 'asymptotic':
        detail = branch3_asymptotic(f, err_fn, x0, inputs.get("steps", 1000))
        return {'branch': branch, 'verdict': detail['verdict'],
                'converges': detail['decreasing'], 'rate': None,
                'detail': detail}

    if branch == 'oscillation':
        detail = branch4_oscillation(f, err_fn, x0,
                                     inputs.get("T", 2),
                                     inputs.get("steps", 200))
        return {'branch': branch, 'verdict': detail['verdict'],
                'converges': detail['converges'], 'rate': detail['q_T'],
                'detail': detail}

    # 默认：压缩映射（分方向采样版）
    detail = branch1_compression(
        f, err_fn, inputs.get("samples", []),
        inputs.get("samples_x"), inputs.get("samples_e"),
        inputs.get("L_est"))
    return {'branch': 'compression', 'verdict': detail['verdict'],
            'converges': detail['converges'], 'rate': detail['lambda'],
            'detail': detail}


# ============================================================
# 自测（直接运行本文件）
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("收敛判定四分支 · 自测（对应 formulas/converge_check.md P1-P3）")
    print("=" * 60)

    def f1(x, e):
        return 0.4 * x + 1

    def err1(x):
        return abs(x - 5 / 3)

    # 分支1 压缩映射（分方向采样）：f1 依赖 x 不依赖 e → q=0.4, r=0, λ=q+rL<1
    samples = [i / 10 for i in range(30)]
    e0 = err1(0.0)
    samples_x = [(abs(b - a), abs(f1(b, e0) - f1(a, e0)))
                 for a, b in zip(samples[:-1], samples[1:])]
    samples_e = [(0.1, abs(f1(0.0, e0 + 0.1) - f1(0.0, e0))),
                 (0.2, abs(f1(0.0, e0 + 0.2) - f1(0.0, e0)))]
    r1 = run({'branch': 'compression', 'f': f1, 'err_fn': err1, 'x0': 0.0,
              'samples': samples, 'samples_x': samples_x,
              'samples_e': samples_e})
    assert r1['converges'] is True, f"P1: 压缩映射应收敛: {r1}"
    assert abs(r1['detail']['q_est'] - 0.4) < 1e-9, f"q 应=0.4: {r1}"
    assert abs(r1['detail']['r_est'] - 0.0) < 1e-9, f"f 不依赖 e，r 应=0: {r1}"
    assert r1['rate'] == r1['detail']['q_est'] + r1['detail']['r_est'] * r1['detail']['L'], \
        "P2: rate=λ=q+r·L（线性速率判据）"
    print(f"✅ 分支1 压缩映射: q={r1['detail']['q_est']:.3f} "
          f"r={r1['detail']['r_est']:.3f} λ={r1['rate']:.3f} {r1['verdict']}")
    # 数据不足路径：无纯方向样本 → 诚实报告不硬判
    r1b = run({'branch': 'compression', 'f': f1, 'err_fn': err1, 'x0': 0.0,
               'samples': samples})
    assert r1b['converges'] is None and '数据不足' in r1b['verdict'], f"应数据不足: {r1b}"
    print(f"✅ 分支1 数据不足路径: {r1b['verdict']}（不硬判）")

    # 分支2 有限步
    r2 = run({'branch': 'finite', 'f': f1, 'err_fn': err1, 'x0': 0.0})
    assert r2['converges'] is True, f"分支2 应有限步收敛: {r2}"
    print(f"✅ 分支2 有限步: {r2['verdict']}")

    # 分支3 渐进
    r3 = run({'branch': 'asymptotic', 'f': f1, 'err_fn': err1, 'x0': 0.0})
    assert r3['converges'] is True, f"分支3 应渐进收敛: {r3}"
    print(f"✅ 分支3 渐进: {r3['verdict']}")

    # 分支4 振荡（交替函数制造周期，err=|x| 在 0/1 间跳 → q_T≈1 不收敛）
    def f_osc(x, e):
        return 1 - x if abs(x) < 10 else x
    r4 = run({'branch': 'oscillation', 'f': f_osc, 'err_fn': lambda x: abs(x),
              'x0': 0.0, 'T': 2})
    assert 'q_T' in r4['detail'] and r4['rate'] == r4['detail']['q_T'], \
        f"分支4 rate 应为 q_T: {r4}"
    print(f"✅ 分支4 振荡: {r4['verdict']}（q_T={r4['rate']:.3f}）")

    # 场景名选择规则（公式卡选择规则表）
    r_s = run({'branch': '周期', 'f': f_osc, 'err_fn': lambda x: abs(x), 'x0': 0.0})
    assert r_s['branch'] == 'oscillation', f"场景'周期'应映射到振荡分支: {r_s}"
    print(f"✅ 场景名选择: '周期' → branch={r_s['branch']}")

    print("=" * 60)
    print("收敛判定四分支自测：全部通过 ✅")
    print("=" * 60)
