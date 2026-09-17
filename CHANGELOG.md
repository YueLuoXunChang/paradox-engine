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
- CLI 测试里硬编码的工具数（23）改为从注册表动态取——防止再漂移。

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
