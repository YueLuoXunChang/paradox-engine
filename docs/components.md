# 构件参考（自动生成，别手改）

> 由 `python engine/_components_doc.py --write` 从各模块 docstring 与 `PORTS` 生成；`--check` 可在改动后比对漂移。手改这份文件会在检查里报不一致。

- 构件数：**39** 个（不含下划线内部件与测试）

## 第 0 层 · 总控（判类/复杂度/路由/五步流水线/工作台）

### `engine/control/classifier.py`

- 做什么：输入一段问题文本 → 输出：题型（主型+副型+置信度）→ 复杂度档（L1/L2/L3）
- 输入端口：`text: str?`、`debug: bool?`
- 输出端口：`verdict: str`、`main_type: str`、`main_name: str`、`types: list`、`confidence: str`、`complexity: dict`、`level: str`、`route: dict`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/control/clue_suggester.py`

- 做什么：clue_suggester.py — 结构化线索建议（第 0 层总控外围，工作台件）
- 输入端口：`text: str?`
- 输出端口：`verdict: str`、`route: str?`、`components: list`、`paste: dict`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/control/controller.py`

- 做什么：输入一段问题文本（可带结构化线索）→ 判类 → 判复杂度 → 切路 →
- 输入端口：`text: str`、`structured: dict?`、`debug: bool?`
- 输出端口：`verdict: str`、`classification: dict`、`execution: list`、`output_check: dict`、`report: str`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/control/session.py`

- 做什么：把逐条诊断与信念修正**记在一个会话文件里**——每加一条材料就落一次诊断，
- 输入端口：`action: str`、`path: str?`、`text: str?`、`new_info: str?`、`beliefs: list?`、`structured: dict?`、`text_file: str?`、`split: str?`、`max_segs: int?`、`max_seg_chars: int?`、`out_file: str?`、`overwrite: bool?`、`scene_id: str?`、`turn: int?`、`clues: bool?`、`start_seg: int?`、`redact: bool?`
- 输出端口：`verdict: str`、`state: dict`、`turn: dict?`、`revision: dict?`、`imported: dict?`、`markdown: str?`、`reviews: list?`、`overview: dict?`、`boundary: str`
- 可独立运行：是（自带自测）

## 第 0 层 · MT-MP-TL 骨架（结构表达，不掺判定）

### `engine/skeleton/mtmp.py`

- 做什么：把"结构/演化/多线推进"表达成可运行对象——点怎么连、几条线怎么跑、
- 输入端口：`mode: str?`、`points: list?`、`edges: list?`、`threads: list?`、`op: str?`、`a: str?`、`b: str?`、`kappa: float?`、`verbose: bool?`
- 输出端口：`verdict: str`、`detail: dict`、`boundary: str`
- 可独立运行：是（自带自测）

## 第 1 层 · 经典逻辑地基（判定/证明/可计算/类型）

### `engine/classical/decidability_map.py`

- 做什么：给"这个问题能不能算"一个可查可跑的答案——四个能力：
- 输入端口：`mode: str?`、`system: str?`、`level: str?`
- 输出端口：`verdict: str`、`entry: dict`、`level: dict`、`fragments: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/equality_tableau.py`

- 做什么：equality_tableau.py — 等词 + 表列法构件（第 1 层经典逻辑基础 1.5）
- 输入端口：`premises: list?`、`conclusion: str?`、`equality: list?`、`max_expand: int?`
- 输出端口：`verdict: str`、`closed_branches: list`、`open_branch_model: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/first_order.py`

- 做什么：在有限论域上判定一阶逻辑公式的（逻辑）后承/可满足性
- 输入端口：`universe: list?`、`facts: list?`、`rules: list?`、`query: str`
- 输出端口：`verdict: str`、`counterexample_model: list`、`atoms_used: int`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/lambda_calculus.py`

- 做什么：λ 项解析 + α/β 归约 + 邱奇编码（自然数/真值/算术）+ Y 不动点
- 输入端口：`expr: str?`、`mode: str?`、`steps_limit: int?`、`church_arg: int?`、`fact_n: int?`
- 输出端口：`verdict: str`、`normal_form: str`、`beta_steps: list`、`church_number: int`、`factorial_value: int`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/ltl.py`

- 做什么：给"演化/过程/因果链"一个形式语言，判定给定状态路径是否满足
- 输入端口：`path: list?`、`formula: str`
- 输出端口：`verdict: str`、`violation_index: int`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/modal.py`

- 做什么：用可能世界语义判定模态公式（□ 必然 / ◇ 可能）的真假与可满足性
- 输入端口：`worlds: list?`、`access: dict?`、`system: str?`、`assign: dict?`、`formula: str`、`world: str?`
- 输出端口：`verdict: str`、`system: str`、`note: str`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/model_check.py`

- 做什么：输入一个**显式 Kripke 结构**（状态、迁移、每个状态上的原子命题）与一个
- 输入端口：`states: list?`、`transitions: list?`、`labels: dict?`、`formula: str?`、`init: list?`
- 输出端口：`verdict: str`、`explanation: str`、`holds_in: list`、`fails_in: list`、`sat_count: int?`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/monadic_fol.py`

