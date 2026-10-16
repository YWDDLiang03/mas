# 固定 raw pool 诊断与后续实现修复

诊断结论：526 是当时的 520 条原始候选提案加 6 个已注册任务锚点，并非 526 条最终有效标准。现有 filter/refine/merge/promote 有明显的自然收敛空间；同时，混合来源锚点的子集匹配和工具输出类型/单位校验确有工程缺口，不能仅靠提案数量下降推断已消除重复计分或不可执行标准。

## 固定范围

- Task: `task_01M51AQ0JK0MYN47806ZD5XS1B`。
- Run: `run_01M51AQ43WQQPDQZVD9GADSVTB`。
- Task journal pin: **3560**；该时刻全部 520 条 pool item 均为 `candidate`。
- 原运行实现绑定：`0e7bdc522692d5b4f87586ff8538afdc301f04cb5c7628d8d12f7f10acde039e`。
- Pool snapshot SHA256: `3e53abfedd07b166837169ba4903ec487137ae463b54921a39b37b46fedc2081`。
- 原始诊断：[raw_pool_3560_2026-10-16.json](raw_pool_3560_2026-10-16.json)；只读脚本：[analyze_raw_pool_2026-10-16.py](analyze_raw_pool_2026-10-16.py)。JSON 在本次源码修复前保存，以下计数均描述原 0e7 行为；后续实现的校验结果应另存，不能覆盖这一记录。

诊断只读取固定 task 的公开提案、已注册锚点和 admitted claims，并调用纯校验/分组函数。没有执行 filter 或任何会写 pool 的 stage，没有读取排名、sealed case/recovery/evaluator，没有模型或网络调用，没有写 primary。

## 原始提案构成与重复

| 类别 | 数量 | 含义 |
|---|---:|---|
| target coverage 维度 | 368 | 仍处于展开阶段 |
| oral bioavailability 维度 | 152 | 截至该 pin 的已完成批次 |
| potency 路由 | 264 | 数值活性/亲和力 |
| engagement/breadth 路由 | 98 | 机制记录存在性或试图表示靶点数量，不能视为 potency |
| predicted property 路由 | 135 | 预测端点，独立于直接测量 |
| computed descriptor 路由 | 6 | 计算描述符 |
| record flag 路由 | 11 | 记录字段 |
| literature quantity 路由 | 6 | 文献数量型提案 |

后三组性质计数与前三组性质计数合计 520；它们是路由类别，不能解释成 520 个不同科学端点。

确定的“相同定义和决策”重复有 **56 组、202 条、146 条重复余量**。比较保留完整 attribute 语义，只忽略 rationale/bound_support，并要求 decision_key 相同；不同引文仍是可保留的支持证据，不构成额外评分标准。

更宽的非文献结构比较（quantity_key、完整路由集、测量类型、聚合、接受的来源/basis、precedence、存在性语义及 decision_key）得到 **51 组、339 条、288 条结构重复余量**；这表示执行字段等价，定义文字仍须由既有审查处理。其中旧 validator clean 子集有 145 条结构重复余量。两套计数相互重叠，不能相加或直接从 520 扣除。

粗 quantity_key 分成 105 桶，quantity×decision 分成 166 组合；这只是分组，不是独立可执行端点数。相同量的阈值、方向、缺失处理或聚合不同，应保留相应发现进入复核，不能因同一个 target 名称直接删除。potency、机制记录存在性和跨 target breadth 本身也不等价。

## 校验与现有收敛机会

原 deterministic validator 有 **208 条存在问题、312 条 clean**；clean 仅表示通过当时的工程校验。

- **195 条**未引用 supporting claims；现有 filter 会记录 `no_supporting_claim` 并移出活跃池。
- 另有 **7 条 bound_support_mismatch**：提议的 source-stated pChEMBL 数字不能从所引证据或已声明转换验证。
- **6 条 schema 问题**：5 条文献绑定不是有单位的 quantitative，1 条 value_transform 使用了无效 basis。
- 对 312 条旧 validator clean、尚未被原锚点识别覆盖的候选，纯 `merge_groups` 形成 **77 组、覆盖 279 条**，展示现有归并机会。实际 critic/refine/merge 决策尚未发生，分组上限和多轮处理也会影响轨迹，不能据此承诺最终保留数量。

因此，后续原 prune 能自然压缩相当一部分 raw 重复；最终活跃条目仍需按实际 promotion/freeze 记录核对，而不是按原始数量或某个目标数量决定删除。

## 两个已证实的缺口

### 1. 混合来源锚点未覆盖数据库子集

五个 potency 锚点的 routes 包含 ChEMBL、GtoPdb 和 literature。`quantity_key` 把全部 capability 纳入身份；数据库子集只含 interaction lookup，因此在 `duplicate_of_registered` 的 route-subset 判断之前就失配。原 filter 对当前原始提案报告锚点覆盖 **0 条**。

