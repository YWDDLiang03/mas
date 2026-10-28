# 案例运行与补充数据

[English](README.md) · [案例教程](../../../../docs/zh/tutorial.md) · [字段说明](data-dictionary.md) · [分析说明](analysis-notes.md) · [校验清单](manifest.json)

这份数据整理了当前口服多靶点案例的任务、标准演化、候选分类、分数和来源观测，可用于研究报告与论文补充数据。通用系统设计见[流程说明](../../../../docs/zh/design.md)，本页数量和结果对应这一项案例。

[下载完整数据包](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/TRIAGE-oral-multitarget-source-data-20261028.zip)，[下载记录](../source-data-download.json)提供大小和 SHA-256。包内包含数据表、来源记录、原公开研究导出和离线核对脚本。论文正文与图稿另行保存。

## 本次运行

任务要求寻找单一口服药物，覆盖 CSF1R、VEGFR1、VEGFR2、VEGFR3 和 FGFR1，候选库包含 3,177 个化合物。标准从空集开始，先纳入六项任务要求，充分展开至 1,917 项工作条目，再经过三轮提炼，分别收敛到 147、68、53 项。

最终六项准入要求与 17 项评分标准共享五项靶点标准，共 18 项独立评价标准，另有 13 项解释性观察。31 项逐候选评估形成 98,487 条记录。22 项保留条目未进入本次评价，具体原因列在标准表中。

保存工作流运行于 **2026 年 10 月 16 日 20:52 至 17 日 00:25（UTC+8）**，历时 3 小时 32 分 42 秒；使用已有证据、mid 工作量、并发上限 4、原预算 5.50 美元。325 次模型请求记录了 5,997,812 个输入 token、2,009,003 个输出 token，费用估计为 4.2101472 美元。详见[运行摘要](run-summary.json)、[各阶段与角色消耗](AI_Data_10_model_usage.csv)及[阶段时间](workflow-phases.csv)。本次数据整理日期为 2026 年 10 月 28 日。

## 数据表

| 数据 | 行数 | 可以回答的问题 |
|---|---:|---|
| [1. 最终标准](AI_Data_1_final_criteria.csv) | 53 | 每项标准测什么、怎样用，哪些尚未纳入评价 |
| [2. 候选结果](AI_Data_2_candidate_results.csv) | 3,177 | 候选属于哪组，具备哪些准入依据，分数和名次是多少 |
| [3. 逐项评估](AI_Data_3_candidate_assessments.csv.gz) | 98,487 | 每个候选在每项标准上的值、状态、证据类型和来源；仓库中为 gzip 压缩 CSV |
| [4. 合格候选评分](AI_Data_4_eligible_candidate_scores.csv) | 170 | 十个合格候选各自的 17 项分数如何形成总分 |
| [5. 标准阶段](AI_Data_5_criterion_stages.csv) | 25 | 展开与提炼如何改变数量，以及本任务两次保存评估的时间 |
| [6. 标准依据](AI_Data_6_criterion_basis.csv) | 17 | 哪些评分标准来自任务，哪些由证据推导，方向和选择依据是什么 |
| [7. 靶点原始观测](AI_Data_7_target_observations.csv) | 1,348 | 238 个靶点汇总值来自哪些端点、实验、物种和来源 |
| [8. 去除预测贡献的对照](AI_Data_8_without_predictions.csv) | 10 | 固定原合格集合，去除 ADMET 预测贡献后名次怎样变化 |
| [9. IC50 对照](AI_Data_9_IC50_comparison.csv) | 10 | 固定原合格集合，只使用 IC50／pIC50 汇总靶点数值时怎样变化 |
| [10. 模型消耗](AI_Data_10_model_usage.csv) | 18 | 各阶段、轮次和角色用了多少请求、token 与估计费用 |

[合格候选榜](eligible-leaderboard.csv)便于直接查看十个候选。全部分类为 **10 Eligible、1,305 Evidence incomplete、1,862 Excluded**。Surufatinib 排名第一，15 项可用评分值形成总分 0.7592592593，直接评分证据覆盖为 10/17。

`source_records/` 保存标准定义、证据集合、生成子集、标准依据、靶点观测、运行设置、模型标识和观测核对结果。[来源索引](source-index.json)连接已公开的完整标准历史、任务、快照、运行配置和模型消耗，并给出文件校验值；完整 ZIP 将它们收在 `study_exports/` 下。

## 如何核对与复算

在当前仓库根目录执行：

```sh
python scripts/build_case_source_data.py
```

脚本核对全部分类、评估关联和文件，重算十个合格候选的分数、238 个靶点中位数，以及已经完成的两项评分对照。仅使用 Python 标准库和保存的数据。

生成完整 ZIP：

```sh
python scripts/build_case_source_data.py --output var/TRIAGE-oral-multitarget-source-data-20261028.zip
```

直接下载 ZIP 后，在解压目录运行 `python tools/build_case_source_data.py`。其中表 3 已解压为普通 CSV。需要通过系统引擎回放，或用保存证据重新开展研究，继续按[智能体运行说明](../../../../docs/zh/agent-run.md)操作。

表 8、9 是原合格集合内的对照分析；表 9 保持原准入集合与非靶点评分，七个候选达到该计算中的覆盖门槛。两项对照中 Surufatinib 均为第一。端点混合、重复记录及缺失信息的具体处理见[分析说明](analysis-notes.md)。
