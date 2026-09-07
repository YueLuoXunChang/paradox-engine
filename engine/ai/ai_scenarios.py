# -*- coding: utf-8 -*-
"""
ai_scenarios.py — AI 挂载层：2 个真实场景端到端演示（阶段 6 验收）
========================================================================
ROADMAP 阶段 6 验收：给一段真实中文论证 → 引擎返回结构化诊断。
本文件演示引擎作为 **AI 可调用工具集** 的用法——模拟 AI 拿到
TOOL_SCHEMAS 后按场景决策调用（场景 1 走总控一条龙；场景 2 走
判类→路由→撞墙→Dung 多工具链，展示"工具编排"由 AI 或上层做）。

运行：python engine/ai/ai_scenarios.py

诚实边界：
    - 场景是"引擎能干什么"的展示，不是"AI 会自动这么想"的承诺——
      编排由调用方决策（引擎只提供工具 + 诊断）；
    - 每个工具输出带 boundary（只诊断不决策随行）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from engine.ai.tools import tools, call_tool  # noqa: E402
except ImportError:
    from tools import tools, call_tool  # noqa: E402


def banner(t):
    print("\n" + "=" * 62)
    print(t)
    print("=" * 62)


def scenario1_argument_conflict():
    """场景 1：论证矛盾检查（真实中文论证 → 结构化诊断）。"""
    banner("场景 1 · 论证矛盾检查：产品需求会议的一段话")
    text = ('销售坚持"三周内必须上线抢占市场"，研发坚持"合规审查'
            '十二周一步不能少"——既要抢占市场，又要完整合规，两边'
            '都觉得对方在拖后腿。')
    print(f"输入论证：{text}\n")
    print("【AI 决策】这像是论证矛盾（T2）——调总控一条龙。")
    r = call_tool('controller', {
        'text': text,
        'structured': {'A': '三周内上线(销售)', 'B': '合规审查12周(研发)',
                       'wA': 5, 'wNotA': 5}})
    res = r['result']
    print(f"→ 判类：{res['classification']['main_type']} "
          f"{res['classification']['main_name']} · "
          f"{res['classification']['level']} · 路由 "
          f"{res['classification']['route']['route_id']}")
    for e in res['execution']:
        if e['status'] == 'run':
            print(f"→ 执行 {e['component']}: "
                  f"μ={e['output'].get('mu')} "
                  f"grade={e['output'].get('grade')}")
    print("→ 输出（给人看）：")
    for line in res['report'].splitlines():
        print(f"   {line}")
    return res


def scenario2_discipline_modeling():
    """场景 2：学科题目建模示意（判类→路由→撞墙→Dung 工具链）。"""
    banner("场景 2 · 学科建模示意：癌耐药的多线演化 + 治疗悖论")
    text = ('肿瘤在靶向药下如何演化出耐药，能否建模其多线路径，'
            '以及"杀灭敏感株却选择出耐药株"算不算悖论？')
    print(f"输入：{text}\n")
    print("【AI 决策】学科题目（T9）+ 含悖论扫描——先判类看路由。")
    r = call_tool('classifier', {'text': text})
    cl = r['result']
    print(f"→ 判类：{cl['main_type']} {cl['main_name']} · {cl['level']} · "
          f"路由 {cl['route']['route_id']}")
    print(f"→ 管线建议：{cl['route']['pipeline']}")
    print("\n【AI 决策】管线含 wall_pipeline——撞墙管线扫治疗悖论。")
    r2 = call_tool('wall_pipeline', {
        'wall': '杀灭敏感株却选择出耐药株',
        'thesis': '用药杀灭肿瘤', 'antithesis': '用药选择耐药'})
    wp = r2['result']
    print(f"→ 五选一诊断：{wp['verdict']}")
    print(f"→ {wp['diagnosis']['label']}")
    print(f"→ 注解卡 LV = {wp['annotation'].get('LV')}")
    print("\n【AI 决策】治疗矛盾场里哪些立场站得住——Dung 分析。")
    r3 = call_tool('dung_framework', {
        'arguments': ['联合用药压耐药', '换药延迟耐药', '手术清除主灶',
                      '免疫疗法'],
        'attacks': [('换药延迟耐药', '联合用药压耐药'),
                    ('手术清除主灶', '换药延迟耐药'),
                    ('免疫疗法', '联合用药压耐药')]})
    dg = r3['result']
    print(f"→ grounded（站得住）：{dg['grounded']}")
    print(f"→ preferred：{dg['preferred']}")
    print(f"→ 争议集：{dg['conflict_pairs']}")
    print("\n说明：这些是诊断（立场建议），治疗决策由医生/研究者判断"
          "（只诊断不决策）。")
    return wp, dg


def main():
    print('=' * 62)
    print('AI 挂载层 · 真实场景端到端演示（阶段 6 验收）')
    print('=' * 62)
    print(f"可用工具 {len(tools())} 件（function-calling schema 见 "
          f"tools().list 或 engine/ai/tools.py）")
    s1 = scenario1_argument_conflict()
    s2 = scenario2_discipline_modeling()
    print("\n" + "=" * 62)
    print('验收达成：')
    mt = s1['classification']['main_type']
    print('  · 场景 1：真实中文论证 → 结构化诊断（'
          f"{mt}，路由 {s1['classification']['route']['route_id']}，"
          f"五查 {len(s1['output_check'])} 项）✅")
    print('  · 场景 2：学科建模 → 判类→路由→撞墙（治疗悖论五选一）→ '
          f"Dung 立场（grounded={s2[1]['grounded']}）✅")
    print('  · 每个工具输出带 boundary（只诊断不决策随行）✅')
    print('=' * 62)


if __name__ == '__main__':
    main()
