# 撞名登记（④ 轴：同名不同物一律标注）

由 `engine/_term_audit.py --write` 自动生成；判定表在脚本的 `JUDGMENTS`。

口径：把全部构件的 `PORTS["out"]` 字段名撞在一起；**不同型 = 同名不同物的高危信号**，
必须在本表有判定（同物/不同物 + 理由）。

共 **29** 个撞名 · 其中**不同型 9 个** · 未判定 **0 个**。

## 不同型撞名（逐条判定）

| 字段 | 件数 | 类型 | 判定 | 理由 |
|---|---|---|---|---|
| `counterexample` | 4 | dict/str | **不同物** | presburger=反例算术式 · propositional=赋值 · many_valued=真值指派 · relevance=反模型：都是"反例"但**载体不同** |
| `value` | 3 | bool/float/str | **不同物** | belnap_four=四值真值 · intuitionistic=节点真值 · many_valued=n 值真值：**载体不同** |
| `changed` | 2 | bool/list | **不同物** | freeze_tool_schema=契约漂移条目 · review_marks=审核状态变更：**含义不同** |
| `equivalent` | 2 | bool/str | **不同物** | presburger=公式等价 · bisimulation=互模拟等价：**关系不同** |
| `level` | 2 | dict/str | **不同物** | decidability_map=可判定层级 · classifier=分级（P-A/B/C）：**不同** |
| `report` | 2 | list/str | **不同物** | controller=五查报告 · scenarios=场景报告：**形态不同** |
| `review` | 2 | dict/str | **不同物** | corpus_stats=审核汇总 dict · review_marks=审核状态串（ok/wrong/edge/pending）：**载体不同** |
| `route` | 2 | dict/str | **不同物** | classifier=判定路径 · clue_suggester=管线路线：**不同** |
| `scenes` | 2 | int/list | **不同物** | corpus_stats=统计用场景集 · scenarios=场景库：**不同集合** |

## 同型撞名（默认同物，仍列出供扫）

- `boundary` × 48：skeleton/mtmp、classical/decidability_map、classical/equality_tableau、classical/first_order、classical/lambda_calculus、classical/ltl、classical/modal、classical/model_check、classical/monadic_fol、classical/nd_propositional、classical/presburger、classical/propositional、classical/recursion_theorem、classical/resolution、classical/stlc、classical/turing_machine、mechanisms/boundary_paradox、mechanisms/converge_check、mechanisms/counterpoint_gen、mechanisms/criticality、mechanisms/growth_guard、mechanisms/observer_bypass、mechanisms/paradox_annotate、mechanisms/paradox_measure、mechanisms/selfref_fixpoint、mechanisms/wall_pipeline、cold/agm_revision、cold/asp、cold/belnap_four、cold/bisimulation、cold/default_logic、cold/description_logic、cold/dung_framework、cold/interval_algebra、cold/intuitionistic_logic、cold/many_valued、cold/mu_calculus、cold/relevance_logic、cold/truth_revision、control/classifier、control/clue_suggester、control/controller、control/session、ai/freeze_tool_schema、ai/tools、scenarios/corpus_stats、scenarios/review_marks、scenarios/scenarios
  - 判定为同物：边界声明："本层承诺/不承诺什么"——形态统一
- `verdict` × 48：skeleton/mtmp、classical/decidability_map、classical/equality_tableau、classical/first_order、classical/lambda_calculus、classical/ltl、classical/modal、classical/model_check、classical/monadic_fol、classical/nd_propositional、classical/presburger、classical/propositional、classical/recursion_theorem、classical/resolution、classical/stlc、classical/turing_machine、mechanisms/boundary_paradox、mechanisms/converge_check、mechanisms/counterpoint_gen、mechanisms/criticality、mechanisms/growth_guard、mechanisms/observer_bypass、mechanisms/paradox_annotate、mechanisms/paradox_measure、mechanisms/selfref_fixpoint、mechanisms/wall_pipeline、cold/agm_revision、cold/asp、cold/belnap_four、cold/bisimulation、cold/default_logic、cold/description_logic、cold/dung_framework、cold/interval_algebra、cold/intuitionistic_logic、cold/many_valued、cold/mu_calculus、cold/relevance_logic、cold/truth_revision、control/classifier、control/clue_suggester、control/controller、control/session、ai/freeze_tool_schema、ai/tools、scenarios/corpus_stats、scenarios/review_marks、scenarios/scenarios
  - 判定为同物：统一判词："这件给出什么结论"——48 件同义，词表见术语表
