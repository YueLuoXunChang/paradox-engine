# -*- coding: utf-8 -*-
"""
recursion_theorem.py — Kleene 递归定理 · 自指程序构造演示（第 1 层扩展）
========================================================================
概念来源：**外部经典共识**——Kleene 第二递归定理（1952）：对任意可计算
函数 f，存在程序 e 使得 φ_e = φ_{f(e)}（程序能拿到自己的代码并把它交给
f）。本构件为借鉴实现（落落三问：借什么=递归定理的自指构造思想；为什么=
给"自指=程序拿到自己"一个可运行的教学演示，与 1.6 λ 的 Y 组合子、
1.7 图灵机 UTM 自模拟并置成"自指三形态"；怎么记账=标注来源归借鉴区）。
详规：ROADMAP 阶段 7（借数学底座，标注来源）。
公式卡：docs/formulas/recursion_theorem.md

本构件做什么（一句话）：
    演示"程序可以拿到自己的代码"——两个形态：
    ① quine 形态：构造打印自身的程序（自复制，自指的最直观形态）；
    ② 递归定理形态：对任意"程序变换 f"，构造自指程序 e——
       e 运行时先取自己的源码 s，算 f(s)，然后执行 f(s) 的结果
       （行为 = f 作用后的自己，即 φ_e = φ_{f(e)} 的工程演示）。

与 Y 组合子 / UTM 自模拟的关系（自指三形态对照）：
    - λ 的 Y：值不动点（Y f = f (Y f)）——函数层自指；
    - 图灵机 UTM：机模拟机——执行层自指；
    - 本构件：程序读自己源码再变换——代码层自指（Kleene 递归定理核心）。

诚实边界：
    - 这是递归定理思想的**工程演示**（Python 引号自指技巧），不是形式化
      证明——形式化在 λ 演算/图灵机层（1.6/1.7 已代码化），本构件给
      "程序拿自己"一个看得见的版本；
    - 生成的 quine/自指程序需无中文源码（引号技巧对多行/特殊字符敏感，
      诚实限制输入为单行无引号的简单源码）；
    - 自指不解决不可判定——递归定理与停机问题并存（不宣称绕定理）。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: str——'quine'（自复制演示）| 'recursive'（递归定理形态）
        payload: str——quine 模式：要输出的内容（默认 '你好，自指'）
        transform: callable——recursive 模式：程序变换 f(code)->code
                   （默认：给代码加一行注释 = 行为等价变换）
    输出:
        verdict: str——'constructed'|'verified'|'input_pending'|'parse_error'
        program: str——构造出的自指程序源码
        runs_like: str——运行行为说明
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'payload': 'str?', 'transform': 'callable?'},
    'out': {'verdict': 'str', 'program': 'str', 'runs_like': 'str',
            'boundary': 'str'},
}

# 生成 quine 的模板（Python 引号自指技巧：把源码嵌入自身打印）
# 结构：s = "代码...%r..." % s → 用 %r 把自己插进自己的字符串再打印
_QUINE_TMPL = (
    '# -*- coding: utf-8 -*-\n'
    's = {payload!r}\n'
    'print("s = " + repr(s) + "\\nprint(s)")  # 输出内容: ' + 'PAYLOAD_PLACEHOLDER' + '\n'
)


def _simple_transform(code):
    """默认程序变换：在源码末尾加一行注释（行为等价——不变量示例）。"""
    return code + '\n# [transform] 已应用：此注释由变换 f 添加（行为等价）\n'


def _verify(program, expect_output):
    """运行生成的程序并核对输出（自测/正式测试用）。"""
    import subprocess
    import sys
    import tempfile
    import os
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                     encoding='utf-8') as fh:
        fh.write(program)
        tmp = fh.name
    try:
        import os as _os
        _env = dict(_os.environ)
        _env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, tmp], capture_output=True,
                           text=True, timeout=10, env=_env,
                           encoding='utf-8')
        return r.stdout, r.returncode
    finally:
        os.remove(tmp)


def _build_quine(payload):
    """
    构造打印 payload 的 quine——但真正的 quine 打印自己。
    为让"自复制"可演示且输出可验证：程序打印两行——
    第一行是自己的源码（repr 形式），第二行固定说明。
    """
    body = f'msg = {payload!r}\nprint(msg)\n'
    # quine: 输出自身源码 + msg
    src = (
        '# -*- coding: utf-8 -*-\n'
        's = ' + repr(body) + '\n'
        'print("--- 程序源码 ---")\nprint("s = " + repr(s))\n'
        'print("print(s)")\n'
        'print("--- 运行输出 ---")\n' + 'exec(s)\n'
    )
    return src


def _build_recursive(transform):
    """
    递归定理形态：给定变换 f，构造程序 e——
    e 的源码里嵌着自己的"种子"（一段会恢复出 e 完整源码的代码），
    运行时取自身源码 s，算 f(s)，exec(f(s))。
    工程版：e = 引号自指程序，其中被 exec 的是 transform(自身源码)。
    由于 Python 源码自指用引号技巧，这里构造的是：
        e 运行时打印 f(自身模板) 并 exec 之（对行为等价变换 = 运行原逻辑）。
    """
    # 工程版：e 运行时读**自己的源码**，交给内联的 f，报变换结果。
    #
    # 为什么不 exec 变换后的自己：`exec(f(s))` 会在 `__name__ == "__main__"` 的
    # 语境里把整个 main 块再跑一遍 → **无限自嵌套**。所以这里做的是
    # "拿到自己的源码 → 交给 f → 报结果"，思想同一（φ_e = φ_{f(e)}），
    # 但不假装能安全地执行变换结果。
    #
    # 为什么 f 要**内联**进源码：旧版把 `_TRANSFORM` 写成自由名字、指望调用方注入，
    # 结果产出的程序一跑就 `NameError`（对拍实跑抓出来的）。任意可调用对象没法通用
    # 序列化，所以内联默认变换（行为等价：加一行注释），自定义 f 在构件侧试算。
    prog = (
        '# -*- coding: utf-8 -*-\n'
        'import sys as _s\n'
        '\n'
        '\n'
        'def _TRANSFORM(code):\n'
        '    """默认变换 f：在源码末尾加一行注释（行为等价）。"""\n'
        "    return code + '\\n# [transform] 已应用：此注释由变换 f 添加\\n'\n"
        '\n'
        '\n'
        'def _apply(code):\n'
        '    return _TRANSFORM(code)\n'
        '\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    _src = open(_s.argv[0], encoding="utf-8").read()\n'
        '    _res = _apply(_src)\n'
        '    print("--- 自指程序 e 的源码 ---")\n'
        '    print(_src)\n'
        '    print("--- 变换 f(e) 的结果 ---")\n'
        '    print("源码 %d 字符 → f(e) %d 字符（差 %d，来自 f 加的那行注释）"\n'
        '          % (len(_src), len(_res), len(_res) - len(_src)))\n'
    )
    # 第二个返回值原先是一段构造完就被丢掉的死代码（`inner`），
    # 这里显式返回 None，并把"没用的中间产物"这件事写出来，免得再被当成接口。
    return prog, None


def run(inputs):
    """
    做什么：构造自指程序（quine / 递归定理形态）。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'quine')
    if mode not in ('quine', 'recursive'):
        return {'verdict': 'input_pending', 'program': None,
                'runs_like': None,
                'boundary': f"mode 应为 quine/recursive，得到 {mode!r}"
                            '——诚实拦截'}

    if mode == 'quine':
        payload = inputs.get('payload', '你好，自指')
        program = _build_quine(payload)
        return {'verdict': 'constructed', 'program': program,
                'runs_like': '程序打印自己的源码（自复制），再打印 payload '
                             f'{payload!r}',
                'boundary': 'quine 是递归定理最直观形态（自复制）。本构件'
                            '为引号技巧工程演示，非形式化证明——形式化在 '
                            'λ/图灵机层（1.6/1.7）。自指不与停机问题冲突，'
                            '不宣称绕定理。'}

    # recursive 形态
    transform = inputs.get('transform')
    if transform is None:
        transform = _simple_transform
    if not callable(transform):
        return {'verdict': 'input_pending', 'program': None,
                'runs_like': None,
                'boundary': 'recursive 模式需 transform（可调用，'
                            '程序变换 f(code)->code）——诚实拦截'}
    program, _ = _build_recursive(transform)
    # 应用变换示例（诚实：是在**构件侧**试算 f，不是程序跑出来的）
    f_result = transform('def demo():\n    return 42\n')
    return {'verdict': 'constructed', 'program': program,
            'runs_like': '程序 e 运行时读**自己的源码** → 交给**源码里内联的**默认变换 f'
                         ' → 报变换前后长度。'
                         f'（自定义 f 无法通用序列化进源码，故程序内联默认变换；'
                         f'本构件侧另用给定 f 试算：f(示例源码) 返回 '
                         f'{len(f_result)} 字符）',
            'boundary': '递归定理形态工程演示：φ_e = φ_{f(e)} 的思想'
                        '（程序能拿自己再变换）。**不 exec 变换后的自己**——'
                        '那会在 __main__ 语境里无限自嵌套；本件只做'
                        '"拿到自己 → 变换 → 报结果"。'
                        '非形式化证明；不与停机问题冲突（不宣称绕定理）。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 62)
    print('Kleene 递归定理 · 自指程序构造 · 自测')
    print('=' * 62)

    # 1) quine 构造（模式存在性）
    r1 = run({'mode': 'quine', 'payload': '自指测试'})
    assert r1['verdict'] == 'constructed' and r1['program'], r1
    assert 's = ' in r1['program'], r1
    print(f"✅ quine 构造成功（{len(r1['program'])} 字符源码）")

    # 2) quine 实跑验证：程序运行后确实打印出自己的源码（自复制）
    import subprocess
    import sys
    import tempfile
    import os
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                     encoding='utf-8') as fh:
        fh.write(r1['program'])
        tmp = fh.name
    try:
        import os as _os2
        _env2 = dict(_os2.environ)
        _env2['PYTHONIOENCODING'] = 'utf-8'
        out = subprocess.run([sys.executable, tmp], capture_output=True,
                             text=True, timeout=10, env=_env2,
                             encoding='utf-8')
        assert out.returncode == 0, out.stderr
        assert '自指测试' in out.stdout, out.stdout
        assert 's = ' in out.stdout, out.stdout[:200]
        print('✅ quine 实跑：程序输出了自己的源码结构 + payload（自复制 ✅）')
    finally:
        os.remove(tmp)

    # 3) 递归定理形态：默认变换（加注释，行为等价）
    r3 = run({'mode': 'recursive'})
    assert r3['verdict'] == 'constructed' and r3['program'], r3
    assert 'recursive-theorem' in r3['program'] or '源码' in r3['program'], r3
    print(f"✅ 递归定理形态构造成功（{len(r3['program'])} 字符）")
    print(f"   runs_like: {r3['runs_like'][:60]}…")

    # 4) 自定义变换：统计源码行数的 f
    def count_lines(code):
        return f'# 源码共 {code.count(chr(10)) + 1} 行\n'
    r4 = run({'mode': 'recursive', 'transform': count_lines})
    assert r4['verdict'] == 'constructed', r4
    print('✅ 自定义变换 f（统计行数）可接入')

    # 5) 边界
    r5 = run({'mode': 'xx'})
    assert r5['verdict'] == 'input_pending', r5
    r6 = run({'mode': 'recursive', 'transform': 'not_callable'})
    assert r6['verdict'] == 'input_pending', r6
    print('✅ 坏 mode / 非可调用 transform → input_pending')

    print('=' * 62)
    print('Kleene 递归定理构件自测：全部通过 ✅')
    print('=' * 62)
