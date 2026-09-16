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

### 修复
- **一致性判定三态化**（诚实边界）：AGM 原先把「算不动」（经典层真值表
  原子数上限 10 → `size_limit`）当成「不一致」，会把自洽信念集错判成矛盾
  并平白弃掉信念；现区分 yes/no/unknown，算不动报 `undecided`；
- 新信息自身不可满足时单列 `new_info_unsatisfiable`（不再混报 size_limit）；
- **跨项目污染守卫**：`python engine/ai/ai_scenarios.py` 原先在脚本模式下
  `import engine` 会解析到**本机另一个项目**（顶层包名同为 `engine`）的代码
  ——同名的构件会被静默误用；现入口先钉本仓库根到 `sys.path` 首位，且
  `_load_module()` 核对模块文件确在本仓库内，越界即诚实报错（新增守卫测试）;
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
