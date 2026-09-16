# -*- coding: utf-8 -*-
"""
run_tests.py — 全量回归入口（一条命令跑遍全部正式测试）
============================================================
用法:
    python run_tests.py             # 跑全部 engine/**/test_*.py，汇总断言数
    python run_tests.py --quiet     # 只打失败与合计
    python run_tests.py --list      # 只列测试文件

退出码: 全绿 0；任一文件失败 1（CI 直接用）。

诚实边界:
    - 本脚本只做**发现 + 运行 + 汇总**——每个文件的通过线由文件自身声明
      （文件末行 `结果: N/M 通过`），汇总层不替它判定，也不吞掉失败；
    - 找不到 `结果:` 行的文件按**失败**计（沉默通过不算通过）；
    - 输出编码强制 UTF-8（构件自测含 emoji，GBK 控制台会炸）。
"""

import os
import re
import subprocess
import sys

# 自愈编码：构件自测含 emoji，GBK 控制台（Windows 默认）直接 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001——老 Python/重定向流不支持就算了
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
_RESULT_RE = re.compile(r'结果:\s*(\d+)/(\d+)\s*通过')


def discover(root=None):
    """发现全部正式测试文件（engine/**/test_*.py；跳过缓存与构建产物）。"""
    root = root or os.path.join(_HERE, 'engine')
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ('__pycache__', 'build', '.git')]
        for fn in sorted(filenames):
            if fn.startswith('test_') and fn.endswith('.py'):
                found.append(os.path.join(dirpath, fn))
    return sorted(found)


def run_one(path):
    """跑一个测试文件。返回 (passed, total, ok, tail)——ok=False 表示失败。"""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, path], cwd=_HERE, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace')
    out = proc.stdout or ''
    m = None
    for m in _RESULT_RE.finditer(out):
        pass
    if m is None:
        return 0, 0, False, out.strip().splitlines()[-6:]
    passed, total = int(m.group(1)), int(m.group(2))
    ok = (proc.returncode == 0 and passed == total)
    tail = [] if ok else out.strip().splitlines()[-10:]
    return passed, total, ok, tail


def main(argv):
    quiet = '--quiet' in argv or '-q' in argv
    files = discover()
    if '--list' in argv:
        for f in files:
            print(os.path.relpath(f, _HERE))
        print(f'共 {len(files)} 个测试文件')
        return 0
    if not files:
        print('未发现测试文件——诚实报告，不假装通过')
        return 1

    total_p = total_d = 0
    failures = []
    for f in files:
        rel = os.path.relpath(f, _HERE)
        passed, denom, ok, tail = run_one(f)
        total_p += passed
        total_d += denom
        if not quiet:
            flag = '✅' if ok else '❌'
            print(f'  {flag} {rel:<48} {passed}/{denom}')
        if not ok:
            failures.append((rel, passed, denom, tail))

    print('=' * 66)
    print(f'测试文件 {len(files)} 个 · 断言 {total_p}/{total_d} 通过')
    if failures:
        print(f'失败 {len(failures)} 个文件：')
        for rel, passed, denom, tail in failures:
            print(f'  ❌ {rel}（{passed}/{denom}）')
            for line in tail:
                print(f'      {line}')
        return 1
    print('全绿 ✅')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
