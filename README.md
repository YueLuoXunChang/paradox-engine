# paradox-engine · 悖论引擎

> 一个分层逻辑架构的可运行存证——经典逻辑打底，算不清的矛盾当研究对象。
> 立场：**只诊断不决策**——测量它、注解它、报告它，把判断留给使用它的人。
>
> [![tests](https://github.com/YueLuoXunChang/paradox-engine/actions/workflows/test.yml/badge.svg)](https://github.com/YueLuoXunChang/paradox-engine/actions/workflows/test.yml)
> [![license](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](LICENSE)
> [![python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
> [![dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](pyproject.toml)
>
> 🌐 **English**：[README.en.md](README.en.md)

## 〇、命名说明（先回答"它到底是啥"）

仓库叫 `paradox-engine`（悖论引擎），名字取自整个架构里**最具特色的
原创部分**。按本仓库的记账纪律分清两类内容：

- **原创区**（体系自有，无外部来源可标）：第 0 层 MT-MP-TL 骨架
  （点/线程/拓扑）、总控编排（12 题型判类 / 复杂度分级 / 36 键路由 /
  五步流水线）、第 2 层悖论机制（μ 测度 / 注解卡 / 撞墙管线五选一）、
  "只诊断不决策"立场；
- **共识/借鉴区**（外部共识，逐文件标注来源）：第 1 层经典逻辑
  （公共地基，人人都有）、第 3 层冷门逻辑（Belnap / Dung / AGM /
  相干 / 直觉主义，借鉴区记账）。

名字跟着悖论层走，因为撞到不可判定时"测墙→钻墙→创生"的处理方式
是这个架构区别于"又一个逻辑库"的地方。但它的本体是一个**完整的
分层逻辑架构**，悖论只是其中一层（特色层）。

一句话定位：

- 它**是**：一个纯 Python、零依赖的分层逻辑工具集 + 一套可运行的自查体系；
- 它**不是**：AI、概率模型、真理裁决器。它不替你判断对错，只把"矛盾"
  变成可测量、可注解、可追溯的对象。

**它是什么（给陌生读者）**：你把一段"有矛盾的论述 / 自指的句子 / 冲突
的需求"丢给它，它不替你吵架、不消灭矛盾，而是告诉你：这个矛盾有多
尖锐（μ）、是什么类型、能不能稳定存在、哪些立场站得住——全部带依据、
可复核。经典逻辑能算的先算清，算不清的自指和矛盾走"撞墙管线"给
五选一诊断（可判 / 良性自指 / 共振带自指 / 发散真墙 / 可创生）。

本仓库是「落落逻辑体系」（月落寻常原创）的**公开存证容器**：与体系本体
（完整文档库、全量机制库）分离，只放作者挑选后可以公开的内容。不设
版本号、不做推广——让体系的核心主张变成能跑、能测、能对账的实物。

---

## 一、分层架构

```
总控      引擎大脑          判类 / 复杂度 / 路由 / 五步流水线（神经系统）
AI 挂载   工具化封装        引擎函数 = AI 可调用工具（function-calling）
第 3 层   冷门逻辑          Belnap / Dung / AGM / 相干 / 直觉主义（借鉴区）
第 2 层   悖论 / 创生       测度 μ · 注解 · 撞墙管线（体系原创主场）
第 1 层   经典逻辑          命题 / 谓词 / 时序 / 模态 / λ / 图灵机 / 类型
第 0 层   MT-MP-TL 骨架     点 / 线程 / 拓扑 / 操作（自有骨架，结构表达）
```

数据怎么在总控与各层之间流动：

```
输入（中文/公式/结构化线索）
  → 总控：判类（12 题型）→ 复杂度分级（L1/L2/L3）→ 切路由（36 键）
  → 执行：经典层能判的直接判；判不动 → 上卷第 2 层撞墙管线
  → 输出：中文诊断报告 / 结构化 dict，附"依据 + 边界声明"
```

四条贯穿性主张：

- **矛盾当第一公民**：先承认它存在，不假装没有；
- **测量**：悖论强度 μ ∈ [0,1]，一个数，不靠嘴争；
- **白箱**：每个结论带依据，可复核；
- **只诊断不决策**：把判断留给使用者。

---

## 二、快速开始（2 分钟）

### 方式 A：装成包用（pip install）

```bash
# 从 GitHub 安装
pip install git+https://github.com/YueLuoXunChang/paradox-engine.git
# 或本地克隆后安装
git clone https://github.com/YueLuoXunChang/paradox-engine.git
cd paradox-engine && pip install .

# 命令行直接用
paradox-engine --text "产品既要快又要稳"          # 中文诊断报告
paradox-engine --text "这句话是假的" --json       # 结构化输出
paradox-engine --scenarios                       # 场景库（25 个真实场景 + 复核状态）
paradox-engine --scene S01                       # 跑单场景：期望 vs 实际 + 真跑白箱
paradox-engine --text "..." --explain            # 判类依据（主型/副型得分+命中信号+路由）
paradox-engine --review                          # 场景复核模式（逐条给依据+勾选指引）
paradox-engine --stats                           # 场景库统计（题型分布/通过数/复核进度）
```

### 方式 B：不装，直接跑演示

```bash
python demo.py          # 十九步演示（①~⑲ 看完全部能力）
python run_tests.py     # 全量回归（一条命令：37 个测试文件 / 954 项断言）
```

### 命令行选项一览

| 选项 | 作用 |
|---|---|
| `--text "…"` | 输入问题文本，输出中文诊断报告 |
| `--file 路径` | 从文件读问题文本 |
| `--json` | 结构化 JSON 输出（给脚本 / AI 管道用） |
| `--structured '{"A":…}'` | 结构化线索（如 `{"A":"要快","B":"要稳"}`，给 T2 真跑构件用） |
| `--explain` | 判类白箱：主型/副型得分、命中信号、复杂度构成、路由依据 |
| `--scenarios` | 列场景库（真实中文场景 + 期望诊断 + 复核状态） |
| `--scene S01` / `--scene all` | 跑场景对照：期望 vs 实际 + 实际跑了哪些构件 |
| `--review` | 复核模式：逐场景给依据 + 可粘贴的复核结论行 |
| `--stats` | 场景库统计：题型分布 / 对照通过数 / 复核进度 |
| `--tools` | 列出全部可调用工具（function-calling schema） |
| `--demo` | 跑完整演示（同 `python demo.py`） |

### 作为 Python 包 import

```python
# 总控（一段文本进来，诊断报告出去）
from engine.control.controller import run as controller
r = controller({'text': '产品既要快又要稳'})
print(r['report'])

# 直接调悖论测度
from engine.mechanisms.paradox_measure import run as measure
r = measure({'mode': 'mu1', 'wA': 5, 'wNotA': 5})
print(r['mu'])   # 1.0 —— 证据对等，悖论强度最大

# 或调经典层构件
from engine.classical.propositional import run as pl
r = pl({'premises': ['人→会死', '人'], 'conclusion': '会死',
        'mode': 'validity'})
print(r['verdict'])   # valid
```

---

## 三、分层构件详解

每个构件 = 一个自包含的 py 文件：`run(inputs) -> dict` 统一接口 +
PORTS 端口声明 + `__main__` 自测。正式测试为 `test_*.py` 同目录伴随。

### 总控（引擎大脑）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/control/classifier.py | 判类器 + 复杂度 + 路由：12 题型信号表计分 → 主型/副型/置信度 → L1/L2/L3 → ROUTE 36 键（带 reason 白箱） | 自测6+正式72 |
| engine/control/controller.py | 总控五步流水线：判类→复杂度→切路→真跑构件→五查判输出（中文报告+结构化对象） | 自测6+正式43 |

### 第 0 层 · MT-MP-TL 骨架（结构表达，不掺判定）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/skeleton/mtmp.py | 点（异构/自治/变形）+ 线程（方向/速度/汇合/交叉）+ 拓扑 12 形态分类 + 操作（connect/disconnect/replace/fold/spawn） | 自测6+正式42 |

### 第 1 层 · 经典逻辑地基（经典共识，判定/证明/可计算/类型四分法覆盖）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/classical/propositional.py | 命题逻辑：真假/有效性/可满足性/重言式（经典二值） | 自测8+正式15 |
| engine/classical/nd_propositional.py | 命题自然演绎 ND：证明树（经典/直觉主义两套规则） | 自测8+正式16 |
| engine/classical/first_order.py | 一阶谓词：量词/关系/逻辑后承（有限论域展开，可判） | 自测7+正式11 |
| engine/classical/resolution.py | 一阶归结：Skolem 化 + 合一 + 归结链（完整推理机） | 自测6+正式10 |
| engine/classical/equality_tableau.py | 等词替换 + 命题 tableau（反例模型输出） | 自测6+正式14 |
| engine/classical/ltl.py | 时序 LTL：G/F/X/U 沿路径判定（含违约定位） | 自测9+正式14 |
| engine/classical/modal.py | 模态逻辑：□/◇ Kripke 语义（K/T/S4/S5，框架自检） | 自测7+正式14 |
| engine/classical/lambda_calculus.py | λ 演算：β 归约 / 邱奇编码 / Y 不动点（自指的计算形态） | 自测5+正式16 |
| engine/classical/turing_machine.py | 图灵机：模拟 + UTM 自模拟 + 停机不可判定的诚实答案 | 自测6+正式14 |
| engine/classical/stlc.py | 简单类型 λ：类型检查/推导，拦自应用（Curry-Howard） | 自测8+正式15 |
| engine/classical/recursion_theorem.py | Kleene 递归定理：自指程序构造（quine 形态，借数学底座） | 自测5+正式16 |
| engine/classical/decidability_map.py | 可判定片段 + 算术层级：16 条片段逐条标源 + Δ1/Σ1/Π1/Σ2/Π2 引擎承诺 | 自测7+正式51 |

### 第 2 层 · 悖论机制（体系原创主场——矛盾当第一公民）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/mechanisms/paradox_measure.py | 悖论强度 μ ∈ [0,1]：四分支（证据权重/自指/层级/熵） | 自测1 |
| engine/mechanisms/paradox_annotate.py | 悖论注解：8 字段卡（ID/LV/POS/SRC/CT/EF/ST/AN）+ P-A/P-B/P-C 分级 | 自测6 |
| engine/mechanisms/converge_check.py | 收敛判定：压缩映射/有限步/渐进/振荡四分支 | 自测6 |
| engine/mechanisms/selfref_fixpoint.py | 递归修正×自指检测：共振带三态（不动点/共振带/发散）——钻墙主力 | 自测7+正式23 |
| engine/mechanisms/boundary_paradox.py | 边界悖论判定：墙=边界（张力/划设即撤销/重生路径） | 自测4+正式20 |
| engine/mechanisms/observer_bypass.py | 悖论全程自反旁路：主链不停，旁路观察+注解（架构级免疫） | 自测4+正式22 |
| engine/mechanisms/counterpoint_gen.py | 对位创生第三态：对立交汇 → 候选+依据（同向两全/反向共振/交叉桥） | 自测5+正式21 |
| engine/mechanisms/wall_pipeline.py | 撞墙管线 A：测墙→注解→钻墙→看墙→旁路→创生 → 五选一诊断 | 自测5+正式24 |

### 第 3 层 · 冷门逻辑（按真实痛点选，外部共识归借鉴区——六件齐）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/cold/belnap_four.py | Belnap 四值（T/F/两者/皆非）：矛盾取"两者"不爆炸（借鉴 1977） | 自测7+正式30 |
| engine/cold/dung_framework.py | Dung 论证框架：冲突场哪些立场站得住（grounded/preferred，借鉴 1995） | 自测5+正式21 |
| engine/cold/truth_revision.py | Gupta-Belnap 真值修正：修正序列稳定/周期振荡（共振带的学界锚点，1993） | 自测6+正式19 |
| engine/cold/agm_revision.py | AGM 信念修正 + 非单调默认：新信息来了旧结论还成立吗（1985/Reiter） | 自测8+正式48 |
| engine/cold/relevance_logic.py | 相干逻辑：前提结论是否共享变量——真冲突 vs 话术冲突（1975） | 自测8+正式43 |
| engine/cold/intuitionistic_logic.py | 直觉主义：Kripke 求值 + 反模型搜索 + 经典 vs 构造性对照（1959） | 自测8+正式43 |

### AI 挂载层

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/ai/tools.py | 全量构件封装为 function-calling 工具（schema 从 PORTS 自动生成）+ call_tool 分派 | 自测11+正式49 |
| engine/ai/freeze_tool_schema.py | 工具协议冻结：契约快照 + 调用方文档，自动生成防漂移 | 正式21 |
| engine/ai/ai_scenarios.py | 真实场景端到端：论证矛盾检查 / 学科题目建模 | 两场景跑通 |

### 场景库（期望 vs 实际的对照与复核）

| 文件 | 一句话 | 测试 |
|---|---|---|
| engine/scenarios/scenarios.py | 25 场景注册表（T1-T12 每题型 ≥2）：输入+期望诊断+实际对照+复核状态 | 自测5组 |

---

## 四、核心机制原理

### 判类：12 题型（T1-T11 + 诚实兜底）

判类器对输入文本做信号表计分（命中词 → 加权得分），输出主型/副型/
置信度。11 个定义题型：

| 型 | 名称 | 型 | 名称 |
|---|---|---|---|
| T1 | 命题真值 | T7 | 对立交汇 |
| T2 | 论证矛盾 | T8 | 证据冲突 |
| T3 | 关系结构 | T9 | 学科题目 |
| T4 | 演化过程 | T10 | 定义辨析 |
| T5 | 知识更新 | T11 | 假设检验 |
| T6 | 自指/深层 | T12 | **未分类（兜底）** |

**T12 是诚实设计**：一个信号都不命中时，引擎返回"未分类"（置信度 low），
而不是硬塞一个题型。承认"不知道"，是这个引擎的第一反应。

### 悖论测度 μ（四分支）

| 分支 | 适用 | 公式 |
|---|---|---|
| mu1 证据权重（默认） | 两边都有证据 | μ = 1 − \|wA−wNotA\| / (wA+wNotA+ε) |
| mu2 自指 | X = ¬X | 直接取 1（完全悖论） |
| mu3 层级 | 跨层真值 | μ = \|τ_L1 − τ_L2\| |
| mu4 熵 | 不确定性视角 | μ = 香农熵 H(p)，p = wA/(wA+wNotA+ε) |

### 悖论注解（8 字段卡）

检测到 A∧¬A 共存后，**不解决、不消除**，生成一张 8 字段注解卡
（ID/LV/POS/SRC/CT/EF/ST/AN）并按来源分级：
公理层 → P-A（结构性，最高）；运行期 → P-B；观察者 → P-C。

### 撞墙管线（第 1 层判不动时上卷）

```
经典层判不动（不可判定/自指）
  → 测墙（μ + 收敛判定）
  → 注解（8 字段卡）
  → 钻墙（递归修正×自指检测：不动点/共振带/发散三态）
  → 看墙（边界悖论：这堵墙是死路还是可研究的边界）
  → 旁路（观察线程并行，主链不停）
  → 创生（对位交汇 → 第三态候选）
  ⇒ 五选一诊断：可判 / 良性自指 / 共振带自指 / 发散真墙 / 可创生
```

墙没有被穿过，也没有被假装不存在——它被**定位、分类、写成报告**。

### 总控五步

一段中文进来：判类 → 复杂度分级（L1 简单问题单机制直出 / L3 复杂问题
全管线，不简化）→ 切路由（36 键，每键带 reason）→ 真跑构件 → 五查判输出。
最小充分原则：简单问题绝不复杂化。

---

## 五、设计哲学（为什么"只诊断不决策"）

很多系统遇到矛盾的第一反应是"修掉它"——但这常常是**在证据不足时偷偷
做决定**。paradox-engine 换了个顺序：

```
矛盾出现 → 测量（μ） → 注解（卡） → 报告（白箱）→ 判断权交还使用者
```

诊断与决策分离：引擎负责"如实描述矛盾"，使用它的系统/人负责"拿它
怎么办"。这样矛盾不会被消灭，也不会被无视——它成为可以被讨论、比较、
追溯的对象。

三个设计约定贯穿所有机制：

- **诚实**：输入缺什么就报告"还差什么"（`*_pending`），不瞎猜不硬判；
  无信号命中 → T12 未分类；算不动 → `undecided`；一阶半可判段的
  `undetermined` 是合法输出，不许硬截断；
- **拦截**：非法输入诚实报告，不产生假值；
- **白箱**：advice 说明依据，重要路径可回溯。

### 为什么分层

- **第 1 层经典逻辑**：别人一看就懂、可靠（经典共识）——证明"这不是玄学"；
- **第 2 层悖论**：独特的在下一层——经典层撞到不可判定 → 上卷 →
  五选一诊断，把"墙"从终点变成状态机的一格；
- **外部借鉴明确记账**：Belnap / Dung / AGM / 相干 / 直觉主义全部标注
  来源归借鉴区，不混原创区（落落三问纪律）。

---

## 六、工程纪律与测试状态

### 不变式测试（每条对应一次真实踩坑）

| 不变式 | 防什么 |
|---|---|
| 引用 `engine.*` 的模块必须做 sys.path 引导 | 顶层包名撞车（别家 editable 包装成 `engine` 静默顶替） |
| pyproject packages 覆盖全部含 .py 的子目录 | 打包漏子包（pip 装出来少模块） |
| ROUTE 出现的构件名必须有适配器 | 路由画饼（写了构件却没适配器） |
| CLI/demo 入口调用控制台自愈 | GBK 控制台打 emoji 直接 UnicodeEncodeError |
| 门面文件无版本号 + `__version__=0.1.0` | 版本号乱标（死命令：真发布才推进） |
| 发布面残留扫描（本机路径/密钥形态/私有名） | 内部信息泄漏进公开仓库 |
| README 数字与实测对账 | 门面数字漂移（说谎从文档开始） |

### 测试状态

- **954 项正式断言全过**（37 个测试文件），覆盖全部
  机制构件与总控/场景/AI 工具层；
- **一条命令跑全量回归**：`python run_tests.py`（发现 + 运行 + 汇总；
  任一文件失败即非零退出——CI 与本地同一入口）；
- **安装路径已验证**：`python verify_install.py` 真构建 wheel → 临时 venv
  装 → 跑安装后的 `paradox-engine --text/--json/--file/--tools` 与 import
  接入（CI 每次也跑这一档）；
- CI：`.github/workflows/test.yml`（Python 3.9 / 3.12 上跑回归 + 演示 +
  CLI 冒烟 + 安装验证）；
- 每个构件自包含：`python engine/<层>/<名>.py` 跑自测（机制自身验证），
  `python engine/<层>/test_<名>.py` 跑正式测试；
- 演示：`python demo.py` 十九步全过；真实场景端到端：
  `python engine/ai/ai_scenarios.py`；场景库对照：25 场景（T1-T12 每个
  题型 ≥2）（`python engine/scenarios/scenarios.py`）；
- 零第三方依赖，纯 Python 标准库（≥3.9）；
- **行尾统一 LF**（不变式测试守着）+ **控制台自愈**（CLI/demo 入口全走，
  防 GBK 控制台 UnicodeEncodeError）；

### AI 挂载：29 个可调用工具

全部引擎构件已封装为 function-calling 工具（schema 从 PORTS 自动生成，
零手工漂移）。工具协议已冻结：契约快照 `engine/ai/tool_schema_frozen.json`
+ 调用方文档 `docs/tool_schema.md`，`test_tool_contract.py` 防漂移——
契约改了必须重新冻结并记账，不能静默改。AI 拿到工具清单即可调用整个
引擎（`--tools` 查看）。

### 没写完的与不做的（诚实清单）

- **场景人工复核 4/25**：25 场景机器对照全过，但作者人工复核只完成
  4 个——按纪律，复核没做完之前**误判率不报数**（进度见 `--stats`）；
- **阶段 7 按需未做**：撞墙管线 B/C 支线、多轮状态、Web/API/LLM 对接
  （待授权）——有真实痛点才上，不硬写；
- **三个未来姿态的深化点未做**：文本自动抽冲突、文本自动建拓扑、
  与真实 LLM 对接（见 docs/ROADMAP.md §6.1）；
- **体系本体不在此仓库**（完整机制库、文档库）；这里只放作者挑选后
  可以公开的部分；
- 本项目**不宣称解决任何哲学/逻辑学争议**，也不宣称绕过图灵停机/哥德尔
  不完备（那是定理）。它做两件事：经典能算的算清；算不清的矛盾——
  测量、注解、诚实报告，把判断留给使用者。

### 关于更新（先说清，不画饼）

- 本仓库**会不定期更新**：随作者整理进度逐步放入新的精选内容（机制、
  文档、演示），不设时间表；
- 体系本体的大部分内容（完整机制库、文档库）**尚未公开**；后期**或许**
  会以新的仓库形式公开更多逻辑架构与机制——是否公开、何时公开、公开
  多少，均未定，以作者届时发布为准；
- 想跟踪变化可以 watch 本仓库。没有群、没有频道、没有其他发布渠道——
  存证仓库，保持安静。

---

## 七、术语表（体系黑话 → 人话）

| 术语 | 意思 |
|---|---|
| 墙 | 不可判定性的边界——停机问题、哥德尔不完备这类定理划出的界线 |
| 撞墙 | 经典逻辑判不动、碰到墙的那一刻（不是错误，是被记录的状态） |
| 撞墙管线 | 撞墙后的诊断流水线：测墙→注解→钻墙→看墙→旁路→创生 |
| 共振带 | 自指修正序列每步翻转但**稳定振荡**（说谎者句周期 2 是教科书结论） |
| 钻墙 | 用递归修正去探自指结构：收敛到不动点 / 共振带振荡 / 发散 |
| 看墙 | 把墙当研究对象：这堵墙是死路，还是可划设/可撤销/可重生的边界 |
| 对位创生 | 两个对立命题交汇处生成第三态候选（不是二选一） |
| MT-MP-TL | 落落体系的自有骨架：点 / 线程 / 拓扑 / 操作（代号源自体系本体） |
| 只诊断不决策 | 引擎报告矛盾的所有事实，判断权永远在使用者手里 |
| 存证 | 这个仓库的存在方式：不是产品发布，是把体系主张变成可复核的实物 |

---

## 八、来源、协作与许可

- **概念原创**：月落寻常（落落），"落落逻辑体系"作者。本仓库内容由其
  从体系中**精选**并授权公开；体系本体（完整文档库/全量机制库）不在本仓库。
- **AI 强力辅助**：实话实说——本仓库的工程化实现（代码、测试、文档、
  demo 编排）**大部分工作量由 AI 完成**；概念与设计取向来自作者
  （落落），取舍与最终决策由作者拍板。AI 干活最多，作者掌舵。
  分层的逻辑主张（第 1 层经典能算的算清、第 2 层矛盾当第一公民、
  只诊断不决策）为作者原创方向。
- **外部借鉴**：代码中借用的经典共识（如 Belnap 四值、Dung 论证框架、
  AGM 信念修正 1985、Reiter 默认逻辑、Anderson-Belnap 相干逻辑 1975、
  直觉主义（Brouwer/Heyting/Kripke 1959）、经典逻辑各构件）均在对应文件
  docstring 标注来源，归借鉴区，不混原创区。
- 代码中的公式卡引用（`docs/formulas/*.md`）为概念说明，可能随仓库演化
  补齐。
- **许可**：**MPL-2.0（Mozilla Public License 2.0）**——允许商用、允许修改、
  欢迎协作（fork / 提 PR / 一起改）；改了哪个源文件，那个文件保持 MPL
  开源。[LICENSE](LICENSE) 为纯 MPL-2.0 全文；版权/署名/AI 协作声明见
  [NOTICE](NOTICE)。

---

## 九、给贡献者

想加一个机制？看现有文件格式（PORTS + run + `__main__` 自测），
先在小处跑通再扩展。本仓库纪律：

- 每个机制必须自包含、可独立运行；
- 非法输入必须诚实拦截，不产生假值；
- 只诊断不决策，不替使用者下结论；
- 改完跑 `python run_tests.py` 全绿再提交（CI 同款入口）。

更多见 [CONTRIBUTING.md](CONTRIBUTING.md)（五条硬纪律 + 发布面红线 +
自检清单）。
