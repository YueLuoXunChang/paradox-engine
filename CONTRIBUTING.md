# 贡献指南（CONTRIBUTING）

> 欢迎一起来改。这份文档只讲一件事：**在这个仓库里怎么改，才算改得对**。
> 项目概念与方向由作者主导（见 [NOTICE](NOTICE)）；工程实现欢迎协作。

---

## 一、先看清这个仓库是什么

- 这是一个**分层逻辑引擎**：能算的算清（第 1 层经典逻辑），算不清的当第一公民
  （第 2 层悖论：测量→注解→诊断），非经典立场按需接入（第 3 层冷门），
  外加数学底座与 AI 工具挂载层；
- **只诊断不决策**：引擎输出诊断、依据与边界声明，不替使用者下结论。这条是
  设计底线，不是措辞——任何 PR 都不要把"建议怎么做"塞进构件输出；
- 体系本体（完整机制库与文档库）**不在本仓库**，这里只放作者挑选后可以公开的
  部分。所以：不要往这里搬内部材料，也不要在代码注释里引用内部文档编号。

---

## 二、五条硬纪律（本项目特有，请先读）

1. **零第三方依赖**：纯 Python 标准库（≥3.9）。需要外部库的方案请先开 issue 讨论。
2. **每个构件自包含**：`python engine/<层>/<名>.py` 跑自测（构件自身验证），
   `python engine/<层>/test_<名>.py` 跑正式测试——两个都要有，且自测要在文件内
   （不依赖测试框架）。
3. **诚实边界**：算不动就说算不动（返回 `undecided` / `*_pending` / `size_limit`
   这类状态），**绝不**编造数值、绝不静默落默认值、绝不把"算不出"写成"不成立"。
   借用外部共识（经典逻辑、非经典逻辑、计算理论）必须在该文件 docstring 标注来源。
4. **改动要记账**：功能变更写进 [CHANGELOG.md](CHANGELOG.md)；对外契约（工具名 /
   参数名）变更还要重新生成契约快照与文档（见下）。
5. **不加版本号**：代码与文档里不写"版本：vX.Y"这类字样；真发布才由作者打 tag
   （从 `v0.1.0` 起步）。批次用日期而非版本号表达。

---

## 三、动手之前

```bash
git clone https://github.com/YueLuoXunChang/paradox-engine.git
cd paradox-engine
python demo.py        # 十九步演示：先看它能干什么
python run_tests.py   # 全量回归：当前应当全绿
```

- Windows 上也**不需要**设 `PYTHONIOENCODING`：CLI、demo 与每个构件自测都自带
  控制台编码自愈；
- 仓库行尾统一 **LF**（`.gitattributes` 全局 `eol=lf`）；`core.autocrlf` 开着也不会
  把文件翻成 CRLF，别手动改行尾。

---

## 四、改法：三类常见改动

### 1. 加一个构件（新机制 / 新逻辑层组件）

1. 放 `engine/<层>/<名>.py`：文件头写清「概念来源 / 做什么 / 诚实边界 / 统一接口」，
   导出 `PORTS`（输入输出声明）与 `run(inputs) -> dict`，文件末跑自测；
2. 配 `engine/<层>/test_<名>.py`：正式测试（每项断言一条中文 `check(...)`，
   末行 `print(f"结果: {PASS}/N 通过")` 并以 `raise SystemExit(0 if PASS == N else 1)`
   收尾——`run_tests.py` 就认这一行；
3. 想让它能被 AI 调用：在 `engine/ai/tools.py` 的注册表加一行；
4. 若该构件要进总控管线：在 `engine/control/classifier.py` 的 `ROUTE` 指向它，
   **同时**在 `engine/control/controller.py` 的 `ADAPTER_SPECS` 加适配器
   （有不变式测试盯着"路由里出现的构件必须有适配器"）；
5. 重新生成工具契约（若工具清单变了）：

```bash
python engine/ai/freeze_tool_schema.py    # 更新快照与 docs/tool_schema.md
python run_tests.py                       # 全绿再提交
```

### 2. 改判类信号表（语料回馈）

`engine/control/classifier.py` 的 `TYPE_DEFS`（每型：中文信号 + 权重）。
改法有据：**先加一个真实场景**（`engine/scenarios/scenarios.py`）复现误判，再改信号，
再回归——判错的场景会把差异打出来，改完必须让"已复核场景全通过"。

```bash
python engine/scenarios/scenarios.py      # 看 14 个场景的期望 vs 实际
```

### 3. 改对外契约（工具名 / 参数名）

工具名与参数名是**对外承诺**（AI 客户端、脚本会照它写）。改了就：

```bash
python engine/ai/freeze_tool_schema.py    # 重新冻结快照 + 文档
python engine/ai/test_tool_contract.py    # 契约一致性
```

并在 CHANGELOG 里写明"哪个工具 / 哪个参数 / 为什么"，别悄悄改。

---

## 五、提交前自检清单

```bash
python run_tests.py        # 必过：全量回归（逐文件跑，汇总断言数）
python demo.py             # 必过：端到端演示
python engine/ai/freeze_tool_schema.py --check   # 契约没漂（改了才需重新生成）
```

- 回归里已经内建的不变式（会自动帮你查）：
  可独立运行的文件都带控制台自愈、路由构件都有适配器、打包不列漏子包、
  工作区文本文件无 CRLF、发布面不夹带内部残留、门面数字与实测一致；
- 提交信息：中文写清「做了什么 / 为什么 / 怎么验证的」，一次改动一个主题；
- 不确定的地方**不要猜**——按"先查不许猜"来：查代码、查文档、查不到的写成
  诚实标注（`*_pending` / `undecided`）而不是编一个。

---

## 六、提 Issue / PR 的建议格式

- **Issue**：给一个真实输入（中文原文）+ 你期望的诊断 + 实际输出；若是判类问题，
  说明属于哪一型（T1-T12）；
- **PR**：说明改了什么、影响哪些对外行为（诊断结果 / 工具契约 / 路由）、
  自检命令的输出摘要（`run_tests.py` 的合计行就行）。

---

## 七、许可与署名

- 许可 **MPL-2.0**：允许商用与修改；你改过的源文件保持 MPL 开源（见 [LICENSE](LICENSE)）；
- 版权、署名与 AI 协作说明见 [NOTICE](NOTICE)；
- 概念与分层主张（经典能算的算清 / 矛盾当第一公民 / 只诊断不决策）为作者原创方向，
  fork 或再发布时请保留出处。
