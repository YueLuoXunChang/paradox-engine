# 验证方登记（每件产物点名它的验证方）

> 本文件由 `engine/_verifier_audit.py` 自动生成（`--check` 守着漂移）。**别手改**。
>
> **口径**（来自"工具不可自证"）：**产物没有独立检验方时处于"未验状态"**——不是
> "暂时没验"，而是不得当定论用。本表只回答"**有没有**独立验证方、**是谁**"，
> **不回答"验得对不对"**（那是变异验收与对拍脚本的活）。
>
> **五态怎么判**：结构性判据（测试文件 ↔ 构件的对应、**AST 扫 import** 看它引用了
> 哪个别的构件）＋ 关键词初筛（"按定义直算/穷举/手算/对拍/oracle"等字样，**命中词写进
> 证据列**、供人复核）＋ 人工登记（外部验证方那几条）。**初筛不是终判**：会漏（换写法就
> 认不出）也会误（提了一句"对拍"不等于真做了）。
>
> 因此：**`只有性质/接口测试` 与 `无测试引用` 两类必须逐个登记签字**（见 `engine/test_verifier_audit.py` 的登记表），新增这类件就得改一处。

## 一、统计

| 态 | 件数 | 含义 |
|:--|--:|:--|
| 外部验证方 | **3** | 有**外部/第三方**实现当验证方（人工登记，命中词须在测试里出现） |
| 跨构件互验 | **13** | 同仓**另一个构件**参与互验（AST 扫 import 判出来的） |
| 独立复算（初筛） | **19** | 测试里有**独立复算**的痕迹（关键词初筛） |
| 只有性质/接口测试 | **14** | 只有性质/接口断言（PORTS · boundary · 单调/恒等 · 拒绝路径）——**待人工确认** |
| 无测试引用 | **2** | 没有测试文件引用它——**待人工确认** |
| 合计 | **51** | 构件总数（扫盘口径，与 `docs/components.md` 同源） |

## 二、逐件登记

