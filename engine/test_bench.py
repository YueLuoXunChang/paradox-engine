# -*- coding: utf-8 -*-
"""
test_bench.py — 正式测试：性能基准与护栏
用例依据：仓库此前零基准（改一处实现不知道是否变慢）；这里是**冒烟级护栏**——
只抓数量级异常，不做严谨 benchmark，也不对外报数。
运行：python engine/test_bench.py
"""
import io
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

import bench  # noqa: E402

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


print("性能基准 · 正式测试")
print("=" * 60)

rows, tmpdir = bench.cases()
check("基准用例齐备（≥5 件代表操作，次数固定）",
      len(rows) >= 5 and all(isinstance(n, int) and n > 0
                             for _, n, _ in rows), str([(n[0][:12], n[1])
                                                        for n in rows]))
names = [r[0] for r in rows]
check("覆盖关键路径（判类 / 五步 / 两个新构件 / 台账写盘）",
      any('classifier' in n for n in names)
      and any('controller' in n for n in names)
      and any('monadic' in n for n in names)
      and any('model_check' in n for n in names)
      and any('session' in n for n in names), str(names))

t0 = time.perf_counter()
for name, n, fn in rows:
    for _ in range(n):
        fn()
elapsed = time.perf_counter() - t0
check("整套基准在护栏内跑完（< 60 秒；超了说明数量级出问题）",
      elapsed < 60, '%.1f 秒' % elapsed)
check("单件操作不超护栏（< 20 秒）", elapsed / len(rows) < 20)

out = subprocess.run([sys.executable, 'bench.py', '--json'], cwd=_REPO,
                     capture_output=True)
try:
    data = json.loads(out.stdout.decode('utf-8'))
    ok = len(data['results']) == len(rows) and data['ms_total'] > 0
except Exception as e:  # noqa: BLE001
    ok, data = False, {'err': str(e)}
check("--json 模式给出结构化结果（脚本/CI 可用）", ok, str(data)[:120])
check("基准自带口径声明（冒烟级、不对外报数）",
      '冒烟级' in bench.__doc__ and '不用于对外报数' in bench.__doc__)
check("基准不往仓库里写文件（只在临时目录）",
      not any(f.startswith('s.json') for f in os.listdir(_REPO)))

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

print("=" * 60)
print(f"结果: {PASS}/7 通过")
raise SystemExit(0 if PASS == 7 else 1)
