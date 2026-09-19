# -*- coding: utf-8 -*-
"""
_refs_audit.py — 私有档案引用清点（只读，只列不改）
================================================================
为什么有它：发布面红线里「指向私有档案的章节引用」属于悬挂引用（读者打不开），
但仓库里这类引用散落在模块 docstring / CHANGELOG / ROADMAP 里，**光靠人翻看不完**。
本文件把全仓的引用清点出来——**只列不删**：清还是留是作者的口径，引擎不擅自改。

怎么判（两种形态）：
    1) 私有档案**名 + 章节号**：`详规 §五`、`《第3层冷门详规》§三`、`总架构 §3.2`、
       `公式卡 §2.1`、`…蓝图` 这一类（档案名前后 ±30 字内出现 § 号）；
    2) 内部文档**编号型**指针：形如 `NN_某内部文档.md`（两位数编号打头的文档名）。

**本仓内的章节引用不算**：`§6.4` 指的是本仓 docs/ROADMAP.md 的小节，读者打得开，
不在此列（这条是判据的关键，否则误报会淹掉真问题）。
"""

import io
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

# 私有档案名（读者打不开的那些）
PRIVATE_NAMES = ('详规', '总架构', '公式卡', '蓝图', '公式源', '机制组合方案')
# 内部文档编号型指针
NUMBERED_DOC = re.compile(r'\b\d{2}_[^\s`）)、，。]*\.md')
_SEC = re.compile(r'§\s*[0-9一二三四五六七八九十百]+(?:\.[0-9]+)?')
_TEXT_EXT = ('.py', '.md', '.json', '.yml', '.yaml', '.toml', '.txt')
_TEXT_NAME = ('NOTICE', '.gitignore', '.gitattributes', 'LICENSE')
_SKIP_DIRS = {'__pycache__', 'build', '.git', 'paradox_engine.egg-info'}
_WINDOW = 30


def text_files(root=None):
    root = root or _REPO
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in _SKIP_DIRS]
        for f in fn:
            if f.endswith(_TEXT_EXT) or f in _TEXT_NAME:
                out.append(os.path.join(dp, f))
    return sorted(out)


def scan_file(path):
    """返回该文件里的私有引用：[(行号, 片段, 形态)]。"""
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().split('\n')
    except (IOError, OSError):
        return []
    hits, seen = [], set()
    for i, line in enumerate(lines, 1):
        for m in NUMBERED_DOC.finditer(line):
            key = (i, m.group(0))
            if key not in seen:
                seen.add(key)
                hits.append((i, m.group(0), '编号型指针'))
        for m in _SEC.finditer(line):
            lo = max(0, m.start() - _WINDOW)
            hi = min(len(line), m.end() + _WINDOW)
            ctx = line[lo:hi].strip()
            for name in PRIVATE_NAMES:
                if name in ctx:
                    key = (i, ctx)          # 同一行的同一段上下文只记一处
                    if key not in seen:
                        seen.add(key)
                        hits.append((i, ctx, '私有档案名+章节号'))
                    break
    return hits


def audit(root=None):
    """全仓清点：{'files': {相对路径: [命中]}, 'total': n, 'files_hit': m}"""
    root = root or _REPO
    files = {}
    total = 0
    for p in text_files(root):
        rel = os.path.relpath(p, root).replace('\\', '/')
        if rel in ('engine/_refs_audit.py', 'engine/test_public_face.py'):
            continue   # 本文件与发布面判据都必须**写出**这些名字，跳过
        hits = scan_file(p)
        if hits:
            files[rel] = hits
            total += len(hits)
    return {'files': files, 'total': total, 'files_hit': len(files)}


def report_text(root=None):
    """人看的清单（只列不删，落不落文件由调用方决定）。"""
    r = audit(root)
    L = ['私有档案引用清点（只列不改；清或留由作者定）', '=' * 48]
    kinds = {}
    for hits in r['files'].values():
        for _ln, _frag, kind in hits:
            kinds[kind] = kinds.get(kind, 0) + 1
    L.append('共 %d 处，涉及 %d 个文件：%s'
             % (r['total'], r['files_hit'],
                ' · '.join('%s %d 处' % kv
                           for kv in sorted(kinds.items()))))
    for rel in sorted(r['files']):
        hits = r['files'][rel]
        L.append('')
        L.append('%s（%d 处）' % (rel, len(hits)))
        for ln, frag, kind in hits[:8]:
            L.append('  %4d 行 [%s] %s' % (ln, kind, frag[:78]))
        if len(hits) > 8:
            L.append('  …还有 %d 处' % (len(hits) - 8))
    L.append('')
    L.append('口径：同一行的同一段上下文只记一处（例如「详规 §一~§五」按一处计），'
             '所以本工具的数字**偏保守**——不会比实际引用多；'
             '逐条命令的宽松扫描可能比这里多 1〜2 处，差在口径不在漏计。')
    L.append('说明：发布面判据文件自身写的「允许项样例」不计入（它必须写出'
             '这些名字，否则没法测）；本仓内章节引用（如 ROADMAP 的 §6.4）'
             '不算私有引用——'
             '读者打得开。清或留是作者口径，**本工具不改任何文件**。')
    L.append('提醒：这份清单里带着私有档案名，**别提交进公开仓库**'
             '（要存档就存进私有仓）。')
    return '\n'.join(L)


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass
    print(report_text())
