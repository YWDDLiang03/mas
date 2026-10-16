# Windows mid 完整验收 — 2026-10-16

**按用户后续调整的目标，本轮工作已完成：A 达到 top 5，Windows 浏览器从 Settings 到完整榜单导出实际跑通，英文默认和中文界面切换可用。** B 和 reduce 数量按软指标如实报告。结果是有冻结配置与来源记录的探索性研究读数。

当前界面：[完整结果](http://127.0.0.1:8769/leaderboard?task=task_01M50Q5EZE12GGDES5QNWR0JQX&snapshot=lb_task_01M50Q5EZE12GGDES5QNWR0JQX_1) · [Settings](http://127.0.0.1:8769/settings?task=task_01M50Q5EZE12GGDES5QNWR0JQX) · [Surufatinib 证据](http://127.0.0.1:8769/candidate?task=task_01M50Q5EZE12GGDES5QNWR0JQX&id=cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N&snapshot=lb_task_01M50Q5EZE12GGDES5QNWR0JQX_1)。

## 最终结果及其含义

| 读数 | 本轮完整运行 | 保留的原 Windows A |
|---|---:|---:|
| Surufatinib 排名 / 可排名候选 | **5 / 50** | 5 / 50 |
| 总候选数 | **3,177** | 3,177 |
| 偏好证据覆盖 | **8 / 9（88.89%）** | 8 / 11（72.73%） |
| 指定受体证据覆盖 | **5 / 5** | 4 / 5，CSF1R 缺失 |
| 已处理评估单元 / 计划单元 | **28,593 / 28,593** | 34,947 / 34,947 |
| 状态 | provisional | provisional |

前五名为 Tinengotinib、Catequentinib、Erdafitinib、Motesanib、Surufatinib。Surufatinib 的本轮分数为 **0.6962960276309735**。排序覆盖门槛为 0.5；指定标准资格门槛为 1.0，资格与排名分别报告。

本轮提高了指定靶点的证据完整性，名次仍为第 5。评分集、补证和机器复核共同改变了测量配置，因此两次结果作描述性对照。全量完成表示每个计划单元都有评估状态：其中 19,231 个仍是 `unknown_missing`，7,347 个 pass，2,015 个 fail；全库证据覆盖约 33%，达到排序覆盖门槛的候选为 50 个。

Surufatinib 的五个指定受体均有证据，但“已获批口服途径”硬条件仍待专家决定，口服临床文献项在本轮明确延后；整体状态保留 provisional。另一项偏好“已记录机制涉及的指定受体数量”缺少可用计数，保持未知；TPSA 121 Å² 超过本次解释得到的 90 Å² 偏好阈值，失败状态保留。结果用于研究优先级，不能代替临床有效性或专家确认。

## Reduce 与 B

注册标准从 93 条减少到 **59 条**，另有 **5 条未注册待处理项**，总 active 数为 64；没有为压到 30 而删除独立终点或隐藏未知。冻结构成为：**9 条评分、46 条延后、4 条注册待决定**。后两类仍保留在标准集和历史中。38 条最新注册谱系处于退役状态，历史注册记录完整保留。

最终固定 59 条注册集的 B 只提交一次有效 comparison：**exact 0、near-equivalent 1、missed 10，即 1/11（9.09%）**；额外内容按意义计 41 项、按标准计 58 条。5 条未注册 backlog 不计入 B。比较输入锁在 task seq 1852，digest 与报告间没有漂移，gate 首次通过。

本次 B 为 `assisted / descriptive_inherited`，沿用前次隔离评价的严格解释。原 4/11 和 93 条集的 1/11 均保留；标准集合、早期解释执行和审计曝光不同，不能把这些差值当作受控的能力变化。B 按用户软指标要求结束，不根据已看到的列表继续调整标准。

安全聚合摘要：[evaluator_safe_aggregate.json](../../var/primary/recovery/task_01M50Q5EZE12GGDES5QNWR0JQX/evaluator_safe_aggregate.json)。Evaluator-only 输入、映射及逐项报告保持在 ignored 目录，根代理未读取本次明细。

## 补证实际如何进入结果

使用已核验的 [Lin 等，Communications Chemistry 7, 3 (2024)](https://doi.org/10.1038/s42004-023-01084-0) 原文：WT CSF1R IC50 **5 nM**、WT FGFR1 **34 nM**，两条突变测量排除并保留理由。实验构建修饰和未知 ATP 条件留在来源记录。

- CSF1R：`9 − log10(5) = 8.301029995663981 pChEMBL`，与保存的 cell 一致。
- FGFR1：34 nM 转为 7.468521082957745 pChEMBL，与另外三条已接纳记录共同按冻结的 median 聚合，得到 **7.6442605414788725**；没有只挑较高值。
- **没有使用其他化合物平均值填补缺失。** 来源选择发生在知道参考候选缺口之后，已标记 `exploratory_known_gap_source`；本轮未执行对所有候选对称的文献搜索。

证据：[原文核验](supplement_source_2024.json) · [两条最终 cell 的转换与聚合复核](supplement_cell_trace.json) · [参考候选完整数据](../../var/acceptance-mid/reference-candidate.json)。

## 实际浏览器流程与修复

采用浅蓝界面，英文默认；English / 中文切换保存界面选择，研究任务、标准、证据、提示和原文不随界面语言改写。常用操作使用简明名称，编号和完整记录放在次级展示或展开区。

| 环节 | 本次实际证据 |
|---|---|
| Settings | 实际选择两项 Medium 并保存；有效值均为 `mid`，4 workers、breadth 4、depth 2、40 full reads、USD cap 10、autonomous |
| 当前任务与导航 | 实际切换任务及语言、点击六个主导航；当前任务保持一致，页面正常加载 |
| Reduce | 继承与 reduce 通过工作台 HTTP 操作入口执行；明确记录渠道，没有将其称为鼠标点击 |
| 补证与三项复核 | 实际点击添加补证，逐项提交 MW、logP、TPSA 机器复核；MW 拒绝 500 上限并保留纯测量排序，另外两项记录解释来源 |
| 冻结与运行 | 实际提交 Prepare evaluation，选择新配置，点击 Start full run 并跟进真实进度至完成 |
| 榜单与证据 | 实际打开榜单、下一页和上一页、筛选 Surufatinib、查看其 9 项评估与 16 条接纳证据 |
| 下载 | 实际点击 Export full results，下载 CSV；**3,177 个唯一候选**，与同 snapshot 的完整 API 导出逐字节一致 |
| 复核页面 | 仅当前任务的有效版本进入待处理计数：30 条；29 条旧版本请求另行展示 |
| 窄窗口与双语 | 候选名称、数值、单位及按钮不再逐字断行，表格横向滚动；中文只改变界面标签，英文研究名称和数值保持原样 |

真实 GUI 记录：[gui_verification.json](gui_verification.json)。早期 HTTP 检查与浏览器不可用记录作为历史保留，后续已用实际浏览器完成上述流程。

修复了 task 缺失的导航链接、任务切换后语言链接回跳、历史完成作业重新选择旧任务、未知 run 类型导致首页异常、Review 列表混入其他任务/旧版本及急算路线导致等待、运行中准备按钮状态、保存提示中英混杂，以及窄窗口表格断字。UI 后续修复只增加精确版本的标准显示名和排版；[最终 9 个 cell 逐字段核对](post_evaluation_display_check.json)确认数值、单位、判定、证据、分数和排名不变。

## 工程与流程分析

**实际故障已保留并定向修复。** Reduce 的科研 run 已完成，结束原因 `round_limit_reached`；随后 CLI 打印合法的 `retained_unchanged` 结果时发生 `KeyError: rule_kind`，进程退出码为 1。打印器修复后从已保存 artifact 恢复报告，没有再次支付一次 reduction，也没有把原失败作业改成成功。

终态审计发现旧 reduction 改写了任务强制靶点绑定。系统在原结果上追加可审计纠正，恢复原始作者与父谱系；后续 reduce 保护任务锚点，freeze 前后都核对五项原始要求。最终 profile 中保存五个指定受体 proof，避免通过缩小要求分母制造资格改善。

已实施的流程优化包括：只重用明确来源 run 的成功/空工具结果；从历史 PubChem 整行记录本地取列；refine 去除复制链等非科学元数据、保留证据/异议，批次从 20 改为 8；模型修复调用的费用与 token 聚合、异常已知费用保留；Windows Exchange 临时共享锁的有界重试。两份旧 trace 的同批 prompt 字符分别减少 **23.48% / 17.77%**，这是离线输入比较，后续实际时间和费用收益尚未单独测量。

最终 sweep 约 **10 分 40 秒**。60,364 条工具结果中，50,832 条是历史精确重放，9,252 条是历史 PubChem 本地投影，279 条是普通 PubChem provider 调用（均返回空），1 条是普通 ChEMBL provider 调用。工具调用数量不等于 HTTP 请求数量：PubChem 共用整行缓存，ChEMBL 会分页。没有 `tool.errored`。

剩余性能热点已定位：一次 ChEMBL 调用约 249 秒；完成阶段重复扫描历史 run journal 的区域约 68 秒，当前 journal hash 约 8 秒。后续新配置可显式纳入本次已完成来源来减少重复外部请求，或为快照查询建立索引。本轮不改变冻结来源或重跑已完成实验来追求速度。

设计能力审查及闭环状态见 [design_validation_review.md](design_validation_review.md)。本轮覆盖继承、reduce、补证、配置冻结、全量评估、来源回溯、双语 UI、导出和数值复现；新一轮全库文献检索、预测模型性能、跨家族独立性、专家判断质量与跨任务泛化不在此次实测范围。

## 验证、费用和可复现身份

冻结 cell → calibration → roll-up → score → 完整榜单的离线复算 **PASS，0 differences**；覆盖所有 3,177 个身份、28,593 个评估单元、分数、覆盖、资格及名次，浮点容差 1e-12。复算为只读，没有重新抓取来源或调用模型。[leaderboard_replay.json](leaderboard_replay.json)

既有相关验证保持有效：required bindings / reduction / measurement 等组合 94 passed；CLI 打印故障相关 13 passed；最终表格与候选展示的三个既有定向测试通过。测试数字表示各次相关检查，存在覆盖重叠，不累计成一个新的全项目通过数。

本轮记录的 DeepSeek 费用估计：来源阅读 **$0.003781**、reduction **$1.902035**、三项复核 **$0.0166893**，合计 **$1.9225053**。最终 sweep 没有新的模型调用。旧 reduction/source 事件缺少完整逐尝试用量，合计是保留的已知估计，不是完整账户账单；不含更早实验及 Codex 智能体用量。[cost_record.json](cost_record.json)

| 身份 | 固定值 |
|---|---|
| Task | `task_01M50Q5EZE12GGDES5QNWR0JQX@v2` |
| Run | `run_01M50X7EYSBXPDCP0SG859666R` |
| Snapshot | `lb_task_01M50Q5EZE12GGDES5QNWR0JQX_1` |
| Rules / profile | `rules@v1` / `art_5a84d471a676` |
| 配置 SHA256 | `e2c30f795622fa7bfbf7754d1b8a5b89282e61e1abbd98672cf425686260c31c` |
| 执行源码 SHA256 | `1f8cd8ce24c35e354b340a5c7543de51354d1d9a277b8dce0e13d5bad0f21b4e` |
| 执行源码 archive SHA256 | `148a951dd20aa11f64037ae983f089b35c395a5ad7dcb4ecb10962fe2dd2f795` |
| GUI 下载 CSV SHA256 | `a03a3fcebef772f7984b6582ae52971d7b2ec6ac9de59cccabeac3f96fc5142d` |

执行源码：[source.zip](../../var/provenance/mid-acceptance-sweep/1f8cd8ce24c3/source.zip)。科研结果和已经完成的复算绑定此版本。运行之后的两个 UI 显示文件另存 [final_ui_implementation.json](final_ui_implementation.json)，不追认原运行使用了后来的界面源码。

如需再次复算，先解压上述执行源码，把 `PYTHONPATH` 指向其 `src`，再使用 `scripts/verify_leaderboard_replay.py` 和表中的 run/snapshot/profile/rules；当前工作区包含后来的 UI 修复，直接用它会被精确源码检查拒绝。已有 PASS 结果无需为了交付重复运行。

## 交付文件

- [完整 GUI 下载 CSV：3,177 行](../../var/acceptance-mid/browser-leaderboard.csv)
- [完整榜单 JSON](../../var/acceptance-mid/leaderboard.json)
- [最终读数](mid_reading.json) · [最终执行清单](final_execution_manifest.json)
- [冻结配置](../../var/acceptance-mid/measurement-profile.json) · [五项原始绑定审计](../../var/acceptance-mid/reduction-binding-audit-frozen.json)
- [原 A 读数](primary_reading.json) · [原 A 执行清单](execution_manifest.json)
- [CLI 原结果恢复报告](../../var/acceptance-mid/reduction-report-recovered.txt)
- [英文候选页截图](../../var/acceptance-mid/browser/surufatinib-final.jpg) · [中文候选页截图](../../var/acceptance-mid/browser/surufatinib-zh-final.jpg) · [窄窗口榜单截图](../../var/acceptance-mid/browser/leaderboard-final.jpg)

![最终英文界面](../../var/acceptance-mid/browser/surufatinib-final.jpg)
