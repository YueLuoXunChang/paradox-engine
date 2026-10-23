# paradox-engine · 悖论引擎

> 把"矛盾"当成研究对象来工程化的最小引擎。
> 立场：**只诊断不决策**——测量它、注解它、报告它，把判断留给使用它的人。
>
> [![tests](https://github.com/YueLuoXunChang/paradox-engine/actions/workflows/test.yml/badge.svg)](https://github.com/YueLuoXunChang/paradox-engine/actions/workflows/test.yml)
> [![license](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](LICENSE)
> [![python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
> [![dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](pyproject.toml)
>
> 🌐 **English**：[README.en.md](README.en.md)

**paradox-engine** 是一个小而专注的悖论/矛盾检测引擎原型，从"落落逻辑体系"
（月落寻常原创）中精选出的核心机制构成。本仓库是**独立开源容器**：只包含
作者挑选后可以公开的内容，与体系本体（文档库、完整机制库）分离。

> **它是什么（一句话给陌生读者）**：一个纯 Python 写的逻辑小工具集——
> 你把一段"有矛盾的论述 / 自指的句子 / 冲突的需求"丢给它，它不替你
> 吵架、不消灭矛盾，而是告诉你：这个矛盾有多尖锐（μ）、是什么类型、
> 能不能稳定存在、以及哪些立场站得住——全部带依据、可复核。
> 经典逻辑能算的先算清（命题/一阶/时序/模态/λ/类型），算不清的自指
> 和矛盾走"撞墙管线"给五选一诊断（可判/良性自指/共振带自指/发散真墙/
> 可创生）。零第三方依赖，`python demo.py` 十六步看完所有能力。

---

## 一、这个项目主张什么（30 秒）

| 别的做法 | paradox-engine 的做法 |
|---|---|
| 消灭矛盾、回避矛盾、假装没有 | **矛盾当第一公民**：先承认它存在 |
| "这算不算悖论"靠嘴争 | **测量**：悖论强度 μ ∈ [0,1]，一个数 |
| 给结论不给过程 | **白箱**：每个结论带依据，可复核 |
| 顺手替用户做决定 | **只诊断不决策**：把判断留给使用者 |

一句话：**我们不解决悖论——我们把它变成可测量的、可注解的、可追溯的对象。**

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
paradox-engine --text "产品既要快又要稳"
paradox-engine --text "这句话是假的" --json      # 结构化输出
paradox-engine --scenarios                      # 场景库（28 个真实场景 + 复核状态）
paradox-engine --scene S01                      # 跑单场景：期望 vs 实际 + 真跑白箱
paradox-engine --text "..." --explain          # 判类依据（主型/副型得分+命中信号+路由）
paradox-engine --text "既要快又要稳" --structured '{"A":"要快","B":"要稳","wA":5,"wNotA":5}'
                                                # 给结构化线索：构件才真跑（线索缺什么用 --suggest 看）
paradox-engine --text "既要快又要稳" --suggest  # 结构化线索建议（含可粘贴命令，建议不自动应用）
paradox-engine --review                        # 场景复核模式（逐条给依据+落笔命令）
paradox-engine --review --board --pending-only # 复核看板：只看待复核（只读，落笔仍是你的判断）
paradox-engine --review --packet               # 复核包：待复核逐个排好（原文+依据+落笔命令），一屏批阅
paradox-engine --review --packet --packet-out 复核包.md   # 同上，写成 Markdown（默认不覆盖）
paradox-engine --session 会话.json --review --scene all   # 复核依据记进会话台账
paradox-engine --mark S05 --verdict ok         # 复核落笔：结论写回场景表
paradox-engine --stats                         # 场景库统计（题型分布/通过数/复核分布/混淆矩阵/覆盖缺口）

# 多轮会话：一批材料一条条看，跨命令记住前文
paradox-engine --session 会话.json --add "产品既要快又要稳" --clues   # 顺手记下线索建议
paradox-engine --session 会话.json --add-file 材料.md   # 整篇材料逐段诊断（按空行分段）
paradox-engine --session 会话.json --add-file 大材料.md --chunk 20   # 分块跑：有进度、可续跑
paradox-engine --session 会话.json --add-file 大材料.md --from-seg 41 # 接着上次没处理的段
paradox-engine --session 会话.json --add "这句话是假的" --structured-json '{"sentence":"liar"}'
paradox-engine --session 会话.json --revise "¬Q" --beliefs "P→Q,P"   # 新信息 → 信念修正
paradox-engine --session 会话.json --session-state                # 汇总：轮次/题型/墙清单/信念
paradox-engine --session 会话.json --overview                     # 批次汇总：判类/复杂度/置信度/构件状态
paradox-engine --session 会话.json --pending                      # 欠线索工作单（可粘贴命令 + 待填空位）
paradox-engine --session 会话.json --progress                     # 复核进度快照（与上次比：又复核了哪些）
paradox-engine --session 会话.json --brief                        # 一页简报（状态/欠什么/复核到哪/下一步）
paradox-engine --session 会话.json --reconcile                    # 对账：会话记的依据 vs 场景表标记（只报差异）
paradox-engine --session 会话.json --export 台账.md               # 导出 Markdown 诊断台账
paradox-engine --session 会话.json --export 台账.md --redact      # 隐私导出：材料原文只留字数与开头
paradox-engine --repl --session 会话.json     # 交互台：普通文字＝材料当场诊断，斜杠命令看汇总/简报/场景

# 或作为 Python 包 import
from engine.control.controller import run as controller
r = controller({'text': '产品既要快又要稳'})
print(r['report'])
```

### 方式 B：不装，直接跑演示

```bash
# 克隆后，在仓库根目录
python demo.py          # 二十步演示
python -m engine.cli --tools          # 看 41 件工具清单
python -m engine.cli --call asp --args '{"program": "p :- not q. q :- not p."}'   # 直接调一个工具（不经判类路由）
python -m engine.cli --call presburger --args '{"formula": "∀x x + 1 > x"}' --json
python run_tests.py     # 全量回归（一条命令：78 个测试文件 / 2227 项断言）
```

`demo.py` 演示二十件事（①②③ 悖论三件套 → ④-⑩ 经典逻辑地基 → ⑪ 撞墙管线 → ⑫ 总控五步 → ⑬ MT-MP-TL 骨架 → ⑭ 冷门逻辑 → ⑮ AI 挂载 → ⑯ 数学底座 → ⑰ 冷门补完 → ⑱ 构造性立场 → ⑲ 墙的精确地图 → ⑳ 工作台）：

| 步骤 | 演示 | 层 |
|---|---|---|
| ① 悖论测度 | 五五开证据 → μ = 1.0（强悖论）——矛盾多尖锐，一个数说清 | 第 2 层 |
| ② 悖论注解 | 矛盾拿一张 8 字段"身份证" + 分级（P-A/P-B/P-C） | 第 2 层 |
| ③ 收敛判定 | 迭代会不会停（压缩映射 → 收敛） | 第 2 层 |
| ④ 命题逻辑 | 三段论有效性 / 反例 / 排中律 | 第 1 层 |
| ⑤ 一阶谓词 | ∀/∃ 量词推理（有限论域展开判定） | 第 1 层 |
| ⑥ 时序 LTL | G/F/U 演化性质 + 违约定位 | 第 1 层 |
| ⑦ 模态逻辑 | □/◇ Kripke 语义（K/T/S4/S5） | 第 1 层 |
| ⑧ λ 演算 | β 归约 / Y 不动点 / 邱奇编码（自指计算形态） | 第 1 层 |
| ⑨ 图灵机 | 模拟 + 停机问题不可判定的诚实答案 | 第 1 层 |
| ⑩ STLC 类型 | 类型拦住自应用（类型正确 ⇒ 终止）——与 ⑧ 对照 | 第 1 层 |
| ⑪ 撞墙管线 | 说谎者句 → **五选一诊断**（测墙→注解→钻墙→看墙→旁路→创生） | 第 2 层 |
| ⑫ 总控五步 | 一段中文 → 判类→复杂度→切路→执行→判输出（中文诊断报告） | 总控 |
| ⑬ MT-MP-TL 骨架 | 多线程并行→汇合 + 拓扑分类（结构表达，不掺判定） | 第 0 层 |
| ⑭ 冷门逻辑 | 矛盾取"两者"（Belnap 四值）+ 立场分析（Dung 论证框架） | 第 3 层 |
| ⑮ AI 挂载 | 全量引擎函数 = AI 可调用工具（function-calling schema 自动生成） | 挂载 |
| ⑯ 数学底座 | 自指程序构造（Kleene 递归定理）+ 真值修正（Gupta-Belnap——共振带学界锚点） | 借鉴 |
| ⑰ 冷门补完 | 信念修正/非单调（AGM：黑天鹅撤销旧结论）+ 相干逻辑（真冲突 vs 话术冲突） | 第 3 层 |
| ⑱ 构造性立场 | 直觉主义：Kripke 反模型（排中律为何非构造有效）+ 经典 vs 直觉主义对照表 | 第 3 层 |
| ⑲ 墙的精确地图 | 可判定片段（16 条逐条标源）+ 算术层级 Δ1/Σ1/Π1/Σ2/Π2（每层写清引擎承诺） | 数学底座 |
| ⑳ 工作台 | 一批材料 → 会话台账（逐条诊断 + 线索建议 + 欠什么）→ 一页简报；跨命令记住前文 | 工作台 |

也可以直接调机制：

```python
from engine.mechanisms.paradox_measure import run as measure

r = measure({'mode': 'mu1', 'wA': 5, 'wNotA': 5})
print(r['mu'])   # 1.0 —— 证据对等，悖论强度最大
```

或调经典层构件：

```python
from engine.classical.propositional import run as pl

r = pl({'premises': ['人→会死', '人'], 'conclusion': '会死',
        'mode': 'validity'})
print(r['verdict'])   # valid
```

---

## 三、目录结构

```
paradox-engine/
├── engine/
│   ├── ai/                     ← AI 挂载（引擎函数 = function-calling 工具集）
│   │   ├── tools.py              全量构件 schema 自动生成 + call_tool 分派
│   │   ├── freeze_tool_schema.py 工具契约快照 + 漂移检查（防接口悄悄变）
│   │   └── ai_scenarios.py       两真实场景端到端演示（论证矛盾/学科建模）
│   ├── control/               ← 总控（引擎大脑：判类/复杂度/路由/五步流水线）
│   │   ├── classifier.py        12 题型判类 + L1/L2/L3 复杂度 + ROUTE 36 键
│   │   ├── controller.py        总控五步：判类→复杂度→切路→执行→判输出
│   │   ├── session.py           多轮会话台账（材料逐段导入/批次汇总/复核依据/台账与简报）
│   │   └── clue_suggester.py    结构化线索建议（按实际路由给可粘贴建议，不自动应用）
│   ├── mechanisms/            ← 悖论机制（第 2 层：run(inputs)->dict + PORTS + 自测）
│   │   ├── paradox_measure.py   悖论测度 μ（四分支）
│   │   ├── paradox_annotate.py  悖论注解（8 字段卡 + P-A/B/C）
│   │   ├── converge_check.py    收敛判定（四分支）
│   │   ├── selfref_fixpoint.py  递归修正×自指检测（共振带三态，钻墙主力）
│   │   ├── boundary_paradox.py  边界悖论判定（墙=边界：张力/划设即撤销/重生）
│   │   ├── observer_bypass.py   悖论全程自反旁路（主链不停，观察+注解+注入）
│   │   ├── counterpoint_gen.py  对位创生第三态（对立交汇 → 候选+依据）
│   │   ├── wall_pipeline.py     撞墙管线 A（测→注→钻→看→旁→创 → 五选一诊断）
│   │   ├── criticality.py       临界诊断（事件规模 → 是否无标度 + 三态 + 距阈值多远）
│   │   └── growth_guard.py       增长护栏（限幅/增益调度/滞后补偿 + 截断代价与开关抖动）
│   ├── scenarios/             ← 场景库（真实输入+期望诊断+复核——语料回馈判类器）
│   │   ├── scenarios.py          28 场景注册表 + run_all 对照（期望 vs 实际）
│   │   ├── corpus_stats.py       语料统计（一致率/混淆矩阵/覆盖缺口/复核进度）
│   │   └── review_marks.py       复核落笔（结论写回场景表，只改 checked/review）
│   ├── skeleton/              ← MT-MP-TL 骨架（第 0 层：结构表达，不掺判定）
│   │   └── mtmp.py              点/线程/拓扑（12 形态）/操作（5 种）
│   ├── cold/                  ← 冷门逻辑（第 3 层：按痛点选，外部共识归借鉴区）
│   │   ├── belnap_four.py        Belnap 四值（矛盾取"两者"不爆炸）
│   │   ├── many_valued.py        多值逻辑（三值 K3/Ł3：未知传播、重言式与三套对照）
│   │   ├── interval_algebra.py   区间代数（事件之间的定性时序：先于/相接/重叠/包含…）
│   │   ├── description_logic.py  描述逻辑 ALC（概念包含/本体分类：谁是谁的子类）
│   │   ├── mu_calculus.py        模态 μ 演算（不动点：μ 最小/ν 最大，CTL 可翻成它）
│   │   ├── asp.py                答案集程序（规则+否定即失败+约束 → 自洽结论集合）
│   │   ├── dung_framework.py     Dung 论证框架（grounded/preferred/stable）
│   │   ├── agm_revision.py       AGM 信念修正 + 非单调默认（旧结论可撤销）
│   │   ├── default_logic.py      默认逻辑完整不动点（所有扩展/共同结论/立场之争）
│   │   ├── relevance_logic.py    相干逻辑（真冲突 vs 话术冲突）
│   │   ├── truth_revision.py     Gupta-Belnap 真值修正（修正序列振荡）
│   │   ├── intuitionistic_logic.py 直觉主义（Kripke 求值/反模型搜索/两系统对照）
│   │   └── bisimulation.py        双模拟检查（行为等价：最大双模拟分划 + 不等价的见证 + 商系统）
│   └── classical/             ← 经典逻辑地基（第 1 层：判定/证明/可计算/类型）
│       ├── propositional.py      命题逻辑（有效/反例/可满足/重言式）
│       ├── nd_propositional.py   命题自然演绎 ND（证明树，经典/直觉主义）
│       ├── first_order.py        一阶谓词（∀/∃ 有限论域展开）
│       ├── monadic_fol.py        一元谓词判定（可判片段：域展开 ≤2^k，含反模型）
│       ├── presburger.py         Presburger 算术判定（量词消元：整数上判恒真/有解）
│       ├── model_check.py        CTL 模型检查（显式 Kripke：不变式/可达性/响应性）
│       ├── resolution.py         一阶归结（Skolem + 合一 + 归结链）
│       ├── equality_tableau.py   等词替换 + tableau（反例模型）
│       ├── ltl.py                时序 LTL（G/F/X/U 沿路径判定）
│       ├── modal.py              模态 □/◇（Kripke 语义 K/T/S4/S5）
│       ├── lambda_calculus.py    λ 演算（β 归约 / Y 不动点）
│       ├── turing_machine.py     图灵机（模拟 + UTM 自模拟 + 停机演示）
│       ├── stlc.py               简单类型 λ（类型检查，拦自应用）
│       ├── recursion_theorem.py  Kleene 递归定理（自指程序构造）
│       └── decidability_map.py   可判定片段 + 算术层级（墙的精确地图）
│       （每个构件配 test_*.py 正式测试 + 公式卡）
│   ├── cli.py                 ← 命令行入口（--text/--json/--file/--tools/--repl）
│   └── repl.py                ← 交互式诊断台（命令行薄前端：普通文字＝材料）
├── demo.py                  ← 2 分钟上手演示（二十步）
├── run_tests.py             ← 全量回归入口（一条命令，CI 同款）
├── verify_install.py        ← 安装路径端到端验证（构建 wheel→venv 装→真跑命令行）
├── pyproject.toml           ← pip 打包（paradox-engine console 命令）
├── .github/workflows/       ← CI（跑全量回归 + 演示 + CLI 冒烟）
├── docs/
│   ├── components.md            构件参考（51 个构件：做什么/端口/能否自跑，自动生成）
│   ├── mechanisms.md            分层能力总表（每构件：自测N+正式M）
│   ├── capability_matrix.md     能力矩阵（题型×构件×**接线状态**，自动生成）
│   ├── trigger_audit.md         触发实测（**候选集×触发集**：谁排进了管线却没真跑，自动生成）
│   ├── verifier_audit.md        验证方登记（**每件产物点名验证方**：外部/跨构件/独立复算/只有性质，自动生成）
│   ├── tool_schema.md           工具协议（39 工具契约表，自动生成，供调用方）
│   ├── glossary.md              术语表（引擎自己的术语定死；中英对照）
│   ├── ROADMAP.md               分层路线（7 阶段）
│   └── formulas/                公式卡 ×15（第 1 层每构件一张概念说明）
├── bench.py                 ← 性能基准（冒烟级：数量级护栏，不对外报数）
├── README.md                ← 本文件（中英双语 + 测试状态）
├── CONTRIBUTING.md          ← 贡献指南（五条硬纪律 + 发布面红线 + 自检清单）
├── CODE_OF_CONDUCT.md       ← 行为准则（Contributor Covenant 2.1）
├── SECURITY.md              ← 安全策略（私密报告通道 + 诚实攻击面范围）
├── .editorconfig            ← 编辑器约定（LF / UTF-8 / 4 空格）
├── .gitignore               ← 忽略构建产物与本机私有名清单（后者不进公开仓）
├── CHANGELOG.md             ← 变更日志（按日期，未发布不标版本）
├── NOTICE                   ← 版权/署名/AI 协作声明
└── (内容将逐步扩充——作者只放入精选后可以公开的部分)
```

每个构件文件是**自包含**的：`python engine/<层>/<名>.py` 直接跑自测；
正式测试 `python engine/<层>/test_<名>.py`。

---

## 四、核心概念

### 机制（mechanism）= 一个只诊断的判定函数

统一接口：
```python
run(inputs: dict) -> dict
```

三个设计约定贯穿所有机制：
- **诚实**：输入缺什么就报告"还差什么"（`*_pending`），不瞎猜不硬判；
- **拦截**：非法输入诚实报告，不产生假值；
- **白箱**：advice 说明依据，重要路径可回溯。

### 悖论测度 μ（paradox_measure）

四个分支度量"这个矛盾有多尖锐"：
- `mu1` 证据权重（默认）：两边证据越对等，μ 越接近 1；
- `mu2` 自指：X = ¬X 直接判 1；
- `mu3` 层级：不同层级论断的矛盾度；
- `mu4` 熵：不确定性越大，悖论倾向越强。

### 悖论注解（paradox_annotate）

检测到 A∧¬A 共存后，**不解决、不消除**，生成一张 8 字段注解卡
（ID/LV/POS/SRC/CT/EF/ST/AN）并按来源分级：
- 公理层（axiom）→ P-A（结构性，最高）；
- 运行期（runtime）→ P-B；
- 观察者（observer）→ P-C。

### 收敛判定（converge_check）

判定递归修正序列 x_{n+1} = f(x_n, err(x_n)) 是否收敛：
压缩映射（默认）/ 有限步 / 渐进 / 振荡四分支。

---

## 五、设计哲学（为什么"只诊断不决策"）

很多系统遇到矛盾的第一反应是"修掉它"——但这常常是**在证据不足时偷偷
做决定**。paradox-engine 换了个顺序：

```
矛盾出现 → 测量（μ） → 注解（卡） → 报告（白箱）→ 判断权交还使用者
```

诊断与决策分离：引擎负责"如实描述矛盾"，使用它的系统/人负责"拿它怎么办"。
这样矛盾不会被消灭，也不会被无视——它成为可以被讨论、比较、追溯的对象。

---

## 六、范围与路线

**当前已实现（分层）**：
- **总控（引擎大脑）**：判类器（12 题型信号表 → 主型/副型/置信度）+ 复杂度
  分级（L1/L2/L3）+ 路由表（36 键带 reason）+ **总控五步流水线**（判类→
  判复杂度→切路→真跑构件→五查判输出）——最小充分原则：简单问题绝不
  复杂化（L1 单机制直出），复杂问题不简化（L3 全管线）；
- **第 1 层 · 经典逻辑地基（9 构件族全完成）**：命题判定 → 命题自然演绎 ND
  → 一阶谓词 → 一阶归结 → 等词+tableau → 时序 LTL → 模态 → λ 演算 →
  图灵机 → 简单类型 λ（STLC）——经典共识，别人无门槛；判定类可判定即
  判（有限域展开/合一/tableau/类型检查），证明论/可计算性/类型论给
  诚实答案（证明树、归结链、停机不可判定收编为标本、类型拦自应用）；
- **第 0 层 · MT-MP-TL 骨架**：点（异构/自治/变形）+ 线程（方向/速度/
  汇合/交叉）+ 拓扑 12 形态分类 + 操作（connect/disconnect/replace/fold/
  spawn）——只做结构表达，不掺判定；
- **第 2 层 · 悖论（撞墙管线五件套）**：悖论测度（μ）+ 注解（8 字段卡 +
  分级）+ 收敛判定 + **递归修正×自指检测**（共振带三态）+ **边界悖论判定**
  + **悖论全程自反旁路** + **对位创生第三态** + **增长护栏**（限幅/增益调度/滞后补偿）——经典层撞到不可判定
  → 上卷 → **五选一诊断**（可判/良性自指/共振带自指/发散真墙/可创生），
  "矛盾当第一公民"从主张变成可跑管线；
- **第 3 层 · 冷门逻辑（按痛点接入，十三件齐）**：Belnap 四值（矛盾取"两者"
  不爆炸——次协调语义地基）+ **多值逻辑**（三值：K3 管"未知"传播、Ł3 管"中间真值"，
  连 P→P 是不是重言式两套都不同，附经典/两套三值的对照表）+ Dung 论证框架
  （grounded/preferred/**stable**——冲突场哪些立场站得住，stable 还可能一个都没有）+ **AGM 信念修正/非单调**（新信息来了旧结论还成立吗——
  最小放弃 + 可废止默认）+ **默认逻辑完整不动点**（Reiter 原义：算出所有
  扩展，分清"每个扩展都成立"与"只在部分扩展成立"）+ **相干逻辑**（前提结论
  是否共享变量——真冲突 vs 话术冲突）+ Gupta-Belnap 真值修正（修正序列振荡）
  + **区间代数**（Allen 定性时序推理：事件之间"谁先谁后/谁包含谁"自不自治，不一致给冲突对、没发现冲突给可复核的整数区间见证）+ **直觉主义逻辑**（构造性立场：Kripke 反模型 + 经典 vs 直觉主义对照——
  排中律/双重否定消去/Peirce 律在构造性立场不成立）+ **描述逻辑 ALC**（概念包含/
  本体分类：判"是不是所有 A 都是 B"，可满足给规范模型；补的是第 3 类"关系结构"
  与第 10 类"定义辨析"缺的**概念层级**这块——有限论域一阶只能答"在这几个对象上
  成不成立"）+ **模态 μ 演算**（不动点逻辑：μ 最小/ν 最大两个算子自己拼时序性质，
  "反复、最终、从此以后"这类过程性质从"写不出来"变成"能算且留痕"；CTL 的八个
  路径量子都能翻成 μ 式子——补的是第 4 类"演化过程"与第 6 类"自指/深层"缺的
  **循环性质**这块）+ **答案集程序 ASP**（规则 + "否定即失败" + 约束 → 自洽的结论
  集合：可能一个、多个、也可能**一个都没有**（那就是这套规则自相矛盾），每个原子
  写明靠哪条规则撑住；补的是第 2 类"论证矛盾"与第 5 类"知识更新"缺的**程序化
  非单调推理**这块）+ **双模拟检查**（两个状态是不是"行为上分不开"：最大双模拟分划 + 不等价的见证（轮次/标号/区分序列）+ 商系统；与 μ 演算互验——补的是"两个系统/两个状态是不是同一个行为"这块）——按痛点选，外部共识
  标注来源归借鉴区；
  **接线三态**（详见 `docs/capability_matrix.md`，按活代码自动生成）：① **默认管线**
  ——判类器按"题型 × 复杂度档"自动送材料（AGM 接 T5、相干检查接 T2-L2 等 11 件）；
  ② **线索触发补跑**——题型对得上 + 人给足该构件的线索就跑，**不进默认管线**：
  区间代数（events+relations）· 描述逻辑 ALC（sub/super 或 tbox）· μ 演算
  （formula+states）· 答案集 ASP（program）· Dung 立场集（arguments+attacks）·
  Belnap 四值（formula）· 直觉主义（formula）——它们都要"人写的正式式子"，
  放进管线会让本来线索齐了的材料显示"还欠"，也破坏档位语义；
  ③ **未接线**——只能 `--call` 单独调（17 件）。**引擎不抽公式**：形式化式子由人给；
  **真值修正演示没接**（它无需输入，接进去会让「真跑/缺输入」计数失真）；
- **数学底座（借鉴区，标注来源）**：Kleene 递归定理自指构造（程序拿到
  自己）+ Gupta-Belnap 真值修正（共振带收敛的学界锚点——说谎者周期 2
  是教科书结论）+ **可判定片段地图 / 算术层级**（16 条片段标可判/半可判/
  不可判并逐条标出处；Δ1/Σ1/Π1/Σ2/Π2 每层写清**引擎承诺什么**——
  "算不清"从此有精确名字，不是一句搪塞）；
- **AI 挂载层**：全部构件封装为 function-calling 工具（schema 从 PORTS
  自动生成，零手工漂移）+ call_tool 统一分派——AI 拿到工具清单即可调用
  整个引擎；命令行也开了一个口子（`--call 工具 --args {JSON}`，`--tools` 看清单，
  `--json` 给结构化结果；交互台里对应 `/call`）——**41 件工具一个都不再"只能写
  Python 才调得到"**；两真实场景端到端（论证矛盾检查 / 学科建模）；
- **工作台（多轮会话台账）**：`--session 文件.json` 逐条材料累积诊断（跨命令
  记住前文）· `--add-file 材料.md` 整篇材料逐段诊断（超限与空白段照实报，
  不静默截断）· `--overview` 批次汇总（判类/复杂度/置信度/构件状态/墙事件，
  **只统计不下判断**）· `--review` 复核依据落账 + `--mark` 把复核结论写回
  场景表（**引擎不替作者下复核结论**）· `--export 台账.md` 导出 Markdown
  台账（汇总/逐条/复核记录/修正史/边界，默认不覆盖）；T5（知识更新）材料可
  用 `--revise "¬Q" --turn N` 把 AGM 修正挂在对应材料上——**引擎不抽公式**，
  命题式由人给。

**扩展中（见 docs/ROADMAP.md）**：撞墙管线 B/C 支线（按真实痛点接入）。

### 测试状态

- **2227 项正式断言全过**（78 个测试文件），覆盖全部
  机制构件与总控/场景/AI 工具层；
- **一条命令跑全量回归**：`python run_tests.py`（发现 + 运行 + 汇总；
  任一文件失败即非零退出——CI 与本地同一入口）；
- **安装路径已验证**：`python verify_install.py` 真构建 wheel → 临时 venv 装 →
  跑安装后的 `paradox-engine --text/--json/--file/--tools` 与 import 接入
  （CI 每次也跑这一档）；
- CI：`.github/workflows/test.yml`（Python 3.9 / 3.12 上跑回归 + 演示 + CLI 冒烟）；
- 每个构件自包含：`python engine/<层>/<名>.py` 跑自测（机制自身验证），
  `python engine/<层>/test_<名>.py` 跑正式测试；
- 演示：`python demo.py` 二十步全过；真实场景端到端：
  `python engine/ai/ai_scenarios.py`；场景库对照：28 场景（T1-T12 每个题型 ≥2）
  （`python engine/scenarios/scenarios.py`）；
- 零第三方依赖，纯 Python 标准库（≥3.9）；
- **行尾统一 LF**：`.gitattributes` 全局 `eol=lf`——即便 Windows 系统级
  `core.autocrlf=true` 也不会把仓库文本文件翻成 CRLF；有不变式测试守着
  （`test_packaging.py`：工作区文本文件不得含 CRLF，覆盖 json/yml/无后缀文件）；
- Windows 控制台：CLI / demo / 每个构件自测都带**控制台自愈**（自动把输出流设
  UTF-8）——不必先设 `PYTHONIOENCODING`，直接 `python engine/<层>/<名>.py` 即可。

- 纯 Python 标准库，无第三方依赖；
- 体系本体（落落逻辑体系：完整机制库、文档库）**不在此仓库**；这里只放
  作者挑选后认为可以公开的部分；
- 本项目**不宣称解决任何哲学/逻辑学争议**，也不宣称绕过图灵停机/哥德尔
  不完备（那是定理）。它做两件事：经典能算的算清；算不清的矛盾——
  测量、注解、诚实报告，把判断留给使用者。

---

## 七、来源、协作与许可

- **概念原创**：月落寻常（落落），"落落逻辑体系"作者。本仓库内容由其
  从体系中**精选**并授权公开；体系本体（完整文档库/全量机制库）不在本仓库。
- **AI 协作声明**：本仓库的工程化实现（代码、测试、文档、demo 编排）由
  作者与 AI 协作完成——AI 承担实现与整理，概念、设计取向、取舍与最终
  决策由作者主导。分层的逻辑主张（第 1 层经典能算的算清、第 2 层矛盾
  当第一公民、只诊断不决策）为作者原创方向。
- **外部借鉴**：代码中借用的经典共识（如 Belnap 四值、Dung 论证框架、
  AGM 信念修正 1985、Reiter 默认逻辑、Anderson-Belnap 相干逻辑 1975、
  直觉主义（Brouwer/Heyting/Kripke 1959）、经典逻辑各构件）均在对应文件
  docstring 标注来源，归借鉴区，不混原创区。
- 代码中的公式卡引用（`formulas/*.md`）为概念说明，可能随仓库演化补齐。
- **许可**：**MPL-2.0（Mozilla Public License 2.0）**——允许商用、允许修改、
  欢迎协作（fork / 提 PR / 一起改）；改了哪个源文件，那个文件保持 MPL
  开源。[LICENSE](LICENSE) 为纯 MPL-2.0 全文；版权/署名/AI 协作声明见
  [NOTICE](NOTICE)。

---

## 八、给贡献者

想加一个机制？看现有文件格式（PORTS + run + `__main__` 自测），
先在小处跑通再扩展。本仓库纪律：
- 每个机制必须自包含、可独立运行；
- 非法输入必须诚实拦截，不产生假值；
- 只诊断不决策，不替使用者下结论。
