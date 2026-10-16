# 实施与交付状态 — 2026-10-16

**交付完成：snapshot 2 中 Surufatinib qualified、位置 4/10；22 项独立数值检查全过，新旧快照 GUI、CSV 点击及生产 8769 交接均已完成。**
此页取代之前混杂的进行中检查点。原运行、失败、源码绑定、导出及验收文件保留原样，历史材料不充当当前状态。
交付总表与研究未解决项见 [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md)，标准演化见 [CQA_EVOLUTION.md](CQA_EVOLUTION.md)。

## 当前实际状态

- 任务：`task_01M51AQ0JK0MYN47806ZD5XS1B`；工作流：`wf_033db93e15fa4bb289c2e03606674f6b`。
- Snapshot 2 已完成：`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_2`，run `run_01M51RRJ8Y3D5DYAQGMYPY13AP`，rules@v3，profile `art_9d00e221a8fc`。
  全库 3,177：qualified 10、pending 3,167、rejected 0、unassessed 0；Surufatinib qualified、位置 4/10，score **0.6629629629629631**，与 Nintedanib 第 5 同分；
  hard **1/1**、必需靶点 **5/5**、直接偏好证据覆盖 **0.5238095238095238**。这些实际 API 读数已经 22 项独立 source/API/CSV/score 检查验证。
- Snapshot 1 历史记录保留：`lb_task_01M51AQ0JK0MYN47806ZD5XS1B_1`，run `run_01M51NWNGBK6EY7AAC4GZEQBVC`，rules@v2，profile `art_8e5c3de6bcc7`。
  3,177 候选，10 qualified、3,167 pending；Surufatinib 为 qualified、位置 4/10，得分 0.6074074074074075，与 Nintedanib 同分。
- 导出后数学审计发现两条 logP 的区间距离与原值比较符语义不一致。根任务已完成新版本复核、rules@v3 冻结及全库筛选，并发布上述 snapshot 2；原 snapshot 1 与原问题保留。
- 新汇总仍为 43 个注册、19 个延后、11 个未注册 pool 待处理；24 个参与评估记录含 1 hard、22 preference、1 context。
  两条 logP 保留各自算法与来源，显式同 quantity_id、同 2–4 距离决策，沿用 direct-first，预测旁证不加第二分。
  [新冻结只读核对](../../var/workbench-v2-acceptance/snapshot2-freeze-readonly-check.json) 已确认 24 执行条目=23 独立决策（21 preference、1 hard、1 exploratory）。
  两条 logP 均获 agent_verdict/bound_interpretation_granted/approve，confirmed_by_a_person=false，不是人审。
  新 run `run_01M51RRJ8Y3D5DYAQGMYPY13AP`，profile `art_9d00e221a8fc`；旧 snapshot 1 哈希保持不变。
- 最新源码归档：[14a4047b794d1696](../../var/provenance/workbench-v2/14a4047b794d1696/manifest.json)。

## 已实施的用户流程

| 路径 | 实际状态与依据 |
| --- | --- |
| Settings→目标草稿→一次启动 | 真实 GUI 已保存 mid/mid、4 workers；填写多行目标及可选 targets/constraints/library/evidence source/reference；[session](../../var/workbench-v2-acceptance/session.json)、[草稿截图](../../var/workbench-v2-acceptance/browser/research-draft.jpg) |
| Edit task | 预填目标与选项，记录 revision_of，原任务/结果保留；新研究从空 CQA 开始；[启动记录](../../var/workbench-v2-acceptance/full-run-start.json) |
| Overview / Criteria / Candidates / Evidence / Settings | 真实 API 读取；任务选择稳定；筛选状态保持；Criteria/Evidence 的恢复和 Candidates 全库第二页 51–100 of 3177 刷新恢复均有真实 GUI 证据 |
| 全局进度 | 真实阶段、活动、耗时、最近记录时间与费用；未知分母不造百分比；暂停/继续/停止和重启后的保存位置已有实测；完成态紧凑、阶段可展开 |
| CQA 生成与提炼 | 0→6→1,807→54，37 提案注册+6 任务绑定=43 注册，另 11 待处理；[演化记录](CQA_EVOLUTION.md) |
| 标准与任务编辑 | 任务绑定通过 Edit task 修改；普通标准保存新版本并重新复核；LD50 v1→v2 的实际 GUI 修改、原值和理由已保留 |
| 版本与谱系 | 阶段条目按 change 打开，注册条目按精确版本打开；真实父 v1 可点击，保留阶段/搜索；属性与规则的 supersedes 前后字段分别比较 |
| logP 新版本复核与进度 | [新版差异 AX](../../var/workbench-v2-acceptance/browser/logp-v2-review-and-diff.txt)、[进度 AX](../../var/workbench-v2-acceptance/browser/corrected-run-progress.txt) 已实测；保存时 72,826/76,248、96%，不冒称已完成 |
| Candidates 全库分页恢复 | [page2 refresh AX](../../var/workbench-v2-acceptance/browser/all-candidates-page2-refresh.txt) 显示刷新后仍为 51–100 of 3177 |
| Pending 原因 | 原注册状态与最近准备评估状态独立；MW v2 Active + Deferred、真实 queue/receipt 理由可展开；历史版本不伪造过去的未启用结论 |
| 资格与排名 | 先硬条件及必需靶点直接证据，再偏好排序；qualified/pending/rejected/unassessed 分组，50 条分页、完整 CSV、具体未排名原因和来源卡 |
| 结论→证据 | 实际 GUI 已跳到口服支持来源，并显示 Show all evidence；按真实 claim refs 筛选，反证单列，无引用时原因保留 |
| 英文/中文和窄窗口 | 英文默认，中文仅界面；真实 EN→中文→EN、研究原文保持与 390/760px 截图均已留存；详见 [验收证据表](FINAL_ACCEPTANCE.md) |

