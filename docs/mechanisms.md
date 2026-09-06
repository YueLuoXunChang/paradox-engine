# paradox-engine · 能力目录

> 分层：第 0 层骨架（规划）· 第 1 层经典逻辑（建设中）· 第 2 层悖论（已有）·
> 第 3 层冷门（规划）· 第 4 层 AI 挂载（规划）。见 docs/ROADMAP.md。
> 每个文件自包含：`python <文件>` 直接跑自测。

## 第 2 层 · 悖论（核心三件套，已收）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/mechanisms/paradox_measure.py | 悖论强度 μ ∈ [0,1]（四分支） | ✅ |
| engine/mechanisms/paradox_annotate.py | 悖论注解（8 字段卡 + P-A/B/C） | ✅ |
| engine/mechanisms/converge_check.py | 收敛判定（压缩/有限步/渐进/振荡） | ✅ |

## 第 1 层 · 经典逻辑学基础

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/classical/propositional.py | 命题逻辑：真假/有效性/可满足性/重言式（经典二值） | ✅ 自测8+正式15 |
| engine/classical/first_order.py | 一阶谓词：量词/关系/逻辑后承（有限论域展开法，可判） | ✅ 自测7+正式11 |
| engine/classical/ltl.py | 时序 LTL：G/F/X/U 沿路径判定（含违约定位） | ✅ 自测8+正式14 |
| engine/classical/modal.py | 模态逻辑：□/◇ Kripke 语义（K/T/S4/S5，框架自检） | ✅ 自测7+正式14 |
| engine/classical/lambda_calculus.py | λ 演算：β 归约/邱奇编码/Y 不动点（自指计算版） | ✅ 自测5+正式16 |
| engine/classical/turing_machine.py | 图灵机：模拟/UTM 自模拟/停机不可判定演示 | ✅ 自测6+正式14 |
| nd_propositional.py | 命题自然演绎 ND（规划） | ⏳ |
| resolution.py | 一阶归结：Skolem+合一（规划） | ⏳ |
| equality_tableau.py | 等词 + 表列法 tableau（规划） | ⏳ |
| turing_machine.py | 图灵机：模拟/UTM 自模拟/停机演示（规划） | ⏳ |
| stlc.py | 简单类型 λ 演算 STLC（规划，后补） | ⏳ |

> 每构件完整规格见任务指标《39_逻辑建模引擎_经典逻辑层详规》v2。

## 为什么分层

- **第 1 层经典逻辑**：别人一看就懂、可靠（经典共识）——证明"这不是玄学"；
- **第 2 层悖论**：独特的在下一层——矛盾当第一公民（测量→注解→报告）；
- 只诊断不决策：把判断留给使用它的人。

## 规划中（见 docs/ROADMAP.md）

撞墙处理管线（无限递归收敛三态/边界悖论/悖论全程自反）· MT-MP-TL 骨架 ·
冷门逻辑（Dung/次协调）· 对位创生 · AI 挂载层。
