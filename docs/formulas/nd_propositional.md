# 公式卡：命题自然演绎（nd_propositional）

> 概念来源：经典证明论（Gentzen 自然演绎 ND）——非落落原创，经典共识
> 代码：engine/classical/nd_propositional.py · 测试：engine/classical/test_nd_propositional.py
> 与 1.1 区别：1.1 判"真吗"（语义枚举）；1.2 证"怎么证出来"（证明论规则推导）。

## 一、导言

自然演绎用**引入/消去规则**从前提推结论，每步带规则名——产出证明树白箱，
不是"有效/无效"二值。回答"这公式怎么证出来、依据是什么"。

## 二、规则集

| 规则 | 形式 | 名称 |
|---|---|---|
| → 引入 | [A]⋮B ⊢ A→B | 假设引入后消去 |
| → 消去 | A→B, A ⊢ B | modus ponens |
| ∧ 引入/消去 | A,B⊢A∧B；A∧B⊢A/B | 合取 |
| ∨ 引入/消去 | A⊢A∨B；A∨B,[A]⋮C,[B]⋮C⊢C | 析取 |
| ¬ 引入 | [A]⋮⊥ ⊢ ¬A | 归谬 |
| ⊥ 消去 | ⊥ ⊢ A | 爆炸（ex falso）|
| ¬¬ 消去 | ¬¬A ⊢ A | **经典特有（直觉主义无）** |

## 三、判定算法（反向搜索）

```
search(goal, hyps):
  goal ∈ hyps → axiom 闭合
  goal = A→B → →引入：hyps+{A} 证 B
  goal = A∧B → ∧引入：分别证 A、B
  goal = ¬A → ¬引入：hyps+{A} 找 ⊥
  goal = A∨B → ∨引入（证一支）；失败走经典反证（classical）
  hyps 有 A∨B → ∨消去：A 下、B 下分别证 goal
  hyps 有矛盾 → ⊥消去（爆炸）
  classical 附加：¬¬消去、反证（¬goal→⊥→¬¬goal→goal）
```

## 四、性质（P）

- P1 可靠：证明树的每步都是有效推理（规则保真）；
- P2 经典/直觉主义区分：¬¬消去是经典特有——system 参数标注；
- P3 证明树白箱：每步规则名+依据可复核；
- P4 命题可判定：真值表 2ⁿ（1.1）保证"能否证"有语义答案；ND 搜索是
  找"证明路径"（可能多条）。

## 五、注记与边界

- **搜索不完整**：本策略非穷举完备（如排中律的经典反证证明需要更深
  reductio 嵌套）——not_proved 输出标注"未找到≠不可证"（诚实）；
- 排中律 ⊢P∨¬P（经典）：策略能力内可能 not_proved——这是**诚实边界**
  不是错误：ND 证明存在（经典）但搜索策略未必找到；
- 系统标注：同一公式在 classical/intuitionistic 结论可不同——输出带 system。
