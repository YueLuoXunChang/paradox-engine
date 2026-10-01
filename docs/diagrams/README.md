# 逻辑流程图（每个模块一张）

> 本文件由 `engine/_diagram_audit.py --write` 生成索引部分；**每张图本身是手写/逐条对着代码核的**。
> 口径：图要能**照着复核**——输入校验的每条拒绝路径 · 判定的每个分支与业务词 ·
> 核心算法的数据流与关键常量 · 返回字段与 `boundary`，缺一块就不算"详细"。

## 怎么读

- 每张图对应一个模块文件（`engine/<层>/<模块名>.py`），文件名同模块名：`docs/diagrams/<模块名>.md`。
- 图里出现的每个 `verdict` 词，必须**在模块源码里真的存在**（防编造）——由常设检查守着：
  `python engine/_diagram_audit.py --check`（门禁之一）。
- 图是**逻辑视图**，不是调用图：画的是"这次 run 会怎么走、在哪一步拒、返回什么"。

## mermaid 写法约定（沿用语料侧既有图集的避坑清单，逐条都是真炸过的）

**会炸的写法（一律不许出现，`_diagram_audit.py` 会扫）：**

| 别写 | 为什么 | 改成 |
|:--|:--|:--|
| `A -- 是 --> B` | 中文标签简写在某些渲染器不稳 | `A -->\|是\| B` |
| 节点标签里出现 `<` `>` `≤` `≥` | 被当成 HTML 标签/实体 | 写成「小于 / 大于 / 不大于 / 不小于」 |
| 节点标签里出现 `"`（中文双引号）· `&` | 实体冲突 | 去掉，或改用「」 |
| `subgraph 核心层` | 子图名不带引号、含中文会炸 | `subgraph "核心层"` |
| 节点标签塞长句 | 一行读不完 | ≤15 字，细节放下一层节点或正文 |

**固定要有的写法：**

1. **布局只用 `flowchart TD`**（上下）——视觉一致；要分阶段用 `subgraph`，别换方向；
2. **菱形只放判断**（短句 + `?`），长条件拆成节点；
3. **配色约定**（与语料侧图集一致，四类一眼分清）：

   | 语义 | classDef（照抄这一行，`fill` 就是这个色） |
   |:--|:--|
   | 核心结构 / 主流程 | `classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px` 蓝 |
   | 方法 / 工具 / 校验 | `classDef tool fill:#f0f0f0,stroke:#666` 灰 |
   | 结果 / 输出 | `classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px` 绿 |
   | 堵点 / 拒绝路径 / 边界 | `classDef stop fill:#fdecea,stroke:#c0392b` 红 |

   用法：图末 `class R1,R2 stop` 按 id 批量上色（id 用大写字母+数字，稳）；
4. **一段代码块一张图**；一份文件可以有多张，开头用一行「图 N → 用途」列出来；
5. 换行用 `<br />`，不要写 `\n`；别用 `end` 当节点 id。

## 索引（按层）

<!-- INDEX:BEGIN（下面这段由 --write 重新生成，别手改） -->
共 **51** 个模块，已有图 **29** 张；图里点名到的判词 **175/175**（字面量口径：字典 `verdict` 值 ＋ 出口函数首参的常量 / 三元 / 拼接 ＋ `return 判词, 详情字典`。**数据结构构造标签**（如 `('top',)`）与 f-string 拼出来的都不计，见文末边界）。

