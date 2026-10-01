# 临界诊断 criticality — 逻辑流程图

> 模块：`engine/mechanisms/criticality.py` · 层：第 2 层机制（诊断层）
> 一句话：给一串「事件规模」，判它**是否落在无标度区间**，落在的话给幂律指数、**三态**
> （次临界/临界/超临界）、**距阈值多远**与**自举稳定性**。
> 图 1 → `run()` 主流程（四道校验 + 两道门槛 + 三态）
> 图 2 → 两条独立估计路与三个门槛（这是本件的核心：宁可不判，不硬判）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：先拦 → 两条路各算一遍 → 过两道门槛才给三态

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"mode 在 diagnose / compare 里?"}
  V1 -->|否| R1["input_pending<br/>mode 只认这两个"]
  V1 -->|是| V2{"sizes 是非空列表?"}
  V2 -->|否| R2["input_pending<br/>需要 sizes"]
  V2 -->|是| V3{"alpha_critical / tol 是数?"}
  V3 -->|否| R3["input_pending<br/>阈值必须是数"]
  V3 -->|是| N1{"样本数 不小于 MIN_N 8?"}
  N1 -->|否| R4["input_pending<br/>样本不足，判不了"]
  N1 -->|是| N2{"样本数 不超过 MAX_N 5000?"}
  N2 -->|否| R5["size_limit<br/>超上限不硬跑"]
  N2 -->|是| N3{"每个值都是正数且非 NaN?"}
  N3 -->|否| R6["input_pending<br/>规模必须是正数"]
  N3 -->|是| X1["下界 x_min：缺省取样本最小值"]
  X1 --> X2{"x_min 在 (0, 最大值] 内?"}
  X2 -->|否| R7["input_pending<br/>下界越界"]
  X2 -->|是| D1{"不同取值数 不小于 MIN_DISTINCT 5?"}
  D1 -->|否| R8["not_scale_free<br/>取值太单一，无法拟合"]
  D1 -->|是| EST["两条独立路各算一遍：<br/>A 回归路：log-log CCDF 斜率取负<br/>B Hill 路：n / 求和 ln(s 除 x_min)"]
  EST --> E1{"两条路都算出来了?"}
  E1 -->|否| R9["not_scale_free<br/>算法条件不满足"]
  E1 -->|是| G1{"门槛一：拟合 R² 不小于 0.90?"}
  G1 -->|否| R10["not_scale_free<br/>直线不直，不给三态"]
  G1 -->|是| G2["门槛二：两条路的差是否超过容差<br/>max(0.25, 0.15 乘 回归指数绝对值)"]
  G2 -->|超过| R11["estimator_disagree<br/>两条路对不上，硬给结论会误导"]
  G2 -->|没超| T1{"回归指数 与阈值比较（容差 tol 默认 0.25）"}
  T1 -->|小于 阈值减容差| T2["超临界"]
  T1 -->|大于 阈值加容差| T3["次临界"]
  T1 -->|落在容差带内| T4["临界"]
  T2 --> B1["自举稳定性：有放回重采样算分位<br/>（次数上限 MAX_BOOT 1000；给 0 就不给分位）"]
  T3 --> B1
  T4 --> B1
  B1 --> OUT["diagnosed<br/>指数三件套 + R² + 三态 + 距阈值距离 + 分位"]
  OUT --> BND["boundary：样本不足 / 不直 / 两路不一致一律如实报，<br/>不编数也不硬给三态"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R10,R11,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class OUT out
  class B1,D1,E1,G1,G2,N1,N2,N3,T1,T2,T3,T4,V1,V2,V3,X1,X2 tool
```

## 二、两条独立估计路与三道闸（为什么"宁可不判"）

```mermaid
flowchart TD
  S["同一份规模样本"] --> P1["回归路：<br/>取值点的 log 与 log 互补累积分布做一元线性回归<br/>斜率取负即指数"]
  S --> P2["Hill 路：<br/>n 除以 求和 ln(取值 除 下界)"]
  P1 --> M1{"点数不少于 MIN_DISTINCT 5?"}
  M1 -->|否| Q1["回归不可用"]
  M1 -->|是| M2{"分母平方和大于 0?"}
  M2 -->|否| Q1
  M2 -->|是| Q2["给出指数与 R²"]
  P2 --> M3{"尾部点数不少于 2 且分母大于 0?"}
  M3 -->|否| Q3["Hill 不可用"]
  M3 -->|是| Q4["给出指数"]
  Q2 --> CMP{"两路之差在容差内?"}
  Q4 --> CMP
  CMP -->|否| D1["estimator_disagree"]
  CMP -->|是| C1["出口径换算：密度指数等于互补累积指数加 1<br/>（防口径误读；两种口径差 1）"]
  C1 --> D2["diagnosed + 三态"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class P1,P2,M1,M2,M3,CMP,C1 tool
  class Q1,Q3,D1 stop
  class Q2,Q4,D2 out
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`diagnose` / `compare`）· `sizes` · `sizes_b`（对照用）·
  `alpha_critical`（默认 2.0）· `tol`（默认 0.25）· `x_min` · `n_boot`（默认 200）· `seed`（默认 0，同输入同输出）。
- **判词**：`diagnosed` · `not_scale_free` · `estimator_disagree` · `input_pending` · `size_limit`
  （另：门槛前六道校验各自返回 `input_pending`，见上图）。
- **关键常量**：`MIN_N = 8` · `MIN_DISTINCT = 5` · `MAX_N = 5000` · `R2_GATE = 0.90` · `MAX_BOOT = 1000`。
- **两条路的差容差**：`max(0.25, 0.15 × |回归指数|)`——**两路对不上就不给三态**，这是本件最重要的一条纪律。
- **口径**：本件对外一律用**互补累积分布（CCDF）指数**；`alpha_pdf` 是**回归路**换算成密度指数的
  （＝ CCDF 指数 + 1）——**别拿它去和别人的 MLE 密度指数直接比**（两条路会差一个估计差）。
- **`compare` 模式**：只**并置事实**（两侧的三态与距离），不判"谁该停"；有一条没给出三态时如实说距离无从比。
- **诚实边界**（`boundary` 字段随每个返回点带回）：只做**形状与指数**的诊断；样本太少 / 直线不直 /
  两路不一致 → **直接报，不硬给三态**；阈值与容差是**参数**（默认值只是常用约定，不是体系结论）；
  **不做模型族检验**（幂律 vs 对数正态的正式比较要外部库）；只诊断不决策。
