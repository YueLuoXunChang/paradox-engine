# -*- coding: utf-8 -*-
"""
tools.py — AI 挂载层：function-calling 工具封装（阶段 6）
================================================================
概念来源：ROADMAP 阶段 6（AI 挂载层——引擎函数 = AI 可调用工具）
设计：38 总架构（输出双形态：给人看/给 AI 用）+ 各构件统一 run 接口。
本文件不是新判定构件——是**挂载器**：把全部 23 个构件包装成
OpenAI 风格 function-calling 工具（name/description/parameters JSON
Schema），并提供 call_tool(name, args) 统一分派。

本文件做什么（一句话）：
    AI（或任何函数调用客户端）拿到 TOOL_SCHEMAS 就知道引擎能干什么、
    每个工具要什么参数；调 call_tool 拿到结构化诊断——引擎变成
    AI 可调用的工具集。

诚实边界：
    - schema 从各构件 PORTS 自动生成（字段类型/必填一致），描述为
      手工中文（每工具一句话）；
    - call_tool 透传参数到构件 run()——缺参由构件自己诚实拦截
      （*_pending），挂载层不伪造输入；
    - 工具输出带 boundary 字段（只诊断不决策声明随行）；
    - 本层不做编排决策——总控（controller）或 AI 自己决定调哪个。

统一接口：
    tools() -> list[dict]      —— OpenAI 风格工具清单
    call_tool(name, args) -> dict —— 分派到构件 run()
    run(inputs: dict) -> dict  —— 本文件自身 run：'list'|'call'
"""

PORTS = {
    'in': {'action': 'str?', 'name': 'str?', 'arguments': 'dict?'},
    'out': {'verdict': 'str', 'tools': 'list', 'result': 'dict',
            'boundary': 'str'},
}

import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 工具注册表：工具名 → (模块路径, 中文描述)
_TOOL_REGISTRY = [
    ('paradox_measure', 'mechanisms.paradox_measure',
     '悖论强度测度：矛盾多尖锐 → μ∈[0,1]（四分支，mu2 自指直判）'),
    ('paradox_annotate', 'mechanisms.paradox_annotate',
     '悖论注解：给矛盾生成 8 字段卡 + P-A/B/C 分级'),
    ('converge_check', 'mechanisms.converge_check',
     '收敛判定：递归修正序列收不收敛（压缩/有限步/渐进/振荡）'),
    ('selfref_fixpoint', 'mechanisms.selfref_fixpoint',
     '自指检测：递归修正三态（不动点/共振带/发散/说谎者每步翻转）'),
    ('boundary_paradox', 'mechanisms.boundary_paradox',
     '边界悖论判定：墙=边界（张力/划设即撤销/重生路径）'),
    ('observer_bypass', 'mechanisms.observer_bypass',
     '悖论全程自反旁路：主链不停，旁路观察+注解+注入'),
    ('counterpoint_gen', 'mechanisms.counterpoint_gen',
     '对位创生第三态：对立交汇 → 候选+依据（同向/反向/交叉）'),
    ('wall_pipeline', 'mechanisms.wall_pipeline',
     '撞墙管线 A：测墙→注解→钻墙→看墙→旁路→创生 → 五选一诊断'),
    ('propositional', 'classical.propositional',
     '命题逻辑：有效性/反例/可满足/重言式（经典二值）'),
    ('first_order', 'classical.first_order',
     '一阶谓词：量词推理（有限论域展开判定）'),
    ('ltl', 'classical.ltl', '时序 LTL：G/F/X/U 沿路径判定（含违约定位）'),
    ('modal', 'classical.modal', '模态逻辑：□/◇ Kripke 语义（K/T/S4/S5）'),
    ('nd_propositional', 'classical.nd_propositional',
     '命题自然演绎 ND：证明树（经典/直觉主义）'),
    ('resolution', 'classical.resolution',
     '一阶归结：Skolem+合一+归结链反证'),
    ('equality_tableau', 'classical.equality_tableau',
     '等词+表列法：等词替换 + tableau 反例模型'),
    ('lambda_calculus', 'classical.lambda_calculus',
     'λ 演算：β 归约/Y 不动点/邱奇编码/Ω 诚实发散'),
    ('turing_machine', 'classical.turing_machine',
     '图灵机：模拟/UTM 自模拟/停机不可判定演示'),
    ('stlc', 'classical.stlc', '简单类型 λ：类型检查/拦自应用（Curry-Howard）'),
    ('mtmp', 'skeleton.mtmp', 'MT-MP-TL 骨架：点/线程/拓扑 12 形态/5 操作'),
    ('belnap_four', 'cold.belnap_four', 'Belnap 四值：矛盾取"两者"不爆炸'),
    ('dung_framework', 'cold.dung_framework',
     'Dung 论证框架：哪些立场站得住（grounded/preferred）'),
    ('classifier', 'control.classifier',
     '判类器：12 题型 + 复杂度 L1/L2/L3 + 路由'),
    ('controller', 'control.controller',
     '总控五步：判类→复杂度→切路→真跑→判输出（中文诊断报告）'),
]

