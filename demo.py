# -*- coding: utf-8 -*-
"""
demo.py — paradox-engine · 2 分钟上手演示
==========================================
运行：python demo.py

演示八件事：
  1) 悖论测度：矛盾有多尖锐 → 一个数 μ ∈ [0,1]；
  2) 悖论注解：矛盾拿一张 8 字段"身份证" + 分级（P-A/P-B/P-C）；
  3) 收敛判定：一个迭代过程会不会停下来；
  4) 经典逻辑地基：命题推理（有效性/反例/重言式）——第 1 层；
  5) 一阶谓词：量词推理（∀/∃ 展开判定）——第 1 层；
  6) 时序 LTL：演化性质（G 一直/F 最终/U 直到）——第 1 层；
  7) 模态逻辑：必然/可能（□/◇，系统 K/T）——第 1 层；
  8) λ 演算：自指计算形态（β 归约/Y 不动点/邱奇编码）——第 1 层。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.mechanisms.paradox_measure import run as measure
from engine.mechanisms.paradox_annotate import run as annotate
from engine.mechanisms.converge_check import run as converge


def banner(t):
    print("\n" + "=" * 62)
    print(t)
    print("=" * 62)


def main():
    banner("① 悖论测度：把“矛盾”量化成 0~1 的数")
    print("场景：A 说 P，B 说 ¬P，两边证据一样强（wA=5, wNotA=5）。")
    r1 = measure({'mode': 'mu1', 'wA': 5, 'wNotA': 5})
    print(f"  → 悖论强度 μ = {r1['mu']}")
    print("  → μ 越接近 1 矛盾越尖锐；五五开 = 1.0（强悖论）")
    r1b = measure({'mode': 'mu1', 'wA': 10, 'wNotA': 0})
    print(f"  → 对比：证据一边倒（wA=10, wNotA=0）→ μ = {r1b['mu']:.2e}（无悖论）")
    print("  立场：只诊断不决策——先承认矛盾存在，不急着消灭它。")

    banner("② 悖论注解：给矛盾发一张“身份证”")
    print("场景：上面那个矛盾，来源是“公理”（axiom）。")
    r2 = annotate({'paradox': {'A': 'P', 'notA': '¬P'}, 'source': 'axiom'})
    print(f"  → 分级 = {r2['grade']}")
    print(f"  → 8 字段注解卡：")
    for k, v in r2['annotation'].items():
        print(f"      {k:>3} = {v}")

    banner("③ 收敛判定：迭代会不会停下来？")
    print("场景：f(x) = 0.4x + 1（压缩映射，收缩系数 < 1）→ 必然收敛。")
    r3 = converge({'branch': 'finite',
                   'f': lambda x, e: 0.4 * x + 1,
                   'err_fn': lambda x: abs(x - 5 / 3),
                   'x0': 0.0, 'max_steps': 1000, 'tol': 1e-6})
    print(f"  → 收敛 = {r3['converges']}")
    print(f"  → 判定 = {r3['verdict']}")
    if r3.get('detail') and r3['detail'].get('finite_steps'):
        print(f"  → 有限步数 = {r3['detail']['finite_steps']}")

    banner("④ 经典逻辑地基：命题推理（第 1 层）")
    print("场景：经典三段论——所有人会死，苏格拉底是人。")
    from engine.classical.propositional import run as pl
    r4 = pl({'premises': ['人→会死', '人'], 'conclusion': '会死',
             'mode': 'validity'})
    print(f"  → 推理有效性 = {r4['verdict']}（经典逻辑：有效）")
    r4b = pl({'premises': ['P∨Q'], 'conclusion': 'P', 'mode': 'validity'})
    print(f"  → 反例示范：P∨Q ⊢ P 无效，反例 = {r4b['counterexample']}")
    r4c = pl({'formula': 'P∨¬P'})
    print(f"  → 排中律 P∨¬P = {r4c['verdict']}（恒真）")

    banner("⑤ 一阶谓词：量词推理（第 1 层）")
    print("场景：带量词的推理——所有人会死，苏格拉底是人 → 苏格拉底会死。")
    from engine.classical.first_order import run as fol
    r5 = fol({'facts': ['人(苏格拉底)'],
              'rules': ['∀x(人(x)→会死(x))'],
              'query': '会死(苏格拉底)'})
    print(f"  → 结论 = {r5['verdict']}（∀ 规则在论域上展开判定）")
    r5b = fol({'facts': ['鸟(企鹅)'],
               'rules': ['∀x(鸟(x)→会飞(x))'],
               'query': '会飞(老鹰)'})
    print(f"  → 反例示范：⊢会飞(老鹰) = {r5b['verdict']}（老鹰不在鸟集合）")
    print(f"     反例模型（节选）= {r5b['counterexample_model'][:3] if r5b['counterexample_model'] else None}")
    print("  经典能算的算清（命题→谓词），算不清的矛盾留给下一层。")

    banner("⑥ 时序 LTL：事情会怎样发展（第 1 层）")
    print("场景：系统状态序列 [正常运行 → 故障 → 恢复]——满足什么性质？")
    from engine.classical.ltl import run as ltl
    path = [{'正常'}, {'down'}, {'恢复'}, {'正常'}]
    r6a = ltl({'path': path, 'formula': 'G(¬down)'})
    print(f"  → G(¬down)（一直不出故障）= {r6a['verdict']}"
          f"{'，位置 ' + str(r6a['violation_index']) + ' 违约' if r6a['violation_index'] is not None else ''}")
    r6b = ltl({'path': path, 'formula': 'F(恢复)'})
    print(f"  → F(恢复)（最终恢复）= {r6b['verdict']}")
    print("  LTL 把'演化'变成可判定的性质——'会不会恢复''会不会一直坏'有了明确答案。")

    banner("⑦ 模态逻辑：必然与可能（第 1 层）")
    print("场景：□p→◇p（必然蕴含可能）——在 K 与 T 系统下结论不同。")
    from engine.classical.modal import run as modal
    r7a = modal({'worlds': ['w0'], 'access': {'w0': []}, 'system': 'K',
                 'assign': {}, 'formula': '□p→◇p', 'world': 'w0'})
    print(f"  → 系统 K（无可达世界）：{r7a['verdict']}")
    r7b = modal({'worlds': ['w0'], 'access': {'w0': ['w0']}, 'system': 'T',
                 'assign': {'p': ['w0']}, 'formula': '□p→◇p', 'world': 'w0'})
    print(f"  → 系统 T（自反）：{r7b['verdict']}")
    print("  结论绑定系统假设——输出永远标注'在哪个系统下成立'（白箱纪律）。")

    banner("⑧ λ 演算：自指的计算形态（第 1 层）")
    print("场景：Y 组合子 = 不动点 = 自指律 X=f(X) 的计算版。")
    from engine.classical.lambda_calculus import run as lam
    r8a = lam({'expr': '(λx.x)(λy.y)'})
    print(f"  → β 归约 (λx.x)(λy.y) → 正规形 {r8a['normal_form']}")
    r8b = lam({'mode': 'church', 'church_arg': 2})
    print(f"  → 邱奇编码 succ(2) → {r8b['church_number']}（自然数=函数）")
    r8c = lam({'mode': 'factorial', 'fact_n': 5})
    print(f"  → Y 递归（有界展开）5! = {r8c['factorial_value']}")
    r8d = lam({'mode': 'self_apply'})
    print(f"  → Ω=(λx.xx)(λx.xx) 自应用 → {r8d['verdict']}（无范式，诚实不卡死）")
    print("  λ 演算给'自指'一个干净底座：Y f = f(Y f)——引擎能算的边界内自指。")

    print("\n" + "=" * 62)
    print("paradox-engine 的分层主张：")
    print("  第 1 层经典逻辑：能算的先算清（命题/谓词/时序/模态/λ）")
    print("  第 2 层悖论：算不清的当第一公民（测量→注解→报告）")
    print("  只诊断不决策：把判断留给使用它的人。")
    print("更多：见 README.md + docs/ROADMAP.md")
    print("=" * 62)


if __name__ == "__main__":
    main()
