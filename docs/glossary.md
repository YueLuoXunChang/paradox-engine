# 术语表（glossary）

> 用途：读 README、工具契约、诊断报告时对不上号，查这里。
> **口径**：写的是"**引擎自己怎么说、怎么办**"——术语指向实现，不是外部百科的复述；
> 借来的概念（外部共识）逐条标「借鉴区」，与落落原创区分开记。
> **维护**：改术语要同步这张表；`engine/test_glossary.py` 守着几条硬约束
> （表里提到的构件必须真实存在、T1–T12 全覆盖、工具数与注册表一致、README 中英都指向本表）。
> 关联：构件参考 `docs/components.md`（自动生成）· 工具契约 `docs/tool_schema.md`（自动生成）·
> 分层路线 `docs/ROADMAP.md`。

## 一、分层（layers）

| 术语 | English | 引擎里的意思 | 实现入口 |
|---|---|---|---|
| 第 0 层 · MT-MP-TL 骨架 | L0 skeleton | 点 / 线程 / 拓扑 / 操作——只做**结构表达**，不掺判定 | `engine/skeleton/mtmp.py` |
| 第 1 层 · 经典逻辑层 | L1 classical | 命题 → 谓词 → 时序 → 模态（地基，经典共识） | `engine/classical/` |
| 第 2 层 · 悖论/创生层 | L2 paradox | 悖论测度·注解·递归修正 + 对位创生（引擎主场） | `engine/mechanisms/` |
| 第 3 层 · 冷门逻辑层 | L3 cold | 次协调 / Dung / 非单调 / 相干 / 直觉主义…（按痛点选） | `engine/cold/` |
| AI 挂载层 | AI mounting | 构件函数 = AI 可调用工具（**36 件**，契约冻结） | `engine/ai/tools.py` |
| 总控 | controller | 判类 → 复杂度 → 切路 → 真跑 → 判输出（五步） | `engine/control/controller.py` |
| 工作台 | workshop | 一批材料 → 会话台账 → 简报/看板/对账 | `engine/control/session.py` |

## 二、判类与路由（classifier / routing）

### 2.1 题型 T1–T12

| 型 | 中文名 | English | 认什么（信号举例） |
|---|---|---|---|
| T1 | 命题真值 | propositional truth | 所有/都/任何/所以/真假/成立 |
| T2 | 论证矛盾 | argumentative conflict | 既要…又要/一方面…另一方面/矛盾/打架/冲突 |
| T3 | 关系结构 | relational structure | 支持/反对/依赖/包含/攻击/关系 |
| T4 | 演化过程 | evolution / process | 逐渐/最终/越来越/演化/衰减/增长 |
| T5 | 知识更新 | belief update | 原来以为…现在发现/例外/黑天鹅/推翻旧结论 |
| T6 | 自指/深层 | self-reference | 这句话/本命题/不可证/说谎者/递归 |
| T7 | 对立交汇 | opposite-pair meeting | 自由与秩序/个体与集体/要快与要稳/兼得 |
| T8 | 证据冲突 | evidence conflict | 证据/数据显示/实验/报告/样本/相互矛盾的数据 |
| T9 | 学科题目 | discipline problem | 建模/机制/多线/通路/系统/理论 |
| T10 | 定义辨析 | definition analysis | 区别/不同/算不算/什么算/边界 |
| T11 | 假设检验 | hypothesis testing | 靠不靠谱/置信/显著/样本/调查/抽样/比例 |
| T12 | **未分类** | unclassified | 一条信号都没命中时**诚实返回**，不硬塞题型 |

> T12 不是第 12 个"正经题型"，而是"没归上类"的诚实出口：它照样估复杂度、走最小管线。

### 2.2 复杂度与路由

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 复杂度档 L1/L2/L3 | complexity level | 按结构打分：≤3 → L1 · ≤7 → L2 · >7 → L3；另有规则修正（学科题信号密集时上调，标注为规则产物） |
| 路由 id | route id | `R{型号}-{档}`，如 `R2-L2`（T2 型走 L2 档的管线） |
| 管线 | pipeline | 这一档实际要跑哪些构件（路由表给出），哈希结构才升级骨架 |
| 主型 / 副型 / 置信度 | main / sub type, confidence | 主型是最高分题型；副型是次高；置信度看分差 |
| 判类命中信号 | matched signals | 命中的词表条目（判类白箱 `--explain` 会列出来，便于复核） |

