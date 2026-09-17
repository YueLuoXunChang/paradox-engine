# -*- coding: utf-8 -*-
"""
test_packaging.py — 正式测试：打包与工程不变式（防"踩过一次的坑"复发）
=======================================================================
为什么有这个文件（每条都对应一次真实踩坑）：
  1) **跨项目包名撞车**：本机另一个项目（内部引擎项目）以 editable 装进全局
     Python 且顶层包名也是 `engine` —— 脚本方式运行时 `import engine.*` 会
     解析到**别人的代码**，同名构件被静默误用（比崩溃更危险）。守则：任何
     `import engine.*` 的模块必须在文件内先做 sys.path 引导（钉本仓库根）。
  2) **路由画饼**：ROUTE 里写了构件名、执行层却没有适配器（只能报"未实现"）。
     守则：ROUTE 出现的构件名必须在 ADAPTER_SPECS 里有适配器（见 test_controller）。
  3) **打包漏子包**：pyproject 的 packages 列表若漏了新子包，pip 装出来就
     少模块。守则：engine 下每个含 .py 的目录都得在 packages 列表里。
  4) **控制台编码**：CLI/demo 在 GBK 控制台崩（emoji）→ 入口必须自愈编码。
运行：python engine/test_packaging.py
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


def _py_files(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('__pycache__', 'build')]
        for f in fn:
            if f.endswith('.py'):
                out.append(os.path.join(dp, f))
    return out


print("打包与工程不变式 · 正式测试")
print("=" * 60)

_all = _py_files(_HERE)
print(f"  （扫描 engine/ 下 {len(_all)} 个 .py）")

# ── 用例1：路径引导守则（防跨项目包名撞车）
# 判据：**真代码里**出现 `import engine.*`（用 ast 判，文档串/注释不算）的
# 文件，必须同时把 _REPO 插进 sys.path；否则脚本方式运行可能加载到别人的引擎
def _engine_imports(path):
    import ast
    tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == 'engine' or a.name.startswith('engine.'):
                    return True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            if mod == 'engine' or mod.startswith('engine.'):
                return True
    return False


_needs_boot = []
_boot_ok = []
for p in _all:
    if not _engine_imports(p):
        continue
    src = open(p, encoding='utf-8').read()
    _needs_boot.append(os.path.relpath(p, _REPO))
    if 'sys.path' in src and ('_REPO' in src or '_HERE' in src):
        _boot_ok.append(os.path.relpath(p, _REPO))
check("引用 engine.* 的模块都做了 sys.path 引导（防包名撞车）",
      len(_needs_boot) == len(_boot_ok),
      f"缺引导: {sorted(set(_needs_boot) - set(_boot_ok))}")
check("受守则覆盖的模块数 ≥10（守则真的在管一大片）",
      len(_needs_boot) >= 10, str(len(_needs_boot)))

# ── 用例2：打包完整性（pyproject packages 覆盖 engine 下所有子包）
pyp = open(os.path.join(_REPO, 'pyproject.toml'), encoding='utf-8').read()
m = re.search(r'packages\s*=\s*\[(.*?)\]', pyp, re.S)
check("pyproject 有显式 packages 列表", bool(m), pyp[:200])
declared = set(re.findall(r'"([^"]+)"', m.group(1)))
_dirs = set()
for dp, dn, fn in os.walk(_HERE):
    dn[:] = [d for d in dn if d not in ('__pycache__', 'build')]
    if any(f.endswith('.py') for f in fn):
        rel = os.path.relpath(dp, _REPO).replace('\\', '.')
        _dirs.add(rel)
check("engine 下每个含 .py 的目录都在 packages 里",
      _dirs <= declared, f"漏: {sorted(_dirs - declared)}")
check("packages 无多余条目（与目录一致）",
      declared <= _dirs, f"多: {sorted(declared - _dirs)}")
check("packages 声明 ≥7 个子包", len(declared) >= 7, str(sorted(declared)))

# ── 用例3：console 入口与控制台自愈
check("console script 指向 engine.cli:main",
      'paradox-engine = "engine.cli:main"' in pyp)
from engine._console import ensure_utf8_console  # noqa: E402
check("控制台自愈函数可导入并返回布尔",
      isinstance(ensure_utf8_console(), bool))
_cli = open(os.path.join(_HERE, 'cli.py'), encoding='utf-8').read()
check("CLI 入口调用控制台自愈", 'ensure_utf8_console()' in _cli)
_demo = open(os.path.join(_REPO, 'demo.py'), encoding='utf-8').read()
check("demo 入口调用控制台自愈", 'ensure_utf8_console()' in _demo)

# 每个可独立运行的文件（构件自测含 __main__、测试文件模块级执行）都要自带
# 控制台自愈——否则 Windows GBK 控制台一跑就 UnicodeEncodeError（实测曾中招：
# 31/33 入口 + 31 个测试文件）
def _has_console_guard(src):
    return (".reconfigure(encoding='utf-8')" in src
            or 'ensure_utf8_console(' in src)


_no_guard = []
_n_covered = 0
for p in _all:
    name = os.path.basename(p)
    src = open(p, encoding='utf-8').read()
    if '__main__' not in src and not name.startswith('test_'):
        continue
    _n_covered += 1
    if not _has_console_guard(src):
        _no_guard.append(os.path.relpath(p, _REPO))
check("可独立运行的入口/测试文件都带控制台自愈（GBK 不崩）", not _no_guard,
      f"缺自愈: {sorted(_no_guard)}")
check("自带自愈的文件数 ≥60（入口 + 测试全覆盖）",
      _n_covered - len(_no_guard) >= 60, str(_n_covered - len(_no_guard)))

# ── 用例4：回归入口与 CI（一条命令 + 同一套标准）
check("run_tests.py 存在（全量回归入口）",
      os.path.exists(os.path.join(_REPO, 'run_tests.py')))
_rt = open(os.path.join(_REPO, 'run_tests.py'), encoding='utf-8').read()
check("回归入口在缺失结果行时判失败（沉默通过不算通过）",
      'ok = (proc.returncode == 0 and passed == total)' in _rt)
_wf = os.path.join(_REPO, '.github', 'workflows', 'test.yml')
check("CI 工作流存在", os.path.exists(_wf))
_wfs = open(_wf, encoding='utf-8').read() if os.path.exists(_wf) else ''
check("CI 跑同一入口 run_tests.py", 'python run_tests.py' in _wfs)
check("CI 覆盖 3.9 与 3.12（requires-python 下界）",
      '"3.9"' in _wfs and '"3.12"' in _wfs, _wfs[:200])

# ── 用例5：死命令——门面文件不出现版本号
_face = ['README.md', 'README.en.md', 'pyproject.toml']
_bad_ver = []
for f in _face:
    p = os.path.join(_REPO, f)
    src = open(p, encoding='utf-8').read()
    # 允许 Python 版本（3.9/3.12 等）与 "v0.1.0 起步" 这类"真发布才打"的说明
    for mm in re.finditer(r'版本[:：]\s*v?\d+\.\d+\.\d+', src):
        _bad_ver.append(f'{f}: {mm.group(0)}')
check("门面文件无「版本：vX.Y.Z」这类乱标（死命令）", not _bad_ver,
      str(_bad_ver))
check("engine/__init__.py 的 __version__ 为 0.1.0（未发布基线）",
      __import__('engine').__version__ == '0.1.0')

print("=" * 60)
print(f"结果: {PASS}/19 通过")
raise SystemExit(0 if PASS == 19 else 1)
