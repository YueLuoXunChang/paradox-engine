# -*- coding: utf-8 -*-
"""
test_controller.py — 正式测试：总控五步流水线（步1-5 落码）
用例依据：内部规格（走查一/三 + 五查 + 诚实边界）
运行：python engine/control/test_controller.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller import run  # noqa: E402

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


print("总控五步流水线 · 正式测试")
print("=" * 60)

# ── 用例1：38 走查一——需求打架（T2-L2 端到端）
r = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
         'structured': {'A': '尽快上线(3周)', 'B': '完整覆盖合规(12周)',
                        'wA': 5, 'wNotA': 5}})
check("→ done（有构件真跑）", r['verdict'] == 'done', str(r))
check("判类 T2", r['classification']['main_type'] == 'T2', str(r))
check("复杂度 L2", r['classification']['level'] == 'L2', str(r))
check("路由 R2-L2",
      r['classification']['route']['route_id'] == 'R2-L2', str(r))
ran = [e for e in r['execution'] if e['status'] == 'run']
check("μ 测度真跑",
      any('paradox_measure' in e['component'] for e in ran), str(ran))
check("注解真跑",
      any('paradox_annotate' in e['component'] for e in ran), str(ran))
check("μ 输出数值",
      any((e.get('output') or {}).get('mu') is not None for e in ran),
      str(ran))
check("注解输出 grade",
      any((e.get('output') or {}).get('grade') for e in ran), str(ran))
check("五查全带", r['output_check'] and len(r['output_check']) == 5,
      str(r['output_check']))
check("报告含类型行", '【类型】T2' in r['report'], r['report'])
check("报告含五查行", '【五查】' in r['report'], r['report'])
check("报告含边界行", '【边界】' in r['report'], r['report'])

# ── 用例2：一致性五查（μ 与 grade 交叉）
c = r['output_check']['consistency']
check("一致性检查给结论", 'ok' in c, str(c))

# ── 用例3：38 走查三——排中律（L1 单机制，最小充分）
r = run({'text': '今天下雨或没下雨',
         'structured': {'premises': [], 'conclusion': 'P∨¬P'}})
ran = [e for e in r['execution'] if e['status'] == 'run']
check("排中律真跑 1 件", len(ran) == 1, str(ran))
check("单机制是 propositional",
      'propositional' in ran[0]['component'], str(ran))
check("排中律 L1", r['classification']['level'] == 'L1', str(r))
check("排中律验证 tautology",
      (ran[0].get('output') or {}).get('verdict') == 'tautology',
      str(ran[0]))

# ── 用例4：说谎者（T6 → selfref_fixpoint，mu2 路由）
r = run({'text': '这句话是假的', 'structured': {'sentence': '这句话是假的'}})
ran = [e for e in r['execution'] if e['status'] == 'run']
check("说谎者 T6", r['classification']['main_type'] == 'T6', str(r))
check("selfref_fixpoint 真跑",
      any('selfref' in e['component'] for e in ran), str(ran))
liar = next((e['output'] for e in ran if 'selfref' in e['component']), {})
check("说谎者判 liar_cycle", liar.get('verdict') == 'liar_cycle',
      str(liar))

# ── 用例5：缺结构化 → 诚实 missing_input（classified_only）
r = run({'text': '产品既要快又要稳'})
check("无结构化 → classified_only", r['verdict'] == 'classified_only',
      str(r))
check("缺输入诚实标注",
      any(e['status'] == 'missing_input' for e in r['execution']), str(r))
check("缺输入带说明",
      any(e['status'] == 'missing_input' and e['note']
          for e in r['execution']), str(r))

# ── 用例6：T12 未分类诚实
r = run({'text': '随便写点什么'})
check("无信号 → T12", r['classification']['main_type'] == 'T12', str(r))
check("报告提示未识别", '未识别' in r['report'], r['report'])
check("T12 置信度 low 提示",
      r['classification']['confidence'] == 'low', str(r))

# ── 用例7：充分度五查（L1 长文本 → 建议升档）
r = run({'text': '所有的人都支持所有的事情，所有的事情都支持所有的'
                 '人，这中间有复杂的演化过程还会自指',
         'structured': {'premises': ['P'], 'conclusion': 'P∨Q'}})
check("充分度检查存在", 'adequacy' in r['output_check'], str(r))

# ── 用例8：T7 对立交汇端到端（L1 路由 μ 单机制——最小充分）
r = run({'text': '要自由还是要秩序，能不能兼得',
         'structured': {'wA': 5, 'wNotA': 5}})
ran = [e for e in r['execution'] if e['status'] == 'run']
check("对立交汇 T7", r['classification']['main_type'] == 'T7', str(r))
check("T7-L1 真跑 1 件（最小充分）", len(ran) == 1, str(ran))
check("T7-L1 单机制是 μ 测度",
      'paradox_measure' in ran[0]['component'], str(ran))
# 文本更复杂（含演化+多实体）→ 升 L2/L3 → counterpoint_gen 进管线
r2 = run({'text': '要自由还是要秩序，社会系统演化中还要平衡效率与公平，'
                  '如何兼得',
          'structured': {'wA': 5, 'wNotA': 5}})
pipe2 = r2['classification']['route']['pipeline']
check("复杂对立文本 → 管线含创生件",
      any('counterpoint' in p for p in pipe2), str(pipe2))

# ── 用例9：冷门新构件接线（T5 AGM / T2 相干）+ 适配器完备性不变式
r = run({'text': '原来以为所有天鹅都是白的，现在发现黑天鹅，旧结论还成立吗',
         'structured': {'beliefs': ['P→Q', 'P'], 'new_info': '¬Q',
                        'priorities': {'P→Q': 1, 'P': 10}}})
_ex = {e['component']: e for e in r['execution']}
check("T5 管线含 agm_revision", 'agm_revision' in _ex, sorted(_ex))
check("agm_revision 真跑 → revised",
      _ex['agm_revision']['status'] == 'run'
      and _ex['agm_revision']['output']['verdict'] == 'revised',
      str(_ex.get('agm_revision')))
check("AGM 最小放弃生效（弃 P→Q 保 P）",
      _ex['agm_revision']['output']['dropped'] == ['P→Q'],
      str(_ex['agm_revision']['output']))
r2 = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
          'structured': {'prop_a': 'P', 'prop_b': '¬P', 'wA': 5,
                         'wNotA': 5}})
_ex2 = {e['component']: e for e in r2['execution']}
check("T2-L2 管线含 relevance_logic", 'relevance_logic' in _ex2,
      sorted(_ex2))
check("相干检查真跑 → real_conflict（真冲突）",
      _ex2['relevance_logic']['status'] == 'run'
      and _ex2['relevance_logic']['output']['verdict'] == 'real_conflict',
      str(_ex2.get('relevance_logic')))
r3 = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
          'structured': {'A': '要快', 'B': '要稳', 'wA': 5, 'wNotA': 5}})
_ex3 = {e['component']: e for e in r3['execution']}
check("相干检查缺命题输入 → 诚实报缺（不拿 A/B 硬凑）",
      _ex3['relevance_logic']['status'] == 'missing_input',
      str(_ex3.get('relevance_logic')))

# 不变式：路由表承诺的构件，执行层都得有适配器（防"路由画饼"）
from classifier import ROUTE  # noqa: E402
from controller import ADAPTER_SPECS  # noqa: E402
_names = set()
for _pipeline, _ in ROUTE.values():
    _names |= set(_pipeline)
check("ROUTE 里每个构件名都有适配器（无画饼路由）",
      all(n in ADAPTER_SPECS for n in _names),
      sorted(n for n in _names if n not in ADAPTER_SPECS))
check("管线用到的构件都有适配器（覆盖 ≥18 件）", len(_names) >= 18,
      str(len(_names)))

# ── 用例10：诚实边界
check("空文本 → input_pending", run({})['verdict'] == 'input_pending')
check("非字符串 → input_pending",
      run({'text': 42})['verdict'] == 'input_pending')
check("边界声明含不下决策",
      '不下决策' in run({'text': 'x', 'structured': {}})['boundary'])
r = run({'text': '这句话是假的'})
check("T6 无结构化 → 至少诚实执行或缺输入",
      r['verdict'] in ('done', 'classified_only'), str(r))


# ══════════════════════════════════════════════════════════════
# 用例N：接线批次（2026-09-20）——四件外部机制 + 四件老冷门件
#   口径：判类只看文本判档；**人给的形式化线索**决定还能跑哪些（线索驱动补跑）。
# ══════════════════════════════════════════════════════════════
from scenarios.scenarios import SCENES  # noqa: E402

_by_type = {}
for _s in SCENES:
    _by_type.setdefault(_s['expect_type'], _s['text'])

NEW_CASES = [
    ('T4', 'interval_algebra',
     {'events': ['A', 'B'], 'relations': [['A', 'b', 'B']]}),
    ('T4', 'mu_calculus',
     {'formula': 'μX.(p | <>X)', 'states': ['s0', 's1'],
      'transitions': [['s0', 's1']], 'labels': {'s1': ['p']}}),
    ('T6', 'mu_calculus',
     {'formula': 'νX.(p & <>X)', 'states': ['a'], 'transitions': [['a', 'a']],
      'labels': {'a': ['p']}}),
    ('T10', 'description_logic.subsumption',
     {'sub': 'Woman', 'super': 'Person',
      'tbox': ['Woman ≡ Person ⊓ Female']}),
    ('T3', 'description_logic.classify',
     {'tbox': ['Woman ≡ Person ⊓ Female', 'Man ≡ Person ⊓ ¬Woman']}),
    ('T2', 'asp', {'program': 'p :- not q. q :- not p.'}),
    ('T2', 'belnap_four', {'formula': 'P ∨ ¬P', 'assign': {'P': 'B'}}),
    ('T2', 'dung', {'arguments': ['a', 'b'], 'attacks': [['a', 'b']]}),
    ('T1', 'intuitionistic_logic', {'formula': 'P∨¬P'}),
]
_runs, _miss, _notes = [], [], []
for _typ, _comp, _clues in NEW_CASES:
    _r = run({'text': _by_type[_typ], 'structured': _clues})
    _e = [x for x in _r['execution'] if x['component'] == _comp]
    if not _e:
        _miss.append((_comp, _typ, '不在执行里'))
        continue
    if _e[0]['status'] != 'run':
        _miss.append((_comp, _typ, _e[0]['status'], _e[0].get('note')))
    else:
        _runs.append(_comp)
        _notes.append(_e[0].get('note') or '')

check("★接线后新构件给线索就真跑（9 条用例 / 8 件构件，含四件外部机制）",
      not _miss and len(_runs) == len(NEW_CASES)
      and len(set(_runs)) == 8, (_miss, _runs))
check("★补跑的在 note 里注明「线索触发补跑：…」（白箱：为什么跑要看得见）",
      all('线索触发补跑' in n or 'OK' == n for n in _notes),
      [n[:40] for n in _notes])

# 结果抽查：真跑了而且结论对
_r = run({'text': _by_type['T2'],
          'structured': {'program': 'p :- not q. q :- not p.'}})
_asp = [x for x in _r['execution'] if x['component'] == 'asp'][0]['output']
check("★答案集抽查：p :- not q. q :- not p. → 两个答案集 {p}/{q}",
      _asp['verdict'] == 'solved' and _asp['count'] == 2,
      _asp.get('answer_sets'))
_r = run({'text': _by_type['T10'],
          'structured': {'sub': 'Woman', 'super': 'Person',
                         'tbox': ['Woman ≡ Person ⊓ Female']}})
_dl = [x for x in _r['execution']
       if x['component'] == 'description_logic.subsumption'][0]['output']
check("★ALC 抽查：本体下 Woman ⊑ Person → subsumed", _dl['verdict'] == 'subsumed',
      _dl['verdict'])
_r = run({'text': _by_type['T4'],
          'structured': {'events': ['A', 'B'], 'relations': [['A', 'b', 'B']]}})
_ia = [x for x in _r['execution'] if x['component'] == 'interval_algebra'][0]
check("★区间代数抽查：A 先于 B 自洽，并给可复核的整数区间见证",
      _ia['output']['verdict'] in ('model_found', 'consistent')
      and _ia['output'].get('model'), _ia['output'].get('verdict'))

# 口径：没给线索 → 补跑的构件**安静跳过**（不刷一屏 missing_input）
_r = run({'text': _by_type['T4']})
_names_no_clue = [x['component'] for x in _r['execution']]
check("★没给线索时，补跑表里的构件安静跳过（不刷 missing_input）",
      'interval_algebra' not in _names_no_clue, _names_no_clue)

# 口径：题型对不上就不补跑（asp 的线索给到 T4 材料上也不跑）
_r = run({'text': _by_type['T4'], 'structured': {'program': 'p.'}})
check("★题型对不上不补跑（线索只在该题型生效）",
      'asp' not in [x['component'] for x in _r['execution']])

# 口径：既在路由里又在补跑表里的构件只跑一次
_r = run({'text': _by_type['T2'],
          'structured': {'program': 'p :- not q.'}})
_names = [x['component'] for x in _r['execution']]
check("★同一个构件在一次运行里只出现一次（路由 + 补跑不重复）",
      len(_names) == len(set(_names)), _names)

# 口径：管线里就有、但人没给线索 → 诚实报 missing_input（不许假装跑过）
_r = run({'text': _by_type['T6']})
_mu = [x for x in _r['execution'] if x['component'] == 'mu_calculus']
check("管线内的新构件缺线索 → missing_input（诚实报缺，不硬凑）",
      not _mu or _mu[0]['status'] == 'missing_input',
      _mu[0] if _mu else '不在管线（该档没有它）')

print("=" * 60)
print(f"结果: {PASS}/52 通过")
raise SystemExit(0 if PASS == 52 else 1)
