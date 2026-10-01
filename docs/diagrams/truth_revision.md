# 真值修正 truth_revision — 逻辑流程图

> 模块：`engine/cold/truth_revision.py` · 层：第 3 层冷门逻辑（自指与修正序列）
> 一句话：给一组**互相引用的句子**，按"每句重新算真值"迭代下去——
> 看它是**收敛到定点**、**进入周期振荡**，还是**窗口内既不收敛也不周期**。
> 图 1 → `run()` 两个模式：内置三个演示系统 / 自定方程组
> 图 2 → 迭代观察怎么分出三态（定点 / 周期 / 不稳定）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：两组演示 + 自定方程组

```mermaid
flowchart TD
  IN["run(inputs)"] --> M{"mode 是哪个?"}
  M -->|demo| D1["跑三个演示系统：<br/>说谎者型 · 互指环 · 良性句"]
  M -->|custom| C1{"sentences 是字典且有内容?"}
  C1 -->|否| R1["input_pending<br/>没给方程组不硬跑"]
  C1 -->|是| C2{"每句都是可调用的真值条件?"}
  C2 -->|否| R2["input_pending<br/>如实拦下，不猜"]
  C2 -->|是| C3["逐轮全量更新赋值向量"]
  M -->|其他| R3["input_pending"]
  D1 --> D2["每个系统各自给判词与说明"]
  C3 --> O1{"观察结果?"}
  O1 -->|赋值重复 且 周期为 1| S1["stable<br/>收敛到稳定赋值"]
  O1 -->|赋值重复 且 周期大于 1| S2["periodic<br/>进入长度 p 的循环"]
  O1 -->|窗口内既不重复也不稳定| S3["unstable<br/>看不出稳定值或周期"]
  D2 --> OUT1["demo：三个系统并置对照"]
  S1 --> OUT2["custom：判词 + 轨迹"]
  S2 --> OUT2
  S3 --> OUT2
  OUT1 --> BND
  OUT2 --> BND
  BND["boundary：只报修正序列的形态——<br/>稳定 / 周期 / 不稳定，不替使用者定句子的地位"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R1,R2,R3 stop
  class BND,OUT1,OUT2 out
  class C1,C2,C3,D1,D2,M,O1 tool
  class S1,S2,S3 out
```

## 二、迭代观察：三态是怎么分出来的

```mermaid
flowchart TD
  A["初始赋值 + 每句的真值条件"] --> L1["记下本轮赋值"]
  L1 --> L2{"这个赋值以前出现过吗?"}
  L2 -->|出现过| P1["算周期 = 本轮步数 减 上次出现的步数"]
  P1 --> P2{"周期等于 1?"}
  P2 -->|是| T1["stable：一步到定点<br/>良性，可给结果"]
  P2 -->|否| T2["periodic：长度 p 的循环<br/>周期 2 就是每步翻转的说谎者型"]
  L2 -->|没出现过| U1["按每句的真值条件重算<br/>全量更新下一轮赋值"]
  U1 --> U2{"还有观察步数吗?"}
  U2 -->|有| L1
  U2 -->|没有| U3{"最近三步赋值相同?"}
  U3 -->|是| T3["stable：序列稳住了"]
  U3 -->|否| T4["unstable：窗口内无稳定也无周期<br/>可能要更长观察"]
  T1 --> N1["每个判词配一句人话说明"]
  T2 --> N1
  T3 --> N1
  T4 --> N1
  N1 --> BND["boundary：形态由修正序列本身给出，<br/>不是引擎自创的结论"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A core
  class L1,L2,P1,P2,U1,U2,U3,N1 tool
  class T1,T2,T3 out
  class T4,BND stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`demo` / `custom`）· `sentences`（每句一个可调用的真值条件）·
  `start`（初始赋值）· `max_steps`（观察步数上限，默认 50）。
- **判词**：`stable` · `periodic` · `unstable` · `demo` · `input_pending`。
- **一条要点：周期 1 与定点是同一件事**。赋值重复且周期为 1 → `stable`（一步到定点）；
  周期大于 1 才是真振荡。所以"到定点"有**两条到达路径**（逐步稳住 / 一步稳住），
  出口都记 `stable`，用 `fixed_value` 给出定在哪。
- **周期 2 就是说谎者型**：句子每步在真/假之间翻转——修正理论的口径是"**无稳定真值，
  落入振荡**"（这是学界共识的口径，不是本引擎自创的结论）；周期更大则报长度 p 的循环。
- **不稳定的判据是"窗口"**：走满观察步数后，若最近三步赋值相同仍算 `stable`；
  否则 `unstable`——**只说"这个窗口里看不出来"**，不说"它永远不稳定"。
- **全量更新**：每一轮所有句子一起重算（不是逐句就地改），所以轨迹可复现、可逐步核对。
- **诚实边界**（`boundary` 字段随每个返回点带回）：本件只报**修正序列的形态**
  （收敛 / 周期 / 窗口内不稳定），并给出轨迹让人复核；**不判定句子的真值地位**，
  也不替使用者决定"该采用哪一套真值条件"。
