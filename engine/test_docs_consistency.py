# -*- coding: utf-8 -*-
"""
test_docs_consistency.py — 正式测试：文档一致性抽查（门面数字不许漂）
========================================================================
为什么有这个文件：
    README 上写着"X 项断言 / Y 个测试文件 / Z 件工具 / N 步 demo / M 个场景"——
    这些数字是给外人看的承诺，但每次加构件都得手改，**漏改就是对外说谎**。
    历史教训：断言数 533→588→770→841→866→869 期间，README 与实测多次对不上，
    靠人记着改不可靠。本文件把"门面上写的数字 == 实测"变成不变式。

查什么（都从**活代码/实际文件**取，不信文档自述）：
    ① 正式断言数与测试文件数：实跑 run_tests.py 的发现逻辑（只发现+计数，
       不重复执行测试，避免递归）；
    ② 工具件数：`engine.ai.tools` 注册表长度 + 契约快照里的 tool_count；
    ③ demo 步数：`demo.py` 里 banner("⑳ …") 的实际条数；
    ④ 场景数：`engine.scenarios.scenarios.SCENES`；
    ⑤ 冷门构件数：`engine/cold/` 下非 test 的构件数；
    ⑥ README/README.en 里声明的上述数字必须与实测一致（正则抓"X 项正式断言/
       Y 个测试文件 / Z 件工具 / N 步"）。
运行：python engine/test_docs_consistency.py
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


def _read(rel):
    return open(os.path.join(_REPO, rel), encoding='utf-8').read()


# ── 源码仓专属检查：装到 site-packages 后没有仓库根（README/docs/），这类检查
# 无从查起——**在任何读仓库文件之前**就判定并诚实跳过（不报假失败、不假装通过）。
try:
    from engine._layout import in_source_checkout, skip_note
except ImportError:
    sys.path.insert(0, _HERE)
    from _layout import in_source_checkout, skip_note

if not in_source_checkout():
    print(skip_note('门面数字一致性抽查'))
    print("=" * 60)
    print("结果: 1/1 通过")
    raise SystemExit(0)

# ── 实测值（从活代码/文件系统取）
_test_files = []
for dp, dn, fn in os.walk(_HERE):
    dn[:] = [d for d in dn if d not in ('__pycache__', 'build')]
    for f in fn:
        if f.startswith('test_') and f.endswith('.py'):
            _test_files.append(os.path.join(dp, f))
_n_test_files = len(_test_files)

# 断言总数：解析各测试文件末行的「结果: ... N 通过」——注意测试里写的是
# f-string（`print(f"结果: {PASS}/869 通过")`），源码中没有字面总数，
# 所以要同时认「{PASS}/N」与「N/M」两种形态（取分母 = 声明的通过线）。
# 不执行测试：执行是 run_tests.py 的活，在测试里跑全部测试会递归。
_total_asserts = 0
_den_re = re.compile(r'结果:\s*(?:\{PASS\}|(\d+))/(\d+)\s*通过')
_unknown = []
for p in _test_files:
    text = open(p, encoding='utf-8').read()
    ms = list(_den_re.finditer(text))
    if not ms:
        _unknown.append(os.path.relpath(p, _REPO))
        continue
    _total_asserts += int(ms[-1].group(2))

from engine.ai.tools import _TOOL_REGISTRY, tools  # noqa: E402
from engine.scenarios.scenarios import SCENES  # noqa: E402

_n_tools = len(_TOOL_REGISTRY)
_demo_steps = len(re.findall(r'banner\("', _read('demo.py')))
_n_scenes = len(SCENES)
_cold = [f for f in os.listdir(os.path.join(_HERE, 'cold'))
         if f.endswith('.py') and not f.startswith('test_')
         and f != '__init__.py']
_n_cold = len(_cold)

print("文档一致性抽查 · 正式测试")
print("=" * 60)
print(f"  实测：测试文件 {_n_test_files} 个 / 断言 {_total_asserts} 项 / "
      f"工具 {_n_tools} 件 / demo {_demo_steps} 步 / 场景 {_n_scenes} 个 / "
      f"冷门构件 {_n_cold} 件")

check("每个测试文件都声明通过线（无可解析『结果:』的漏网）",
      not _unknown, f"缺声明: {_unknown}")

_zh = _read('README.md')
_en = _read('README.en.md')

# ── ① 断言数 / 测试文件数
check("实测断言数 ≥800（规模下限）", _total_asserts >= 800, str(_total_asserts))
check("中文 README 断言数与实测一致",
      f'{_total_asserts} 项正式断言全过' in _zh,
      [m.group(0) for m in re.finditer(r'\d+ 项正式断言全过', _zh)])
check("英文 README 断言数与实测一致",
      f'{_total_asserts} formal assertions pass' in _en,
      [m.group(0) for m in re.finditer(r'\d+ formal assertions pass', _en)])
check("中文 README 测试文件数与实测一致",
      f'（{_n_test_files} 个测试文件）' in _zh,
      [m.group(0) for m in re.finditer(r'（\d+ 个测试文件）', _zh)])
check("英文 README 测试文件数与实测一致",
      f'({_n_test_files} test files)' in _en,
      [m.group(0) for m in re.finditer(r'\(\d+ test files\)', _en)])

# ── ② 工具件数
check("实测工具数 = 注册表长度", _n_tools == len(tools()), str(_n_tools))
check("中文 README 工具数与实测一致（出现即须对）",
      all(m.group(1) == str(_n_tools)
          for m in re.finditer(r'(\d+) 个可调用工具', _zh)),
      [m.group(0) for m in re.finditer(r'\d+ 个可调用工具', _zh)])
check("docs/tool_schema.md 的件数与实测一致",
      f'共 **{_n_tools}** 件工具' in _read('docs/tool_schema.md'),
      [m.group(0) for m in re.finditer(r'共 \*\*\d+\*\* 件工具',
                                       _read('docs/tool_schema.md'))])

# ── ③ demo 步数（README 用圈码 ①…⑳ 列表，中文数字描述步数——两种都得对）
_CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
_CN_NUM = {15: '十五', 16: '十六', 17: '十七', 18: '十八', 19: '十九',
           20: '二十'}


def _circled(n):
    return _CIRCLED[n - 1] if 1 <= n <= len(_CIRCLED) else ''


_last_marker = _circled(_demo_steps)
check("中文 README 的 demo 步数与实测一致（圈码列表有最后一步）",
      bool(_last_marker) and _last_marker in _zh,
      f"实测 {_demo_steps} 步，找 {_last_marker!r}")
check("中文 README 的步数文案与实测一致（中文数字）",
      f'{_CN_NUM.get(_demo_steps, _demo_steps)}步' in _zh,
      [m.group(0) for m in re.finditer(r'[一二三四五六七八九十]+步', _zh)])
_EN_NUM = {15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
           19: 'nineteen', 20: 'twenty'}
check("英文 README 的 demo 步数与实测一致（英文数字）",
      (f'{_EN_NUM.get(_demo_steps, _demo_steps)}-step' in _en
       or f'{_EN_NUM.get(_demo_steps, _demo_steps)} steps' in _en),
      [m.group(0) for m in re.finditer(r'[a-z]+-step\w*|[a-z]+ steps', _en)])
check("demo 步数 ≥19（⑲ 墙的精确地图在位）", _demo_steps >= 19,
      str(_demo_steps))

# ── ④ 场景数与题型覆盖
check("中文 README 场景数与实测一致",
      f'{_n_scenes} 场景' in _zh,
      [m.group(0) for m in re.finditer(r'\d+ 场景', _zh)])
_covered = {s['expect_type'] for s in SCENES}
check("场景覆盖 T1-T12 全 12 题型（README 声称的口径）",
      len(_covered) == 12, f"{sorted(_covered)}")

# ── ⑤ 冷门构件数
check("中文 README 冷门件数与实测一致（六件齐口径）",
      ('六件齐' in _zh and _n_cold == 6) or f'{_n_cold} 件' in _zh,
      f"实测 {_n_cold}: {sorted(_cold)}")

# ── ⑥ 文档文件清单与实物一致
check("门面文件清单都在（README/许可/贡献/安全/模板/CI）",
      all(os.path.exists(os.path.join(_REPO, f)) for f in (
          'docs/mechanisms.md', 'docs/ROADMAP.md', 'docs/tool_schema.md',
          'docs/github_meta.md', 'README.md', 'README.en.md',
          'CHANGELOG.md', 'NOTICE', 'LICENSE', 'run_tests.py',
          'demo.py', 'pyproject.toml', 'CONTRIBUTING.md',
          'CODE_OF_CONDUCT.md', 'SECURITY.md', '.editorconfig',
          '.github/PULL_REQUEST_TEMPLATE.md',
          '.github/ISSUE_TEMPLATE/bug_report.yml',
          '.github/ISSUE_TEMPLATE/feature_request.yml',
          '.github/ISSUE_TEMPLATE/config.yml',
          '.github/workflows/test.yml')),
      '缺文件')
check("pyproject 的 readme 指向真实文件",
      'readme = "README.md"' in _read('pyproject.toml')
      and os.path.exists(os.path.join(_REPO, 'README.md')))

# ── ⑦ 数字口径自洽：README 的断言数不得小于实测（防乐观写小/写大）
_zh_claims = [int(m.group(1)) for m in
              re.finditer(r'(\d+) 项正式断言', _zh)]
check("README 断言声明不多不少（= 实测）",
      all(c == _total_asserts for c in _zh_claims), str(_zh_claims))

print("=" * 60)
print(f"结果: {PASS}/19 通过")
raise SystemExit(0 if PASS == 19 else 1)
