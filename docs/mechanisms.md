# paradox-engine · 能力目录

> 分层：总控（神经系统）· 第 0 层骨架（✅）· 第 1 层经典逻辑（✅）·
> 第 2 层悖论（✅ 核心）· 第 3 层冷门（规划）· 第 4 层 AI 挂载（规划）。
> 见 docs/ROADMAP.md。每个文件自包含：`python <文件>` 直接跑自测。

## 总控 · 引擎大脑（38 总控五步）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/control/classifier.py | 判类器+复杂度+路由：12 题型信号表计分 → 主型/副型/置信度 → L1/L2/L3 → ROUTE 36 键（带 reason 白箱） | ✅ 自测6+正式69 |
| engine/control/controller.py | 总控五步流水线：判类→复杂度→切路→真跑构件→五查判输出（中文报告+结构化对象） | ✅ 自测6+正式35 |

## 第 0 层 · MT-MP-TL 骨架（结构表达，不掺判定）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/skeleton/mtmp.py | 点（异构/自治/变形）+ 线程（方向/速度/汇合/交叉）+ 拓扑 12 形态分类 + 操作（connect/disconnect/replace/fold/spawn） | ✅ 自测6组+正式42 |

## 第 2 层 · 悖论（矛盾当第一公民——落落独创主场）

### 核心三件套（初版）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/mechanisms/paradox_measure.py | 悖论强度 μ ∈ [0,1]（四分支，mu2 自指直判） | ✅ 自测1 |
| engine/mechanisms/paradox_annotate.py | 悖论注解（8 字段卡 + P-A/B/C 分级） | ✅ 自测6 |
| engine/mechanisms/converge_check.py | 收敛判定（压缩/有限步/渐进/振荡） | ✅ 自测6 |

### 撞墙管线五件（阶段 2 新增，41 详规 2.3-2.6 + 管线 A）

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/mechanisms/selfref_fixpoint.py | 递归修正 × 自指检测：共振带三态（不动点/共振带/发散）+ 说谎者每步翻转 + 哥德尔 P-A 注解 | ✅ 自测7+正式23 |
| engine/mechanisms/boundary_paradox.py | 边界悖论判定：墙=边界（张力/划设即撤销/重生路径，B(B(S)) 递归） | ✅ 自测4+正式20 |
| engine/mechanisms/observer_bypass.py | 悖论全程自反旁路：主链不停，旁路观察+注解+注入参考（架构级免疫） | ✅ 自测4+正式22 |
| engine/mechanisms/counterpoint_gen.py | 对位创生第三态：对立交汇 → 候选+依据（同向两全/反向共振/交叉桥） | ✅ 自测5+正式21 |
| engine/mechanisms/wall_pipeline.py | 撞墙管线 A：测墙→注解→钻墙→看墙→旁路→创生 → **五选一诊断** | ✅ 自测5+正式24 |

## 第 1 层 · 经典逻辑学基础

| 文件 | 一句话 | 状态 |
|---|---|---|
| engine/classical/propositional.py | 命题逻辑：真假/有效性/可满足性/重言式（经典二值） | ✅ 自测8+正式15 |
| engine/classical/first_order.py | 一阶谓词：量词/关系/逻辑后承（有限论域展开法，可判） | ✅ 自测7+正式11 |
| engine/classical/ltl.py | 时序 LTL：G/F/X/U 沿路径判定（含违约定位） | ✅ 自测9+正式14 |
| engine/classical/modal.py | 模态逻辑：□/◇ Kripke 语义（K/T/S4/S5，框架自检） | ✅ 自测7+正式14 |
| engine/classical/lambda_calculus.py | λ 演算：β 归约/邱奇编码/Y 不动点（自指计算版） | ✅ 自测5+正式16 |
| engine/classical/turing_machine.py | 图灵机：模拟/UTM 自模拟/停机不可判定演示 | ✅ 自测6+正式14 |
| engine/classical/nd_propositional.py | 命题自然演绎 ND（证明树/经典 vs 直觉主义） | ✅ 自测8+正式16 |
| engine/classical/resolution.py | 一阶归结（Skolem+合一+归结链，常量≠变量） | ✅ 自测6+正式10 |
| engine/classical/equality_tableau.py | 等词替换 + 命题 tableau（反例模型） | ✅ 自测6+正式14 |
| engine/classical/stlc.py | 简单类型 λ STLC（类型检查/推导，拦自应用，Curry-Howard） | ✅ 自测8+正式15 |

> 每构件完整规格见任务指标《39_逻辑建模引擎_经典逻辑层详规》v2。

## 为什么分层

- **第 1 层经典逻辑**：别人一看就懂、可靠（经典共识）——证明"这不是玄学"；
- **第 2 层悖论**：独特的在下一层——矛盾当第一公民（测量→注解→钻墙
  五选一→创生）；经典层撞到不可判定 → 上卷第 2 层 → 五选一诊断
  （可判/良性自指/共振带自指/发散真墙/可创生），把"墙"从终点变成
  状态机的一格；
- 只诊断不决策：把判断留给使用它的人。

## 规划中（见 docs/ROADMAP.md）

MT-MP-TL 骨架（阶段 3）· 冷门逻辑（阶段 4：Dung/次协调 Belnap）·
对位创生扩展（阶段 5 已并入 2.6）· AI 挂载层（阶段 6）。
