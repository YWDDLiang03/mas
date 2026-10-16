# 完成工作流的最终工程验收

任务 `task_01M52CBE5GYPK9F0MCZYBMPH84`；工作流 `wf_cb4caec3dec348908fb3d34eae5b11d1`；快照 `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`。

工程检查全部通过：**True**。此字段不代表科学目标成功或参考候选获得资格。

## 完成后的 HTTP 测量

每个接口实际测量 50 次；首次值是完成门槛之后的首个测量请求，不等同于数据库冷构建。

| 列表 | 成功样本 | 首次 ms | P95 ms | 最大 ms | 错误数 |
|---|---:|---:|---:|---:|---:|
| overview | 50 | 73.376 | 86.803 | 89.022 | 0 |
| criteria | 50 | 239.805 | 263.063 | 270.873 | 0 |
| stages | 50 | 6.525 | 33.003 | 45.903 | 0 |
| candidates | 50 | 7.197 | 30.802 | 31.257 | 0 |
| evidence | 50 | 30.494 | 57.783 | 58.32 | 0 |

## 隔离重建与源记录对齐

临时库重建：{"seconds": 857.751, "cache_bytes": 6189428736, "schema_version": 4, "source_cursor": 2151293, "cache_location": "disposable system temporary directory", "deleted_after_checks": true}。

重建只写独立临时数据库并在结束时清理。服务 cache 与源库以只读方式打开；只对本任务进行分页、summary、stages、候选快照与源注册记录核对。

| 核对 | 一致 |
|---|---|
| api_vs_service_cache.summary | True |
| api_vs_rebuild.summary | True |
| api_vs_service_cache.criteria_all_items | True |
| api_vs_rebuild.criteria_all_items | True |
| api_vs_service_cache.candidates_all_items | True |
| api_vs_rebuild.candidates_all_items | True |
| api_vs_rebuild.evidence_first_page | True |
| service_cache_vs_rebuild.snapshot_summary | True |
| api_vs_source.registry_summary | True |
| api_vs_source.active_rule_refs | True |
| api_vs_source.stage_ids | True |
| api_vs_source.latest_prepared_evaluation_membership_and_reasons | True |
| api_vs_service_cache.stages | True |
| api_vs_rebuild.stages | True |
| api_vs_source.recorded_stage_boundaries_and_states | True |
| api_vs_source.full_snapshot_candidate_ids_rank_and_score | True |
| api_candidate_page.total_vs_source | True |
| api_vs_source.explicit_candidate_qualifications | True |
| service_cache_vs_source.snapshot_header | True |
| api_vs_source.recorded_qualified_count | True |
| api_criteria_ids_exist_in_source_registry_or_pool | True |
| api_evidence_first_page_ids_are_public_source_claims | True |
| source_task_unchanged_during_acceptance | True |
| service_cursor_consumed_snapshot_publication | True |
| rebuild_cursor_consumed_snapshot_publication | True |

先前性能证据保留原文件与 SHA-256；历史单次比较没有当作 P95，本次没有重跑旧任务基准。原始 50 样本、分页 ID、差异与重建状态见 acceptance.json。
