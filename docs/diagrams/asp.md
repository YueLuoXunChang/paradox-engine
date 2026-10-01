# 答案集程序 ASP — 逻辑流程图

> 模块：`engine/cold/asp.py` · 层：第 3 层（外部共识：Gelfond-Lifschitz 1988 稳定模型语义，归借鉴区）
> 一句话：算「规则 + 否定即失败 + 约束」这套写法下的**自洽结论集合**（答案集，可能一个、多个、
> 或**一个都没有**），并给每个原子的**推导依据**；还能按怀疑论 / 轻信论两种口径回答"某原子在不在"。
> 图 1 → `run()` 两种 mode 的主流程
> 图 2 → 答案集是怎么算出来的（reduct + 极小性）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["input_pending"]
  V1 -->|是| V2{"mode 在 solve / query 里?"}
  V2 -->|否| R2["input_pending<br/>mode 只认 solve / query"]
  V2 -->|是| V3{"program 是非空文本?"}
  V3 -->|否| R3["input_pending<br/>需要 program"]
  V3 -->|是| P1["解析：规则头 / 体 / 否定即失败 / 约束"]
  P1 --> P2{"原子数不超过 MAX_ATOMS 16<br/>且规则数不超过 MAX_RULES 400?"}
  P2 -->|否| R4["size_limit<br/>超上限不硬跑"]
  P2 -->|是| P3{"解析有语法错?"}
  P3 -->|是| R5["parse_error"]
  P3 -->|否| P4{"程序里一个原子都没有?"}
  P4 -->|是| R6["input_pending<br/>诚实拦截"]
  P4 -->|否| P5{"既没规则也没约束?"}
  P5 -->|是| R7["input_pending<br/>诚实拦截"]
  P5 -->|否| SOLVE["算全部答案集（reduct + 极小性）"]
  SOLVE --> S1{"答案集个数超过 MAX_LISTED 64?"}
  S1 -->|是| S2["列表截断，但计数照实给"]
  S1 -->|否| S3["全列出"]
  S2 --> M1{"mode 是 query?"}
  S3 --> M1
  M1 -->|否| Q1{"一个答案集都没有?"}
  Q1 -->|是| O1["no_answer_set<br/>规则自相矛盾（是语义结果，不是失败）"]
  Q1 -->|否| O2["solved<br/>答案集 + 计数 + 每个原子的推导依据"]
  M1 -->|是| Q2{"query 给了且非空?"}
  Q2 -->|否| R8["input_pending<br/>query 模式需要 query"]
  Q2 -->|是| Q3{"query 这个原子在程序里出现过?"}
  Q3 -->|否| R9["input_pending<br/>诚实拦截，不隐式补一个原子"]
  Q3 -->|是| Q4{"压根没有答案集?"}
  Q4 -->|是| O3["in_none<br/>谈不上它在不在"]
  Q4 -->|否| Q5{"每个答案集里都有它?"}
  Q5 -->|是| O4["in_all<br/>怀疑论口径：可以下这个结论"]
  Q5 -->|否| Q6{"部分答案集里有它?"}
  Q6 -->|是| O5["in_some<br/>轻信论口径：能撑住，但另一套同样自洽"]
  Q6 -->|否| O6["in_none<br/>每个答案集里都没有它"]
  O2 --> BND["boundary：结论是相对这套规则的，<br/>不替使用者挑哪个答案集更对"]
  O1 --> BND
  O3 --> BND
  O4 --> BND
  O5 --> BND
  O6 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class M1,P1,P2,P3,P4,P5,Q1,Q2,Q3,Q4,Q5,Q6,S1,S2,S3,V1,V2,V3 tool
```

## 二、答案集怎么算：先化简（reduct），再验极小性

```mermaid
flowchart TD
  A["规则集合 + 候选集合 X"] --> B["把带 not 的体按 X 化简：<br/>not a 在 X 里成立就把这条规则整个丢掉"]
  B --> C["化简后的程序只含正规则"]
  C --> D["从规则头出发反复推，直到推不出新的原子<br/>（得到最小模型）"]
  D --> E{"推出来的集合 恰好等于 X?"}
  E -->|是| F["X 是一个答案集（稳定模型）"]
  E -->|否| G["X 不是答案集"]
  F --> H["约束检查：约束体成立就不许<br/>（约束只筛候选、不产生结论）"]
  H --> I{"约束被违反?"}
  I -->|是| J["这个 X 作废"]
  I -->|否| K["收进答案集列表"]
  K --> L["给每个原子记推导依据：<br/>靠哪条规则、体上每个条件怎么满足"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,B,C,D core
  class E,H,I tool
  class F,K,L out
  class G,J stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`solve` / `query`）· `program`（规则文本）· `query`（要问的原子名）。
- **判词**：`solved` · `no_answer_set` · `in_all` · `in_some` · `in_none` · `input_pending` ·
  `parse_error` · `size_limit` · `internal_error`。
- **关键常量**：`MAX_ATOMS = 16` · `MAX_RULES = 400` · `MAX_LISTED = 64`（列表截断但**计数照实给**）。
- **两种口径写清**：`in_all` = 怀疑论（每个答案集里都有）；`in_some` = 轻信论（只在部分里有，
  且会报"几个里几个"）；`in_none` 分两种来路——**根本没有答案集**（谈不上在不在）与
  **每个答案集里都没有**。
- **推导依据**：每个原子记"靠哪条规则撑住"——结论不是"我说有就有"，是可逐条复核的。
- **诚实边界**：**只做正规则程序**——不做选择规则、基数约束、聚合、优化，也不做带变量规则的
  grounding（本构件是命题层面）；答案集**可能一个、多个或一个都没有**（没有就是规则自相矛盾），
  一律照实报；结论是**相对这套规则**的，**不替使用者挑"哪个答案集更对"**；只诊断不决策。
