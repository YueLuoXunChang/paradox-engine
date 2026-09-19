# -*- coding: utf-8 -*-
"""
test_robustness.py — 正式测试：输入健壮性与诚实边界（坏输入不许崩、不许编数）
================================================================================
为什么有这个文件：
    构件的"诚实边界"写在每个 docstring 里，但**没被系统测过**。本批按 29 个工具
    × 4 类坏输入做扫描，当场抓到真问题：

      · μ 测度（旗舰构件）：`wA=5, wNotA=-5` 算出 **μ = -9999999999.0**——
        违反自己声明的 μ∈[0,1]；`wA="五"` 直接 TypeError 崩；
      · 悖论注解：`paradox=5` / `paradox=None` / `source=123` 三种崩法
        （AttributeError / KeyError）；
      · Dung 论证框架：`arguments=5`（len 崩）、`attacks="xy"` / `attacks=[1]`
        （unpack 崩）。

    修法都是同一件事：**非法输入拦下并说清**（verdict='input_pending' + 中文
    说明），绝不硬算、绝不返回越界值。本文件把这条纪律固化成不变式。

测什么：
    ① 坏输入扫描：29 工具 × {空 args, 错类型, 负值, None} —— 不抛异常；挂载层
       verdict 必须 ok（构件自己诚实拦截）；构件输出必须带 verdict 字段；
    ② μ 不变量：任何输入下 μ 要么是 None（拦截/未算），要么 ∈ [0,1]——
       绝不给越界数值；非法权重/未知 mode/缺 tau 都要拦；
    ③ 控制器层：超长文本 / 纯 emoji / 纯符号 / 控制字符 / 中英混排 / 单字 /
       空串 —— 不崩，且空串诚实报 input_pending；
    ④ 语义非法的"看着像结果"的值：负数权重、布尔权重不得被接受。
运行：python engine/test_robustness.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


from engine.ai.tools import _TOOL_REGISTRY, call_tool  # noqa: E402
from engine.control.controller import run as controller  # noqa: E402
from engine.mechanisms.paradox_measure import run as measure  # noqa: E402

print("输入健壮性与诚实边界 · 正式测试")
print("=" * 60)

# ── 用例1：坏输入扫描（29 工具 × 4 类）
_BAD = [
    ('空 args', {}),
    ('错类型', {'mode': 123, 'text': 42, 'formula': [], 'premises': 'x',
                'beliefs': 5, 'worlds': 'w', 'wA': '五', 'wNotA': '五',
                'max_beliefs': '十', 'max_arguments': -3, 'arguments': 'abc',
                'attacks': 1, 'facts': 5, 'rules': {}, 'query': [],
                'level': 7, 'system': 8, 'sentence': 9}),
    ('负值', {'wA': -5, 'wNotA': -5, 'x0': -1, 'max_beliefs': -1,
              'max_arguments': -1, 'tau_L1': -1, 'tau_L2': -1}),
    ('None 值', {'wA': None, 'wNotA': None, 'formula': None, 'text': None,
                 'premises': None, 'conclusion': None}),
]
# 诚实拦截可能发生在两处（都合格）：
#   ① 挂载层按声明 schema 先挡（verdict='input_pending'，result 里带 error）；
#   ② 透传给构件，由构件自己拦（verdict='ok'，构件输出 verdict='input_pending'）。
# 不合格的只有两种：抛异常，或挂载层报 tool_error（= 构件崩了被兜住）。
_crash, _tool_error, _dishonest = [], [], []
for name, path, desc in _TOOL_REGISTRY:
    for label, args in _BAD:
        try:
            r = call_tool(name, args)
        except Exception as e:  # noqa: BLE001——崩了就是问题，记下来
            _crash.append(f'{name}[{label}] {type(e).__name__}: {str(e)[:40]}')
            continue
        v = r.get('verdict')
        if v == 'tool_error':
            _tool_error.append(f"{name}[{label}] → {str(r.get('error'))[:50]}")
            continue
        if v == 'input_pending':          # 挂载层拦下：必须给说明
            out = r.get('result') or {}
            if not out.get('error'):
                _dishonest.append(f"{name}[{label}] 拦截但无说明")
            continue
        if v != 'ok':
            _dishonest.append(f"{name}[{label}] 挂载层 verdict={v}")
            continue
        out = r.get('result') or {}
        if 'verdict' not in out:
            _dishonest.append(f"{name}[{label}] 构件输出缺 verdict 键="
                              f"{sorted(out)[:3]}")
check(f"坏输入扫描：{len(_TOOL_REGISTRY)} 工具 ×4 类不抛异常", not _crash,
      str(_crash[:4]))
check("坏输入扫描：没有构件崩到挂载层（无 tool_error）", not _tool_error,
      str(_tool_error[:4]))
check("坏输入扫描：拦截都给说明 + 输出都带 verdict（接口统一）",
      not _dishonest, str(_dishonest[:4]))

# ── 用例2：μ 不变量（旗舰构件——曾算出负值/崩）
_cases = [
    ('正常', {'mode': 'mu1', 'wA': 5, 'wNotA': 5}, 'measured', 1.0),
    ('零证据', {'mode': 'mu1', 'wA': 0, 'wNotA': 0}, 'measured', None),
    ('单边', {'mode': 'mu1', 'wA': 0, 'wNotA': 9}, 'measured', 0.0),
    ('超大', {'mode': 'mu1', 'wA': 10 ** 18, 'wNotA': 1}, 'measured', None),
    ('负数', {'mode': 'mu1', 'wA': 5, 'wNotA': -5}, 'input_pending', None),
    ('全负', {'mode': 'mu1', 'wA': -5, 'wNotA': -5}, 'input_pending', None),
    ('字符串', {'mode': 'mu1', 'wA': '五', 'wNotA': '五'}, 'input_pending', None),
    ('None', {'mode': 'mu1', 'wA': None, 'wNotA': None}, 'input_pending', None),
    ('布尔', {'mode': 'mu1', 'wA': True, 'wNotA': 1}, 'input_pending', None),
    ('坏 mode', {'mode': 'xx'}, 'input_pending', None),
    ('mu3 缺 tau', {'mode': 'mu3'}, 'input_pending', None),
    ('mu3 负 tau', {'mode': 'mu3', 'tau_L1': -1, 'tau_L2': .5},
     'input_pending', None),
    ('mu2', {'mode': 'mu2'}, 'measured', 1.0),
]
_out_of_range = []
_wrong_verdict = []
_for_fake = []
for label, args, want_v, want_mu in _cases:
    r = measure(dict(args))
    mu = r.get('mu')
    if r.get('verdict') != want_v:
        _wrong_verdict.append(f'{label}: {r.get("verdict")} ≠ {want_v}')
    if mu is not None and not (0.0 <= float(mu) <= 1.0):
        _out_of_range.append(f'{label}: μ={mu}')
    if want_v != 'measured' and mu is not None:
        _for_fake.append(f'{label}: 拦截却给了 μ={mu}')
    if want_mu is not None and mu is not None and abs(float(mu) - want_mu) > 1e-9:
        _wrong_verdict.append(f'{label}: μ={mu} ≠ {want_mu}')
check("μ 各分支判定与声明一致（合法→measured，非法→input_pending）",
      not _wrong_verdict, str(_wrong_verdict))
check("μ 永远落在 [0,1]（越界值一律不返回）", not _out_of_range,
      str(_out_of_range))
check("拦截时绝不给 μ（不编造数值）", not _for_fake, str(_for_fake))
_r = measure({'mode': 'mu1', 'wA': 5, 'wNotA': -5})
check("负数权重被点名拒绝（错误信息含参数名与原因）",
      'wNotA' in (_r.get('error') or '') and '负' in (_r.get('error') or ''),
      str(_r.get('error'))[:80])
_r = measure({'mode': 'mu1', 'wA': '五', 'wNotA': '五'})
check("非数值被点名拒绝（含类型）",
      'str' in (_r.get('error') or '') or '不是数值' in (_r.get('error') or ''),
      str(_r.get('error'))[:80])

# ── 用例3：控制器层坏文本（超长/emoji/控制字符/中英混排）
_texts = [
    ('空串', '', 'input_pending'),
    ('纯空白', '   \n\t  ', None),
    ('超长 5 万字', '既要快又要稳' * 5000, None),
    ('纯 emoji', '😀😀😀🎉', None),
    ('纯符号', '!!!???###@@@', None),
    ('控制字符', 'abc\x00\x07def', None),
    ('中英混排', 'This is a test 既要快又要稳 OK?', None),
    ('单字', '?', None),
]
_txt_bad = []
for label, text, want in _texts:
    try:
        r = controller({'text': text, 'structured': {}})
    except Exception as e:  # noqa: BLE001
        _txt_bad.append(f'{label}: 崩 {type(e).__name__}: {str(e)[:40]}')
        continue
    if want and r.get('verdict') != want:
        _txt_bad.append(f'{label}: verdict={r.get("verdict")} ≠ {want}')
check("控制器对 8 类坏文本不崩且判定符合预期", not _txt_bad, str(_txt_bad))
check("空文本诚实报 input_pending（不硬分类）",
      controller({'text': '', 'structured': {}})['verdict'] == 'input_pending')
check("非字符串 text 诚实报 input_pending",
      controller({'text': 123, 'structured': {}})['verdict'] == 'input_pending')

# ── 用例4：结构化参数语义非法
_r = controller({'text': '既要快又要稳',
                 'structured': {'wA': -5, 'wNotA': -5}})
_exec = {e['component']: e for e in _r.get('execution', [])}
_mu_run = _exec.get('paradox_measure.mu1', {})
check("控制器里负数权重也被构件拦下（不静默算 μ）",
      (_mu_run.get('output') or {}).get('verdict') in ('input_pending', None),
      str(_mu_run)[:120])
check("控制器返回结构完整（含五查与报告）",
      all(k in _r for k in ('classification', 'execution', 'output_check',
                            'report')), sorted(_r))

print("=" * 60)
print(f"结果: {PASS}/13 通过")
raise SystemExit(0 if PASS == 13 else 1)
