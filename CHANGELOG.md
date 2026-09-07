# 变更日志（CHANGELOG）

> 记录对外可见的重要变更。纪律：**未正式发布不标版本号**——按日期分节；
> 真实版本（tag）等正式发布从 v0.1.0 起步。

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
