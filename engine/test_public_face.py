# -*- coding: utf-8 -*-
"""
test_public_face.py — 正式测试：外向化抽查（发布面不夹带内部残留）
=====================================================================
为什么有这个文件：
    仓库是**公开**的，但它的来源是体系内部工程（内部规划文档、内部私有仓、本机
    路径）。历史教训：推送前靠人工逐条清——人眼会漏、下次还会漏。本文件把
    "发布面干净"变成**可执行的不变式**：任何文本文件里出现内部残留，回归即失败
    并指名到文件与行号。

两档判据（重要）：
    · **通用判据（写在本文件里，公开安全）**：本机绝对路径、内部文档**编号**
      （形如「NN_xxx.md」「NN 蓝图」）、悬挂的私有档案章节引用（形如「X §12」）、
      个人联系方式、常见密钥形态——这些**不需要点名任何私有工程**就能查；
    · **私有名清单（本机可选）**：具体私有仓/档案的名字**不写进本文件**——本文件
      本身是公开的，把私有名列在这里等于把内部结构公布了。改为从仓库根的
      `.public-face-local.txt`（已 gitignore，每行一个待禁词组）读取；有就一起查，
      没有就只跑通用判据（CI 属于后者，本机跑则全覆盖）。

为什么这么设计（一次真实自查发现）：第一版把私有名明文写在判据里，等于"用公布
私有名的代价来防止私有名外泄"——本文件一旦发布就自相矛盾。

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


_LOCAL_LIST = os.path.join(_REPO, '.public-face-local.txt')


def _local_patterns():
    """本机私有名清单（可选、gitignored）：每行一个词组，'#' 起注释。"""
    if not os.path.exists(_LOCAL_LIST):
        return []
    out = []
    with open(_LOCAL_LIST, encoding='utf-8') as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith('#'):
                out.append(s)
    return out


# ── 判据（通用项 + 可选的私有名）
# 每项：(标签, 正则, 预处理函数或 None)。预处理用于"先中性化允许表述再扫"
# ——例如「详规 §4.2」是允许的（通用表述+章节号），把它替换成非中文占位符后，
# 「XX §N」正则就不会误伤它；剩下的才是真·悬挂引用。
_ALLOWED_SPEC = ('详规', '总架构', '公式卡', '公式源')


def _neutralize_allowed(text):
    for w in _ALLOWED_SPEC:
        text = text.replace(w, '__')
    return text


_BANS = [
    ('本机绝对路径',
     re.compile(r'[A-Za-z]:\\\\|[A-Za-z]:\\[A-Za-z]|/Users/[A-Za-z]|/home/[a-z]'),
     None),
    ('内部文档编号',
     re.compile(r'\b\d{2}_[^\s`）)]*\.md|(?:4[0-5]|3[89])\s*蓝图'), None),
    ('悬挂的私有档案引用',
     re.compile(r'[\u4e00-\u9fff]{2,8}\s*§\s*\d+'), _neutralize_allowed),
    ('个人联系方式',
     re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+|QQ[:：]?\s*\d{5,}'), None),
    ('常见密钥形态',
     re.compile(r'sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,}'
                r'|-----BEGIN [A-Z ]*PRIVATE KEY-----'), None),
]
_priv = _local_patterns()
if _priv:
    _BANS.append(('本机私有名清单（.public-face-local.txt）',
                  re.compile('|'.join(re.escape(x) for x in _priv)), None))

_TEXT_EXT = ('.py', '.md', '.json', '.yml', '.yaml', '.toml', '.txt')
_TEXT_NAME = ('NOTICE', '.gitignore', '.gitattributes', 'LICENSE')
_SKIP_DIRS = {'__pycache__', 'build', '.git', 'paradox_engine.egg-info'}

# 显式排除集合（三项，且下面有断言盯着——防"排除集"被悄悄扩大）：
#   · LICENSE：MPL 全文照抄，不做关键词过滤；
#   · 本判据文件自身：它必须**写出**禁止词样例（正则与自检字符串），否则没法测；
#   · .public-face-local.txt：本机私有名清单——它**按设计**就写着私有名，且已在
#     .gitignore（不进仓库）；下面有断言核对这一点，排除它才不会掩盖真问题。
_SELF = os.path.relpath(os.path.abspath(__file__), _REPO).replace('\\', '/')
_EXCLUDE = {'LICENSE', _SELF, '.public-face-local.txt'}


def _text_files():
    out = []
    for dp, dn, fn in os.walk(_REPO):
        dn[:] = [d for d in dn if d not in _SKIP_DIRS]
        for f in fn:
            if f.endswith(_TEXT_EXT) or f in _TEXT_NAME:
                out.append(os.path.join(dp, f))
    return sorted(out)


# ── 源码仓专属检查：装到 site-packages 后没有仓库根（README/docs/），这类检查
# 无从查起——**在任何读仓库文件之前**就判定并诚实跳过（不报假失败、不假装通过）。
try:
    from engine._layout import in_source_checkout, skip_note
except ImportError:
    sys.path.insert(0, _HERE)
    from _layout import in_source_checkout, skip_note

if not in_source_checkout():
    print(skip_note('发布面残留抽查'))
    print("=" * 60)
    print("结果: 1/1 通过")
    raise SystemExit(0)

_FILES = _text_files()
_hits = {label: [] for label, _pat, _pre in _BANS}
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
    for label, pat, pre in _BANS:
        scanned = pre(text) if pre else text
        for m in pat.finditer(scanned):
            line = text.count('\n', 0, m.start()) + 1
            _hits[label].append(f'{rel}:{line} {m.group(0)[:30]!r}')

print("外向化抽查 · 正式测试")
print("=" * 60)
print(f"  （扫描 {len(_FILES)} 个文本文件；"
      f"私有名清单 {'已加载 ' + str(len(_priv)) + ' 条' if _priv else '未提供（CI 常态）'}）")

for label, _pat, _pre in _BANS:
    arr = _hits[label]
    check(f"无{label}", not arr, f"{len(arr)} 处: {arr[:4]}")

# 判据自查：故意造一条命中，确认判据真的抓得住（防止正则写废了还全绿）
_fake = ("某内部档案 §151 与 D:\\某盘\\x 与 99_某内部文档.md 与 a@b.com"
         " 与 sk-abcdefghijklmnop")
_caught = [label for label, pat, pre in _BANS
           if pat.search(pre(_fake) if pre else _fake)]
check("判据自检：通用禁止项都能被抓住（正则未写废）",
      len(_caught) >= 4, f"只抓到 {_caught}")
check("允许项不误伤（详规 §1.1 / 公式卡 §2.1 放行——中性化后不再命中）",
      not any(pat.search(pre('详规 §1.1 与 公式卡 §2.1') if pre
                         else '详规 §1.1 与 公式卡 §2.1')
              for _, pat, pre in _BANS))
check("私有名清单是本地可选（不在仓库内=不会随发布泄露）",
      not os.path.exists(os.path.join(_REPO, '.public-face-local.txt'))
      or '.public-face-local.txt' in open(
          os.path.join(_REPO, '.gitignore'), encoding='utf-8').read(),
      '.public-face-local.txt 未在 .gitignore 中')
check("公式卡文件本身在仓库内（引用它们是内部链接非死链）",
      os.path.exists(os.path.join(_REPO, 'docs', 'formulas')))
check("许可文本保留 MPL 字样（LICENSE 排除在关键词过滤外）",
      'Mozilla Public License' in open(os.path.join(_REPO, 'LICENSE'),
                                       encoding='utf-8').read())
check("扫描覆盖面 ≥80 文件（含 py/md/json/yml/NOTICE）", len(_FILES) >= 80,
      str(len(_FILES)))
check("排除集合固定为「判据文件 + LICENSE + 本地私有名清单」（防悄悄扩大）",
      _skipped == _EXCLUDE and len(_EXCLUDE) == 3, str(sorted(_skipped)))
check("被排除的本地清单确实在 .gitignore（排除才安全）",
      '.public-face-local.txt' in open(os.path.join(_REPO, '.gitignore'),
                                       encoding='utf-8').read())

print("=" * 60)
print(f"结果: {PASS}/14 通过")
raise SystemExit(0 if PASS == 14 else 1)
