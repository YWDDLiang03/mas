# 工作流最终记录与验收报告

这是已完成工作流发布快照的记录导出。工作流完成表示处理结束；科学结论按以下真实资格、覆盖与未知状态陈述。

- 工作流：`wf_033db93e15fa4bb289c2e03606674f6b`
- 任务：`task_01M51AQ0JK0MYN47806ZD5XS1B`
- 快照：`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_1`
- 模式：staged；资格政策：qualification_first_v1
- Readiness：ready；结果类型：both_reported
- 弃权／无推荐原因：未知／未记录

## 数量与覆盖

候选总数 **3177**；qualified **10**；其余状态：{"qualified": 10, "pending": 3167}。
CSV 实际行数 **3177**，已与原始 snapshot 及完整 API 候选集合核对。

| 指标 | 原记录 |
|---|---|
| sweep_completeness | 1.0 |
| assessment_completeness | 1.0 |
| direct_coverage_fraction | 0.25911499318014897 |
| coverage_fraction | 0.42578165984681565 |
| recorded_cell_n | 76248 |
| assessed_cell_n | 76248 |
| skipped_after_rejection_n | 0 |
| missing_or_conflicted_n | 43783 |
| error_n | 0 |

缺失、冲突、未评估和拒绝后跳过分别保留；缺失指标表示未知，不补成零。

## Surufatinib 的实际结果

- 候选：`cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N`（["Surufatinib"]）
- 资格：**qualified**；排名：**4**；得分：0.6074074074074075
- 偏好覆盖：0.5；硬条件证据覆盖：1.0；任务要求覆盖：1.0
- 原资格记录：{"applicable_hard_count": 1, "blocking_hard_rule_refs": [], "failed_hard_rule_refs": [], "hard_blocked": 0, "hard_direct_coverage": 1.0, "hard_failed": 0, "hard_passed": 1, "hard_total": 1, "missing_direct_required_rule_refs": [], "qualified": true, "required_direct_answered": 5, "required_direct_coverage": 1.0, "required_total": 5, "state": "qualified", "verified_hard_count": 1}
- 原因：qualification: qualified；缺失：[]；排名说明：未知／未记录

## CQA 演化

当前 API 摘要：{"candidate_count": 3177, "criteria_count": 43, "hard_count": 1, "preference_count": 41, "task_required_count": 6, "pending_count": 14, "pending_review_count": 14, "historical_pending_review_count": 0, "active_registered_count": 43, "historical_registered_count": 43, "retired_latest_count": 0, "additional_unregistered_active_count": 11, "unresolved_pool_count": 11, "total_active_count": 54, "scoring_count": 24, "scoring_in_latest_frozen_set_count": 24, "deferred_count": 19, "registered_pending_count": 0, "latest_frozen_rule_set_ref": "rules@v2", "reduction_run_id": null, "historical_criteria_count": 1840, "run_count": 4, "claim_count": 39600}。

阶段数量严格保留 count_basis；工作提案数量与当前注册数量按各自口径显示。下面的未知边界保留为空缺，完整版本、变更与 lineage 见 cqa.json 和 source-cqa-history.json。

| 阶段 | 迭代 | 计数口径 | 前 → 后 | 新增 | 修改 | 合并 | 移除 |
|---|---:|---|---|---:|---:|---:|---:|
| evidence | 0 | active_registered_plus_unregistered_proposals | 0 → 0 | 0 | 0 | 0 | 0 |
| mandated | 0 | active_registered_plus_unregistered_proposals | 0 → 6 | 6 | 0 | 0 | 0 |
| propose:target_coverage | 0 | active_registered_plus_unregistered_proposals | 6 → 374 | 368 | 0 | 0 | 0 |
| propose:oral_bioavailability | 0 | active_registered_plus_unregistered_proposals | 374 → 866 | 492 | 0 | 0 | 0 |
| propose:metabolic_stability | 0 | active_registered_plus_unregistered_proposals | 866 → 未知／未记录 | 270 | 0 | 0 | 0 |
| propose:metabolic_stability | 0 | active_registered_plus_unregistered_proposals | 1136 → 1262 | 126 | 0 | 0 | 0 |
| propose:toxicological_safety | 0 | active_registered_plus_unregistered_proposals | 1262 → 1807 | 545 | 0 | 0 | 0 |
| filter | 1 | active_registered_plus_unregistered_proposals | 1807 → 1072 | 0 | 931 | 0 | 735 |
| distill | 1 | active_registered_plus_unregistered_proposals | 1072 → 1019 | 0 | 26 | 0 | 53 |
| refine | 1 | active_registered_plus_unregistered_proposals | 1019 → 185 | 0 | 90 | 0 | 834 |
| merge | 1 | active_registered_plus_unregistered_proposals | 185 → 106 | 30 | 0 | 109 | 0 |
| filter | 2 | active_registered_plus_unregistered_proposals | 106 → 96 | 0 | 36 | 0 | 10 |
| distill | 2 | active_registered_plus_unregistered_proposals | 96 → 96 | 0 | 3 | 0 | 0 |
| refine | 2 | active_registered_plus_unregistered_proposals | 96 → 69 | 0 | 20 | 0 | 27 |
| merge | 2 | active_registered_plus_unregistered_proposals | 69 → 66 | 3 | 0 | 6 | 0 |
| filter | 3 | active_registered_plus_unregistered_proposals | 66 → 66 | 0 | 16 | 0 | 0 |
| distill | 3 | active_registered_plus_unregistered_proposals | 66 → 62 | 0 | 13 | 0 | 4 |
| refine | 3 | active_registered_plus_unregistered_proposals | 62 → 54 | 0 | 8 | 0 | 8 |
| merge | 3 | active_registered_plus_unregistered_proposals | 54 → 54 | 0 | 0 | 0 | 0 |
| promote | 0 | active_registered_plus_unregistered_proposals | 54 → 54 | 0 | 42 | 0 | 0 |
| identity | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| assess | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| identity | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| assess | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 0 | 0 | 0 | 0 |
| snapshot | 未知／未记录 | working_proposals | 未知／未记录 → 未知／未记录 | 未知／未记录 | 未知／未记录 | 未知／未记录 | 未知／未记录 |

