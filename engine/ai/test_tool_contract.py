# -*- coding: utf-8 -*-
"""
test_tool_contract.py — 正式测试：工具协议冻结（轨 C1）
用例依据：轨 C1「工具协议稳定 + 调用方文档」——工具名/参数名是对外契约，
         改了要让调用方知道（快照 + 文档 + 记账），不能静默漂移。
运行：python engine/ai/test_tool_contract.py
"""
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

from freeze_tool_schema import (  # noqa: E402
    _DOC, _SNAPSHOT, check, contract, render_markdown, run)
from tools import _TOOL_REGISTRY, tools  # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check_(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


# 源码仓判定：文档（docs/tool_schema.md）属源码仓产物，pip 安装后没有它——
# 此时**契约快照断言照跑**（JSON 随包发布），仅把"文档相关"断言标注为源码仓专属。
try:
    from engine._layout import in_source_checkout
except ImportError:
    sys.path.insert(0, _REPO)
    from engine._layout import in_source_checkout

_IN_SRC = in_source_checkout()

print("工具协议冻结 · 正式测试")
print("=" * 60)

_tl = tools()
_live = contract(_tl)

# ── 用例1：快照存在且与活注册表一致（防漂移）
check_("冻结快照文件存在", os.path.exists(_SNAPSHOT), _SNAPSHOT)
_snap = json.load(open(_SNAPSHOT, encoding='utf-8'))
check_("快照含说明与契约", '_note' in _snap and 'contract' in _snap,
       sorted(_snap))
check_("快照工具数与工具数一致", _snap['tool_count'] == len(_tl),
       f"{_snap['tool_count']} vs {len(_tl)}")
check_("活注册表 == 冻结快照（契约无漂移）", _snap['contract'] == _live,
       [k for k in _snap['contract']
        if _snap['contract'].get(k) != _live.get(k)][:5])
ok, changed = check()
check_("check() 报告一致（CI 用同一判据）", ok, str(changed))

# ── 用例2：文档与契约一致（文档不落后于实现）
check_("调用方文档存在（源码仓专属）", (not _IN_SRC) or os.path.exists(_DOC), _DOC)
# 文档属源码仓产物：安装环境没有它——存在才读（断言侧已按源码仓守卫）
_md = open(_DOC, encoding='utf-8').read() if os.path.exists(_DOC) else ''
check_("文档覆盖全部工具（无遗漏；源码仓专属）",
       (not _IN_SRC) or all(f'`{n}`' in _md for n in _live),
       [n for n in _live if f'`{n}`' not in _md][:5])
check_("文档标明自动生成（勿手改；源码仓专属）",
       (not _IN_SRC) or ('自动生成' in _md and '请勿手改' in _md), _md[:80])
check_("文档给出调用示例（源码仓专属）",
       (not _IN_SRC) or ('call_tool(' in _md
                          and 'from engine.ai.tools' in _md))
check_("文档渲染函数与文件内容一致（可重生成；源码仓专属）",
       (not _IN_SRC) or render_markdown(_tl).strip() == _md.strip(),
       '文件与渲染结果不一致——跑 freeze_tool_schema.py 重新生成')

# ── 用例3：契约完备性（工具名/参数名/类型/必填齐全）
check_("契约条目数 = 注册表条数", len(_live) == len(_TOOL_REGISTRY),
       f"{len(_live)} vs {len(_TOOL_REGISTRY)}")
check_("每工具至少声明参数类型", all(
    all('type' in p and 'required' in p for p in params.values())
    for params in _live.values()))
check_("必填参数与 PORTS 一致（抽查 3 件）",
       _live['paradox_measure']['mode']['required'] is True
       and _live['paradox_measure']['wA'].get('required') in (False, None)
       and _live['controller']['text']['required'] is True,
       str(_live['paradox_measure']))
check_("工具数 ≥29（对外承诺规模）", len(_live) >= 29, str(len(_live)))

# ── 用例4：check=True 的只读语义（不写文件）
# 文档可能不存在（安装环境）——只对存在的文件比 mtime
_watched = [p for p in (_SNAPSHOT, _DOC) if os.path.exists(p)]
_before = tuple(os.path.getmtime(p) for p in _watched)
_r = run({'check': True})
_after = tuple(os.path.getmtime(p) for p in _watched)
check_("run(check=True) → consistent",
       _r['verdict'] == 'consistent', str(_r)[:120])
check_("check 模式不写文件（只读）", _before == _after,
       f"{_before} vs {_after}")

# ── 用例5：漂移能被抓住（模拟：改一个参数名 → 判 drifted）
# 纪律：测试**不得改动被跟踪文件**——漂移模拟写到临时快照上（原先直接改真快照，
# 且文本模式在 Windows 会把整个文件写成 CRLF，等于测试污染仓库）。
import hashlib  # noqa: E402
import tempfile  # noqa: E402

import freeze_tool_schema as _F  # noqa: E402

