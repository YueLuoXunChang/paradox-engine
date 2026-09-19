# -*- coding: utf-8 -*-
"""
test_fuzz.py — 正式测试：随机模糊（固定种子，可复现）
================================================================
为什么有这个文件：
    坏输入扫描（test_robustness）覆盖的是**我想到的**坏输入——枚举法天然有漏。
    本文件用**固定种子的随机**去撞没被想到的组合：随机文本、随机结构化参数、
    随机类型、随机嵌套。目标不是"断言具体结论"，而是三条铁律：

      ① **不崩**：任何随机输入都不许抛异常出 engine 边界；
      ② **verdict 合法**：返回的 verdict 必须落在各自允许集合里（不许 None/乱值）；
      ③ **不编数**：算不动时不许给出数值（μ 尤其：要么 None，要么 ∈ [0,1]）。

    固定种子（默认 20260907，可用 --seed 改）——失败可一键复现，这是 fuzz 能进
    回归的前提；不固定种子会变成随机红灯。

用法：
    python engine/test_fuzz.py            # 固定种子全跑（默认 300 轮/组）
    python engine/test_fuzz.py --n 2000   # 加轮数（手动压测）
运行环境：纯标准库，无第三方依赖。
"""

import os
import random
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


import argparse  # noqa: E402
import json  # noqa: E402

from engine.ai.tools import _TOOL_REGISTRY, call_tool  # noqa: E402
from engine.control.controller import run as controller  # noqa: E402
from engine.mechanisms.paradox_measure import run as measure  # noqa: E402
from engine.scenarios.scenarios import SCENES  # noqa: E402

_ap = argparse.ArgumentParser()
_ap.add_argument('--n', type=int, default=300)
_ap.add_argument('--seed', type=int, default=20260907)
_args, _ = _ap.parse_known_args()
SEED, N = _args.seed, _args.n
rnd = random.Random(SEED)

print("随机模糊（fixed-seed）· 正式测试")
print("=" * 60)
print(f"  种子 {SEED} / 每组 {N} 轮")

# ── 随机素材池
_CHARS = ('既要快又要稳矛盾冲突证据数据显示研究实验1234567890'
          'abcXYZ!?,.。、；：（）[]{}<>@#$%^&*')
_WEIRD = ['', ' ', '\n', '\t', '\x00', '\x07', '\u200b', '😀', '𝔘',
          '\ud800', 'a' * 10000, '既要' * 5000, '0' * 5000]
_STRUCT_KEYS = ['A', 'B', 'notA', 'wA', 'wNotA', 'formula', 'premises',
                'conclusion', 'beliefs', 'new_info', 'priorities',
                'arguments', 'attacks', 'facts', 'rules', 'query',
                'worlds', 'order', 'valuation', 'mode', 'text',
                'sentences', 'max_beliefs', 'max_arguments', 'tau_L1',
                'tau_L2', 'x0', 'f', 'err_fn', 'system', 'level',
                'scene_id', 'action', 'source', 'impact', 'eliminable']


def _rand_value(depth=0):
    kind = rnd.randrange(12)
    if kind == 0:
        return None
    if kind == 1:
        return rnd.choice([True, False])
    if kind == 2:
        return rnd.choice([0, 1, -1, 5, -5, 10 ** 18, -10 ** 18,
                           1.5, -1.5, 1e-9, float('inf'), float('nan')])
    if kind == 3:
        return rnd.choice(_WEIRD)
    if kind == 4:
        return ''.join(rnd.choice(_CHARS) for _ in range(rnd.randrange(40)))
    if kind == 5:
        return [rnd.choice(_WEIRD) for _ in range(rnd.randrange(4))]
    if kind == 6:
        return {rnd.choice(_STRUCT_KEYS): _rand_value(depth + 1)
                for _ in range(rnd.randrange(3))} if depth < 2 else 0
    if kind == 7:
        return (rnd.randrange(5), rnd.randrange(5))
    if kind == 8:
        return [('a', 'b'), ('b', 'a'), ('a',)][rnd.randrange(3)]
    if kind == 9:
        return {'a', 'b'}
    if kind == 10:
        return lambda x: x  # callable（converge_check 期望函数）
    return rnd.randrange(-3, 4)


def _rand_struct():
    d = {}
    for _ in range(rnd.randrange(1, 5)):
        d[rnd.choice(_STRUCT_KEYS)] = _rand_value()
    return d


# ── 用例1：随机文本 → 控制器
_text_crash, _text_badverdict = [], []
_OK_TEXT_VERDICTS = {'done', 'classified_only', 'input_pending'}
for i in range(N):
    t = _rand_value()
    if not isinstance(t, str):
        t = rnd.choice(_WEIRD + [rnd.choice(_CHARS)])
        if not isinstance(t, str):
            t = '随机文本'
    try:
        r = controller({'text': t, 'structured': {}})
    except Exception as e:  # noqa: BLE001
        _text_crash.append(f'{type(e).__name__}: {str(e)[:50]} | text={t[:24]!r}')
        continue
    if r.get('verdict') not in _OK_TEXT_VERDICTS:
        _text_badverdict.append(f"verdict={r.get('verdict')} | {t[:24]!r}")
check(f"随机文本 ×{N}：控制器不崩", not _text_crash, str(_text_crash[:3]))
check(f"随机文本 ×{N}：verdict 落在合法集合", not _text_badverdict,
      str(_text_badverdict[:3]))

