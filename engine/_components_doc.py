# -*- coding: utf-8 -*-
"""
_components_doc.py — 构件参考自动生成（docs/components.md）+ 漂移检查
================================================================
为什么有它：41 个引擎模块的说明散在各文件 docstring 里，对外只有一份
`docs/tool_schema.md`（那是**工具**的）。前面查索引时发现 README 结构树漏登记 9 个模块——
**人肉维护清单必然漏**。这里把「从代码生成参考 + 漂移即报」补上。

生成什么（每构件一段）：
    层 · 模块路径 · 一句话（docstring 里的「本构件做什么」）· 端口（PORTS in/out）·
    是否能独立运行（有 __main__ 自测）

口径：
    - **只读代码**：从 AST 里取 PORTS（literal）与 docstring，不 import、不执行；
    - 生成物由 `--write` 落盘，默认只打印；`--check` 比对现有文件（漂移即非零退出）；
    - 下划线内部件（_validate/_layout/_console/_refs_audit/_components_doc）不进参考。
"""

import ast
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
DOC = os.path.join(_REPO, 'docs', 'components.md')

LAYERS = (
    ('control', '第 0 层 · 总控（判类/复杂度/路由/五步流水线/工作台）'),
    ('skeleton', '第 0 层 · MT-MP-TL 骨架（结构表达，不掺判定）'),
    ('classical', '第 1 层 · 经典逻辑地基（判定/证明/可计算/类型）'),
    ('mechanisms', '第 2 层 · 悖论机制（撞墙管线 A 与五件套）'),
    ('cold', '第 3 层 · 冷门逻辑（按痛点接入，外部共识归借鉴区）'),
    ('scenarios', '场景库（真实输入 + 期望 + 对照 + 复核）'),
    ('ai', 'AI 挂载层（function-calling 工具与契约快照）'),
    ('(root)', '其它（数学底座等根目录模块）'),
)


def _summary(doc, path):
    """取 docstring 里的一句话（「本构件做什么」优先）。"""
    if not doc:
        return '（无 docstring——建议补上）'
    lines = [l.strip() for l in doc.split('\n')]
    for i, l in enumerate(lines):
        if '本构件做什么' in l:
            for nxt in lines[i + 1:]:
                if nxt:
                    return nxt.rstrip('。')
    for l in lines:                      # 退而求其次：第一行有内容的
        if l and not l.startswith(('===', '—', '-')):
            return l.rstrip('。')[:100]
    return '（无说明）'


def _ports(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == 'PORTS':
                    try:
                        return ast.literal_eval(node.value)
                    except ValueError:
                        return None
    return None


def scan():
    """扫全仓构件：返回按层分组的列表（只读 AST，不 import）。"""
    out = {}
    for dp, dn, fn in os.walk(_HERE):
        dn[:] = [d for d in dn if d != '__pycache__']
        for f in sorted(fn):
            if not f.endswith('.py') or f.startswith(('test_', '_')):
                continue
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, _REPO).replace('\\', '/')
            src = io.open(path, encoding='utf-8').read()
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            layer = os.path.basename(dp) if dp != _HERE else '(root)'
            out.setdefault(layer, []).append({
                'path': rel,
                'summary': _summary(ast.get_docstring(tree), path),
                'ports': _ports(tree),
                'selfrun': "'__main__'" in src or '"__main__"' in src,
            })
    return out


def render():
    mods = scan()
    total = sum(len(v) for v in mods.values())
    L = ['# 构件参考（自动生成，别手改）', '',
         '> 由 `python engine/_components_doc.py --write` 从各模块 docstring 与 `PORTS` 生成；'
         '`--check` 可在改动后比对漂移。手改这份文件会在检查里报不一致。', '',
         '- 构件数：**%d** 个（不含下划线内部件与测试）' % total, '']
    for key, title in LAYERS:
        items = mods.get(key)
        if not items:
            continue
        L.append('## %s' % title)
        L.append('')
        for it in items:
            L.append('### `%s`' % it['path'])
            L.append('')
            L.append('- 做什么：%s' % it['summary'])
            p = it['ports']
            if p and isinstance(p, dict):
                ins = p.get('in') or {}
                outs = p.get('out') or {}
                L.append('- 输入端口：%s'
                         % ('、'.join('`%s: %s`' % kv for kv in ins.items())
                            or '（无）'))
                L.append('- 输出端口：%s'
                         % ('、'.join('`%s: %s`' % kv for kv in outs.items())
                            or '（无）'))
            else:
                L.append('- 端口：未声明 `PORTS`')
            L.append('- 可独立运行：%s' % ('是（自带自测）' if it['selfrun']
                                          else '否'))
            L.append('')
    # 未在 LAYERS 里点到名的目录也要列出来（防新目录被漏）
    others = [k for k in mods if k not in dict(LAYERS)]
    if others:
        L.append('## 其它目录')
        L.append('')
        for k in sorted(others):
            for it in mods[k]:
                L.append('- `%s`：%s' % (it['path'], it['summary']))
        L.append('')
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    text = render()
    if '--write' in argv:
        with io.open(DOC, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('已写出 %s（%d 字）'
              % (os.path.relpath(DOC, _REPO).replace('\\', '/'), len(text)))
        return 0
    if '--check' in argv:
        have = (io.open(DOC, encoding='utf-8').read()
                if os.path.exists(DOC) else '')
        if have != text:
            print('构件参考与代码不一致（跑 --write 更新）')
            return 1
        print('构件参考一致')
        return 0
    print(text)
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
