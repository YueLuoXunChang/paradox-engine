# -*- coding: utf-8 -*-
"""
test_default_logic.py — 正式测试：默认逻辑（Reiter 完整不动点）
用例依据：Reiter 1980 的默认理论语义（扩展 = Γ 的不动点）+ 与 agm_revision
里那个"简化版默认推理"的对照（两边各说自己算的是什么）。
运行：python engine/cold/test_default_logic.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.cold.default_logic import MAX_ATOMS, run  # noqa: E402

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


def r(_inputs=None, **kw):
    return run(_inputs if _inputs is not None else kw)


print("默认逻辑（Reiter 完整不动点） · 正式测试")
print("=" * 60)

# ── 一、扩展算得对不对
a = r(facts=['鸟'], defaults=[('鸟', '会飞')])
check("正常默认：鸟 + (鸟:会飞/会飞) → 一个扩展，共同结论含 鸟/会飞",
      a['verdict'] == 'evaluated' and len(a['extensions']) == 1
      and set(a['in_all']) == {'鸟', '会飞'}, str(a['extensions']))

b = r(facts=['鸟', '企鹅'],
      defaults=[('鸟', '会飞'), ('企鹅', '¬会飞')])
check("Reiter 原义：两条默认各管各的 → 两个扩展（歧义，不是 bug）",
      b['verdict'] == 'evaluated' and len(b['extensions']) == 2,
      str(b['verdict']))
check("歧义时两边结论都只是「部分扩展成立」（轻信论而非怀疑论）",
      '会飞' in b['in_some'] and '¬会飞' in b['in_some']
      and '会飞' not in b['in_all'], str((b['in_all'], b['in_some'])))

c = r(facts=['鸟', '企鹅'],
      defaults=[('鸟 ∧ ¬企鹅', '会飞'), ('企鹅', '¬会飞')])
check("例外写进前提（Reiter 的标准写法）→ 唯一扩展，¬会飞 是共同结论",
      c['verdict'] == 'evaluated' and len(c['extensions']) == 1
      and '¬会飞' in c['in_all'] and '会飞' in c['in_none'],
      str((c['verdict'], c['in_all'], c['in_none'])))

d = r(defaults=['⊤ : P / ¬P'])
check("自相拆台的默认 → no_extension（语义结果，不是算不出来）",
      d['verdict'] == 'no_extension' and d['extensions'] == [], str(d['verdict']))

e = r(defaults=['⊤ : P / P'])
check("无前提默认 (: P)/P → 一个扩展，P 成立",
      e['verdict'] == 'evaluated' and len(e['extensions']) == 1
      and 'P' in e['in_all'], str(e['extensions']))

# ── 二、辩护（justification）的两种命运
f = r(facts=['P'], defaults=[('⊤', '¬P', 'Q')])
check("辩护被事实推翻（¬P 遇 P）→ 默认阻断，Q 哪个扩展里都没有",
      f['verdict'] == 'evaluated' and 'Q' in f['in_none']
      and f['default_status'][0]['status'] == 'never',
      str((f['in_none'], f['default_status'])))
g = r(facts=['P'], defaults=[('⊤', 'P', 'Q')])
check("辩护被事实保证（⊤:P/Q 且事实 P）→ 默认照样生效，Q 成立",
      g['verdict'] == 'evaluated' and 'Q' in g['in_all'],
      str((g['verdict'], g['in_all'])))
h = r(facts=['¬C'], defaults=[('C', 'A')])
check("前提不成立 → 默认永不生效（status=never）",
      h['verdict'] == 'evaluated' and h['default_status'][0]['status'] == 'never',
      str(h['default_status']))

# ── 三、扩展数、规则状态、立场之争
i = r(facts=['C'], defaults=[('C', 'A'), ('C', '¬A')])
check("前提相同、结论冲突 → 两个扩展，两条规则都只是「有时生效」",
      i['verdict'] == 'evaluated' and len(i['extensions']) == 2
      and all(s['status'] == 'sometimes' for s in i['default_status']),
      str(i['default_status']))
check("从不共存的规则对进 ambiguous_defaults（立场之争）",
      len(i['ambiguous_defaults']) == 1
      and set(i['ambiguous_defaults'][0]) == {'C : A / A', 'C : ¬A / ¬A'},
      str(i['ambiguous_defaults']))
j = r(facts=['鸟'], defaults=[('鸟', '会飞')])
check("只有一个扩展时规则状态是 always（每条都在生效）",
      j['default_status'][0]['status'] == 'always'
      and j['default_status'][0]['applicable_in'] == [1],
      str(j['default_status']))

# ── 四、query：想问的那句话落在哪一档
k = r(facts=['鸟'], defaults=[('鸟', '会飞')], query='会飞')
l = r(facts=['鸟', '企鹅'],
      defaults=[('鸟', '会飞'), ('企鹅', '¬会飞')], query='会飞')
m_ = r(facts=['鸟'], defaults=[('鸟', '会飞')], query='下雨')
check("query 三档：共同结论 in_all / 只在部分扩展 in_some / 都推不出 in_none",
      k['query_status'] == 'in_all' and l['query_status'] == 'in_some'
      and m_['query_status'] == 'in_none',
      str((k['query_status'], l['query_status'], m_['query_status'])))

# ── 五、四种写法等价（写错了会静默改语义，所以单独钉一条）
n = r(facts=['鸟'], defaults=[('鸟', '会飞')])
o = r(facts=['鸟'], defaults=[('鸟', '会飞', '会飞')])
p = r(facts=['鸟'], defaults=[{'prerequisite': '鸟', 'consequent': '会飞'}])
q = r(facts=['鸟'], defaults=['鸟 : 会飞 / 会飞'])
q2 = r(facts=['鸟'], defaults=['鸟 / 会飞'])
check("四种写法（两句/三句/字典/一行字符串）结果一致",
      all(x['verdict'] == 'evaluated' and x['in_all'] == n['in_all']
          for x in (o, p, q, q2)), str([x['in_all'] for x in (o, p, q, q2)]))
check("⊤ 只能整条用：混在式子中间 → parse_error（不当原子名偷偷用）",
      r(defaults=[('P ∧ ⊤', 'Q')])['verdict'] == 'parse_error')

# ── 六、诚实边界（算不动就说算不动）
check("事实集自相矛盾 → facts_unsatisfiable（不报「有扩展」）",
      r(facts=['P', '¬P'], defaults=[('P', 'Q')])['verdict']
      == 'facts_unsatisfiable')
check("缺 defaults / 形状不对 → input_pending",
      r({})['verdict'] == 'input_pending'
      and r(facts=['P'])['verdict'] == 'input_pending')
check("坏写法（只给一项的元组）→ parse_error",
      r(defaults=[('P',)])['verdict'] == 'parse_error')
check("默认条数超上限 → size_limit；把上限调上去就能跑",
      r(defaults=[('P', 'Q')] * 13)['verdict'] == 'size_limit'
      and r(defaults=[('P', 'Q')] * 13,
            max_defaults=13)['verdict'] == 'evaluated')
check("原子数超真值表上限 → undecided（算不动 ≠ 没有扩展）",
      # 口径锚：边界＝MAX_ATOMS，用常量构造刚好超限的输入
      r(facts=['P%d' % i for i in range(MAX_ATOMS + 1)],
        defaults=[('P0', 'P1')])['verdict'] == 'undecided')

# ── 七、与 agm_revision 那个"简化版"的对照（两边各说自己算的是什么）
from engine.cold.agm_revision import run as agm  # noqa: E402
_simple = agm({'mode': 'default', 'defaults': [('鸟', '会飞')],
               'facts': ['鸟', '企鹅'], 'exceptions': ['企鹅']})
_full = r(facts=['鸟', '企鹅'], defaults=[('鸟', '会飞')])
check("同一输入两种口径都各异：简化版按例外阻断，本构件按 Reiter 原义算扩展",
      _simple['conclusions'][0]['status'] == 'blocked'
      and _full['verdict'] == 'evaluated' and '会飞' in _full['in_all'],
      str((_simple['conclusions'][0]['status'], _full['in_all'])))

# ── 八、输出契约
check("每个扩展都带 derived 与 applicable_defaults；结论带边界声明",
      all('derived' in x and 'applicable_defaults' in x
          for x in n['extensions']) and bool(n['boundary'])
      and n['extensions'][0]['applicable_defaults'] == ['鸟 : 会飞 / 会飞'],
      str(n['extensions']))
check("in_all / in_some / in_none 互斥且穷尽（每个原子及其否定各归恰好一档）",
      sorted(list(n['in_all']) + list(n['in_some']) + list(n['in_none']))
      == sorted(['鸟', '¬鸟', '会飞', '¬会飞']),
      str((n['in_all'], n['in_some'], n['in_none'])))
check("不同候选子集收敛到同一理论时只算一个扩展（不重复报）",
      len(r(defaults=[('⊤', 'A'), ('⊤', 'B')])['extensions']) == 1,
      str(r(defaults=[('⊤', 'A'), ('⊤', 'B')])['extensions']))

print("=" * 60)
print(f"结果: {PASS}/24 通过")
raise SystemExit(0 if PASS == 24 else 1)
