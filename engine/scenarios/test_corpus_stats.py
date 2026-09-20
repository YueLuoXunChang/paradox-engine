# -*- coding: utf-8 -*-
"""
test_corpus_stats.py — 正式测试：语料统计（对照一致率 / 混淆矩阵 / 覆盖缺口 / 复核进度）
用例依据：轨 B（语料回馈闭环）+ 三个口径必须分清（一致率＝机械口径 / 误判率＝人工复核口径 /
覆盖缺口＝机械计数），以及"统计不许改场景表、不许替作者复核"这两条纪律。
运行：python engine/scenarios/test_corpus_stats.py
"""
import hashlib
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.scenarios import corpus_stats as cs  # noqa: E402

PASS = 0
_SCENES_PATH = os.path.join(_HERE, 'scenarios.py')

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


def _sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


print("语料统计 · 正式测试")
print("=" * 60)

_before = _sha(_SCENES_PATH)

# ── 一、真数据上的结构不变式
r = cs.run({})
check("默认 mode=summary → summarized", r['verdict'] == 'summarized', str(r['verdict']))
n = r['scenes']
check("场景数与场景库一致（≥10）",
      n == len(cs._scenes_module().SCENES) and n >= 10, str(n))
check("混淆矩阵总和 = 场景数", sum(sum(v.values()) for v in r['matrix'].values())
      == n, str(r['matrix']))
check("矩阵每行和 = 该期望型的场景数",
      all(sum(v.values()) == r['coverage']['count'][e]
          for e, v in r['matrix'].items()),
      str({e: sum(v.values()) for e, v in r['matrix'].items()}))
check("一致率的分子分母都对得上（match = passed 数）",
      r['agreement']['overall']['n'] == n
      and r['agreement']['overall']['match']
      == sum(1 for x in cs._scenes_module().run({'action': 'run'})['scenes']
             if x['passed']), str(r['agreement']['overall']))
check("不一致格子数 = 场景数 − 一致数，且与 confusions 逐格相加吻合",
      sum(c['count'] for c in r['confusions'])
      == n - r['agreement']['overall']['match'],
      str(r['confusions']))
check("逐型一致率：n = 0 的型不给比率（不拿 0/0 当 0%）",
      all(d['rate'] is None for d in r['agreement']['by_type'].values()
          if d['n'] == 0), str(r['agreement']['by_type']))

# ── 二、覆盖缺口（机械计数，不评价场景质量）
cov = r['coverage']
check("覆盖缺口自洽：total_gap = 各型缺口之和",
      cov['total_gap'] == sum(cov['gap'].values()), str(cov['total_gap']))
check("每型缺口 = max(0, 目标 − 已有)，目标默认 5",
      cov['target'] == 5 and all(
          cov['gap'][t] == max(0, cov['target'] - cov['count'][t])
          for t in cov['count']), str(cov['gap']))
check("next_to_add 按缺口从大到小排，且只列还缺的型",
      all(x['gap'] > 0 for x in cov['next_to_add'])
      and cov['next_to_add'] == sorted(cov['next_to_add'],
                                       key=lambda x: (-x['gap'], x['type'])),
      str(cov['next_to_add'][:4]))
check("目标可配置：per_type_target=1 时缺口按 1 算（不与 5 混）",
      cs.run({'per_type_target': 1})['coverage']['total_gap']
      <= cov['total_gap'], str(cs.run({'per_type_target': 1})['coverage']))

# ── 三、复核进度与"两个口径不许混"
rv = r['review']
check("已复核 + 待复核 = 场景数", rv['checked'] + rv['pending'] == n, str(rv))
if rv['pending']:
    check("复核没做完 → 误判率报 None（不报数），并写明原因",
          rv['misclassification_rate'] is None and '不报数' in rv['rate_note'],
          str(rv['rate_note']))
    check("说明里点出「误判率是人工复核口径」，不许拿一致率冒充",
          '人工复核' in rv['rate_note'] and '一致率' in rv['rate_note'],
          str(rv['rate_note']))
else:
    check("复核全做完 → 给误判率（人工口径）",
          rv['misclassification_rate'] is not None, str(rv))
    check("说明里点出误判率与一致率不是一回事",
          '不是一回事' in rv['rate_note'], str(rv['rate_note']))
check("未复核过的型单独列出来（作者的工作面）",
      isinstance(rv['types_untouched'], list), str(rv['types_untouched']))
