# 设计到验收证据审查 — 2026-10-16

**最终闭环已完成。** 下文保留运行过程中形成的审查与当时的未验证状态；最终实测结果见 [FINAL_ACCEPTANCE_2026-10-16.md](FINAL_ACCEPTANCE_2026-10-16.md)。D1 在终态真实触发后通过追加纠正恢复全部五受体绑定，并在冻结时验证；D2 已用冻结 cell 完整复算通过，0 differences。新 run 全部 28,593 cells 完成，完整 3,177 行 CSV 已实际 GUI 下载且与固定 snapshot 导出一致。Settings、任务切换、双语、补证、逐项复核、冻结、全量运行、分页与候选详情均有真实 GUI 证据；继承/reduce 的发起渠道仍如实为 HTTP。

本路径可以验收“在继承证据上完成一次有来源、可追踪的描述性新实验”。当前用户将 B 恢复率和标准数量设为软指标；交付重点是实际完成 Settings → 继承任务 → registered reduction → 已核验补证 → 冻结 → 3,177 全量扫描 → 完整榜单与 CSV，并分析结果。原 A 的 **5/50 rankable、3,177 总候选**保持为独立历史读数。

审查对象是新 task `task_01M50Q5EZE12GGDES5QNWR0JQX`。审查开始时，父任务报告 reduction `run_01M50Q7SWTRAM3B7E1MHV0D8V7` 正在运行。本审查只读设计、当前源码和公开执行摘要；没有查询运行中的 store，没有模型调用、测试或科学代码修改，没有读取 case/recovery/evaluator 明细。下表的“已记录”来自既有公开记录，不代表本审查重测；新任务的后续实测仍待实际执行证据。

## 覆盖矩阵

| 环节 | 设计中应覆盖的能力 | 当前实现与已有证据 | 本次最少的验收证据 / 当前状态 |
|---|---|---|---|
| Settings 与 mid | C4/C6/C15：解析分层设置，使用真正生效的数值 | [config.py](../../src/mas/core/config.py)、[operations.py](../../src/mas/ui/operations.py)；mid 控件、保存和配置 hash 已实现 | 保留真实操作渠道、保存后的有效配置及 reduction/sweep 各自绑定 hash。**新 GUI 全链尚未由本审查验证** |
| 完整继承 | C9/C10：完整候选范围、原 criteria/version、来源 pin、旧失败和旧结果保留 | [staging.inherit_task](../../src/mas/core/staging.py) 记录源 task pin、artifact hash、完整 scope，重建需要的本地 review；不移植旧决定为新决定 | 新 task 源 pin / universe 仍为 3,177；原 A 指定 snapshot 和 profile 保持原值。已有继承回归继续有效 |
| registered reduction | C7/C10：filter/distill/refine/merge/promote，保留退役历史与未解决项 | [reduce_registered](../../src/mas/core/derivation_run.py:415) 固定来源、原 admitted claims 和 inputs manifest；无 broker/enumeration/propose。当前真实 reduction 结果尚未检查 | 终态、termination reason、输入 manifest；分别报告 active registry、pending、未注册 backlog、scoring、retired/merged。数量不设硬阈值 |
| 真实补证 | C9：数字、原文位置、单位、身份与目标范围能回溯 | [supplement_source_2024.json](supplement_source_2024.json) 记录 2024 原文 WT CSF1R **5 nM**、WT FGFR1 **34 nM**；2 个突变记录被排除。[supplements.py](../../src/mas/core/supplements.py:29) 验原 claim/quote/value，不接收替代数字 | reduction 完成后 attach，得到新 task version；只核对两条实际用于评分的 trace、单位转换和聚合结果。这两条是实测来源，**本路径未启用均值填补** |
| 冻结测量配置 | C15/C19：先固定仪器，再产生新结果 | [measurement.py](../../src/mas/core/measurement.py) 固定 task/rules/source code/config/scope、seed、cutoff、补证 digest；controller start/load/出榜检查 | 记录新 profile id、实际 scoring 数 N、deferrals、seed/cutoff、源码身份；profile 先于 sweep 的第一个 cell。机器裁决与 pending 状态继续显示 exploratory |
| 继承工具证据 | C13/C16：可复用来源而不伪造新采样 | [broker.py](../../src/mas/core/broker.py:150) 只重放指定 completed runs 的 exact ok/empty；[pubchem.py](../../src/mas/adapters/drug/pubchem.py) 显式整行选列，保留旧检索时间并标本地派生 | 保留本 run replay manifest；实际工具统计区分 historical replay、本地投影和 fresh retrieval/失败。无需重抓已有内容验证缓存 |
| 全量 sweep | C11/C15：每个候选 × 每个已冻结评分规则均有记录，无遇到成功即停止 | [controller.py](../../src/mas/core/controller.py:305) identity-first、按规则遍历、固定 seed、无硬失败短路 | 核对 **3,177 个唯一候选**、计划 cells = 3,177 × N、完整性 1、completed、unswept 为空；unknown 与 not_assessed 分开。此新 sweep **尚未实测** |
| 排名与资格 | C11/C12：排名、证据覆盖、资格、未知分开展示 | rank-only policy 使用偏好门槛 0.5，资格门槛 1.0；新补证通过 lookup 进入原评分链，不直接改 score/position | 同时报新排名/rankable N、偏好覆盖、hard/mandated 资格和缺项；尤其验证 reduction 没让 required-receptor 分母丢失，见下方 D1 |
| 完整榜单与 CSV | C12/C17/操作面：同一 snapshot 的分页和完整导出 | [views.board](../../src/mas/ui/views.py:249) 分页并固定 snapshot；[server._csv_board](../../src/mas/ui/server.py:84) 导出全部行，携带 snapshot/rules | 实际导出后检查候选唯一数/行数 3,177，未排名者保留，CSV 和 JSON 归属同一 snapshot/rules；抽看第一页、末页与参考候选 trace，无需逐页重复测试 |
| 重现与解释 | C1/C3/C9/C17：源码/config/来源可还原，结果语义如实表达 | 原 A 有源码 archive 和 profile；当前 journal/hash 机制可验证已存事件完整性 | 一次离线的 frozen-cell→score/coverage/position 重建比对才支持“重算得到同一榜”。现有 `projection.hash` 本身仅哈希事件列表，见 D2。新结果须与旧 A 分别报告 |

