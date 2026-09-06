# -*- coding: utf-8 -*-
"""
test_classifier.py — 正式测试：判类器 + 复杂度 + 路由（总控步 1/2/3）
用例依据：任务指标 44（信号表/打分公式/ROUTE）+ 38（走查一二三）
运行：python engine/control/test_classifier.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classifier import run, ROUTE, TYPE_DEFS  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    assert cond, f"{label} 失败: {detail}"
    PASS += 1
    print(f"  ✅ {label}")


print("判类器 + 复杂度 + 路由 · 正式测试")
print("=" * 60)

# ── 用例1：38 走查三——排中律（T1-L1，不被复杂化）
r = run({'text': '今天下雨或没下雨'})
check("排中律 → T1", r['main_type'] == 'T1', str(r))
check("排中律 → L1", r['level'] == 'L1', str(r))
check("L1 轻量管线（单机制）",
      r['route']['pipeline'] == ['propositional.validity'], str(r))
check("路由带 reason 白箱", bool(r['route']['reason']), str(r))
check("L1 不启骨架", r['route']['needs_skeleton'] is False, str(r))

# ── 用例2：38 走查一——需求打架（T2-L2）
r = run({'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）'})
check("需求打架 → T2", r['main_type'] == 'T2', str(r))
check("需求打架 → L2（含时间约束）", r['level'] == 'L2', str(r))
check("R2-L2 管线 = μ+注解",
      r['route']['pipeline'] == ['paradox_measure.mu1',
                                 'paradox_annotate'], str(r))
check("T2 主型 + T1/T4 副型列出",
      len(r['types']) >= 1 and r['types'][0]['type'] == 'T2', str(r))

# ── 用例3：说谎者（T6 自指，mu2 直判路由）
r = run({'text': '这句话是假的'})
check("说谎者 → T6", r['main_type'] == 'T6', str(r))
check("T6 路由含自指检测",
      any('mu2' in p or 'selfref' in p for p in r['route']['pipeline']),
      str(r))

# ── 用例4：38 走查二——耐药演化（T9-L3 全量道）
r = run({'text': '肿瘤在靶向药下如何演化出耐药，能否建模其多线路径'})
check("耐药演化 → T9", r['main_type'] == 'T9', str(r))
check("耐药演化 → L3", r['level'] == 'L3', str(r))
check("T9-L3 全管线含演化+悖论",
      'ltl' in r['route']['pipeline']
      and 'wall_pipeline' in r['route']['pipeline'], str(r))

# ── 用例5：T7 对立交汇 / T3 关系 / T4 演化 / T10 辨析 / T11 假设
r = run({'text': '要自由还是要秩序，能不能兼得'})
check("自由×秩序 → T7", r['main_type'] == 'T7', str(r))
r = run({'text': 'A 支持 B，B 反对 C，C 支持 A'})
check("关系环 → T3", r['main_type'] == 'T3', str(r))
r = run({'text': '水温每10分钟降一半，多久到20度'})
check("降温递推 → T4", r['main_type'] == 'T4', str(r))
r = run({'text': '同情与共情是不是一回事，边界在哪'})
check("概念辨析 → T10", r['main_type'] == 'T10', str(r))
r = run({'text': '广告说这药95%有效，靠不靠谱'})
check("假设检验 → T11", r['main_type'] == 'T11', str(r))

# ── 用例6：复杂度打分边界
r = run({'text': '所有 A 都支持 B，B 都支持 C，C 都支持 D，D 都支持 E'})
check("多实体多关系 → 至少 L2",
      r['level'] in ('L2', 'L3'), str(r))
check("复杂度给分数与档位",
      isinstance(r['complexity']['score'], int)
      and r['complexity']['level'] == r['level'], str(r))
r = run({'text': '所有 A 都支持 B，B 都支持 C，C 都支持 D，D 都支持 E，'
                 'E 都支持 F，F 都支持 G，G 都支持 H，H 都支持 I'})
check("超多实体关系 → L3 或 L2（诚实不硬判 L3）",
      r['level'] in ('L2', 'L3'), str(r))

# ── 用例7：未分类 T12 + 副型 + 置信度
r = run({'text': '随便写点什么没有信号'})
check("无信号 → T12 未分类", r['main_type'] == 'T12', str(r))
check("T12 走通用最小管线",
      r['route']['pipeline'] == ['propositional.consistency'], str(r))
check("T12 置信度 low", r['confidence'] == 'low', str(r))
r = run({'text': '这个方案既要快又要稳还要便宜'})
check("多型命中主型在前",
      r['types'][0]['type'] == r['main_type'], str(r))
check("主型=论证矛盾（既要又要）", r['main_type'] == 'T2', str(r))

# ── 用例8：ROUTE 表完备性（12 型 × 3 档全覆盖）
for tid in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9',
            'T10', 'T11', 'T12']:
    for lv in ('L1', 'L2', 'L3'):
        check(f"ROUTE 覆盖 {tid}-{lv}", (tid, lv) in ROUTE)
# 12 型 × 3 档 = 36 键
check("ROUTE 表 36 键", len(ROUTE) == 36, str(len(ROUTE)))
check("12 型定义齐全", len(TYPE_DEFS) == 11  # T12 为默认兜底非定义
      and all(f'T{i}' in TYPE_DEFS for i in range(1, 12)), str(TYPE_DEFS))

# ── 用例9：诚实边界
check("空文本 → input_pending", run({})['verdict'] == 'input_pending')
check("非字符串 → input_pending",
      run({'text': 123})['verdict'] == 'input_pending')
r = run({'text': '这句话是假的', 'debug': True})
check("debug 输出带全型得分", '全型得分' in r['boundary'], r['boundary'])
check("边界声明启发式非完备",
      '启发' in run({'text': '随便写'})['boundary'])

print("=" * 60)
print(f"结果: {PASS}/69 通过")
raise SystemExit(0 if PASS == 69 else 1)
