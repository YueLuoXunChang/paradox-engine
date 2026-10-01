# 增长护栏 growth_guard — 逻辑流程图

> 模块：`engine/mechanisms/growth_guard.py` · 层：第 2 层机制
> 一句话：给"每轮产物规模 + 预算"，算增长率、限幅/增益调度/滞后补偿三件套的压制效果与**代价**
> （累计截断量 · 每轮最大跳变 · 开关抖动次数），以及"不截断需要多大预算"。
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：先拦、再判、最后才推演

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["parse_error<br/>reason=输入必须是 dict"]
  V1 -->|是| V2{"mode ∈ {compare, watch}?"}
  V2 -->|否| R2["parse_error<br/>mode 只认这两个"]
  V2 -->|是| V3{"budget 是正整数?"}
  V3 -->|否| R3["parse_error<br/>budget 必须是正整数"]
  V3 -->|是| V4{"steps 正整数?"}
  V4 -->|否| R4["parse_error"]
  V4 -->|是| V5{"steps 不大于 MAX_STEPS 200?"}
  V5 -->|否| R5["size_limit<br/>推演轮数超上限，不硬跑"]
  V5 -->|是| V6{"gain_min / high_ratio / low_ratio<br/>都在 (0,1] 内?"}
  V6 -->|否| R6["parse_error<br/>阈值必须是 (0,1] 的数"]
  V6 -->|是| V7{"low_ratio 小于 high_ratio?"}
  V7 -->|否| R7["parse_error<br/>下阈必须小于上阈（否则没有滞后带）"]
  V7 -->|是| M1{"给了 sizes 吗?"}

  M1 -->|是| S1{"sizes 是非空列表?"}
  S1 -->|否| R8["parse_error"]
  S1 -->|是| S2{"点数 不大于 MAX_POINTS 5000?"}
  S2 -->|否| R9["size_limit<br/>实测点数超上限"]
  S2 -->|是| S3{"逐点都是非负数值?"}
  S3 -->|否| R10["parse_error<br/>非数值 / 负数"]
  S3 -->|是| S4{"点数 不小于 MIN_POINTS 3<br/>且凑得出 不小于2 对比值?"}
  S4 -->|否| R11["insufficient_data<br/>点太少判不了增长率"]
  S4 -->|是| G1["增长率 r = 相邻两轮比值的**几何平均**<br/>（出现 0 规模时退回中位比值并在 detail 说明）"]

  M1 -->|否| N1{"n0 与 rate 齐吗?"}
  N1 -->|否| R12["input_pending<br/>要么给 sizes，要么给 n0+rate"]
  N1 -->|是| N2{"n0 非负整数、rate 非负数?"}
  N2 -->|否| R13["parse_error"]
  N2 -->|是| G1

  G1 --> K1["kind = 比 1 的容差（GROWTH_TOL 0.02）"]
  K1 --> K2{"r 大于 1+tol ?"}
  K2 -->|是| KG["geometric_growth"]
  K2 -->|否| K3{"r 小于 1−tol ?"}
  K3 -->|是| KS["shrinking"]
  K3 -->|否| KF["flat"]

  KG --> O1{"实测序列里已经越过预算?"}
  KS --> O1
  KF --> O1
  O1 -->|是| R14["observed_exceeded<br/>先把数据本身处理掉，再谈护栏参数"]
  O1 -->|否| O2{"kind 是 geometric_growth?"}
  O2 -->|否| R15["bounded_no_guard<br/>不护栏也有界（对给定增长模型的推演）"]
  O2 -->|是| SIM["三件套推演 + 参照系（每轮 trace 留痕）"]
  SIM --> OUT["guard_engaged"]
  OUT --> BND["boundary：对给定增长模型的推演，不是对真实递归的证明"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R10,R11,R12,R13,R14,R15,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class OUT out
  class M1,V1,V2,V3,V4,V5,V6,V7 tool
```

## 二、三件套各自的压制逻辑（同一张图的另一种读法）

```mermaid
flowchart TD
  subgraph "RAW[""参照系（不上护栏）"]
    R0["n ← ⌊r·n⌋"] --> R1["每轮乘倍数 → 指数增长"]
    R1 --> R2["报 exceeded_at（第几轮越界）"]
  end
  subgraph "CL[""限幅 clamp"]
    C0["want = ⌊r·n⌋"] --> C1["n ← min(want, B)"]
    C1 --> C2["cut_total += max(0, want − n)<br/>代价＝整块截断"]
  end
  subgraph "GA[""增益调度 gain"]
    G0["want_raw = ⌊r·n⌋"] --> G1{"want_raw 不大于 B ?"}
    G1 -->|是| G2["原样长（**不威胁预算就不动**）"]
    G1 -->|否| G3["g = min(1, max(g_min, 1 − n/B))<br/>want = ⌊n + g·(r−1)·n⌋"]
    G3 --> G4["逐步逼近 B，不是一步顶到上限"]
  end
  subgraph "HY[""滞后补偿 hysteresis"]
    H0{"介入中?"} -->|否| H1{"n 不小于 high ?"}
    H1 -->|是| H2["介入，switches += 1"]
    H0 -->|是| H3{"n 不大于 low ?"}
    H3 -->|是| H4["退出，switches += 1"]
    H1 -->|否| H5["带内：状态不变（这段就是滞后带）"]
    H3 -->|否| H5
    H2 --> H6["介入时按增益地板长：rate' = 1 + g_min·(r−1)"]
    H4 --> H7["退出后恢复原倍率"]
  end
  C2 --> SUM["policies：{trace, max_size, final_size,<br/>exceeded_at, switches, max_jump, cut_total}"]
  G4 --> SUM
  H6 --> SUM
  H7 --> SUM
  R2 --> CMP["recommendation：no_cut_budget / cut_needed /<br/>rounds_to_budget_*"]
  SUM --> CMP
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R0,R1,R2 stop
  class C0,C1,C2 tool
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`sizes` / `n0` / `rate` / `budget` / `steps` / `mode` / `gain_min` /
  `high_ratio` / `low_ratio`。
- **判定的每个出口**：`world` 侧＝`geometric_growth` / `flat` / `shrinking`；
  **判词**：`bounded_no_guard` · `guard_engaged` · `observed_exceeded` · `insufficient_data` ·
  `input_pending` · `parse_error` · `size_limit` · `internal_error`。
- **关键常量**：`MIN_POINTS=3` · `MAX_POINTS=5000` · `MAX_STEPS=200` · `DEFAULT_STEPS=20` ·
  `GROWTH_TOL=0.02` · `DEFAULT_GAIN_MIN=0.1` · `DEFAULT_HIGH=0.9` · `DEFAULT_LOW=0.6`。
- **留痕**：每条策略都给逐轮 `trace`；`max_jump` 把"起点到自己第一轮"那一跳也算进去
  （各策略起点必须同源）。
- **诚实边界**（`boundary` 字段随每个返回点带回）：限幅与增益都是**有损**的，本件只报代价、
  **不判砍掉的那部分要不要紧**；取整语义是 `⌊n·r⌋`（规模很小时增长会被取整抹平）；
  本件**没有"步长限幅"（速率限）**这一件——只报每轮最大跳变，不限它；只诊断不决策。
