# -*- coding: utf-8 -*-
"""
test_model_check.py — 正式测试：CTL 模型检查（显式 Kripke 结构）
用例依据：第 1 层可判定片段（Clarke–Emerson 1981 标记算法）——时序性质可算
运行：python engine/classical/test_model_check.py
"""
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.classical.model_check import MUTEX, run  # noqa: E402

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


def q(formula, **kw):
    return run(dict(dict(MUTEX, **kw), formula=formula))


print("CTL 模型检查 · 正式测试")
print("=" * 60)

check("互斥不变式 AG !(c1 & c2) 成立（结构里进不去临界区并存）",
      q('AG !(c1 & c2)')['verdict'] == 'holds')
check("EF c1 成立（存在路径能进临界区）",
      q('EF c1')['verdict'] == 'holds')
check("AF c1 不成立（可以一直不进——存在环形路径）",
      q('AF c1')['verdict'] == 'fails')
check("路径量词有区别：E[!c1 U c2] 成立而 A[!c1 U c2] 不成立",
      q('E[!c1 U c2]')['verdict'] == 'holds'
      and q('A[!c1 U c2]')['verdict'] == 'fails')
check("响应性 AG (c1 -> AF !c1) 成立（占着就一定会放开）",
      q('AG (c1 -> AF !c1)')['verdict'] == 'holds')
check("EG c1 不成立（不可能永远占着）",
      q('EG c1')['verdict'] == 'fails')
check("sat_count 与结构一致（互斥不变式在全部 3 个状态成立）",
      q('AG !(c1 & c2)')['sat_count'] == 3,
      str(q('AG !(c1 & c2)').get('sat_count')))

check("LTL 写法（G c1）诚实报 parse_error——本构件只管 CTL",
      q('G c1')['verdict'] == 'parse_error', q('G c1').get('explanation'))
check("迁移引用了未声明状态 → input_pending（不猜）",
      q('AG c1', transitions=[['n1n2', 'XX']])['verdict'] == 'input_pending')
check("labels 里有未声明状态 → input_pending",
      q('AG c1', labels={'n1n2': [], 'ghost': ['c1']})['verdict']
      == 'input_pending')
check("缺 states / 缺 formula 都诚实拦下",
      run({'formula': 'AG c1'})['verdict'] == 'input_pending'
      and run({'states': ['a'], 'transitions': []})['verdict']
      == 'input_pending')
check("init 不在状态集里 → input_pending",
      q('AG c1', init=['nope'])['verdict'] == 'input_pending')
check("死锁状态上全称算子按空集真（标准约定，写在边界里）",
      run({'states': ['d'], 'transitions': [], 'labels': {'d': []},
           'formula': 'AX c1', 'init': ['d']})['verdict'] == 'holds')
r = q('AG !(c1 & c2)')
check("边界文本含关键声明",
      '相对给定' in r['boundary'] and 'LTL' in r['boundary'])
check("确定性：同一输入两次结论一致",
      q('AF c1')['verdict'] == q('AF c1')['verdict'])

print("=" * 60)
print(f"结果: {PASS}/15 通过")
raise SystemExit(0 if PASS == 15 else 1)