## 模型用量与费用估算

仅累计本工作流时间窗内的 agent.finished 聚合；内部 provider_attempt 不重复相加。前两次停止运行费用由操作者另行合并，本脚本没有将其加到本次费用。

已知费用小计：**3.8478801 USD**；状态：**partial**。
工作流预算原记录：{"used_usd": 3.8478800999999994, "limit_usd": 9.67, "cost_status": "recorded_estimate"}。未结束的模型逻辑请求：1。

| 阶段／操作 | 角色 | 请求 | 输入 token | 输出 token | 已知 USD | 费用状态 |
|---|---|---:|---:|---:|---:|---|
| propose / propose:metabolic_stability | proposer | 16 | 571582 | 244955 | 0.4654206 | estimated |
| propose / propose:oral_bioavailability | proposer | 16 | 475937 | 258118 | 0.4525227 | estimated |
| propose / propose:target_coverage | proposer | 21 | 515148 | 227457 | 0.4274928 | estimated |
| propose / propose:toxicological_safety | proposer | 18 | 620073 | 259456 | 0.4973691 | estimated |
| refine / distill | proposer | 6 | 180199 | 22969 | 0.0816225 | estimated |
| refine / distill | proposer | 2 | 69498 | 5746 | 0.0277446 | estimated |
| refine / distill | proposer | 2 | 65874 | 7571 | 0.0288474 | estimated |
| refine / filter | critic | 32 | 489247 | 380027 | 0.6028065 | estimated |
| refine / filter | critic | 3 | 70703 | 31323 | 0.0587985 | estimated |
| refine / filter | critic | 1 | 23688 | 7692 | 0.0163368 | estimated |
| refine / merge | adjudicator | 9 | 131408 | 92358 | 0.150252 | estimated |
| refine / merge | adjudicator | 1 | 20744 | 10162 | 0.0184176 | estimated |
| refine / merge | adjudicator | 1 | 4697 | 2044 | 0.0038619 | estimated |
| refine / promote | critic | 1 | 36138 | 6699 | 0.0188802 | estimated |
| refine / refine | proposer | 117 | 1633061 | 156835 | 0.6781203 | estimated |
| refine / refine | proposer | 6 | 97778 | 18685 | 0.0517554 | estimated |
| refine / refine | proposer | 2 | 45589 | 11148 | 0.0270543 | estimated |
| review / — | adjudicator | 20 | 111215 | 172094 | 0.2398773 | estimated |
| task / — | proposer | 1 | 956 | 344 | 0.0006996 | estimated |

## 核对与保留项

核对原记录：{"workflow_completed": true, "snapshot_present": true, "snapshot_run_matches_workflow": true, "snapshot_candidates": 3177, "csv_rows": 3177, "api_candidate_rows": 3177, "csv_and_api_candidate_id_multisets_match_snapshot": true, "source_publication_rowid": 1524367, "surufatinib_match_status": "found", "snapshot_readiness": "ready", "scientific_success_claimed": false, "cqa_api_as_of": "2026-10-16T06:32:09.964Z", "cqa_source_history_scope": "selected task through this snapshot publication", "excluded_cqa_artifacts": []}。

本报告不自动声称研究成功、找到了合格候选或达到了参考药物目标。资格为 pending/not_ready、排名为空、覆盖不足和费用未知均按原记录保留。

完整候选：[candidates.csv](candidates.csv)、[candidates.json](candidates.json)、[snapshot.json](snapshot.json)；模型记录：[model-accounting.json](model-accounting.json)；导出范围与文件校验和见 manifest.json。
