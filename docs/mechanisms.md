# 机制目录（paradox-engine）

> 本仓库就做这三个核心机制（悖论/矛盾检测），不再扩展。
> 每个机制文件自包含：`python engine/mechanisms/<名>.py` 直接跑自测。

## 收录机制（3 个）

| 机制 | 一句话 | 输入要点 | 输出要点 | 状态 |
|---|---|---|---|---|
| paradox_measure | 悖论强度 μ ∈ [0,1]（四分支） | mode + wA/wNotA（mu1）；或自指/层级/熵输入 | mu, branch | ✅ 核心 |
| paradox_annotate | 悖论注解（8 字段卡 + P-A/B/C） | paradox 对象 + source/impact/eliminable | annotation, grade | ✅ 核心 |
| converge_check | 收敛判定（压缩/有限步/渐进/振荡） | branch + f + err_fn + x0 | verdict, converges, rate, detail | ✅ 核心 |

## 为什么是这三个

它们合起来正好讲清"矛盾当第一公民"的完整主张：
1. **测量**（paradox_measure）：矛盾有多尖锐 → 一个数 μ；
2. **注解**（paradox_annotate）：矛盾是什么、哪一层、影响多大 → 一张卡；
3. **判定**（converge_check）：一个迭代过程会不会停下来 → 一个结论。

体系本体的其余机制不在本仓库（也不打算并入）。
