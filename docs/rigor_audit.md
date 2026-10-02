# 硬核度体检报告

> 本文件由 `engine/_rigor_audit.py --write` 生成，**不要手改**。
> 口径：① 判据＝阈值必须被测试钉住或声明为参数（硬错）；②③④ 只报数，不判错。

## 一、① 判据轴（阈值钉边界）

- 阈值被测试钉住 27 个 · 声明为参数 13 个 · **未钉未声明 0 个**

## 二、② 算法轴（有嵌套循环、无上限或复杂度声明）

共 **12** 件：ai_scenarios、freeze_tool_schema、ltl、modal、model_check、monadic_fol、belnap_four、intuitionistic_logic、clue_suggester、corpus_stats、review_marks、mtmp

## 三、③ 验证轴（随机对拍 / 独立互验 / 变异接受 三样皆无）

共 **35** 件（占 49 件构件）：

```
ai_scenarios、freeze_tool_schema、tools、decidability_map、equality_tableau、first_order
lambda_calculus、ltl、modal、model_check、monadic_fol、nd_propositional
presburger、propositional、recursion_theorem、resolution、stlc、turing_machine
default_logic、interval_algebra、many_valued、relevance_logic、classifier、clue_suggester
session、boundary_paradox、converge_check、observer_bypass、paradox_annotate、paradox_measure
selfref_fixpoint、wall_pipeline、corpus_stats、review_marks、scenarios
```

## 四、④ 契约轴（PORTS / boundary 缺口）

- 没有 PORTS：**ai_scenarios、review_marks**
- 返回里没有 boundary：**ai_scenarios、review_marks**
- 没有测试文件：**ai_scenarios、freeze_tool_schema、converge_check**

## 五、边界

本件只做**静态体检**：数阈值、数覆盖、数验证手段，不执行被测构件、不判对错。阈值那条是**硬错**（没被钉住或声明就是没钉住）；其余三条轴只报数，因为"该用什么验证手段"要按构件性质定，不由本件替它决定。

> 更正记录：第一版把"模块里写过参数/约定这类词"当作已声明，结果 11 件阈值全部"看起来合规"——太松。改成"阈值名必须出现在测试里，或定义行附近写明是参数"，才量出真实缺口。
