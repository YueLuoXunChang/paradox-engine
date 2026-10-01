# 命题逻辑 propositional — 逻辑流程图

> 模块：`engine/classical/propositional.py` · 层：第 1 层经典逻辑（命题真值表）
> 一句话：把公式枚举**全部赋值**算真值表，据此判**有效性**（前提能否推出结论）、
> **可满足性**、以及公式是不是重言式 / 矛盾式；原子太多就如实拦下，不硬算。
> 图 1 → `run()` 三条路与四道拦（缺前提 / 缺结论 / 解析失败 / 规模超限）
> 图 2 → 有效性是怎么判的，反例从哪来
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：三条路，四道拦

```mermaid
flowchart TD
  IN["run(inputs)"] --> M{"走哪条路?"}
  M -->|有前提且有结论<br/>或 mode 是有效性| P1{"给了前提吗?"}
  P1 -->|没给| R1["premises_pending"]
  P1 -->|给了| P2{"给了结论吗?"}
  P2 -->|没给| R2["conclusion_pending"]
  P2 -->|给了| P3["连前提与结论一起解析"]
  M -->|mode 是真值表| T1{"给了 formula 吗?"}
  T1 -->|没给| R3["formula_pending"]
  T1 -->|给了| T2["解析这个公式"]
  M -->|mode 是可满足| S1["解析这个公式"]
  P3 --> E1{"解析成功?"}
  T2 --> E1
  S1 --> E1
  E1 -->|否| R4["parse_error<br/>给出出错位置"]
  E1 -->|是| A1{"原子数不超过 10?"}
  A1 -->|否| R5["size_limit<br/>枚举会爆，如实拦下"]
  A1 -->|是| A2["枚举全部赋值"]
  A2 --> V1{"当前模式?"}
  V1 -->|有效性| V2{"有赋值让前提全真而结论假?"}
  V2 -->|有| O2["invalid<br/>附反例赋值"]
  V2 -->|没有| O1["valid"]
  V1 -->|真值表| O3["truth_table<br/>逐行列出"]
  V1 -->|可满足| V4{"有赋值让它为真?"}
  V4 -->|有| O4["satisfiable"]
  V4 -->|没有| O5["unsatisfiable"]
  O1 --> BND
  O2 --> BND
  O3 --> BND
  O4 --> BND
  O5 --> BND
  BND["boundary：枚举型判定——原子多、公式大一律如实报，<br/>不给没算过的结论"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R1,R2,R3,R4,R5 stop
  class BND,O1,O2,O3,O4,O5 out
  class A1,A2,E1,M,P1,P2,P3,S1,T1,T2,V1,V2,V4 tool
```

## 二、有效性怎么判：反例就是"前提全真、结论为假"的那一行

```mermaid
flowchart TD
  A["前提集合 + 结论"] --> B1["收集出现过的原子"]
  B1 --> B2["给出原子到真假的赋值表"]
  B2 --> B3{"还有没试过的赋值吗?"}
  B3 -->|有| B4["算出该赋值下<br/>每个前提与结论的真值"]
  B4 --> B5{"前提全真且结论为假?"}
  B5 -->|是| B6["记下这一行当反例"]
  B5 -->|否| B3
  B6 --> B7["invalid：反例一行就够"]
  B3 -->|试完了| B8["valid：找不到反例"]
  B7 --> C1["结论同时给：反例赋值 + 原子表"]
  B8 --> C1
  C1 --> D1["真值表模式另给逐行表"]
  D1 --> BND["boundary：判定是枚举出来的——<br/>超出枚举上限就报 size_limit，不猜"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A core
  class B1,B2,B3,B4,B5,C1,D1 tool
  class B7,B8 out
  class B6,BND stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`formula`（单个公式）· `premises`（前提列表）· `conclusion`（结论）·
  `mode`（`validity` / `truth_table` / `satisfiable`，也可由"给了前提与结论"自动走有效性）。
- **判词**：`valid` · `invalid` · `truth_table` · `satisfiable` · `unsatisfiable` ·
  `parse_error` · `size_limit` · `premises_pending` · `conclusion_pending` · `formula_pending`。
- **契约**：`_CONNECTIVES` 认 `¬ ∧ ∨ → ↔`；优先级 `↔ 小于 → 小于 ∨ 小于 ∧`（数值越大结合越紧）。
- **规模上限**：`_MAX_ATOMS = 10`——原子超过 10 个，赋值组合会爆，直接报 `size_limit`
  并把原子数列出来，**不硬算**。
- **反例是判定的副产品**：`invalid` 一定带一个反例赋值（前提全真而结论假的那一行），
  可以直接拿去复核；`valid` 则不给反例。
- **无前提 / 无结论**是两件不同的事，分别报 `premises_pending` 与 `conclusion_pending`，
  这样调用方知道缺的是哪一半。
- **诚实边界**（`boundary` 字段随每个返回点带回）：本件是**枚举型**判定——给的都是
  算过的结果；解析失败报 `parse_error` 并指出位置；**只判真值与可满足性，
  不管公式"该不该写"，也不做任何取舍决策**。
