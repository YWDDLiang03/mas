# 怎样比较评价标准

[English](../reference/cqa-comparison.md) · [组件实现](../components/evaluation-and-recovery.md) · [合成示例](../../config/examples/criterion-comparison.synthetic.json)

先比较科学含义，再统计对应数量。标准名称之外，还需要核对测量对象、人群或实验条件、单位、依据类型，以及用于准入还是评分。

## 比较步骤

1. 固定两套标准及其版本。
2. 明确每条标准的量、单位、条件、依据和用途。
3. 对应相同含义，记录阈值、方向或人群差异。
4. 保留未对应和待澄清条目，每条基线标准只计一次。
5. 标准比较与候选排名分别报告。

## 合成示例

以下条目仅用于说明比较格式，不是研究测量结果。

| 较早定义 | 后续定义 | 对应含义 |
|---|---|---|
| 实测粒径 ≤150 nm，必须满足 | 测量、条件与必需阈值相同 | 同一操作性标准 |
| 实测细胞活力 ≥80%，必须满足 | 同一测量，数值越高评分越高 | 测量相关，决策用途不同 |
| 实验 A 下的递送效率 | 实验 B 下的摄取量 | 关系待澄清，需核对不同终点和条件 |

[JSON 示例](../../config/examples/criterion-comparison.synthetic.json)明确标记为合成材料。实际比较由用户提供获准使用的基线及生成标准。

## 实现与访问

[`recovery.py`](../../src/mas/core/recovery.py)检查映射、计数、来源标签和评价者访问；[`freeze.py`](../../src/mas/core/freeze.py)保存策略与版本。公开报告可以提供汇总计数，基线全文及逐项映射按私有材料管理。见[公开内容规范](../reference/public-content.md)。
