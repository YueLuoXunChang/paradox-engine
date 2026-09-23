# 工具协议（AI 可调用工具清单）

> 本文件由 `python engine/ai/freeze_tool_schema.py` 从 `engine/ai/tools.py` 的注册表**自动生成**，请勿手改。
> 工具名与参数名是对外契约（轨 C1）：有意变更须重新生成本文件与 `engine/ai/tool_schema_frozen.json`，并在 CHANGELOG 与变更记账。

共 **41** 件工具。调用方式：

```python
from engine.ai.tools import tools, call_tool
print(tools())                      # OpenAI 风格 schema 清单
r = call_tool('paradox_measure', {'mode': 'mu1', 'wA': 5, 'wNotA': 5})
print(r['result'])                  # 构件原始输出（含 boundary 边界声明）
```

命令行也能直接调（不经判类路由；“--tools”看清单、“--json”给结构化结果）：

```bash
paradox-engine --call mu_calculus --args '{"mode": "evaluate", "formula": "p", "states": ["a"], "labels": {"a": ["p"]}}'
paradox-engine --call presburger --args '{"formula": "2*x = 4"}' --json
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
| `criticality` | `alpha_critical`:number `mode`:string `n_boot`:integer `seed`:integer `sizes*`:array `sizes_b`:array `tol`:number `x_min`:number | 临界诊断：事件规模是否无标度 + 三态（次临界/临界/超临界）+ 距阈值多远 |
| `growth_guard` | `budget`:integer `gain_min`:number `high_ratio`:number `low_ratio`:number `mode`:string `n0`:integer `rate`:number `sizes`:array `steps`:integer | 增长护栏：迭代产物会不会指数爆炸 + 限幅/增益调度/滞后补偿的压制效果与代价 |
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
| `many_valued` | `assignment`:object `conclusion`:string `formula`:string `logic`:string `mode`:string `premises`:array | 多值逻辑：K3 未知传播 / Ł3 中间真值（重言式与推理判定，三套对照） |
| `interval_algebra` | `events`:array `mode`:string `relation`:string `relations`:array | 区间代数：事件之间的定性时序关系自不自治（先于/相接/重叠/包含…），矛盾给冲突对，不矛盾给可复核的整数区间见证 |
| `description_logic` | `c1`:string `c2`:string `concept`:string `max_nodes`:integer `mode`:string `sub`:string `super`:string `tbox`:array | 描述逻辑 ALC：概念可不可满足、甲包不包含乙、两个概念相不相交、整张本体的概念层级（谁是谁的子类），可满足给规范模型 |
| `mu_calculus` | `c1`:string `c2`:string `ctl`:string `formula`:string `init`:array `labels`:object `mode`:string `states`:array `transitions`:array | 模态 μ 演算：在给定迁移系统上求不动点式子（μ 最小/ν 最大）成立的状态，每轮迭代留痕；CTL 公式可翻成 μ 式子再求值 |
| `bisimulation` | `lts*`:object `mode`:string `relation`:array `s1`:string `s2`:string | 双模拟检查：两个状态是不是"行为上分不开"（最大双模拟分划 + 不等价的见证（轮次/标号/区分序列）+ 商系统）；与 μ 演算互验 |
| `asp` | `mode`:string `program`:string `query`:string | 答案集程序：规则 + 否定即失败 + 约束 → 自洽的结论集合（答案集，可能一个都没有），每个原子给出它的推导依据 |
| `dung_framework` | `arguments`:array `attacks`:array `max_arguments`:integer | Dung 论证框架：哪些立场站得住（grounded/preferred/stable） |
| `truth_revision` | `max_steps`:integer `mode`:string `sentences`:object `start`:object | Gupta-Belnap 真值修正：多句系统修正序列分类（稳定/振荡——共振带锚点） |
| `recursion_theorem` | `mode`:string `payload`:string `transform`:object | Kleene 递归定理：自指程序构造（quine/程序拿自己——借数学底座） |
| `agm_revision` | `beliefs`:array `defaults`:array `exceptions`:array `facts`:array `max_beliefs`:integer `mode`:string `new_info`:string `priorities`:object | AGM 信念修正+非单调默认：新信息来了旧结论还成立吗（最小放弃/可废止） |
| `default_logic` | `defaults`:array `facts`:array `max_defaults`:integer `query`:string | 默认逻辑（Reiter 完整不动点）：默认规则下所有扩展、共同结论与立场之争 |
| `relevance_logic` | `conclusion`:string `mode`:string `premises`:array `prop_a`:string `prop_b`:string | 相干逻辑：前提结论是否共享变量（区分真冲突与话术冲突） |
| `intuitionistic_logic` | `formula`:string `formulas`:array `max_worlds`:integer `mode`:string `order`:array `valuation`:object `world`:string `worlds`:array | 直觉主义逻辑：Kripke 求值/反模型搜索（排中律为何非构造有效）+ 两系统对照 |
| `decidability_map` | `level`:string `mode`:string `system`:string | 可判定片段地图：这个问题能不能算（判定性结论/算术层级/墙的精确地图） |
| `monadic_fol` | `formula`:string `mode`:string | 一元谓词逻辑判定：闭的一元谓词公式是否有效（有限域展开，含反模型） |
| `presburger` | `formula*`:string `mode`:string | Presburger 算术判定：整数上带加减与整除的式子是否恒真/有解（量词消元，含等价式与反例） |
| `model_check` | `formula`:string `init`:array `labels`:object `states`:array `transitions`:array | CTL 模型检查：显式 Kripke 结构上公式是否在所有初始状态成立（含反例状态） |
| `classifier` | `debug`:boolean `text`:string | 判类器：12 题型 + 复杂度 L1/L2/L3 + 路由 |
| `controller` | `debug`:boolean `structured`:object `text*`:string | 总控五步：判类→复杂度→切路→真跑→判输出（中文诊断报告） |

## 返回约定

- `call_tool` 统一返回 `{verdict, tools, result, boundary}`：`verdict='ok'` 表示构件真跑；`result` 是构件原始输出；
- 构件缺参时**诚实拦截**（`*_pending`），挂载层不伪造输入；
- 每个构件输出都带 `boundary`（只诊断不决策声明随行）；
- 未知工具返回 `verdict='tool_unknown'` 并附可用清单。

