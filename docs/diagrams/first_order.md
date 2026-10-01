# 一阶判定 first_order — 逻辑流程图

> 模块：`engine/classical/first_order.py` · 层：第 1 层经典逻辑（带量词的判定，有限论域展开）
> 一句话：给一个**有限论域**，把带量词的公式**展开成不带量词的命题**，
> 交给命题引擎逐赋值判定——推得出就 `entailed`，推不出就 `not_entailed` **并给出反例模型**。
> 图 1 → `run()` 主流程：论域 → 展开 → 判定
> 图 2 → 量词展开的规则与两条拦阻（没论域 / 原子太多）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：论域有了才谈得上判定

```mermaid
flowchart TD
  IN["run(inputs)"] --> Q1{"给了查询吗?"}
  Q1 -->|没给| R1["query_pending"]
  Q1 -->|给了| P1{"事实、规则、查询都解析成功?"}
  P1 -->|否| R2["parse_error"]
  P1 -->|是| U1{"公式里带量词吗?"}
  U1 -->|不带| U2["不需要论域，直接展开"]
  U1 -->|带| U3{"给了论域<br/>或能从常量自动收集?"}
  U3 -->|没有| R3["no_universe<br/>有量词却没有论域，判不了"]
  U3 -->|有| U2
  U2 --> G1["按论域展开量词<br/>得到不带量词的公式"]
  G1 --> G2{"展开出的原子数超过 64?"}
  G2 -->|超过| R4["size_limit<br/>展开会爆，如实拦下"]
  G2 -->|不超过| G3["把展开结果转成命题逻辑写法"]
  G3 --> G4["逐赋值检查：前提全真时查询是否也真"]
  G4 --> E1{"所有赋值下都真?"}
  E1 -->|是| O1["entailed"]
  E1 -->|否| O2["not_entailed<br/>附反例模型"]
  O1 --> BND
  O2 --> BND
  R4 --> BND
  BND["boundary：有限论域下才有判定——<br/>展开有上限，超了不硬算"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R1,R2,R3,R4 stop
  class BND,O1,O2 out
  class E1,G1,G3,G4,P1,Q1,U1,U2,U3 tool
  class G2 stop
```

## 二、量词怎么展开：全称展成合取，存在展成析取

```mermaid
flowchart TD
  A["带量词的公式 + 有限论域"] --> B0{"是原子公式?"}
  B0 -->|是| B1["展开结果就是它本身"]
  B0 -->|否| B2{"最外层是哪个量词?"}
  B2 -->|全称| B3["对论域里每个对象替换一次<br/>结果用合取连起来"]
  B2 -->|存在| B4["对论域里每个对象替换一次<br/>结果用析取连起来"]
  B2 -->|否定| B5["否定照搬<br/>里面继续展开"]
  B2 -->|合取或析取或蕴含| B6["两边各自展开<br/>再按原联结词拼回去"]
  B3 --> C1["论域里每个对象都覆盖到<br/>所以展开是有限且确定的"]
  B4 --> C1
  B5 --> C1
  B6 --> C1
  C1 --> C2{"论域里没有对象?"}
  C2 -->|是| C3["全称展开成真<br/>存在展开成假<br/>（空论域的老实话）"]
  C2 -->|否| C4["得到不带量词的公式"]
  C3 --> C4
  C4 --> C5["收集展开后的所有原子并编号"]
  C5 --> C6["交给命题引擎逐赋值判定"]
  C6 --> BND["boundary：判定只在有限论域下成立——<br/>无界论域不适用，本件不硬套"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A core
  class B0,B1,B2,B3,B4,B5,B6,C1,C4,C5,C6 tool
  class C3 out
  class BND stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`universe`（论域对象，可省——从事实常量自动收集）·
  `facts`（事实）· `rules`（规则）· `query`（要判的查询）。
- **判词**：`entailed` · `not_entailed` · `no_universe` · `size_limit` · `query_pending` ·
  `parse_error`。
- **判定的地基是"有限论域"**：量词按论域逐个对象展开（全称→合取、存在→析取），
  展开完就是命题问题，所以判定是**确定且可复核**的；**论域不有限就不适用**。
- **有量词却没有论域 → `no_universe`**：这时不猜、不默认一个论域，直接拦下——
  猜一个论域会凭空造出结论。
- **展开上限 `_MAX_GROUND_ATOMS = 64`**：原子太多就报 `size_limit`，
  **返回里带上实际原子数**，让人知道离上限有多远。
- **反例是模型**：`not_entailed` 会给一份**反例模型**（哪些原子取真、哪些取假），
  可以直接拿去复核，不用重跑。
- **空论域照实处理**：论域里一个对象都没有时，全称展开为真、存在展开为假
  （这是标准的老实话），代码里单独处理。
- **诚实边界**（`boundary` 字段随每个返回点带回）：本件是**有限域展开型**判定——
  无界量词不在适用范围；解析失败与超限都如实报；**只判蕴含关系，
  不判前提本身对不对，也不做取舍决策**。
