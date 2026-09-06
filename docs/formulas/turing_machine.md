# 公式卡：图灵机构件（turing_machine）

> 概念来源：经典可计算性理论（Turing 1936）——非落落原创，经典共识
> 代码：engine/classical/turing_machine.py · 测试：engine/classical/test_turing_machine.py
> 与体系咬合：UTM 自模拟 = 图灵机级自指；停机不可判定 = 可演示的
> "收编为标本"结果。

## 一、导言

图灵机 = 纸带 + 读写头 + 状态 + 规则表的最简计算模型。它是"可计算"的
精确定义（邱奇-图灵论题），也是理解"什么算得出来、什么算不出来"的地基。

## 二、形式化

```
TM = (Q, Σ, Γ, δ, q0, q_accept, q_reject)
  Q 状态集；Σ 输入符号；Γ 纸带符号（含空白 ⊔）
  δ: Q×Γ → Q×Γ×{L,R} 转移函数
格局 = (状态, 读写头位置, 纸带内容)
```

## 三、性质（P）

- P1 邱奇-图灵论题：图灵机 = λ 演算 = 递归函数（同一可计算类）；
- P2 通用机：存在 UTM 模拟任意 TM——**UTM 能模拟自己（自指的计算形态，
  可运行非悖论）**；
- P3 停机不可判定：不存在 H 判定任意 ⟨M⟩ 停机（对角化 D(⟨D⟩) 矛盾）——
  这是定理，引擎如实报 undecidable；
- P4 模拟器诚实性：跑 N 步未停 = steps_exceeded，**不是"永不停"判定**。

## 四、公式（判定结构）

```
run({program, input, mode})
  ├─ simulate：跑 TM → accept / reject / steps_exceeded / halt_undefined
  ├─ self_simulate：⟨M⟩ 喂给 M → self_simulated_*（自指可运行）
  └─ halting_demo：停机问题 → undecidable + 对角化说明
```

## 五、注记与边界

- **停机问题 = undecidable 判定结果**：引擎不宣称绕过（那是伪数学）——
  收编为标本：μ₂ 自指测度=1 → 注解 P-A 结构性（41 详规接缝）；
- 模拟器步数上限默认 10000，超限报 steps_exceeded（诚实）；
- 自模拟的完整版需 ⟨M⟩ 编码语法化（把机器定义编码成纸带串）——本版给
  结构演示（机器模拟自己运行），完整编码后补；
- 与 1.6 λ 演算互为表里：Y 组合子（λ 级自指）与 UTM 自模拟（机器级自指）
  是同一"自指可计算"的两种形态。
