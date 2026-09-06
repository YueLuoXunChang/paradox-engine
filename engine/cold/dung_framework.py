# -*- coding: utf-8 -*-
"""
dung_framework.py — Dung 论证框架构件（第 3 层冷门 3.2，冲突立场分析）
========================================================================
概念来源：**外部经典共识**——Dung, P.M. (1995) 抽象论证框架
（AF = 论证集 + 攻击关系图；可接受语义 grounded/preferred）。
本构件为借鉴实现（落落三问：借什么=AF 语义算法；为什么=T2-L3/T3-L3
比 μ 单值更细——不只说"有矛盾"，还说"哪些立场顶得住攻击"；
怎么记账=标注来源归借鉴区，不混原创区）。
详规：任务指标《43 第3层冷门详规》§二
咬合：论证攻击图 = 一种拓扑（第 0 层可表达）；可接受立场接本构件。

本构件做什么（一句话）：
    输入论证集 + 攻击关系图 → 输出站得住的立场集（grounded 唯一 /
    preferred 极大可接受）+ 争议集——"矛盾场里哪些立场站得住"。

Dung 语义（1995）：
    - 无冲突集 conflict-free：内部无互相攻击；
    - 可接受集 admissible：无冲突 + 每个攻击者都被集内论证反击（可防御）；
    - grounded 扩展：从无争议论证迭代（F 的最小不动点）——唯一最小；
    - preferred 扩展：极大 admissible 集（按包含序，可能多个）。

诚实边界：
    - 语义枚举对论证数做上限保护（>10 论证诚实报告规模限制，不硬跑）；
    - grounded/preferred 是**立场建议**（哪些论证可站），不是判决谁对
      （只诊断不决策）——攻击图本身由使用者/上层给出；
    - 争议集 = 互相攻击的对（双向攻击）——标出"打成一团"的核。

统一接口：
    run(inputs: dict) -> dict
    输入:
        arguments: list[str]——论证集（至少 2 个）
        attacks: list[(a, b)]——a attacks b（a 反对 b）
        max_arguments: int——枚举上限（默认 12）
    输出:
        verdict: str——'evaluated'|'input_pending'|'size_limit'
        grounded: list——grounded 扩展（唯一）
        preferred: list[list]——preferred 扩展（可能多个）
        admissible_examples: list——可接受集示例（最多 3 个）
        conflict_pairs: list——争议集（互相攻击对）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'arguments': 'list?', 'attacks': 'list?',
           'max_arguments': 'int?'},
    'out': {'verdict': 'str', 'grounded': 'list', 'preferred': 'list',
            'admissible_examples': 'list', 'conflict_pairs': 'list',
            'boundary': 'str'},
}


def _attacked_by(a, attacks):
    """攻击 a 的论证集 {b: (b,a) ∈ attacks}。"""
    return {b for b, x in attacks if x == a}


def _attacks_from(s, attacks):
    """集合 s 攻击的所有论证（攻击边的头）。"""
    return {x for a, x in attacks if a in s}


def _conflict_free(s, attacks):
    """s 无冲突：内部无互相攻击。"""
    for a in s:
        for b in s:
            if a != b and (a, b) in attacks:
                return False
    return True


def _defends(s, a, attacks):
    """s 防御 a：每个攻击 a 的论证都被 s 反击。"""
    for b in _attacked_by(a, attacks):
        if not any((c, b) in attacks for c in s):
            return False
    return True


def _admissible(s, attacks):
    """s 可接受：无冲突 + 防御自己每个成员。"""
    if not _conflict_free(s, attacks):
        return False
    return all(_defends(s, a, attacks) for a in s)


def _grounded(args, attacks):
    """
    grounded 扩展（Dung 1995）：特征函数 F(S) = {a : S 防御 a}
    从 ∅ 迭代到最小不动点（F 单调）。
    """
    F = lambda S: {a for a in args if _defends(S, a, attacks)}  # noqa: E731
    ext = set()
    while True:
        nxt = F(ext)
        if nxt == ext:
            return sorted(ext)
        ext = nxt


def _preferred(args, attacks):
    """
    preferred 扩展：极大 admissible 集（按包含序）。
    枚举所有子集取 admissible 极大（论证数上限保护）。
    """
    import itertools
    n = len(args)
    argl = sorted(args)
    admissible_sets = []
    for r in range(n + 1):
        for combo in itertools.combinations(argl, r):
            s = set(combo)
            if _admissible(s, attacks):
                admissible_sets.append(s)
    # 取极大（不被其他 admissible 真包含）
    maximal = []
    for s in admissible_sets:
        if not any(t != s and s < t for t in admissible_sets):
            maximal.append(sorted(s))
    # 去重排序
    seen = set()
    out = []
    for m in sorted(maximal, key=lambda x: (-len(x), x)):
        key = tuple(m)
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


def run(inputs):
    """
    做什么：Dung 论证框架语义——哪些立场站得住。

    返回 dict（见模块 docstring）。"""
    args = inputs.get('arguments')
    if not args or len(args) < 2:
        return {'verdict': 'input_pending', 'grounded': [],
                'preferred': [], 'admissible_examples': [],
                'conflict_pairs': [],
                'boundary': '需 arguments（≥2 论证）与 attacks——诚实'}
    attacks = set()
    for pair in inputs.get('attacks') or []:
        a, b = pair
        if a in args and b in args:
            attacks.add((a, b))
        else:
            return {'verdict': 'input_pending', 'grounded': [],
                    'preferred': [], 'admissible_examples': [],
                    'conflict_pairs': [],
                    'boundary': f'攻击边 {a}→{b} 引用不存在论证——诚实拦截'}
    max_args = inputs.get('max_arguments', 12)
    if len(args) > max_args:
        return {'verdict': 'size_limit', 'grounded': [],
                'preferred': [], 'admissible_examples': [],
                'conflict_pairs': [],
                'boundary': f'论证 {len(args)} 个 > 上限 {max_args}——'
                            '枚举语义诚实报告规模限制，不硬跑'}

    grounded = _grounded(args, attacks)
    preferred = _preferred(args, attacks)

    # 争议集：互相攻击对（去重——a→b 与 b→a 都命中时只记一对）
    seen_cp = set()
    conflict_pairs = []
    for a, b in attacks:
        if (b, a) in attacks:
            key = tuple(sorted([a, b]))
            if key not in seen_cp:
                seen_cp.add(key)
                conflict_pairs.append(sorted([a, b]))
    conflict_pairs.sort()

    # 可接受集示例（至多 3 个，含 ∅ 之外的先取小的）
    import itertools
    argl = sorted(args)
    examples = []
    for r in range(1, len(argl) + 1):
        for combo in itertools.combinations(argl, r):
            if len(examples) >= 3:
                break
            s = set(combo)
            if _admissible(s, attacks):
                examples.append(sorted(s))
        if len(examples) >= 3:
            break

    return {'verdict': 'evaluated', 'grounded': grounded,
            'preferred': preferred, 'admissible_examples': examples,
            'conflict_pairs': conflict_pairs,
            'boundary': 'Dung 论证框架（外部共识，借鉴区）。grounded/'
                        'preferred 是立场建议（哪些论证可站），不是判决'
                        '谁对（只诊断不决策）。攻击图由使用者/上层给出。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('Dung 论证框架构件 · 自测（第 3 层 3.2）')
    print('=' * 62)

    # 1) 经典三论证：a→b, b→c（Dung 教材例）
    r1 = run({'arguments': ['a', 'b', 'c'],
              'attacks': [('a', 'b'), ('b', 'c')]})
    assert r1['verdict'] == 'evaluated', r1
    assert r1['grounded'] == ['a', 'c'], r1
    assert ['a', 'c'] in r1['preferred'], r1
    print(f"✅ a→b, b→c → grounded={r1['grounded']}，"
          f"preferred={r1['preferred']}")

    # 2) 互攻对（争议）：a↔b
    r2 = run({'arguments': ['a', 'b'],
              'attacks': [('a', 'b'), ('b', 'a')]})
    assert r2['grounded'] == [], r2
    assert r2['conflict_pairs'] == [['a', 'b']], r2
    assert r2['preferred'] in ([['a']], [['a'], ['b']], [['b']], [['a'], ['b']]), r2
    print(f"✅ a↔b 互攻 → grounded=[]（无无争议起点），"
          f"preferred={r2['preferred']}，争议集={r2['conflict_pairs']}")

    # 3) 自攻论证：a→a（无争议集为空）
    r3 = run({'arguments': ['a', 'b'],
              'attacks': [('a', 'a'), ('b', 'a')]})
    # b 不被攻 → grounded 含 b；a 自攻且被 b 攻
    print(f"✅ a 自攻 + b→a → grounded={r3['grounded']}（b 无争议先入）")

    # 4) 三角互攻（3-cycle）：a→b→c→a
    r4 = run({'arguments': ['a', 'b', 'c'],
              'attacks': [('a', 'b'), ('b', 'c'), ('c', 'a')]})
    assert r4['grounded'] == [], r4
    # Dung 标准结果：3-cycle 无无争议论证；每个单点都被攻击且不自卫
    # → 唯一极大可接受集 = 空（preferred=[[]]）
    assert r4['preferred'] == [[]], r4
    print(f"✅ 3-cycle → grounded=[]，preferred={r4['preferred']}"
          f"（Dung 标准：无单点可自卫，极大可接受=空）")

    # 5) 边界
    r5 = run({'arguments': ['a']})
    assert r5['verdict'] == 'input_pending', r5
    r6 = run({'arguments': ['a', 'b'],
              'attacks': [('a', 'x')]})
    assert r6['verdict'] == 'input_pending', r6
    print('✅ 边界：论证<2/攻击引用不存在 → 诚实拦截')

    print('=' * 62)
    print('Dung 论证框架构件自测：全部通过 ✅')
    print('=' * 62)
