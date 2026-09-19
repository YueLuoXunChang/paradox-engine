# -*- coding: utf-8 -*-
"""
test_doc_commands.py — 不变式：文档里的命令示例必须真能跑
================================================================
为什么要有这条：这一段时间 CLI 从 11 个旗标涨到 39 个，README 里的示例是读者
第一眼看到的东西——**示例里的旗标写错一个字母，读者复制就报错**；
反过来，新加的旗标没写进文档，就等于没做。

检查两条（双向）：
    1) 文档里出现的引擎 CLI 示例，旗标必须在解析器里真实存在；
    2) 解析器里的旗标（除 -h/--help）必须在文档里出现过。
范围：README.md / README.en.md / CONTRIBUTING.md / docs/*.md（CHANGELOG 里也扫）。
运行：python engine/test_doc_commands.py
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli import build_parser  # noqa: E402

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


# 旗标 token：右边界不让 --structured 匹配到 --structured-json 里
_FLAG = re.compile(r'--[a-z][a-z0-9-]*(?![a-z0-9-])')
_CMD = re.compile(r'(?:paradox-engine|python -m engine\.cli)\s+([^\n`]*)')

DOCS = ['README.md', 'README.en.md', 'CONTRIBUTING.md', 'CHANGELOG.md']
_docs_dir = os.path.join(_REPO, 'docs')
DOCS += ['docs/' + f for f in sorted(os.listdir(_docs_dir))
         if f.endswith('.md')]

parser_flags = {s for a in build_parser()._actions for s in a.option_strings}
parser_flags_public = parser_flags - {'-h', '--help'}

print("文档命令示例 · 不变式检查")
print("=" * 60)

texts = {}
examples = []          # (doc, 片段)
doc_flags = set()      # 文档里出现过的旗标（含散文里的）
for d in DOCS:
    path = os.path.join(_REPO, d)
    if not os.path.exists(path):
        continue
    t = io.open(path, encoding='utf-8').read()
    texts[d] = t
    doc_flags |= set(_FLAG.findall(t))
    for m in _CMD.finditer(t):
        frag = m.group(1).strip()
        if _FLAG.search(frag):        # 只算带旗标的才算"示例命令"
            examples.append((d, frag))

check("扫到的文档文件 ≥ 4 个", len(texts) >= 4, str(sorted(texts)))
check("提取到带旗标的命令示例 ≥ 40 条（否则提取器坏了）",
      len(examples) >= 40, f"{len(examples)} 条")
check("示例跨中英 README（两处都扫到）",
      any(d == 'README.md' for d, _ in examples)
      and any(d == 'README.en.md' for d, _ in examples))

# ── 正向：示例里的旗标必须真实存在
bad = []
for d, frag in examples:
    for fl in _FLAG.findall(frag):
        if fl == '-h':
            continue
        if fl not in parser_flags:
            bad.append((d, fl, frag[:60]))
check("示例里的旗标全部真实存在（没有写错的旗标）", not bad,
      '; '.join('%s: %s ← %s' % b for b in bad[:5]))

# ── 反向：解析器的旗标都得在文档里出现过
undoc = sorted(parser_flags_public - doc_flags)
check("解析器旗标全部在文档里出现过（没有默默加的旗标）", not undoc,
      '未写进文档的旗标: %s' % ' '.join(undoc))

# ── 关键动作都要有例子（新加的旗标别只活在 --help 里）
KEY_FLAGS = ['--text', '--json', '--scenarios', '--scene', '--explain',
             '--suggest', '--review', '--mark', '--stats', '--session',
             '--add', '--add-file', '--clues', '--overview', '--pending',
             '--progress', '--brief', '--export', '--revise', '--session-state']
missing_examples = [fl for fl in KEY_FLAGS
                    if not any(fl in frag for _, frag in examples)]
check("关键动作旗标都有命令示例（不只是 --help 里写着）",
      not missing_examples, '缺示例: %s' % ' '.join(missing_examples))

# ── 示例里「需要取值的旗标」后面得跟值，不许紧跟另一个旗标（漏值写法）
import argparse  # noqa: E402
_noarg = set()
for _a in build_parser()._actions:
    if isinstance(_a, (argparse._StoreTrueAction, argparse._StoreConstAction)) \
            or _a.nargs == 0:
        _noarg |= set(_a.option_strings)
_pairs = re.compile(r'(--[a-z][a-z0-9-]*(?![a-z0-9-]))\s+'
                    r'(--[a-z][a-z0-9-]*(?![a-z0-9-]))')
weird = []
for d, frag in examples:
    for m in _pairs.finditer(frag):
        if m.group(1) not in _noarg:        # 前一个要取值，却紧跟旗标 → 漏值
            weird.append((d, m.group(0), frag[:60]))
check("示例里没有「需要取值的旗标漏了值」的写法", not weird,
      str(weird[:3]))

# ── 帮助文本与解析器一致（每个旗标都有 help，别留光秃秃的旗标）
no_help = [a.option_strings[0] for a in build_parser()._actions
           if a.option_strings and not (a.help or '').strip()
           and a.option_strings[0] not in ('-h', '--help')]
check("每个旗标都写了 help（别留光秃秃的）", not no_help, str(no_help))

print("=" * 60)
print(f"结果: {PASS}/8 通过")
raise SystemExit(0 if PASS == 8 else 1)
