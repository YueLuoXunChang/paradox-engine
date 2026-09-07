# -*- coding: utf-8 -*-
"""
test_belnap_four.py — 正式测试：Belnap 四值逻辑（第 3 层 3.1 次协调语义）
用例依据：内部规格 43 §一（矛盾取"两者"不爆炸 + 与第 2 层咬合）+ 借鉴标注
运行：python engine/cold/test_belnap_four.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from belnap_four import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("Belnap 四值逻辑 · 正式测试")
print("=" * 60)

# ── 用例1：核心——矛盾取"两者"B（不爆炸，次协调立场）
r = run({'formula': 'A∧¬A', 'assign': {'A': 'B'}})
check("A∧¬A 在 A=B → B", r['value'] == 'B', str(r))
check("truth_set 含真假双方", set(r['truth_set']) == {'真', '假'}, str(r))
check("note 声明不爆炸", '不爆炸' in r['note'], r['note'])
check("A=T 时 A∧¬A → F（一致时不矛盾）",
      run({'formula': 'A∧¬A', 'assign': {'A': 'T'}})['value'] == 'F')
check("A=F 时 A∧¬A → F",
      run({'formula': 'A∧¬A', 'assign': {'A': 'F'}})['value'] == 'F')
check("A=N 时 A∧¬A → N（无信息）",
      run({'formula': 'A∧¬A', 'assign': {'A': 'N'}})['value'] == 'N')

# ── 用例2：排中律四值非恒真
r = run({'formula': 'P∨¬P', 'assign': {'P': 'B'}})
check("P∨¬P 在 P=B → B（非恒真）", r['value'] == 'B', str(r))
check("P∨¬P 在 P=T → T（经典情形仍真）",
      run({'formula': 'P∨¬P', 'assign': {'P': 'T'}})['value'] == 'T')
check("P∨¬P 在 P=N → N",
      run({'formula': 'P∨¬P', 'assign': {'P': 'N'}})['value'] == 'N')

# ── 用例3：联结词性质
check("¬B=B", run({'formula': '¬P',
                   'assign': {'P': 'B'}})['value'] == 'B')
check("¬N=N", run({'formula': '¬P',
                   'assign': {'P': 'N'}})['value'] == 'N')
check("¬T=F", run({'formula': '¬P',
                   'assign': {'P': 'T'}})['value'] == 'F')
check("B∧T=B（meet）", run({'formula': 'P∧Q',
                            'assign': {'P': 'B',
                                       'Q': 'T'}})['value'] == 'B')
check("B∧N=F（N 与 B 的 meet=F，菱形格）",
      run({'formula': 'P∧Q', 'assign': {'P': 'B',
                                        'Q': 'N'}})['value'] == 'F')
check("B∨N=T（join）",
      run({'formula': 'P∨Q', 'assign': {'P': 'B',
                                        'Q': 'N'}})['value'] == 'T')
check("T→B = ¬T∨B = F∨B = B",
      run({'formula': 'P→Q', 'assign': {'P': 'T',
                                        'Q': 'B'}})['value'] == 'B')
check("括号嵌套 (A∧B)∨¬C",
      run({'formula': '(A∧B)∨¬C', 'assign': {'A': 'T', 'B': 'N',
                                             'C': 'T'}})['value'] == 'N')

# ── 用例4：与第 2 层咬合（对位创生/共振带语义地基）
r = run({'formula': 'A∧¬A', 'assign': {'A': 'B'}})
check("矛盾值=两者 → 非无解非爆炸", r['value'] == 'B', str(r))
check("note 提到次协调立场", '次协调' in r['note'], r['note'])

# ── 用例5：真值表白箱
r = run({'formula': 'A∧¬A', 'assign': {'A': 'T'}})
check("真值表行数=4（单原子×4 值）", len(r['rows']) == 4, str(r))
check("真值表含 B→B 行",
      any(row.get('A') == 'B' and row.get('→') == 'B'
          for row in r['rows']), str(r))

# ── 用例6：demo 模式
r = run({'demo': True})
check("demo → evaluated", r['verdict'] == 'evaluated', str(r))
check("demo 行数 ≥8（排中律4 + 矛盾4）", len(r['rows']) >= 8, str(r))
check("demo 注明排中律非恒真",
      any('非恒真' in r['note'] for r in [r]), r['note'])

# ── 用例7：诚实边界
check("缺输入 → input_pending", run({})['verdict'] == 'input_pending')
check("解析错 → parse_error",
      run({'formula': 'A∧', 'assign': {'A': 'T'}})
      ['verdict'] == 'parse_error')
check("坏赋值 → assign_pending",
      run({'formula': 'A', 'assign': {'A': 'X'}})['verdict']
      == 'assign_pending')
check("缺赋值 → assign_pending",
      run({'formula': 'A', 'assign': {}})['verdict'] == 'assign_pending')
check("边界声明借鉴来源（Belnap 外部共识）",
      'Belnap' in run({'formula': 'A', 'assign': {'A': 'T'}})['boundary'])
check("边界声明不宣称判定说谎者真值",
      '不宣称' in run({'formula': 'A', 'assign': {'A': 'T'}})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/30 通过")
raise SystemExit(0 if PASS == 30 else 1)
