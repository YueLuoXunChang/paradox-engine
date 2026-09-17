# -*- coding: utf-8 -*-
"""
decidability_map.py — 算术层级 · 可判定片段地图（阶段 7 数学底座 / 墙的精确地图）
================================================================================
概念来源：**外部经典共识**——可判定性与算术层级（Gödel 1931 不完备、
Church 1936 / Turing 1936 不可判定、Presburger 1929 可判定算术、
Kripke 1963/1965 模态与直觉主义可判定、Pnueli 1977 / Sistla-Clarke 1985
时序可判定、Thomason 1975 一般框架不可判定、Löwenheim 1915 一元谓词可判、
Soare 递归论层级完全性）。本构件为**借鉴实现**（落落三问：借什么=判定性
结论与算术层级这套"墙的地图"；为什么=引擎的分层主张"经典能算的算清、
算不清的当第一公民"需要一个**可查的边界依据**——不然"算不清"只是说法，
有了这张图就能说清"为什么算不清、算不清到哪一层、有没有可判的替身"；
怎么记账=来源逐条标注归借鉴区）。
蓝图：45 长期架构蓝图 轨 A · A1（算术层级——借数学底座，标注来源）验收：
自测 + 正式测试 + docstring 公式卡 + 与 1.6 λ演算 / 1.7 图灵机 / 2.3 递归修正
接线演示。

本构件做什么（一句话）：
    给"这个问题能不能算"一个可查可跑的答案——四个能力：
    ① **片段查询**（mode='lookup'）：按逻辑系统/问题名查判定结论 + 复杂度 +
       出处 + **引擎里有没有对应构件**（有就跑得动，没有就诚实说没有）；
    ② **层级查询**（mode='hierarchy'）：算术层级 Δ1/Σ1/Π1/Σ2/Π2 的定义、
       完全问题代表、以及**引擎在每层承诺什么**（可判定给结论；
       只有 Σ1 能"枚举到才说是"；更高层不承诺）；
    ③ **地图总览**（mode='map'）：整张城墙地图（可判/半可判/不可判分组）；
    ④ **接线演示**（mode='demo'）：真跑引擎构件，把"能算的"和"算不清的"
       摆在一起（1.6 λ / 1.7 图灵机 / 2.3 递归修正 / 命题逻辑 / 直觉主义）。

与引擎分层主张的关系（这张图是"只诊断不决策"的依据）：
    - Δ1（可判定）→ 引擎**给是/否结论**（如命题逻辑、LTL、Presburger 类）；
    - Σ1（递归可枚举）→ 引擎只能"枚举到就给是"（如停机：跑出来停就是停），
      枚举不到**不给否**；
    - Π1 及以上 → 引擎不承诺结论，只做诊断与诚实报告（挡在门口）。

诚实边界：
    - 本表是**人工整理的参考文献表**，不是判定过程：它回答"这一类问题学界
      结论是什么"，不替你判某个具体式子；
    - 表里 engine_component 为 None 的条目 = 引擎**没有**对应构件
      （诚实标注"未实现"，绝不假装能算）；标了构件的条目保证能 import 并
      真跑（有测试兜底）；
    - 复杂度栏只在文献有公认结论时填写；不确定就留空，不猜。

统一接口：
    run(inputs: dict) -> dict
    输入:
        mode: 'lookup'|'hierarchy'|'map'|'demo'（默认 lookup）
        system: str（lookup 用：片段/问题名，如 'propositional'）
        level: str（hierarchy 用：'Δ1'|'Σ1'|'Π1'|'Σ2'|'Π2'）
    输出:
        verdict: str——'found'|'level_found'|'mapped'|'demo'
                        |'unknown_system'|'unknown_level'|'input_pending'
        entry: dict——片段条目（lookup）
        level: dict——层级条目（hierarchy）
        fragments: list——地图条目（map/demo）
        boundary: str——诚实边界声明
"""

PORTS = {
    'in': {'mode': 'str?', 'system': 'str?', 'level': 'str?'},
    'out': {'verdict': 'str', 'entry': 'dict', 'level': 'dict',
            'fragments': 'list', 'boundary': 'str'},
}

import os
import sys

