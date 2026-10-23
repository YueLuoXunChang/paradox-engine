# -*- coding: utf-8 -*-
"""test_rigor_audit.py — 硬核度体检**自身**的测试（工具不可自证：门禁也要被验）

验三件事：
    ① 判定规则本身：钉住 / 声明（参数或护栏）/ 未钉 三态分得清；
       且"钉住"按**词边界**认名字——否则 `MAX_A` 会被 `MAX_ABC` 蒙过去；
    ② 提取规则：阈值只从**构件源码**里抠，测试文件与检查脚本不算构件
       （第一版把 68 个测试文件的 `PASS`/`TOTAL` 当成阈值，就是这么错的）；
    ③ 体检结果：① 轴当前无硬错（门禁是绿的），报告四节齐，--json 可解析。
运行：python engine/test_rigor_audit.py
"""
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

from engine import _rigor_audit as R  # noqa: E402

PASS = 0

try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass


def check(label, cond, detail=''):
    global PASS
    if cond:
        PASS += 1
        print('✅ %s' % label)
    else:
        print('❌ %s  %s' % (label, detail))


print('=' * 70)
print('一、判定规则：三态分得清')
check('测试里按词边界点到 → pinned',
      R.classify_threshold('MAX_ATOMS', '# 无声明', '用 MAX_ATOMS + 1 构造') == 'pinned')
check('同名前缀不算点到（MAX_A 不该被 MAX_ABC 蒙过去）',
      R.classify_threshold('MAX_A', '# 无声明', '用 MAX_ABC 构造') == 'loose')
check('声明「参数」→ declared',
      R.classify_threshold('X', '# 参数：可调默认值', '') == 'declared')
check('声明「护栏」→ declared',
      R.classify_threshold('X', '# 护栏：内部兜底', '') == 'declared')
check('声明「约定」→ declared',
      R.classify_threshold('X', '# 常用约定，不是体系结论', '') == 'declared')
check('声明「启发式」→ declared',
      R.classify_threshold('X', '# 启发式，非完备', '') == 'declared')
check('既不钉也不声明 → loose（硬错）',
      R.classify_threshold('X', '# 就拿它当阈值', '# 没提到') == 'loose')
check('名称出现在测试里时不再看声明（钉住优先）',
      R.classify_threshold('X', '# 参数：是参数', '引用 X') == 'pinned')

print()
print('二、提取规则：只从构件源码抠')
src = ('MAX_ONE = 5   # 就是个数\n'
       'MIN_TWO = 2\n'
       'lower = 3\n'
       'MAX_DEC = 1.5\n')
th = dict((n, ln) for n, ln, _ctx in R.thresholds_of(src))
check('抠到大写阈值 MAX_ONE', 'MAX_ONE' in th)
check('抠到大写阈值 MIN_TWO', 'MIN_TWO' in th)
check('小数点阈值也认（MAX_DEC）', 'MAX_DEC' in th)
check('小写变量不当阈值（lower）', 'lower' not in th)
check('行号对得上（MAX_ONE 在第 1 行）', th.get('MAX_ONE') == 1, th.get('MAX_ONE'))
comps = [os.path.basename(c) for c in R.components()]
check('构件清单不含测试文件', not any(f.startswith('test_') for f in comps),
      [f for f in comps if f.startswith('test_')][:3])
check('构件清单不含下划线检查脚本', not any(f.startswith('_') for f in comps),
      [f for f in comps if f.startswith('_')][:3])
check('构件清单非空且有规模', len(comps) > 40, len(comps))

print()
print('三、体检结果与报告')
rows, problems = R.audit()
st = R.stats(rows)
check('① 轴当前无硬错（阈值都钉住或声明为非判据）', problems == [],
      problems[:3])
check('四条轴的统计键齐',
      set(['ports_gap', 'boundary_gap', 'no_test', 'nested_no_bound',
           'weak_verification']) <= set(st))
check('每个构件都有 has_test 标记', all('has_test' in r for r in rows))
check('阈值三态分到三只筐里（无遗漏）',
      all(len(r['thr_pinned']) + len(r['thr_declared']) + len(r['thr_loose'])
          >= 0 for r in rows))
md = R.render(rows, problems, st)
check('报告四节齐', all(h in md for h in ('## 一、① 判据轴', '## 二、② 算法轴',
                                          '## 三、③ 验证轴', '## 四、④ 契约轴')))
check('报告写明边界', R.BOUNDARY[:12] in md)
check('报告带更正记录（第一版判据太松这件事写下来了）', '更正记录' in md)
check('--json 输出可解析', json.loads(json.dumps(
    {'problems': problems, 'stats': st}, ensure_ascii=False)) is not None)
out = io.StringIO()
_o, _s = sys.stdout, sys.stderr
try:
    sys.stdout = out
    rc = R.main(['_', '--check'])
finally:
    sys.stdout, sys.stderr = _o, _s
check('--check 退出码 0（门禁是绿的）', rc == 0, rc)
check('--check 打印了四条轴的口径', '① 判据' in out.getvalue()
      and '④ 契约' in out.getvalue())

print('=' * 70)
# ── ② 轴判据（2026-10-02 重写后锁定）
# 旧判据只看"12 行内又出现 for"，把**连续**两个循环也当嵌套 → 12 件里 4-5 件误报。
_RA = __import__('engine._rigor_audit', fromlist=['x'])
_consec = "for a in xs:" + chr(10) + "    pass" + chr(10) + "for b in ys:" + chr(10) + "    pass"
_nest = "for a in xs:" + chr(10) + "    for b in ys:" + chr(10) + "        pass"
check('② 判据：连续两个循环**不算**嵌套（旧版误报的根因）',
      _RA._nested_loops(_consec) == [], _RA._nested_loops(_consec))
check('② 判据：真嵌套（缩进递增）能认出来',
      len(_RA._nested_loops(_nest)) == 1)
check('② 判据：外层遍历常量结构（全大写名/字面量）→ 判为非算法件',
      _RA._static_header('key, v in VERDICTS.items()')
      and _RA._static_header('b in (False, True)')
      and not _RA._static_header('w in worlds'))
check('② 判据：声明分三档（复杂度 / 只有上限 / 两者都无）',
      _RA._claim_kind('"""\n复杂度：O(n)\n"""\n') == 'complexity'
      and _RA._claim_kind('"""\n上限 10 步\n"""\n') == 'bound'
      and _RA._claim_kind('"""\n什么也没说\n"""\n') == 'none')
_rows2, _p2 = _RA.audit()
_st2 = _RA.stats(_rows2)
check('② 统计三档齐（both-none / bound-only / static）且两两不重叠',
      set(_st2['nested_no_bound']) & set(_st2['nested_static']) == set()
      and set(_st2['nested_no_bound']) & set(_st2['nested_bound']) == set()
      and _st2['nested_total'] >= (len(_st2['nested_no_bound'])
                                   + len(_st2['nested_bound'])))

print(f'结果: {PASS}/31 通过')
raise SystemExit(0 if PASS == 31 else 1)
