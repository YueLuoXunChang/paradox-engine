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