# 路径引导（本仓所有构件的统一开头）：脚本方式运行时也保证
# `import engine.*` 解析到**本仓库**——本机若同时 editable 装了别的项目、
# 其顶层包名也叫 engine，不钉这一下会静默加载到别人的代码。
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 判定性取值：可判定 / 半可判定（只一侧可枚举）/ 不可判定
DECIDABLE = 'decidable'
SEMI = 'semi_decidable'
UNDECIDABLE = 'undecidable'

_DECIDABILITY_CN = {
    DECIDABLE: '可判定（Δ1：有算法在有限步内给是/否）',
    SEMI: '半可判定（只有一个方向可枚举）',
    UNDECIDABLE: '不可判定（无算法；有数学定理兜底）',
}

# ══════════════════════════════════════════════════════════════
# 一、墙体地图：逻辑片段 / 判定问题 → 判定结论（借鉴区，逐条标源）
# ══════════════════════════════════════════════════════════════
# 字段：
#   name            中文名
#   decidability    decidable / semi_decidable / undecidable
#   hierarchy       算术层级位置（Δ1/Σ1/Π1/Σ2/Π2）
#   complexity      复杂度（有公认结论才填，否则 None）
#   source          出处（借鉴区标注）
#   engine_component 引擎里对应构件（module path）或 None（= 未实现，诚实）
#   engine_note     引擎侧的诚实说明（能做多少、不能做多少）
#   note            一句话要点

