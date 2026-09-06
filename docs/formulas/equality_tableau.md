# 公式卡：等词 + 表列法（equality_tableau）

> 概念来源：经典逻辑（等词替换语义 + tableau 证明方法）——非落落原创，经典共识
> 代码：engine/classical/equality_tableau.py · 测试：engine/classical/test_equality_tableau.py

## 一、导言

两块能力：
1. **等词 =**：a=b 的对象可互相替换——建模"同一对象不同名字"
   （晨星=暮星/水=H₂O/超人与克拉克）；
2. **表列法 tableau**：树形反证——把 ¬结论 展开成公式树，全支闭则
   有效；开放分支 = 反例模型。

## 二、判定原理

### 等词替换
```
等词事实 a=b, b=c → union-find 建 常量→代表元 映射
→ 所有公式中的常量替换为代表元
（替换后 喜欢(晨星,c) → 喜欢(暮星,c)，问题变成纯命题/地面判定）
```

### 命题 tableau
```
判定 premises ∧ ¬conclusion 是否可满足：
  公式集 → 展开规则（∧同支/∨分叉/→分叉/¬De Morgan）
  闭合检查：A 与 ¬A 同支 → 闭
  全部支闭 → 不可满足 → 结论有效
  有开放分支 → 可满足 → 反例模型（前提真结论假）
```

## 三、性质（P）

- P1 有效 ⟺ premises∧¬conclusion 不可满足（反证核心）；
- P2 等词替换：a=b 下 φ(a) ⟺ φ(b)（替换公理）；
- P3 反例模型：invalid 时开放分支 = 前提真结论假的指派；
- P4 命题 tableau 可判定且完备（有限树穷尽）。

## 四、公式（判定结构）

```
run({premises, conclusion, equality, max_expand})
  ├─ 缺 conclusion → conclusion_pending
  ├─ 解析失败 → parse_error
  ├─ 全支闭 → valid
  ├─ 展开超限 → undetermined（诚实）
  └─ 开放分支 → invalid + 反例模型
```

## 五、注记与边界

- **首期无量词**：带 ∀/∃ → parse_error（诚实报告不支持，不硬算）——
  一阶 tableau 有界实例化（max_expand）留扩展；
- 等词事实必须 a=b 形状（union-find 前校验）；
- 展开上限 max_expand（默认 30）→ undetermined 是合法输出
  （诚实：可能还需展开才能判）；
- 开放分支输出给人看（反例模型白箱）。
