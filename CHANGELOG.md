# 变更日志（CHANGELOG）

> 记录对外可见的重要变更。纪律：**未正式发布不标版本号**——按日期分节；
> 真实版本（tag）等正式发布从 v0.1.0 起步。

## 2026-09-07

### 新增
- **冷门逻辑补完（第 3 层 3.3/3.4）**：
  - `engine/cold/agm_revision.py`——AGM 信念修正（最小放弃 + 优先级/信念度）+ 非单调默认推理（可废止，Reiter 简化版）——T5 知识更新痛点；
  - `engine/cold/relevance_logic.py`——相干逻辑：前提与结论是否共享变量（真冲突 vs 话术冲突）——T2 增强；
  - `engine/cold/intuitionistic_logic.py`——直觉主义：Kripke 求值 + 反模型搜索（完备界 2^n，界内无解才判有效）+ 经典 vs 直觉主义对照表（排中律/双重否定消去/Peirce 律非构造有效）——详规 §五收口；
  - 三构件均逐条标注外部来源（AGM 1985 / Reiter / Anderson-Belnap 1975 / Brouwer-Heyting-Kripke 1959）归借鉴区；
- 正式测试 3 件（`test_agm_revision.py` 48 项、`test_relevance_logic.py` 43 项、`test_intuitionistic_logic.py` 43 项）；
- AI 挂载层注册三新工具（工具总数 25 → 28）；demo 扩到十八步（新增 ⑰ 冷门补完、⑱ 构造性立场）。
- **全量回归入口 `run_tests.py`**：一条命令发现并运行全部 30 个测试文件，解析各文件自报的通过线并汇总；任何文件失败即非零退出（沉默通过不算通过）；
- **CI**：`.github/workflows/test.yml`（Python 3.9/3.12 跑全量回归 + demo + AI 场景 + CLI 冒烟）；
- **冷门构件接入总控路由**（原先只能手调）：T5 → `agm_revision`（最小放弃修正）、T2-L2 → `relevance_logic`（真冲突 vs 话术冲突）；`needs_cold_logic` 由硬编码 `dung` 改为按冷门构件名前缀判定（加新构件不用改标记逻辑）；
- **补齐路由画饼**：`ltl`、`nd_propositional` 原先出现在路由表却无适配器（执行层只能报"未实现层"），现入声明表可真跑；新增不变式测试「ROUTE 里每个构件名都有适配器」；
- **场景库 +2（共 9 个）**：S08 真冲突 vs 话术冲突（相干检查接线）、S09 天鹅黑天鹅（AGM 接线）；场景结果新增 `execution` 白箱字段（本场景实际跑了哪些构件、什么状态/结论）。
- **可判定片段地图 + 算术层级**（`engine/classical/decidability_map.py`——阶段 7 收口）：16 条逻辑片段标可判/半可判/不可判并逐条标出处（Church 1936 / Turing 1936 / Gödel 1931 / Presburger 1929 / Kripke 1963·1965 / Thomason 1975 / Soare / Löwenheim 1915 / Cook 1971 等）；算术层级 Δ1/Σ1/Π1/Σ2/Π2 每层写清**引擎承诺**（可判给结论、Σ1 只"枚举到才说是"、更高层不承诺）；`mode='demo'` 真跑 1.6 λ / 1.7 图灵机 / 2.3 递归修正，完成蓝图 A1 的接线验收；未实现片段诚实标 `engine_available=False`（不假装能算）；
- **工程不变式测试**（`engine/test_packaging.py`）：路径引导（防顶层包名撞车）、打包完备（pyproject packages 覆盖所有子包）、路由无画饼、入口控制台自愈、门面版本纪律——每条对应一次真实踩坑；
- 正式测试 2 件（`test_decidability_map.py` 51 项、`test_packaging.py` 17 项）；AI 工具注册第 29 件（`decidability_map`）；demo 扩到十九步（⑲ 墙的精确地图）。
- **场景库扩到 14 个、覆盖 T1-T12 全部 12 题型**（轨 B2 判类语料回馈闭环）：
  - 新增 S10 三段论（T1）/ S11 依赖环（T3）/ S12 折价递推（T4）/ S13 证据冲突（T8）/ S14 无信号兜底（T12）；
  - **语料回馈闭环实例**：S13 首跑判错（T8 证据冲突被判成 T2）——根因是 T8 信号表只认「数据显示/报告说/相互矛盾的数据」这类固定短语，真实说法「研究说…另一份研究说…数据也互相矛盾」全漏；按真实用词扩表（平局仍归 T2，不打乱纯冲突文本）→ 三个真实候选全部判对，T2/T9/T11 不受影响；场景测试新增不变式「覆盖 12 题型（判类语料无盲区）」；