## 三、悖论与创生（第 2 层）

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 悖论测度 μ | paradox measure | 矛盾强度 ∈ [0,1]，四分支配：`mu1` 证据权重型 `1−\|wA−wNotA\|/(wA+wNotA+ε)` · `mu2` 自指型（X=¬X 取 1）· `mu3` 层级型 `\|τ_L1−τ_L2\|` · `mu4` 熵权型 `H(p)/log2`；优先级 mu2 > mu3 > mu4 > mu1 |
| 注解卡 | annotation card | 给矛盾生成 8 字段卡；分级 `grade ∈ {P-A, P-B, P-C}`（来源 axiom / runtime / observer，A 最高） |
| 共振带 | resonance band | 递归修正既不收敛也不发散、稳定振荡的状态——自指的"合法驿站" |
| 自指三态 | self-reference states | `fixed_point`（不动点）/ `resonance_band`（共振带）/ `diverge`（发散）；说谎者句另出 `liar_cycle`（每步翻转） |
| 边界悖论 | boundary paradox | 墙=边界：划设 → 张力 → 撤销 → 重生路径 |
| 对位创生 | counterpoint generation | 对立交汇出**第三态候选 + 依据**（不是二选一） |
| 全程自反旁路 | observer bypass | 主链不停，旁路观察 + 注解 + 注入（架构级免疫） |
| 撞墙管线（A） | wall pipeline | 测墙 → 注解 → 钻墙 → 看墙 → 旁路 → 创生，输出**五选一诊断**：可判 / 良性自指 / 共振带自指 / 发散真墙 / 可创生 |

## 四、冷门逻辑（第 3 层，外部共识归借鉴区）

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 四值（Belnap） | four-valued | 值 = 真 / 假 / **两者** / 皆非；矛盾取"两者"不爆炸（次协调语义地基） |
| 三值 K3 / Ł3 | three-valued | 值 = 0 / ½ / 1，设计值只有 1；**K3** 的 ½ 是"未知"（无重言式），**Ł3** 的 ½ 是"中间真值"（有重言式但无排中律） |
| grounded / preferred / stable | Dung semantics | 站得住的立场集：grounded 唯一最小 · preferred 极大可接受 · stable 把集外都攻击到（**可能一个都没有**） |
| 争议集 | conflict pairs | 互相攻击的对（打成一团"的核） |
| AGM 三操作 | AGM operations | 扩张 / 收缩 / 修正；新信息与旧信念冲突时按**最小放弃**收缩（可指定信念度） |
| 可废止 / 阻断 | defeasible / blocked | 默认结论不是绝对真：辩护被推翻即阻断 |
| 默认逻辑·扩展 | default logic, extension | 默认理论 (W, D) 的 Γ **不动点**；一个理论可能**没有**扩展，也可能有多个（歧义） |
| 怀疑论 / 轻信论结论 | skeptical / credulous | 每个扩展都成立 vs 只在部分扩展成立 |
| 相干 / 不相干 | relevant / irrelevant | 前提与结论是否共享变量（区分真冲突与话术冲突） |
| 修正序列 | revision sequence | 真值在序列里如何收敛（稳定 / 周期振荡——共振带的学界锚点） |
| 构造性立场 | constructive stance | 直觉主义：Kripke 反模型；排中律、双重否定消去、Peirce 律都不成立 |
| 区间代数（Allen） | interval algebra | 事件之间的**定性时序**：13 个基本关系（先于／相接／重叠／开始于／包含于／结束于／同时 + 逆）+ 复合 + 路径一致性；报"没发现冲突"不等于有解 |
| 描述逻辑 ALC | description logic ALC | 概念描述语言（⊓ ⊔ ¬ ∃R.C ∀R.C）+ 本体公理（`C ⊑ D` / `C ≡ D`）：判概念可不可满足、甲包不包含乙、相不相交、整张本体的概念层级 |
| 表列法 / 撞车 | tableau / clash | 把"这个概念能不能成立"化成"展开处处撞车吗"：交拆开、并分两支、∃ 造后继、∀ 发给后继；同现 A 与 ¬A（或 ⊥）就叫撞车，该支关闭 |
| 子集阻塞 | subset blocking | 某节点的标号被**祖先**标号装下就不再为它造后继（祖先顶上这个节点）——循环本体（`A ≡ ∃R.A`）靠这个收口；方向反了就是假阻塞 |
| TBox / ABox | TBox / ABox | 本构件只做**概念层 TBox**（公理是概念之间的包含）；**不做 ABox**（"张三属于某概念"这类个体断言） |

## 五、可计算性与判定（decidability）

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 可判定 Δ1 | decidable (Δ1) | 有算法在有限步内给是/否 → 引擎**给结论** |
| 半可判定 Σ1 | semi-decidable (Σ1) | 只有"是"这一侧可枚举 → 引擎**枚举到才说是**，枚举不到不给否 |
| Π1 / Σ2 / Π2 | — | 更高层：引擎**不承诺**结论，只做诚实报告 |
| 可判定片段 | decidable fragment | 把语言限制到某个片段后判定性回来了（如一元谓词、Presburger 算术） |
| 墙体地图 | wall map | 可查的"什么问题算得清、算不清到哪一层、有没有可判替身"的参考文献表 |
| 参考表 ≠ 判定过程 | reference table vs decision procedure | 地图回答"这一类问题学界结论是什么"，**不替你判某个具体式子** |
| `size_limit` | scale limit | 规模超上限——**不是**判定结论（式子本身可能很可判） |
| `undecided` | undecided | 搜索不完备/算不动——**≠ 不可满足、≠ 命题为假** |
| `input_pending` | input pending | 缺参数或形状不对——诚实拦截，不编输入 |

