# Dung 论证框架 dung_framework — 逻辑流程图

> 模块：`engine/cold/dung_framework.py` · 层：第 3 层（外部共识：Dung 1995 抽象论证框架，归借鉴区）
> 一句话：给一批**论证**和它们之间的**攻击关系**，算出哪些立场**站得住**——
> 三种口径并排给：grounded（唯一最小）· preferred（极大可接受）· stable（把集外都攻击到，
> **可能一个都没有**）。
> 图 1 → `run()` 主流程：校验 → 三种语义并排算 → 汇总
> 图 2 → 可接受性是怎么判的（这是三种语义共同的地基）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"arguments 是非空列表?"}
  V1 -->|否| R1["input_pending<br/>需要 arguments"]
  V1 -->|是| V2{"每个论证都是非空字符串?"}
  V2 -->|否| R2["input_pending"]
  V2 -->|是| V3{"论证名不重复?"}
  V3 -->|否| R3["input_pending"]
  V3 -->|是| V4{"attacks 是列表?"}
  V4 -->|否| R4["input_pending"]
  V4 -->|是| V5{"每个攻击都写成两元组?"}
  V5 -->|否| R5["input_pending"]
  V5 -->|是| V6{"攻击两端都是已声明的论证?"}
  V6 -->|否| R6["input_pending<br/>不认未声明的论证"]
  V6 -->|是| V7{"论证数不超过 max_arguments?"}
  V7 -->|否| R7["size_limit"]
  V7 -->|是| W1["算争议集：两边互攻的成对论证"]
  W1 --> W2["算 grounded：唯一最小可接受集"]
  W2 --> W3["算 preferred：极大可接受集（可能有多个）"]
  W3 --> W4["算 stable：把集外都攻击到的那些"]
  W4 --> W5["举 3 个可接受集例子（枚举子集抽查，留痕给人看）"]
  W5 --> W6{"stable 为空?"}
  W6 -->|是| O1["evaluated<br/>外加诚实说明：这套框架没有稳定扩展"]
  W6 -->|否| O2["evaluated<br/>三种语义 + 争议集 + 可接受例子"]
  O1 --> BND["boundary：三种口径并排给，<br/>不替使用者挑哪个立场对"]
  O2 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4,R5,R6,R7 stop
  class V1,V2,V3,V4,V5,V6,V7 tool
```

## 二、可接受性：三种语义共同的地基

```mermaid
flowchart TD
  A["一个论证集合 S"] --> B{"S 内部无冲突?<br/>（S 里没人攻击 S 里的人）"}
  B -->|否| X["S 不是无冲突集"]
  B -->|是| C["逐个检查 S 里的每个论证 a"]
  C --> D{"攻击 a 的每个论证 b<br/>都被 S 里的某个论证反击?"}
  D -->|否| Y["a 不是可接受的 → S 不满足"]
  D -->|是| E["a 可接受（在 S 的辩护下）"]
  E --> F["S 全部论证都可接受 ⇒ S 是可接受集"]
  F --> G["grounded：最小那个（从空集往上加，加到不动）"]
  F --> H["preferred：极大那些（没有一个可接受集能再装下它）"]
  F --> I["stable：S 把集外每个论证都攻击到<br/>（可能一个都没有——如实报）"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,C core
  class B,D tool
  class E,F,G,H,I out
  class X,Y stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`arguments`（论证名列表）· `attacks`（攻击对 `[a, b]` 表示 a 攻击 b）·
  `max_arguments`（规模上限）。
- **判词**：`evaluated` · `input_pending`（六条拦截：空列表 · 非字符串 · 重名 · attacks 不是列表 ·
  攻击不是两元组 · 端点在声明外）· `size_limit`。
- **输出四项并排**：`grounded` · `preferred` · `stable` · `admissible_examples`（举 3 个例子，
  枚举子集**留痕**给人看）＋ `conflict_pairs`（争议集：两边互攻的那些对）。
- **stable 可能一个都没有**——这是**语义结果**，不是失败；返回时附带说明。
- **诚实边界**：三种口径**并排给**，**不替使用者挑"哪个立场对"**；只诊断不决策。
