# 工作台易用性与通用 CSV 流程验收

更新日期：2026-10-16。

本轮已通过真实 GUI 完成自定义载体任务的候选导入、测量校验、草稿保存、启动、故障修复后恢复、标准生成和完整评估，最终保存了第二个结果快照。三个候选均为明确标注的合成工程数据，用来检查软件流程；结果不构成载体性能的科研结论。

本轮验收已完成：通用 CSV 流程通过独立来源/判定复核，证据关联、原文上下文、双语及窄屏展示已实际浏览器验证，新版已部署至 8769。先前药物研究的最终快照与导出保持一致。

## 版本与结果定位

| 项目 | 实际记录 |
| --- | --- |
| 研究任务 | `task_01M51XZ4F555HRPDD3X5H8QGWN` |
| 工作流 | `wf_8f251703c86449118d90094ba3fda439` |
| 草稿 | `draft_e3a2243eaf7048a5983789798ffe9533` |
| 最终评估运行 | `run_01M51YYATSTRNXR6C7HSDA2CZF` |
| 最终快照 | `lb_task_01M51XZ4F555HRPDD3X5H8QGWN_2` |
| 载体最终评估绑定实现 | `6528cbfa9ef07d09845b0e78c2177c02cd6e5604aec35b259891744769336591` |
| 最终部署后端 | `b7f38e2682426287c5fb7d0cdb5fcfefee901e6a3c6be86fb904a8c47db44476` |
| 最终前端归档摘要 | `b79b47437f2f252c31e4f1d2366b4b2fd0bc0dd7fd119e5dde28fc1032a9a999` |
| 使用入口 | `http://127.0.0.1:8769/workbench/` |
| 兼容入口 | 8770 已重定向至 8769，真实浏览器已验证；8765 原转发未触碰 |

精确部署依据为[最终构建](../../var/workbench-usability/final-build.json)和[生产切换记录](../../var/workbench-usability/production-deployment.json)。最终前端资源为 `index-DLzE2VLa.js` / `index-DTcDzMxU.css`，构建目录为 `web/client/dist-next`。后端与前端分别归档：[最终后端清单](../../var/provenance/workbench-v2/b7f38e2682426287/manifest.json)、[最终前端清单](../../var/provenance/workbench-v2-ui/b79b47437f2f252c/manifest.json)。后端归档内较早的 UI 不代表最终 UI，以独立前端清单为准。

载体评估绑定的 [6528 实现归档](../../var/provenance/workbench-v2/6528cbfa9ef07d09/manifest.json)继续保留，部署更新没有改写该运行的源码绑定。

本轮通用 CSV 任务与先前药物研究分开保存。先前科研快照及其 `14a4047…` 科研源码归档保持原记录，参见[上一轮最终验收](../workbench_redesign_2026-10-16/FINAL_ACCEPTANCE.md)。

## 用户流程的真实 GUI 证据

验收从 Settings 开始：search/textbook 均为 Medium，并发 4，通用合成任务临时费用上限为 $1。通过 **Use own data** 新建 carrier 研究，输入自定义目标，未自动继承当前药物案例的证据来源。验收完成后，未来新任务的设置已恢复为 Medium / Medium、并发 4、费用上限 $10，见[恢复后的 Settings](../../var/workbench-usability/browser/settings-restored.txt)；已保存运行的原费用上限与历史费用保持原值。

