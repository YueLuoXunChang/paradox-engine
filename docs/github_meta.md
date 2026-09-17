# GitHub 仓库页配置建议

> 仓库页 Settings → General 填的字段（本文件是备查文本，方便复制粘贴）。

## Description（推荐 中文）

悖论/矛盾检测引擎——经典逻辑能算的算清，算不清的当第一公民（只诊断不决策）。概念原创：月落寻常，AI 协作实现 · MPL-2.0

## Description（推荐 English）

Pure-Python paradox/contradiction detection engine — classical logic decides what it can, the undecidable is measured, annotated and reported (diagnose only, never decide). MPL-2.0

## Topics

```
logic
paradox
contradiction
logical-reasoning
reasoning
python
diagnosis
non-classical-logic
```

## 建议的 GitHub 字段

| 字段 | 值 |
|---|---|
| Repository name | paradox-engine |
| Description | 见上（中英任选或都试——GitHub 只存一个，选英文兼容性更广，中文放 README） |
| Topics | 见上 |
| Website（可选） | 留空（无独立站点） |
| Releases/tags | 暂不打——稳定后打 v0.1.0（死命令：真发布才 tag） |

## 备注

- README.md 是中文主文档（含 🌐 English 切换链接 README.en.md）；
- 不要勾选 GitHub 自动生成的 README/LICENSE/.gitignore（仓库内已有）；
- CI 已配置：`.github/workflows/test.yml`（Python 3.9/3.12 跑全量回归 +
  演示 + CLI 冒烟）——push 后仓库页 Actions 会出绿/红，README 可挂状态徽章
  （徽章 URL 形如 `https://github.com/<用户>/paradox-engine/actions/workflows/test.yml/badge.svg`，
  要用时再加一行即可，本文件不预先写死）；
- 本地跑同一套回归：`python run_tests.py`（32 测试文件 / 841 断言）。

## 仓库页可展示的状态行（About/议题里可直接用）

- 分层引擎：总控 + 第 0/1/2/3 层 + 数学底座 + AI 挂载（29 个可调用工具）；
- 零第三方依赖（纯标准库，Python ≥3.9）；841 项正式断言 + CI 全绿；
- 冷门逻辑六件齐（Belnap 四值 / Dung / 真值修正 / AGM / 相干 / 直觉主义）
  + 可判定片段地图（16 条，逐条标源）；
- 诚实边界：能算的算清，算不清的测量+注解+报告——**只诊断不决策**。
