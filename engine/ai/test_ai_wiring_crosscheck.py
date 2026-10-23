# -*- coding: utf-8 -*-
"""test_ai_wiring_crosscheck.py — 挂载层两条**接线级**验证（③ 验证轴 · 第十二批）

这一批补两件：
    `tools`（工具注册表）与 `freeze_tool_schema`（契约快照）。两件都不是"判定件"，
    所以判据只能是**接线**与**机制自身能不能抓到漂移**——这正是 ③ 轴要的
    "变异接受"：**故意把东西改坏，看守护它的那条判据抓不抓**。

两条：
    ① **清单 ↔ 命令行**（**互验**）：注册表里的**每一个**工具名，都能从命令行 `--call` 调到
       —— 41 条**逐条核**（`--tools` 列得出来 ≠ `--call` 调得动；
       "数目对而清单缺最骗人"的反面）。
    ② **快照变异接受**：把落盘快照**故意改坏**（删掉一条工具），
       `check()` 必须**逐条核**出差异并点名；随后**逐字节还原**（sha256 核对）。
       没有这条，"漂移检查"就只是"它自己说它一致"。

运行：python engine/ai/test_ai_wiring_crosscheck.py
"""
import contextlib
import hashlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engine.ai import freeze_tool_schema as F   # noqa: E402
from engine.ai import tools as T                # noqa: E402

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


def _run_cli(argv):
    """走**命令行入口**（不是 call_tool 内部函数），返回 (rc, out)。"""
    from engine import cli
    buf = io.StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        rc = cli.main(argv)
    except SystemExit as exc:                     # argparse 用法错
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout = old
    return rc, buf.getvalue()


print('=' * 70)
print('一、清单 ↔ 命令行：每个注册工具都能从 `--call` 调到')
_names = [n for n, _m, _d in T._TOOL_REGISTRY]
_bad_call, _bad_out = [], []
for _n in _names:
    _rc, _out = _run_cli(['--call', _n, '--args', '{}'])
    if _rc not in (0, 1):
        _bad_call.append((_n, _rc))
    elif not _out.strip():
        _bad_out.append(_n)
check('41 个注册工具**逐个**从命令行 --call 调用（无用法错/无异常退出）',
      _bad_call == [], _bad_call[:3])
check('每个工具的 --call 都有输出（不静默）', _bad_out == [], _bad_out[:3])
check('`--tools` 列出的条数 == 注册表条数（清单不短）',
      len(T.tools()) == len(T._TOOL_REGISTRY) == len(_names))

print()
print('=' * 70)
print('二、注册表条目 ↔ 构件模块：名字对得上、模块真的在')
import importlib
_missing_mod, _no_ports = [], []
for _n, _mod, _desc in T._TOOL_REGISTRY:
    try:
        _m = importlib.import_module('engine.' + _mod)
    except Exception as _exc:                     # noqa: BLE001
        _missing_mod.append((_n, _mod, type(_exc).__name__))
        continue
    if not getattr(_m, 'PORTS', None):
        _no_ports.append(_n)
check('41 条注册项指向的构件模块**都 import 得动**', _missing_mod == [],
      _missing_mod[:2])
check('这些模块都声明了 PORTS（注册表 ↔ 契约对得上）', _no_ports == [],
      _no_ports[:3])

print()
print('=' * 70)
print('三、★快照变异接受：故意改坏，看 check() 抓不抓')
_sha = hashlib.sha256(open(F._SNAPSHOT, 'rb').read()).hexdigest()
_orig = open(F._SNAPSHOT, 'rb').read()
_ok0, _ch0 = F.check()
check('先确认当前快照是一致的（不然下面的变异没意义）',
      _ok0 is True and not _ch0, (_ok0, _ch0))
try:
    # 变异：从快照的 contract 里**删掉一条工具**（结构变化最不易被"格式宽容"吃掉）
    _data = json.loads(_orig.decode('utf-8'))
    _contract = _data['contract']
    assert isinstance(_contract, dict) and _contract, '快照 contract 不是非空 dict'
    _victim = sorted(_contract)[0]
    del _contract[_victim]
    open(F._SNAPSHOT, 'w', encoding='utf-8', newline='').write(
        json.dumps(_data, ensure_ascii=False, indent=2))
    _ok1, _ch1 = F.check()
    check('从快照删掉一条工具（%s）→ check() 报不一致并点名' % _victim,
          _ok1 is False and bool(_ch1) and _victim in str(_ch1),
          (_ok1, str(_ch1)[:120]))
finally:
    open(F._SNAPSHOT, 'wb').write(_orig)
_sha2 = hashlib.sha256(open(F._SNAPSHOT, 'rb').read()).hexdigest()
check('变异后**逐字节还原**（sha256 一致）', _sha2 == _sha, (_sha[:12], _sha2[:12]))
_ok2, _ch2 = F.check()
check('还原后 check() 又回到一致', _ok2 is True and not _ch2, (_ok2, _ch2))

print()
print('=' * 70)
print('四、快照 ↔ 活注册表：contract 的条目数对得上')
_c = F.contract(T.tools())
check('contract(活工具清单) 产出 dict，且条目数 == 注册表条数',
      isinstance(_c, dict)
      and (len(_c) == len(_names)
           or len(_c.get('contract', {}) or {}) == len(_names)),
      (type(_c).__name__, len(_c) if isinstance(_c, dict) else None))

print()
print('=' * 70)
print(f'结果: {PASS}/10 通过')
raise SystemExit(0 if PASS == 10 else 1)