| 用户动作 | 实际观察 | 保存证据 |
| --- | --- | --- |
| 候选 CSV 粘贴、列映射与预览 | 三个独立文本 ID 与可读名称，候选表先保存，研究尚未启动 | [候选预览截图](../../var/workbench-usability/browser/csv-candidate-preview.jpg)、[候选 CSV](../../var/workbench-usability/fixtures/carriers.csv) |
| 测量 CSV 校验 | 12 行中 11 行有效，明确提示 `Row 2 · Unit` 缺失数值单位 | [缺单位错误](../../var/workbench-usability/browser/csv-unit-error.txt) |
| 修正单位并重新校验 | 12/12 行有效，最多展示前 10 行预览；随后保存与所选候选库绑定的测量表 | [修正后预览](../../var/workbench-usability/browser/csv-measurements-preview.txt)、[测量 CSV](../../var/workbench-usability/fixtures/carrier-measurements.csv) |
| 保存草稿 | 显示 `Draft saved. Research has not started.`，导入与启动分开 | [草稿与数据就绪](../../var/workbench-usability/browser/csv-study-ready.txt) |
| 一次启动与常驻进度 | 新任务实际创建，显示 0/8 个流程阶段；等待、恢复和后续阶段由保存状态驱动 | [启动截图](../../var/workbench-usability/browser/csv-live-start.jpg)、[启动页面](../../var/workbench-usability/browser/csv-live-start.txt)、[启动响应](../../var/workbench-usability/carrier-start.json) |
| 完整评估完成 | 最终工作流 `completed`，8/8 个阶段完成，保存第二个快照 | [最终工作流](../../var/workbench-usability/carrier-completed-final.json)、[最终榜单截图](../../var/workbench-usability/browser/carrier-final-board.jpg)、[榜单页面](../../var/workbench-usability/browser/carrier-final-board.txt) |
| 候选逐条判定与证据 | 候选详情提供精确标准版本、判定值、依据和支持证据 | [候选详情记录](../../var/workbench-usability/browser/carrier-detail.txt) |

本轮 GUI 实际使用的是粘贴 CSV 入口。文件选择及 `File.text()` 已接线，不以粘贴验证冒称浏览器文件选择已独立实测。模板、字段和适用范围见[CSV 使用指南](CSV_GUIDE.md)。

## 合成载体任务的最终结果

最终 API 结果为 3 个候选：qualified 2、rejected 1、pending 0、unassessed 0，采用 staged screening。数值来自[最终候选响应](../../var/workbench-usability/carrier-results-final.json)，最终工作流来自[完成记录](../../var/workbench-usability/carrier-completed-final.json)。

| 合成候选 | 结果 | 合格榜名次 | 偏好分 | 关键判定 |
| --- | --- | --- | --- | --- |
| Example carrier A / `DEMO-A` | Qualified | 1 | 1.0 | cell viability 92%，通过 ≥80% 的硬条件；已回答必需观测 |
| Example carrier B / `DEMO-B` | Qualified | 2 | 0.0 | cell viability 85%，通过同一硬条件；已回答必需观测 |
| Example carrier C / `DEMO-C` | Rejected | — | — | cell viability 55% <80%，在硬条件阶段淘汰，后续偏好不用于挽回资格 |

目标要求 `surface_charge` 有直接记录，但没有指定偏好正电或负电。最终语义为记录是否可用，不添加方向性偏好。A 的详情保留相应 `available` 判定与原始 -10 mV 观测；该属性不因正负号产生额外排名分。

原始合成表包含四种属性：`particle_size`、`cell_viability`、`delivery_efficiency`、`surface_charge`，每行保留条件与合成来源说明。UI 中的依据类型是上传者声明，数据合成属性并未因 `measured` 标签变成真实实验。

独立复核已通过，见[复核报告](../../var/workbench-usability/generic-source-audit.md)与[逐条 JSON](../../var/workbench-usability/generic-source-audit.json)：

- 12 条上传观测与 12 条 admitted claims 的候选、属性、值、单位、条件、声明依据、行位置与 quoted row/hash 全部一致。
- 冻结方案为 1 hard、2 preference、2 context，共 5 条执行记录、4 种属性。两条 surface charge 记录均为 context / recorded observation；其中任务模板负责 required direct scope，另一条保留生成轨迹，不形成额外方向偏好。
- staged 实际保存 15 个 cells：11 个完成评估、4 个在 C 的硬失败后明确跳过。C 的已上传粒径与递送效率仍有来源，跳过不被写成缺证。
- 离线 full 计算全部 15 个 cells，离线 staged 与保存语义一致；两种模式均得到 A→B、分数 1→0，C rejected。完整模式一致性来自离线复核，没有第二次 GUI full-mode 实跑。

