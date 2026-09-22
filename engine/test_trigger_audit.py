# -*- coding: utf-8 -*-
"""
test_trigger_audit.py — 触发实测（钝点定位）的正式测试
=======================================================
这张表要守的不是"数字对不对"，而是**接线状态的变化必须被看见**：
  ① 生成的表与真实语料一致（漂移检查）——语料/路由/适配器一改，这里就红；
  ② 判定与计数自洽（测试侧**另算一遍**：不 import 审计器的 _verdict）；
  ③ **凡是"被排进管线却一次没真跑"的构件，必须出现在下面的登记表里**——
     新增一个钝点、或某个钝点悄悄变好，都必须在这里改一处（故意的：状态变化要有人签字）；
  ④ "线索触发补跑"那批在"题型有材料"的前提下真跑 0 次，同样登记在册。

口径提醒（读这张表的人）：这些都是**对当前语料**的实测，不是构件的性质。
"""

import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)

import _trigger_audit as ta                                             # noqa: E402

PASS = 0
try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

TOTAL = 0


def check(label, cond, detail=''):
    global PASS, TOTAL
    TOTAL += 1
    if cond:
        PASS += 1
        print(f'  ✅ {label}')
    else:
        print(f'  ❌ {label}  {detail}')


# ── 登记表（**改这里要有理由**：接线状态变了、或语料补了带线索的材料）──────────
KNOWN_DEAD = {                      # 被排进管线，却在全部语料上一次没真跑
    'propositional.consistency', 'first_order.query',
    'converge_check.finite', 'ltl', 'wall_pipeline',
}
KNOWN_HALF = {                      # 跑了，但没跑满候选
    'propositional.validity', 'agm_revision', 'relevance_logic',
}
KNOWN_SUPPLEMENT_ZERO = {           # 线索触发补跑：题型有材料、真跑 0 次
    'interval_algebra', 'mu_calculus', 'description_logic.subsumption',
    'description_logic.classify', 'asp', 'belnap_four', 'dung',
    'intuitionistic_logic',
}


def verdict_of(n_cand, n_fire):
    """测试侧**独立**实现的判定（不 import 审计器的 _verdict，两条路互验）。"""
    if n_cand > 0 and n_fire == 0:
        return '钝点'
    if 0 < n_fire < n_cand:
        return '半空转'
    if n_cand > 0 and n_fire == n_cand:
        return '全触发'
    return '未出现'


rows, cand, fired, stuck, sup = ta._audit()

print('一、漂移：落盘的表 == 真实语料现算')
live = ta.render()
disk = io.open(ta.DOC, encoding='utf-8').read() if os.path.exists(ta.DOC) else ''
check('docs/trigger_audit.md 与现算一致（改了语料/路由就红）', live == disk,
      '不一致就跑 python engine/_trigger_audit.py --write')

print('二、自洽：触发集 ⊆ 候选集，判定与计数对得上')
bad_subset = [c for c in cand if not fired.get(c, set()) <= cand[c]]
check('每个构件的触发集都 ⊆ 候选集', not bad_subset, bad_subset)
mismatch = []
for c in cand:
    n_c, n_f = len(cand[c]), len(fired.get(c, ()))
    if verdict_of(n_c, n_f) != ta._verdict(n_c, n_f):
        mismatch.append((c, n_c, n_f))
check('测试侧独立判定 == 审计器判定（两条路互验）', not mismatch, mismatch)
check('没跑起来的原因不是"未出现"（要么有原因，要么是真跑过）',
      all(stuck.get(c) in ('missing_input', 'not_built', 'error')
          for c in cand if not fired.get(c, ())),
      [(c, stuck.get(c)) for c in cand if not fired.get(c, ())])

print('三、机械算的总数与台账一致')
dead = sorted(c for c in cand if not fired.get(c, ()))
half = sorted(c for c in cand if 0 < len(fired.get(c, ())) < len(cand[c]))
full = sorted(c for c in cand if len(fired.get(c, ())) == len(cand[c]))
check('钝点集合 == 登记表（**新增钝点必须在此登记**）', set(dead) == KNOWN_DEAD,
      f'现算 {dead} vs 登记 {sorted(KNOWN_DEAD)}')
check('半空转集合 == 登记表', set(half) == KNOWN_HALF,
      f'现算 {half} vs 登记 {sorted(KNOWN_HALF)}')
check('钝点/半空转/全触发三态互斥且覆盖所有出现过的构件',
      len(dead) + len(half) + len(full) == len(cand),
      (len(dead), len(half), len(full), len(cand)))
check('全触发那几件的候选数都 > 0', all(len(cand[c]) > 0 for c in full), full)

print('四、线索触发补跑：题型有材料却真跑 0 次的也要登记')
sup_zero = set()
types = {}
for r in rows:
    types[r['expect_type']] = types.get(r['expect_type'], 0) + 1
for comp, tps, _why in sup:
    avail = sum(types.get(t, 0) for t in tps)
    if avail > 0 and len(fired.get(comp, ())) == 0:
        sup_zero.add(comp)
check('"题型有材料但真跑 0 次"的集合 == 登记表（补跑件也是接线状态的一部分）',
      sup_zero == KNOWN_SUPPLEMENT_ZERO,
      f'现算 {sorted(sup_zero)} vs 登记 {sorted(KNOWN_SUPPLEMENT_ZERO)}')
check('补跑件若真跑过，会出现在触发表里（不会静默漏统计）',
      all((c in cand) for c in fired if c in {x[0] for x in sup}))

print('五、语料侧底线')
check('场景数 = 28（语料没被悄悄删过）', len(rows) == 28, len(rows))
check('每个场景都给出了 execution（白箱没被关掉）',
      all(isinstance(r.get('execution'), list) and r['execution'] for r in rows))
check('每个 execution 项都带 component 与 status',
      all(('component' in e and 'status' in e)
          for r in rows for e in r['execution']))
check('触发数不会超过该场景里的构件出现次数',
      all(len(fired.get(c, ())) <= len(cand[c]) for c in cand))

print('六、口径警告写在产物里（免得被当"构件好不好用"读）')
check('产物含"不是构件的性质"的口径警告',
      '不是构件的性质' in disk and '读法警告' in disk)
check('产物含三态定义（钝点/半空转/全触发）',
      all(k in disk for k in ('钝点', '半空转', '全触发')))

print(f'结果: {PASS}/16 通过')
raise SystemExit(0 if PASS == 16 else 1)