_TYPE_MAP = {
    'str': 'string', 'dict': 'object', 'list': 'array',
    'bool': 'boolean', 'int': 'integer', 'float': 'number',
    'callable': 'object',
}


def _port_to_schema(ports_in):
    """PORTS['in']（{field: 'str?'}）→ JSON Schema properties + required。"""
    properties = {}
    required = []
    for field, spec in (ports_in or {}).items():
        optional = spec.endswith('?')
        base = spec.rstrip('?')
        properties[field] = {'type': _TYPE_MAP.get(base, 'string'),
                             'description': f'参数 {field}'
                             + ('（可省）' if optional else '（必填）')}
        if not optional:
            required.append(field)
    return properties, required


def _load_module(mod_path):
    return importlib.import_module(f'engine.{mod_path}')


def tools():
    """OpenAI 风格工具清单：全 23 件（schema 从 PORTS 自动生成）。"""
    out = []
    for name, mod_path, desc in _TOOL_REGISTRY:
        mod = _load_module(mod_path)
        props, req = _port_to_schema(mod.PORTS.get('in'))
        out.append({
            'type': 'function',
            'function': {
                'name': name,
                'description': desc,
                'parameters': {
                    'type': 'object',
                    'properties': props,
                    'required': req,
                },
            },
        })
    return out


def call_tool(name, arguments=None):
    """
    分派：工具名 → 构件 run(arguments)。
    缺参由构件自己诚实拦截（*_pending），本层不伪造。
    """
    args = arguments or {}
    for tname, mod_path, _desc in _TOOL_REGISTRY:
        if tname == name:
            try:
                mod = _load_module(mod_path)
            except Exception as e:
                return {'verdict': 'tool_error',
                        'error': f'工具 {name} 模块加载失败：{e}'}
            try:
                result = mod.run(args)
            except Exception as e:
                return {'verdict': 'tool_error',
                        'error': f'工具 {name} 执行异常：{e}'}
            # 挂载层补白箱：工具名 + 输入回显（构件输出原样透传）
            if isinstance(result, dict):
                result = dict(result)
                result['_tool'] = name
                result['_input'] = args
            return {'verdict': 'ok', 'tool': name, 'result': result}
    return {'verdict': 'tool_unknown',
            'error': f'未知工具 {name!r}——可用：'
                     f'{[t[0] for t in _TOOL_REGISTRY]}'}


def run(inputs):
    """
    做什么：AI 挂载层统一入口。
    action='list' → 工具清单；action='call' → call_tool(name, arguments)。
    """
    action = inputs.get('action', 'list')
    if action == 'list':
        return {'verdict': 'tools_listed',
                'tools': tools(),
                'result': None,
                'boundary': '工具输出带 boundary（只诊断不决策随行）。'
                            'schema 从 PORTS 自动生成，描述手工中文。'}
    if action == 'call':
        name = inputs.get('name')
        if not name:
            return {'verdict': 'input_pending', 'tools': None,
                    'result': None,
                    'boundary': 'call 需 name（工具名）——诚实'}
        r = call_tool(name, inputs.get('arguments') or {})
        return {'verdict': r['verdict'], 'tools': None, 'result': r,
                'boundary': 'call_tool 透传参数到构件 run()——缺参由构件'
                            '诚实拦截（*_pending），挂载层不伪造输入。'}
    return {'verdict': 'input_pending', 'tools': None, 'result': None,
            'boundary': f"action 应为 list/call，得到 {action!r}"}


