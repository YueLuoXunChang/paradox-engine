# 直觉主义逻辑 intuitionistic_logic — 逻辑流程图

> 模块：`engine/cold/intuitionistic_logic.py` · 层：第 3 层（外部共识：Brouwer / Heyting / Kripke 1959，归借鉴区）
> 一句话：**构造性立场**上的推理——在 Kripke 模型里求值、给反模型（"为什么排中律不是构造有效的"），
> 并把六个经典地标在**经典 vs 直觉主义**两边并排对照。
> 图 1 → `run()` 三种 mode 的主流程
> 图 2 → Kripke 求值规则与反模型搜索（含模型合法性检查）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> M1{"mode 是 evaluate?"}
  M1 -->|是| E0["_evaluate(formula, worlds, order, valuation, world)"]
  M1 -->|否| M2{"mode 是 countermodel?"}
  M2 -->|是| C0["_countermodel(formula, max_worlds)"]
  M2 -->|否| M3{"mode 是 compare?"}
  M3 -->|是| P0["拿地标表逐条比：经典判法 vs 直觉主义判法"]
  P0 --> O1["compared<br/>六个地标两边并排"]
  M3 -->|否| R1["input_pending<br/>mode 只认 evaluate / countermodel / compare"]

  E0 --> E1{"formula 与 worlds 都给了?"}
  E1 -->|否| R2["input_pending"]
  E1 -->|是| E2{"formula 解析得了?"}
  E2 -->|否| R3["parse_pending"]
  E2 -->|是| E3{"world 没指定就取第一个世界"}
  E3 --> E4{"world 在 worlds 里?"}
  E4 -->|否| R4["input_pending"]
  E4 -->|是| E5["检查模型合法性：<br/>自反 · 反对称 · 传递 · 赋值单调"]
  E5 --> E6{"模型合法?"}
  E6 -->|否| R5["model_invalid<br/>指出哪条不满足（含反例原子与世界）"]
  E6 -->|是| E7["按 Kripke 规则求值"]
  E7 --> O2["evaluated<br/>value = 真 / 假"]

  C0 --> C1{"formula 非空?"}
  C1 -->|否| R6["input_pending"]
  C1 -->|是| C2{"解析得了?"}
  C2 -->|否| R7["parse_pending"]
  C2 -->|是| C3["在 max_worlds 界内**穷举**可能的世界结构"]
  C3 --> C4{"界内找到反模型了吗?"}
  C4 -->|是| O3["refuted<br/>给出反模型（可复核）"]
  C4 -->|否| O4["not_found_in_limit<br/>界内没找到 ≠ 这条式子构造有效"]
  O1 --> BND["boundary：完备界内没找到反模型才判有效；<br/>只诊断不决策"]
  O2 --> BND
  O3 --> BND
  O4 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4,R5,R6,R7 stop
  class C0,C1,C2,C3,C4,E0,E1,E2,E3,E4,E5,E6,E7,M1,M2,M3,P0 tool
```

## 二、Kripke 求值规则与"模型必须合法"

```mermaid
flowchart TD
  A["节点：世界 w + 可达关系 + 各世界的原子赋值"] --> B{"公式是原子?"}
  B -->|是| C["看该世界赋值里有没有它"]
  B -->|否| D{"是 非 ?"}
  D -->|是| E["在**所有 w 可达的世界**里该子式都不成立"]
  D -->|否| F{"是 且 / 或 ?"}
  F -->|是| G["且：两边都成立<br/>或：至少一边成立"]
  F -->|否| H["蕴含：对每个 w 可达的世界 v，<br/>只要前件在 v 成立，后件在 v 也要成立"]
  C --> OK["给出该世界的真值"]
  E --> OK
  G --> OK
  H --> OK
  OK --> M1["模型合法性检查（四条）"]
  M1 --> M2{"可达关系自反?"}
  M2 -->|否| X1["model_invalid"]
  M2 -->|是| M3{"反对称且传递?"}
  M3 -->|否| X1
  M3 -->|是| M4{"赋值单调：<br/>在 w 成立的原子，在 w 可达的世界里也成立?"}
  M4 -->|否| X2["model_invalid<br/>给出违约的原子与两个世界"]
  M4 -->|是| M5["模型合法 → 求值结论可用"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,B,D,F core
  class C,E,G,H,M1,M2,M3,M4 tool
  class OK,M5 out
  class X1,X2 stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`evaluate` / `countermodel` / `compare`）· `formula` ·
  `worlds` · `order`（可达关系）· `valuation`（各世界的原子赋值）· `world` · `formulas` · `max_worlds`。
- **判词**：`evaluated` · `refuted` · `valid` · `compared` · `model_invalid` ·
  `not_found_in_limit` · `parse_pending` · `input_pending` · `size_limit`。
- **求值规则**（照着代码核的）：原子查赋值；`¬` 要在**所有可达世界**上子式不成立；
  `∧` / `∨` 照常；`→` 要看**每个可达世界**——只要前件成立，后件也得成立
  （这就是"构造性"的来源：真值不是"当前世界的一个标记"，而是**沿可达结构往后传**）。
- **模型合法性四条**：可达关系**自反 · 反对称 · 传递**，且赋值**单调**（在 w 成立的原子，
  在 w 可达的世界里也成立）——不满足就报 `model_invalid` 并指出违约处。
- **反模型搜索是**"**完备界内的穷举**"：界内找到 → `refuted`（反模型可复核）；
  界内没找到 → `not_found_in_limit`——**没找到 ≠ 构造有效**，这条不越界宣称。
- **地标对照表**（compare）：排中律 `P∨¬P` · 双重否定消去 `¬¬P→P` · Peirce 律
  `((P→Q)→P)→P` · 两条 De Morgan · 爆炸 `P→(Q→P)`——每条给出经典判法与直觉主义判法。
- **诚实边界**：只做**构造性立场上的求值与反模型搜索**；界内无解才判有效；
  经典与直觉主义**两边并排给**，不替使用者挑立场；只诊断不决策。
