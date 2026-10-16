# 工作台交付与验收汇总

**最终科学运行已完成：snapshot 2 中 Surufatinib 为 qualified，位列 4/10，硬条件 1/1、必需靶点直接证据 5/5。**
新结果实际达到 qualified/top five 目标；独立数值核验 22 项全过，新旧快照切换、CSV 按钮点击和生产入口交接均已完成并留存证据。
两条 logP 的区间语义修订已按全库执行；snapshot 1 及原数学问题保留为历史，不覆盖原记录。

| 范围 | 已证实状态 | 依据 |
| --- | --- | --- |
| CQA 从空集生成、三轮提炼及注册 | 已完成，0→6→1,807→54；43 注册、11 未注册待处理 | [CQA_EVOLUTION.md](CQA_EVOLUTION.md) |
| Snapshot 1 全库评估 | 已完成，3,177 候选、24 条启用标准 | [原始导出报告](final/wf_033db93e15fa4bb289c2e03606674f6b/report.md) |
| Snapshot 1 工程验收 | v2 全部通过，包含读取性能、重建及源/API 对齐 | [验收报告](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/report.md) |
| Snapshot 1 导出 | CSV/API/snapshot 均为 3,177 行；14 个 manifest 文件校验通过 | [导出复核](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/export-postcheck.json) |
| 科学最终结果 | **Snapshot 2 已完成：qualified、4/10；新分数 0.6629629629629631** | [独立数值核验](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) |
| Snapshot 2 导出与独立核验 | 15 文件；source/API/CSV/score/rank 和原 claim 公式核对均通过，22/22 | [新导出报告](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/report.md)、[独立核验 JSON](../../var/workbench-v2-acceptance/snapshot2-numerical-check/numerical-check.json) |
| 生产入口交接 | 新版 8769 已部署，新根及旧链接 HTTP 200，真实浏览器验证通过；8770 已停止，8765 未触碰 | [部署记录](../../var/workbench-v2-acceptance/production-deployment.json) |

任务为 `task_01M51AQ0JK0MYN47806ZD5XS1B`，工作流为 `wf_033db93e15fa4bb289c2e03606674f6b`。
本轮使用 standard 预设、search/textbook 为 mid、4 workers、existing_only、staged。
目标、约束、标准、证据原文及运行数据保留英文；默认英文界面，可切换中文界面。
参考候选由用户显式声明，供结果对照，不能作为排序加分或候选专属标准的来源。

## 最终科学读数：snapshot 2

运行 `run_01M51RRJ8Y3D5DYAQGMYPY13AP` 已实际完成并发布
`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_2`；规则集 `rules@v3`，profile `art_9d00e221a8fc`，
数值源码绑定 `14a4047b794d169635fe03b59c0ac7648892e0d1ccda3ceab09e9385599b2b81`。
以下实际 API 读数已与独立 source/API/CSV/score/rank 核验对齐。

| 指标 | Snapshot 2 实际结果 |
| --- | --- |
| 全库 | 3,177 |
| 资格分组 | qualified 10；pending 3,167；rejected 0；unassessed 0 |
| Surufatinib | qualified；位置 4/10；偏好分 **0.6629629629629631** |
| 同分 | Nintedanib 位置 5，与 Surufatinib 同偏好分；按既定同分排序保留位置 |
| Surufatinib 直接依据 | hard **1/1**；必需靶点 **5/5**；直接偏好证据覆盖 **0.5238095238095238** |
| 启用记录与独立决策 | **24 个执行条目、23 个独立决策**；独立角色为 21 preference、1 hard、1 exploratory |
| 注册与待处理 | 43 当前注册、19 延后、11 未注册 pool 待处理 |
| 已知费用 | 工作流 USD **3.8550975**；加先前停止流程 USD 0.3239793 后 session 小计 **4.1790768**；未知 legacy 费用保留 |

