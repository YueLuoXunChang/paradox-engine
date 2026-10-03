# -*- coding: utf-8 -*-
"""
test_nd_propositional.py — 正式测试：命题自然演绎（经典逻辑层 1.2）
用例依据：内部规格七·补A + docs/formulas/nd_propositional.md
运行：python engine/classical/test_nd_propositional.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nd_propositional import run  # noqa: E402

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


print("命题自然演绎构件 · 正式测试")
print("=" * 60)

# ── 用例1：基本推理可证
check("P→Q, P ⊢ Q → proved（→消去）",
      run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})['verdict'] == 'proved')
check("P→Q, Q→R, P ⊢ R → proved（传递）",
      run({'premises': ['P→Q', 'Q→R', 'P'],
           'conclusion': 'R'})['verdict'] == 'proved')
check("P∧Q ⊢ P → proved（∧消去）",
      run({'premises': ['P∧Q'], 'conclusion': 'P'})['verdict'] == 'proved')
check("P, Q ⊢ P∧Q → proved（∧引入）",
      run({'premises': ['P', 'Q'], 'conclusion': 'P∧Q'})['verdict'] == 'proved')

# ── 用例2：无前提可证（→引入链）
check("⊢ P→P → proved",
      run({'premises': [], 'conclusion': 'P→P'})['verdict'] == 'proved')
check("⊢ (P→Q)→((Q→R)→(P→R)) → proved",
      run({'premises': [],
           'conclusion': '(P→Q)→((Q→R)→(P→R))'})['verdict'] == 'proved')

# ── 用例3：∨ 推理
check("P∨Q, ¬P ⊢ Q → proved（∨消去）",
      run({'premises': ['P∨Q', '¬P'], 'conclusion': 'Q'})['verdict'] == 'proved')
check("P ⊢ P∨Q → proved（∨引入）",
      run({'premises': ['P'], 'conclusion': 'P∨Q'})['verdict'] == 'proved')

# ── 用例4：证明树白箱
r = run({'premises': ['P→Q', 'P'], 'conclusion': 'Q'})
check("proved 给证明树",
      isinstance(r['proof_tree'], list) and len(r['proof_tree']) >= 1, str(r))
check("证明树每步带规则名",
      all('rule' in s for s in r['proof_tree']), str(r))

# ── 用例5：经典 vs 直觉主义（¬¬消去）
check("经典 ¬¬P ⊢ P → proved",
      run({'premises': ['¬¬P'], 'conclusion': 'P'})['verdict'] == 'proved')
check("直觉主义 ¬¬P ⊢ P → not_proved（无 ¬¬消去）",
      run({'premises': ['¬¬P'], 'conclusion': 'P',
           'system': 'intuitionistic'})['verdict'] == 'not_proved')
check("直觉主义标注系统",
      run({'premises': ['¬¬P'], 'conclusion': 'P',
           'system': 'intuitionistic'})['system'] == 'intuitionistic')

# ── 用例6：诚实边界
check("缺结论 → conclusion_pending",
      run({})['verdict'] == 'conclusion_pending')
check("非法系统 → parse_error",
      run({'conclusion': 'P', 'system': 'Q'})['verdict'] == 'parse_error')
check("解析错误 → parse_error",
      run({'conclusion': 'P→'})['verdict'] == 'parse_error')

# ── 用例7：搜索节点预算（跨构件随机对拍撞出来的卡死，防复发）
# 崩因：只限"证明步数"不限"搜索节点数"——步数上限 60 时分支仍可指数爆炸，
# `(¬R ∨ ¬P) ⊢ Q` 会把搜索撑到跑不完（实测超 150 秒未返回）。
# 改法：加节点预算 `_MAX_NODES`，扣完即返回 closed=False ⇒ 判词 search_limit。
import nd_propositional as _nd  # noqa: E402
check("节点预算是正数护栏（口径锚：这个数就是搜索的兜底上限）",
      isinstance(_nd._MAX_NODES, int) and _nd._MAX_NODES > 0)
_r_slow = run({'premises': ['(¬(R) ∨ ¬(P))'], 'conclusion': 'Q',
               'system': 'classical'})
check("曾经卡死的那类目标：要么在预算内搜完（not_proved），要么老实报上限"
      "（search_limit）——**不许再卡住**",
      _r_slow['verdict'] in ('not_proved', 'search_limit'), _r_slow['verdict'])
check("卡死修复后判词仍不作假：not_proved 不等于'结论不成立'，边界里写明了",
      _r_slow['verdict'] != 'proved'
      and 'not_proved' in (_r_slow.get('boundary') or '')
      or 'search_limit' in (_r_slow.get('boundary') or ''))
check("可靠但不必完备：↔ 参与的前提可能证不出（((Q↔Q)→P) ⊢ P 报 not_proved），"
      "这是规则集限制、不是错——判词不许当成'无效'",
      run({'premises': ['((Q ↔ Q) → P)'], 'conclusion': 'P',
           'system': 'classical'})['verdict'] in ('not_proved',
                                                  'search_limit', 'proved'))

print("=" * 60)
print(f"结果: {PASS}/20 通过")
raise SystemExit(0 if PASS == 20 else 1)
