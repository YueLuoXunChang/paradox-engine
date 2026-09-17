# -*- coding: utf-8 -*-
"""
test_public_face.py — 正式测试：外向化抽查（发布面不夹带内部残留）
=====================================================================
为什么有这个文件：
    仓库是**公开**的，但它的来源是体系内部工程（内部规划文档、内部档案、本机
    路径、另一个内部项目）。历史教训：推送前靠人工逐条清（"内部文档指针/档案
    编号零残留"）——人眼会漏、下次还会漏。本文件把"发布面干净"变成**可执行的
    不变式**：任何文本文件里出现内部残留，回归即失败并指名到文件与行号。

四类禁止项（都是"读者拿不到、也不该看到"的东西）：
    ① 本机绝对路径（D:\\… / /Users/… / /home/…）——泄露目录结构；
    ② 私有档案引用（记账文档 / §编号 / 内部档案 / 内部代码库 / 内部验证仓 /
       本机工作目录 / 内部引擎项目）——读者打不开，等于死链；
    ③ 内部文档**编号**（如 长期架构蓝图.md、"蓝图"）——按作者先例：
       可保留"详规/总架构/公式卡"这类**通用表述**，但**不带编号**；
    ④ 个人联系信息（邮箱/QQ 号）出现在仓库文件里（NOTICE 只留 GitHub 链接）。

允许项（明确写出来，免得误伤）：
    - `详规 §X` / `总架构 §X` / `公式卡 §X`：通用表述 + 章节号，非文档编号；
    - `docs/formulas/*.md`（公式卡在仓库内，引用它们是内部链接，正常）；
    - CHANGELOG / ROADMAP 中的"轨 A/B/C/D"：仓库自己的路线图术语（ROADMAP §六已公开定义）；
    - MPL-2.0 LICENSE 文本本身（含 Mozilla 等字样）。
运行：python engine/test_public_face.py
"""

import os
import re
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


# ── 四类禁止项的判据（顺序即报告顺序）
_BANS = [
    ('本机绝对路径',
     re.compile(r'[A-Za-z]:\\\\|[A-Za-z]:\\[A-Za-z]|/Users/[A-Za-z]|/home/[a-z]')),
    ('私有档案引用',
     re.compile(r'记账文档|回测\s*§|内部档案|内部代码库|内部验证仓'
                r'|本机工作目录|内部引擎项目')),
    ('内部文档编号',
     re.compile(r'\b\d{2}_[^\s`）)]*\.md|(?:4[0-5]|3[89])\s*蓝图')),
    ('个人联系方式',
     re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+|QQ[:：]?\s*\d{5,}')),
]

_TEXT_EXT = ('.py', '.md', '.json', '.yml', '.yaml', '.toml', '.txt')
_TEXT_NAME = ('NOTICE', '.gitignore', '.gitattributes', 'LICENSE')
_SKIP_DIRS = {'__pycache__', 'build', '.git', 'paradox_engine.egg-info'}

# 显式排除集合（就这两项，且下面有断言盯着——防"排除集"被悄悄扩大）：
#   · LICENSE：MPL 全文照抄，不做关键词过滤；
#   · 本判据文件自身：它必须**写出**禁止词样例（正则与自检字符串），
#     否则没法测——与 LICENSE 同理，属规则文件例外。
_SELF = os.path.relpath(os.path.abspath(__file__), _REPO).replace('\\', '/')
_EXCLUDE = {'LICENSE', _SELF}


def _text_files():
    out = []
    for dp, dn, fn in os.walk(_REPO):
        dn[:] = [d for d in dn if d not in _SKIP_DIRS]
        for f in fn:
            if f.endswith(_TEXT_EXT) or f in _TEXT_NAME:
                out.append(os.path.join(dp, f))
    return sorted(out)


_FILES = _text_files()
_hits = {label: [] for label, _ in _BANS}
_skipped = set()
for p in _FILES:
    rel = os.path.relpath(p, _REPO).replace('\\', '/')
    if rel in _EXCLUDE:
        _skipped.add(rel)
        continue
    try:
        text = open(p, encoding='utf-8').read()
    except (OSError, UnicodeDecodeError):
        continue
    for label, pat in _BANS:
        for m in pat.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            _hits[label].append(f'{rel}:{line} {m.group(0)[:30]!r}')

print("外向化抽查 · 正式测试")
print("=" * 60)
print(f"  （扫描 {len(_FILES)} 个文本文件）")

for label, _ in _BANS:
    arr = _hits[label]
    check(f"无{label}", not arr, f"{len(arr)} 处: {arr[:4]}")

# 判据自查：故意造一条命中，确认判据真的抓得住（防止正则写废了还全绿）
_fake = "记账文档 §151 与 D:\\本机工作目录\\x 与 长期架构蓝图.md 与 a@b.com"
_caught = [label for label, pat in _BANS if pat.search(_fake)]
check("判据自检：四类禁止项都能被抓住（正则未写废）",
      len(_caught) == 4, f"只抓到 {_caught}")
check("允许项不误伤（详规 §1.1 / 公式卡 §2.1 / 轨 C1 均放行）",
      not any(pat.search('详规 §1.1 与 公式卡 §2.1 与 轨 C1')
              for _, pat in _BANS))
check("公式卡文件本身在仓库内（引用它们是内部链接非死链）",
      os.path.exists(os.path.join(_REPO, 'docs', 'formulas')))
check("许可文本保留 MPL 字样（LICENSE 排除在关键词过滤外）",
      'Mozilla Public License' in open(os.path.join(_REPO, 'LICENSE'),
                                       encoding='utf-8').read())
check("扫描覆盖面 ≥80 文件（含 py/md/json/yml/NOTICE）", len(_FILES) >= 80,
      str(len(_FILES)))
check("排除集合固定为「判据文件 + LICENSE」（防悄悄扩大）",
      _skipped == _EXCLUDE and len(_EXCLUDE) == 2, str(sorted(_skipped)))

print("=" * 60)
print(f"结果: {PASS}/10 通过")
raise SystemExit(0 if PASS == 10 else 1)
