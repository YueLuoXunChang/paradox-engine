# -*- coding: utf-8 -*-
"""
ltl.py — 时序逻辑 LTL 构件（第 1 层经典逻辑地基 1.3）
======================================================
概念来源：经典时序逻辑（LTL 标准语义——非落落原创，经典共识）

本构件做什么：
    给"演化/过程/因果链"一个形式语言，判定给定状态路径是否满足
    LTL 性质。算子：
        X φ   下一状态满足 φ
        G φ   所有（未来）状态满足 φ（一直）
        F φ   存在某个未来状态满足 φ（最终）
        φ U ψ φ 一直成立直到 ψ 成立（直到）
    本版做"路径判定"（一条/多条显式路径），不做无限状态系统模型检测
    （那是后续 Büchi 自动机版）。

能力：
    - 路径上的原子命题状态（dict: {原子: 真/假} 或 {原子: True} 稀疏）
    - LTL 公式解析 + 沿路径求值
    - 不满足时输出反例路径前缀（在哪一步违约）

诚实边界：
    - 有穷路径判定；无穷路径的 F(φ) "永不满足"需无穷观察——
      本版在有界路径上判"未满足"，标注有界性；
    - 只判经典 LTL 语义（线性时间），不含 CTL 路径量词（后续构件）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        path: list[dict]，状态序列（每状态 = 原子命题为真的集合或 dict）
        formula: str，LTL 公式（X/G/F/U + 命题联结词 + 原子）
    输出:
        verdict: 'holds' | 'violated' | 'formula_pending' | 'parse_error'
                  | 'empty_path'
        violation_index: int 或 null（首次违约位置）
        boundary: str
"""

PORTS = {
    'in': {'path': 'list?', 'formula': 'str'},
    'out': {'verdict': 'str', 'violation_index': 'int',
            'boundary': 'str'},
}


class _ParseError(ValueError):
    pass


# LTL 一元时态算子（最高优先，类似 ¬）：X, G, F
_TEMP1 = {'X', 'G', 'F'}
# 二元联结词与时态：U
_BIN = {'∧', '∨', '→', '↔', 'U'}
_UN = {'¬'}
_PREC = {'↔': 1, '→': 2, 'U': 3, '∨': 4, '∧': 5}


def _tokenize(s):
    toks = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in '()':
            toks.append(ch)
            i += 1
        elif ch in _BIN or ch in _UN or ch in _TEMP1:
            toks.append(ch)
            i += 1
        elif ch == ' ':
            i += 1
        else:
            j = i
            while j < n and s[j] not in '()' and s[j] != ' ' \
                    and s[j] not in _BIN and s[j] not in _UN \
                    and s[j] not in _TEMP1:
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


class _P:
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def next(self):
        t = self.peek()
        self.pos += 1
        return t

    def expect(self, ch):
        t = self.next()
        if t != ch:
            raise _ParseError(f"期望 '{ch}'，得到 '{t}'")

    def parse(self, min_prec=0):
        t = self.peek()
        if t is None:
            raise _ParseError("公式不完整")
        if t == '(':
            self.next()
            node = self.parse(0)
            self.expect(')')
        elif t == '¬':
            self.next()
            node = ('¬', self.parse(6))
        elif t in _TEMP1:
            self.next()
            node = (t, self.parse(6))
        elif t in _BIN or t == ')':
            raise _ParseError(f"缺左操作数：'{t}'")
        else:
            node = ('atom', t)
            self.next()
        while True:
            op = self.peek()
            if op in _BIN:
                prec = _PREC[op]
                if prec < min_prec:
                    break
                self.next()
                right = self.parse(prec + 1)
                node = (op, node, right)
            else:
                break
        return node


def parse(s):
    toks = _tokenize(s)
    if not toks:
        raise _ParseError("空公式")
    p = _P(toks)
    node = p.parse()
    if p.pos != len(p.toks):
        raise _ParseError(f"多余内容: {p.toks[p.pos:]}")
    return node


# ============================================================
# 沿路径求值
# path[i] 视为"状态 i 中为真的原子集合"（list/set/dict keys）
# ============================================================

def _state_atoms(state):
    """状态 → 原子集合（dict 取 keys，list/set 直接用）。"""
    if isinstance(state, dict):
        return set(state.keys())
    return set(state)


def holds_at(ast, path, i):
    """公式 ast 在路径 path 的位置 i 是否满足。返回 (bool, fail_at)。"""
    k = ast[0]
    if k == 'atom':
        return (ast[1] in _state_atoms(path[i])), i
    if k == '¬':
        v, f = holds_at(ast[1], path, i)
        return (not v), f
    if k == '∧':
        v1, f1 = holds_at(ast[1], path, i)
        if not v1:
            return False, f1
        return holds_at(ast[2], path, i)
    if k == '∨':
        v1, f1 = holds_at(ast[1], path, i)
        if v1:
            return True, None
        v2, f2 = holds_at(ast[2], path, i)
        return v2, f2
    if k == '→':
        v1, f1 = holds_at(ast[1], path, i)
        if not v1:
            return True, None
        return holds_at(ast[2], path, i)
    if k == '↔':
        v1, _ = holds_at(ast[1], path, i)
        v2, _ = holds_at(ast[2], path, i)
        return (v1 == v2), i
    if k == 'X':
        if i + 1 >= len(path):
            return False, i  # 路径尽头无下一状态 → X 违约
        return holds_at(ast[1], path, i + 1)
    if k == 'G':
        # 所有未来状态（含当前）都满足；违约 = 第一个不满足的位置
        for j in range(i, len(path)):
            v, f = holds_at(ast[1], path, j)
            if not v:
                return False, (f if f is not None else j)
        return True, None
    if k == 'F':
        # 存在未来状态满足（含当前）
        for j in range(i, len(path)):
            v, _ = holds_at(ast[1], path, j)
            if v:
                return True, None
        # 有界路径内未满足
        return False, len(path) - 1
    if k == 'U':
        # φ U ψ：存在 j≥i 使 ψ 在 j 真，且 ∀k∈[i,j) φ 真
        for j in range(i, len(path)):
            vj, fj = holds_at(ast[2], path, j)
            if vj:
                # 检查 [i, j) 间 φ 都真
                for k in range(i, j):
                    vk, fk = holds_at(ast[1], path, k)
                    if not vk:
                        return False, (fk if fk is not None else k)
                return True, None
            # 当前不满足 ψ → 当前位置必须满足 φ，否则违约
            vk, fk = holds_at(ast[1], path, i)
            if not vk:
                return False, (fk if fk is not None else i)
        # 路径走完 ψ 从未满足 → 违约
        return False, len(path) - 1
    raise _ParseError(f"未知节点 {k}")


