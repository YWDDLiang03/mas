# 工作流最终记录与验收报告

这是已完成工作流发布快照的记录导出。工作流完成表示处理结束；科学结论按以下真实资格、覆盖与未知状态陈述。

- 工作流：`wf_cb4caec3dec348908fb3d34eae5b11d1`
- 任务：`task_01M52CBE5GYPK9F0MCZYBMPH84`
- 快照：`lb_task_01M52CBE5GYPK9F0MCZYBMPH84_1`
- 模式：staged；资格政策：qualification_first_v1
- Readiness：ready；结果类型：both_reported
- 弃权／无推荐原因：未知／未记录

## 数量与覆盖

候选总数 **3177**；qualified **6**；其余状态：{"qualified": 6, "pending": 3171}。
CSV 实际行数 **3177**，已与原始 snapshot 及完整 API 候选集合核对。

| 指标 | 原记录 |
|---|---|
| sweep_completeness | 1.0 |
| assessment_completeness | 1.0 |
| direct_coverage_fraction | 0.045833460253637534 |
| coverage_fraction | 0.06614070892605116 |
| recorded_cell_n | 98487 |
| assessed_cell_n | 98487 |
| skipped_after_rejection_n | 0 |
| missing_or_conflicted_n | 91973 |
| error_n | 0 |

缺失、冲突、未评估和拒绝后跳过分别保留；缺失指标表示未知，不补成零。

## Surufatinib 的实际结果

- 候选：`cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N`（["Surufatinib"]）
- 资格：**qualified**；排名：**未排名（原记录 position=null）**；得分：0.8666666666666666
- 偏好覆盖：0.35294117647058826；硬条件证据覆盖：1.0；任务要求覆盖：1.0
- 原资格记录：{"applicable_hard_count": 1, "blocking_hard_rule_refs": [], "failed_hard_rule_refs": [], "hard_blocked": 0, "hard_direct_coverage": 1.0, "hard_failed": 0, "hard_passed": 1, "hard_total": 1, "missing_direct_required_rule_refs": [], "qualified": true, "required_direct_answered": 5, "required_direct_coverage": 1.0, "required_total": 5, "state": "qualified", "verified_hard_count": 1}
- 原因：qualification: qualified；缺失：[]；排名说明：too little preference evidence to rank (coverage 0.35 below 0.50)

## CQA 演化

当前 API 摘要：{"candidate_count": 3177, "criteria_count": 45, "hard_count": 1, "preference_count": 31, "task_required_count": 6, "pending_count": 5, "pending_review_count": 5, "historical_pending_review_count": 0, "active_registered_count": 45, "historical_registered_count": 45, "retired_latest_count": 0, "additional_unregistered_active_count": 8, "unresolved_pool_count": 8, "total_active_count": 53, "scoring_count": 31, "scoring_in_latest_frozen_set_count": 31, "deferred_count": 14, "registered_pending_count": 0, "latest_frozen_rule_set_ref": "rules@v1", "reduction_run_id": null, "historical_criteria_count": 1968, "run_count": 3, "claim_count": 15126}。

阶段数量严格保留 count_basis；工作提案数量与当前注册数量按各自口径显示。下面的未知边界保留为空缺，完整版本、变更与 lineage 见 cqa.json 和 source-cqa-history.json。

| 阶段 | 迭代 | 计数口径 | 前 → 后 | 新增 | 修改 | 合并 | 移除 |
|---|---:|---|---|---:|---:|---:|---:|
| evidence | 0 | active_registered_plus_unregistered_proposals | 0 → 0 | 0 | 0 | 0 | 0 |
| mandated | 0 | active_registered_plus_unregistered_proposals | 0 → 6 | 6 | 0 | 0 | 0 |
| propose:target_coverage | 0 | active_registered_plus_unregistered_proposals | 6 → 293 | 287 | 0 | 0 | 0 |
| propose:oral_bioavailability | 0 | active_registered_plus_unregistered_proposals | 293 → 504 | 211 | 0 | 0 | 0 |
| propose:metabolic_stability | 0 | active_registered_plus_unregistered_proposals | 504 → 1192 | 688 | 0 | 0 | 0 |
| propose:toxicological_safety | 0 | active_registered_plus_unregistered_proposals | 1192 → 1917 | 725 | 0 | 0 | 0 |
| filter | 1 | active_registered_plus_unregistered_proposals | 1917 → 1373 | 0 | 1215 | 0 | 544 |
| distill | 1 | active_registered_plus_unregistered_proposals | 1373 → 1337 | 0 | 24 | 0 | 36 |
| refine | 1 | active_registered_plus_unregistered_proposals | 1337 → 291 | 0 | 158 | 0 | 1046 |
| merge | 1 | active_registered_plus_unregistered_proposals | 291 → 147 | 45 | 0 | 189 | 0 |
| filter | 2 | active_registered_plus_unregistered_proposals | 147 → 109 | 0 | 53 | 0 | 38 |
| distill | 2 | active_registered_plus_unregistered_proposals | 109 → 97 | 0 | 4 | 0 | 12 |
| refine | 2 | active_registered_plus_unregistered_proposals | 97 → 78 | 0 | 34 | 0 | 19 |
| merge | 2 | active_registered_plus_unregistered_proposals | 78 → 68 | 6 | 0 | 16 | 0 |
| filter | 3 | active_registered_plus_unregistered_proposals | 68 → 63 | 0 | 28 | 0 | 5 |
| distill | 3 | active_registered_plus_unregistered_proposals | 63 → 62 | 0 | 1 | 0 | 1 |
| refine | 3 | active_registered_plus_unregistered_proposals | 62 → 53 | 0 | 19 | 0 | 9 |
| merge | 3 | active_registered_plus_unregistered_proposals | 53 → 53 | 0 | 0 | 0 | 0 |
| promote | 0 | active_registered_plus_unregistered_proposals | 53 → 53 | 0 | 44 | 0 | 0 |
| identity | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| assess | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| snapshot | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 未知／未记录 | 未知／未记录 | 未知／未记录 | 未知／未记录 |

