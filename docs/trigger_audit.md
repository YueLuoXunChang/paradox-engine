# 触发实测（钝点定位）：候选集 × 触发集

> 本文件由 `python engine/_trigger_audit.py` 从**真实语料**自动生成（`engine/scenarios` 全库，跑控制器五步流水线 + 线索触发补跑），请勿手改；漂移检查见 `engine/test_trigger_audit.py`。
>
> **口径**：**候选集** = 被判类器**排进管线**的场景数；**触发集** = 其中 `status==run`（真跑起来）的场景数。**钝点** = 排了却一次没真跑；**半空转** = 跑了但没跑满候选；**全触发** = 跑满。
>
> **★ 读法警告**：三者都是**对当前语料**的实测，**不是构件的性质**——材料不给结构化线索，任何构件都跑不起来。本表只回答"接线到不到位"，**不许当"构件好不好用"读**。

## 一、语料（实测）

- 场景数：**28**
- 题型分布：T1×2、T10×3、T11×2、T12×2、T2×3、T3×3、T4×3、T5×2、T6×2、T7×2、T8×2、T9×2

## 二、逐件触发表（候选集 → 触发集）

| 构件 | 候选（被排进管线） | 触发（真跑） | 没跑起来的原因 | 判定 |
|---|---:|---:|---|---|
| `propositional.consistency` | 7 | 0 | missing_input | 钝点 |
| `first_order.query` | 6 | 0 | missing_input | 钝点 |
| `paradox_measure.mu1` | 6 | 6 | — | 全触发 |
| `propositional.validity` | 4 | 2 | missing_input | 半空转 |
| `converge_check.finite` | 3 | 0 | missing_input | 钝点 |
| `agm_revision` | 2 | 1 | missing_input | 半空转 |
| `paradox_annotate` | 2 | 2 | — | 全触发 |
| `relevance_logic` | 2 | 1 | missing_input | 半空转 |
| `selfref_fixpoint` | 2 | 2 | — | 全触发 |
| `ltl` | 1 | 0 | missing_input | 钝点 |
| `paradox_measure.mu4` | 1 | 1 | — | 全触发 |
| `wall_pipeline` | 1 | 0 | missing_input | 钝点 |

## 三、三态小结（机器算）

- **钝点 5 件**：`propositional.consistency`、`first_order.query`、`converge_check.finite`、`ltl`、`wall_pipeline`
- **半空转 3 件**：`propositional.validity`、`agm_revision`、`relevance_logic`
- **全触发 4 件**：`paradox_measure.mu1`、`paradox_annotate`、`selfref_fixpoint`、`paradox_measure.mu4`

## 四、线索触发补跑：挂在哪些题型、真跑几次

| 构件 | 适用题型 | 该题型本库材料数 | 真跑次数 | 说明 |
|---|---|---:|---:|---|
| `interval_algebra` | T4 | 3 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `mu_calculus` | T4 · T6 | 5 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `description_logic.subsumption` | T10 · T3 | 6 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `description_logic.classify` | T3 · T10 | 6 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `asp` | T2 · T5 | 5 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `belnap_four` | T2 · T8 | 5 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `dung` | T2 · T3 | 6 | 0 | 题型有材料，但材料没带它要的结构化线索 |
| `intuitionistic_logic` | T1 · T6 | 4 | 0 | 题型有材料，但材料没带它要的结构化线索 |

## 五、小结（机器算）

- 出现在语料里的构件：**12** 件；其中 钝点 **5** · 半空转 **3** · 全触发 **4**
- 线索触发补跑 **8** 件里，**8 件**在"题型有材料"的前提下真跑 **0** 次
- ⚠️ 这不是"构件坏了"，是**材料侧没给结构化线索**：要让它真跑，得先有带线索的材料（或改接线口径）——**要不要改属作者设计权**。