## 会影响结论的具体设计差异

**D1 — task-mandated 身份可能在修订/合并 promotion 时丢失，须在 freeze 前核对。**

`derivation_run.py:511` 把源规则的 `task_mandated` 记录在 `source_registry`；`StageContext.task_mandated()` 能在 reduction 中识别它。然而 [promote](../../src/mas/core/derivation_stages.py:1562) 对发生改写/合并的条目重新赋 `derived_from={pool_criterion, derivation_run}`，并由 proposer 注册，随后退役父规则。另一方面，[criteria.is_task_mandated](../../src/mas/core/criteria.py:274) 只识别 `proposed_by.role == adapter_template` 且有 `derived_from.field` 的属性；controller 用它生成 mandated population。源 `task_mandated` 谱系没有进入该判定。

这是静态可核验的不一致，**本次是否触发尚未实测**。如果五受体模板被修订/压缩，分母可能缩小或变空，即使 task 的五个目标没有变化；由此得到的“资格提高”不能解释为补证效果。最小动作是 reduction 结束后检查五个 task 要求仍有逐目标 coverage 记录。若丢失，先保留当前结果与 reduction 历史，再修复“任务要求独立于压缩后 scoring criteria”的表示并冻结新的政策；不可直接把 proposer 标成 adapter 或专家。原模板被原样保留的分支不会触发此缺陷。

**D2 — 事件完整性 hash 与榜单重算重现之间仍有证据缺口。**

[controller.py:673](../../src/mas/core/controller.py:673) 的 `projection.hash` 对截至该点的 `Event.to_record()` 列表求 hash；这能校验事件记录，却没有重新运行 scorer/coverage/排序，也没有比较重建 snapshot 的内容。设计 [evaluation_plan §8.4](../evaluation_plan.md:147) 要求从 journal 重建 leaderboard。最少的一次有效补充是在新 sweep 完成后，用已冻结规则和实际 cell 做离线重算，比较 score、coverage、position 与 identity 集合；排除生成时间和新随机记录 ID。它不需要模型、HTTP、额外 sweep 或一套新 mock。若暂不执行，报告写“来源/冻结校验通过，榜单重算未验证”。

**D3 — 新实测补证的来源独立性与候选选择对称性是两个维度。**

补证来自独立的 2024 原文，数值与 WT/突变范围有记录；其选择仍是已经知道参考候选缺口后的定向补证。[supplements.py](../../src/mas/core/supplements.py:89) 已明确记录 `exploratory_known_gap_source` 和 `is_independent_candidate_search=false`。这不同于旧 [case_study_protocol §6.4](../case_study_protocol.md:239) 的严格候选对称检索协议。因此新实验可以说明“加入该已核验实测并执行 reduction 后的排序”，不承担候选对称盲法验证的结论。只需保留此标签和旧 A；用户当前目标不要求为此扩展全库文献检索或新增大规模对照。

