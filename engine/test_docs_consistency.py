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
# f-string（`print(f"结果: {PASS}/870 通过")`），源码中没有字面总数，
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

# 2026-09-20 补：一个测试文件里**只许有一条**通过线。
# 起因是两次真事故——插新通过线时忘了删旧行，而下面取的是**最后一次出现**，
# 于是旧数字把新数字盖住（README 的断言数就是这么被误导的）。
# 注意口径：早退路径写 `print("结果: 1/1 通过")`（字面、与 PASS 无关）是**合法**的，
# 隐患只是"两条引用 {PASS} 的通过线"（旧行盖新数字），所以只卡那一种。
_pass_line = re.compile(r'^\s*print\(f?[\'"][^\'"]*结果:[^\'"]*\{PASS\}',
                        re.M)
_dup = []
for p in _test_files:
    _n = len(_pass_line.findall(open(p, encoding='utf-8').read()))
    if _n > 1:
        _dup.append((os.path.relpath(p, _REPO), _n))
check("每个测试文件只有一条 `{PASS}` 通过线（旧行不许留着盖新数字）", not _dup,
      _dup)
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
# ── ④ 目录树完整性：新增引擎模块别忘了登记进 README 中英的结构树
#    （复验时发现：这段新加的 session.py / clue_suggester.py / review_marks.py
#      等模块一个都没进树——数字都同步了，索引却漏了）
def _tree_names(doc):
    names = set()
    for line in _read(doc).split('\n'):
        m = re.search(r'[├└]──\s*([^\s←]+)', line)
        if m:
            names.add(m.group(1).rstrip('/'))
    return names


# 口径：**扫盘**，不数 `git ls-files`——后者看不见未提交的新文件，会出现
# "提交前全绿、提交后才红"的假通过（2026-09-22 真踩过：新构件提交前这门是绿的）。
import subprocess as _sp  # noqa: E402  （后面根白名单判据还要用）
_mods = []
for _dp, _dn, _fn in os.walk(os.path.join(_REPO, 'engine')):
    _dn[:] = [d for d in _dn if d not in ('__pycache__', 'build')]
    for _f in _fn:
        if (not _f.endswith('.py')) or _f.startswith(('test_', '_')) or \
                _f == '__init__.py':
            continue
        _mods.append(os.path.relpath(os.path.join(_dp, _f), _REPO)
                     .replace('\\', '/'))
_mods.sort()
_miss_zh = [f for f in _mods
            if os.path.basename(f) not in _tree_names('README.md')]
_miss_en = [f for f in _mods
            if os.path.basename(f) not in _tree_names('README.en.md')]
check("README 中英目录树都列全引擎模块（新模块别忘登记）",
      not _miss_zh and not _miss_en,
      "中文缺 %s；英文缺 %s" % (_miss_zh, _miss_en))

check("demo 步数 ≥19（⑲ 墙的精确地图在位）", _demo_steps >= 19,
      str(_demo_steps))
# 横幅顺序也必须对：插错位置（比如插到演示中段）时步数照样是 20，
# 光数条数抓不出来——所以这里查升序，最后一步必须是 ⑳
_markers = [l.strip()[8:10] for l in
            _read('demo.py').split('\n') if 'banner("' in l]
check("demo 横幅按 ①→⑳ 升序排列（插错位置会被抓出）",
      _markers == [_circled(i) + " " for i in range(1, _demo_steps + 1)],
      str(_markers))

# ── ④ 场景数与题型覆盖
check("中文 README 场景数与实测一致",
      f'{_n_scenes} 场景' in _zh,
      [m.group(0) for m in re.finditer(r'\d+ 场景', _zh)])
_covered = {s['expect_type'] for s in SCENES}
check("场景覆盖 T1-T12 全 12 题型（README 声称的口径）",
      len(_covered) == 12, f"{sorted(_covered)}")

# ── ⑤ 冷门构件数
_CN_COLD = {6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二'}
check("中文 README 冷门件数与实测一致（第 3 层 N 件齐口径）",
      (f'{_CN_COLD.get(_n_cold, _n_cold)}件齐' in _zh)
      or f'{_n_cold} 件' in _zh,
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

# ── ⑧ 英文 README 的数字也守（此前只有中文那份有守卫，英文漂了没人管）
#    构件数：实测取生成器同一来源（磁盘扫描），与中国那份的口径一致
from engine._components_doc import scan as _comp_scan  # noqa: E402
_n_components = sum(len(v) for v in _comp_scan().values())
_zh_comp = [int(m.group(1)) for m in re.finditer(r'(\d+) 个构件', _zh)]
_en_comp = [int(m.group(1)) for m in re.finditer(r'(\d+) components', _en)]
check("中文 README 的构件数与实测一致",
      bool(_zh_comp) and all(c == _n_components for c in _zh_comp),
      f"实测 {_n_components}，中文 README 写 {_zh_comp}")
check("英文 README 的构件数与实测一致（英文那份也守）",
      bool(_en_comp) and all(c == _n_components for c in _en_comp),
      f"实测 {_n_components}，英文 README 写 {_en_comp}")
_en_tools = [int(m.group(1)) for m in re.finditer(r'(\d+) tool contracts?', _en)]
check("英文 README 的工具数与实测一致",
      bool(_en_tools) and all(c == _n_tools for c in _en_tools),
      f"实测 {_n_tools}，英文 README 写 {_en_tools}")
_en_scenes = [int(m.group(1)) for m in re.finditer(r'(\d+) scenes', _en)]
check("英文 README 的场景数与实测一致",
      bool(_en_scenes) and all(c == _n_scenes for c in _en_scenes),
      f"实测 {_n_scenes}，英文 README 写 {_en_scenes}")

# ── ⑨ 根目录白名单：被跟踪的根文件都得在两份 README 里被提到
#    （没有这条时，仓库根多出一个文件不会被任何东西报出来——真踩过）
_root_files = [f for f in _sp.run(['git', 'ls-files'], cwd=_REPO,
                                  capture_output=True, text=True,
                                  encoding='utf-8').stdout.split()
               if '/' not in f]
_unlisted = [f for f in _root_files if f not in _zh or f not in _en]
check("根目录每个被跟踪的文件都在中英 README 里有交代",
      not _unlisted, f"没交代：{_unlisted}")

print("=" * 60)
print(f"结果: {PASS}/27 通过")
raise SystemExit(0 if PASS == 27 else 1)