- **工具协议冻结**（轨 C1 生态接口）：`engine/ai/freeze_tool_schema.py` 从活注册表生成契约快照 `engine/ai/tool_schema_frozen.json` 与调用方文档 `docs/tool_schema.md`；`test_tool_contract.py` 21 项防漂移（契约被改即报不一致并指名到具体工具；check 模式只读不写）；
- **公共契约修正**：`controller` 的 `text` 原声明可选（`str?`），但缺它其实会诚实拦截——对外 schema 改标必填，避免调用方以为可以不传（契约变更已重新冻结 + 记账）。
- **贡献者路径**（`CONTRIBUTING.md`）：五条硬纪律（零依赖 / 构件自包含 / 诚实边界 / 改动记账 / 不加版本号）+ 三类常见改法（加构件 / 改判类信号 / 改对外契约）+ 提交前自检清单 + Issue/PR 格式；README 中英各加入口。
- **两项门面不变式测试**：
  - `engine/test_public_face.py`（10 项）——发布面不夹带内部残留：本机绝对路径 / 私有档案引用 / 内部文档编号 / 个人联系方式；含判据自检（正则不能写废）、允许项不误伤、排除集合固定；
  - `engine/test_docs_consistency.py`（19 项）——门面数字与实测一致：断言数 / 测试文件数 / 工具件数 / demo 步数 / 场景数 / 冷门件数 / 文件清单 / pyproject 指向。
- **输入健壮性修复**（坏输入扫描 29 工具 × {空/错类型/负值/None} 抓到的真问题）：
  - μ 测度（旗舰构件）：`wA=5, wNotA=-5` 曾算出 **μ = -9999999999.0**（违反自身声明的 μ∈[0,1]）、
    `wA="五"`/`None` 直接 TypeError 崩 → 现做数值语义校验（负数/非数值/布尔一律拦下并点名说明），
    并加 μ 自检：越界值不返回（宁可诚实报错）；
  - 悖论注解：`paradox=5`/`None`、`source=123` 三种崩法 → 现校验并诚实拦截，输出补 `verdict`；
  - Dung 论证框架：`arguments=5`（len 崩）、`attacks="xy"`/`[1]`（unpack 崩）→ 现校验形状、
    重名与引用未知节点，一律诚实拦截；
  - 新增 `engine/_validate.py`（共用输入校验：实数判定、非负校验、中文说明）；
  - 新增正式测试 `engine/test_robustness.py`（13 项）：29 工具 × 4 类坏输入不抛异常 / 挂载层不报
    tool_error / 构件输出都带 verdict / μ 永不越界 / 拦截时绝不给数值 / 控制器 8 类坏文本不崩。
- **安装路径端到端验证**（`verify_install.py` + CI 一步）：真构建 wheel → 临时 venv
  离线安装 → 真跑安装后的 `paradox-engine --text/--json/--file/--tools` 与 import 接入 →
  跑随包测试。**首次验证抓到三个真问题**：① 工具契约快照 JSON 没进 wheel（setuptools
  默认只收 .py）→ 已在 pyproject 声明 package-data；② 门面级测试在安装环境读不到仓库根
  会崩 → 改为 `engine/_layout.in_source_checkout()` **诚实跳过**；③ 契约测试无条件读
  `docs/tool_schema.md`、无条件比 mtime → 同为源码仓专属，现改为存在才读。
- **发布面清理**：按作者先例去掉内部**文档编号**引用（编号型指向统一改为「轨 X」这类通用表述），并清除指向私有记账文档的死链引用（改为"记入 CHANGELOG"）——此后由 `test_public_face.py` 长期守着。

- **CLI 暴露场景库**：新增 `--scenarios`（列 25 个场景 + 复核状态）与 `--scene S01|all`
  （跑对照：期望 vs 实际 + 真跑白箱，支持 `--json`）；未知场景 id 诚实报错退出 2
  （原先会报"0/0 通过"——那是假通过）。
- **随机模糊测试**（`engine/test_fuzz.py`，固定种子可复现）：随机文本 / 随机结构化参数 /
  随机数值 / 随机工具参数 —— 断言"不崩 + verdict 合法 + μ 要么 None 要么 ∈[0,1]"。
  首跑撞出**系统性错类型问题**（`equality_tableau` 在 `conclusion=True/-5/dict` 上 `len()` 崩）
  → 新增**参数类型闸**（`engine/_validate.arg_type_error`），挂载层与总控适配器**共用同一把闸**：
  错类型在进入构件前被拦下并点名参数，不再让 29 个构件各自崩一遍。
- **场景库扩到 25 个（每个题型 ≥2）**：新增 S15-S25；并**抓到第二处判类误判**——
  "这个调查说八成的人支持，样本只有一百人，靠不靠谱" 原判 T3（命中"支持"），
  根因是 T11 信号表只有"靠不靠谱/有效率/显著"这类评价词，「调查/样本/比例」全不在表里；
  按真实用词扩表后判对（T2/T8/T9 抽测不受影响）。测试新增不变式「每个题型 ≥2 个场景」。