FRAGMENTS = {
    'propositional': {
        'name': '命题逻辑', 'decidability': DECIDABLE, 'hierarchy': 'Δ1',
        'complexity': 'SAT 为 NP 完全；有效性与可满足性互归约',
        'source': '经典共识（Cook 1971 的 NP 完全性）',
        'engine_component': 'classical.propositional',
        'engine_note': '真值表枚举判定（原子数上限 10，超限诚实报 '
                       'size_limit——算不动≠不可判定）',
        'note': '有限搜索即可判定：引擎最底层、最可靠的"能算的算清"。',
    },
    'first_order': {
        'name': '一阶逻辑（一般）', 'decidability': UNDECIDABLE,
        'hierarchy': 'Σ1（有效式集合递归可枚举；不可满足式亦递归可枚举）',
        'complexity': None,
        'source': 'Church 1936 / Turing 1936（判定问题不可解）',
        'engine_component': 'classical.first_order',
        'engine_note': '引擎只做**有限论域展开**（可判片段）——一般一阶逻辑'
                       '不承诺判定；这正是"墙"的第一块砖',
        'note': '一半可枚举：证明能枚举到（有效就证出来），"无效"给不出。',
    },
    'monadic_fol': {
        'name': '一元谓词一阶逻辑（monadic）', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1', 'complexity': 'NEXPTIME 完全',
        'source': 'Löwenheim 1915 / 表列法经典结果',
        'engine_component': None,
        'engine_note': '引擎**未实现**（诚实标注：不假装能算）',
        'note': '去掉二元以上谓词，一阶逻辑立刻变可判——可判片段的典型。',
    },
    'presburger': {
        'name': 'Presburger 算术（自然数 + 加法）', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1', 'complexity': '超指数下界（Fischer-Rabin 1974）',
        'source': 'Presburger 1929',
        'engine_component': None,
        'engine_note': '引擎**未实现**；蓝图列为按需扩展项',
        'note': '有加法无数乘 → 可判；一旦加上乘法就掉进不可判（见 PA）。',
    },
    'full_arithmetic': {
        'name': '一阶皮亚诺算术 PA（加法 + 乘法）',
        'decidability': UNDECIDABLE,
        'hierarchy': '不可判定；真算术更超出 Σ1/Π1（Tarski 不可定义）',
        'complexity': None,
        'source': 'Gödel 1931（不完备）；Tarski 1936（真不可定义）',
        'engine_component': None,
        'engine_note': '引擎**不做**——这是本引擎明确不碰的领域（诚实划界）',
        'note': '乘法一加，判定性与完备性双失——"墙"的核心段落。',
    },
    'halting': {
        'name': '停机问题', 'decidability': UNDECIDABLE,
        'hierarchy': 'Σ1 完全（K = {e : φ_e(e)↓}）',
        'complexity': None,
        'source': 'Turing 1936；Σ1 完全性（Soare 递归论标准结果）',
        'engine_component': 'classical.turing_machine',
        'engine_note': '引擎**演示**不可判定（模拟停机 + 对角化说明），'
                       '不是判定器',
        'note': '跑出来停就是停（Σ1 的"是"可枚举）；跑不停永远不知道。',
    },
    'untyped_lambda': {
        'name': '无类型 λ 演算（β 等价/停机）', 'decidability': UNDECIDABLE,
        'hierarchy': 'Σ1（可归约到停机问题）', 'complexity': None,
        'source': 'Church 1936',
        'engine_component': 'classical.lambda_calculus',
        'engine_note': '引擎做**归约演示**（β 归约/Y 不动点/诚实发散），'
                       '不判两式是否 β 等价',
        'note': '与图灵机等价的计算模型——同一堵墙的另一种砌法。',
    },
    'stlc': {
        'name': '简单类型 λ 演算（STLC）', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1（类型检查可判）', 'complexity': '类型检查线性时间',
        'source': 'Girard 1972 / Tait（强规范化）；Curry-Howard',
        'engine_component': 'classical.stlc',
        'engine_note': '引擎真跑类型检查（拦自应用），并演示"类型正确 ⇒ 终止"',
        'note': '加上类型就是可判的：类型把自应用挡在门外——对 1.6 的对照。',
    },
    'equality_tableau': {
        'name': '等词 + 无解释函数一阶片段', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1', 'complexity': 'NP 完全（等词逻辑）',
        'source': '经典共识（表列法/合一）',
        'engine_component': 'classical.equality_tableau',
        'engine_note': '引擎真跑：等词替换 + 表列法反例模型',
        'note': '可判片段的又一例：只有等词时判定可行。',
    },
    'resolution': {
        'name': '一阶归结（反证搜索）', 'decidability': SEMI,
        'hierarchy': 'Σ1（不可满足式可枚举：归结反证）', 'complexity': None,
        'source': 'Robinson 1965（归结原理）',
        'engine_component': 'classical.resolution',
        'engine_note': '引擎真跑 Skolem 化 + 合一 + 归结链；证不出来不等于'
                       '可满足（诚实标注）',
        'note': '只给"不可满足"这一侧——半可判定的教科书形态。',
    },
    'modal_k_s4_s5': {
        'name': '模态逻辑 K/T/S4/S5', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1', 'complexity': 'K: PSPACE 完全；S5: NP 完全',
        'source': 'Kripke 1963；Ladner 1977（复杂度）',
        'engine_component': 'classical.modal',
        'engine_note': '引擎真跑 Kripke 语义（K/T/S4/S5 框架自检）',
        'note': '框架一固定就可判；换成"任意框架"立刻不可判（见下条）。',
    },
    'modal_all_frames': {
        'name': '模态逻辑（任意框架下的有效性）', 'decidability': UNDECIDABLE,
        'hierarchy': 'Σ1（可归约自二阶逻辑/一阶判定问题）', 'complexity': None,
        'source': 'Thomason 1975（二阶逻辑归约到模态逻辑）',
        'engine_component': None,
        'engine_note': '引擎**不做**任意框架有效性（诚实划界）：只做具名框架',
        'note': '同一套语法，量化范围一变就跨过墙。',
    },
    'ltl': {
        'name': '线性时序逻辑 LTL', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1', 'complexity': 'PSPACE 完全（Sistla-Clarke 1985）',
        'source': 'Pnueli 1977；Sistla & Clarke 1985',
        'engine_component': 'classical.ltl',
        'engine_note': '引擎真跑 G/F/X/U 沿路径判定 + 违约定位',
        'note': '有界路径上判定可行——工程验证主流选择的原因。',
    },
    'intuitionistic_prop': {
        'name': '直觉主义命题逻辑', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1（有限模型性质：2^n 节点内完备）',
        'complexity': 'PSPACE 完全',
        'source': 'Kripke 1965（有限模型性质）',
        'engine_component': 'cold.intuitionistic_logic',
        'engine_note': '引擎真跑：Kripke 反模型搜索（完备界 2^n）+ 经典对照',
        'note': '构造性立场也可判——"不认排中律"不等于"算不出来"。',
    },
    'second_order': {
        'name': '二阶逻辑', 'decidability': UNDECIDABLE,
        'hierarchy': 'Σ1（有效性递归可枚举但不可判；无完备证明系统）',
        'complexity': None,
        'source': '经典共识（标准结果）',
        'engine_component': None,
        'engine_note': '引擎**不做**（诚实划界）',
        'note': '量化到谓词上 → 判定性与完备性同时失守。',
    },
    'belief_revision_finite': {
        'name': '有限信念集上的 AGM 修正', 'decidability': DECIDABLE,
        'hierarchy': 'Δ1（信念数上限内枚举子集）',
        'complexity': '枚举规模随信念数为组合级（引擎设上限）',
        'source': 'AGM 1985（本引擎按有限枚举实现）',
        'engine_component': 'cold.agm_revision',
        'engine_note': '引擎真跑最小放弃修正；超上限诚实报 size_limit',
        'note': '把"知识更新"限制在有限信念集内，就从哲学问题落成可算问题。',
    },
}