## 模型用量与费用估算

仅累计本工作流时间窗内的 agent.finished 聚合；内部 provider_attempt 不重复相加。前两次停止运行费用由操作者另行合并，本脚本没有将其加到本次费用。

已知费用小计：**4.2101472 USD**；状态：**estimated**。
工作流预算原记录：{"used_usd": 4.210147199999997, "limit_usd": 5.5, "cost_status": "recorded_estimate"}。未结束的模型逻辑请求：0。

| 阶段／操作 | 角色 | 请求 | 输入 token | 输出 token | 已知 USD | 费用状态 |
|---|---|---:|---:|---:|---:|---|
| propose / propose:metabolic_stability | proposer | 16 | 479712 | 294361 | 0.4971468 | estimated |
| propose / propose:oral_bioavailability | proposer | 16 | 427722 | 141658 | 0.2983062 | estimated |
| propose / propose:target_coverage | proposer | 21 | 501355 | 171136 | 0.3557697 | estimated |
| propose / propose:toxicological_safety | proposer | 18 | 697311 | 332904 | 0.6086781 | estimated |
| refine / distill | proposer | 7 | 179208 | 23936 | 0.0824856 | estimated |
| refine / distill | proposer | 3 | 86556 | 5771 | 0.032892 | estimated |
| refine / distill | proposer | 2 | 52512 | 2652 | 0.018936 | estimated |
| refine / filter | critic | 42 | 649138 | 502910 | 0.7982334 | estimated |
| refine / filter | critic | 3 | 94636 | 31931 | 0.066708 | estimated |
| refine / filter | critic | 1 | 44685 | 13669 | 0.0298083 | estimated |
| refine / merge | adjudicator | 13 | 233905 | 144964 | 0.2441283 | estimated |
| refine / merge | adjudicator | 2 | 33408 | 36399 | 0.0537012 | estimated |
| refine / promote | critic | 1 | 38340 | 11430 | 0.025218 | estimated |
| refine / refine | proposer | 152 | 2232699 | 214710 | 0.9274617 | estimated |
| refine / refine | proposer | 7 | 121957 | 26564 | 0.0684639 | estimated |
| refine / refine | proposer | 4 | 87907 | 18209 | 0.0482229 | estimated |
| review / — | adjudicator | 16 | 35306 | 35395 | 0.0530658 | estimated |
| task / — | proposer | 1 | 1455 | 404 | 0.0009213 | estimated |

## 核对与保留项

核对原记录：{"workflow_completed": true, "snapshot_present": true, "snapshot_run_matches_workflow": true, "snapshot_candidates": 3177, "csv_rows": 3177, "api_candidate_rows": 3177, "csv_and_api_candidate_id_multisets_match_snapshot": true, "source_publication_rowid": 1862200, "surufatinib_match_status": "found", "snapshot_readiness": "ready", "scientific_success_claimed": false, "cqa_api_as_of": "2026-10-16T15:31:44.626Z", "cqa_source_history_scope": "selected task through this snapshot publication", "excluded_cqa_artifacts": []}。

本报告不自动声称研究成功、找到了合格候选或达到了参考药物目标。资格为 pending/not_ready、排名为空、覆盖不足和费用未知均按原记录保留。

完整候选：[candidates.csv](candidates.csv)、[candidates.json](candidates.json)、[snapshot.json](snapshot.json)；模型记录：[model-accounting.json](model-accounting.json)；导出范围与文件校验和见 manifest.json。
