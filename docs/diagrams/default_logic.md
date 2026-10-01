# 默认逻辑 default_logic — 逻辑流程图

> 模块：`engine/cold/default_logic.py` · 层：第 3 层（外部共识：Reiter 1980 原义，归借鉴区）
> 一句话：算出默认理论 (W, D) 的**全部扩展**（Γ 算子的不动点），分清
> "**每个扩展都成立**"与"**只在部分扩展成立**"——一个理论可能**没有**扩展，也可能有好几个。
> 图 1 → `run()` 主流程：解析 → 规模闸 → 枚举候选 → 逐个验不动点
> 图 2 → 一条默认什么时候生效 ＋ 不动点怎么验
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["input_pending"]
  V1 -->|是| V2{"facts 是列表（可为空）?"}
  V2 -->|否| R2["input_pending"]
  V2 -->|是| V3{"defaults 是非空列表?"}
  V3 -->|否| R3["input_pending<br/>四种默认写法都认，但要给"]
  V3 -->|是| V4{"max_defaults 是正整数?"}
  V4 -->|否| R4["input_pending"]
  V4 -->|是| V5{"默认条数不超过 max_defaults?"}
  V5 -->|否| R5["size_limit<br/>2 的 n 次方枚举会炸，超了不硬跑"]
  V5 -->|是| P1["解析事实与默认，归一化成（前提, 辩护, 结论）"]
  P1 --> P2{"解析有语法错?"}
  P2 -->|是| R6["parse_error"]
  P2 -->|否| N1{"原子数不超过 MAX_ATOMS 10?"}
  N1 -->|否| R7["undecided<br/>算不动 —— 不等于没有扩展"]
  N1 -->|是| N2{"事实集合自身可满足?"}
  N2 -->|否| R8["facts_unsatisfiable<br/>底板就矛盾了"]
  N2 -->|是| E1["枚举候选：默认结论的任意子集<br/>（2 的 n 次方个，**完整**不漏）"]
  E1 --> E2{"候选 T 的闭包 等于 T 自己?"}
  E2 -->|否| E3["不是扩展，跳过"]
  E2 -->|是| E4{"这个闭包已经收过?"}
  E4 -->|是| E5["去重"]
  E4 -->|否| E6["收进 extensions"]
  E3 --> E7{"还有候选没试?"}
  E5 --> E7
  E6 --> E7
  E7 -->|是| E2
  E7 -->|否| F1{"一个扩展都没有?"}
  F1 -->|是| O1["no_extension<br/>语义结果，不是失败"]
  F1 -->|否| F2["把原子分三类装桶"]
  F2 --> F3["每个扩展都成立的 → in_all"]
  F2 --> F4["只在部分扩展成立的 → in_some"]
  F2 --> F5["每个扩展都不成立的 → in_none"]
  F3 --> Q1{"query 给了?"}
  F4 --> Q1
  F5 --> Q1
  Q1 -->|是| O2["evaluated + query_status<br/>该原子在哪一桶"]
  Q1 -->|否| O3["evaluated<br/>三分桶 + 每条默认的状态 + 歧义默认"]
  O1 --> BND["boundary：只做有限命题情形；<br/>规则本身合不合理由使用者判断"]
  O2 --> BND
  O3 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4,R5,R6,R7,R8 stop
  class E1,E2,E3,E4,E5,E6,E7,F1,F2,F3,F4,F5,N1,N2,P1,P2,Q1,V1,V2,V3,V4,V5 tool
```

## 二、一条默认什么时候生效 ＋ "不动点才算扩展"

```mermaid
flowchart TD
  A["一条默认：前提 α ／ 辩护 β ／ 结论 γ"] --> B{"α 在 T 的推论里推得出?"}
  B -->|否| X1["不适用（前提不满足）"]
  B -->|是| C{"β 与 T 冲突?"}
  C -->|是| X2["被阻断（辩护被推翻）"]
  C -->|否| D["生效：γ 加进 T"]
  D --> E["反复施加所有生效的默认 + 前提事实<br/>直到推不出新的东西"]
  E --> F{"推出来的集合 恰好等于 T?"}
  F -->|是| G["T 是 Γ 的不动点 ⇒ 一个扩展"]
  F -->|否| H["T 不是不动点，跳过"]
  G --> I["同时记下：哪些默认在它里面生效了"]
  I --> J["跨扩展对比 → 歧义默认（有的扩展里生效、有的里不生效）"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,D,E core
  class B,C,F tool
  class G,I,J out
  class X1,X2,H stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`facts`（命题式列表，可空）· `defaults`（默认规则，**四种写法都认**）·
  `query`（要问的原子）· `max_defaults`（默认条数上限）。
- **判词**：`evaluated` · `no_extension` · `facts_unsatisfiable` · `undecided` · `input_pending` ·
  `parse_error` · `size_limit`。
- **关键常量**：`MAX_ATOMS = 10` · `MAX_DEFAULTS = 12`（**2 的 n 次方枚举**的闸）。
- **输出分桶**：`extensions` · `in_all`（每个扩展都成立）· `in_some`（只在部分成立）·
  `in_none` · `default_status`（每条默认的状态）· `ambiguous_defaults`（**歧义默认**：
  有的扩展里生效、有的里不生效的那几条）· `query_status`。
- **两处"算不动"分得很清**：原子超上限 → `undecided`（**算不动 ≠ 没有扩展**）；
  默认条数超上限 → `size_limit`；而 `no_extension` 是**语义结果**（这个理论本来就没有扩展）。
- **诚实边界**：只做**有限命题**情形；扩展在默认条数的 2^n 个子集上**枚举候选再逐个验不动点**——
  **完整**（不漏扩展）；"有例外就阻断"是 `agm_revision` 的简化版，**不是本构件**；
  只诊断不决策——规则本身合不合理由使用者判断。