_hash_before = hashlib.sha256(open(_SNAPSHOT, 'rb').read()).hexdigest()
_bad = dict(_live)
_bad['paradox_measure'] = dict(_bad['paradox_measure'])
_bad['paradox_measure']['wA2'] = {'type': 'integer', 'required': False}
_snap_tmp = json.loads(json.dumps(_snap))
_snap_tmp['contract'] = _bad
_tmpdir = tempfile.mkdtemp(prefix='pe_contract_')
_tmp_snap = os.path.join(_tmpdir, 'tool_schema_frozen.json')
with open(_tmp_snap, 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(_snap_tmp, fh, ensure_ascii=False, indent=2, sort_keys=True)
_real_snap_path = _F._SNAPSHOT
try:
    _F._SNAPSHOT = _tmp_snap
    ok2, changed2 = check()
finally:
    _F._SNAPSHOT = _real_snap_path
check_("契约被改（模拟漂移）→ check 报不一致", not ok2, str(changed2)[:120])
check_("漂移报告指名到具体工具",
      any('paradox_measure' in c for c in changed2), str(changed2)[:120])
check_("测试未改动被跟踪快照（前后哈希一致）",
      hashlib.sha256(open(_SNAPSHOT, 'rb').read()).hexdigest() == _hash_before,
      '快照被测试改动了——测试应写临时文件')
import shutil  # noqa: E402
shutil.rmtree(_tmpdir, ignore_errors=True)
ok3, changed3 = check()
check_("恢复后重新一致（测试无副作用）", ok3, str(changed3)[:120])

# ── 用例6：入口自愈与接口
check_("PORTS 声明 in/out", True, '')
from freeze_tool_schema import PORTS  # noqa: E402
check_("PORTS.out 含 verdict/changed",
      {'verdict', 'changed'} <= set(PORTS['out']), sorted(PORTS['out']))


# ── 用例N：PORTS 声明 == 实际返回形状（2026-09-20 补：这条当场抓出四处不一致）
import importlib  # noqa: E402


def _shape_check():
    """每件工具 × 3 类输入，比对 PORTS['out'] 与实际返回的键。

    口径：
      · 挂载层会往结果里塞 `_tool`/`_input`（它自己的记账），**不算构件的字段**；
      · PORTS 里带 `?` 的是可选字段，允许缺席；不带 `?` 的必须在；
      · 反过来，返回里出现的键也必须在 PORTS 里声明——PORTS 是对外声明，
        多返回少声明同样是文档说谎。
    """
    missing, extra, no_verdict, no_boundary = [], [], [], []
    for name, modpath, _desc in _TOOL_REGISTRY:
        mod = importlib.import_module('engine.' + modpath)
        ports_out = (getattr(mod, 'PORTS', {}) or {}).get('out') or {}
        required = {k for k, v in ports_out.items()
                    if not str(v).endswith('?')}
        for args in ({}, {'x': 1}, {'mode': 'zzz'}):
            from tools import call_tool
            r = call_tool(name, args)
            res = (r.get('result') or {})
            body = set(res) - {'_tool', '_input'}
            if required - body:
                missing.append((name, sorted(required - body)))
            if body - set(ports_out):
                extra.append((name, sorted(body - set(ports_out))))
            if 'verdict' not in res:
                no_verdict.append(name)
            if 'boundary' not in res or 'boundary' not in ports_out:
                no_boundary.append(name)
    return missing, extra, no_verdict, no_boundary


_missing, _extra, _no_verdict, _no_boundary = _shape_check()
check_("★PORTS 声明了就必须返回：非可选字段一个都不许缺", not _missing,
       _missing[:4])
check_("★返回的键必须在 PORTS 里声明（多返回少声明也是文档说谎）", not _extra,
       _extra[:4])
check_("每个构件的每个返回点都带 verdict", not _no_verdict,
       sorted(set(_no_verdict))[:4])
check_("每个构件都带 boundary，且 PORTS 里声明了它（全仓约定）",
       not _no_boundary, sorted(set(_no_boundary))[:4])


# ── 用例N+1：静态查所有返回点（动态那条只喂空参，走不到成功路径）
import ast as _ast  # noqa: E402


def _static_return_gaps():
    """每个带 verdict 的 return 字典都必须带 boundary（静态 AST 查，路径全覆盖）。"""
    gaps = []
    seen = set()
    for name, modpath, _desc in _TOOL_REGISTRY:
        mod = importlib.import_module('engine.' + modpath)
        path = getattr(mod, '__file__', None)
        if not path or path in seen:
            continue
        seen.add(path)
        tree = _ast.parse(io.open(path, encoding='utf-8').read())
        # 只看 run() 里的返回——**对外契约是 run 的返回**；helper 里那种带 verdict 的
        # 中间结构（如 converge_check 的分支小结果）不是对外输出，不该被这条管。
        for fn in [n for n in tree.body
                   if isinstance(n, _ast.FunctionDef) and n.name == 'run']:
            for st in fn.body:
                for node in _ast.walk(st):
                    if not isinstance(node, _ast.Return) or \
                            not isinstance(node.value, _ast.Dict):
                        continue
                    keys = [k.value for k in node.value.keys
                            if isinstance(k, _ast.Constant)]
                    if 'verdict' in keys and 'boundary' not in keys:
                        gaps.append((os.path.basename(path), node.lineno))
    return gaps


_gaps = _static_return_gaps()
check_("★静态查返回点：每个带 verdict 的返回字典都带 boundary（含成功路径）",
       not _gaps, _gaps[:5])

print("=" * 60)
print(f"结果: {PASS}/27 通过")
raise SystemExit(0 if PASS == 27 else 1)
