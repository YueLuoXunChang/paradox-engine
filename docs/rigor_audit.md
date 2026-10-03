# 硬核度体检报告

> 本文件由 `engine/_rigor_audit.py --write` 生成，**不要手改**。
> 口径：① 判据＝阈值必须被测试钉住或声明为参数（硬错）；②③④ 只报数，不判错。

## 一、① 判据轴（阈值钉边界）

- 阈值被测试钉住 27 个 · 声明为参数 13 个 · **未钉未声明 0 个**

## 二、② 算法轴（有嵌套循环、无上限或复杂度声明）

共 **12** 件：ai_scenarios、freeze_tool_schema、ltl、modal、model_check、monadic_fol、belnap_four、intuitionistic_logic、clue_suggester、corpus_stats、review_marks、mtmp

## 三、③ 验证轴（口径：**验证方登记**，不是本件自己扫的）

- 口径来源：验证方登记 engine/_verifier_audit.py（AST 扫 import ＋ 人工签字）
- 处于"未验状态"的构件 **16** 件（只有性质·接口测试 14 件 ＋ 无测试引用 2 件）：

```
ai_scenarios、boundary_paradox、converge_check、freeze_tool_schema、lambda_calculus、observer_bypass
paradox_annotate、paradox_measure、recursion_theorem、repl、selfref_fixpoint、stlc
tools、truth_revision、turing_machine、wall_pipeline
```

**旁证**（关键词扫描，**不参与口径**，只作参考）：随机对拍 5 件 · 独立互验字样 16 件 · 变异字样 2 件；三样都扫不到的是 33 件——**与上面那个数不同是正常的**，差异来自判据不同（关键词 vs AST），以登记为准。

## 四、④ 契约轴（PORTS / boundary 缺口）

- 没有 PORTS：**ai_scenarios、review_marks**
- 返回里没有 boundary：**ai_scenarios、review_marks**
- 没有测试文件：**ai_scenarios、freeze_tool_schema、converge_check**

## 五、边界

本件只做**静态体检**：数阈值、数覆盖、数验证手段，不执行被测构件、不判对错。阈值那条是**硬错**（没被钉住或声明就是没钉住）；其余三条轴只报数，因为"该用什么验证手段"要按构件性质定，不由本件替它决定。

> 更正记录：第一版把"模块里写过参数/约定这类词"当作已声明，结果 11 件阈值全部"看起来合规"——太松。改成"阈值名必须出现在测试里，或定义行附近写明是参数"，才量出真实缺口。