# ============================================================
# 自测
# ============================================================
if __name__ == '__main__':
    print('=' * 62)
    print('AI 挂载层 · 自测（function-calling 封装）')
    print('=' * 62)

    # 1) 工具清单：全 23 件，schema 有 name/parameters
    tl = tools()
    assert len(tl) == 23, len(tl)
    names = [t['function']['name'] for t in tl]
    assert 'paradox_measure' in names and 'controller' in names, names
    assert all('parameters' in t['function'] for t in tl)
    assert all('description' in t['function'] for t in tl)
    print(f'✅ 工具清单 {len(tl)} 件（schema 自动生成）')
    print(f"   示例: {tl[0]['function']['name']} ← "
          f"{list(tl[0]['function']['parameters']['properties'])[:3]}…")

    # 2) schema 结构与 PORTS 一致：properties 覆盖 PORTS 字段
    pm = next(t for t in tl if t['function']['name'] == 'paradox_measure')
    assert set(pm['function']['parameters']['properties']) == \
        {'mode', 'wA', 'wNotA'}, pm
    assert pm['function']['parameters']['required'] == ['mode'], pm
    ct = next(t for t in tl if t['function']['name'] == 'controller')
    assert set(ct['function']['parameters']['properties']) == \
        {'text', 'structured', 'debug'}, ct
    dg = next(t for t in tl if t['function']['name'] == 'dung_framework')
    assert set(dg['function']['parameters']['properties']) == \
        {'arguments', 'attacks', 'max_arguments'}, dg
    print('✅ schema 字段与各构件 PORTS 一致（自动生成，无手工漂移）')

    # 3) call_tool：悖论测度
    r3 = call_tool('paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5})
    assert r3['verdict'] == 'ok', r3
    assert abs(r3['result']['mu'] - 1.0) < 1e-9, r3
    assert r3['result']['_tool'] == 'paradox_measure', r3
    print(f"✅ call_tool paradox_measure → μ={r3['result']['mu']}")

    # 4) call_tool：撞墙管线（说谎者）
    r4 = call_tool('wall_pipeline', {'wall': '这句话是假的'})
    assert r4['verdict'] == 'ok', r4
    assert r4['result']['verdict'] == 'resonance_selfref', r4
    print(f"✅ call_tool wall_pipeline → {r4['result']['verdict']}")

    # 5) call_tool：总控（真实中文论证）
    r5 = call_tool('controller', {
        'text': '产品既要尽快上线（3周），又要完整覆盖所有合规项（12周）',
        'structured': {'A': '尽快上线(3周)', 'B': '完整覆盖合规(12周)',
                       'wA': 5, 'wNotA': 5}})
    assert r5['verdict'] == 'ok', r5
    assert r5['result']['classification']['main_type'] == 'T2', r5
    print(f"✅ call_tool controller → "
          f"{r5['result']['classification']['main_type']}"
          f"（{r5['result']['classification']['route']['route_id']}）")

    # 6) 缺参透传：构件诚实拦截
    r6 = call_tool('selfref_fixpoint', {})
    assert r6['result']['verdict'] == 'input_pending', r6
    print('✅ call_tool 缺参 → 构件 input_pending（诚实拦截）')

    # 7) 未知工具
    r7 = call_tool('no_such_tool', {})
    assert r7['verdict'] == 'tool_unknown', r7
    print('✅ 未知工具 → tool_unknown（诚实报告可用清单）')

    # 8) run 接口
    r8 = run({'action': 'list'})
    assert r8['verdict'] == 'tools_listed' and len(r8['tools']) == 23, r8
    r8b = run({'action': 'call', 'name': 'dung_framework',
               'arguments': {'arguments': ['a', 'b'],
                             'attacks': [('a', 'b')]}})
    assert r8b['verdict'] == 'ok', r8b
    print('✅ run(action=list/call) 统一入口 OK')

    print('=' * 62)
    print('AI 挂载层自测：全部通过 ✅')
    print('=' * 62)