# ══════════════════════════════════════════════════════════════
# 二、算术层级：定义 + 完全问题代表 + 引擎承诺（借鉴区）
# ══════════════════════════════════════════════════════════════

HIERARCHY = {
    'Δ1': {
        'name': 'Δ1 · 可判定（递归）',
        'definition': '存在算法：对任何输入都在有限步内输出是/否。',
        'complete_problems': ['命题逻辑可满足性', 'Presburger 算术',
                              'LTL 模型检查', '直觉主义命题逻辑'],
        'engine_promise': '引擎**给结论**：能算的算清（这是第 1 层的立足点）。',
        'source': '经典共识（可计算性理论基础）',
    },
    'Σ1': {
        'name': 'Σ1 · 递归可枚举（r.e.）',
        'definition': '存在算法把成员一个个枚举出来（但停不下来时无法断言"不是"）。',
        'complete_problems': ['停机问题（Σ1 完全）', '一阶逻辑有效性',
                              '一阶不可满足性（归结反证）'],
        'engine_promise': '引擎**只在枚举到"是"时给结论**（e.g. 程序跑停了就是'
                          '停了）；枚举不到**不给否**——诚实标注"未判定"。',
        'source': 'Turing 1936；Σ1 完全性（Soare 递归论标准结果）',
    },
    'Π1': {
        'name': 'Π1 · 余递归可枚举（co-r.e.）',
        'definition': '其补集递归可枚举；即可以枚举"反例"的一侧。',
        'complete_problems': ['不停机问题（K 的补，Π1 完全）'],
        'engine_promise': '引擎**只给反例侧结论**：找到反例就否决；找不到不给肯定。',
        'source': '经典共识（K 的补 Π1 完全）',
    },
    'Σ2': {
        'name': 'Σ2',
        'definition': '形如 ∃x∀y R(x,y)（R 可判定）的语句类。',
        'complete_problems': ['Fin（程序定义域有限：Σ2 完全）'],
        'engine_promise': '引擎**不承诺**——超出承诺范围即诚实报"算不动"，'
                          '不硬给结果。',
        'source': 'Soare（Fin 的 Σ2 完全性）',
    },
    'Π2': {
        'name': 'Π2',
        'definition': '形如 ∀x∃y R(x,y)（R 可判定）的语句类。',
        'complete_problems': ['Tot（程序处处停机：Π2 完全）'],
        'engine_promise': '引擎**不承诺**（同上）；把它标出来，是为了让"算不清"'
                          '有精确名字。',
        'source': 'Soare（Tot 的 Π2 完全性）',
    },
}


def _entry_out(key, e):
    out = dict(e)
    out['system'] = key
    out['decidability_cn'] = _DECIDABILITY_CN[e['decidability']]
    out['engine_available'] = e.get('engine_component') is not None
    return out


def _lookup(system):
    if not system:
        return {'verdict': 'input_pending', 'entry': {}, 'level': {},
                'fragments': [],
                'boundary': 'mode=lookup 需 system（片段/问题名，如 '
                            "'propositional'/'halting'）——诚实拦截。可用键："
                            + '、'.join(sorted(FRAGMENTS))}
    e = FRAGMENTS.get(system)
    if e is None:
        return {'verdict': 'unknown_system', 'entry': {}, 'level': {},
                'fragments': [],
                'boundary': f'表中没有 {system!r} ——诚实报告（本表是人工整理的'
                            '参考文献表，不是完备清单）。可用键：'
                            + '、'.join(sorted(FRAGMENTS))}
    return {'verdict': 'found', 'entry': _entry_out(system, e), 'level': {},
            'fragments': [],
            'boundary': f'{e["name"]}：{_DECIDABILITY_CN[e["decidability"]]}。'
                        f'出处：{e["source"]}。引擎侧：{e["engine_note"]}'}


