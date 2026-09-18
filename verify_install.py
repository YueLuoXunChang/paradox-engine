# -*- coding: utf-8 -*-
"""
verify_install.py — 安装路径端到端验证（README 声称的用法，真装真跑）
=========================================================================
为什么有这个脚本：
    README 写着 `pip install .` 然后 `paradox-engine --text "..."`。这条路径
    可能与源码仓里跑测试**完全不是一回事**——测过才知道。第一次做这个验证就抓到
    三个真问题（见下），所以把它固化成可复现脚本，并接进 CI。

它做什么（全离线，不需要网络）：
    ① 构建 wheel（`pip wheel --no-deps --no-build-isolation`）；
    ② 建临时 venv，`pip install --no-index --no-deps` 装这个 wheel；
    ③ 真跑安装后的 console 命令：--text / --json / --file / --tools；
    ④ 真跑安装后的 import 接入（从别的工作目录）；
    ⑤ 跑随包发布的测试模块（源码仓专属的应诚实跳过，而非假失败）；
    ⑥ 汇总：任一项失败即非零退出。

用法：
    python verify_install.py             # 全跑（约 20-40 秒）
    python verify_install.py --keep      # 保留临时目录（排查用）
    python verify_install.py --skip-tests # 只验 CLI（CI 快速档）

诚实边界：
    - 只验证**本机这套 Python** 的安装路径，不做跨平台保证；
    - 临时 venv 与 wheel 放系统临时目录，跑完清理（--keep 可留）；
    - 不发布、不推送：本脚本只构建并本地安装。

首次验证抓到的真问题（已修，留档防复发）：
    1) `engine/ai/tool_schema_frozen.json` 没进 wheel——setuptools 默认只收 .py，
       装完之后契约自查必然失败 → 已在 pyproject 声明 package-data；
    2) 门面级测试（发布面/文档一致性/打包不变式）在安装环境读不到仓库根，
       直接崩 → 现改用 engine/_layout.in_source_checkout() **诚实跳过**；
    3) 契约测试无条件读 docs/tool_schema.md、无条件取 mtime → 同为源码仓专属，
       现改为存在才读/只对存在的文件比 mtime。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))

try:  # 控制台自愈：Windows GBK 控制台打印 emoji 会崩
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

# 随包发布的测试模块（挑覆盖面广的；名字即 module path）
_TEST_MODULES = [
    'engine.test_cli',
    'engine.ai.test_tools',
    'engine.ai.test_tool_contract',
    'engine.control.test_classifier',
    'engine.control.test_controller',
    'engine.cold.test_agm_revision',
    'engine.classical.test_decidability_map',
    'engine.scenarios.test_scenarios',
    'engine.skeleton.test_mtmp',
]
# 源码仓专属（安装环境应"诚实跳过"，输出 1/1 通过 + 说明）
_SKIP_MODULES = [
    'engine.test_public_face',
    'engine.test_docs_consistency',
    'engine.test_packaging',
]

_FAILS = []
_RESULT_RE = re.compile(r'结果:\s*(\d+)/(\d+)\s*通过')


def _run(cmd, **kw):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True,
                          encoding='utf-8', errors='replace', **kw)


def _step(label, ok, detail=''):
    flag = '✅' if ok else '❌'
    print(f"  {flag} {label}" + (f" — {detail}" if detail else ''))
    if not ok:
        _FAILS.append(label)
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description='安装路径端到端验证')
    ap.add_argument('--keep', action='store_true', help='保留临时目录')
    ap.add_argument('--skip-tests', action='store_true',
                    help='只验 CLI 与 import（CI 快速档）')
    args = ap.parse_args(argv)

    py = sys.executable
    print('=' * 66)
    print('安装路径端到端验证（构建 wheel → 临时 venv 安装 → 真跑）')
    print('=' * 66)
    tmp = tempfile.mkdtemp(prefix='pe_install_')
    dist = os.path.join(tmp, 'dist')
    venv = os.path.join(tmp, 'venv')
    try:
        # ① 构建 wheel（--no-build-isolation：不联网取构建依赖）
        print('① 构建 wheel')
        r = _run([py, '-m', 'pip', 'wheel', _HERE, '--no-deps',
                  '--no-build-isolation', '-w', dist], cwd=tmp)
        whls = ([f for f in os.listdir(dist) if f.endswith('.whl')]
                if os.path.isdir(dist) else [])
        if not _step('构建 wheel', r.returncode == 0 and whls,
                     r.stdout.strip().splitlines()[-1] if r.stdout else ''):
            print(r.stdout[-800:])
            return 1
        whl = os.path.join(dist, whls[0])
        print(f"     → {whls[0]}（{os.path.getsize(whl)} 字节）")

        # ①b wheel 内容自查：契约快照必须随包（曾漏）
        import zipfile
        names = zipfile.ZipFile(whl).namelist()
        _step('wheel 含工具契约快照 engine/ai/tool_schema_frozen.json',
              'engine/ai/tool_schema_frozen.json' in names)
        _step('wheel 含控制台自愈 engine/_console.py',
              'engine/_console.py' in names)
        _step('wheel 未误收构建产物', not any(
            n.startswith(('build/', 'dist/')) or '__pycache__' in n
            for n in names))

        # ② 临时 venv + 离线安装
        print('② 临时 venv 离线安装')
        r = _run([py, '-m', 'venv', venv])
        if not _step('创建 venv', r.returncode == 0):
            print(r.stdout[-500:])
            return 1
        vpy = os.path.join(venv, 'Scripts' if os.name == 'nt' else 'bin',
                           'python.exe' if os.name == 'nt' else 'python')
        vexe = os.path.join(venv, 'Scripts' if os.name == 'nt' else 'bin',
                            'paradox-engine' + ('.exe' if os.name == 'nt'
                                                else ''))
        r = _run([vpy, '-m', 'pip', 'install', '--no-index', '--no-deps',
                  '--quiet', whl], cwd=tmp)
        _step('安装 wheel（离线）', r.returncode == 0,
              r.stdout.strip()[-200:] if r.returncode else '')
        _step('console 脚本已生成', os.path.exists(vexe))

        # ③ console 命令（从别的工作目录跑，Windows 默认 GBK 控制台）
        print('③ console 命令真跑（工作目录=临时目录，不设 PYTHONIOENCODING）')
        env = {k: v for k, v in os.environ.items()
               if k != 'PYTHONIOENCODING'}
        r = subprocess.run([vexe, '--text', '产品既要快又要稳'],
                           cwd=tmp, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True,
                           encoding='utf-8', errors='replace', env=env)
        _step('--text 中文报告（GBK 控制台不崩）',
              r.returncode == 0 and '【类型】' in r.stdout,
              f"exit={r.returncode}")
        r = subprocess.run([vexe, '--json', '--text', '这句话是假的'],
                           cwd=tmp, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True,
                           encoding='utf-8', errors='replace', env=env)
        ok_json = False
        try:
            data = json.loads(r.stdout)
            ok_json = r.returncode == 0 and 'main_type' in data
        except Exception:  # noqa: BLE001
            ok_json = False
        _step('--json 输出可解析', ok_json, f"exit={r.returncode}")
        r = subprocess.run([vexe, '--tools'], cwd=tmp, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True,
                           encoding='utf-8', errors='replace', env=env)
        m = re.search(r'可用工具 (\d+) 件', r.stdout or '')
        _step('--tools 列出工具', r.returncode == 0 and bool(m),
              f"{m.group(1) if m else '?'} 件")
        txt = os.path.join(tmp, 'in.txt')
        with open(txt, 'w', encoding='utf-8') as fh:
            fh.write('要自由还是要秩序，能不能兼得')
        r = subprocess.run([vexe, '--file', txt], cwd=tmp,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True,
                           encoding='utf-8', errors='replace', env=env)
        _step('--file 读文件', r.returncode == 0, f"exit={r.returncode}")

        # ④ import 接入（从别的工作目录）
        print('④ import 接入（工作目录=临时目录）')
        r = _run([vpy, '-c',
                  "from engine.control.controller import run;"
                  "r=run({'text':'既要快又要稳','structured':"
                  "{'wA':5,'wNotA':5,'A':'要快','B':'要稳'}});"
                  "print('OK', r['classification']['main_type'])"], cwd=tmp)
        _step('import engine 可用', 'OK' in (r.stdout or ''),
              (r.stdout or '').strip().splitlines()[-1] if r.stdout else '')
        r = _run([vpy, '-m', 'engine.ai.freeze_tool_schema', '--check'],
                 cwd=tmp)
        _step('安装后工具契约自查一致', r.returncode == 0,
              (r.stdout or '').strip().splitlines()[-1] if r.stdout else '')

        # ⑤ 随包测试
        if not args.skip_tests:
            print('⑤ 随包测试（安装环境）')
            for mod in _TEST_MODULES:
                r = _run([vpy, '-m', mod], cwd=tmp)
                ms = list(_RESULT_RE.finditer(r.stdout or ''))
                ok = r.returncode == 0 and ms and \
                    ms[-1].group(1) == ms[-1].group(2)
                _step(f'{mod}', bool(ok),
                      ms[-1].group(0) if ms else f'exit={r.returncode}')
            for mod in _SKIP_MODULES:
                r = _run([vpy, '-m', mod], cwd=tmp)
                skipped = '跳过' in (r.stdout or '')
                _step(f'{mod}（源码仓专属，应诚实跳过）',
                      r.returncode == 0 and skipped, 'ok' if skipped else
                      f'exit={r.returncode}')
    finally:
        if args.keep:
            print(f'（临时目录保留：{tmp}）')
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print('=' * 66)
    if _FAILS:
        print(f'安装路径验证：{len(_FAILS)} 项失败 → {_FAILS}')
        return 1
    print('安装路径验证：全部通过 ✅（README 声称的 pip 安装用法可用）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
