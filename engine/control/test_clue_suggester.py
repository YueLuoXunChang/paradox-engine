# -*- coding: utf-8 -*-
"""
test_clue_suggester.py — 正式测试：结构化线索建议
用例依据：诊断工作台第 0 米摩擦（缺结构化线索用不起来）+ 诚实边界
         （建议要人确认、不产生逻辑式、不替人估权重、不自动应用）
运行：python engine/control/test_clue_suggester.py
"""
import hashlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from engine.control.clue_suggester import run as suggest  # noqa: E402
from engine.control.classifier import run as cl  # noqa: E402

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


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


TXT_T2 = '产品既要三周上线又要十二周合规，销售和研发各执一词'
TXT_T6 = '这句话是假的，越绕越深'
TXT_TRUTH = '这句话是真的，那它到底算不算真'
TXT_GODEL = '这个命题不可证明，也就是说它在系统内无法被证明'
TXT_T1 = '所有员工都买了保险，小李是员工，那小李买了保险吗'
TXT_L3 = ('这道题要求建模：先说清机制与理论模型，再讨论系统演化与多条通路，'
          '为什么产量导致成本上升，库存导致资金占用，广告导致需求波动，'
          '汇率促进出口，税率抑制投资，监管抑制加急，审计隶属法务，'
          '这条通路隶属主系统，另有一条通路隶属备用模型；'
          '报告说这套模型有效，另一份报告说无效，数据互相矛盾；'
          '方案既要三周上线，又要十二周合规')

print("结构化线索建议 · 正式测试")
print("=" * 60)

scen = os.path.join(_HERE, '..', 'scenarios', 'scenarios.py')
scen_sha = sha(os.path.normpath(scen))

# ── 用例1：T2（矛盾两方）能从原文里指出来
r = suggest({'text': TXT_T2})
check("T2 文本 → verdict=suggested", r['verdict'] == 'suggested', r['verdict'])
flat = {s['key']: s for c in r['components'] for s in c['ready']}
check("建议里有 A / B 两方", 'A' in flat and 'B' in flat, str(sorted(flat)))
check("A / B 是原文里的词（照原文用词，不编）",
      flat['A']['value'] in TXT_T2 and flat['B']['value'] in TXT_T2,
      str(flat))
check("每项建议都带依据与「是猜测」标记",
      all(s['why'] and s['is_guess'] is True for s in flat.values()), str(flat))
check("建议值里不出现逻辑符号（不产生公式）",
      not any(ch in s['value'] for s in flat.values()
              for ch in ('→', '∧', '∨', '¬')),
      str([s['value'] for s in flat.values()]))

# ── 用例2：人的判断不替人估
mu = [c for c in r['components'] if c['component'] == 'paradox_measure.mu1'][0]
check("证据权重 wA/wNotA 落进「需人给」",
      {x['key'] for x in mu['need_human']} == {'wA', 'wNotA'},
      str(mu['need_human']))
check("写明理由是「不替人估」",
      all('不替人估' in x['reason'] for x in mu['need_human']),
      str(mu['need_human']))
check("有默认值的构件仍不把默认值当建议给人",
      mu['has_defaults'] is True and mu['ready'] == [], str(mu))

# ── 用例3：自指句类型
for txt, want in ((TXT_T6, 'liar'), (TXT_TRUTH, 'truth_teller'),
                  (TXT_GODEL, 'godel')):
    rr = suggest({'text': txt})
    vals = [s['value'] for c in rr['components'] for s in c['ready']
            if s['key'] == 'sentence']
    check(f"自指句建议 sentence={want}", vals == [want], str(vals))

# ── 用例4：命题式一律需人给（引擎不抽公式）
r1 = suggest({'text': TXT_T1})
need1 = {x['key']: x['reason'] for c in r1['components']
         for x in c['need_human']}
check("T1 的 premises/conclusion 落进「需人给」",
      'premises' in need1 and 'conclusion' in need1, str(need1))
check("写明理由是「引擎不抽公式」",
      all('不抽公式' in v for k, v in need1.items()
          if k in ('premises', 'conclusion')), str(need1))
check("无建议时 verdict=no_suggestion（不硬凑）",
      r1['verdict'] == 'no_suggestion', r1['verdict'])

# ── 用例5：构件清单与实际路由一致（不凭空列构件）
r3 = suggest({'text': TXT_L3})
route = cl({'text': TXT_L3})['route']
check("组件列表 = 实际路由 pipeline（逐项一致）",
      [c['component'] for c in r3['components']] == route['pipeline'],
      str([c['component'] for c in r3['components']]))
check("每个构件都把引擎自己的 hint 摆出来",
      all(c['hint'] for c in r3['components']), str(r3['components']))
wall = [s for c in r3['components'] if c['component'] == 'wall_pipeline'
        for s in c['ready']]
check("撞墙管线的 wall 由命中句式的两方拼出",
      wall and wall[0]['key'] == 'wall' and '与' in wall[0]['value'],
      str(wall))
check("need_human 的键不重复且都来自该构件所需",
      all(len({x['key'] for x in c['need_human']})
          == len(c['need_human']) for c in r3['components']))

# ── 用例6：可粘贴片段能直接用（合并后是合法 JSON）
merged = {}
for kv in r3['paste'].values():
    merged.update(kv)
check("paste 合并后是合法 JSON 且有内容",
      bool(merged) and isinstance(json.loads(json.dumps(merged)), dict),
      str(merged))
check("paste 里只放建议项，不放需人给项",
      set(merged) <= {s['key'] for c in r3['components']
                      for s in c['ready']}, str(sorted(merged)))

# ── 用例7：诚实拦截与边界
check("缺文本 → input_pending", suggest({})['verdict'] == 'input_pending')
check("文本非字符串 → input_pending",
      suggest({'text': 5})['verdict'] == 'input_pending')
check("空串 → input_pending",
      suggest({'text': '   '})['verdict'] == 'input_pending')
check("inputs 非 dict → input_pending",
      suggest('x')['verdict'] == 'input_pending')
check("边界写明「要人确认」与「不自动应用」",
      '要人确认' in r['boundary'] and '不会自动应用' in r['boundary'],
      r['boundary'])
check("返回里没有『已应用』这类字段（建议不落到引擎里）",
      'applied' not in r and 'auto_applied' not in r, str(sorted(r)))

# ── 用例8：建议器只读，不碰仓库文件
check("跑完建议后场景表 sha256 未变（只读）", sha(os.path.normpath(scen))
      == scen_sha)

print("=" * 60)
print(f"结果: {PASS}/27 通过")
raise SystemExit(0 if PASS == 27 else 1)
