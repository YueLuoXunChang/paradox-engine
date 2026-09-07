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

# ── 用例9：诚实边界
check("空文本 → input_pending", run({})['verdict'] == 'input_pending')
check("非字符串 → input_pending",
      run({'text': 42})['verdict'] == 'input_pending')
check("边界声明含不下决策",
      '不下决策' in run({'text': 'x', 'structured': {}})['boundary'])
r = run({'text': '这句话是假的'})
check("T6 无结构化 → 至少诚实执行或缺输入",
      r['verdict'] in ('done', 'classified_only'), str(r))

print("=" * 60)
print(f"结果: {PASS}/35 通过")
raise SystemExit(0 if PASS == 35 else 1)