- **判类白箱解释**（`--explain`）：把「为什么这么判」摆给使用者——主型/副型各自
  得分与命中信号、复杂度评分构成（实体/关系/加分项）、路由依据与管线、置信度。
  数据全部取自 classifier 本来的白箱输出，CLI 只排版（不新增"解释用的第二套判类"）。
- **场景复核辅助**（`--review` / `--stats`）：逐场景给期望 vs 实际 + 判类命中信号 +
  复核状态与勾选指引；统计各题型场景数、对照通过数、复核进度，并明确"复核未完成前
  不报误判率"（不拿未完成的分母凑数字）。直接服务作者手上的待复核场景。

- **门面标准件补齐**（GitHub 上直接生效，无需手工配）：`SECURITY.md`（私密报告通道 +
  诚实攻击面范围）· `CODE_OF_CONDUCT.md`（Contributor Covenant 2.1，联系走 Security
  通道、不留邮箱）· `.github/ISSUE_TEMPLATE/`（缺陷/功能模板 + 禁用空白 issue）·
  `.github/PULL_REQUEST_TEMPLATE.md`（自检清单）· `.editorconfig`（LF/UTF-8/4 空格）·
  README 中英加四枚徽章（tests / license / python / zero-dependencies）；
  文件清单纳入 `test_docs_consistency.py` 不变式（防被悄悄删）。

### 修复
- **一致性判定三态化**（诚实边界）：AGM 原先把「算不动」（经典层真值表
  原子数上限 10 → `size_limit`）当成「不一致」，会把自洽信念集错判成矛盾
  并平白弃掉信念；现区分 yes/no/unknown，算不动报 `undecided`；
- 新信息自身不可满足时单列 `new_info_unsatisfiable`（不再混报 size_limit）；
- **跨项目污染守卫**：`python engine/ai/ai_scenarios.py` 原先在脚本模式下
  `import engine` 会解析到**本机另一个项目**（顶层包名同为 `engine`）的代码
  ——同名的构件会被静默误用；现入口先钉本仓库根到 `sys.path` 首位，且
  `_load_module()` 核对模块文件确在本仓库内，越界即诚实报错（新增守卫测试）;
- **Windows 控制台编码自愈（全量）**：原先 CLI/demo 在默认 GBK 控制台直接
  UnicodeEncodeError 崩掉（报告含 ⚠/✅）；实测**33 个可独立运行的构件里 31 个**
  都会崩——按中文友好要求全部补上自愈（入口 `engine/_console.py`，
  构件自测内联 reconfigure）：现在直接 `python engine/<层>/<名>.py` 即可，
  不必先设 `PYTHONIOENCODING`；并加不变式测试防新构件漏加；
- CLI `--demo` 帮助文案"十五步"过时（实际十八步）→ 改为不硬编步数；
- CLI 测试里硬编码的工具数（23）改为从注册表动态取——防止再漂移；
- **测试污染仓库**：`test_tool_contract` 的漂移模拟原本直接改写被跟踪的契约快照，且用文本模式（Windows 下整文件变 CRLF）——现改写临时文件（monkeypatch 路径），并加自检「测试未改动被跟踪快照（前后 sha256 一致）」；
- **行尾根治**：本机**系统级** `core.autocrlf=true` 会把无后缀文件与顶层配置（NOTICE/pyproject.toml/.gitignore/.gitattributes）检出成 CRLF → `.gitattributes` 首行改为 `* text=auto eol=lf`（全局钉 LF，依据是 eol 属性优先于 autocrlf），并 `--renormalize` + 强制重放；不变式测试扩到全仓文本文件；

## 2026-09-06

### 新增
- **GitHub 首次发布**：仓库公开（YueLuoXunChang/paradox-engine），MPL-2.0 许可，中英双语 README，AI 协作声明；
- **包化 + CLI**：`pip install` 可装（console 命令 `paradox-engine`），`python -m engine.cli` 支持 `--text/--json/--file/--tools`；
- **场景库**：`engine/scenarios/`——7 个真实场景注册表（输入 + 期望诊断 + 复核标记），用于语料回馈判类器；
- **数学底座**：Kleene 递归定理自指构造（quine 自复制实跑验证）、Gupta-Belnap 真值修正（说谎者周期 2 教科书结论）——均标注外部来源归借鉴区；
- demo 从十五步扩到十六步。

### 变更
- controller 执行映射声明式化（`ADAPTER_SPECS` 表 + 特殊钩子）——加新构件 = 加一行；
- 全层 `__init__.py`：从 namespace 包变正规 Python 包。

### 修复
- 全仓去 UTF-8 BOM（35 文件）；统一行尾（.gitattributes）；
- 判类器 T1 信号过泛「是」移除（误伤 T2 冲突的根因）；
- 推送前敏感内容清理（内部文档指针/档案编号零残留）。

## 更早

见 git 历史（`git log`）：容器首版 → 阶段 0-6 分层落地（悖论/经典/骨架/冷门/AI 挂载）。
