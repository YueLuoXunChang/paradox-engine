# -*- coding: utf-8 -*-
"""test_ai_scenarios.py — AI 挂载层两个端到端场景的正式测试（③ 验证轴 · 第九批之二）

这一件此前**零测试**（登记表"无测试引用"）。它本身是**演示脚本**，不是判定件，
所以判据不是"算得对不对"，而是——

    · 两个场景**真的跑出结构化诊断**（不是打印两句就算）；
    · 返回结构符合 PORTS 声明（s1 是 controller 结果；s2 是 (wall_pipeline, dung) 二元组）；
    · **每个返回都带 boundary**（本层承诺"原样透传、不覆盖"）；
    · `main()` 端到端不抛异常（演示脚本的最低要求）。

场景里的输入是**写死的示例文本**（PORTS 里已声明），所以这里不复现业务判断，只验"接线 + 契约"。

运行：python engine/ai/test_ai_scenarios.py
"""
import contextlib
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.ai import ai_scenarios as AS   # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=''):
    global PASS
    if cond:
        PASS += 1
        print('✅ %s' % label)
    else:
        print('❌ %s  %s' % (label, detail))


def _silent(fn):
    """跑一次并吞掉打印（场景是给人看的演示，测试只看返回结构）。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn()
    return out, buf.getvalue()


print('=' * 70)
print('一、场景 1（论证矛盾检查）：结构化诊断 + boundary 透传')
_s1, _out1 = _silent(AS.scenario1_argument_conflict)
check('场景 1 返回 dict（PORTS 声明的 controller 结果）', isinstance(_s1, dict),
      type(_s1).__name__)
check('带判类/执行/报告/五查四样（结构化诊断，不是一句话）',
      all(k in _s1 for k in ('classification', 'execution', 'report',
                             'output_check')),
      sorted(_s1)[:8])
check('判类给出了类型与路由（T 号 + route_id）',
      bool(_s1['classification'].get('main_type'))
      and bool(_s1['classification'].get('route', {}).get('route_id')),
      _s1['classification'].get('main_type'))
check('★返回带 boundary（本层承诺"原样透传、不覆盖"——自己再断言一次）',
      'boundary' in _s1)
check('执行列表里有 status=run 的构件（真跑过，不是空表）',
      any(e.get('status') == 'run' for e in _s1['execution']), _s1['execution'])
check('场景 1 的打印里给了人读的报告（含【类型】或【边界】）',
      ('【类型】' in _out1) or ('【边界】' in _out1), _out1[:120])

print()
print('=' * 70)
print('二、场景 2（学科建模）：判类 → 撞墙 → Dung 多工具链')
_s2, _out2 = _silent(AS.scenario2_discipline_modeling)
check('场景 2 返回二元组 (wall_pipeline 结果, dung 结果)',
      isinstance(_s2, tuple) and len(_s2) == 2
      and all(isinstance(x, dict) for x in _s2), type(_s2).__name__)
_wp, _dg = _s2
check('撞墙件的返回带五选一判词与诊断（verdict/diagnosis）',
      bool(_wp.get('verdict')) and bool(_wp.get('diagnosis')), list(_wp)[:6])
check('Dung 件的返回带 grounded/preferred（立场排序，不是空壳）',
      'grounded' in _dg and 'preferred' in _dg, list(_dg)[:6])
check('★两个返回都带 boundary',
      'boundary' in _wp and 'boundary' in _dg)
check('场景 2 的打印里给了判类与五选一诊断', '判类' in _out2 or '五选一' in _out2,
      _out2[:120])

print()
print('=' * 70)
print('三、端到端：main() 不抛异常，且两场景都被调到')
_main_ok, _out3 = True, ''
try:
    _ret, _out3 = _silent(AS.main)      # main() 返回 None（演示脚本），不能当成功标志
except Exception as _exc:                                   # noqa: BLE001
    _main_ok = False
    _out3 = '%s: %s' % (type(_exc).__name__, _exc)
check('main() 端到端跑通（演示脚本的最低要求）', _main_ok, str(_out3)[:120])
check('main() 的输出提到两个场景与"验收"（说明都跑到了）',
      ('场景 1' in str(_out3)) and ('场景 2' in str(_out3)), str(_out3)[:120])

print()
print('=' * 70)
print(f'结果: {PASS}/13 通过')
raise SystemExit(0 if PASS == 13 else 1)
