# 公式卡：命题逻辑构件（propositional）

> 概念来源：经典逻辑（命题逻辑标准语义）——非落落原创，经典共识
> 代码：engine/classical/propositional.py · 测试：engine/classical/test_propositional.py
> 本构件归第 1 层（经典地基层）：只做经典框架内能算的，不掺私货。

## 一、导言

命题逻辑是逻辑的地基：把断言（P、Q…）用联结词（¬ ∧ ∨ → ↔）组合，
判定真假、推理有效性、可满足性、公式类型。别人一看就懂——它证明
paradox-engine 不是玄学。

## 二、判定原理

n 个原子 → 2ⁿ 个真值指派全枚举（经典语义）：
- **有效性**：前提都真时结论必真（无任何指派使前提真结论假）；
- **无效 → 反例**：给出一个"前提真、结论假"的指派（最有价值的输出）；
- **重言式**：所有指派下都真（如排中律 P∨¬P）；
- **矛盾式**：所有指派下都假（如 P∧¬P）；
- **可满足**：存在指派使其真。

## 三、性质（P）

- P1 三段论：((P→Q) ∧ P) → Q 是重言式 → 推理有效；
- P2 反例存在性：P∨Q ⊢ P 无效，反例 {P=假, Q=真}；
- P3 排中律 P∨¬P 恒真；无矛盾律 ¬(P∧¬P) 恒真；
- P4 二值完备：真/假穷尽一切指派。

## 四、公式（判定结构）

```
run({formula} 或 {premises, conclusion, mode})
  ├─ validity：premises ⊢ conclusion？invalid 给反例指派
  ├─ truth_table：完整真值表（原子 ≤ 上限）
  ├─ satisfiable：有真指派吗
  └─ 默认 kind：tautology / contradiction / contingent
诚实拦截：解析失败 → parse_error；原子过多 → size_limit（不硬枚举）
```

## 五、注记与边界

- 原子数 > 10 → size_limit（2ⁿ 爆炸，诚实报规模，建议拆式/转谓词）；
- 经典二值语义——不掺三值/四值（那是第 2/3 层 Belnap/次协调的事）；
- 反例指派是最有价值的输出：证明"为什么无效"，白箱可复核。
