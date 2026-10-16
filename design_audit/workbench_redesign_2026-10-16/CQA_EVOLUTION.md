# 从空 CQA 到评估方案：实际演化记录

**CQA 生成与三轮提炼已完成。** Snapshot 1 时的结果是 43 条当前注册标准、11 条未注册待处理提案；
严格冻结 `rules@v2` 启用其中 24 条，延后 19 条。两条 logP 后续数学修订已复核并产生 `rules@v3`，
新筛选已完成并发布 snapshot 2：24 个执行条目对应 23 个独立决策问题；
不把 24 当作生成结束时的全部标准数量，也不把未解决提案隐藏成已完成。

任务 `task_01M51AQ0JK0MYN47806ZD5XS1B`；工作流 `wf_033db93e15fa4bb289c2e03606674f6b`。
原始阶段与逐条历史：[stages.json](final/wf_033db93e15fa4bb289c2e03606674f6b/stages.json)、
[source-cqa-history.json](final/wf_033db93e15fa4bb289c2e03606674f6b/source-cqa-history.json)、
[cqa.json](final/wf_033db93e15fa4bb289c2e03606674f6b/cqa.json)。这些文件属于 snapshot 1 导出，原记录保留。
Snapshot 2 已另行导出：[新 cqa.json](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/cqa.json)、
[新原始历史](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/source-cqa-history.json)、
[新 manifest](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/manifest.json)。

## 起点与证据范围

[full-run-start.json](../../var/workbench-v2-acceptance/full-run-start.json) 明确记录初始 registry=0、pool=0。
新任务从固定已保存证据生成 CQA，不继承旧任务的规则、裁决或排名。
事实 manifest `art_a3ad5ef89e0b` 固定 3,157 个去重事实、164 个来源；参考候选专属内容不参与标准派生，
但对称评估仍可使用已固定事实。候选 library 为 3,177 项，续跑和评估前核对其固定 hash。
本轮 existing_only，不新搜文献、不重读全文。

先建立 6 个任务绑定：5 个必需靶点的独立证据标准与 1 个口服硬条件。
任务绑定 Added=6 来自真实创建事件及 stage.result 引用，一对属性/规则计一条，不重复计成 12。
原始记录核对见 [Added 验证](postrun_criteria_scope/validation.json)。

## 真实 0→多→精数量

下表的阶段口径均为 `active_registered_plus_unregistered_proposals`，含任务绑定及当前工作提案。
“修改”是事件统计，不等于新增独立标准；合并同时保留新 child 和原 parent 记录。

| 阶段 | 轮次 | 前→后 | 新增 | 修改 | 合并父条目 | 移除 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 固定证据准备 | 0 | 0→0 | 0 | 0 | 0 | 0 |
| 任务绑定 | 0 | 0→6 | 6 | 0 | 0 | 0 |
| 靶点标准生成 | 0 | 6→374 | 368 | 0 | 0 | 0 |
| 口服生物利用度生成 | 0 | 374→866 | 492 | 0 | 0 | 0 |
| 代谢稳定性，原 run 中断 | 0 | 866→未知 | 270 | 0 | 0 | 0 |
| 代谢稳定性，版本化续跑 | 0 | 1,136→1,262 | 126 | 0 | 0 | 0 |
| 安全性生成 | 0 | 1,262→1,807 | 545 | 0 | 0 | 0 |
| Filter | 1 | 1,807→1,072 | 0 | 931 | 0 | 735 |
| Distill | 1 | 1,072→1,019 | 0 | 26 | 0 | 53 |
| Refine | 1 | 1,019→185 | 0 | 90 | 0 | 834 |
| Merge | 1 | 185→106 | 30 | 0 | 109 | 0 |
| Filter | 2 | 106→96 | 0 | 36 | 0 | 10 |
| Distill | 2 | 96→96 | 0 | 3 | 0 | 0 |
| Refine | 2 | 96→69 | 0 | 20 | 0 | 27 |
| Merge | 2 | 69→66 | 3 | 0 | 6 | 0 |
| Filter | 3 | 66→66 | 0 | 16 | 0 | 0 |
| Distill | 3 | 66→62 | 0 | 13 | 0 | 4 |
| Refine | 3 | 62→54 | 0 | 8 | 0 | 8 |
| Merge | 3 | 54→54 | 0 | 0 | 0 | 0 |
| Promote | 0 | 54→54 | 0 | 42 | 0 | 0 |

峰值 **1,807 = 6 个任务绑定 + 1,801 个原始提案**。
原中断阶段没有 closed/after 记录，不能伪造其完成值；1,136 是安全续跑已保存工作集的入口，
由完整批次及固定 manifest 顺序恢复。生成主 run 从 `run_01M51AQ43WQQPDQZVD9GADSVTB`
版本化续接到 `run_01M51DNTG28TNJ16JBMNBBZWFB`，旧绑定和失败/中断状态保留。
[续跑证据](../../var/workbench-v2-acceptance/continuation-start.json)。

Promote 的 54→54 表示身份/注册状态改变，不是又新增 37 个标准；其中 37 个提案注册，
加原 6 个任务绑定得到 43 条注册，余下 11 个仍在 pool 等待处理。

## 注册、延后与启用分别报告

