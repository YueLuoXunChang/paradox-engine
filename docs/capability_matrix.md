# 能力矩阵（题型 × 构件 × 接线状态）

> 本文件由 `python engine/_capability_matrix.py` 从**活代码**自动生成（`control/classifier.py` 的 ROUTE 表 + `ai/tools.py` 的注册表 + 各构件 docstring），请勿手改；漂移检查见 `engine/test_capability_matrix.py`。
>
> 口径（**三态**）：
> 1. **默认管线**——判类器按"题型 × 复杂度档"自动把材料送过去；
> 2. **线索触发补跑**——题型对得上 + 人给足该构件的线索就跑。这些构件都要"人写的正式式子"（formula / program / relations / tbox / states / arguments），**不进默认管线**：放进管线会让本来线索齐了的材料显示"还欠"，也破坏 L1/L2/L3 的档位语义；
> 3. **未接线**——只能单独调用（命令行 `paradox-engine --call 工具`、AI 工具 `call_tool`）。

## 一、每个题型现在接了什么（逐字来自 ROUTE 表）

### T1 命题真值

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional | 命题单机制判有效性（最小充分） |
| L2 | propositional · first_order | 加一阶量词展开 |
| L3 | first_order · nd_propositional | 复杂断言集走一阶+证明 |

### T10 定义辨析

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional | 概念对一致性检查 |
| L2 | first_order | 谓词刻画两概念 |
| L3 | first_order · boundary_paradox | 本体对齐 + 边界诊断 |

### T11 假设检验

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional | 单概率断言检查 |
| L2 | converge_check | 权重迭代校验 |
| L3 | wall_pipeline | 假设检验遇冲突走管线 |

### T12 未分类

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional | 未分类——通用最小管线 |
| L2 | propositional | 同 L1（不升档，诚实标注） |
| L3 | propositional | 同 L1（不升档，诚实标注） |

### T2 论证矛盾

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | paradox_measure | 单对矛盾测 μ（轻量） |
| L2 | paradox_measure · paradox_annotate · relevance_logic | μ + 注解卡（冲突定位）+ 相干检查（真冲突 vs 话术冲突） |
| L3 | wall_pipeline | 撞墙管线五选一（含立场分析） |

### T3 关系结构

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional | 简单关系一致性检查 |
| L2 | first_order | 关系推理（传递/对称） |
| L3 | first_order · skeleton | 拓扑形态（需骨架层） |

### T4 演化过程

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | converge_check | 一步递推检查 |
| L2 | converge_check | 收敛判定四分支 |
| L3 | ltl · converge_check · skeleton | 时序 LTL + 收敛 + 多线骨架 |

### T5 知识更新

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | propositional · agm_revision | 新旧断言对比 + AGM 修正（最小放弃） |
| L2 | paradox_measure · agm_revision | 新信息冲突测 μ + AGM 修正（信念度先弃低者） |
| L3 | wall_pipeline | 信念更新撞墙走五选一 |

### T6 自指/深层

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | paradox_measure | 自指直判 μ=1 |
| L2 | selfref_fixpoint | 递归修正三态观察 |
| L3 | selfref_fixpoint · boundary_paradox · counterpoint_gen | 共振带 + 边界诊断 + 创生 |

### T7 对立交汇

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | paradox_measure | 对立对共存检查 |
| L2 | counterpoint_gen | 第三态生成（共振/桥） |
| L3 | counterpoint_gen · wall_pipeline | 第三态 + 撞墙管线全编排 |

### T8 证据冲突

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | paradox_measure | 两证据权重对比 |
| L2 | paradox_measure | 证据冲突熵测度 |
| L3 | wall_pipeline | 证据冲突上卷撞墙管线 |

### T9 学科题目

| 档 | 路由到的构件 | 路由理由（路由表原文） |
|---|---|---|
| L1 | first_order | 罕见——最小谓词建模 |
| L2 | first_order · propositional | 谓词建模 + 关键量检验 |
| L3 | first_order · ltl · wall_pipeline | 本体化 + 演化 + 悖论扫描（全管线） |

## 二、每个题型的接线概览

| 题型 | 名称 | L1 | L2 | L3 | 涉及构件数 |
|---|---|---|---|---|---|
| T1 | 命题真值 | propositional | propositional + first_order | first_order + nd_propositional | 3 |
| T10 | 定义辨析 | propositional | first_order | first_order + boundary_paradox | 3 |
| T11 | 假设检验 | propositional | converge_check | wall_pipeline | 3 |
| T12 | 未分类 | propositional | propositional | propositional | 1 |
| T2 | 论证矛盾 | paradox_measure | paradox_measure + paradox_annotate + relevance_logic | wall_pipeline | 4 |
| T3 | 关系结构 | propositional | first_order | first_order + skeleton | 3 |
| T4 | 演化过程 | converge_check | converge_check | ltl + converge_check + skeleton | 3 |
| T5 | 知识更新 | propositional + agm_revision | paradox_measure + agm_revision | wall_pipeline | 4 |
| T6 | 自指/深层 | paradox_measure | selfref_fixpoint | selfref_fixpoint + boundary_paradox + counterpoint_gen | 4 |
| T7 | 对立交汇 | paradox_measure | counterpoint_gen | counterpoint_gen + wall_pipeline | 3 |
| T8 | 证据冲突 | paradox_measure | paradox_measure | wall_pipeline | 2 |
| T9 | 学科题目 | first_order | first_order + propositional | first_order + ltl + wall_pipeline | 4 |

