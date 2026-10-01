# 相干逻辑 relevance_logic — 逻辑流程图

> 模块：`engine/cold/relevance_logic.py` · 层：第 3 层冷门逻辑（相干性）
> 一句话：问两件事——**前提与结论有没有共享原子**（相干），以及**两个命题是真冲突还是空洞冲突**。
> 相干与否，与"经典上有没有效"是**两个维度**，本件把两个维度都报出来。
> 图 1 → `run()` 两个模式与相干四态（相干 × 有效）
> 图 2 → 冲突定性：真冲突与空洞冲突怎么分开
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：相干四态是两个维度的交叉

```mermaid
flowchart TD
  IN["run(inputs)"] --> M{"mode 是哪个?"}
  M -->|既不是 conflict 也不是 relevance| R0["input_pending<br/>只认这两个模式"]
  M -->|conflict| C0{"给了两个命题吗?"}
  M -->|relevance| P0{"给了前提与结论吗?"}
  C0 -->|没给| R1["input_pending"]
  C0 -->|给了| C1["解析两个命题成原子集合"]
  P0 -->|没给| R1
  P0 -->|给了| P1["解析前提与结论成原子集合"]
  C1 --> C2{"两边都解析成功了吗?"}
  C2 -->|否| R2["parse_pending<br/>解析不了就如实说"]
  C2 -->|是| C3["取共享原子"]
  P1 --> P2{"解析成功了吗?"}
  P2 -->|否| R2
  P2 -->|是| P3["取共享原子"]
  C3 --> D1{"共享原子为空?"}
  P3 --> D1B{"共享原子为空?"}
  D1 -->|是| H1["空洞冲突<br/>形如两件各自自相矛盾的事"]
  D1 -->|否| H2["真冲突<br/>冲突落在共同的原子上"]
  D1B -->|是| REL0["不相干"]
  D1B -->|否| REL1["相干"]
  H1 --> BND
  H2 --> BND
  REL0 --> V1{"经典上有效吗?"}
  REL1 --> V1
  V1 -->|无效且不相干| Q1["irrelevant_invalid"]
  V1 -->|有效且不相干| Q2["irrelevant_valid"]
  V1 -->|无效且相干| Q3["relevant_invalid"]
  V1 -->|有效且相干| Q4["relevant_valid"]
  Q1 --> BND
  Q4 --> BND
  BND["boundary：相干性与经典有效性分开报<br/>判不了就 undecided，不替使用者下结论"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R0,R1,R2 stop
  class BND out
  class C0,C1,C2,C3,D1,D1B,M,P0,P1,P2,P3,REL0,REL1,V1 tool
  class H1,H2,Q1,Q2,Q3,Q4 out
```

## 二、冲突定性：先看共享原子，再看各自是不是自相矛盾

```mermaid
flowchart TD
  A["两个命题 A 与 B"] --> S1["各取原子集合"]
  S1 --> S2{"解析成功?"}
  S2 -->|否| S3["parse_pending<br/>不猜"]
  S2 -->|是| S4["求交：共享原子"]
  S4 --> S5{"交集为空?"}
  S5 -->|空| T1["不相干的一对：<br/>冲突若存在，也是各说各的"]
  S5 -->|不空| T2["相干的一对：<br/>冲突落在共同的原子上"]
  T1 --> T3{"两边互不冲突?"}
  T2 --> T3
  T3 -->|互不冲突| T4["no_conflict"]
  T3 -->|冲突| T5{"交集为空?"}
  T5 -->|是| T6["hollow_conflict<br/>空洞冲突：形似而实不同"]
  T5 -->|否| T7["real_conflict<br/>真冲突"]
  T4 --> U1["仍要报共享原子<br/>供使用者自己看"]
  T6 --> U1
  T7 --> U1
  U1 --> U2["判不了共享结构时<br/>返回 undecided"]
  U2 --> BND["boundary：本件判的是'相干结构'，<br/>不是'该信哪一个'"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A core
  class S1,S2,S4,S5,T1,T2,T3,T5,U1,U2 tool
  class T4,T6,T7 out
  class S3,BND stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`relevance` / `conflict`）· `premises`（前提列表）·
  `conclusion`（结论）· `prop_a` · `prop_b`（冲突模式的两个命题）。
- **判词**：`relevant_valid` · `relevant_invalid` · `irrelevant_valid` · `irrelevant_invalid` ·
  `real_conflict` · `hollow_conflict` · `no_conflict` · `undecided` · `parse_pending` ·
  `input_pending`。
- **两个维度分开报**：**相干**看的是前提与结论**有没有共享原子**；**有效**看的是经典语义下
  前提能否推出结论。四态就是这两维的交叉——所以"不相干但经典有效"（`irrelevant_valid`）
  是一个**正常结果**，不是异常，也不是"错了"。
- **空洞冲突**（`hollow_conflict`）：两个命题各自都自相矛盾（比如两件互不相干的事各自
  又正又反），但**没有共享原子**——形式上像冲突，结构上不相干。真冲突落在共同原子上。
- **输出**：`shared_atoms` · `premise_atoms` · `conclusion_atoms` · `classically_valid` ·
  `counterexample`（给出反例，便于复核）。
- **诚实边界**（`boundary` 字段随每个返回点带回）：解析不了就 `parse_pending`，
  结构判不了就 `undecided`，**不硬给四态**；本件只判**相干结构**与经典有效性，
  **不判"该信哪一个"、不做取舍决策**。