| 构件 | 层 | 状态 | 验证方/证据 | 被哪个测试文件引用 | 自带自测 |
|:--|:--|:--|:--|:--|:--|
| `agm_revision` | cold | 跨构件互验 | 引用了同仓构件 propositional；疑似独立复算：命中 另算、真值表、穷尽 | `test_agm_revision.py`、`test_default_logic.py`、`test_session.py` | ✅ |
| `ai_scenarios` | ai | 无测试引用 | 没有任何测试文件引用它 | — | ✅ |
| `asp` | cold | 跨构件互验 | 引用了同仓构件 dung_framework；疑似独立复算：命中 另写、对拍、按定义、第三条路 | `test_asp.py` | ✅ |
| `belnap_four` | cold | 独立复算（初筛） | 疑似独立复算：命中 真值表 | `test_belnap_four.py` | ✅ |
| `bisimulation` | cold | 外部验证方 | 外部：外部协作者另写的分区细化实现；引用了同仓构件 mu_calculus；疑似独立复算：命中 oracle、互验、参考实现、定义直算 | `test_bisimulation.py` | ✅ |
| `boundary_paradox` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） | `test_boundary_paradox.py` | ✅ |
| `classifier` | control | 跨构件互验 | 引用了同仓构件 controller；疑似独立复算：命中 交叉 | `test_classifier.py`、`test_clue_suggester.py`、`test_controller.py`、`test_session.py`、`test_glossary.py` | ✅ |
| `cli` | engine | 跨构件互验 | 引用了同仓构件 scenarios、tools | `test_cli.py`、`test_review_marks.py`、`test_doc_commands.py`、`test_doc_examples_live.py`、`test_workshop_flow.py` | ✅ |
| `clue_suggester` | control | 跨构件互验 | 引用了同仓构件 classifier | `test_clue_suggester.py` | ✅ |
| `controller` | control | 跨构件互验 | 引用了同仓构件 classifier、scenarios；疑似独立复算：命中 交叉 | `test_controller.py`、`test_classifier.py`、`test_session.py`、`test_capability_matrix.py`、`test_fuzz.py`、`test_robustness.py` | ✅ |
| `converge_check` | mechanisms | 无测试引用 | 没有任何测试文件引用它 | — | ✅ |
| `corpus_stats` | scenarios | 跨构件互验 | 引用了同仓构件 scenarios | `test_corpus_stats.py` | ✅ |
| `counterpoint_gen` | mechanisms | 独立复算（初筛） | 疑似独立复算：命中 交叉 | `test_counterpoint_gen.py` | ✅ |
| `criticality` | mechanisms | 外部验证方 | 外部：外部协作者另写的 oracle 夹具；疑似独立复算：命中 oracle、互验、另写、对拍 | `test_criticality.py` | ✅ |
| `decidability_map` | classical | 独立复算（初筛） | 疑似独立复算：命中 已知答案 | `test_decidability_map.py`、`test_presburger.py` | ✅ |
| `default_logic` | cold | 跨构件互验 | 引用了同仓构件 agm_revision；疑似独立复算：命中 真值表、穷尽 | `test_default_logic.py` | ✅ |
| `description_logic` | cold | 独立复算（初筛） | 疑似独立复算：命中 另写、对拍、穷举、逐条核 | `test_description_logic.py` | ✅ |
| `dung_framework` | cold | 独立复算（初筛） | 疑似独立复算：命中 另写、对拍、按定义、第三条路 | `test_dung_framework.py`、`test_asp.py` | ✅ |
| `equality_tableau` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、对拍、已知答案、穷举 | `test_equality_tableau.py`、`test_fol_crosscheck.py` | ✅ |
| `first_order` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、对拍、已知答案、穷举 | `test_first_order.py`、`test_fol_crosscheck.py` | ✅ |
| `freeze_tool_schema` | ai | 只有性质/接口测试 | 只有接口/性质断言（无独立验证方） | `test_tool_contract.py` | ✅ |
| `growth_guard` | mechanisms | 外部验证方 | 外部：外部协作者另写的参考实现；疑似独立复算：命中 oracle、互验、参考实现、另写 | `test_growth_guard.py` | ✅ |
| `interval_algebra` | cold | 独立复算（初筛） | 疑似独立复算：命中 手推、穷举 | `test_interval_algebra.py` | ✅ |
| `intuitionistic_logic` | cold | 独立复算（初筛） | 疑似独立复算：命中 交叉 | `test_intuitionistic_logic.py` | ✅ |
| `lambda_calculus` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） | `test_lambda_calculus.py` | ✅ |
| `ltl` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、互验、对拍、已知答案 | `test_ltl.py`、`test_modal_family_crosscheck.py` | ✅ |
| `many_valued` | cold | 独立复算（初筛） | 疑似独立复算：命中 真值表 | `test_many_valued.py` | ✅ |
| `modal` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、互验、对拍、已知答案 | `test_modal.py`、`test_modal_family_crosscheck.py` | ✅ |
| `model_check` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、互验、反向 BFS、另一条路 | `test_model_check.py`、`test_modal_family_crosscheck.py`、`test_mu_calculus.py` | ✅ |
| `monadic_fol` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、对拍、已知答案、穷举 | `test_monadic_fol.py`、`test_fol_crosscheck.py` | ✅ |
| `mtmp` | skeleton | 独立复算（初筛） | 疑似独立复算：命中 交叉 | `test_mtmp.py` | ✅ |
| `mu_calculus` | cold | 跨构件互验 | 引用了同仓构件 model_check；疑似独立复算：命中 oracle、互验、参考实现、反向 BFS | `test_mu_calculus.py`、`test_bisimulation.py` | ✅ |
| `nd_propositional` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、另写、对拍、已知答案 | `test_nd_propositional.py`、`test_classical_crosscheck.py` | ✅ |
| `observer_bypass` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 3 条（能挡回归，**不构成独立验证方**） | `test_observer_bypass.py` | ✅ |
| `paradox_annotate` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） | `test_paradox_annotate.py` | ✅ |
| `paradox_measure` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 21 条（能挡回归，**不构成独立验证方**） | `test_paradox_measure.py`、`test_fuzz.py`、`test_robustness.py` | ✅ |
| `presburger` | classical | 跨构件互验 | 引用了同仓构件 decidability_map；疑似独立复算：命中 已知答案 | `test_presburger.py` | ✅ |
| `propositional` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、另写、另算、对拍 | `test_propositional.py`、`test_classical_crosscheck.py`、`test_agm_revision.py`、`test_relevance_logic.py` | ✅ |
| `recursion_theorem` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） | `test_recursion_theorem.py` | ✅ |
| `relevance_logic` | cold | 跨构件互验 | 引用了同仓构件 propositional | `test_relevance_logic.py` | ✅ |
| `repl` | engine | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） | `test_repl.py` | ✅ |
| `resolution` | classical | 独立复算（初筛） | 疑似独立复算：命中 oracle、另写、对拍、已知答案 | `test_resolution.py`、`test_classical_crosscheck.py` | ✅ |
| `review_marks` | scenarios | 跨构件互验 | 引用了同仓构件 cli | `test_review_marks.py`、`test_session.py` | ✅ |
| `scenarios` | scenarios | 独立复算（初筛） | 疑似独立复算：命中 交叉 | `test_scenarios.py`、`test_controller.py`、`test_session.py`、`test_corpus_stats.py`、`test_cli.py`、`test_docs_consistency.py`、`test_fuzz.py`、`test_review_packet.py` | ✅ |
| `selfref_fixpoint` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 9 条（能挡回归，**不构成独立验证方**） | `test_selfref_fixpoint.py` | ✅ |
| `session` | control | 跨构件互验 | 引用了同仓构件 agm_revision、classifier、controller、review_marks、scenarios、wall_pipeline | `test_session.py`、`test_ledger_traceable.py` | ✅ |
| `stlc` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 2 条（能挡回归，**不构成独立验证方**） | `test_stlc.py` | ✅ |
| `tools` | ai | 只有性质/接口测试 | 用例集：期望值直接写死 57 条（能挡回归，**不构成独立验证方**） | `test_tools.py`、`test_tool_contract.py`、`test_capability_matrix.py`、`test_cli.py`、`test_docs_consistency.py`、`test_fuzz.py`、`test_glossary.py`、`test_robustness.py` | ✅ |
| `truth_revision` | cold | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） | `test_truth_revision.py` | ✅ |
| `turing_machine` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） | `test_turing_machine.py` | ✅ |
| `wall_pipeline` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 114 条（能挡回归，**不构成独立验证方**） | `test_wall_pipeline.py`、`test_session.py` | ✅ |

