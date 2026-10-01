# 区间代数 interval_algebra — 逻辑流程图

> 模块：`engine/cold/interval_algebra.py` · 层：第 3 层（外部共识：Allen 1983 关系代数与路径一致性，归借鉴区）
> 一句话：给若干**事件**与它们之间的**定性时序关系**，判这套关系自不自洽、能不能找到具体排布；
> 也能算关系的**复合**与**逆**。
> 图 1 → `run()` 五种 mode 的主流程
> 图 2 → 路径一致性：逐对收紧，收紧到空集就是真不一致
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"inputs 是 dict?"}
  V1 -->|否| R1["input_pending"]
  V1 -->|是| V2{"mode 在 consistent / solve / point / compose / converse 里?"}
  V2 -->|否| R2["input_pending"]
  V2 -->|是| M1{"mode 是 compose 或 converse?"}
  M1 -->|是| B1{"converse：relation 给了?"}
  B1 -->|否| R3["input_pending<br/>converse 需 relation"]
  B1 -->|是| O1["conversed<br/>算关系的逆（每个基本关系取逆后并回去）"]
  B1 -->|不是 converse| B2{"compose：relations 是两个?"}
  B2 -->|否| R4["input_pending<br/>compose 需 relations 两个"]
  B2 -->|是| O2["composed<br/>两关系逐对复合后并起来"]
  M1 -->|否| E1{"events 是非空列表?"}
  E1 -->|否| R5["input_pending<br/>需 events"]
  E1 -->|是| E2{"事件名都是非空字符串?"}
  E2 -->|否| R6["input_pending"]
  E2 -->|是| E3{"事件不重名?"}
  E3 -->|否| R7["input_pending<br/>同一事件不该出现两次"]
  E3 -->|是| E4{"事件数不超过 MAX_EVENTS 8?"}
  E4 -->|否| R8["size_limit"]
  E4 -->|是| E5{"relations 是非空列表?"}
  E5 -->|否| R9["input_pending<br/>需 relations"]
  E5 -->|是| E6{"每项都写成 [甲, 关系, 乙]?"}
  E6 -->|否| R10["input_pending"]
  E6 -->|是| E7{"两端事件都在 events 里?"}
  E7 -->|否| R11["input_pending<br/>不认未声明的事件"]
  E7 -->|是| C1["建关系矩阵：同一对事件的关系取并集"]
  C1 --> C2{"解析有语法错?"}
  C2 -->|是| R12["parse_error"]
  C2 -->|否| C3{"某一对事件的关系已经成空集?"}
  C3 -->|是| O3["inconsistent<br/>直接矛盾（给出挤空的那一对）"]
  C3 -->|否| C4["路径一致性：逐对收紧到不动"]
  C4 --> C5{"收紧过程中某对变空集?"}
  C5 -->|是| O4["inconsistent"]
  C5 -->|否| M2{"mode 是 consistent?"}
  M2 -->|是| O5["path_consistent<br/>只说明**没发现冲突**，不等于有解"]
  M2 -->|否| M3{"mode 是 point（点代数）?"}
  M3 -->|是| O6["consistent<br/>点代数上路径一致性**完备**"]
  M3 -->|否| S1["solve：在有界预算内搜一个解（MAX_SOLVE_NODES 200000）"]
  S1 --> S2{"找到了具体排布?"}
  S2 -->|是| O7["model_found<br/>给出可复核的模型"]
  S2 -->|否| O8["not_found_in_budget<br/>预算内没找到 ≠ 无解"]
  O1 --> BND["boundary：区间代数上路径一致性只给必要条件；<br/>报 path_consistent 不等于有解"]
  O2 --> BND
  O3 --> BND
  O4 --> BND
  O5 --> BND
  O6 --> BND
  O7 --> BND
  O8 --> BND
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1,R10,R11,R12,R2,R3,R4,R5,R6,R7,R8,R9 stop
  class B1,B2,C1,C2,C3,C4,C5,E1,E2,E3,E4,E5,E6,E7,M1,M2,M3,S1,S2,V1,V2 tool
```

## 二、路径一致性：逐对收紧到不动（这是"必要条件"）

```mermaid
flowchart TD
  A["关系矩阵：每对事件一个**候选关系集**"] --> B["取三元组（甲, 乙, 丙）"]
  B --> C["候选收紧：<br/>甲到丙 的候选 ← 甲到丙 ∩（甲到乙 复合 乙到丙）"]
  C --> D{"候选变了没有?"}
  D -->|变了| E["记录下来，继续扫其他三元组"]
  D -->|没变| F{"所有三元组都扫完且都不再变?"}
  F -->|否| B
  F -->|是| G["停在不动点：矩阵稳定"]
  E --> H{"有没有哪一对被收紧成空集?"}
  H -->|是| I["inconsistent<br/>**真不一致**——找到了挤空的那一对"]
  H -->|否| J["path_consistent<br/>只是**没发现**冲突，有解与否它答不了"]
  G --> H
  J --> K["想要确定结论走 mode=solve：<br/>有界预算内找见证，找到的模型可复核"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class A,B,C,E core
  class D,F,H tool
  class G,J,K out
  class I stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`mode` · `events`（事件名列表）· `relations`（`[甲, 关系, 乙]` 列表）·
  `relation`（compose / converse 用）。
- **判词**：`composed` · `conversed` · `consistent` · `path_consistent` · `inconsistent` ·
  `model_found` · `not_found_in_budget` · `input_pending` · `parse_error` · `size_limit`。
- **关键常量**：`MAX_EVENTS = 8` · `MAX_SOLVE_NODES = 200000`；基本关系 13 个（先于 / 相接 / 重叠 /
  开始于 / 包含于 / 结束于 / 同时 + 各自逆），另有 `REL_CN` 中文别名与本构件认识的各种写法（`ALIASES`）。
- **点代数**：`mode=point` 用三个点关系（`<` / `=` / `>`）＋ 各自的复合与逆表，
  **点代数上路径一致性是完备的**（所以那个模式给的是 `consistent` 而不是 `path_consistent`）。
- **诚实边界**（`boundary`）：**区间代数上路径一致性只给必要条件**——报 `inconsistent` 就是**真不一致**
  （找到了挤空的那一对）；报 `path_consistent` **只说明没发现冲突，不等于有解**；要确定结论用
  `mode=solve`（有界预算内找到的模型可复核）；**只做定性关系、不给数值**；
  见证搜索有界：**没找到 ≠ 无解**；只诊断不决策。