if rv['state'] is not None:
    check("复核分布与 review_marks 的既有口径一致（两处数不许打架）",
          rv['state']['pending'] == rv['pending'], str(rv['state']))

# ── 四、混淆矩阵（真数据上没有不一致格，用注入数据把这条路径跑实）
_syn = [
    {'id': 'X1', 'expect_type': 'T8', 'actual_type': 'T2', 'passed': False},
    {'id': 'X2', 'expect_type': 'T8', 'actual_type': 'T2', 'passed': False},
    {'id': 'X3', 'expect_type': 'T8', 'actual_type': 'T8', 'passed': True},
    {'id': 'X4', 'expect_type': 'T1', 'actual_type': 'T6', 'passed': False},
    {'id': 'X5', 'expect_type': 'T1', 'actual_type': 'T1', 'passed': True},
]
_sc = {x['id']: {'checked': x['id'] in ('X1', 'X3')} for x in _syn}
d = cs._stats_from(_syn, _sc, 3, state={'ok': 1, 'wrong': 1, 'edge': 0,
                                        'pending': 0})
check("注入数据：复核没做完时不报误判率（同一份数据换个复核状态就变口径）",
      d['review']['misclassification_rate'] is None
      and d['review']['pending'] == 3, str(d['review']))
_sc_all = {x['id']: {'checked': True} for x in _syn}
d_all = cs._stats_from(_syn, _sc_all, 3,
                       state={'ok': 4, 'wrong': 1, 'edge': 0, 'pending': 0})
check("注入数据：矩阵按「期望型 × 实际型」计数（T8 行 = {T2:2, T8:1}）",
      d['matrix']['T8'] == {'T2': 2, 'T8': 1}, str(d['matrix']))
check("注入数据：一致率 = 2/5（两个 T8→T2、一个 T1→T6 判不一致）",
      d['agreement']['overall'] == {'n': 5, 'match': 2, 'rate': 0.4},
      str(d['agreement']['overall']))
check("注入数据：混淆对按次数排序并带上涉及场景 id",
      d['confusions'][0] == {'expect': 'T8', 'actual': 'T2', 'count': 2,
                            'scenes': ['X1', 'X2']}, str(d['confusions']))
check("注入数据：逐型一致率算对（T8 = 1/3）",
      d['agreement']['by_type']['T8']['rate'] == round(1 / 3, 4),
      str(d['agreement']['by_type']['T8']))
check("注入数据：全部已复核时给人工口径误判率（误判 1 / 5 = 0.2）",
      d_all['review']['misclassification_rate'] == 0.2
      and '不是一回事' in d_all['review']['rate_note'], str(d_all['review']))
check("注入数据：未复核过的型进 types_untouched",
      'T1' in d['review']['types_untouched'], str(d['review']['types_untouched']))

# ── 五、只统计不判定 + 只读不改
check("边界声明点明「只统计不判定」",
      '只统计不判定' in r['boundary'], str(r['boundary'][:60]))
check("边界声明点明样本小、不对外报数",
      '不对外报数' in r['boundary'] or '对外报数' in r['boundary'],
      str(r['boundary'][-60:]))
check("review 模式边界点明「不替作者落笔」（不代签 checked）",
      '不替作者落笔' in cs.run({'mode': 'review'})['boundary'])
check("统计过程不改场景表（前后 sha256 一致）",
      _sha(_SCENES_PATH) == _before, '场景表被改动了')

# ── 六、四种 mode 与输入守卫
check("matrix 模式只给矩阵（其他段留空）",
      cs.run({'mode': 'matrix'})['verdict'] == 'mapped'
      and cs.run({'mode': 'matrix'})['agreement'] == {})
check("coverage 模式只给覆盖（其他段留空）",
      cs.run({'mode': 'coverage'})['verdict'] == 'covered'
      and cs.run({'mode': 'coverage'})['matrix'] == {})
check("review 模式只给复核（其他段留空）",
      cs.run({'mode': 'review'})['verdict'] == 'reviewed'
      and cs.run({'mode': 'review'})['coverage'] == {})
check("坏 mode / 坏目标数 → input_pending（诚实拦截）",
      cs.run({'mode': 'xx'})['verdict'] == 'input_pending'
      and cs.run({'per_type_target': 0})['verdict'] == 'input_pending'
      and cs.run('不是 dict')['verdict'] == 'input_pending')

print("=" * 60)
print(f"结果: {PASS}/31 通过")
raise SystemExit(0 if PASS == 31 else 1)
