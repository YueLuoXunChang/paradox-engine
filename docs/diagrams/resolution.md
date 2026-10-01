# 归结 resolution — 逻辑流程图

> 模块：`engine/classical/resolution.py` · 层：第 1 层经典逻辑（子句归结，带量词）
> 一句话：把公式**子句化成 CNF 子句集**（顺带把存在量词换掉），再对着子句对反复求归结式——
> **出现空子句就证明成立**，归结步数用完就如实报"没到结论"，并把每步归结式留痕。
> 图 1 → `run()` 主流程：子句化 → 归结 → 空子句
> 图 2 → 子句化四步与 Skolem 化的记账
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：归结到空子句为止

```mermaid
flowchart TD
  IN["run(inputs)"] --> C1{"给了结论吗?"}
  C1 -->|没给| R1["conclusion_pending"]
  C1 -->|给了| C2["把前提与结论合成待证公式集"]
  C2 --> C3{"解析并子句化成功?"}
  C3 -->|否| R2["parse_error<br/>报出失败原因"]
  C3 -->|是| C4["得到 CNF 子句集<br/>附用到的 Skolem 常量"]
  C4 --> L1{"还有没试过的子句对吗?"}
  L1 -->|有| L2["取一对子句求归结式<br/>能合一的对消掉互补文字"]
  L2 --> L3{"归结式是空子句吗?"}
  L3 -->|是| O1["proved<br/>给出归结链"]
  L3 -->|否| L4{"这条归结式以前见过?"}
  L4 -->|见过| L1
  L4 -->|没见过| L5["加进子句集"] --> L6{"步数到上限了吗?"}
  L6 -->|没到| L1
  L6 -->|到了| O2["not_proved<br/>归结链截前 20 步"]
  L1 -->|全试完没有新的| O2
  O1 --> BND
  O2 --> BND
  BND["boundary：归结步数有上限——<br/>到上限只说'没归结出来'，不说'证不出'"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R1,R2 stop
  class BND,O1 out
  class C1,C2,C3,C4,L1,L2,L4,L5,L6 tool
  class L3,O2 stop
```

## 二、子句化四步：消蕴含 → 否定内移 → Skolem 化 → 取 CNF

```mermaid
flowchart TD
  A["待证公式"] --> S1["第一步：消去蕴含与等值<br/>都换成否定 或 合取 或 析取"]
  S1 --> S2["第二步：否定内移<br/>量词与联结词逐层翻，直到贴着原子"]
  S2 --> S3{"碰到存在量词吗?"}
  S3 -->|是| S4["第三步：Skolem 化<br/>换成新的常量名，并记账"]
  S3 -->|否| S5["量词原样保留"]
  S4 --> S6["第四步：拆成子句集<br/>合取拆条，析取成一条子句"]
  S5 --> S6
  S6 --> S7["子句集：每条形如文字的析取"]
  S7 --> S8["归结：找互补文字<br/>做合一代换后相消"]
  S8 --> S9{"得到空子句?"}
  S9 -->|是| S10["proved：矛盾已导出"]
  S9 -->|否| S11["把新归结式并入集<br/>继续找下一对"]
  S10 --> S12["Skolem 用的常量名随结果给出<br/>便于复核"]
  S11 --> S12
  S12 --> BND["boundary：子句化会指数膨胀——<br/>所以有步数上限与截断，且如实标注"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A core
  class S1,S2,S3,S4,S5,S6,S7,S8,S9,S11,S12 tool
  class S10 out
  class BND stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`premises`（前提列表）· `conclusion`（结论）·
  `facts`（额外事实）· `max_resolvents`（归结步数上限，默认 500）。
- **判词**：`proved` · `not_proved` · `parse_error` · `conclusion_pending`。
- **出口是"空子句"**：归结链里一旦出现空子句（链上记作 `□`），就是 `proved`——
  判据是**矛盾导出来了**，不是"看起来像"。
- **Skolem 化会记账**：存在量词换成新常量（形如 `c_1`、`c_2`），用到的名字在
  `skolem_used` 里列出；**常量名是新鲜生成的**，不与会话里已有名字撞车。
- **合一**：归结前先对两边的文字做合一（含出现检查，避免无限替换），
  合一代换作用到整条归结式上。
- **两条如实标注的截断**：归结步数到 `max_resolvents` 或子句对试尽仍无新子句 →
  `not_proved`，且**归结链只截前 20 步**（免得结果里塞进整条长链）。
- **诚实边界**（`boundary` 字段随每个返回点带回）：子句化与归结都可能指数膨胀，
  所以**上限与截断都写在返回里**；`not_proved` 只意味着"按这个上限没归结出来"，
  **不等于"结论不成立"**；本件只判可证性，不做取舍决策。