- 做什么：判定一个**闭的一元谓词公式**是否有效：谓词只作用在一个变量上（P(x)、Q(x)…），
- 输入端口：`formula: str?`、`mode: str?`
- 输出端口：`verdict: str`、`explanation: str`、`countermodel: dict?`、`predicates: list`、`domain_size: int?`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/nd_propositional.py`

- 做什么：自然演绎证明搜索——用引入/消去规则从前提推出结论
- 输入端口：`premises: list?`、`conclusion: str?`、`system: str?`、`max_steps: int?`
- 输出端口：`verdict: str`、`proof_tree: list`、`system: str`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/propositional.py`

- 做什么：判定命题公式的真假、推理有效性、可满足性、重言式/矛盾式
- 输入端口：`formula: str`、`premises: list?`、`conclusion: str?`、`mode: str?`
- 输出端口：`verdict: str`、`counterexample: dict`、`truth_table: list`、`atoms: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/recursion_theorem.py`

- 做什么：演示"程序可以拿到自己的代码"——两个形态：
- 输入端口：`mode: str?`、`payload: str?`、`transform: callable?`
- 输出端口：`verdict: str`、`program: str`、`runs_like: str`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/resolution.py`

- 做什么：一阶归结反证——子句化/Skolem/合一 mgu/归结链
- 输入端口：`premises: list?`、`conclusion: str?`、`facts: list?`、`max_resolvents: int?`
- 输出端口：`verdict: str`、`resolution_chain: list`、`skolem_used: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/stlc.py`

- 做什么：STLC 类型检查与推导——Γ ⊢ M : A（类型规则）+ Curry-Howard 对照
- 输入端口：`expr: str?`、`context: dict?`、`expected: str?`
- 输出端口：`verdict: str`、`inferred: str`、`derivation: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/classical/turing_machine.py`

- 做什么：1. 图灵机定义与模拟器（跑任意给定 TM）；
- 输入端口：`program: dict?`、`input: str?`、`mode: str?`、`steps_limit: int?`
- 输出端口：`verdict: str`、`trace: list`、`diagonalization_note: str`、`boundary: str`
- 可独立运行：是（自带自测）

## 第 2 层 · 悖论机制（撞墙管线 A 与五件套）

### `engine/mechanisms/boundary_paradox.py`

- 做什么：把"可计算/可判定/领域"的墙当作**边界对象**诊断——墙存在吗？
- 输入端口：`wall_name: str?`、`domain: str?`、`inside: str?`、`outside: str?`、`recursive_layer: int?`、`mode: str?`
- 输出端口：`verdict: str`、`tension: float`、`self_undermining: bool`、`removable: bool`、`advice: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/converge_check.py`

- 做什么：converge_check.py — 收敛判定四分支（核心机制）
- 输入端口：`branch: str?`、`f: callable`、`err_fn: callable`、`x0: float?`
- 输出端口：`verdict: str`、`converges: bool`、`rate: any`、`detail: dict`
- 可独立运行：是（自带自测）

### `engine/mechanisms/counterpoint_gen.py`

- 做什么：对立对 (A, ¬A) 交汇——不判谁对、不消除——产生第三态 C：
- 输入端口：`thesis: str?`、`antithesis: str?`、`coupling: str?`、`dimensions: list?`
- 输出端口：`verdict: str`、`coupling: str`、`third_state: dict`、`derivation: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/observer_bypass.py`

- 做什么：系统级旁路：主线程正常推进（建模/推理/演化），悖论旁路线程并行
- 输入端口：`main_events: list?`、`detect: callable?`、`use_advice: bool?`
- 输出端口：`verdict: str`、`main_ran: int`、`findings: list`、`injected_at: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/paradox_annotate.py`

- 做什么：paradox_annotate.py — 悖论注解机制（核心机制）
- 输入端口：`paradox: dict?`、`source: str?`、`impact: str?`、`eliminable: bool?`、`seq: int?`
- 输出端口：`annotation: dict`、`grade: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/paradox_measure.py`

- 做什么：paradox_measure.py — 悖论测度 μ（核心机制）
- 输入端口：`mode: str`、`wA: float?`、`wNotA: float?`
- 输出端口：`mu: float`、`branch: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/selfref_fixpoint.py`

- 做什么：把"不可判定/自指"从死胡同变成可诊断态——跑递归修正序列
- 输入端口：`mode: str?`、`f: callable?`、`state0: any?`、`sentence: str?`、`max_steps: int?`、`tol: float?`
- 输出端口：`verdict: str`、`selfref_type: str`、`detail: dict`、`annotation: dict`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/mechanisms/wall_pipeline.py`