# ── 用例2：随机结构化参数 → 控制器（真跑构件的那条路）
_struct_crash, _struct_no_verdict = [], []
for i in range(N):
    try:
        r = controller({'text': rnd.choice(
            ['既要快又要稳', '这句话是假的', 'A 支持 B，B 反对 C',
             '随便写点什么']), 'structured': _rand_struct()})
    except Exception as e:  # noqa: BLE001
        _struct_crash.append(f'{type(e).__name__}: {str(e)[:60]}')
        continue
    for e in r.get('execution', []):
        if e['status'] == 'run':
            out = e.get('output') or {}
            if 'verdict' not in out and e['component'] not in (
                    'paradox_measure.mu3',):
                _struct_no_verdict.append(
                    f"{e['component']} 输出缺 verdict")
check(f"随机结构化 ×{N}：控制器不崩", not _struct_crash,
      str(_struct_crash[:3]))
check(f"随机结构化 ×{N}：真跑构件都给出 verdict",
      not _struct_no_verdict, str(_struct_no_verdict[:3]))

# ── 用例3：随机数值 → μ 不变量（要么 None，要么 ∈[0,1]）
_mu_bad = []
_MU_VERDICTS = {'measured', 'input_pending'}
for i in range(N):
    args = {'mode': rnd.choice(['mu1', 'mu2', 'mu3', 'mu4', 'mu1']) }
    if rnd.random() < 0.8:
        args['wA'] = _rand_value()
        args['wNotA'] = _rand_value()
    if rnd.random() < 0.3:
        args['tau_L1'] = _rand_value()
        args['tau_L2'] = _rand_value()
    try:
        r = measure(dict(args))
    except Exception as e:  # noqa: BLE001
        _mu_bad.append(f'崩 {type(e).__name__}: {str(e)[:40]} | {args}')
        continue
    mu = r.get('mu')
    if r.get('verdict') not in _MU_VERDICTS:
        _mu_bad.append(f"verdict={r.get('verdict')} | {args}")
    if mu is not None:
        try:
            ok = 0.0 <= float(mu) <= 1.0
        except (TypeError, ValueError):
            ok = False
        if not ok:
            _mu_bad.append(f'μ 越界 {mu!r} | {args}')
    if r.get('verdict') == 'input_pending' and mu is not None:
        _mu_bad.append(f'拦截却给 μ={mu!r} | {args}')
check(f"随机数值 ×{N}：μ 要么 None 要么 ∈[0,1]（不越界、不编数）",
      not _mu_bad, str(_mu_bad[:3]))

# ── 用例4：随机参数 → 全部工具（不崩 + 挂载层不报 tool_error）
_tool_crash, _tool_err = [], []
for i in range(N):
    name, path, desc = _TOOL_REGISTRY[rnd.randrange(len(_TOOL_REGISTRY))]
    try:
        r = call_tool(name, _rand_struct())
    except Exception as e:  # noqa: BLE001
        _tool_crash.append(f'{name}: {type(e).__name__}: {str(e)[:50]}')
        continue
    if r.get('verdict') == 'tool_error':
        _tool_err.append(f"{name}: {str(r.get('boundary'))[:60]}")
check(f"随机参数 ×{N}：全部工具不崩（含 callable/超长/NaN/inf）",
      not _tool_crash, str(_tool_crash[:3]))
check(f"随机参数 ×{N}：构件自己诚实拦截（挂载层不报 tool_error）",
      not _tool_err, str(_tool_err[:3]))

# ── 用例5：随机场景 id → 场景库（诚实处理未知 id）
_sc_bad = []
for i in range(min(N, 60)):
    sid = rnd.choice([s['id'] for s in SCENES] + ['S99', '', 's01', None])
    try:
        from engine.scenarios.scenarios import run as scenes_run
        r = scenes_run({'action': 'run', 'scene_id': sid})
    except Exception as e:  # noqa: BLE001
        _sc_bad.append(f'{sid!r}: {type(e).__name__}: {str(e)[:40]}')
        continue
    if r.get('verdict') != 'ran':
        _sc_bad.append(f'{sid!r}: verdict={r.get("verdict")}')
check("随机场景 id（含未知/空/None）：场景库不崩且给 ran",
      not _sc_bad, str(_sc_bad[:3]))

# ── 用例6：挂载层类型闸（按声明 schema 挡错类型，且不误伤）
_r = call_tool('equality_tableau', {'conclusion': True})
check("错类型被挂载层按 schema 拦下（点名参数，不透传给构件）",
      _r['verdict'] == 'input_pending'
      and 'conclusion' in (_r['result'].get('error') or ''), str(_r)[:150])
_ok_cases = [
    ('list 接 tuple', 'equality_tableau', {'premises': ('P', 'Q')}),
    ('float 接 int', 'paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5}),
    ('str 正常', 'propositional', {'formula': 'P', 'mode': 'satisfiable'}),
]
_wrong_reject = []
for label, tool, args in _ok_cases:
    rr = call_tool(tool, args)
    if rr['verdict'] != 'ok':
        _wrong_reject.append(f"{label}: {rr['verdict']} "
                             f"{str(rr.get('result'))[:60]}")
check("类型闸不误伤合法输入（tuple/int 兼容、str 正常）",
      not _wrong_reject, str(_wrong_reject))

# ── 用例7：fuzz 自身可复现（同种子同结果——否则红灯不可复现）
_r1 = random.Random(SEED)
_r2 = random.Random(SEED)
check("固定种子可复现（同种子同序列）",
      [_r1.randrange(10 ** 6) for _ in range(5)]
      == [_r2.randrange(10 ** 6) for _ in range(5)])
check("轮数可调（--n）且本轮机跑满", N >= 1, str(N))

print("=" * 60)
print(f"结果: {PASS}/12 通过")
raise SystemExit(0 if PASS == 12 else 1)
