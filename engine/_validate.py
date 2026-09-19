# -*- coding: utf-8 -*-
"""
_validate.py — 输入校验小工具（构件共用的诚实拦截判据）
=============================================================
为什么需要它（真实踩坑）：
    旗舰构件 μ 测度原先不校验数值——`wA=5, wNotA=-5` 算出 **μ = -9999999999.0**
    （违反自己声明的 μ∈[0,1]），`wA="五"` 直接 `TypeError` 崩。构件的"诚实边界"
    要求：**语义非法的输入必须被拦截并说明**，绝不能算出一个看起来像结果的东西。

设计原则：
    - 判据集中在一处（避免 29 个构件各写一套、各漏一处）；
    - 只做**类型与取值域**校验，不做业务判断（业务边界仍在各构件里）；
    - 校验失败返回中文说明字符串（构件直接放进 error/boundary 字段）。

注意 bool 是 int 的子类：`True` 不该被当成权重 1 接受——显式排除。
"""

import numbers


def is_number(x):
    """是否是可用于计算的实数（bool 不算）。"""
    return isinstance(x, numbers.Real) and not isinstance(x, bool)


def bad_number(x):
    """不是实数 → 返回中文说明；是实数 → None。"""
    if is_number(x):
        return None
    if isinstance(x, bool):
        return f'{x!r} 是布尔值——数值参数不接受布尔（易与 0/1 混淆）'
    return f'{x!r}（{type(x).__name__}）不是数值'


def bad_nonneg(x, name):
    """要求非负实数 → 返回中文说明；合法 → None。"""
    err = bad_number(x)
    if err:
        return f'{name} 非法：{err}'
    if x < 0:
        return f'{name} 非法：{x!r} 为负数——权重/度量不接受负值'
    return None


def check_nonneg(**kw):
    """批量校验非负实数。返回 (ok, 说明)；说明为 None 表示全部合法。

    用法：
        ok, why = check_nonneg(wA=wA, wNotA=wNotA)
        if not ok:
            return {'mu': None, 'error': why + '——诚实拦截，不硬算'}
    """
    for name, val in kw.items():
        err = bad_nonneg(val, name)
        if err:
            return False, err
    return True, None


# ── 参数类型闸（按构件声明的 PORTS['in'] 挡错类型）
# 为什么：random fuzz 撞出 equality_tableau 在 conclusion=True/-5/dict 上
# `len()` 崩——这类"错类型"是**系统性**的（29 个构件都可能中），所以按声明
# 契约先挡一道。挂载层（call_tool）与总控（controller 适配器）共用本函数，
# 两条路都不把错类型透给构件。
_TYPE_CHECKERS = {
    'str': lambda v: isinstance(v, str),
    'dict': lambda v: isinstance(v, dict),
    'list': lambda v: isinstance(v, (list, tuple)),
    # 数值：bool 是 int 子类，明确排除（易与 0/1 混淆）
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'float': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    'bool': lambda v: isinstance(v, bool),
    'callable': callable,
}


def arg_type_error(ports_in, args):
    """按 PORTS['in'] 校验实参类型。返回中文说明；无问题返回 None。

    · 只查**声明了类型**且**实参已提供**的字段（缺参由构件自己拦）；
    · None 一律放行（多为"可省"语义，交给构件判定）；
    · 'object' 等无判据的类型不限。
    """
    if not isinstance(args, dict):
        return f'arguments 应为对象（dict），得到 {type(args).__name__}'
    for field, spec in (ports_in or {}).items():
        if field not in args:
            continue
        checker = _TYPE_CHECKERS.get(str(spec).rstrip('?'))
        if checker is None:
            continue
        val = args[field]
        if val is None:
            continue
        if not checker(val):
            return (f'参数 {field} 类型不符：声明 {str(spec).rstrip("?")}，'
                    f'得到 {type(val).__name__}——按声明契约拦下'
                    '（不把错类型透传给构件）')
    return None
