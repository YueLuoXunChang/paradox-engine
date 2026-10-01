# 自然演绎 nd_propositional — 逻辑流程图

> 模块：`engine/classical/nd_propositional.py` · 层：第 1 层经典逻辑（自然演绎证明搜索）
> 一句话：给前提与结论，按自然演绎规则**搜一棵证明树**——证到了就 `proved` 并给出树，
> 搜完没找到就 `not_proved`，搜到上限就 `search_limit`（**不把"没找到"说成"不存在"**）。
> 图 1 → `run()` 主流程与三种出口
> 图 2 → 两套系统的分叉：经典多一条"双重否定消去"
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：给结论 → 选系统 → 搜证明树

```mermaid
flowchart TD
  IN["run(inputs)"] --> C1{"给了结论吗?"}
  C1 -->|没给| R1["conclusion_pending"]
  C1 -->|给了| S1{"system 是 classic 或 intuitionistic?"}
  S1 -->|不是| R2["parse_error<br/>系统名非法"]
  S1 -->|是| P1{"前提与结论都解析成功?"}
  P1 -->|否| R3["parse_error"]
  P1 -->|是| S2["取步数上限<br/>缺省 60 步"]
  S2 --> SR["深度优先搜证明树：<br/>前提当假设，结论当目标"]
  SR --> Q1{"搜到证明了吗?"}
  Q1 -->|搜到| O1["proved<br/>给出证明树"]
  Q1 -->|搜索空间走完仍没有| O2["not_proved<br/>给出已展开的树"]
  Q1 -->|步数用完| O3["search_limit<br/>只说没搜完"]
  O1 --> BND
  O2 --> BND
  O3 --> BND
  BND["boundary：'没找到'与'不存在'分得很清——<br/>步数用完一律报 search_limit"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class IN core
  class R1,R2,R3 stop
  class BND,O1 out
  class C1,P1,S1,S2,SR,Q1 tool
  class O2,O3 stop
```

## 二、两套系统的差别：经典比直觉主义多一条双重否定消去

```mermaid
flowchart TD
  G["目标与已有假设"] --> M{"目标已经被假设给出?"}
  M -->|是| P1["关闭：直接得证"]
  M -->|否| M2{"结论是合取?"}
  M2 -->|是| P2["拆成两个子目标分别证"]
  M2 -->|否| M3{"结论是蕴含?"}
  M3 -->|是| P3["把前件加进假设<br/>再证后件"]
  M3 -->|否| M4{"结论是析取?"}
  M4 -->|是| P4["尝试两个分支"]
  M4 -->|否| M5{"结论是双重否定?"}
  M5 -->|是| P5["先处理否定"]
  M5 -->|否| M6{"系统是经典?"}
  M6 -->|是| P6["可用双重否定消去<br/>由非非A 得 A"]
  M6 -->|否| P7["不用这条：<br/>直觉主义侧只留构造性规则"]
  P1 --> OK1["proved"]
  P2 --> OK1
  P3 --> OK1
  P4 --> OK1
  P5 --> OK1
  P6 --> OK1
  P7 --> NG["该目标在直觉主义侧证不出"] --> OK2["not_proved 或 search_limit"]
  OK1 --> N1["每一步都进证明树，可逐步复核"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class G core
  class M,M2,M3,M4,M5,M6,P2,P3,P4,P5,P6,N1 tool
  class P1,OK1 out
  class P7,NG,OK2 stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`premises`（前提列表）· `conclusion`（结论）·
  `system`（`classical` 默认 / `intuitionistic`）· `max_steps`（步数上限，默认 60）。
- **判词**：`proved` · `not_proved` · `search_limit` · `conclusion_pending` · `parse_error`。
- **三种出口分得很清**（这是本件最要紧的一条纪律）：
  - `proved`：真的搜到了，附**证明树**，每一步都能对着规则核；
  - `not_proved`：搜索空间走完了仍没有——**"在这套规则下没搜到"**，附已展开的树；
  - `search_limit`：步数用完——**只说"没搜完"**，不说"证不出"。后两者不能互相冒充。
- **两套系统的差别只有一条**：`classical` 多一条**双重否定消去**（由"非非 A"得 A），
  `intuitionistic` 不留这条，只保留构造性规则。所以同一对前提与结论，
  换系统可能从 `proved` 变成 `not_proved`——这是**有意为之**，不是不稳定。
- **每一步都留痕**：证明树与已展开的树都会随返回值给出（`proof_tree`），
  复核不用重跑搜索。
- **诚实边界**（`boundary` 字段随每个返回点带回）：本件是**搜索型**证明，
  证到就给树、搜不完就报上限，**不宣称"该结论成立"或"不成立"，
  也不替使用者决定用哪套系统**（系统名是调用方给的参数）。
