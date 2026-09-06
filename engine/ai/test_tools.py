# -*- coding: utf-8 -*-
"""
test_tools.py — 正式测试：AI 挂载层（function-calling 封装）
用例依据：ROADMAP 阶段 6（引擎函数=AI 可调用工具 + schema 与 PORTS 一致）
运行：python engine/ai/test_tools.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import tools, call_tool, run  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("AI 挂载层 · 正式测试")
print("=" * 60)

# ── 用例1：工具清单完整性
tl = tools()
check("工具清单 23 件", len(tl) == 23, str(len(tl)))
names = [t['function']['name'] for t in tl]
check("含悖论/经典/骨架/冷门/总控全层工具",
      all(n in names for n in ('paradox_measure', 'wall_pipeline',
                               'propositional', 'stlc', 'mtmp',
                               'dung_framework', 'controller')), str(names))
check("每工具带 description", all(t['function']['description']
      for t in tl), str(tl[0]))
check("每工具 parameters 是 object schema",
      all(t['function']['parameters']['type'] == 'object' for t in tl))
check("每工具 properties 为 dict",
      all(isinstance(t['function']['parameters']['properties'], dict)
          for t in tl))

# ── 用例2：schema 与 PORTS 一致性（抽查 3 工具）
pm = next(t for t in tl if t['function']['name'] == 'paradox_measure')
check("paradox_measure schema 字段 = mode/wA/wNotA",
      set(pm['function']['parameters']['properties']) ==
      {'mode', 'wA', 'wNotA'}, str(pm))
check("mode 必填", pm['function']['parameters']['required'] == ['mode'],
      str(pm))
dg = next(t for t in tl if t['function']['name'] == 'dung_framework')
check("dung schema 字段 = arguments/attacks/max_arguments",
      set(dg['function']['parameters']['properties']) ==
      {'arguments', 'attacks', 'max_arguments'}, str(dg))
ct = next(t for t in tl if t['function']['name'] == 'controller')
check("controller schema 字段 = text/structured/debug",
      set(ct['function']['parameters']['properties']) ==
      {'text', 'structured', 'debug'}, str(ct))

# ── 用例3：call_tool 分派（多工具抽查）
r = call_tool('paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5})
check("μ 调用 → ok", r['verdict'] == 'ok', str(r))
check("μ=1.0", abs(r['result']['mu'] - 1.0) < 1e-9, str(r))
check("结果带 _tool 白箱", r['result'].get('_tool') == 'paradox_measure',
      str(r))
check("结果带 _input 回显", r['result'].get('_input') ==
      {'mode': 'mu1', 'wA': 5, 'wNotA': 5}, str(r))
r = call_tool('wall_pipeline', {'wall': '这句话是假的'})
check("撞墙管线调用 → resonance_selfref",
      r['result']['verdict'] == 'resonance_selfref', str(r))
r = call_tool('dung_framework',
              {'arguments': ['a', 'b', 'c'],
               'attacks': [('a', 'b'), ('b', 'c')]})
check("Dung 调用 → grounded=[a,c]",
      r['result']['grounded'] == ['a', 'c'], str(r))
r = call_tool('belnap_four', {'formula': 'A∧¬A', 'assign': {'A': 'B'}})
check("Belnap 调用 → 两者 B", r['result']['value'] == 'B', str(r))
r = call_tool('stlc', {'expr': 'λx:A.x x'})
check("STLC 调用 → 拦自应用 type_error",
      r['result']['verdict'] == 'type_error', str(r))

# ── 用例4：总控调用（真实中文论证端到端）
r = call_tool('controller', {
    'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
    'structured': {'A': '尽快上线(3周)', 'B': '完整覆盖合规(12周)',
                   'wA': 5, 'wNotA': 5}})
check("总控调用 → ok", r['verdict'] == 'ok', str(r))
check("总控判 T2", r['result']['classification']['main_type'] == 'T2',
      str(r))
check("总控路由 R2-L2",
      r['result']['classification']['route']['route_id'] == 'R2-L2', str(r))
check("总控五查齐全", len(r['result']['output_check']) == 5, str(r))
check("总控报告中文含【类型】", '【类型】' in r['result']['report'],
      str(r))

# ── 用例5：缺参透传（诚实拦截）
r = call_tool('selfref_fixpoint', {})
check("缺参 → 构件 input_pending",
      r['result']['verdict'] == 'input_pending', str(r))
check("input_pending 带诚实边界", 'boundary' in r['result'], str(r))
r = call_tool('propositional', {})
check("propositional 缺参 → formula_pending 或拦截",
      r['result']['verdict'] in ('formula_pending', 'premises_pending'),
      str(r))

# ── 用例6：run 统一入口
r = run({'action': 'list'})
check("run list → tools_listed", r['verdict'] == 'tools_listed', str(r))
check("run list 带 23 工具", len(r['tools']) == 23, str(r))
r = run({'action': 'call', 'name': 'converge_check'})
check("run call 缺参 → 构件 input_pending 透传", r['verdict'] == 'ok'
      and r['result']['result']['verdict'] == 'input_pending', str(r))
check("run 边界声明不伪造输入",
      '不伪造' in run({'action': 'call', 'name': 'paradox_measure'})
      ['boundary'], str(r))

# ── 用例7：诚实边界
check("未知工具 → tool_unknown",
      call_tool('nope', {})['verdict'] == 'tool_unknown')
check("未知工具带可用清单", '可用' in
      str(call_tool('nope', {})), str(call_tool('nope', {})))
check("call 缺 name → input_pending",
      run({'action': 'call'})['verdict'] == 'input_pending')
check("坏 action → input_pending",
      run({'action': 'xx'})['verdict'] == 'input_pending')
check("边界声明：只诊断不决策随行",
      '只诊断' in run({'action': 'list'})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/34 通过")
raise SystemExit(0 if PASS == 34 else 1)
