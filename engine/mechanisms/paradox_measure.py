"""
paradox_measure.py — 悖论测度 μ（核心机制）
=============================================
概念来源：落落逻辑体系 · P-Logic 悖论代数系统
公式卡：formulas/paradox_measure.md

本机制做什么（一句话）：
    计算命题的矛盾强度 μ ∈ [0,1]（四分支路由）。

统一接口：
    def run(inputs: dict) -> dict
    输入:  {proposition, mode, wA, wNotA, tau_L1, tau_L2}
    输出:  {mu, branch}

四分支：
    mu1 证据权重型（默认）：1 - |wA-wNotA|/(wA+wNotA+ε)
    mu2 自指型：X=¬X 时取 1
    mu3 层级型：|tau_L1 - tau_L2|
    mu4 熵权型：H(p)/log2（香农熵）

扩展方式：
    新分支 → 在本文件加分支 + 在 choose_branch 加路由
"""

import math

EPS = 1e-9

# 端口类型声明（v2 决策2：builder 装配早期校验用）
# in: 输入字段及类型；out: 输出字段及类型
PORTS = {
    'in': {'mode': 'str', 'wA': 'float?', 'wNotA': 'float?'},
    'out': {'mu': 'float', 'branch': 'str'},
}


def choose_branch(is_self_ref=False, has_layers=False, need_entropy=False):
    """
    做什么：按输入特征路由悖论测度分支。

    优先级：mu2(自指) > mu3(层级) > mu4(熵) > mu1(默认)

    参数:
        is_self_ref: bool, 是否自指不动点
        has_layers: bool, 是否跨层真值
        need_entropy: bool, 是否需要熵视角

    返回:
        str: 分支名 'mu1'|'mu2'|'mu3'|'mu4'
    """
    if is_self_ref:
        return 'mu2'
    if has_layers:
        return 'mu3'
    if need_entropy:
        return 'mu4'
    return 'mu1'


def _mu1(wA, wNotA):
    """证据权重型：wA=wNotA → 1（完全悖论）；wA=0,wNotA=0 → 1（双无证据=不可判定）。"""
    denom = wA + wNotA + EPS
    return 1.0 - abs(wA - wNotA) / denom


def _mu2():
    """自指型：直接取完全悖论。"""
    return 1.0


def _mu3(tau_L1, tau_L2):
    """层级型：跨层真值差。"""
    return abs(tau_L1 - tau_L2)


def _mu4(wA, wNotA):
    """熵权型：p=0.5 最大熵=1；p→0/1 → 0。

    边界处理（2026-08-16 修复，公式卡 P8 闭环发现）：
        原判定 p<=0 or p>=1 严格边界——但 EPS=1e-9 使 p=5/(5+1e-9)≈0.9999999998
        不触发 p>=1，落入熵计算，(1-p)·log2(1-p) 残留 ~7e-9。
        修复：边界容差 TOL 须覆盖 EPS 造成的偏移（ε/wA 量级，约 2e-10），
        取 TOL = 1e-6 确保 P8（p→1 时 μ→0）成立，同时不误伤中段。
    """
    TOL = 1e-6
    p = wA / (wA + wNotA + EPS)
    if p <= TOL or p >= 1.0 - TOL:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def run(inputs):
    """
    做什么：计算悖论测度 μ（统一接口，供 builder 装配）。

    输入:
        inputs: dict
            proposition: 命题标识（可选）
            mode: str 或 None, 强制指定分支（默认自动路由）
            wA/wNotA: 证据权重（mu1/mu4 用）
            tau_L1/tau_L2: 跨层真值（mu3 用）
            is_self_ref/has_layers/need_entropy: 路由特征（可选）

    返回:
        dict: {mu, branch, proposition}
    """
    proposition = inputs.get("proposition", "?")
    mode = inputs.get("mode")
    wA = inputs.get("wA", 0)
    wNotA = inputs.get("wNotA", 0)
    tau_L1 = inputs.get("tau_L1")
    tau_L2 = inputs.get("tau_L2")

    # 未指定分支时自动路由
    if mode is None:
        mode = choose_branch(
            inputs.get("is_self_ref", False),
            inputs.get("has_layers", False),
            inputs.get("need_entropy", False))

    # 非法 mode 诚实拦截（2026-09-06 补：未知/拼错 mode 曾静默落 mu1——
    # 与 μ₂ 丢 else 分支同类隐患：改了分支不知道。显式报错兜测试）
    if mode not in ('mu1', 'mu2', 'mu3', 'mu4'):
        return {'mu': None, 'branch': mode,
                'proposition': proposition,
                'error': f'未知分支 mode={mode!r}（应为 mu1/mu2/mu3/mu4）'
                         '——诚实拦截，不静默落默认'}
    if mode == 'mu3' and (tau_L1 is None or tau_L2 is None):
        return {'mu': None, 'branch': mode, 'proposition': proposition,
                'error': 'mu3 层级型需 tau_L1/tau_L2（跨层真值）——'
                         '诚实拦截，不硬算'}
    if mode == 'mu2':
        mu = _mu2()
    elif mode == 'mu3':
        mu = _mu3(tau_L1, tau_L2)
    elif mode == 'mu4':
        mu = _mu4(wA, wNotA)
    else:  # mu1 默认
        mu = _mu1(wA, wNotA)

    return {'mu': mu, 'branch': mode, 'proposition': proposition}


# ============================================================
# 自测（直接运行本文件）
# ============================================================

if __name__ == "__main__":
    assert abs(run({"wA": 5, "wNotA": 5, "mode": "mu1"})['mu'] - 1.0) < 1e-9
    assert abs(run({"wA": 10, "wNotA": 0, "mode": "mu1"})['mu'] - 0.0) < 1e-9
    assert run({"mode": "mu2"})['mu'] == 1.0
    assert abs(run({"tau_L1": 1, "tau_L2": 0, "mode": "mu3"})['mu'] - 1.0) < 1e-9
    assert abs(run({"wA": 5, "wNotA": 5, "mode": "mu4"})['mu'] - 1.0) < 1e-9
    assert run({"proposition": "A∧¬A", "is_self_ref": True})['branch'] == 'mu2'
    print("✅ 悖论测度 μ 自测通过")