## 六、工作台与会话（workshop）

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 会话台账 | session ledger | 一个 JSON 文件：逐条材料 + 引擎自己的诊断，跨命令记住前文 |
| 轮次 | turn | 台账里的一条材料（`--add` / `--add-file` 逐段加入） |
| 批次汇总 | overview | 按**引擎自己的标签**分组计数（判类/复杂度/置信度/构件状态/墙事件）——只统计，不做相似度聚类 |
| 复核 | review | 人对场景的判定：`checked` 与 `review` 两个字段，**只能作者落笔** |
| 复核落笔 | mark | `--mark S05 --verdict ok/wrong/edge/pending`：把结论写回场景表（只改那两个字段） |
| 复核依据 | review evidence | 复核时的期望 vs 实际 + 命中信号，记进台账（**不**替作者改 `checked`） |
| 线索 | clues | 构件要的结构化输入（如 A/B 两方、wA/wNotA）；建议器只给建议、不产生逻辑式 |
| 工作单 | pending list | 还欠线索的轮次 + 可粘贴命令，欠的键留 `<待填>` 空位 |
| 对账 | reconcile | 会话里记的依据 vs 场景表落的笔，分三类报差异（两边都不改） |
| 分批与续跑 | chunking / resume | 大材料分块跑、有进度、可续跑（被上限挡下的段不算处理过） |
| 隐私导出 | redacted export | 台账导出时材料原文只留字数与开头（便于给别人看） |

## 七、工程口径（conventions）

| 术语 | English | 引擎里的意思 |
|---|---|---|
| 只诊断不决策 | diagnose, do not decide | 引擎不替使用者/作者下结论（输出都带 `boundary` 声明随行） |
| 借鉴区 | borrowed section | 外部共识（AGM / Dung / Belnap / Presburger 等）逐条标源，不混进原创区 |
| 不变式 | invariant | 把"声明"变成会失败的断言（数字漂了、索引漏了、示例跑不动 → 回归直接红） |
| 漂移 | drift | 文档/清单与实际不符（典型：README 数字、索引漏登记——靠不变式守） |
| 发布面红线 | public-face red lines | 公开仓不许出现的东西（本机路径 / 身份信息 / 私有档案名与章节号 / 密钥 / 专业建议题材 / 版本号） |
| 私有引用清点 | private-reference audit | 只列不改地扫一遍私有档案引用（目标：0 处） |
| 工具契约冻结 | frozen tool contract | 工具名与参数名是对外契约：改了要重新冻结快照并在 CHANGELOG 记账 |
| 诚实拦截 | honest interception | 缺参/超限/算不动 → 明确报为什么，**不假装有结论** |
| 冒烟级基准 | smoke-level benchmark | 只看数量级变化，不对外报数 |

## 八、英文速查（按英文排序）

| English | 中文 | 一句话 |
|---|---|---|
| annotation card | 注解卡 | 矛盾的 8 字段卡 + P-A/B/C 分级 |
| boundary paradox | 边界悖论 | 划设 / 张力 / 撤销 / 重生 |
| complexity level | 复杂度档 | L1 / L2 / L3 |
| conflict pairs | 争议集 | 互相攻击的对 |
| counterpoint generation | 对位创生 | 对立交汇出第三态候选 |
| decidability | 可判定 | 有算法给是/否 |
| default logic extension | 默认逻辑扩展 | Γ 不动点 |
| description logic ALC | 描述逻辑 ALC | 概念包含 / 本体分类（表列 + 子集阻塞） |
| defeasible | 可废止 | 有反例即阻断 |
| diagnose, do not decide | 只诊断不决策 | 引擎不替人下结论 |
| drift | 漂移 | 文档与实际不符 |
| four-valued (Belnap) | Belnap 四值 | 矛盾取"两者" |
| grounded / preferred / stable | Dung 三语义 | 立场集的三种口径 |
| honest interception | 诚实拦截 | 不假装有结论 |
| invariant | 不变式 | 声明变成会失败的断言 |
| model checking | 模型检查 | 给定结构上跑 CTL |
| paradox measure μ | 悖论测度 | 矛盾强度四分支 |
| quantifier elimination | 量词消去 | Presburger 判定的做法 |
| resonance band | 共振带 | 振荡稳定态 |
| route id | 路由 id | `R2-L2` 这样的档位标识 |
| semi-decidable | 半可判定 | 只一侧可枚举 |
| skeptical / credulous | 怀疑论 / 轻信论 | 每个扩展都成立 / 只在部分成立 |
| three-valued (K3 / Ł3) | 三值 | 未知 vs 中间真值 |
| wall pipeline | 撞墙管线 | 五选一诊断 |
| workshop ledger | 工作台账 | 逐条材料 + 诊断 |

---

*维护约定：本表由人工维护（不是自动生成）；数字类声明（工具件数、题型数）有不变式守着。*
