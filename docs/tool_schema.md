# 工具协议（AI 可调用工具清单）

> 本文件由 `python engine/ai/freeze_tool_schema.py` 从 `engine/ai/tools.py` 的注册表**自动生成**，请勿手改。
> 工具名与参数名是对外契约（轨 C1）：有意变更须重新生成本文件与 `engine/ai/tool_schema_frozen.json`，并在 CHANGELOG 与变更记账。

共 **29** 件工具。调用方式：

```python
from engine.ai.tools import tools, call_tool
print(tools())                      # OpenAI 风格 schema 清单
r = call_tool('paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5})
print(r['result'])                  # 构件原始输出（含 boundary 边界声明）
```

## 契约表（工具名 → 参数）

| 工具 | 参数（必填加 *）| 一句话 |
|---|---|---|
| `paradox_measure` | `mode*`:string `wA`:number `wNotA`:number | 悖论强度测度：矛盾多尖锐 → μ∈[0,1]（四分支，mu2 自指直判） |
| `paradox_annotate` | `eliminable`:boolean `impact`:string `paradox`:object `seq`:integer `source`:string | 悖论注解：给矛盾生成 8 字段卡 + P-A/B/C 分级 |
| `converge_check` | `branch`:string `err_fn*`:object `f*`:object `x0`:number | 收敛判定：递归修正序列收不收敛（压缩/有限步/渐进/振荡） |
| `selfref_fixpoint` | `f`:object `max_steps`:integer `mode`:string `sentence`:string `state0`:string `tol`:number | 自指检测：递归修正三态（不动点/共振带/发散/说谎者每步翻转） |
| `boundary_paradox` | `domain`:string `inside`:string `mode`:string `outside`:string `recursive_layer`:integer `wall_name`:string | 边界悖论判定：墙=边界（张力/划设即撤销/重生路径） |
| `observer_bypass` | `detect`:object `main_events`:array `use_advice`:boolean | 悖论全程自反旁路：主链不停，旁路观察+注解+注入 |
| `counterpoint_gen` | `antithesis`:string `coupling`:string `dimensions`:array `thesis`:string | 对位创生第三态：对立交汇 → 候选+依据（同向/反向/交叉） |
| `wall_pipeline` | `antithesis`:string `events`:array `thesis`:string `wall`:string | 撞墙管线 A：测墙→注解→钻墙→看墙→旁路→创生 → 五选一诊断 |
| `propositional` | `conclusion`:string `formula*`:string `mode`:string `premises`:array | 命题逻辑：有效性/反例/可满足/重言式（经典二值） |
| `first_order` | `facts`:array `query*`:string `rules`:array `universe`:array | 一阶谓词：量词推理（有限论域展开判定） |
| `ltl` | `formula*`:string `path`:array | 时序 LTL：G/F/X/U 沿路径判定（含违约定位） |
| `modal` | `access`:object `assign`:object `formula*`:string `system`:string `world`:string `worlds`:array | 模态逻辑：□/◇ Kripke 语义（K/T/S4/S5） |
| `nd_propositional` | `conclusion`:string `max_steps`:integer `premises`:array `system`:string | 命题自然演绎 ND：证明树（经典/直觉主义） |
| `resolution` | `conclusion`:string `facts`:array `max_resolvents`:integer `premises`:array | 一阶归结：Skolem+合一+归结链反证 |
| `equality_tableau` | `conclusion`:string `equality`:array `max_expand`:integer `premises`:array | 等词+表列法：等词替换 + tableau 反例模型 |
| `lambda_calculus` | `church_arg`:integer `expr`:string `fact_n`:integer `mode`:string `steps_limit`:integer | λ 演算：β 归约/Y 不动点/邱奇编码/Ω 诚实发散 |
| `turing_machine` | `input`:string `mode`:string `program`:object `steps_limit`:integer | 图灵机：模拟/UTM 自模拟/停机不可判定演示 |
| `stlc` | `context`:object `expected`:string `expr`:string | 简单类型 λ：类型检查/拦自应用（Curry-Howard） |
| `mtmp` | `a`:string `b`:string `edges`:array `kappa`:number `mode`:string `op`:string `points`:array `threads`:array `verbose`:boolean | MT-MP-TL 骨架：点/线程/拓扑 12 形态/5 操作 |
| `belnap_four` | `assign`:object `demo`:boolean `formula`:string | Belnap 四值：矛盾取"两者"不爆炸 |
| `dung_framework` | `arguments`:array `attacks`:array `max_arguments`:integer | Dung 论证框架：哪些立场站得住（grounded/preferred） |
| `truth_revision` | `max_steps`:integer `mode`:string `sentences`:object `start`:object | Gupta-Belnap 真值修正：多句系统修正序列分类（稳定/振荡——共振带锚点） |
| `recursion_theorem` | `mode`:string `payload`:string `transform`:object | Kleene 递归定理：自指程序构造（quine/程序拿自己——借数学底座） |
| `agm_revision` | `beliefs`:array `defaults`:array `exceptions`:array `facts`:array `max_beliefs`:integer `mode`:string `new_info`:string `priorities`:object | AGM 信念修正+非单调默认：新信息来了旧结论还成立吗（最小放弃/可废止） |
| `relevance_logic` | `conclusion`:string `mode`:string `premises`:array `prop_a`:string `prop_b`:string | 相干逻辑：前提结论是否共享变量（区分真冲突与话术冲突） |
| `intuitionistic_logic` | `formula`:string `formulas`:array `max_worlds`:integer `mode`:string `order`:array `valuation`:object `world`:string `worlds`:array | 直觉主义逻辑：Kripke 求值/反模型搜索（排中律为何非构造有效）+ 两系统对照 |
| `decidability_map` | `level`:string `mode`:string `system`:string | 可判定片段地图：这个问题能不能算（判定性结论/算术层级/墙的精确地图） |
| `classifier` | `debug`:boolean `text`:string | 判类器：12 题型 + 复杂度 L1/L2/L3 + 路由 |
| `controller` | `debug`:boolean `structured`:object `text*`:string | 总控五步：判类→复杂度→切路→真跑→判输出（中文诊断报告） |

## 返回约定

- `call_tool` 统一返回 `{verdict, tools, result, boundary}`：`verdict='ok'` 表示构件真跑；`result` 是构件原始输出；
- 构件缺参时**诚实拦截**（`*_pending`），挂载层不伪造输入；
- 每个构件输出都带 `boundary`（只诊断不决策声明随行）；
- 未知工具返回 `verdict='tool_unknown'` 并附可用清单。

