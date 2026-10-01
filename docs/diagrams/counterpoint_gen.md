# 对位创生 counterpoint_gen — 逻辑流程图

> 模块：`engine/mechanisms/counterpoint_gen.py` · 层：第 2 层机制
> 一句话：把对立两侧交给"对位"——判它们怎么耦合（同向 / 反向 / 交叉），据此给出**第三态候选**
> 与**依据**（不是二选一，也不是和稀泥）。
> 图 1 → run() 主流程（校验 + 耦合判定 + 出第三态）
> 图 2 → 三种耦合各自怎么造第三态
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"thesis 与 antithesis 都给了?"}
  V1 -->|否| R1["input_pending<br/>两侧都要给"]
  V1 -->|是| C1{"调用方指定了 coupling 吗?"}
  C1 -->|否| C2["自动探耦合：<br/>扫否定词对，看是否两侧各占一个"]
  C1 -->|是| C3{"coupling 在 same / reverse / cross 里?"}
  C3 -->|否| R2["input_pending<br/>耦合类型不合法"]
  C2 --> C4{"扫到否定词对（一正一反）?"}
  C4 -->|是| C5["reverse<br/>反向耦合"]
  C4 -->|否| C6["cross<br/>交叉耦合"]
  C3 -->|是| B1
  C5 --> B1["按耦合类型造第三态：<br/>拼标签 + 列依据"]
  C6 --> B1
  B1 --> D1["第三态 = 标签 + 依据列表 + 维度"]
  D1 --> OUT["third_state<br/>coupling + third_state + derivation"]
  OUT --> BND["boundary：给候选与依据，采不采由人评估"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2 stop
  class OUT out
  class B1,C1,C2,C3,C4,C5,C6,D1,V1 tool
```

## 二、三种耦合各自怎么造第三态

```mermaid
flowchart TD
  C{"coupling"} -->|same 同向| S1["两侧朝同一个方向"]
  S1 --> S2["第三态：同向叠加后的新维度<br/>依据：两侧共享的方向"]
  C -->|reverse 反向| T1["两侧互为否定（一正一反）"]
  T1 --> T2["第三态：把对立本身当一层<br/>依据：否定词对 + 共存条件"]
  C -->|cross 交叉| U1["两侧各有对方没有的成分"]
  U1 --> U2["第三态：交叉后的合成维度<br/>依据：各自独有的成分对"]
  S2 --> OUT["第三态候选（供人评估）"]
  T2 --> OUT
  U2 --> OUT
  OUT --> NOTE["对齐关系代数里的三类关系：<br/>同向 / 反向 / 交叉"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class C tool
  class S1,T1,U1 core
  class S2,T2,U2,OUT,NOTE out
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`thesis` · `antithesis` · `coupling`（可省，省了就自动探）·
  `dimensions`（维度线索）。
- **判词**：`third_state` · `input_pending`（两条拦截：缺一侧 · 耦合类型不合法）。
- **耦合类型表**：`_VALID_COUPLING = {same, reverse, cross}`——**只认这三种**，不合法就拦。
- **自动探耦合**：扫内置的否定词对，若两侧各占一个 → `reverse`；否则 `cross`
  （**探不出来时不硬猜成同向**，落交叉）。
- **输出结构**：`third_state`（标签 + 依据 + 维度）· `derivation`（推导链，供人复核）·
  `coupling`（实际用的耦合类型，便于追溯）。
- **诚实边界**：出的是**候选 + 依据**，**不替使用者拍板**——"第三个态"要不要用，由人评估；
  与"二选一"和"折中"都不同：它要求给出**为什么这算第三态**。