## 科研与测量约束

- 本轮 existing_only，从已保存事实生成，不新搜文献、不重读全文或新算 ADMET。事实 manifest `art_a3ad5ef89e0b` 固定 3,157 个去重事实和 164 个来源；library 为 3,177 项。
- 参考候选被声明用于结果对照，其专属内容从标准派生中排除；不能增加参考候选得分或按名次选择阈值。
- 预测可辅助偏好，不能单独硬淘汰或增加直接证据覆盖。排名覆盖仍是直接权重/全部适用偏好权重（含预测专用条目），原门槛 0.5 未改。
- 可执行性、严格 withhold 和新复核决定条目能否启用；机器决定不冒充专家批准。MW 有保存的 PubChem 数值，但截点复核尚未解决，当前仍延后。
- 条目数为软目标。明确报告注册、未注册待处理、延后、启用及同量决策去重数量，不以启用条目数伪装全部提案已压缩完成。
- B 本轮不重测，封存 evaluator 内容不读取。

## 已完成验证与原失败记录

Snapshot 1 的 [工程验收 v2](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/report.md) 全部通过：

| HTTP 列表 | 样本数 | P95 ms | 错误 |
| --- | ---: | ---: | ---: |
| Overview | 50 | 69.813 | 0 |
| Criteria | 50 | 189.862 | 0 |
| Stages | 50 | 32.449 | 0 |
| Candidates | 50 | 32.491 | 0 |
| Evidence | 50 | 34.824 | 0 |

隔离 query DB 重建 49.073 秒；源库、服务缓存只读；源/API/缓存/重建的标准、阶段、候选资格/ID/排名/分数及最近评估理由全部对齐。
[导出复核](../../var/workbench-v2-acceptance/final-task_01M51AQ0JK0MYN47806ZD5XS1B-v2/export-postcheck.json) 证明 3,177 行 CSV/API/snapshot 一致，14 个 manifest 文件哈希和大小匹配。
这说明 snapshot 1 的工程记录正确，不消除后来发现的 logP 数学问题。

保留的真实故障及处理：

- 早期 normalizer 口服约束 alias 漏接、长响应截断及内部重试不可及时暂停，均保留停止记录与费用；后续统一 route、批次和按请求检查点修复。
- 版本化生成续跑复用已完成批次；一个原逻辑请求只有 started 记录，未找到 finished/provider-attempt，费用保持未知，旧 run binding 保留。
- 旧 partial sweep `run_01M51MS4KW71HX2FEMTPJ01JHA` 已取消，保存 34,131 单元。MW 错绑预测端点已作为新版本改到精确保存的 PubChem MolecularWeight 路线，再由严格复核决定能否启用。
  [匿名只读诊断](mw_existing_only_diagnostic/REPORT.md) 保留 3,084 行 projection digest 与 1,136/1,177 精确匹配证据；无新计算。
- 验收初次误拒绝 `error:null`、随后 Criteria 读取性能及旧 stage DTO 表示差异均有失败文件；修复后才取得工程 v2 通过，不改写失败。
- logP 距离/区间数学问题通过新属性/规则版本、共享量身份及新冻结修订；数学修正后的 snapshot 2 已完成并用于科学最终验收。

## 费用与档案

- Snapshot 1 已知工作流费用 USD 3.8478801；先前两次停止工作流 USD 0.3239793，已知合计 USD 4.1718594。
  费用状态保留 partial：有一个 legacy 逻辑 started 没有 finished/provider-attempt，不能当作精确最终账单。
