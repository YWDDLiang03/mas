# Fresh browser study — snapshot2 independent audit

Task: `task_01M52CBE5GYPK9F0MCZYBMPH84`
Run: `run_01M52Q4VRB00T5Z3QJW08SSV96`
Snapshot: `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`

**Engineering checks: 34/34 passed. Scientific acceptance: met under the frozen criteria.**

| Check | Actual result |
|---|---|
| Candidate population / full CSV rows | 3,177 / 3,177 |
| Source assessment cells | 98,487, all exact frozen refs |
| Qualified / ranked / pending | 10 / 10 / 3,167 |
| Surufatinib rank | 1 of 10 qualified candidates |
| Surufatinib score, independently recomputed | 0.7592592592592593 |
| Surufatinib direct preference coverage | 10/17 = 0.5882352941176471 |
| Surufatinib hard conditions | 1/1 passed with direct evidence |
| Required target scope | 5/5 directly answered |
| Enabled execution entries | 31 = 17 preference + 1 hard + 13 context |
| Independent core decision groups | 18; context groups separately 13 |
| Corrected deterministic descriptors | 4 × 3,177 cells, all derived and direct |

The audit independently recalculated every candidate qualification, weighted preference score, direct coverage and rank. Source, API and complete CSV IDs and numerical fields agree. Surufatinib has 15 available preferences: 10 direct or derived and 5 predicted; human oral F% and Tmax remain unknown. Predicted values do not add direct coverage.

The new run binds the fixed terminal-tool source closure (two completed sweeps plus the completed tool facts of one cancelled sweep), exact source sequence pins and 68,886 indexed tool results. Both cached panel manifests are fixed and cover all 3,177 candidates. Original snapshot1 source and exported JSON/CSV/manifest hashes remain unchanged. Its earlier acceptance failure remains in its separate audit.

Costs use the recorded model estimates and aggregate agent.finished without adding provider attempts again. The scientific workflow has 325 completed requests, complete usage and no unknown/partial or unfinished requests in this workflow.

- Prior known: $4.4020383
- This scientific workflow: $4.2101472
- Audit cumulative known: $8.6121855
- Additional annotation interpretation: $0.0014724
- Inclusive cumulative known: **$8.6136579**

The annotation increment is reported separately from the audit prior because it occurred afterward. Any prior orphan request already recorded as unknown remains unknown and is not converted to zero.

All source access was read-only. The auditor invoked no models and changed no scientific or cache records.
