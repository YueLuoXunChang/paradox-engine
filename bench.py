# -*- coding: utf-8 -*-
"""
bench.py — 性能基准（记录 + 护栏）
================================================================
为什么有它：仓库此前**零基准**——大材料跑得慢没数，改一处实现也不知道是否变慢。
本脚本量几件代表操作，打印表格（可用 --json），并给一个**宽松**的总时长护栏。

口径（写在前面，免得被误读）：
    - 这是**冒烟级基准**，不是严谨 benchmark：单机单次、不剔噪、不做统计检验；
    - 数值会随机器波动，**只用来发现数量级变化**（比如慢了十倍），不用于对外报数；
    - 用固定输入与固定次数，跑两次口径一致（可复现）。

跑法：python bench.py            # 人看的表格
      python bench.py --json     # 结构化（CI/脚本用）
"""

import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

TEXT = '产品既要三周上线抢占市场，又要十二周合规审查，销售和研发各执一词'
T5 = '原来以为要十二周，现在发现三周就行'

MUTEX = {'states': ['n1n2', 'c1n2', 'n1c2'],
         'transitions': [['n1n2', 'c1n2'], ['n1n2', 'n1c2'],
                         ['c1n2', 'n1n2'], ['n1c2', 'n1n2']],
         'labels': {'n1n2': [], 'c1n2': ['c1'], 'n1c2': ['c2']},
         'init': ['n1n2']}


def cases():
    """返回 [(名称, 次数, 可调用)]——名称与次数固定，保证两次跑口径一致。"""
    from engine.control.classifier import run as cl
    from engine.control.controller import run as ctl
    from engine.classical.monadic_fol import run as mono
    from engine.classical.model_check import run as mc
    import io as _io
    import tempfile
    from engine.control.session import run as sess

    d = tempfile.mkdtemp(prefix='pe_bench_')
    spath = os.path.join(d, 's.json')

    def session_flow():
        sess({'action': 'add', 'path': spath, 'text': TEXT})

    out = [
        ('classifier.run（判类+复杂度+路由）', 200, lambda: cl({'text': TEXT})),
        ('controller.run（五步流水线）', 40, lambda: ctl({'text': TEXT})),
        ('monadic_fol.run（域展开判定）', 10,
         lambda: mono({'formula': '∀x (P(x) ∧ Q(x)) ↔ (∀x P(x) ∧ ∀x Q(x))'})),
        ('model_check.run（CTL 标记）', 20,
         lambda: mc(dict(MUTEX, formula='AG !(c1 & c2)'))),
        ('session.add（台账写盘）', 20, session_flow),
    ]
    return out, d


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rows, tmpdir = cases()
    results = []
    t_all = time.perf_counter()
    for name, n, fn in rows:
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        ms = (time.perf_counter() - t0) * 1000
        results.append({'name': name, 'times': n, 'ms_total': round(ms, 2),
                        'ms_each': round(ms / n, 4)})
    total = (time.perf_counter() - t_all) * 1000
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    if '--json' in argv:
        print(json.dumps({'results': results, 'ms_total': round(total, 2)},
                         ensure_ascii=False, indent=2))
        return 0
    print('性能基准（冒烟级：单机单次、不剔噪，只看数量级）')
    print('=' * 58)
    print('%-38s %5s %10s' % ('操作', '次数', '每次(ms)'))
    for r in results:
        print('%-38s %5d %10.4f' % (r['name'], r['times'], r['ms_each']))
    print('-' * 58)
    print('总计 %.1f ms' % total)
    print('说明：数值随机器波动，用于发现数量级变化，不用于对外报数。')
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # Windows GBK 控制台自愈
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
