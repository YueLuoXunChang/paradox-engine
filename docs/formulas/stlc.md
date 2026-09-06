# 公式卡：简单类型 λ（STLC）（stlc）

> 概念来源：经典类型论（Church 简单类型 + Curry-Howard 对应）——非落落原创，经典共识
> 代码：engine/classical/stlc.py · 测试：engine/classical/test_stlc.py

## 一、导言

STLC（Simply Typed Lambda Calculus，简单类型 λ 演算）——给 λ 项加上
类型，用类型规则 Γ ⊢ M : A 判定"这个程序合不合法"。

首期做**类型检查与推导**（双向：自动推导 + expected 校验），并挂上
Curry-Howard 对照（类型 = 命题、程序 = 证明）。

与 1.6（无类型 λ）**双视角对照**是本构件的定位：
- 1.6 给 Y 组合子——无类型自指，可写 Ω（不死循环）；
- 1.9 用类型**拦住自应用**——`λx:A.x x` 报 type_error，类型正确
  ⇒ 必然终止（强规范化）；
- 结论：**类型能阻止不死循环，代价是表达力下降（不能 Y）**。

## 二、判定原理

### 类型语法与项语法
```
类型 T ::= A | T→T（→ 右结合）
项   M ::= x | λx:T.M | M M      （应用左结合；λ 参数需类型标注）
```

### 类型规则（Curry-Howard 内核）
```
变量      x:T ∈ Γ                    Γ,x:A ⊢ M:B
        ───────── (var)              ──────────────── (→引入)
        Γ ⊢ x:T                      Γ ⊢ λx:A.M : A→B

         Γ ⊢ f:A→B    Γ ⊢ a:A
        ──────────────────────── (→消去/应用)
              Γ ⊢ f a : B
```

### 类型检查流程
```
expr → 解析成 AST（var/lam/app）
     → 上下文 ctx 建表（{变量: 类型}）
     → 自上而下推导（双向）：
         var   → 查上下文，缺 → type_error（未声明变量）
         lam   → 缺标注 → type_error（STLC 需显式类型）
         app   → 函数侧非 → 型 → type_error
               → 参数类型 ≠ 期望 → type_error（含自应用 x x）
     → expected 给了再校验一遍（不符 → type_error）
     → 全过 → typed + 推断类型 + 推导树
```

## 三、性质（P）

- P1 **强规范化**：STLC 所有可类型化项都终止——无 Ω、无 Y（1.6 对照）；
- P2 **拦自应用**：`x x` 类型必错（A→B 的参数要 A，而 x 已是 A→B）——
  Curry-Howard 下自引用程序无类型 = 自指命题无"证明"；
- P3 **类型唯一**（无多态）：每项至多一个主类型，类型错误可判定；
- P4 **Curry-Howard**：类型 = 命题、程序 = 证明、→引入/消去 =
  → 引入/消去——typed ⇒ 该程序即该类型的构造性证明。

## 四、公式（判定结构）

```
run({expr, context, expected})
  ├─ 缺 expr          → expr_pending（诚实：不硬判）
  ├─ 项解析失败       → parse_error
  ├─ 上下文类型解析失败 → parse_error
  ├─ 变量不在上下文    → type_error
  ├─ λ 缺类型标注      → type_error
  ├─ 应用类型不匹配    → type_error（拦自应用 λx:A.x x）
  ├─ expected ≠ 推断  → type_error
  └─ 全过             → typed + inferred + derivation 白箱
```

## 五、注记与边界

- **首期无多态/依赖类型**：System F、依赖类型（命题即类型升级版）→
  parse_error/type_error（诚实报告不支持，不硬算）——留扩展；
- **类型是显式标注优先**：STLC 需 λx:A.M，不写标注 → type_error
  （不做 Hindley-Milner 全推断——那不是 STLC 的强规范化语义）；
- **type_error 带部分 derivation**：推导到出错处的白箱（诚实——人可
  看错在哪一步）；
- **与 1.6 互补**：1.6 能写 Y/Ω 但不停机，1.9 全停机但写不了 Y——
  两构件并置即"表达力 × 终止性"的经典权衡建模。
