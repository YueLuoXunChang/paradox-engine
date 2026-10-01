# 悖论注解 paradox_annotate — 逻辑流程图

> 模块：`engine/mechanisms/paradox_annotate.py` · 层：第 2 层机制
> 一句话：给一条矛盾生成**8 字段注解卡**（ID/LV/POS/SRC/CT/EF/ST/AN）并按来源与影响
> 分出 **P-A / P-B / P-C** 三级——矛盾拿一张"身份证"。
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：三条拦截 → 定级 → 出卡

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"paradox 是非空 dict?"}
  V1 -->|否| R1["input_pending<br/>annotation=None · grade=None<br/>（不硬造注解卡）"]
  V1 -->|是| V2{"source ∈ {axiom, runtime, observer}?"}
  V2 -->|否| R2["input_pending<br/>来源不合法"]
  V2 -->|是| V3{"impact 是字符串?"}
  V3 -->|否| R3["input_pending<br/>影响字段类型不对"]
  V3 -->|是| G1["grade(source, impact, eliminable)"]
  G1 --> A1["annotate(paradox, source, impact, eliminable, seq)"]
  A1 --> A2{"seq 给了吗?"}
  A2 -->|否| A3["用模块计数器自增（_seq_counter += 1）"]
  A2 -->|是| A4["用调用方给的序号"]
  A3 --> CARD["拼 8 字段卡"]
  A4 --> CARD
  CARD --> OUT["annotated<br/>annotation=卡片 · grade=卡片['LV']"]
  OUT --> BND["boundary：非法输入拦下并说明，不硬造卡；<br/>分级只是分级、不是判决"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3 stop
  class OUT out
  class V1,V2,V3 tool
```

## 二、分级规则（`grade`）：基础级 → 两次升级

```mermaid
flowchart TD
  S["source"] --> B["基础级<br/>axiom → P-A<br/>runtime → P-B<br/>observer → P-C"]
  B --> Q1{"impact = global ?"}
  Q1 -->|是| U1["升级一级"]
  Q1 -->|否| Q2
  U1 --> Q2{"eliminable = False ?"}
  Q2 -->|是| U2["再升级一级"]
  Q2 -->|否| FIN
  U2 --> FIN["最终级 LV ∈ {P-A, P-B, P-C}"]
  FIN --> NOTE["_upgrade 规则：P-A 到顶不再升；<br/>P-B→P-A · P-C→P-B（用 _LEVEL_ORDER 查表）"]
  FIN --> ID["ID = 悖论_{LV}_{序号:03d}"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class Q1,Q2 tool
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`paradox`（`{A, notA, pos, src, effect, note}`，可含 `coexist`）·
  `source`（`axiom` / `runtime` / `observer`）· `impact`（`local` / `global`）·
  `eliminable`（bool）· `seq`（序号，缺省自增）。
- **判词**：`annotated` · `input_pending`（三条拦截：paradox 非 dict/空 · source 不合法 ·
  impact 类型不对）。
- **卡片 8 字段**：`ID`（`悖论_P-?_NNN`）· `LV`（分级）· `POS`（位置：系统+层级+点位）·
  `SRC`（来源/触发链）· `CT`（内容：`A=…, ¬A=…, 共存形式=…`）· `EF`（影响的下游系统）·
  `ST`（状态，默认"活跃"）· `AN`（注解自由文本）。
- **关键表**：`_SOURCE_TO_BASE = {axiom→P-A, runtime→P-B, observer→P-C}` ·
  `_LEVEL_ORDER = {P-A:0, P-B:1, P-C:2}`。
- **留痕**：卡片 `ID` 里带分级与序号——同一批材料的卡能按序号对齐复核。
- **诚实边界**（`boundary`）：非法输入拦下并说明，**不硬造注解卡**；分级只是分级、
  **不是判决**；只诊断不决策。