def check_path(path, formula):
    """整条路径（从位置 0）是否满足公式。"""
    ast = parse(formula)
    v, f = holds_at(ast, path, 0)
    return v, f


# ============================================================
# 机制统一入口
# ============================================================

def run(inputs):
    """
    做什么：LTL 路径判定——给定状态路径，公式是否满足。

    输入:
        path: list，状态序列（每状态 = 原子命题为真的集合/dict）
        formula: str，LTL 公式

    返回:
        dict
    """
    formula = inputs.get('formula')
    path = inputs.get('path')

    if not formula:
        return {'verdict': 'formula_pending', 'violation_index': None,
                'boundary': '需先提供 LTL 公式（如 "G(¬down)"）——诚实：不硬判'}
    if not path:
        return {'verdict': 'empty_path', 'violation_index': None,
                'boundary': '状态路径为空——无法判定（诚实：至少需一个状态）'}

    try:
        v, fail = check_path(path, formula)
        if v:
            return {'verdict': 'holds', 'violation_index': None,
                    'boundary': f'路径 {len(path)} 步，LTL 性质满足（线性'
                                f'时间语义）'}
        return {'verdict': 'violated', 'violation_index': fail,
                'boundary': f'路径 {len(path)} 步，位置 {fail} 违约'
                            f'（若含 F/∞ 语义：有界路径内未满足，非"永不"'
                            f'判定——诚实边界）'}
    except _ParseError as e:
        return {'verdict': 'parse_error', 'violation_index': None,
                'boundary': f'公式解析失败：{e}（诚实拦截，不硬算）'}


# ============================================================
# 自测
# ============================================================

if __name__ == '__main__':
    print('=' * 62)
    print('时序逻辑 LTL 构件 · 自测（经典逻辑层 1.3）')
    print('=' * 62)

    # 路径：s0 正常, s1 down, s2 恢复, s3 正常
    p = [{'正常'}, {'down'}, {'恢复'}, {'正常'}]

    # 1) G(¬down) 在含 down 的路径 → violated @1
    r1 = run({'path': p, 'formula': 'G(¬down)'})
    assert r1['verdict'] == 'violated' and r1['violation_index'] == 1, r1
    print('✅ G(¬down) 在含 down 路径 → violated @1')

    # 2) F(恢复) 在最终恢复路径 → holds
    r2 = run({'path': p, 'formula': 'F(恢复)'})
    assert r2['verdict'] == 'holds', r2
    print('✅ F(恢复) 最终恢复 → holds')

    # 3) X(¬正常) 在 s0 后是 down（down 即 ¬正常，若用完整集合则需 ¬正常）
    #    用稀疏集合：s1={down} 不包含 正常 → ¬正常 在 s1 真
    r3 = run({'path': p, 'formula': 'X(¬正常)'})
    assert r3['verdict'] == 'holds', r3
    print('✅ X(¬正常)：s1 不含 正常 → holds')

    # 4) G(正常) → violated（s1 down）
    r4 = run({'path': p, 'formula': 'G(正常)'})
    assert r4['verdict'] == 'violated', r4
    print('✅ G(正常) → violated @1')

    # 5) φ U ψ：正常 U 恢复 → 在 down 位置违约（φ=正常 在 s1 假，ψ 未到）
    r5 = run({'path': p, 'formula': '正常 U 恢复'})
    assert r5['verdict'] == 'violated', r5
    print(f"✅ 正常 U 恢复 → violated @{r5['violation_index']}（s1 违约）")

    # 5b) 全程无 down 的路径 G 满足
    r5b = run({'path': [{'正常'}, {'正常'}, {'完成'}], 'formula': 'G(¬down)'})
    assert r5b['verdict'] == 'holds', r5b
    print('✅ 无 down 路径 G(¬down) → holds')

    # 6) 全部正常路径 G 满足
    p2 = [{'正常'}, {'正常'}, {'正常'}]
    r6 = run({'path': p2, 'formula': 'G(正常)'})
    assert r6['verdict'] == 'holds', r6
    print('✅ 全正常路径 G(正常) → holds')

    # 7) 解析错误
    r7 = run({'path': p, 'formula': 'G('})
    assert r7['verdict'] == 'parse_error', r7
    print('✅ 残缺公式 → parse_error')

    # 8) 空路径 / 缺公式
    r8 = run({'path': [], 'formula': 'G(正常)'})
    assert r8['verdict'] == 'empty_path', r8
    r9 = run({'path': p})
    assert r9['verdict'] == 'formula_pending', r9
    print('✅ 空路径/缺公式 → 诚实报告')

    print('=' * 62)
    print('时序逻辑 LTL 构件自测：全部通过 ✅')
    print('=' * 62)