- 已核对 rules@v3 完成后的已知工作流小计 USD 3.8550975（比旧多 0.0072174），加先前停止流程后已知小计 USD 4.1790768；legacy 未闭合请求费用未知继续保留。
- Snapshot 2 [完整导出](final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/report.md) 已成功：15 文件，manifest 列 14 个数据文件；exporter 自检 3,177 行 CSV/API/snapshot ID 多重集一致，[22 项独立数值核验](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) 已通过。
  Snapshot 1 的 [原 manifest](final/wf_033db93e15fa4bb289c2e03606674f6b/manifest.json) 保留，新目录不覆盖旧快照。
- 初始 [一致备份 manifest](../../var/backups/workbench-redesign-20261016/manifest.json)：5,520,838,656 bytes，SHA256 `63301bb0e17cfca84cc18855c35a004ba70f4b680c803017280338df1c23b033`；这是本轮开始前备份。
- 生成源码 [210c6fe3…](../../var/provenance/workbench-v2/210c6fe3ab139d5c/manifest.json)、snapshot 1 科学绑定 [1cd1f401…](../../var/provenance/workbench-v2/1cd1f401bf2d21f9/manifest.json)、后续读取/展示归档 [35ce8d6f…](../../var/provenance/workbench-v2/35ce8d6f2999a19c/manifest.json)、新数学修订 [14a4047b…](../../var/provenance/workbench-v2/14a4047b794d1696/manifest.json) 分别保留。
- 最终 React UI 已归档 [5825351b…](../../var/provenance/workbench-v2-ui/5825351b32ac2d98/manifest.json)，后端科学绑定仍为 14a4047b…，原归档未覆盖。
  最后仅隐藏表格重复的 qualification 状态回显，原 reason/API/数值记录保留；根任务已通过 TypeScript/Vite。历史 [b1cffa0b…](../../var/provenance/workbench-v2-ui/b1cffa0b13f19c0b/manifest.json) 继续保留。

## 最终交付状态

- [独立数值核验](../../var/workbench-v2-acceptance/snapshot2-numerical-check/report.md) 全部 22 项通过：76,248 个 source 单元、3,177 候选 score/rank/API/CSV 一致；两 logP 中 2,956 可用值按原 claim 公式全部一致。每个合格并排名候选实际参与 weighted score 的偏好值为 15，不把 24 条执行记录当作 24 个计分值。
- 真实 GUI 已完成 [snapshot 1 保留切换](../../var/workbench-v2-acceptance/browser/snapshot1-switch-preserved.txt)、[snapshot 2 切换刷新](../../var/workbench-v2-acceptance/browser/snapshot2-switch-refresh.txt)、[最终候选详情](../../var/workbench-v2-acceptance/browser/snapshot2-surufatinib-detail.txt) 和 [完整最终榜单](../../var/workbench-v2-acceptance/browser/snapshot2-qualified-board-full.jpg)。
- 正式 8769 已实测 [Settings](../../var/workbench-v2-acceptance/browser/production-settings.txt) 的 Medium/Medium、4、9.67 保持；[中文 390px](../../var/workbench-v2-acceptance/browser/production-mobile-zh.jpg) 保留英文研究内容，图已检查无布局遮挡；[CQA 演化](../../var/workbench-v2-acceptance/browser/production-cqa.txt) 显示 0→6→1,807→54、Enabled 24 和 28 个阶段。检查后界面恢复英文并回到最终候选榜。
- [CSV 实际点击](../../var/workbench-v2-acceptance/browser/snapshot2-export-click.json) 已完成。浏览器原生下载文件未独立观察；实际交付 CSV 通过 API 完整导出并由独立核验确认内容/hash，不伪称 Downloads 落盘已观察成功。
- [生产部署](../../var/workbench-v2-acceptance/production-deployment.json) 已完成：8769 新服务部署记录 PID 3152；按归属停止旧服务及 8770；8765 未触碰；根和旧链接 HTTP 200。
  [新版生产 AX](../../var/workbench-v2-acceptance/browser/production-snapshot2.txt) 与 [旧链接 AX](../../var/workbench-v2-acceptance/browser/production-legacy-link.txt) 均实测，最终停留新 snapshot 2。
- 首次合并迁移命令在执行前被 policy 拒绝，未修改服务；拆分身份核对后成功交接，无待审批/未完成项。科学源码 14a4047b…、UI 5825351b… 和旧归档分别保留。

实现、验证和交付已完成。研究未知、未闭合 legacy 费用及原失败记录按原样保留，详情和入口见 [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md)。
