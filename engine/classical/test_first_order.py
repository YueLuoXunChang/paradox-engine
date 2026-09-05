# -*- coding: utf-8 -*-
"""
test_first_order.py — 正式测试：一阶谓词逻辑构件（经典逻辑层 1.2）
用例依据：docs/ROADMAP 阶段1（概念来源：经典逻辑一阶谓词）
运行：python engine/classical/test_first_order.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from first_order import run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("一阶谓词逻辑构件 · 正式测试")
print("=" * 60)

# ── 用例1：三段论（∀ + 地面事实 → 结论）
check("∀x(人→会死), 人(苏) ⊢ 会死(苏) → entailed",
      run({'facts': ['人(苏格拉底)'],
           'rules': ['∀x(人(x)→会死(x))'],
           'query': '会死(苏格拉底)'})['verdict'] == 'entailed')
# 苏格拉底前提不成立则不可推出
check("无 人(柏拉图) 前提 ⊢ 会死(柏拉图) → not_entailed",
      run({'facts': ['人(苏格拉底)'],
           'rules': ['∀x(人(x)→会死(x))'],
           'query': '会死(柏拉图)'})['verdict'] == 'not_entailed')

# ── 用例2：多对象论域推理（规则对每个对象实例化）
r = run({'facts': ['人(苏格拉底)', '人(柏拉图)'],
         'rules': ['∀x(人(x)→会死(x))'],
         'query': '会死(苏格拉底)∧会死(柏拉图)'})
check("∀ 规则对多对象实例化 → 双结论 entailed",
      r['verdict'] == 'entailed', str(r))

# ── 用例3：反例模型输出质量
r = run({'facts': ['鸟(企鹅)'],
         'rules': ['∀x(鸟(x)→会飞(x))'],
         'query': '会飞(老鹰)'})
check("not_entailed 给出反例模型",
      r['verdict'] == 'not_entailed' and r['counterexample_model'] is not None,
      str(r))

# ── 用例4：存在量词
check("∃x(鸟(x)) 有对象 → entailed",
      run({'facts': ['鸟(麻雀)'],
           'rules': [],
           'query': '∃x(鸟(x))'})['verdict'] == 'entailed')
check("∀x(鸟→会飞) ⊢ ∃x(鸟(x))? 前提无反例对象 → 不可推出",
      run({'facts': ['猫(咪咪)'],
           'rules': ['∀x(鸟(x)→会飞(x))'],
           'query': '∃x(鸟(x))'})['verdict'] == 'not_entailed')

# ── 用例5：传递链推理（一阶核心能力）
check("∀x(会死(x)→腐烂(x)) 传递 → 腐烂(苏)",
      run({'facts': ['人(苏格拉底)'],
           'rules': ['∀x(人(x)→会死(x))',
                     '∀x(会死(x)→腐烂(x))'],
           'query': '腐烂(苏格拉底)'})['verdict'] == 'entailed')

# ── 用例6：地面命题混合（无对象也可判）
check("纯命题 下雨→地面湿, 下雨 ⊢ 地面湿 → entailed",
      run({'facts': ['下雨'], 'rules': ['下雨→地面湿'],
           'query': '地面湿'})['verdict'] == 'entailed')

# ── 用例7：否定与反证
check("反证：无事实时 ∀x(人(x)→会死(x)) ⊢ 人(苏)→会死(苏) → entailed",
      run({'facts': [], 'rules': ['∀x(人(x)→会死(x))'],
           'query': '人(苏格拉底)→会死(苏格拉底)'})['verdict'] == 'entailed')

# ── 用例8：诚实边界
check("残缺公式 → parse_error",
      run({'facts': ['人(苏'], 'rules': [],
           'query': '人(苏格拉底)'})['verdict'] == 'parse_error')
check("缺 query → query_pending",
      run({'facts': ['人(苏格拉底)']})['verdict'] == 'query_pending')

print("=" * 60)
print(f"结果: {PASS}/11 通过")
raise SystemExit(0 if PASS == 11 else 1)