| 模块 | 层 | 图 | 段落 | 节点 | 判词覆盖 | 待核对词 |
|:--|:--|:--|--:|--:|:--|:--|
| `agm_revision` | cold | [图](agm_revision.md) | 2 | 69 | 7/7 | — |
| `ai_scenarios` | ai | **缺** | 0 | 0 | 0/0 | — |
| `asp` | cold | [图](asp.md) | 2 | 49 | 7/7 | — |
| `belnap_four` | cold | [图](belnap_four.md) | 2 | 52 | 4/4 | — |
| `bisimulation` | cold | [图](bisimulation.md) | 2 | 49 | 8/8 | — |
| `boundary_paradox` | mechanisms | [图](boundary_paradox.md) | 2 | 44 | 3/3 | — |
| `classifier` | control | **缺** | 0 | 0 | 0/0 | — |
| `cli` | engine | **缺** | 0 | 0 | 0/0 | — |
| `clue_suggester` | control | **缺** | 0 | 0 | 0/0 | — |
| `controller` | control | **缺** | 0 | 0 | 0/0 | — |
| `converge_check` | mechanisms | [图](converge_check.md) | 2 | 60 | 1/1 | — |
| `corpus_stats` | scenarios | **缺** | 0 | 0 | 0/0 | — |
| `counterpoint_gen` | mechanisms | [图](counterpoint_gen.md) | 2 | 24 | 2/2 | — |
| `criticality` | mechanisms | [图](criticality.md) | 2 | 50 | 5/5 | — |
| `decidability_map` | classical | **缺** | 0 | 0 | 0/0 | — |
| `default_logic` | cold | [图](default_logic.md) | 2 | 48 | 7/7 | — |
| `description_logic` | cold | [图](description_logic.md) | 2 | 62 | 13/13 | — |
| `dung_framework` | cold | [图](dung_framework.md) | 2 | 36 | 3/3 | — |
| `equality_tableau` | classical | **缺** | 0 | 0 | 0/0 | — |
| `first_order` | classical | [图](first_order.md) | 2 | 34 | 5/5 | — |
| `freeze_tool_schema` | ai | **缺** | 0 | 0 | 0/0 | — |
| `growth_guard` | mechanisms | [图](growth_guard.md) | 2 | 66 | 7/7 | — |
| `interval_algebra` | cold | [图](interval_algebra.md) | 2 | 55 | 10/10 | — |
| `intuitionistic_logic` | cold | [图](intuitionistic_logic.md) | 2 | 49 | 9/9 | — |
| `lambda_calculus` | classical | **缺** | 0 | 0 | 0/0 | — |
| `ltl` | classical | [图](ltl.md) | 2 | 37 | 5/5 | — |
| `many_valued` | cold | [图](many_valued.md) | 2 | 52 | 9/9 | — |
| `modal` | classical | **缺** | 0 | 0 | 0/0 | — |
| `model_check` | classical | **缺** | 0 | 0 | 0/0 | — |
| `monadic_fol` | classical | **缺** | 0 | 0 | 0/0 | — |
| `mtmp` | skeleton | [图](mtmp.md) | 2 | 43 | 14/14 | — |
| `mu_calculus` | cold | [图](mu_calculus.md) | 2 | 55 | 10/10 | — |
| `nd_propositional` | classical | [图](nd_propositional.md) | 2 | 33 | 5/5 | — |
| `observer_bypass` | mechanisms | [图](observer_bypass.md) | 2 | 35 | 2/2 | — |
| `paradox_annotate` | mechanisms | [图](paradox_annotate.md) | 2 | 28 | 2/2 | — |
| `paradox_measure` | mechanisms | [图](paradox_measure.md) | 2 | 38 | 2/2 | — |
| `presburger` | classical | **缺** | 0 | 0 | 0/0 | — |
| `propositional` | classical | [图](propositional.md) | 2 | 38 | 8/8 | — |
| `recursion_theorem` | classical | **缺** | 0 | 0 | 0/0 | — |
| `relevance_logic` | cold | [图](relevance_logic.md) | 2 | 42 | 6/6 | — |
| `repl` | engine | **缺** | 0 | 0 | 0/0 | — |
| `resolution` | classical | [图](resolution.md) | 2 | 31 | 4/4 | `c_1`、`c_2` |
| `review_marks` | scenarios | **缺** | 0 | 0 | 0/0 | — |
| `scenarios` | scenarios | **缺** | 0 | 0 | 0/0 | — |
| `selfref_fixpoint` | mechanisms | [图](selfref_fixpoint.md) | 2 | 44 | 11/11 | — |
| `session` | control | **缺** | 0 | 0 | 0/0 | — |
| `stlc` | classical | **缺** | 0 | 0 | 0/0 | — |
| `tools` | ai | **缺** | 0 | 0 | 0/0 | — |
| `truth_revision` | cold | [图](truth_revision.md) | 2 | 32 | 5/5 | — |
| `turing_machine` | classical | **缺** | 0 | 0 | 0/0 | — |
| `wall_pipeline` | mechanisms | [图](wall_pipeline.md) | 2 | 39 | 1/1 | — |

> **待核对词**＝图里出现的、既不是本模块判词、也不是字段名/模块名的词——可能是**编造**，也可能只是画图时用的标识符。它进索引不进硬门禁（当索引读，当结论读就错了）；硬门禁只管：**每件都有图 · 形状合法 · 节点够多 · 提到 boundary · 无本机路径 · 至少写出一个本模块判词**。
<!-- INDEX:END -->

## 判据（`engine/_diagram_audit.py`）

1. **覆盖**：每个模块都有对应图文件（少一张就红），也不许有多余的孤儿图；
2. **形状**：至少一段 `mermaid` 代码块，每段首行是 `flowchart`/`graph`；每图节点数不低于下限；
3. **不许编造**：图里写的每个 `verdict` 词必须在模块源码里出现过（AST 抠 `verdict` 字段与
   `_reply(...)` 的第一个参数，比对着查）；
4. **点题**：每张图都要出现 `boundary`（全仓约定：返回值带诚实边界）；
5. **发布面**：不许出现本机路径、私有档案名与章节号（跟别的产物同一把尺子）。
