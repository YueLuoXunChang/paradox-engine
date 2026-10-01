# 描述逻辑 ALC description_logic — 逻辑流程图

> 模块：`engine/cold/description_logic.py` · 层：第 3 层（外部共识：Baader & Sattler 2000 表列算法，归借鉴区）
> 一句话：判概念**可不可满足**、甲包不包含乙、两个概念**等不等价 / 相不相交**，以及整张本体的
> **概念层级**——表列法展开 + 子集阻塞，循环本体（甲定义成"存在关系指向甲自己"）也能收口。
> 图 1 → `run()` 五种 mode 的主流程
> 图 2 → 表列展开与"撞车 / 阻塞"（这是判定的地基）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：五种 mode，共用一台表列机

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["input_pending"]
  V1 -->|是| V2{"mode 在五种里?"}
  V2 -->|否| R2["input_pending<br/>只认 satisfiable / subsumption / equivalent / disjoint / classify"]
  V2 -->|是| V3{"max_nodes 是不小于 10 的整数?"}
  V3 -->|否| R3["input_pending"]
  V3 -->|是| P0["解析本体公理与概念表达式"]
  P0 --> P1{"解析有语法错?"}
  P1 -->|是| R4["parse_error"]
  P1 -->|否| M1{"mode 是 satisfiable?"}
  M1 -->|是| S1{"concept 是非空文本?"}
  S1 -->|否| R5["input_pending"]
  S1 -->|是| TAB1["表列展开：判这个概念**可不可满足**"]
  M1 -->|否| M2{"mode 是 subsumption 或 disjoint?"}
  M2 -->|是| S2{"sub 与 super 都给了?"}
  S2 -->|否| R6["input_pending"]
  S2 -->|是| TAB2["表列展开：判 甲 交 非乙 可不可满足"]
  TAB2 --> D1{"mode 是 disjoint?"}
  D1 -->|是| D2{"甲乙之交可满足?"}
  D2 -->|是| O1["not_disjoint<br/>给出交的模型"]
  D2 -->|否| O2["disjoint"]
  D1 -->|否| D3{"甲乙之交不可满足?"}
  D3 -->|是| O3["subsumed<br/>甲被乙包住"]
  D3 -->|否| O4["not_subsumed<br/>给出反例模型"]
  M2 -->|否| M3{"mode 是 equivalent?"}
  M3 -->|是| S3{"c1 与 c2 都给了?"}
  S3 -->|否| R7["input_pending"]
  S3 -->|是| E1["两个方向各查一次包含"]
  E1 --> E2{"两个方向都包得住?"}
  E2 -->|是| O5["equivalent"]
  E2 -->|否| O6["not_equivalent<br/>给出其中一个方向的反例模型"]
  M3 -->|否| C1["classify：抽取本体里的原子概念"]
  C1 --> C2{"原子数不超过 MAX_ATOMS_CLASSIFY 8?"}
  C2 -->|否| R8["size_limit"]
  C2 -->|是| C3{"本体里有原子概念吗?"}
  C3 -->|否| R9["input_pending<br/>classify 需要 tbox"]
  C3 -->|是| C4{"每对原子概念逐对判包含<br/>（含去重）"}
  C4 --> O7["classified<br/>原子清单 + 包含层级 + 等价/不相交"]
  O1 --> BND["boundary：只做 ALC 与概念层；<br/>节点超上限报 size_limit 不硬跑"]
  O2 --> BND
  O3 --> BND
  O4 --> BND
  O5 --> BND
  O6 --> BND
  O7 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class C1,C2,C3,C4,D1,D2,D3,E1,E2,M1,M2,M3,P0,P1,S1,S2,S3,V1,V2,V3 tool
```

## 二、表列展开：展开到"处处撞车"就不可满足

```mermaid
flowchart TD
  A["待判概念 → 造根节点，标号放待满足的概念"] --> B{"标号里有 交（且）?"}
  B -->|是| C["拆开：两部分都加进标号"]
  B -->|否| D{"标号里有 并（或）?"}
  D -->|是| E["分支：两支各取一边（**纯递归展开，各支在自己副本上算**）"]
  D -->|否| F{"标号里有 存在关系.丙 ?"}
  F -->|是| G["造一个后继节点，标号加 丙"]
  F -->|否| H{"标号里有 对所有关系.丙 ?"}
  H -->|是| I["把丙发给每个已存在的后继；新后继也要继承"]
  H -->|否| J{"标号里同时出现 甲 与 非甲（或 假）?"}
  I --> K["继续展开"]
  G --> K
  C --> K
  E --> K
  K --> L{"这个节点被**祖先**的标号装下了?"}
  L -->|是| M["子集阻塞：不再为它造后继<br/>（祖先顶上这个节点——循环本体靠这个收口）"]
  L -->|否| N["继续展开后继"]
  J -->|是| O["撞车：这一支关闭"]
  J -->|否| P{"节点数超过 MAX_NODES 400?"}
  P -->|是| Q["size_limit：不硬跑"]
  P -->|否| R["展开结束：所有分支都关闭 ⇒ 不可满足"]
  O --> R
  R --> S["判词：unsatisfiable（**确定结论**）"]
  M --> T["还有未关闭的分支 ⇒ 可满足"]
  N --> T
  T --> U["判词：satisfiable<br/>给规范模型（节点标号 + 回接到祖先的标记）"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,B,C,D,F,H,I,K,L,N,P core
  class E,G tool
  class S,T,U,OUT out
  class J,O,Q stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`satisfiable` / `subsumption` / `equivalent` / `disjoint` / `classify`）·
  `concept` · `sub` / `super` · `c1` / `c2` · `tbox` · `max_nodes`。
- **判词**：`satisfiable` · `unsatisfiable` · `subsumed` · `not_subsumed` · `equivalent` ·
  `not_equivalent` · `disjoint` · `not_disjoint` · `classified` · `input_pending` ·
  `parse_error` · `size_limit` · `internal_error`。
- **关键常量**：`MAX_NODES = 400` · `MAX_ATOMS_CLASSIFY = 8` · `MAX_LABEL_SHOWN = 40`。
- **两种结论的强度不同**（写进边界）：报**不可满足**是**确定结论**（表列全部分支关闭）；
  报**可满足**只给**规范模型**（可复核）。
- **子集阻塞的方向**：某节点的标号被**祖先**装下就不再为它造后继——方向反了就是"假阻塞"，
  这一条是历史真缺陷修出来的。
- **诚实边界**：**只做 ALC**——没有数量限制、没有角色层级 / 逆角色 / 传递角色、没有具体域；
  **只做概念层（TBox），不做 ABox 个体断言**；公理 `R ⊑ S` 在本语言里按**概念**包含读
  （名字长得像角色也当概念，本构件分不清）；节点超上限报 `size_limit` 不硬跑；只诊断不决策。
