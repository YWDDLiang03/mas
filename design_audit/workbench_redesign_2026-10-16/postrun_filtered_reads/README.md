# 精确读取性能补丁（尚未应用）

本补丁只改变读取路径，未加入语义缓存或源库索引。当前任务的 88 个全部规则/属性版本、86 个 kind/base 版本列表、44 个规则版本的两条 cited-claims 路径均逐结果相等。对比限定在本 task 及其两个 derivation run，未遍历其他任务、B 或 case。

## 改动

- `criteria._versions/load` 通过 SQL 的 stream、event_type、kind、base、可选 version 过滤，仅反序列化匹配 payload；保留版本 seq 顺序、首次匹配及缺失/非数字引用的既有异常行为。
- `ledger.claims` 将 admission/candidate/attribute 过滤移至 SQL，新增可选 claim_ids。默认仍逐输入 stream 再按 seq 返回，重复 stream、重复 claim 与两个 admission event 类型均保留；空字符串过滤仍按旧逻辑视为无过滤。claim ID 用单个 JSON 参数，避免参数数量上限；旧事件缺 event-level claim_id 时仍检查原 artifact。
- 两个 adjudication cited-claims 路径只读取精确 cited refs，保持既有 stream 集合。`model_decision_boundary` 的额外部分仍依据 artifact 的 attribute_ref 和 determination_basis 选择，避免 inherited event metadata 缺失导致范围变化；先 cited 后 extras，seen 只排除 cited IDs，保留原本重复的 extras。
- 已保留并行加入的 `_completion_limit` 及两个模型调用处的新行为，未修改模型请求。

## 实际只读对比

| 有界读取工作负载 | 修改前 ms | 提案后 ms | 加速 | 相等 |
|---|---:|---:|---:|---|
| load_all_task_attribute_and_rule_versions | 9628.656 | 1252.560 | 7.69× | True |
| versions_all_task_kind_base_pairs | 9375.393 | 1223.819 | 7.66× | True |
| ledger_default_task_and_derivation_streams | 193.365 | 91.825 | 2.11× | True |
| ledger_reverse_and_duplicate_streams | 205.949 | 95.020 | 2.17× | True |
| ledger_candidate_filter_missing | 118.950 | 20.380 | 5.84× | True |
| ledger_attribute_filter_missing | 134.441 | 20.503 | 6.56× | True |
| ledger_exact_cited_refs | 192.821 | 24.590 | 7.84× | True |
| adjudication_cited_claims_all_rule_versions | 7146.951 | 806.643 | 8.86× | True |
| adjudication_route_cited_claims_all_rule_versions | 1559.879 | 376.395 | 4.14× | True |

以上是同一机器上的单次成对本地读取工作负载，不是 HTTP P95，也不把它宣称为完整 Review 的 82 秒间隔测量。scope fallback 在验证时限制为本 task 的两个 derivation run；补丁本身保持原 stream 集合。

## 最小离线检查

- exact versions plus malformed/missing/non-numeric ref exception parity
- ledger default/admitted/candidate/attribute/empty filters preserve stream seq order and duplicate streams/claims
- claim_ids empty, legacy missing event claim ID, and 2000-ID filter
- boundary preserves artifact attribute matching when event metadata omits it; extra duplicated predictions remain duplicated

初始 cProfile 抽样耗时 0.705 秒，其中 journal replay 累计 0.672 秒，JSON 解码 32,845 次，确认整流 replay 是该抽样的主要成本。全部真实版本与规则结果检查通过；3 个 active 源文件 hash 与补丁 baseline 相同。

`filtered_reads.patch` 为可审阅的 unified diff，尚未应用。`*.proposed.py` 是供内存加载核验的提案副本；`baseline.json` 保存源码基线，`verification.json` 保存完整结果与提案后 profile。没有付费调用、科研事件写入、primary/cache 写入或候选结果读取。
