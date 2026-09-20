# -*- coding: utf-8 -*-
"""
test_selftests.py — 正式测试：每个构件的自测（`python engine/<层>/<名>.py`）真能跑过
==============================================================================
为什么有它：README 明写着「每个构件自包含：`python engine/<层>/<名>.py` 跑自测」——
可 `run_tests.py` **只发现 `test_*.py`**，构件里的自测**没有任何东西守着**：
哪天改坏一个构件、自测炸了，全量回归照样全绿，而文档却叫用户去跑那条命令。

本文件把每个带 `__main__` 的构件自测**逐个真跑一遍**（子进程，独立解释器），
全部退出码 0 才算过；顺带卡住三条：发现的个数下限（防发现规则悄悄失效）、
跳过清单只许有 CLI 入口（`engine/cli.py` 的 `__main__` 要参数，不是自测）、
总耗时上限（防某个自测变慢拖垮回归）。

诚实边界：
    - 只验「自测跑得通」，不验自测**测得对不对**——那是各构件正式测试的活；
    - 跳过清单是**白名单**：除 `engine/cli.py` 外多一个都要报出来。

运行：python engine/test_selftests.py
"""
import io
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

PASS = 0
try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

# 跳过白名单：CLI 入口的 __main__ 是命令行入口（要 --text/--file 等参数），不是自测
_SKIP = {'engine/cli.py'}
# 单跑超时（秒）——自测都是秒级，超了说明卡住了
_TIMEOUT = 120
# 总耗时上限（秒）——防止某个自测变慢把回归拖垮
_TOTAL_LIMIT = 120


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


def discover():
    """找出所有带 __main__ 的构件（与 run_tests.py 的发现口径互不覆盖）。"""
    out = []
    for dp, dn, fn in os.walk(_HERE):
        dn[:] = [d for d in dn if d not in ('__pycache__', 'build')]
        for f in fn:
            if not f.endswith('.py') or f.startswith(('test_', '_')):
                continue
            if f == '__init__.py':
                continue
            p = os.path.join(dp, f)
            src = io.open(p, encoding='utf-8', errors='replace').read()
            if '\nif __name__ ==' in src or src.startswith('if __name__ =='):
                rel = os.path.relpath(p, _REPO).replace('\\', '/')
                out.append((rel, p))
    return sorted(out)


def main():
    print('构件自测 · 正式测试')
    print('=' * 62)
    selftests = discover()
    print(f'  实测：带 __main__ 自测的构件 {len(selftests)} 个')

    check('带自测的构件个数 ≥40（发现规则没悄悄失效）',
          len(selftests) >= 40, len(selftests))
    found = {rel for rel, _ in selftests}
    check('跳过清单只含确实存在的 CLI 入口（白名单不许偷偷变长）',
          _SKIP <= found and len(_SKIP) == 1, sorted(_SKIP ^ found)[:4])
    for must in ('engine/cold/description_logic.py',
                 'engine/cold/interval_algebra.py',
                 'engine/classical/presburger.py'):
        check(f'关键构件的自测在清单里：{must}', must in found)

    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    bad, silent, t0 = [], [], time.time()
    for rel, p in selftests:
        if rel in _SKIP:
            continue
        try:
            r = subprocess.run([sys.executable, p], cwd=_REPO,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace',
                               env=env, timeout=_TIMEOUT)
        except subprocess.TimeoutExpired:
            bad.append((rel, '超时 %ds' % _TIMEOUT))
            continue
        if r.returncode != 0:
            tail = (r.stdout or '').strip().split('\n')
            bad.append((rel, ' | '.join(tail[-2:])[:160]))
        elif not (r.stdout or '').strip():
            silent.append(rel)
    cost = time.time() - t0
    check(f'{len(selftests) - len(_SKIP)} 个构件自测全部退出码 0（真跑，不是看有没有）',
          not bad, bad[:4])
    check('每个自测都有输出（防"空跑也算过"）', not silent, silent[:4])
    check(f'自测总耗时 ≤{_TOTAL_LIMIT} 秒（实测 {cost:.1f} 秒）',
          cost <= _TOTAL_LIMIT, '%.1f 秒' % cost)

    print('=' * 62)
    print(f"结果: {PASS}/8 通过")
    raise SystemExit(0 if PASS == 8 else 1)


if __name__ == '__main__':
    main()
