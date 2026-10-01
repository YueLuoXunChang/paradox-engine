# 全程自反旁路 observer_bypass — 逻辑流程图

> 模块：`engine/mechanisms/observer_bypass.py` · 层：第 2 层机制（系统级旁路）
> 一句话：主线程照常推进，**矛盾观察走旁路线程**——检测到矛盾/自指就注解并注入参考，
> **主带不停**。不是宣称判定了矛盾，而是"矛盾观察不阻塞主流程"。
> 图 1 → `run()` 主流程：逐步推进 + 同步旁路观察 + 注入参考
> 图 2 → 检测来源两条路与"不阻塞"的实测口径
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：主线程不停，旁路随行

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"main_events 是非空列表?"}
  V1 -->|否| R1["input_pending<br/>没有主线程不跑旁路"]
  V1 -->|是| L0["初始化：findings 空 · injected_at 空"]
  L0 --> L1["取第 i 步事件（i 从 0 起）"]
  L1 --> MAIN["主线程走完第 i 步<br/>不因旁路而停"]
  MAIN --> D1{"调用方给了 detect 吗?"}
  D1 -->|给了| D2["用调用方的检测函数"]
  D1 -->|没给| D3["用内置启发：<br/>关键词命中 / 相邻步对立"]
  D2 --> D4{"检测抛异常了吗?"}
  D4 -->|抛了| D5["记为 detect_error<br/>如实标注，不吞"]
  D4 -->|没抛| D6{"有发现吗?"}
  D3 --> D6
  D6 -->|没有| NEXT{"还有下一步吗?"}
  D6 -->|有| F1["生成注解：<br/>A / notA / 层级 / 来源 / 状态 / 备注"]
  F1 --> F2{"use_advice 为真吗?"}
  F2 -->|真| F3["注入参考给主线程<br/>记下注入位置"]
  F2 -->|假| F4["只记录发现，不注入"]
  F3 --> NEXT
  F4 --> NEXT
  D5 --> NEXT
  NEXT -->|有| L1
  NEXT -->|没有了| OUT["observed<br/>主线程完整跑完"]
  OUT --> BND["boundary：旁路只做检测 + 注解 + 注入参考——<br/>不消除矛盾、不替主线程决策"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN,MAIN core
  class R1,D5 stop
  class OUT,BND out
  class D1,D2,D3,D4,D6,F1,F2,F3,F4,L0,L1,NEXT,V1 tool
```

## 二、检测来源两条路：一条交给自己，一条内置启发

```mermaid
flowchart TD
  E["第 i 步事件"] --> Q1{"检测来源?"}
  Q1 -->|调用方 detect| X1["自定义检测<br/>返回发现或空"]
  Q1 -->|缺省| X2["内置启发"]
  X2 --> K1{"文本含冲突 / 矛盾 /<br/>悖论 / 自指 / 两难 / 对立?"}
  K1 -->|命中| Y1["paradox 类发现<br/>标注：启发式，非完备"]
  K1 -->|没命中| K2{"上一步是'要 X'<br/>这一步是'不要 X'或'反 X'?"}
  K2 -->|命中| Y2["conflict 类发现<br/>相邻步对立"]
  K2 -->|没命中| Y3["本步无发现"]
  Y1 --> A1["成注解：A 与 notA<br/>层级 P-B · 来源 runtime · 状态 活跃"]
  Y2 --> A1
  A1 --> A2{"use_advice 为真?"}
  A2 -->|真| A3["注入参考<br/>injected_at 记下这一步"]
  A2 -->|假| A4["只入 findings<br/>injected_at 为空"]
  A2 --> A5["主线程完整步数 = 事件条数<br/>这就是'不阻塞'的实测口径"]
  A3 --> A5
  A4 --> A5
  Y3 --> A5
  A5 --> A6["诚实点：只看已发生的步<br/>不预知未来"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class E core
  class X1,X2,K1,K2,A1,A2,A5,A6 tool
  class Y1,Y2,A3 out
  class A4,Y3 stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`main_events`（主线程事件序列，每步一句描述）·
  `detect`（检测函数 `event -> 发现或 None`，缺省用内置启发）· `use_advice`（默认真）。
- **判词**：`observed` · `input_pending`（缺主线程事件时如实拦下）。
- **输出**：`main_ran`（主线程完整步数）· `findings`（每项带位置 / 类型 / 注解 / 是否注入）·
  `injected_at`（注入发生的主线程位置）。
- **"不阻塞"怎么算数**：`main_ran` 等于事件条数——旁路只观察，不改变主事件序列本身；
  主线程是否采纳注入参考，由主线程策略决定（本件**只给参考，不做主线程的决策**）。
- **检测是启发式的**：内置只做关键词命中与相邻步对立，**不是完备判定**，
  命中与未命中都如实标注；调用方可以换成自己的 `detect`，异常会被记成 `detect_error`
  而不是吞掉。
- **不预知未来**：第 i 步的检测只看已经发生的 i 步（`main_events[:i]`），
  所以"注入"发生在检测点之后，白箱可见。
- **诚实边界**（`boundary` 字段随每个返回点带回）：旁路观察 = 检测 + 注解 + 注入参考，
  **既不消除矛盾，也不替代主线程做判断**；本件判的是"观察有没有阻塞主流程"，
  不是"矛盾是否被判定了"。