两项偏好只在合格的 A、B 中分别归一化，A 两项均为 1，B 均为 0，默认等权得到上述分数。复核同时分别记录 fixture 原 UTF-8 BOM/CRLF 字节 hash 与 GUI 提交 UTF-8 文本 hash；GUI 粘贴使用 LF，上传 hash 对应实际提交文本，逐行内容一致。

## 已暴露并修复的问题

| 真实故障 | 修复后的行为 | 历史记录 |
| --- | --- | --- |
| 任务解析把“必须存在某观测”重复表达为无阈值 hard 条件 | 区分数值硬条件、必需观测与偏好，保留无方向的 observation 语义 | 初次解析失败与随后 Resume 保留，不把原失败改写为成功 |
| 上传条件为对象，而部分解码路径预期字符串 | 对保存的条件文本/对象采用精确兼容，条件集合仍与原行一致 | 原上传条件和失败记录保留 |
| 修订实现后复用旧运行被版本策略阻断 | 精确复用不满足时创建 fresh 评估，继续使用保存的数据与已生成标准 | [版本阻断响应](../../var/workbench-usability/carrier-completed-v2.json) 保留 `reuse policy drift: tool_availability_snapshot`；最终运行另存 |
| 上传测量 JSON 直接占据证据卡主视图 | 严格识别完整测量记录后，显示属性、观测值/单位、条件、声明依据、来源与行位置；完整 JSON 留在 Source record 折叠区域 | 普通文献引文保持原文 blockquote；[真实 GUI 证据卡与解读](../../var/workbench-usability/browser/csv-readable-evidence-and-brief.txt)已验证 |
| CSV 下载响应重复 `Content-Disposition` | 候选/测量模板与完整候选导出均只返回一个下载响应头 | [响应头核对](../../var/workbench-usability/csv-download-headers.json)均为 HTTP 200；[修复后实际点击](../../var/workbench-usability/browser/carrier-export-after-fix.txt)后页面可继续使用 |

[第一个保存快照](../../var/workbench-usability/carrier-completed.json)、[旧候选响应](../../var/workbench-usability/carrier-results.json)与最终第二快照同时保留。上述恢复没有覆盖先前失败或旧结果。

## 进度、任务入口与数据用途

常驻浅蓝阶段轨道显示 Goal、Evidence、Develop、Refine、Review、Prepare、Evaluate、Results 八个真实流程节点，完成后仍保留可读轨道。已知分母的证据批次或候选评估使用各自进度；未知分母显示当前活动/等待状态，不伪造总体耗时百分比或剩余时间。费用、总耗时和最后记录活动分开呈现。

Overview 提供显眼的 New research / Use own data，研究目标与范围可直接查看并进入编辑新研究；任务选择及 URL、语言、精确快照/历史标准上下文一起保留。导入 Wizard 提供候选/测量两种类型、模板、列映射、预览、逐行错误和显式保存；未保存或未绑定的观测不悄然进入评估。

通用 adapter 使用用户提供的精确属性与条件，支持 drug、carrier、general。carrier/general 需要自有候选库及对应测量；已有 drug 库可按其精确 ID 补充观测，不按相似名称匹配或替代分子描述符。导入结构校验与后续科学审查分别保留。

## 证据关联、上下文与研究解读

证据 DTO 已提供精确标准版本、候选/运行/快照关系、保存的引文及可取得的相邻段落。列表预览与完整分页用途分开，候选筛选会明确限定关联作用域；没有保存快照的关联不自动跳入最新结果。确定性事实/用途投影、AI 研究解读与原文引句分别显示。

