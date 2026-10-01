# 模态 μ 演算 mu_calculus — 逻辑流程图

> 模块：`engine/cold/mu_calculus.py` · 层：第 3 层（外部共识：Kozen 1983 · Knaster-Tarski · Emerson-Jutla，归借鉴区）
> 一句话：给一个**有限迁移系统**和一个**μ 演算公式**，算出公式在**哪些状态上成立**——
> μ 从空集往上加、ν 从全集往下砍，**每一步留痕**；CTL 的八个路径量子能翻成 μ 式子复核。
> 图 1 → `run()` 四种 mode 的主流程
> 图 2 → 求值内核：两个不动点怎么迭代（外加"负出现"怎么被拦下）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：四种 mode 共用一个求值内核

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["input_pending"]
  V1 -->|是| V2{"mode 在 evaluate / check / ctl / compare 里?"}
  V2 -->|否| R2["input_pending<br/>mode 只认这四个"]
  V2 -->|是| S1["读结构：states / transitions / labels"]
  S1 --> S2{"状态数不超过 MAX_STATES 200?"}
  S2 -->|否| R3["size_limit<br/>超上限不硬跑"]
  S2 -->|是| M1{"mode 是 ctl?"}
  M1 -->|是| C1{"ctl 公式非空?"}
  C1 -->|否| R4["input_pending"]
  C1 -->|是| C2["借 model_check 的解析器把 CTL 翻成 μ 式子"]
  C2 --> C3{"解析器拿得到吗?"}
  C3 -->|否| R5["internal_error"]
  C3 -->|是| EVAL
  M1 -->|否| M2{"mode 是 compare?"}
  M2 -->|是| P1{"c1 与 c2 都给了?"}
  P1 -->|否| R6["input_pending<br/>compare 需要两条公式"]
  P1 -->|是| P2["两条式子各自求值 → 比成立状态集"]
  P2 --> CMP{"两侧成立集相同?"}
  CMP -->|是| O1["same"]
  CMP -->|否| O2["different"]
  M2 -->|否| P3{"公式文本非空?"}
  P3 -->|否| R7["input_pending"]
  P3 -->|是| P4["解析成语法树"]
  P4 --> P5{"语法树里变量都是正出现?"}
  P5 -->|否| R8["non_monotone<br/>负出现没有不动点语义，摆出振荡过程"]
  P5 -->|是| P6["绑定检查：不遮蔽 · 不重绑 · 变量在自己作用域里出现过"]
  P6 --> P7{"绑定检查过?"}
  P7 -->|否| R9["parse_error"]
  P7 -->|是| EVAL["逐状态求值（含不动点迭代）"]
  EVAL --> W1{"这次判定的总工作量超 MAX_WORK 400000?"}
  W1 -->|是| R10["size_limit<br/>卡的是整次判定的工作量，不只是分支数"]
  W1 -->|否| M3{"mode 是 check?"}
  M3 -->|是| K1{"init 是已声明状态的子集?"}
  K1 -->|否| R11["input_pending"]
  K1 -->|是| K2{"init 里有状态不成立?"}
  K2 -->|否| O3["holds<br/>fails_in 为空"]
  K2 -->|是| O4["fails<br/>给出不成立的那些状态"]
  M3 -->|否| O5["evaluated<br/>holds_in 列出成立的状态"]
  O1 --> BND["boundary：只做给定结构上的求值/检查，<br/>不做可满足性判定"]
  O2 --> BND
  O3 --> BND
  O4 --> BND
  O5 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R10,R11,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class C1,C2,C3,K1,K2,M1,M2,M3,P1,P2,P3,P4,P5,P6,P7,S1,S2,V1,V2 tool
```

## 二、求值内核：两个不动点 + 一根"负出现"的红线

```mermaid
flowchart TD
  F["公式节点"] --> A1{"是原子命题?"}
  A1 -->|是| T1["查该状态标号里有没有这个命题"]
  A1 -->|否| A2{"是并 / 交 / 差 / 蕴含?"}
  A2 -->|是| T2["按集合运算：并交差照常，蕴含按补并"]
  A2 -->|否| A3{"是模态?"}
  A3 -->|是| T3["小于号模态：起码有一个后继落在里面<br/>方括号模态：每个后继都落在里面<br/>带动作名的只看该动作的后继"]
  A3 -->|否| A4{"是不动点?"}
  A4 -->|μ 最小| T4["从**空集**出发反复代入，集合只增不减，加到不动就停"]
  A4 -->|ν 最大| T5["从**全集**出发往下砍，砍到不动就停"]
  T4 --> L1["留痕：迭代几步、每步多大<br/>（上限 MAX_FIXPOINTS_TRACE 40）"]
  T5 --> L1
  L1 --> L2{"迭代中出现来回跳（不收敛）?"}
  L2 -->|是| R1["non_monotone<br/>展示前 MAX_OSC_SHOWN 6 步的振荡"]
  L2 -->|否| OK["给出该状态是否成立"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class F,A1,A2,A3,A4 tool
  class T1,T2,T3,T4,T5,L1,L2 core
  class OK out
  class R1 stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode` · `formula` · `ctl` · `c1` / `c2`（compare 用）· `states` ·
  `transitions` · `labels`（每个状态上的原子命题）· `init`（check 用）。
- **判词**：`evaluated` · `holds` · `fails` · `same` · `different` · `non_monotone` ·
  `input_pending` · `parse_error` · `size_limit` · `internal_error`。
- **关键常量**：`MAX_STATES = 200` · **`MAX_WORK = 400000`**（整次判定的工作量上限——光卡分支数不够，
  式子照样能卡死）· `MAX_FIXPOINTS_TRACE = 40` · `MAX_OSC_SHOWN = 6`。
- **留痕**：`fixpoints` 记每轮迭代的集合大小——"只迭代一轮就停""从全集出发"这类错一眼看得出。
- **CTL 复核**：`mode=ctl` 先翻译再求值，`translation` 字段带出翻出来的 μ 式子。
- **诚实边界**：**只做给定结构上的求值与检查**（model checking）——不是逻辑普遍有效，
  **更不做"公式有没有模型"的可满足性判定**；不动点变量必须**正出现**（负出现没有不动点语义，
  会拦下并摆出振荡过程）；状态数/工作量有上限，超了报 `size_limit` 不硬跑；
  交替更深的性质 CTL 写不出来（Emerson-Jutla），本构件**不证这件事、只标来源**。