- `detail` × 7：skeleton/mtmp、mechanisms/converge_check、mechanisms/criticality、mechanisms/growth_guard、mechanisms/selfref_fixpoint、cold/bisimulation、cold/truth_revision
- `annotation` × 3：mechanisms/paradox_annotate、mechanisms/selfref_fixpoint、mechanisms/wall_pipeline
  - ⚠ **已判定为同名不同物**（同型看不出来）：paradox_annotate=8 字段卡 · selfref_fixpoint=结论注记 · wall_pipeline=6 字段卡：**卡形状不同**
- `error` × 3：mechanisms/paradox_annotate、mechanisms/paradox_measure、scenarios/review_marks
- `explanation` × 3：classical/model_check、classical/monadic_fol、classical/presburger
- `atoms` × 2：classical/propositional、cold/many_valued
- `branch` × 2：mechanisms/converge_check、mechanisms/paradox_measure
  - ⚠ **已判定为同名不同物**（同型看不出来）：converge_check=收敛分支名（压缩/有限步/渐进/振荡）· paradox_measure=测度分支名（mu1–mu4）：**命名空间撞车**
- `compare` × 2：mechanisms/criticality、cold/mu_calculus
- `components` × 2：cold/dung_framework、control/clue_suggester
  - ⚠ **已判定为同名不同物**（同型看不出来）：dung_framework=攻击图**连通分量** · clue_suggester=管线构件：**同名不同物**（图论量 vs 系统模块）——注意两者**同型**（都是 list），类型检查看不出来，靠本判定
- `countermodel` × 2：classical/monadic_fol、cold/intuitionistic_logic
- `derivation` × 2：classical/stlc、mechanisms/counterpoint_gen
- `fails_in` × 2：classical/model_check、cold/mu_calculus
- `holds_in` × 2：classical/model_check、cold/mu_calculus
- `matrix` × 2：cold/interval_algebra、scenarios/corpus_stats
  - ⚠ **已判定为同名不同物**（同型看不出来）：interval_algebra=区间关系矩阵 · corpus_stats=统计矩阵：**不同**
- `model` × 2：cold/description_logic、cold/interval_algebra
- `note` × 2：classical/modal、cold/belnap_four
- `system` × 2：classical/modal、classical/nd_propositional
- `types` × 2：control/classifier、scenarios/corpus_stats
  - ⚠ **已判定为同名不同物**（同型看不出来）：classifier=分类类型 · corpus_stats=统计类型：**不同**
- `witness` × 2：classical/presburger、cold/bisimulation

## 各件明细（不同物者重点看）

### `counterexample`
- `engine/classical/presburger.py`：`dict?`（基类型 dict）
- `engine/classical/propositional.py`：`dict`（基类型 dict）
- `engine/cold/many_valued.py`：`dict?`（基类型 dict）
- `engine/cold/relevance_logic.py`：`str?`（基类型 str）

### `value`
- `engine/cold/belnap_four.py`：`str`（基类型 str）
- `engine/cold/intuitionistic_logic.py`：`bool?`（基类型 bool）
- `engine/cold/many_valued.py`：`float?`（基类型 float）

### `changed`
- `engine/ai/freeze_tool_schema.py`：`list`（基类型 list）
- `engine/scenarios/review_marks.py`：`bool`（基类型 bool）

### `equivalent`
- `engine/classical/presburger.py`：`str?`（基类型 str）
- `engine/cold/bisimulation.py`：`bool?`（基类型 bool）

### `level`
- `engine/classical/decidability_map.py`：`dict`（基类型 dict）
- `engine/control/classifier.py`：`str`（基类型 str）

### `report`
- `engine/control/controller.py`：`str`（基类型 str）
- `engine/scenarios/scenarios.py`：`list`（基类型 list）

### `review`
- `engine/scenarios/corpus_stats.py`：`dict`（基类型 dict）
- `engine/scenarios/review_marks.py`：`str?`（基类型 str）

### `route`
- `engine/control/classifier.py`：`dict`（基类型 dict）
- `engine/control/clue_suggester.py`：`str?`（基类型 str）

### `scenes`
- `engine/scenarios/corpus_stats.py`：`int`（基类型 int）
- `engine/scenarios/scenarios.py`：`list`（基类型 list）