最后一轮 GUI 发现，某来源卡曾把 7,531 条候选运行记录标成候选数：实际由 cancelled 运行 1,177 条、第一快照 3,177 条和第二快照 3,177 条组成，独立候选为 3,177。关联投影现默认最新保存评估、显式历史快照保持精确；前端按 DTO 的单位分别显示独立候选、评估/运行记录及标准版本，并显示关联评估的真实发布日期或全部运行范围。[范围复核](../../var/workbench-v2-acceptance/evidence-connection-scope-check.json)确认默认 3,177 个独立候选、8 个精确标准版本，显式两快照的分页、总数与来源/原文上下文不变，24 个已缓存解读的 hash/status 不变；[最终 GUI 范围记录](../../var/workbench-usability/browser/evidence-scope-final.txt)已验证。

后端来源/上下文核对依据为[证据关联核对 JSON](../../var/workbench-v2-acceptance/evidence-context-final-check.json)与[接口/验证说明](../workbench_redesign_2026-10-16/EVIDENCE_CONTEXT_BACKEND.md)。其中早期 5 次本地 ReadModel 样本单独保留。最终性能另以真实 3,177 候选任务的 HTTP 读取检查，每个入口 20 次，见[HTTP 性能结果](../../var/workbench-usability/http-performance.json)：

| 查询 | 20 次 HTTP 的 P95 |
| --- | --- |
| Criteria | 199.915 ms |
| Evidence | 55.111 ms |
| 标准关联证据 | 46.590 ms |
| 候选关联证据 | 209.032 ms |
| Candidates | 37.505 ms |

五项均通过 P95 ≤300 ms 的本轮门槛；不将列表读取性能扩展为所有任务、详情或模型调用的延迟保证。

研究解读已在原药物研究的 24 个启用记录上显式生成两版：每版 18 个 AI 解读和 6 个基于任务要求的说明，无缺失/过期/错误。第二版较首版缩短；四节正文的实际合计词数为 164–323，原 quotes 单独保留。参见[第一版记录](../../var/workbench-usability/research-interpretations.json)与[第二版记录](../../var/workbench-usability/research-interpretations-v2.json)。

这些解读单独标记为 AI interpretation，保留精确 criterion ref、输入摘要和实际 claim/task 引用，不充当新证据或科学审批。GET 页面只读；新任务需要时由用户明确点击 Prepare research interpretation，结果缓存在独立 annotation store。annotation 全局累计上限 $0.50，跨任务/调用/重启累计；共享请求费用不会逐标准重复相加。

通用载体任务也已通过真实 GUI 显式生成一条粒径标准研究解读，见[载体解读记录](../../var/workbench-usability/carrier-interpretations.json)与[可读证据卡和解读页面](../../var/workbench-usability/browser/csv-readable-evidence-and-brief.txt)。该任务五条执行记录当前为 1 ready、2 task-backed、2 missing；本次仅通过按钮显式生成其中一条解读，其余没有自动产生模型调用。

## 最终 GUI、导出与生产交付

