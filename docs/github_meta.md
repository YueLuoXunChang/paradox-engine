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
- 若要加 CI（GitHub Actions 跑测试）——仓库内暂未配置；将来可加
  `.github/workflows/test.yml`（python -m pytest 或逐文件跑），需要时说一声。