> "自带自测"指模块自己的 `__main__` 里跑的那套——**那是自证，不算独立验证方**，
> 单独列出来是为了看清"自测绿"与"有人独立验过"是两件事。

## 三、只自证 / 没测的（这些必须登记签字）

判据：这些件**没有**独立验证方——测试只能挡回归，不能证明对。
补法（按省事程度）：① 找**同仓另一个构件**互验（把问题翻译过去，两条独立实现互相验）；
② 在测试里写**另一条算法**（穷举小模型 / 按定义直算 / 反向 BFS 这类，不走构件内部那条路）；
③ 请**外部实现**对拍（跑法可留在仓库外，本仓测试里点名验证方即可）。

| 构件 | 层 | 状态 | 现在有什么 |
|:--|:--|:--|:--|
| `ai_scenarios` | ai | 无测试引用 | 没有任何测试文件引用它 |
| `boundary_paradox` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） |
| `converge_check` | mechanisms | 无测试引用 | 没有任何测试文件引用它 |
| `freeze_tool_schema` | ai | 只有性质/接口测试 | 只有接口/性质断言（无独立验证方） |
| `lambda_calculus` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） |
| `observer_bypass` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 3 条（能挡回归，**不构成独立验证方**） |
| `paradox_annotate` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） |
| `paradox_measure` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 21 条（能挡回归，**不构成独立验证方**） |
| `recursion_theorem` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 5 条（能挡回归，**不构成独立验证方**） |
| `repl` | engine | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） |
| `selfref_fixpoint` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 9 条（能挡回归，**不构成独立验证方**） |
| `stlc` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 2 条（能挡回归，**不构成独立验证方**） |
| `tools` | ai | 只有性质/接口测试 | 用例集：期望值直接写死 57 条（能挡回归，**不构成独立验证方**） |
| `truth_revision` | cold | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） |
| `turing_machine` | classical | 只有性质/接口测试 | 用例集：期望值直接写死 6 条（能挡回归，**不构成独立验证方**） |
| `wall_pipeline` | mechanisms | 只有性质/接口测试 | 用例集：期望值直接写死 114 条（能挡回归，**不构成独立验证方**） |

> **口径提醒**：`只有性质/接口测试` 是"关键词初筛 ＋ 结构判据"的结果，**不是终判**——
> 换一种写法就可能认不出来（本表第一版就因为词表没对上语料，把一批有独立路的件误判进来，
> 校准后从 26 件降到 21 件）。所以每一件都留了**人工确认位**（登记表在测试文件里）。