固定 pool 中，有 **218 条**满足原锚点路由子集、同 unit/direction/target/transform，其中 **213 条**与锚点同 aggregation、**115 条**通过旧 validator。它们覆盖五个 target 的纯数据库 potency 提案：45、44、43、43、43 条。部分 decision_key 与锚点不同，必须复核；但原实现连 measurement-only match 也看不到，所以可能在 promote 时绕过“同量不同决策不得再注册第二评分量”的保护。这里报告的是具体可触发路径；pin 时尚未 promote，未声称已重复计分。

修复位于 `core/derivation_stages.py::_same_measurement / duplicate_of_registered`。保留现有 quantity_key 的全局分组语义，仅在路由完整子集的覆盖判断中分离传输 capability 与测量本身，并检查测量类型、canonical unit、方向、subject、transform、aggregation、存在性语义。完整 decision duplicate 另需 precedence 与接受证据域可覆盖，证据政策差异不能当作数量身份差异而绕过防重复计分。新增路由、其他 target、不同类型/聚合/变换不会被当作重复。相同测量但不同决策或证据政策仍由现有 promote 路径记录 `decision_semantics_unresolved`，保留待复核，不能额外评分。

### 2. 声明单位/类型与真实工具输出不一致仍可通过

原 pool 有 **48 条**已声明路由与单位/类型不相容，其中 **37 条**仍通过旧 validator。例如 pChEMBL-returning 路由被命名为 nM 或 ng/g 指标；机制记录返回 Boolean，却被定义为 quantitative count。返回 Boolean 的 max/median 不会计算不同 target 的数量；当前数值 assessor 会将 Boolean 视为非数值。

修复位于 `core/derivation.py::_route_output_problems / validate_proposal`：按 catalog 的 property/endpoint/field 确定实际返回单位，使用现有 `assessor.canonical_unit` 与方向明确的 `unit_conversion`。已实现的 nM→pChEMBL 和单位同义继续可用；未实现的反向转换或 ng/g 被记录为 units 问题。固定单位为 null 的 categorical route 不准伪装 numeric count；多条 Boolean routes 也不能自动变为 count。自由文献单位或未给定固定输出的 catalog 不猜测单位。此修复没有引入新转换、计数聚合、阈值或权重。

此外有 **93 条 categorical preference 没有 cutoff/predicate，53 条旧 validator clean**。它们可能在有机制记录时仍产生 unknown，而非可评分 Boolean 判断。这属于另一个可执行性问题，本次未扩展其 schema/执行模型，后续可从实际保留项确认是否仍存在。

## 后续实现身份与验证

改动仅针对后续 continuation/新 binding。原 0e7 运行、已产生提案、费用和原失败/未知轨迹保持原身份；不能把本次修复描述成原进程已经使用。

修改文件：`src/mas/core/derivation.py`、`src/mas/core/derivation_stages.py`、`src/mas/core/vocab.py`、`tests/test_criteria_pool.py`。既有函数调用签名不变。归并拒绝记录同时保留 validator 与越过父项来源的原因；没有变更临床 oral 事实、科学阈值、weights 或真实 store。

为保留已付费完成的提案批次，`StageContext` 新增可选 `completed_proposal_slices: dict[str, set[int]] | None = None`。续跑 owner 必须先固定同一事实 manifest、claim 顺序、batch size 与确实完成入池的来源批次，才能提供 dimension→1-based slice 集合；`propose` 不自行按 `agent.finished` 推断复用。返回结果新增 `reused_slice_count` 与 `reused_slices`，`added` 仅统计本次新写入项。

新批次全部 pool.add 成功后，会在 run stream 记录 `proposal.slice_completed`，payload 包含 `dimension/slice/slices/batch_size/source_claim_count/ordered_claim_ids_sha256/claim_ids/claims_sha256/request_id/added_criterion_refs/refused_at_entry/considered_and_rejected_count`。`claims_sha256` 固定该 slice 的完整有序 claim payload，`ordered_claim_ids_sha256` 固定该维度完整有序 claim IDs。事件是所有先行写入完成的持久凭据；并未把多个 pool 写入改成一个 SQL 事务。部分写入或异常不会生成此 marker，单独的成功 agent.finished 不足以复用该批次。旧 0e7 没有 marker 的批次需由续跑 owner 验证已有 pool 与后续活动证明，不能默认已入池。

验证命令：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_derivation.py tests/test_criteria_pool.py tests/test_registered_reduction.py tests/test_derivation_callbacks.py -q
```

结果：**94 passed in 5.81s**。包括混合来源 anchor 子集识别、不同有证据 threshold/证据政策保留待复核且不新增 scoring rule、类型/聚合/subject/transform 差异保护、实际转换方向与同义单位、Boolean 不能伪装 count，以及已有 filter/refine/merge/promote/reduction/callback 回归。两项新增 slice 检查分别验证显式完成批次不再调用模型或重复入池，以及 schema_ok 的模型响应只部分入池时不生成完成 marker。全部为临时 store/脚本模型；没有付费科学实验。当前真实 workflow 的最终收敛和排名由后续真实记录判定，本诊断不作成功承诺。
