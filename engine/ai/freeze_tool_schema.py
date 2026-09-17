# -*- coding: utf-8 -*-
"""
freeze_tool_schema.py — 工具协议冻结：生成快照 JSON + 调用方文档
====================================================================
概念来源：轨 C1（生态接口）：**工具名与参数名是对外契约**——不随意改，
改了要记账（CHANGELOG），否则调用方（AI 客户端、脚本、上层应用）会静默
挂掉。

本脚本做什么（一句话）：
    把当前 `engine.ai.tools.tools()` 的工具契约（名字 + 参数名/类型/必填）
    写成两层产物：
      ① `engine/ai/tool_schema_frozen.json`——**冻结快照**（机器可读，喂测试）；
      ② `docs/tool_schema.md`——**给调用方看的中文文档**（人可读）。
    两者都从活代码生成，不手写——避免"文档与实现各说各话"。

用法：
    python engine/ai/freeze_tool_schema.py            # 重新生成（有意变更后跑）
    python engine/ai/freeze_tool_schema.py --check    # 只检查是否一致（不改文件）

诚实边界：
    - 快照只冻结**契约**（工具名/参数名/类型/必填），不冻结描述文案——
      文案可改不改契约；
    - 生成 ≠ 批准：改契约仍要在 CHANGELOG 里记账（工具协议是
      对外承诺，不是内部细节）。
"""

PORTS = {
    'in': {'check': 'bool?'},
    'out': {'verdict': 'str', 'changed': 'list', 'boundary': 'str'},
}

import io
import json
import os
import sys

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SNAPSHOT = os.path.join(_HERE, 'tool_schema_frozen.json')
_DOC = os.path.join(_REPO, 'docs', 'tool_schema.md')

_SNAPSHOT_NOTE = ('工具协议冻结快照——工具名与参数名是对外契约（轨 C1）；'
                  '有意变更后跑 python engine/ai/freeze_tool_schema.py 重新生成，'
                  '并在 CHANGELOG 记账。')


def contract(tool_list):
    """从 tools() 结果抽契约：{工具名: {参数名: {type, required}}}（排序稳定）。"""
    out = {}
    for t in tool_list:
        fn = t['function']
        params = {}
        required = set(fn['parameters'].get('required') or [])
        for pname, spec in sorted(fn['parameters']['properties'].items()):
            params[pname] = {'type': spec.get('type', 'string'),
                             'required': pname in required}
        out[fn['name']] = params
    return out


def snapshot_doc(tool_list):
    """快照文件内容（含说明与契约）。"""
    return {'_note': _SNAPSHOT_NOTE,
            'tool_count': len(tool_list),
            'contract': contract(tool_list)}


def render_markdown(tool_list):
    """给调用方的中文文档（人可读）。"""
    lines = [
        '# 工具协议（AI 可调用工具清单）',
        '',
        '> 本文件由 `python engine/ai/freeze_tool_schema.py` 从 '
        '`engine/ai/tools.py` 的注册表**自动生成**，请勿手改。',
        '> 工具名与参数名是对外契约（轨 C1）：有意变更须重新生成'
        '本文件与 `engine/ai/tool_schema_frozen.json`，并在 CHANGELOG 与'
        '变更记账。',
        '',
        f'共 **{len(tool_list)}** 件工具。调用方式：',
        '',
        '```python',
        'from engine.ai.tools import tools, call_tool',
        'print(tools())                      # OpenAI 风格 schema 清单',
        "r = call_tool('paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5})",
        "print(r['result'])                  # 构件原始输出（含 boundary 边界声明）",
        '```',
        '',
        '## 契约表（工具名 → 参数）',
        '',
        '| 工具 | 参数（必填加 *）| 一句话 |',
        '|---|---|---|',
    ]
    for t in tool_list:
        fn = t['function']
        required = set(fn['parameters'].get('required') or [])
        ps = []
        for pname, spec in sorted(fn['parameters']['properties'].items()):
            mark = '*' if pname in required else ''
            ps.append(f"`{pname}{mark}`:{spec.get('type', 'string')}")
        desc = fn['description'].replace('|', '\\|')
        lines.append(f"| `{fn['name']}` | {' '.join(ps) or '（无参数）'} | {desc} |")
    lines += [
        '',
        '## 返回约定',
        '',
        '- `call_tool` 统一返回 `{verdict, tools, result, boundary}`：'
        '`verdict=\'ok\'` 表示构件真跑；`result` 是构件原始输出；',
        '- 构件缺参时**诚实拦截**（`*_pending`），挂载层不伪造输入；',
        '- 每个构件输出都带 `boundary`（只诊断不决策声明随行）；',
        '- 未知工具返回 `verdict=\'tool_unknown\'` 并附可用清单。',
        '',
    ]
    return '\n'.join(lines)