| Snapshot 1 口径 | 实际数量 | 解释 |
| --- | ---: | --- |
| 当前工作集 | 54 | 43 注册 + 11 未注册待处理 |
| 当前注册标准 | 43 | 1 hard、41 preference、1 context |
| 当前待复核注册标准 | 14 | 未解决的复核状态，不因主工作流完成而改为通过 |
| 最近评估已延后 | 19 | 14 unresolved_review + 5 non_executable_preference |
| 最近评估已启用 | 24 | 1 hard、22 preference、1 context；是参与评估数，不全是偏好分数 |
| 历史列表索引条目 | 1,840 | 保留合并、撤回等历史条目，不作为最终独立标准数 |

来源：[overview.json](final/wf_033db93e15fa4bb289c2e03606674f6b/overview.json)、
[最近冻结状态验证](postrun_evaluation_status/validation.json)。`rules@v2` 原冻结 artifact 为 `art_039fe32dbd20`。
14 个待复核是 19 个已延后中的一部分，不能再相加算成 33。
数量约 10–30 是软目标，保留有意义的独立标准和未解决项优先，不为目标数量隐藏条目。

## 逐条谱系和前后版本的实际访问

真实合并示例 `cri_01M51GW2QDP58C6CYM8PA889PT@v1`（CSF1R engagement on record）链接两个原父版本：

- `cri_01M51ASBG7FE3ZQ9VTA8PTJJH5@v1`；
- `cri_01M51BGY30T4YP2D2BEF8YAMH8@v1`。

父版本保留各自原定义；child 的 merge `before=null` 是新建，不能把父内容伪造成 child 旧版。
实际 GUI 已选择 merge iteration 1，搜索得到 3 个相关变更，点击父 v1 后仍保留阶段和搜索。
[结构化 GUI 证明](../../var/workbench-v2-acceptance/cqa-gui-proof.json)、
[确切版本 AX](../../var/workbench-v2-acceptance/browser/cqa-lineage-saved-version.txt)。

注册后的修订沿真实 `supersedes` 读取：属性前后只比较属性，规则前后只比较规则，
`workbench_revision.reason` 说明修订，不沿用旧 rationale 冒充原因。
LD50 v1→v2 的方向修正和理由已经实际展示：[AX](../../var/workbench-v2-acceptance/browser/criterion-math-revision-history.txt)。
Pool 阶段使用确切 change 引用，即使同一版本后来改变状态，也不静默跳到新状态。

MW v2 是不同于注册 Active 的评估 Deferred：证据路线已版本化修复，但原截点的复核仍未解决，
所以未进入 `rules@v2` 的 24 条评估标准。[实际 Pending 详情](../../var/workbench-v2-acceptance/browser/pending-criterion-reason.txt)。
两条 logP 已保留各自来源/算法并修正区间距离语义，显式声明共享 `quantity_id`，
通过既有 direct-first 对同一 2–4 决策问题去重；预测旁证不加第二分，其他阈值或决策含义不同的标准仍分别保留。
根任务报告 `rules@v3` 已完成新复核和冻结，仍为 24 个执行/启用记录、19 个延后、43 个注册和 11 个 pool 待处理。
[新冻结只读核对](../../var/workbench-v2-acceptance/snapshot2-freeze-readonly-check.json) 已确认：24 执行条目（22 preference、1 hard、1 exploratory）对应
23 个独立决策问题（21 preference、1 hard、1 exploratory）。两条 logP 的机器复核均为
`agent_verdict / bound_interpretation_granted / approve`，没有人工审批。
[实际 logP 新版与差异](../../var/workbench-v2-acceptance/browser/logp-v2-review-and-diff.txt) 及 [截图](../../var/workbench-v2-acceptance/browser/logp-v2-review-and-diff.jpg) 已留存。
新源码 [14a4047b…](../../var/provenance/workbench-v2/14a4047b794d1696/manifest.json) 已归档。最终 run `run_01M51RRJ8Y3D5DYAQGMYPY13AP` 已发布
`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_2`，profile `art_9d00e221a8fc`。
最终 CQA 口径为 **43 注册 + 11 pool 待处理；24 启用记录 = 23 独立决策（21 preference、1 hard、1 exploratory）；19 注册条目延后**。
实际 API 结果为全库 3,177、10 qualified/3,167 pending，Surufatinib qualified、位置 4/10、score 0.6629629629629631，
硬条件 1/1、必需靶点 5/5、直接偏好证据覆盖 0.5238095238095238。新导出与 [22 项独立 source/API/CSV/score 核验](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) 均已通过。
全部 76,248 单元和 3,177 候选重算一致；两条 logP 的 6,354 单元中，2,956 个可用值逐一按原 claim 的
`median(max(2-x,0,x-4))` 复核一致。每个合格并排名候选实际使用 15 个偏好值，同量预测旁证未作为第二票。
实际 GUI 已完成 [旧快照保留](../../var/workbench-v2-acceptance/browser/snapshot1-switch-preserved.txt) 与
[新快照切换/刷新](../../var/workbench-v2-acceptance/browser/snapshot2-switch-refresh.txt)，原 v1 与修订 v2 的结果均可访问。
最终科学结果、文件交付和已完成的生产 8769 交接见 [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md)。
正式端已实际展示 0→6→1,807→54、Enabled 24 和 28 个已记录阶段：
[production-cqa.txt](../../var/workbench-v2-acceptance/browser/production-cqa.txt)、
[截图](../../var/workbench-v2-acceptance/browser/production-cqa.jpg)。24 执行记录与 23 独立决策的口径继续按上述核验分别说明。
不重跑已经完成的 CQA 生成，也不回写上述历史阶段。