| 已完成检查 | 实际证据 |
| --- | --- |
| 正式入口、八阶段轨道、目标与自有数据入口 | [生产 Overview](../../var/workbench-usability/browser/production-overview.txt)、[截图](../../var/workbench-usability/browser/production-overview.jpg)；8770 实际浏览器进入后重定向 8769 |
| 原药物榜仍可读取 | [生产候选榜](../../var/workbench-usability/browser/production-surufatinib-board.txt)、[截图](../../var/workbench-usability/browser/production-surufatinib-board.jpg) |
| 中文窄屏与常驻进度 | [中文页面记录](../../var/workbench-usability/browser/mobile-progress-zh.txt)、[截图](../../var/workbench-usability/browser/mobile-progress-zh.jpg)；中文只覆盖 UI，研究原文保持英文 |
| 文献原文与相邻保存段落 | [最终上下文](../../var/workbench-usability/browser/evidence-context-final.txt)、[截图](../../var/workbench-usability/browser/evidence-context-final.jpg) |
| 证据反向进入标准的精确版本 | [精确标准跳转](../../var/workbench-usability/browser/evidence-to-exact-criterion.txt) |
| 关联范围、标准版本数与独立候选数 | [最终作用范围](../../var/workbench-usability/browser/evidence-scope-final.txt) |
| CSV 行结构化呈现与显式解读 | [证据卡与解读](../../var/workbench-usability/browser/csv-readable-evidence-and-brief.txt)、[截图](../../var/workbench-usability/browser/csv-readable-evidence-and-brief.jpg) |
| 上传来源的证据详情 | [最终详情](../../var/workbench-usability/browser/csv-evidence-detail-final.txt)、[截图](../../var/workbench-usability/browser/csv-evidence-detail-final.jpg) |
| CSV 下载响应与修复后实际点击 | [单响应头核对](../../var/workbench-usability/csv-download-headers.json)、[实际点击后页面记录](../../var/workbench-usability/browser/carrier-export-after-fix.txt) |

完整候选导出 [carrier-candidates.csv](../../var/workbench-usability/carrier-candidates.csv)已交付并核对 3 行。浏览器按钮已实际点击，Windows Downloads 中的原生落盘文件没有独立观察，因此该项准确结论为“真实点击 + HTTP 完整导出文件核对”。

独立 audit 同时确认原 Surufatinib Snapshot2 的主库 payload 与既有 `snapshot.json` 完全相等，`candidates.csv`、`surufatinib.json`、`snapshot.json` 的 SHA256 与原导出 manifest 一致。原结果保持 qualified rank 4/10、score 0.6629629629629631、hard 1/1、required direct 5/5、直接偏好覆盖 11/21；本轮易用性改动没有重新评估或替换这一科研结果。

## 费用与验证边界

| 费用范围 | 已记录估计费用 |
| --- | --- |
| 此前已知累计 | $4.1790768 |
| 全部 annotation，15 个完成请求；含两版原研究解读与一条载体解读 | $0.0826809 |
| 通用 CSV 工作流累计，含恢复 | $0.0296355 |
| 本轮新增已知小计 | **$0.1123164** |
| Session 已知累计合计 | **$4.2913932** |

annotation $0.0826809 已包含两版原研究解读的 $0.0804957，未再重复累加；新增单条载体解读为 $0.0021852。上述金额是已记录估计费用；此前遗留 orphan 请求的未知费用继续保持 unknown，不能以此表宣称完整账单已闭合。

本轮前端通过 TypeScript `tsc --noEmit`、最终 Vite 构建、样式解析和少量受影响的实际保存记录渲染检查；后端证据/读模型最终 31 项定向测试通过，上传 API 8 个真实输入检查以及 normalizer/reevaluation 10 项相关检查已完成。真实 GUI、HTTP/读投影检查、离线检查按证据分别陈述；本次文档收尾只读取既有结果，没有新增模型调用或重测。

## 最后交付状态

- 通用 CSV 任务的真实 GUI 完整流程、独立来源/数值/模式复核均已完成，合成数据身份明确。
- 证据关联、精确标准版本、保存原文上下文、双语、窄屏及 CSV 证据卡均有最终浏览器证据。
- 后端与最终前端分别归档，新版已部署 8769；8770 跳转与正式页面已实际浏览器验证，8765 未触碰。
- Settings 已恢复未来新任务的 Medium / Medium、并发 4、费用上限 $10。原研究快照、导出、旧失败及未知费用完整保留。

本轮交付已完成。保留的验证边界为：上传实测采用 Paste CSV；未独立观察浏览器原生 Downloads 落盘；full/staged 一致性采用离线复核；旧 orphan 费用仍未知。