def _load_tools():
    from engine.ai.tools import tools
    return tools()


def check():
    """比对活注册表与冻结快照/文档是否一致。返回 (ok, changed 列表)。"""
    live = contract(_load_tools())
    if not os.path.exists(_SNAPSHOT):
        return False, ['快照文件不存在']
    frozen = json.load(io.open(_SNAPSHOT, encoding='utf-8'))['contract']
    changed = []
    for name in sorted(set(live) | set(frozen)):
        if name not in frozen:
            changed.append(f'+{name}（新增工具，未冻结）')
        elif name not in live:
            changed.append(f'-{name}（快照有、注册表无）')
        elif live[name] != frozen[name]:
            changed.append(f'~{name}（参数契约变了）')
    doc_ok = os.path.exists(_DOC)
    if doc_ok:
        text = io.open(_DOC, encoding='utf-8').read()
        for name in live:
            if f'`{name}`' not in text:
                changed.append(f'{name}（文档缺该工具）')
    else:
        changed.append('文档 docs/tool_schema.md 不存在')
    return not changed, changed


def run(inputs):
    """
    做什么：工具协议冻结——生成快照与文档，或只做一致性检查。

    check=True 只检查不改文件（CI/测试用）。"""
    tool_list = _load_tools()
    if inputs.get('check'):
        ok, changed = check()
        return {'verdict': 'consistent' if ok else 'drifted',
                'changed': changed,
                'boundary': ('工具契约与冻结快照一致' if ok else
                             '检测到契约漂移——有意变更请跑 '
                             'python engine/ai/freeze_tool_schema.py 重新生成'
                             '并记账；无意漂移请改回注册表。')}
    snap = snapshot_doc(tool_list)
    with io.open(_SNAPSHOT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True)
                 + '\n')
    with io.open(_DOC, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(render_markdown(tool_list) + '\n')
    return {'verdict': 'frozen', 'changed': [],
            'boundary': f'已冻结 {len(tool_list)} 件工具契约：'
                        'engine/ai/tool_schema_frozen.json + '
                        'docs/tool_schema.md（描述文案不入快照——文案可改，'
                        '契约改了要记账）。'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 64)
    print('工具协议冻结 · 自测（轨 C1）')
    print('=' * 64)

    if '--check' in sys.argv:
        ok, changed = check()
        print(f"{'✅ 一致' if ok else '⚠️ 漂移'}: {changed or '无差异'}")
        raise SystemExit(0 if ok else 1)

    tools_list = _load_tools()
    ct = contract(tools_list)
    assert len(ct) == len(tools_list), '契约条目数与工具数不一致'
    print(f'✅ 契约抽取：{len(ct)} 件工具')

    md = render_markdown(tools_list)
    assert all(f'`{n}`' in md for n in ct), '文档缺工具'
    print(f'✅ 文档渲染：{len(md)} 字符，覆盖全部工具')

    r = run({})
    assert r['verdict'] == 'frozen', r
    print(f"✅ 冻结输出：{r['boundary'][:38]}…")

    ok, changed = check()
    assert ok, changed
    print('✅ 一致性检查：活注册表 == 冻结快照 == 文档')

    print('=' * 64)
    print('工具协议冻结自测：全部通过 ✅')
    print('=' * 64)
