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

## 第 1 层 · 经典逻辑（建设中）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/classical/propositional.py | 命题逻辑：真假/有效性/可满足性/重言式（经典二值） | ✅ 自测8+正式15 |
| engine/classical/first_order.py | 一阶谓词：量词/关系/逻辑后承（有限论域展开法，可判） | ✅ 自测7+正式11 |
| engine/classical/ltl.py | 时序 LTL：G/F/U 路径判定（规划） | ⏳ |
| engine/classical/modal.py | 模态 K：□/◇ 可能世界（规划） | ⏳ |

## 为什么分层

- **第 1 层经典逻辑**：别人一看就懂、可靠（经典共识）——证明"这不是玄学"；
- **第 2 层悖论**：独特的在下一层——矛盾当第一公民（测量→注解→报告）；
- 只诊断不决策：把判断留给使用它的人。

## 规划中（见 docs/ROADMAP.md）

撞墙处理管线（无限递归收敛三态/边界悖论/悖论全程自反）· MT-MP-TL 骨架 ·
冷门逻辑（Dung/次协调）· 对位创生 · AI 挂载层。
