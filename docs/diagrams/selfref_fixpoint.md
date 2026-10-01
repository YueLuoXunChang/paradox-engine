# 自指检测 selfref_fixpoint — 逻辑流程图

> 模块：`engine/mechanisms/selfref_fixpoint.py` · 层：第 2 层机制（钻墙主力）
> 一句话：把递归修正跑起来看它**落在哪一格**——不动点 / 共振带（稳定振荡）/ 发散 / 说不清；
> 内置三种经典自指句（说谎者 · 真话者 · 哥德尔句），也给自定义修正函数的口子。
> 图 1 → 两种 mode 的主流程（内置句 / 自定义函数）
> 图 2 → 观测器把轨迹判成哪一类
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"mode 在 iterate / sentence 里?"}
  V1 -->|否| R1["input_pending<br/>mode 只认这两个"]
  V1 -->|是| M1{"mode 是 sentence?"}

  M1 -->|是| S1{"sentence 是哪个内置句?"}
  S1 -->|liar| S2["跑说谎者修正函数（每步取反）"]
  S2 --> S3{"观测结果周期等于 2?"}
  S3 -->|是| O1["liar_cycle<br/>每步翻转，正是说谎者的形态"]
  S3 -->|否| O2["undetermined<br/>形态对不上，不硬贴标签"]
  S1 -->|truth_teller| S4["修正函数是恒等 → 一步到不动点"]
  S4 --> O3["fixed_point"]
  S1 -->|godel| S5["哥德尔句没有真值修正函数可跑<br/>（可证性谓词不是真值函数）"]
  S5 --> O4["annotated_pa<br/>如实注解 P-A，不假装跑过序列"]
  S1 -->|其它| R2["input_pending<br/>内置句只有 liar / truth_teller / godel"]

  M1 -->|否| I1{"f 给了吗?"}
  I1 -->|否| R3["input_pending<br/>iterate 模式需要 f"]
  I1 -->|是| I2{"f 可调用?"}
  I2 -->|否| R4["parse_error"]
  I2 -->|是| OBS["调用观测器：跑 max_steps 步，逐步留痕"]
  OBS --> K1{"观测结果"}
  K1 -->|不动点| P1["fixed_point"]
  K1 -->|周期| P2{"周期等于 2 且两个状态互为真假?"}
  P2 -->|是| P3["liar_cycle<br/>说谎者形态"]
  K1 -->|周期| P4{"是数值型周期?"}
  P4 -->|是| P5["resonance_band<br/>共振带收敛（稳定振荡）"]
  K1 -->|增长| P6["diverge<br/>超出阈值绝对值大于 1e12"]
  K1 -->|开放| P7["undetermined<br/>跑满步数仍未见稳定形态"]

  O1 --> CARD["装配注解卡（P-A 免判，其余按形态给卡）"]
  O3 --> CARD
  O4 --> CARD
  P1 --> CARD
  P3 --> CARD
  P5 --> CARD
  P6 --> CARD
  P7 --> CARD
  CARD --> OUT["返回：verdict + selfref_type + detail + annotation"]
  OUT --> BND["boundary：判的是轨迹形态，不是真值"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R2,R3,R4 stop
  class OUT out
  class I1,I2,K1,M1,P1,P2,P3,P4,P5,P6,P7,S1,S2,S3,S4,S5,V1 tool
```

## 二、观测器 `_observe`：把一条轨迹判成哪一格

```mermaid
flowchart TD
  A["输入 f、初值、最大步数、容差"] --> B["seen 列表记下走过的状态"]
  B --> C["循环最多 max_steps 步"]
  C --> D["算下一步 nxt 等于 f(state)"]
  D --> E{"nxt 与上一步相同（容差内）?"}
  E -->|是| F["fixed_point<br/>记下第几步到达"]
  E -->|否| G{"nxt 是否等于 seen 里出现过的某个状态?"}
  G -->|是| H["cycle<br/>记下周期与环起点"]
  G -->|否| I{"nxt 是数值且绝对值大于 1e12?"}
  I -->|是| J["grow<br/>判为发散"]
  I -->|否| K["继续下一步"]
  K --> C
  C -->|跑满步数| L["open<br/>仍未稳定，如实说"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,B,C,D,K core
  class E,G,I tool
  class F,H,J,L out
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`iterate` / `sentence`）· `f`（修正函数）· `state0` ·
  `sentence`（`liar` / `truth_teller` / `godel`）· `max_steps` · `tol`。
- **判词**：`fixed_point` · `resonance_band` · `liar_cycle` · `diverge` · `undetermined` ·
  `annotated_pa` · `input_pending` · `parse_error`。
- **观测器的内部形态词**（不直接对外）：`fixed_point` · `cycle` · `grow` · `open`。
- **留痕**：`detail` 带到达步数、周期与环起点、以及整条 `trace`——"只迭代一轮就停"这类毛病一眼看得出。
- **诚实边界**：判的是**轨迹形态**（落在哪一格），**不是真值**；哥德尔句**没有**真值修正函数可跑，
  所以只给 P-A 注解、**不假装跑过序列**；跑满步数仍未稳定时如实报 `undetermined`，不硬贴标签。