- 做什么：输入一个"疑似墙"（自指/矛盾/不可判定/冲突），跑完管线各步，
- 输入端口：`wall: str?`、`thesis: str?`、`antithesis: str?`、`events: list?`
- 输出端口：`verdict: str`、`diagnosis: dict`、`annotation: dict`、`steps: list`、`boundary: str`
- 可独立运行：是（自带自测）

## 第 3 层 · 冷门逻辑（按痛点接入，外部共识归借鉴区）

### `engine/cold/agm_revision.py`

- 做什么：给"新信息来了旧结论还成立吗"一个可跑答案——两个能力：
- 输入端口：`mode: str?`、`beliefs: list?`、`new_info: str?`、`priorities: dict?`、`defaults: list?`、`facts: list?`、`exceptions: list?`、`max_beliefs: int?`
- 输出端口：`verdict: str`、`kept: list`、`dropped: list`、`conclusions: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/cold/belnap_four.py`

- 做什么：给"矛盾该共存"一个可判定的语义——四值真值表：A 与 ¬A 都有证据
- 输入端口：`formula: str?`、`assign: dict?`、`demo: bool?`
- 输出端口：`verdict: str`、`value: str`、`truth_set: list`、`rows: list`、`note: str`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/cold/dung_framework.py`

- 做什么：输入论证集 + 攻击关系图 → 输出站得住的立场集（grounded 唯一 /
- 输入端口：`arguments: list?`、`attacks: list?`、`max_arguments: int?`
- 输出端口：`verdict: str`、`grounded: list`、`preferred: list`、`admissible_examples: list`、`conflict_pairs: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/cold/intuitionistic_logic.py`

- 做什么：给"这个公式在构造性立场下成立吗"一个可跑答案——三个能力：
- 输入端口：`mode: str?`、`formula: str?`、`worlds: list?`、`order: list?`、`valuation: dict?`、`world: str?`、`formulas: list?`、`max_worlds: int?`
- 输出端口：`verdict: str`、`value: bool?`、`countermodel: dict?`、`comparison: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/cold/relevance_logic.py`

- 做什么：给"这个推理是真有效，还是只是形式有效"一个可跑答案——两个能力：
- 输入端口：`mode: str?`、`premises: list?`、`conclusion: str?`、`prop_a: str?`、`prop_b: str?`
- 输出端口：`verdict: str`、`shared_atoms: list`、`premise_atoms: list`、`conclusion_atoms: list`、`classically_valid: bool?`、`counterexample: str?`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/cold/truth_revision.py`

- 做什么：给定一组句子的真值条件（每句 = 布尔函数 over 全体句子当前真值），
- 输入端口：`mode: str?`、`sentences: dict?`、`start: dict?`、`max_steps: int?`
- 输出端口：`verdict: str`、`detail: dict`、`boundary: str`
- 可独立运行：是（自带自测）

## 场景库（真实输入 + 期望 + 对照 + 复核）

### `engine/scenarios/review_marks.py`

- 做什么：review_marks.py — 场景复核落笔（把人的复核判断写回场景表）
- 端口：未声明 `PORTS`
- 可独立运行：是（自带自测）

### `engine/scenarios/scenarios.py`

- 做什么：scenarios.py — 场景库（真实输入 + 期望诊断 + 复核状态）
- 输入端口：`action: str?`、`scene_id: str?`
- 输出端口：`verdict: str`、`scenes: list`、`report: list`、`boundary: str`
- 可独立运行：是（自带自测）

## AI 挂载层（function-calling 工具与契约快照）

### `engine/ai/ai_scenarios.py`

- 做什么：ai_scenarios.py — AI 挂载层：2 个真实场景端到端演示（阶段 6 验收）
- 端口：未声明 `PORTS`
- 可独立运行：是（自带自测）

### `engine/ai/freeze_tool_schema.py`

- 做什么：freeze_tool_schema.py — 工具协议冻结：生成快照 JSON + 调用方文档
- 输入端口：`check: bool?`
- 输出端口：`verdict: str`、`changed: list`、`boundary: str`
- 可独立运行：是（自带自测）

### `engine/ai/tools.py`

- 做什么：tools.py — AI 挂载层：function-calling 工具封装（阶段 6）
- 输入端口：`action: str?`、`name: str?`、`arguments: dict?`
- 输出端口：`verdict: str`、`tools: list`、`result: dict`、`boundary: str`
- 可独立运行：是（自带自测）

## 其它（数学底座等根目录模块）

### `engine/cli.py`

- 做什么：cli.py — paradox-engine 命令行入口（AI 挂载层 · 阶段 6 扩展）
- 端口：未声明 `PORTS`
- 可独立运行：是（自带自测）
