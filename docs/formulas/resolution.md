# 公式卡：一阶归结构件（resolution）

> 概念来源：经典自动定理证明（Robinson 归结 + 合一）——非落落原创，经典共识
> 代码：engine/classical/resolution.py · 测试：engine/classical/test_resolution.py
> 与 1.3 区别：1.3 只判有限论域（展开）；1.4 给一般一阶公式的证明尝试
> （Skolem + 合一 + 归结反证）——经典自动推理的"真机器"。

## 一、导言

把 ¬结论 并入前提 → 全部子句化（含 Skolem 化消 ∃）→ 用合一 + 归结反复
推到**空子句** ⇒ 前提∪¬结论不可满足 ⇒ 结论有效。产出归结链（白箱：
每步两子句 + mgu + 归结式）。

## 二、核心部件

### 子句化
1. 消 → ↔；
2. ¬ 内移（De Morgan + 量词对偶）；
3. Skolem 化：∃x φ(x) → φ(c)（新常量，记录 skolem_used）；
4. 拆 ∧ 成子句。

### 合一 mgu
```
unify(t1, t2):
  变量 x 与项 → x:=t（occurs check 防 x=f(x)）
  函数同构递归合一
  常量=常量同则成功
```
**变量/常量区分是正确性前提**：量词绑定的名字 = 变量（var），其余 = 常量
（const）——否则 '柏拉图' 会被当变量与 x 合一（错误 proved）。

### 归结
从 C1∨L1、C2∨¬L2（L1/L2 经 mgu 合一）→ C1σ ∨ C2σ；
得空子句 ⇒ 反证成立。

## 三、性质（P）

- P1 可靠：归结只产生逻辑后承（保真）；
- P2 常量≠变量：量词外名字是常量，不参与变量合一；
- P3 Skolem 白箱：∃ 消去的新符号记录（skolem_used）；
- P4 not_proved ≠ 不可证：一阶半可判定，步数内没找到即诚实标注。

## 四、公式（判定结构）

```
run({premises, facts, conclusion, max_resolvents})
  ├─ 缺 conclusion → conclusion_pending
  ├─ 解析/子句化失败 → parse_error
  ├─ 归结得空子句 → proved（附归结链）
  └─ 无新归结式/步数超限 → not_proved（诚实标注）
```

## 五、注记与边界

- **occurs check 必做**（防 x=f(x) 无限合一）；
- **常量/变量标注**（annotate_terms）：合一正确性的关键——回归逮住过
  "柏拉图当变量"的假 proved bug；
- 子句化可指数膨胀：max_resolvents 限制（默认 500）+ 诚实报告；
- 输出归结链 + mgu + skolem_used（白箱可复核）。