当前 assessor 会合并 attribute 可接受的来源，再按已冻结 aggregation 计算；本地补证**不会保证覆盖掉**原 curated 值。两条证据的最小 trace 应显示最终 usable/set-aside、nM→pChEMBL 转换、WT/assay 条件与实际 aggregation。若 FGFR1 同时有旧值和新 34 nM，其结果可能改变，方向以实际计算为准。两项修改同时发生，排名变化按新实验描述；不将其直接归因于 reduction 的独立效果。

**D4 — “mid 主路径完成”覆盖的是此次启用的链路。**

`search.volume/textbook.volume=mid` 会进入设置及 hash；registered reduction 明确没有新 enumeration/propose/检索，sweep 也可显式延后 literature/predicted 能力。这验证 Settings 传播、已有证据上的多角色 reduction、已核验补证接入和全量评估；新的 mid 文献检索深度、跨模型家族独立性、专家 reason-quality、跨任务泛化及 self-improvement 没有在这次运行中测量。它们是当前 claim scope 的边界，不是要求临时扩展的验收任务。

## 当前阻断项与最小收尾

1. **当前真实 reduction 必须正常结束。**未结束时不 attach、不冻结、不改运行中的科学代码；失败/未解决如实保留，不靠隐藏 pending/backlog 达到数量目标。
2. **Freeze 前只检查实质仪器边界。**用 reduction inventory 和将使用的 scoring set 检查 D1 的五受体要求、active/pending/backlog/retired/scoring 分开、补证 task version 与 digest、实际 deferrals、seed/cutoff。无需重跑已通过无关测试。
3. **真实执行一次新的 3,177 全量 sweep。**完整性、终态、unswept、真实工具来源与两条补证 cell trace 是该运行的直接验收证据。
4. **完成同一 snapshot 的 GUI/CSV 与离线重现检查。**真实 GUI 点击与 HTTP 操作各自如实记渠道；D2 若未做，保留未验证状态。进度/预算展示和过大 operations payload 正由 UI agent 处理，本审查不重复该两项。
5. **归档新实验。**保存运行时源码、有效配置/profile、reduction inputs/summary、补证来源、完整 JSON/CSV 与一份结果报告。保留原 A 5/50、旧政策和原失败/未知记录。B 与数量按当前软指标报告，不再重映射追分。机器裁决仍为机器，原文 span 核验与专家科学确认分别表述。

以上未发现需要在 live reduction 期间改代码或追加模型调用的理由。D1 是否触发是 freeze 前最有价值的定向核对；D2 决定最终能否使用“榜单已重算复现”的表述。其余收尾可直接使用本次真正完成的主流程证据。

## 后续工程修复记录

原运行继续使用启动时的归档实现。以下修复用于后续进程，不追认已经执行的阶段使用了新代码。

- D1 已落实原任务绑定保护、只读审计和终态后的追加式纠正。`criteria audit-bindings` / `restore-bindings` 可核查和恢复旧 reduction 的输出；`measurement.prepare/register` 在冻结前及注册时验证 required scope，proof 保存到 `scoring_policy.required_binding_check`。显式延后的非 scope 文献门槛保留原 ref/hash 和 deferred 状态。一次运行中途审计确认五个受体仍 active；终态后仍须重新核对 promotion 的结果。
- D2 的纯离线重算脚本已准备于 `scripts/verify_leaderboard_replay.py`，等待最终新 run/snapshot 后执行一次，尚无真实重算通过结论。
- 模型请求费用与 token 聚合已覆盖 schema repair 和途中异常，并区分 complete/partial/unknown；原事件保持原值。Windows Exchange 的短暂共享锁故障已修复，首次失败及针对性通过记录见 [exchange_sharing_verification.json](exchange_sharing_verification.json)。
- 两批真实 refine trace 的只读诊断见 [REFINE_TRACE_DIAGNOSIS_2026-10-16.md](../REFINE_TRACE_DIAGNOSIS_2026-10-16.md)。语义投影使同批 prompt 字符减少 23.48% / 17.77%，后续 refine 改为每批 8 项并完整遍历。该证据不构成新代码的实测时间或费用改善结论。
- 最新 UI 要求为英文默认、English/中文互切且中文只作界面展示。Settings 的当前任务未传入导航、未知运行类型导致首页异常、Review 急算大量路线详情导致导航等待，均由真实 HTTP 检查定位；修复与双语验证单独归档，不替代最终 GUI 验收。