## 三、线索触发补跑（题型对得上 + 线索给全就跑；不进默认管线）

| 构件 | 适用题型 | 需要的线索（键） | 补跑能补什么 |
|---|---|---|---|
| `interval_algebra` | T4 | events、relations | 定性时序自洽性（events + relations） |
| `mu_calculus` | T4 · T6 | formula、states | 不动点性质（formula + states） |
| `description_logic.subsumption` | T10 · T3 | sub、super | ALC 包含判定（sub + super） |
| `description_logic.classify` | T3 · T10 | tbox | 概念层级（tbox） |
| `asp` | T2 · T5 | program | 答案集自洽性（program） |
| `belnap_four` | T2 · T8 | formula | 四值求值（formula） |
| `dung` | T2 · T3 | arguments、attacks | 立场集（arguments + attacks） |
| `intuitionistic_logic` | T1 · T6 | formula | 构造性立场反模型（formula） |

## 四、未接线（只能单独调用）的构件

（工具名 → 一句话；这些正是"要不要接线"这件事的对象）

| 工具 | 层 | 构件文件 | 一句话 |
|---|---|---|---|
| `decidability_map` | classical | `engine/classical/decidability_map.py` | 可判定片段地图：这个问题能不能算（判定性结论/算术层级/墙的精确地图） |
| `default_logic` | cold | `engine/cold/default_logic.py` | 默认逻辑（Reiter 完整不动点）：默认规则下所有扩展、共同结论与立场之争 |
| `description_logic` | cold | `engine/cold/description_logic.py` | 描述逻辑 ALC：概念可不可满足、甲包不包含乙、两个概念相不相交、整张本体的概念层级（谁是谁的子类），可满足给规范模型 |
| `dung_framework` | cold | `engine/cold/dung_framework.py` | Dung 论证框架：哪些立场站得住（grounded/preferred/stable） |
| `equality_tableau` | classical | `engine/classical/equality_tableau.py` | 等词+表列法：等词替换 + tableau 反例模型 |
| `lambda_calculus` | classical | `engine/classical/lambda_calculus.py` | λ 演算：β 归约/Y 不动点/邱奇编码/Ω 诚实发散 |
| `many_valued` | cold | `engine/cold/many_valued.py` | 多值逻辑：K3 未知传播 / Ł3 中间真值（重言式与推理判定，三套对照） |
| `modal` | classical | `engine/classical/modal.py` | 模态逻辑：□/◇ Kripke 语义（K/T/S4/S5） |
| `model_check` | classical | `engine/classical/model_check.py` | CTL 模型检查：显式 Kripke 结构上公式是否在所有初始状态成立（含反例状态） |
| `monadic_fol` | classical | `engine/classical/monadic_fol.py` | 一元谓词逻辑判定：闭的一元谓词公式是否有效（有限域展开，含反模型） |
| `observer_bypass` | mechanisms | `engine/mechanisms/observer_bypass.py` | 悖论全程自反旁路：主链不停，旁路观察+注解+注入 |
| `presburger` | classical | `engine/classical/presburger.py` | Presburger 算术判定：整数上带加减与整除的式子是否恒真/有解（量词消元，含等价式与反例） |
| `recursion_theorem` | classical | `engine/classical/recursion_theorem.py` | Kleene 递归定理：自指程序构造（quine/程序拿自己——借数学底座） |
| `resolution` | classical | `engine/classical/resolution.py` | 一阶归结：Skolem+合一+归结链反证 |
| `stlc` | classical | `engine/classical/stlc.py` | 简单类型 λ：类型检查/拦自应用（Curry-Howard） |
| `truth_revision` | cold | `engine/cold/truth_revision.py` | Gupta-Belnap 真值修正：多句系统修正序列分类（稳定/振荡——共振带锚点） |
| `turing_machine` | classical | `engine/classical/turing_machine.py` | 图灵机：模拟/UTM 自模拟/停机不可判定演示 |

另有 **2** 件属于引擎自身（`classifier`、`controller`），不参与"要不要接线"的讨论——它们就是路由本身。

## 五、小结（机器算）

- 有路由的题型：**12/12**（T1、T10、T11、T12、T2、T3、T4、T5、T6、T7、T8、T9）
- 路由表条目：**36** 条（题型 × 档）
- 路由里的构件名：**14** 个（agm_revision、boundary_paradox、converge_check、counterpoint_gen、first_order、ltl、nd_propositional、paradox_annotate、paradox_measure、propositional、relevance_logic、selfref_fixpoint、skeleton、wall_pipeline）——其中 **11 个有对应工具**，其余是入口/层名，不占工具位
- 工具总数：**38** 件，分三态：**默认管线 11 件** · **线索触发补跑 8 件** · **未接线（只 --call）17 件**（另有 2 件是引擎自身，见上一节）
