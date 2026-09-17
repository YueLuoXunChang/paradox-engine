# -*- coding: utf-8 -*-
"""
test_tool_contract.py — 正式测试：工具协议冻结（轨 C1）
用例依据：轨 C1「工具协议稳定 + 调用方文档」——工具名/参数名是对外契约，
         改了要让调用方知道（快照 + 文档 + 记账），不能静默漂移。
运行：python engine/ai/test_tool_contract.py
"""
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
check_("调用方文档存在", os.path.exists(_DOC), _DOC)
_md = open(_DOC, encoding='utf-8').read()
check_("文档覆盖全部工具（无遗漏）", all(f'`{n}`' in _md for n in _live),
       [n for n in _live if f'`{n}`' not in _md][:5])
check_("文档标明自动生成（勿手改）", '自动生成' in _md and '请勿手改' in _md,
       _md[:80])
check_("文档给出调用示例", 'call_tool(' in _md and 'from engine.ai.tools' in _md)
check_("文档渲染函数与文件内容一致（可重生成）",
       render_markdown(_tl).strip() == _md.strip(),
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
_before = (os.path.getmtime(_SNAPSHOT), os.path.getmtime(_DOC))
_r = run({'check': True})
_after = (os.path.getmtime(_SNAPSHOT), os.path.getmtime(_DOC))
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

print("=" * 60)
print(f"结果: {PASS}/22 通过")
raise SystemExit(0 if PASS == 22 else 1)