def _hierarchy(level):
    if not level:
        return {'verdict': 'input_pending', 'entry': {}, 'level': {},
                'fragments': [],
                'boundary': 'mode=hierarchy 需 level（Δ1/Σ1/Π1/Σ2/Π2）——诚实'
                            '拦截。可用层：' + '、'.join(HIERARCHY)}
    lv = HIERARCHY.get(level)
    if lv is None:
        return {'verdict': 'unknown_level', 'entry': {}, 'level': {},
                'fragments': [],
                'boundary': f'层级表里没有 {level!r}——诚实报告。可用层：'
                            + '、'.join(HIERARCHY)}
    out = dict(lv)
    out['level'] = level
    return {'verdict': 'level_found', 'entry': {}, 'level': out,
            'fragments': [],
            'boundary': f'{lv["name"]}：{lv["definition"]} 引擎承诺：'
                        f'{lv["engine_promise"]}（来源：{lv["source"]}）'}


def _map():
    groups = {}
    for k in sorted(FRAGMENTS):
        e = FRAGMENTS[k]
        groups.setdefault(e['decidability'], []).append(_entry_out(k, e))
    counts = {d: len(v) for d, v in groups.items()}
    boundary = ('墙的地图（借鉴区：外部经典共识，逐条标源）：可判定 '
                f'{counts.get(DECIDABLE, 0)} 条 / 半可判定 '
                f'{counts.get(SEMI, 0)} 条 / 不可判定 '
                f'{counts.get(UNDECIDABLE, 0)} 条。本表是参考文献表，不是'
                '判定过程——它说"这一类问题学界结论是什么"，不替你判具体式子；'
                'engine_component 为 None 的条目=引擎未实现（诚实标注）。')
    return {'verdict': 'mapped', 'entry': {}, 'level': {},
            'fragments': [x for d in (DECIDABLE, SEMI, UNDECIDABLE)
                          for x in groups.get(d, [])],
            'boundary': boundary}


def _demo():
    """
    接线演示（蓝图 A1 验收）：真跑引擎构件，把"能算的"和"算不清的"摆一起。
    1.6 λ 演算 / 1.7 图灵机 / 2.3 递归修正 + 可判片段（命题/直觉主义）对照。
    """
    import importlib
    rows = []
    plan = [
        ('命题逻辑（Δ1 可判）', 'classical.propositional',
         {'premises': ['P→Q', 'P'], 'conclusion': 'Q', 'mode': 'validity'}),
        ('直觉主义命题（Δ1 可判，见冷门 3.5）', 'cold.intuitionistic_logic',
         {'mode': 'countermodel', 'formula': 'P∨¬P'}),
        ('λ 演算（1.6：自应用无范式——β 等价不可判）',
         'classical.lambda_calculus', {'mode': 'self_apply'}),
        ('图灵机（1.7：停机不可判——Σ1 完全）',
         'classical.turing_machine', {'mode': 'halting_demo'}),
        ('递归修正（2.3：修正序列三态——可判的迭代）',
         'mechanisms.selfref_fixpoint', {'mode': 'sentence',
                                         'sentence': 'liar'}),
    ]
    for label, mod, args in plan:
        try:
            m = importlib.import_module(f'engine.{mod}')
            r = m.run(args)
            rows.append({'label': label, 'component': mod,
                         'verdict': r.get('verdict'),
                         'note': (r.get('boundary') or '')[:120]})
        except Exception as e:  # noqa: BLE001——构件缺失/参数不合就诚实报告
            rows.append({'label': label, 'component': mod,
                         'verdict': None,
                         'note': f'跑不动：{type(e).__name__}: {e}'})
    ok = sum(1 for x in rows if x['verdict'])
    return {'verdict': 'demo', 'entry': {}, 'level': {}, 'fragments': rows,
            'boundary': f'接线演示 {ok}/{len(rows)} 件真跑：可判片段给结论，'
                        '不可判片段只做诚实演示（图灵机停机演示 + λ 发散 + '
                        '修正序列三态）——同一张城墙地图的两侧。'}


