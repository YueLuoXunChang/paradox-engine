# -*- coding: utf-8 -*-
"""
demo.py — paradox-engine · 2 分钟上手演示
==========================================
运行：python demo.py

演示十件事：
  1) 悖论测度：矛盾有多尖锐 → 一个数 μ ∈ [0,1]；
  2) 悖论注解：矛盾拿一张 8 字段"身份证" + 分级（P-A/P-B/P-C）；
  3) 收敛判定：一个迭代过程会不会停下来；
  4) 经典逻辑地基：命题推理（有效性/反例/重言式）——第 1 层；
  5) 一阶谓词：量词推理（∀/∃ 展开判定）——第 1 层；
  6) 时序 LTL：演化性质（G 一直/F 最终/U 直到）——第 1 层；
  7) 模态逻辑：必然/可能（□/◇，系统 K/T）——第 1 层；
  8) λ 演算：自指计算形态（β 归约/Y 不动点/邱奇编码）——第 1 层；
  9) 图灵机：模拟 + 停机问题不可判定的诚实答案——第 1 层；
 10) STLC 类型：拦自应用（类型正确 ⇒ 终止）——与 ⑧ 对照——第 1 层；
 11) 撞墙管线：说谎者句 → 五选一诊断——第 2 层（核心卖点）；
 12) 总控五步：一段中文 → 判类→复杂度→切路→执行→判输出——引擎大脑；
 13) MT-MP-TL 骨架：多线程并行→汇合（点/线程/拓扑/操作）——第 0 层；
 14) 冷门逻辑：矛盾取"两者"（Belnap 四值）+ 立场分析（Dung）——第 3 层；
 15) AI 挂载：23 个引擎函数 = AI 可调用工具（function-calling）——挂载层；
 16) 数学底座：自指程序构造（Kleene 递归定理）+ 真值修正（Gupta-Belnap）。
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
    print("  第 1 层经典逻辑：能算的先算清（命题/谓词/时序/模态/λ/图灵机/类型）")

    banner("⑨ 图灵机：停机问题的诚实答案（第 1 层）")
    print("场景：图灵机模拟 + 停机问题不可判定——引擎怎么回答'这墙能不能过'。")
    from engine.classical.turing_machine import run as tm
    from engine.classical.turing_machine import parity_machine, loop_machine
    r9a = tm({'program': parity_machine(), 'input': '000', 'steps_limit': 100})
    print(f"  → 模拟奇偶机 '000' → {r9a['verdict']}")
    r9b = tm({'program': loop_machine(), 'input': '01', 'steps_limit': 50})
    print(f"  → 模拟永不停止的机 → {r9b['verdict']}（诚实：不假装判停机）")
    r9c = tm({'mode': 'halting_demo'})
    print(f"  → 停机问题 → {r9c['verdict']}（数学定理的可演示版）")
    print("  引擎不宣称绕过停机问题——它把'不可判定'变成可注解的标本（收编为原料）。")

    banner("⑩ STLC 类型：类型如何拦住自指（第 1 层）")
    print("场景：⑧ 的 λ 能写 Y/Ω（自指不死循环）；加上类型后这些全被拦住。")
    from engine.classical.stlc import run as stlc
    r10a = stlc({'expr': 'λx:A.x'})
    print(f"  → λx:A.x 类型检查 = {r10a['verdict']}，推断类型 {r10a['inferred']}")
    r10b = stlc({'expr': 'λx:A.x x'})
    print(f"  → λx:A.x x（自应用）= {r10b['verdict']}（类型拦住——对应 Ω 在类型世界不存在）")
    r10c = stlc({'expr': '(λx:A.x) c', 'context': {'c': 'A'}})
    print(f"  → 应用 (λx:A.x) c（c:A）= {r10c['verdict']} : {r10c['inferred']}")
    print("  双视角：1.6 无类型 λ 能写 Y（自指）但会不停机；1.9 类型拦自应用，")
    print("  类型正确 ⇒ 必然终止——代价是写不了 Y。表达力 × 终止性，经典权衡。")

    banner("⑪ 撞墙管线：说谎者句 → 五选一诊断（第 2 层 · 核心卖点）")
    print("场景：经典逻辑对说谎者句只能说'判定不了'——撞墙管线把它变成")
    print("      五选一诊断（测墙→钻墙→看墙→旁路→创生）。")
    from engine.mechanisms.wall_pipeline import run as wall
    r11 = wall({'wall': '这句话是假的', 'thesis': '要快', 'antithesis': '要稳'})
    print(f"  → 五选一诊断 = {r11['verdict']}")
    print(f"  → {r11['diagnosis']['label']}")
    print(f"  → 注解卡 LV = {r11['annotation'].get('LV')}（结构性 P-A）")
    print("  各步白箱：")
    for s in r11['steps']:
        st = s['status']
        if st == 'run':
            d = s['detail']
            brief = {k: v for k, v in d.items()
                     if k in ('mu', 'grade', 'verdict', 'period', 'tension',
                              'coupling', 'main_ran', 'findings')}
            print(f"      [{s['step']}] {brief}")
        else:
            print(f"      [{s['step']}] skip（{s['detail'].get('reason', '可选步未给输入')}）")
    print("  立场：不是'判定了说谎者真值'——是把它从'死'变成可诊断的一格（只诊断不决策）。")

    banner("⑫ 总控五步：一段中文 → 判类→复杂度→切路→执行→判输出（引擎大脑）")
    print("场景：把 38 总控五步落码——任意一段问题文本，自动判类、判复杂度、")
    print("      切路、按路由真跑构件、五查判输出。")
    from engine.control.controller import run as controller
    r12 = controller({
        'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
        'structured': {'A': '尽快上线(3周)', 'B': '完整覆盖合规(12周)',
                       'wA': 5, 'wNotA': 5}})
    print(r12['report'])
    print("  五查：完整性/一致性/置信度/边界性/充分度——只诊断不决策，判断留给使用者。")

    banner("⑬ MT-MP-TL 骨架：多线程并行→汇合（第 0 层）")
    print("场景：多线程并行推进，撞到汇合点合并——骨架层只表达结构，不掺判定。")
    from engine.skeleton.mtmp import run as skel
    # 两条并行线程在 b 汇合
    r13a = skel({'mode': 'thread', 'action': 'create', 'threads': [
        {'id': 't1', 'points': ['a1', 'b', 'c'], 'speed': 1},
        {'id': 't2', 'points': ['a2', 'b', 'd'], 'speed': 1}]})
    print(f"  → 建 2 线程：{r13a['detail']['threads']}")
    r13b = skel({'mode': 'thread', 'threads': [
        {'id': 't1', 'points': ['a1', 'b', 'c']},
        {'id': 't2', 'points': ['a2', 'b', 'd']}],
        'action': 'converge', 'tid': 't1', 'tid2': 't2', 'point': 'b'})
    print(f"  → 汇合：{r13b['detail']['note']} → 合并后 "
          f"{r13b['detail']['merged_points']}")
    r13c = skel({'mode': 'topology', 'points': ['中心', '甲', '乙', '丙'],
                 'edges': [('中心', '甲'), ('中心', '乙'), ('中心', '丙')],
                 'action': 'classify'})
    print(f"  → 拓扑分类：{r13c['detail']['kind']}"
          f"（{r13c['detail']['note']}）")
    print("  骨架层纪律：只做结构表达——判真假归第 1 层、判悖论归第 2 层。")

    banner("⑭ 冷门逻辑：矛盾取'两者' + 立场分析（第 3 层）")
    print("场景：经典逻辑见矛盾就爆炸；第 3 层给矛盾两个出口——")
    print("      Belnap 四值（矛盾=两者，非无解）与 Dung（哪些立场顶得住攻击）。")
    from engine.cold.belnap_four import run as belnap
    r14a = belnap({'demo': True})
    row_b = [row for row in r14a['rows']
             if row.get('A') == 'B' and 'A∧¬A' in row][0]
    print(f"  → Belnap 四值：A∧¬A 在 A=两者(B) → 值={row_b['A∧¬A']}"
          f"（矛盾是信息态，不爆炸——给第 2 层共振带一个语义地基）")
    print(f"    demo 表：{[(r.get('A'), r.get('A∧¬A')) for r in r14a['rows'][4:]]}")
    from engine.cold.dung_framework import run as dung
    r14b = dung({'arguments': ['方案A省钱', '方案B全面', '方案C快速'],
                 'attacks': [('方案A省钱', '方案B全面'),
                             ('方案B全面', '方案C快速')]})
    print(f"  → Dung：grounded（站得住）= {r14b['grounded']}，"
          f"preferred = {r14b['preferred']}")
    print("  第 3 层纪律：外部共识（Belnap 1977 / Dung 1995）——借鉴区，标注来源不混原创。")

    banner("⑮ AI 挂载：23 个引擎函数 = AI 可调用工具")
    print("场景：把引擎全部构件封装成 function-calling 工具——AI（或任何")
    print("      调用客户端）看 schema 就知道能干什么、要什么参数。")
    from engine.ai.tools import tools as ai_tools
    from engine.ai.tools import call_tool
    tl = ai_tools()
    print(f"  → 工具清单 {len(tl)} 件（schema 从各构件 PORTS 自动生成）")
    for t in tl[:5]:
        fn = t['function']
        print(f"      · {fn['name']}：{fn['description']}")
    print(f"      · …（共 {len(tl)} 件，覆盖悖论/经典/骨架/冷门/总控全层）")
    r15 = call_tool('controller', {
        'text': '销售坚持三周内必须上线抢占市场，研发坚持合规审查十二周'
                '一步不能少——既要抢占市场，又要完整合规',
        'structured': {'A': '抢占市场(3周)', 'B': '完整合规(12周)',
                       'wA': 5, 'wNotA': 5}})
    mt = r15['result']['classification']['main_type']
    print(f"  → call_tool('controller', …) → {mt}，"
          f"路由 {r15['result']['classification']['route']['route_id']}")
    print("  → 真实场景端到端：python engine/ai/ai_scenarios.py")
    print("    （场景1 论证矛盾检查 / 场景2 学科建模——AI 决策工具链）")
    print("  AI 挂载层纪律：schema 与 PORTS 一致；缺参由构件诚实拦截，挂载层不伪造输入。")

    banner("⑯ 数学底座：自指程序 + 真值修正（借鉴区，标注来源）")
    print("场景：给「自指」补两个学界锚点——程序拿到自己（Kleene 递归定理）")
    print("      与修正序列振荡（Gupta-Belnap 真值修正——共振带的学术出处）。")
    from engine.classical.recursion_theorem import run as kleene
    r16a = kleene({'mode': 'quine', 'payload': '自指演示'})
    print(f"  → Kleene 递归定理：quine 自复制程序构造成功"
          f"（{len(r16a['program'])} 字符源码）")
    print(f"    runs_like: {r16a['runs_like']}")
    from engine.cold.truth_revision import run as gb
    r16b = gb({'mode': 'demo'})
    for tag, name in [('liar', '说谎者 P↔¬P'),
                      ('ring', '互指环 P↔Q真/Q↔P假'),
                      ('benign', '良性 P↔P∧Q')]:
        s = r16b['detail']['systems'][tag]
        period_note = ''
        if s.get('period'):
            period_note = f"（周期 {s['period']}）"
        print(f"    {name} → {s['verdict']}{period_note}")
    print("  借鉴纪律：Kleene 1952 / Gupta-Belnap 1993——归借鉴区，不混原创区；")
    print("  振荡≠判真值（说谎者周期 2 是教科书结论，非引擎自创）。")

    print("\n" + "=" * 62)
    print("paradox-engine 的分层主张：")
    print("  总控：判类→判复杂度→切路→执行→判输出（最小充分：简单问题绝不复杂化）")
    print("  第 0 层骨架：点/线程/拓扑/操作——结构表达（12 形态，不掺判定）")
    print("  第 1 层经典逻辑：能算的先算清（命题/谓词/时序/模态/λ/图灵机/类型）")
    print("  第 2 层悖论：算不清的当第一公民（测量→注解→钻墙五选一→创生）")
    print("  第 3 层冷门：矛盾该共存（四值）/立场谁站得住（Dung）——按痛点选")
    print("  数学底座：自指程序（Kleene）/真值修正（Gupta-Belnap）——借鉴标注")
    print("  AI 挂载：引擎 = 23+ 个可调用工具——诊断留给使用者（只诊断不决策）")
    print("  只诊断不决策：把判断留给使用它的人。")
    print("更多：见 README.md + docs/ROADMAP.md")
    print("=" * 62)


if __name__ == "__main__":
    main()
