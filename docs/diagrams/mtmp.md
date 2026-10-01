# MT-MP-TL 骨架 mtmp — 逻辑流程图

> 模块：`engine/skeleton/mtmp.py` · 层：第 0 层骨架（点 / 线程 / 拓扑 / 操作）
> 一句话：一套通用骨架——**点**按自治规则演化，**线程**按方向有序推进，
> **拓扑**判 12 种形态，**操作**按定义改图；判不了的一律标出来，不硬判。
> 图 1 → `run()` 四个模式的分派与各自的第一道校验
> 图 2 → 12 形态的判定顺序（可判 / 需元数据 / 同图歧义）
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：四个模式分派，各自先拦一道

```mermaid
flowchart TD
  IN["run(inputs)"] --> M{"mode 是哪个?"}
  M -->|其他| R0["mode_pending<br/>只认 point / thread / topology / op"]
  M -->|point| PA{"给了 point 吗?"}
  PA -->|没有| E1["input_pending"]
  PA -->|有| PB{"action 是哪个?"}
  PB -->|step| P1["stepped<br/>按自治规则演化一步"]
  PB -->|deform| P2["deformed<br/>type 不变 state 变"]
  PB -->|缺省| P3["created"]
  M -->|thread| TA{"给了 threads 吗?"}
  TA -->|没有| E1
  TA -->|有| TB{"action 是哪个?"}
  TB -->|advance| T1["advanced<br/>按方向推进一步"]
  TB -->|converge| T2["merged / merge_failed<br/>在汇合点并成一条"]
  TB -->|cross| T3["crossed / cross_failed<br/>换信息后各走各的"]
  M -->|topology| GA{"给了 points 吗?"}
  GA -->|没有| E1
  GA -->|有| GB{"action 是哪个?"}
  GB -->|classify| G1["classified<br/>12 形态判词"]
  GB -->|neighbors| G2["neighbors<br/>邻居查询"]
  M -->|op| OA{"给了 op 吗?"}
  OA -->|没有| E1
  OA -->|有| O1["applied<br/>connect / disconnect / replace<br/>fold / spawn"]
  O1 --> O2["rejected<br/>点不存在 / 无边可断 / 不可达"]
  P3 --> BND
  T1 --> BND
  G1 --> BND
  O2 --> BND
  BND["boundary：判不了就说判不了<br/>形态与操作各自带边界声明"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R0,E1,O2 stop
  class BND out
  class G1,G2,O1,P1,P2,P3,T1,T2,T3 tool
  class IN,M,PA,PB,TA,TB,GA,GB,OA core
```

## 二、12 形态的判定顺序：可判的严格判，要元数据的等元数据

```mermaid
flowchart TD
  S["同一份点集与边集"] --> C1{"给了层标记吗?"}
  C1 -->|键数两个以上| H1["stack 叠合"]
  C1 -->|没给| C2{"给了条件表吗?"}
  C2 -->|给了| H2["branch 条件分支"]
  C2 -->|没给| C3{"边数等于全配对?"}
  C3 -->|是| H3["grid 网格"]
  C3 -->|否| C4{"恰一点度 n-1、其余度为 1?"}
  C4 -->|是| H4["star 星型"]
  C4 -->|否| C5{"每点度为 2 且连通?"}
  C5 -->|是| H5["cycle 环路"]
  C5 -->|否| C6{"连通且恰有两个度 1 的端点?"}
  C6 -->|是| H6["linear 线性"]
  C6 -->|否| C7{"多个连通分量且每块都是链?"}
  C7 -->|是| H7["parallel 平行链"]
  C7 -->|否| C8{"边数超过点数减一?"}
  C8 -->|是| H8["chain 链式"]
  C8 -->|否| H9["network 兜底<br/>不编形态名"]
  H8 --> AMB["同图歧义如实报：<br/>3 点链等于 K1,2 判 star<br/>3 点环等于 K3 判 grid<br/>无向图下发散与交汇都判 star"]
  H9 --> AMB
  AMB --> OPX["形态只是判词：<br/>改图另有五个操作<br/>汇合在线程侧（merged）"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class S core
  class C1,C2,C3,C4,C5,C6,C7,C8 tool
  class H1,H2,H3,H4,H5,H6,H7 out
  class H8,H9,AMB stop
  class OPX out
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode`（`point` / `thread` / `topology` / `op`）· `point` · `threads` ·
  `points` · `edges` · `op` · `a` · `b` · `kappa` · `verbose`。
- **判词**（14 个）：`created` · `stepped` · `deformed` · `advanced` · `merged` · `merge_failed` ·
  `crossed` · `cross_failed` · `classified` · `neighbors` · `applied` · `rejected` ·
  `input_pending` · `mode_pending`。
- **点**：`state` 的演化由该点的自治规则决定（有规则才 `stepped`，没规则就如实返回）；
  `deform` 保持 `type` 不变、只改 `state`。
- **线程**：`direction` 定方向（反向线程按倒序访问），`speed` 是单位时间经过的节点数，
  `phase` 是相位差；
  汇合（`merged`）与交叉（`crossed`）是两件事——**交叉不合并成一条**。
- **形态判定的诚实口径**（对着代码核过）：
  - `stack` 只在**给了层标记且键数不少于 2** 时判——判据看的是"有没有层标记"，
    **不校验层号是否真的不同**；所以同一批点全填同一层号，也会判成 `stack`。
  - `diverge`（发散）与 `converge`（交汇）两分支的条件**互相蕴含**，而 `diverge` 排在前面，
    因此 `converge` 的判词实际取不到；**同一张无向图，单源多出与多入单出都先判到 `star`**。
    要分开这两者，必须另外给出**有向**信息（方向来自线程的方向）。
  - 三个节点以内的链与环会与星型 / 全连接同图（见上图），所以形态判词要**连边集一起看**。
- **操作口径**：`op` 模式认 `connect` / `disconnect` / `replace` / `fold` / `spawn`；
  `converge` 落在**线程侧**（`merged`），不在 `op` 模式里。
  `fold` 按实现是**加一条直连把距离压到一跳**——注意这与"折叠只改距离、不改连接关系"
  的读法不同，用的时候照实现理解（本件已在 `boundary` 里声明，不藏）。
- **诚实边界**（`boundary` 字段随每个返回点带回）：判不了就返回 `input_pending` /
  `mode_pending`，不猜；形态里语义型的（叠合 / 条件分支）没有元数据时不硬判；
  **本件只做结构判定，不做矛盾判定、不做决策**。