def run(inputs):
    """
    做什么：查"这个问题能不能算"——片段判定结论 / 算术层级 / 墙体地图 / 接线演示。

    返回 dict（见模块 docstring）。"""
    mode = inputs.get('mode', 'lookup')
    if mode == 'lookup':
        return _lookup(inputs.get('system'))
    if mode == 'hierarchy':
        return _hierarchy(inputs.get('level'))
    if mode == 'map':
        return _map()
    if mode == 'demo':
        return _demo()
    return {'verdict': 'input_pending', 'entry': {}, 'level': {},
            'fragments': [],
            'boundary': f"mode 应为 lookup/hierarchy/map/demo，得到 {mode!r}"
                        '——诚实拦截'}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    try:  # 控制台自愈：Windows GBK 控制台打印 emoji（✅/⚠）会崩
        import sys as _sys
        _sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001——老版本/重定向流不支持就跳过
        pass

    print('=' * 68)
    print('算术层级 · 可判定片段地图 · 自测（阶段 7 数学底座）')
    print('=' * 68)

    # 1) 可判片段：命题逻辑
    r1 = run({'mode': 'lookup', 'system': 'propositional'})
    assert r1['verdict'] == 'found', r1
    assert r1['entry']['decidability'] == DECIDABLE, r1
    assert r1['entry']['engine_available'] is True, r1
    print(f"✅ 命题逻辑 → {r1['entry']['decidability']}"
          f"（引擎构件 {r1['entry']['engine_component']}）")

    # 2) 不可判片段：停机问题（Σ1 完全）
    r2 = run({'mode': 'lookup', 'system': 'halting'})
    assert r2['entry']['decidability'] == UNDECIDABLE, r2
    assert 'Σ1 完全' in r2['entry']['hierarchy'], r2
    print(f"✅ 停机问题 → {r2['entry']['decidability']}（{r2['entry']['hierarchy']}）")

    # 3) 未实现片段：诚实标 engine_component=None
    r3 = run({'mode': 'lookup', 'system': 'presburger'})
    assert r3['entry']['decidability'] == DECIDABLE, r3
    assert r3['entry']['engine_available'] is False, r3
    print(f"✅ Presburger（可判但引擎未实现）→ engine_available="
          f"{r3['entry']['engine_available']}（诚实标注，不假装能算）")

    # 4) 层级查询
    r4 = run({'mode': 'hierarchy', 'level': 'Σ1'})
    assert r4['verdict'] == 'level_found', r4
    assert '枚举' in r4['level']['engine_promise'], r4
    print(f"✅ 层级 Σ1 → 引擎承诺：{r4['level']['engine_promise'][:28]}…")

    # 5) 墙体地图
    r5 = run({'mode': 'map'})
    assert r5['verdict'] == 'mapped', r5
    n = len(r5['fragments'])
    print(f"✅ 墙体地图：{n} 条（可判/半可判/不可判三类）")

    # 6) 接线演示（1.6 λ / 1.7 图灵机 / 2.3 递归修正）
    r6 = run({'mode': 'demo'})
    assert r6['verdict'] == 'demo', r6
    print(f"✅ 接线演示：{len(r6['fragments'])} 件")
    for row in r6['fragments']:
        line = f"   · {row['label']} → {row['verdict']}"
        if not row['verdict']:
            line += f"（跑不动：{row['note']}）"
        print(line)
    assert all(row['verdict'] for row in r6['fragments']), r6['fragments']

    # 7) 边界
    r7 = run({'mode': 'xx'})
    assert r7['verdict'] == 'input_pending', r7
    r8 = run({'mode': 'lookup', 'system': '不存在的系统'})
    assert r8['verdict'] == 'unknown_system', r8
    r9 = run({'mode': 'hierarchy', 'level': 'Σ9'})
    assert r9['verdict'] == 'unknown_level', r9
    print('✅ 边界：坏 mode/未知片段/未知层级 → 诚实拦截（附可用清单）')

    print('=' * 68)
    print('可判定片段地图构件自测：全部通过 ✅')
    print('=' * 68)