[实际 snapshot 2 全候选 API](http://127.0.0.1:8769/api/workbench/tasks/task_01M51AQ0JK0MYN47806ZD5XS1B/candidates?snapshot=lb_task_01M51AQ0JK0MYN47806ZD5XS1B_2&status=all&page=1&page_size=50)
固定读取本快照；[冻结和决策数核对](../../var/workbench-v2-acceptance/snapshot2-freeze-readonly-check.json) 保留其规则、profile、批准依据及旧快照不变证明。
新偏好分数采用修正后的同量决策，不与原 snapshot 1 的分数作跨口径优劣结论。
[Snapshot 2 完整导出](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/report.md) 已成功，目录含 15 文件（manifest 列 14 个数据文件）。
Exporter 自检及 read_models 独立核验均已通过：CSV/API/snapshot 的 3,177 行候选 ID、score、直接覆盖与确定性排名一致。
[22 项独立检查](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) 使用全部 76,248 个单元重算，未调用生产的 preference_scores/rank 函数。

## 科学读数：snapshot 1，保留但不作为最终验收

完成评估运行 `run_01M51NWNGBK6EY7AAC4GZEQBVC`，快照
`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_1`，评估方案 `rules@v2`，测量 profile `art_8e5c3de6bcc7`。

| 指标 | Snapshot 1 原记录 |
| --- | --- |
| 全库 / 资格分组 | 3,177；qualified 10，pending 3,167 |
| 启用标准 | 24：1 hard、22 preference、1 context |
| 当前注册 / 延后 / 未注册待处理 | 43 / 19 / 11；当前工作集 54 |
| Surufatinib | qualified；位置 4/10；偏好分 0.6074074074074075 |
| 同分 | 与 Nintedanib 同偏好分；位置包含既定同分排序，不解释成严格分数优势 |
| Surufatinib 直接依据 | hard 1/1；必需靶点 5/5；直接偏好证据覆盖 0.5 |
| 记录完整性 | sweep 与 assessment completeness 均为 1.0；76,248 个单元；error_n=0 |

这些是实际快照读数。导出后发现 logP optimal-band 的 `distance_outside_band` 与保留的原值比较符不一致；
例如区间内的距离 0 仍被拿去与原值下界比较。另一条 logP 条目也已按同一数学审计完成修订。
修正已按同一量纲和同一规则作用于全库，以新版本、复核、冻结及 snapshot 2 保留变更，原 snapshot 1 不改写。
现有 [导出复核中的科学问题记录](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/export-postcheck.json)
和 [已保存区间依据](../raw_logp_band_support_2026-10-16.json) 可追溯。

直接偏好证据覆盖仍按“有直接证据的适用偏好权重 / 全部适用偏好权重”计算，预测专用偏好仍在分母，门槛维持 0.5。
预测可作为偏好依据，但不增加直接证据覆盖，也不能单独使硬条件通过或失败。
24 条“参与评估”包含硬条件及 context，不能称作 24 条偏好计分标准。

修订完成：两条 logP 均已完成新复核、`rules@v3` 冻结和全库筛选，已发布 snapshot 2。
最终汇总为 24 个启用记录、19 个已延后、43 个注册与 11 个 pool 待处理。
两条 logP 保留各自来源和算法，以显式共享 `quantity_id` 及同一 2–4 距离决策执行既有 direct-first；
预测旁证不加第二分。这不表示算法数值可以互相替换或取平均。
只读冻结核对已确认：**24 个执行条目 = 23 个独立决策问题（21 preference + 1 hard + 1 exploratory）**。
两条 logP 均以 `agent_verdict / bound_interpretation_granted / approve` 获准，`confirmed_by_a_person=false`，属于机器裁决，不是人工审批。
新 run 为 `run_01M51RRJ8Y3D5DYAQGMYPY13AP`，profile 为 `art_9d00e221a8fc`；
[冻结只读证据](../../var/workbench-v2-acceptance/snapshot2-freeze-readonly-check.json) 也确认旧 snapshot 1 与原导出哈希保持一致。
新源码已归档为 [14a4047b…](../../var/provenance/workbench-v2/14a4047b794d1696/manifest.json)。

## 已完成的真实用户路径与 GUI 证据

以下区分实际浏览器记录、接口/导出核对和仅实现状态；截图证明其记录当时的版本，不自动代表 snapshot 2。

| 用户操作 | 已有证据 | 可确认内容 |
| --- | --- | --- |
| Settings→自定义目标→草稿→一次启动 | [session.json](../../var/workbench-v2-acceptance/session.json)、[Settings 截图](../../var/workbench-v2-acceptance/browser/settings-saved.jpg)、[草稿截图](../../var/workbench-v2-acceptance/browser/research-draft.jpg) | 实际保存 mid/mid/4；填写目标、5 靶点、口服约束及参考候选；保存草稿并点击 Start；早期失败保留 |
| 编辑任务并产生可追溯新研究 | [revised-run-start.json](../../var/workbench-v2-acceptance/revised-run-start.json)、[full-run-start.json](../../var/workbench-v2-acceptance/full-run-start.json)、[截图](../../var/workbench-v2-acceptance/browser/revised-task.jpg) | revision_of_task_id、初始 registry/pool=0、固定证据 manifest 和真实新任务记录 |
| 暂停、继续、刷新恢复与停止 | [live-ui-checks.json](../../var/workbench-v2-acceptance/live-ui-checks.json)、[停止记录](../../var/workbench-v2-acceptance/first-run-stopped.json)、[版本化续跑记录](../../var/workbench-v2-acceptance/continuation-start.json) | 实际 run.paused/run.resumed；早期 stopped 流程与原请求、费用保留；续跑不覆写原绑定 |
| CQA 阶段、搜索、分页和原父版本 | [cqa-gui-proof.json](../../var/workbench-v2-acceptance/cqa-gui-proof.json)、[谱系截图与 AX](../../var/workbench-v2-acceptance/browser/cqa-lineage-saved-version.txt) | 0→1,807、任务绑定 Added=6、merge 阶段搜索；打开确切父 v1 后保留原筛选 |
| 标准 v1→v2 差异和真实修订理由 | [历史 AX](../../var/workbench-v2-acceptance/browser/criterion-math-revision-history.txt)、[截图](../../var/workbench-v2-acceptance/browser/criterion-math-revision-history.jpg) | LD50 旧方向与新方向分别保留；supersedes 及 workbench_revision 理由可查 |
| logP 新版、复核与数学差异 | [AX](../../var/workbench-v2-acceptance/browser/logp-v2-review-and-diff.txt)、[截图](../../var/workbench-v2-acceptance/browser/logp-v2-review-and-diff.jpg)、[冻结核对](../../var/workbench-v2-acceptance/snapshot2-freeze-readonly-check.json) | 两条 v2 保留原来源与算法，使用同一完整区间距离；机器批准路径和共享量身份明确，未冒充人审 |
| Pending 的独立原因 | [MW 待处理 AX](../../var/workbench-v2-acceptance/browser/pending-criterion-reason.txt)、[截图](../../var/workbench-v2-acceptance/browser/pending-criterion-reason.jpg) | 注册 Active 与最近评估 Deferred 分列；机器复核未解决，不冒称人工审批 |
| 候选结论→来源卡 | [口服证据 AX](../../var/workbench-v2-acceptance/browser/surufatinib-oral-evidence.txt)、[截图](../../var/workbench-v2-acceptance/browser/surufatinib-oral-evidence.jpg) | 实际点击后显示 Sources for / Supporting evidence，并有 Show all evidence；来源正文保留原文 |
| 英文/中文与筛选恢复 | [evidence-ui-check.json](../../var/workbench-v2-acceptance/evidence-ui-check.json)、[中文证据截图](../../var/workbench-v2-acceptance/browser/evidence-zh-original-content.jpg)、[live-ui-checks.json](../../var/workbench-v2-acceptance/live-ui-checks.json) | Evidence `oral` 352 条，第二页刷新及 EN→中文→EN 保持；Criteria 第二页刷新及跨页面往返保持 |
| Candidates 全库第二页刷新恢复 | [实际 AX](../../var/workbench-v2-acceptance/browser/all-candidates-page2-refresh.txt) | All groups 的 `51–100 of 3177` 在实际刷新后保留，不再列为待完成 |
| 修订后的真实运行进度 | [AX](../../var/workbench-v2-acceptance/browser/corrected-run-progress.txt)、[截图](../../var/workbench-v2-acceptance/browser/corrected-run-progress.jpg) | 保存时 72,826/76,248、96%，Last activity 1s、已记录估计费用可见；这是进行中证据，不是最终快照 |
| 窄窗口 | [760px](../../var/workbench-v2-acceptance/browser/overview-760.jpg)、[390px](../../var/workbench-v2-acceptance/browser/overview-390.jpg)、[中文谱系](../../var/workbench-v2-acceptance/browser/cqa-lineage-mobile-zh.jpg)、[候选表](../../var/workbench-v2-acceptance/browser/final-candidates-mobile-zh.jpg)、[候选详情](../../var/workbench-v2-acceptance/browser/surufatinib-mobile-zh.jpg) | 已有真实窄窗口留存；表格使用水平滚动，研究内容不随界面语言翻译 |
| 完成结果 | [qualified 榜单](../../var/workbench-v2-acceptance/browser/final-qualified-board.jpg)、[候选详情 AX](../../var/workbench-v2-acceptance/browser/surufatinib-final-detail.txt) | Snapshot 1 的资格、分数、覆盖和来源入口；Export 链接指向该确切 snapshot |

## 已完成工程验收与性能

[v2 验收报告](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/report.md)
对五类接口各取 50 个实际 HTTP 样本，均无错误。首个测量请求不等于冷库构建。

| 接口 | P95，毫秒 | 最大，毫秒 |
| --- | ---: | ---: |
| Overview | 69.813 | 84.279 |
| Criteria | 189.862 | 236.240 |
| Stages | 32.449 | 36.053 |
| Candidates | 32.491 | 35.274 |
| Evidence | 34.824 | 37.807 |

隔离 query DB 重建耗时 49.073 秒，源库和服务缓存只读；临时数据库检查后清理。
源记录、服务缓存、重建结果与 API 的 summary、标准、阶段、候选资格/ID/排名/分数及评估理由对齐全部通过。
原始样本和比较见 [acceptance.json](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/acceptance.json)。
此前一次验收脚本误拒绝 `error:null`、一次 Criteria 性能/旧阶段 DTO 不一致均有原始失败记录；
相应修复后 v2 才通过，不能把早期失败删去或改写为通过。
这组性能结论属于 snapshot 1 的已验收版本，数学修订后的数据一致性另行确认。

## 导出、费用与归档

- Snapshot 2 完整交付：[报告](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/report.md)、[CSV](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/candidates.csv)、
  [snapshot JSON](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/snapshot.json)、[manifest](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/manifest.json)。
  导出本身完成、零模型调用、源库和缓存未写入；独立复核已完成，两版 manifest 所列文件大小和 SHA256 均一致。
- Snapshot 1 完整导出目录：[final/wf_033db93e15fa4bb289c2e03606674f6b](final/wf_033db93e15fa4bb289c2e03606674f6b/report.md)。
  [CSV](final/wf_033db93e15fa4bb289c2e03606674f6b/candidates.csv)、[候选 JSON](final/wf_033db93e15fa4bb289c2e03606674f6b/candidates.json)、
  [snapshot JSON](final/wf_033db93e15fa4bb289c2e03606674f6b/snapshot.json)、[manifest](final/wf_033db93e15fa4bb289c2e03606674f6b/manifest.json)
  和 CQA/模型用量原记录均已保存。目录名中的 final 是导出类别，不代表已通过此次数学修正后的最终科学验收。
- Snapshot 1 已知模型费用小计 USD **3.8478801**；先前两个停止流程 USD **0.3239793**，已知合计 **4.1718594**。
  一个 legacy 逻辑请求只有 started、无 finished/provider-attempt，费用状态保留 partial，不能当作精确最终账单。
  Snapshot 2 已知工作流小计为 3.8550975，session 已知小计为 4.1790768；未知项继续保留。[模型记录](final/wf_033db93e15fa4bb289c2e03606674f6b/model-accounting.json)。
  已核对 `rules@v3` 完成后的已知工作流小计为 USD **3.8550975**，比 snapshot 1 多 **0.0072174**；
  加旧停止流程后已知 session 小计 **4.1790768**。已知小计与旧账目分别保留；legacy 未闭合请求费用仍为未知，不将小计声称为精确账单。
- 初始 SQLite 一致备份：[备份 manifest](../../var/backups/workbench-redesign-20261016/manifest.json)，5,520,838,656 bytes，
  SHA256 `63301bb0e17cfca84cc18855c35a004ba70f4b680c803017280338df1c23b033`。
  这是本轮开始前备份，不冒称包含后来 snapshot 的最终备份。
- 生成续跑源码归档：[210c6fe3…](../../var/provenance/workbench-v2/210c6fe3ab139d5c/manifest.json)；
  snapshot 1 的数值运行绑定 [1cd1f401…](../../var/provenance/workbench-v2/1cd1f401bf2d21f9/manifest.json)；
  后续展示/读取版本另有 [35ce8d6f…](../../var/provenance/workbench-v2/35ce8d6f2999a19c/manifest.json)，不覆盖科学绑定。
  [run-bindings.json](final/wf_033db93e15fa4bb289c2e03606674f6b/run-bindings.json) 保留各段对应关系。
- 最终 React UI 已单独归档：[5825351b…](../../var/provenance/workbench-v2-ui/5825351b32ac2d98/manifest.json)，包含源文件与 dist 哈希，后端科学绑定仍为 14a4047b…，原归档未覆盖。
  最后一处仅隐藏表格中重复的 `qualification: qualified` 状态回显，原候选 reason、API、分数和排名保留；TypeScript/Vite 由根任务验证通过。
  早期 [b1cffa0b…](../../var/provenance/workbench-v2-ui/b1cffa0b13f19c0b/manifest.json) 继续作为历史 UI 归档保留。

## 最终数值核验与生产交接

[数值核验报告](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) 和
[完整 22 项检查](../../var/workbench-v2-acceptance/snapshot2-numerical-check/numerical-check.json) 均已通过：
全部 76,248 个单元、3,177 个候选的 source score/直接覆盖/排序与 API/CSV 一致。
两 logP 共 6,354 个执行单元，其中 2,956 个可用值逐一用原 claim 复核
`median(max(2-x, 0, x-4))`，没有差异；缺失保留原状态。
每个合格并排名候选实际参与 weighted score 的偏好值为 15 个，预测 logP 旁证没有增加第二票。

实际 GUI 已完成并保存：

| 交付动作 | 真实证据与结论 |
| --- | --- |
| Snapshot 1↔2 切换与刷新 | [旧快照](../../var/workbench-v2-acceptance/browser/snapshot1-switch-preserved.txt)、[新快照刷新](../../var/workbench-v2-acceptance/browser/snapshot2-switch-refresh.txt)：原 0.6074、新 0.6630 分别保留，选择和刷新正常 |
| 新最终榜单及候选详情 | [完整榜单截图](../../var/workbench-v2-acceptance/browser/snapshot2-qualified-board-full.jpg)、[详情 AX](../../var/workbench-v2-acceptance/browser/snapshot2-surufatinib-detail.txt)、[详情截图](../../var/workbench-v2-acceptance/browser/snapshot2-surufatinib-detail.jpg) |
| 正式端 Settings | [生产设置 AX](../../var/workbench-v2-acceptance/browser/production-settings.txt)：Medium/Medium、4 workers、cap 9.67 保持；此前停止费用另列，仍在原 USD 10 已知预算范围内 |
| 正式端中文窄窗口 | [390px AX](../../var/workbench-v2-acceptance/browser/production-mobile-zh.txt)、[截图](../../var/workbench-v2-acceptance/browser/production-mobile-zh.jpg)：中文界面、英文研究内容，图已检查无布局遮挡 |
| 正式端 CQA 演化 | [AX](../../var/workbench-v2-acceptance/browser/production-cqa.txt)、[截图](../../var/workbench-v2-acceptance/browser/production-cqa.jpg)：真实 0→6→1,807→54、Enabled 24、28 个已记录阶段；54 工作集与 24 启用明确分开 |
| CSV 按钮 | [实际点击记录](../../var/workbench-v2-acceptance/browser/snapshot2-export-click.json)：选定 snapshot 2 后点击成功，页面保持可用；**未独立观察浏览器原生下载落盘**。交付的完整 CSV 由 API 导出并已独立核对内容与 hash，不声称 Downloads 文件已观察成功 |
| 生产新版与旧链接 | [新版 AX](../../var/workbench-v2-acceptance/browser/production-snapshot2.txt)、[截图](../../var/workbench-v2-acceptance/browser/production-snapshot2.jpg)、[旧链接 AX](../../var/workbench-v2-acceptance/browser/production-legacy-link.txt)：两者实测可打开，最后回到新 snapshot 2 |

[生产部署记录](../../var/workbench-v2-acceptance/production-deployment.json) 记载 2026-10-16T07:31:30.667108Z，
8769 新服务 PID 3152；旧 8769 与 preview 8770 按归属检查后停止，切换前无活动 legacy jobs，8765 用户转发未触碰。
新根及旧兼容链接均为 HTTP 200。正式端设置、中文窄窗口和标准演化检查后，界面已恢复英文并回到最终候选榜。
首次合并切换命令被策略在执行前拒绝，没有触动服务；
随后分别核对身份并执行停止/隐藏启动，交接已完成，不存在待审批或未完成切换。

生产入口：[最终 snapshot 2 工作台](http://127.0.0.1:8769/workbench/?view=candidates&task=task_01M51AQ0JK0MYN47806ZD5XS1B&snapshot=lb_task_01M51AQ0JK0MYN47806ZD5XS1B_2&lang=en)。
科学源码为 14a4047b…，UI 为 5825351b…；旧科学失败、原快照、未知费用及初始备份保留。
本轮不重测 B，不读取封存 evaluator 内容。本次实现、验收与交接已完成；上述研究未知和浏览器原生落盘观察边界按原记录报告。
