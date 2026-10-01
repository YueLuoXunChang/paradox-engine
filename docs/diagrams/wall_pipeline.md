# 撞墙管线 wall_pipeline — 逻辑流程图

> 模块：`engine/mechanisms/wall_pipeline.py` · 层：第 2 层机制（撞墙管线 A）
> 一句话：经典层撞到不可判定时上卷到这里——**测墙 → 注解 → 钻墙 → 看墙 → 旁路 → 创生**，
> 最后给**五选一诊断**（可判在别处 / 良性自指 / 共振带自指 / 发散真墙 / 可创生）。
> 图 1 → 六步主流程与五选一
> 图 2 → 五选一是怎么从"钻"的结果映射出来的
> 判据与写法约定见 `docs/diagrams/README.md`。

## 一、run(inputs) 主流程：六步走完才给诊断

```mermaid
flowchart TD
  IN["run(inputs)"] --> V1{"wall 给了，或 thesis 与 antithesis 都有?"}
  V1 -->|否| R1["input_pending<br/>至少要一样材料"]
  V1 -->|是| S1["1 测墙：算悖论测度与张力"]

  S1 --> W1{"wall 是文本吗?"}
  W1 -->|是| W2["按内置自指句匹配：<br/>不可证 · 这句话是假的 等等"]
  W2 --> W3["命中哪个内置句，就用它的修正函数"]
  W1 -->|否| W4["用 thesis / antithesis 拼一个修正函数"]

  W3 --> S2["2 注解：生成 8 字段卡并分级"]
  W4 --> S2
  S2 --> S3["3 钻墙：交给自指检测跑修正序列"]
  S3 --> S4{"events 给了吗?"}
  S4 -->|是| S5["4 看墙：把事件喂给区间代数看时序自洽"]
  S4 -->|否| S6["4 看墙：缺线索，跳过并标注"]
  S5 --> S7{"thesis 与 antithesis 都有?"}
  S6 --> S7
  S7 -->|是| S8["5 旁路：走全程自反旁路（主链不停）"]
  S7 -->|否| S9["5 旁路：跳过并标注原因"]
  S8 --> S10["6 创生：对位创生第三态候选"]
  S9 --> S10
  S10 --> D1{"自指检测给的形态"}
  D1 -->|不动点| X1["benign_selfref<br/>良性自指，可给结果"]
  D1 -->|共振带或说谎者周期| X2["resonance_selfref<br/>稳定振荡，判振荡模式不判真值"]
  D1 -->|发散| X3["divergent_wall<br/>发散真墙，诚实标记不硬钻"]
  D1 -->|P-A 注解| X4["structural_wall<br/>结构性墙（哥德尔型）"]
  D1 -->|其它且两侧都在| X5["creatable<br/>可创生，第三态候选供人评估"]
  D1 -->|其它| X6["decidable_elsewhere<br/>未落入自指谱系，交经典层或人工"]
  X1 --> OUT["返回 verdict + diagnosis + annotation + steps"]
  X2 --> OUT
  X3 --> OUT
  X4 --> OUT
  X5 --> OUT
  X6 --> OUT
  OUT --> BND["boundary：五选一是诊断不是判决；<br/>可选步缺输入就 skip，不假装跑过"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class R1 stop
  class OUT out
  class D1,S1,S10,S2,S3,S4,S5,S6,S7,S8,S9,V1,X1,X2,X3,X4,X5,X6 tool
```

## 二、五选一的映射规则（钻的结果 → 一只出口）

```mermaid
flowchart TD
  FV["自指检测的形态"] --> A{"是 fixed_point?"}
  A -->|是| B["良性自指<br/>修正序列收敛到不动点"]
  A -->|否| C{"是 resonance_band 或 liar_cycle?"}
  C -->|是| D["共振带自指<br/>稳定振荡，只判振荡模式"]
  C -->|否| E{"是 diverge?"}
  E -->|是| F["发散真墙<br/>不硬钻"]
  E -->|否| G{"是 annotated_pa?"}
  G -->|是| H["结构性墙（哥德尔型）<br/>注解 P-A，不宣称判定"]
  G -->|否| I{"thesis 与 antithesis 都有?"}
  I -->|是| J["可创生<br/>对立交汇出第三态候选"]
  I -->|否| K["可判在别处<br/>诚实：不硬套"]
  classDef core fill:#e8f4fd,stroke:#4a90d9,stroke-width:2px
  classDef tool fill:#f0f0f0,stroke:#666
  classDef out fill:#e8f8e8,stroke:#2d8c2d,stroke-width:2px
  classDef stop fill:#fdecea,stroke:#c0392b
  class FV,A,C,E,G,I tool
  class B,D,H,J out
  class F stop
  class K stop
```

## 三、对着代码核过的口径与边界

- **输入**（`PORTS['in']`）：`wall`（墙的文本或描述）· `thesis` / `antithesis`（对立两侧）·
  `events`（事件线索，喂区间代数用）。
- **判词**：`benign_selfref` · `resonance_selfref` · `divergent_wall` · `structural_wall` ·
  `creatable` · `decidable_elsewhere` · `input_pending`。
- **六步都留在 `steps` 里**：每步记 `step` / `status`（跑了 / skip）与 `detail`，
  可选步缺输入时 `status` 为 skip 并**写明原因**（`skip——wall 未给` 这类）。
- **`diagnosis` 汇总**：`label`（人话结论）· `mu`（测墙的测度）· `grade`（注解分级）·
  `drill`（钻的结果）· `tension`（看墙的张力）。
- **诚实边界**（`boundary`）：五选一是**诊断不是判决**（只诊断不决策）；
  **共振带自指不等于判真值**；发散真墙 / 结构性墙是**合法输出**（不宣称绕停机 / 哥德尔）；
  可选步缺输入就 skip——诚实标注，不假装跑过。
