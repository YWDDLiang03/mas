# 组件实操教程：读懂、修改和验证一次研究

[English](../component-walkthrough.md) · [Agent 一键运行](../agent-run.md) · [组件参考](../components/README.md) · [浏览器教程](tutorial.md)

这份教程沿着一条已保存研究，说明各组件怎样接收输入、产生输出和留下来源记录，再介绍下一次实验的修改位置。建议先运行只读示例：它们使用 Python 标准库读取已发布文件，不请求模型、网络，也不打开研究数据库。组件参考解释完整契约，本页展示这些契约在实际研究中怎样衔接。

## 先选择你要完成的操作

| 操作 | 输入与执行内容 | 结果含义 |
|---|---|---|
| 查看发布文件 | 读取 `examples/oral-multitarget/latest` 中的 JSON/CSV | 理解历史结果及来源；不开展新筛选。 |
| 恢复并回放 | 将可移植记录恢复到独立工作区，调用生产资格判断、偏好评分和快照生成器 | 检查当前引擎能否从固定评估重建保存的榜单；标准与观测固定。 |
| 在固定证据上重新生成 | 新建任务，从空标准池和注册表出发，复用 164 个来源中的 3,157 条事实及 68,886 条历史工具结果 | 新的模型实验，重新生成、审查、评估和排序，再与历史结果比较。 |
| 修改输入后开展研究 | 使用新工作区/任务，配置自己的目标、数据、来源、工具和模型 | 新实验，需要独立保存输入、费用和结论。 |

可直接执行的恢复、回放和新运行命令见 [Agent 运行指南](../agent-run.md)。共同实现位于 [`reproduction.py`](../../src/mas/core/reproduction.py)：`import_bundle()` 恢复选定记录，`verify_replay()` 调用实际生产引擎，`prepare_live()` 准备用于独立生成的纯证据来源。可移植包保存的是声明了排除项的公开记录选择。[清单](../../examples/oral-multitarget/latest/reproduction/manifest.json)记录哈希、依赖、排除的全文/模型轨迹和不可用历史引用；较大的包文件未在本地时，按其中分发说明获取。

固定回放目标是任务 `task_01M52CBE5GYPK9F0MCZYBMPH84`、运行 `run_01M52Q4VRB00T5Z3QJW08SSV96`、快照 `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`、`rules@v2`。本次研究包含 3,177 个候选、18 条独立启用决策规则和 13 条参考观察项。六项准入要求由一项口服条件和五项必需靶点观测组成；五项靶点标准同时属于 17 项计分标准，因此 `6＋17−5＝18`。当前分组为 **10 个符合准入要求、1,305 个准入证据不完整、1,862 个已排除**。Surufatinib 排名第一，分数 `0.7592592592592593`，直接偏好覆盖率 `10/17`。冻结来源保留 `qualified: 10`、`pending: 3167`、`rejected: 0`，当前显示见[分类映射](../reference/system-alignment.md#classification-version)。新模型实验记录自己的实际输出。

<a id="read-records"></a>
## 1. 基础记录：先确定正在阅读哪个版本

**输入 → 输出：**任务与运行 ID 指向不可变版本和产物，导出文件提供其可读视图。先打开 [task.json](../../examples/oral-multitarget/latest/results/task.json)、[run-bindings.json](../../examples/oral-multitarget/latest/results/run-bindings.json)、[snapshot.json](../../examples/oral-multitarget/latest/results/snapshot.json) 和 [source-facts.json](../../examples/oral-multitarget/latest/source-facts.json)。

在仓库根目录执行以下 PowerShell 块，只读取发布文件：

```powershell
@'
import csv, json
from collections import Counter
from pathlib import Path
root = Path("examples/oral-multitarget/latest")
task = json.loads((root / "results/task.json").read_text(encoding="utf-8"))
bindings = json.loads((root / "results/run-bindings.json").read_text(encoding="utf-8"))
rows = list(csv.DictReader((root / "results/candidates.csv").open(
    encoding="utf-8-sig", newline="")))
print(task["task_context_id"], task["version"])
print("Candidates:", len(rows), dict(Counter(row["qualification"] for row in rows)))
print("Pinned tool facts:", bindings["run_01M52Q4VRB00T5Z3QJW08SSV96"]
      ["tool_replay"]["cache_entries"])
'@ | python -
```

预期输出：任务版本 `3`；`3177`、`{'qualified': 10, 'pending': 3167}`；`68886`。JSON 键顺序不定义科学身份。[`canonical.py`](../../src/mas/core/canonical.py)、[`ArtifactStore`](../../src/mas/core/artifacts.py) 和 [`Journal`](../../src/mas/core/journal.py)负责内容哈希与事件沿革。导出清单的文件 SHA-256 与产物 ID 分别对应原始文件字节和规范化产物封装。

**继续前核对：**所选任务、运行、快照互相匹配。解释 `_2` 时保留 `_1` 的结果及修正历史。详见[基础组件参考](../components/foundation.md)。

<a id="task-and-config"></a>
## 2. 任务与配置：把问题绑定成一次实验

保存的英文目标要求找到一个能同时作用于 CSF1R、VEGFR1/2/3 和 FGFR1 的口服药物。`original_user_input` 保留原始表单字段；`scope_entities` 绑定五个靶点标识符；`constraints[0]` 将口服给药记录为硬条件，来源为 `user_task_normalized`。`seed_candidates` 披露用户提供的参考候选，其名称本身不提供证据。

[`investigation.py`](../../src/mas/core/investigation.py)规范化工作台输入，[`task.record_version()`](../../src/mas/core/task.py)验证并记录版本。[`config.resolve()`](../../src/mas/core/config.py)解析设置及其生效层。筛选运行绑定任务/规则版本、设置、适配器、工具和实现身份。理解旧结果时应读取 `run-bindings.json` 中该次评估的绑定。

**核对：**五个必需靶点身份、口服硬条件、`existing_only`、`staged`、并发数及记录预算符合研究意图。修改目标后创建新任务，见[修改目标](#change-objective)和[任务配置参考](../components/tasks-and-configuration.md)。

<a id="model-and-budget"></a>
## 3. 模型角色与预算：了解谁解释了证据

模型负责规范化任务、阅读、提出/提炼标准、批评和裁决。[`ModelRoster` 与 `call_role()`](../../src/mas/core/models.py)将角色绑定到实际供应商，记录调用，并将修复、重试等实际尝试计入费用。多个角色可以共享同一个模型。

读取 [model-accounting.json](../../examples/oral-multitarget/latest/results/model-accounting.json)、运行绑定和 [workflow.json](../../examples/oral-multitarget/latest/results/workflow.json)。该工作流保存的预算上限为 USD `5.5`，用量为 `4.210147199999997`，状态为 `recorded_estimate`。历史模型身份为 `deepseek-v4-flash`；新配置的供应商属于新运行。可移植包按清单排除了原始模型轨迹，因此其中没有全部历史提示原文。

**核对：**区分模型/供应商身份、角色、实际尝试次数、已知费用与未知费用。固定评估回放不新增模型调用，独立生成按自己的配置产生费用。见[修改模型和预算](#change-model-budget)及[组件参考](../components/models-and-budgets.md)。

<a id="tools-and-replay"></a>
## 4. 工具与供应商：回答一个精确定义的问题

以 FGFR1 为例，证据路线请求指定靶点的活性观测。[`Broker`](../../src/mas/core/broker.py)按能力和问题类型选择已注册工具，检查输入/版本，再返回结果状态和来源。工具输出观测，后续评估器决定如何使用。

最终绑定的 `tool_replay` 包含 68,886 条完成的 `ok`/`empty` 结果。匹配依据包括工具 ID、契约版本、实现版本、问题类型和规范化输入。一个来源运行处于 cancelled 状态，其已成功完成的工具结果固定到终止序号 `92831`；取消状态也被保留。`failed`/`partial` 调用不进入精确事实缓存。PubChem 整行投影另有明确策略。

**核对：**回放命中保留原日期、来源与版本；`existing_only` 下未命中返回 `existing_evidence_unavailable`。新增接入见[修改工具](#change-tool)，结果状态见[工具参考](../components/tools-and-providers.md)。

<a id="evidence-and-reading"></a>
## 5. 证据与阅读：沿着一条 claim 找到原文位置

新标准生成使用来源任务 `task_01M51AQ0JK0MYN47806ZD5XS1B` 中固定的 3,157 条事实、164 个来源。第一条 evidence 阶段记录复用了其中经过该阶段选择的 3,021 条 claim，新增阅读为零、新搜索为零、复制标准为零。这两个计数描述不同范围，应分别保留。

精简的 [source-facts.json](../../examples/oral-multitarget/latest/source-facts.json)提供两条实用追踪路径：

| 路径 | 实际保留记录 | 查看内容 |
|---|---|---|
| 口服给药 | `claim_01M52QZFZHBESVFSHMK8TX8AGV`，来源 DOI `10.1080/07853890.2026.2698360`，位置 `sec2.3.p1` | 保存的原文段落、布尔路线投影、临床上下文及 `rule_documented-oral-administration@v1` 关联。 |
| FGFR1 活性 | `claim_supp_0fc07290141d48a811fe3d11`，来源 DOI `10.1038/s42004-023-01084-0`，位置 `sec2.1.p1` | 保存的 `34 nM`、实测依据、靶点/实验上下文、文档/claim 产物引用及 `span_checked_against_source`。 |

这里解释已有证据记录，未重新获取或认证出版物。FGFR1 记录明确保留了 ATP 浓度、靶点对应蛋白浓度及孵育时间未知。原文定位检查和 `verification_status` 回答不同问题，两者都需保留。

[`reading.py`](../../src/mas/core/reading.py)提取带位置的 claim，[`evidence.py`](../../src/mas/core/evidence.py)处理准入，[`existing_research.py`](../../src/mas/core/existing_research.py)固定事实及来源序号。**核对：**候选/靶点身份、依据、单位、条件、原文/位置和来源版本在投影中仍可追踪。见[修改证据](#change-evidence)和[证据参考](../components/evidence-and-reading.md)。

<a id="criteria-and-review"></a>
## 6. 标准与审查：追踪展开、收敛及批准依据

打开 [stages.json](../../examples/oral-multitarget/latest/results/stages.json)、[cqa.json](../../examples/oral-multitarget/latest/results/cqa.json) 与 [source-cqa-history.json](../../examples/oral-multitarget/latest/results/source-cqa-history.json)。初始标准池和注册表均为零，先记录六条任务要求标准；四个提议维度把活动数量依次展开至 `293 → 504 → 1192 → 1917`。随后三轮 filter/distill/refine/merge 在每轮 merge 结束时收敛至 `147 → 68 → 53`。

最终集合各有不同含义：53 个活动条目、45 个注册条目、18 条独立启用决策规则和 13 条参考观察项。18 条规则承担 6 项准入要求和 17 项计分用途，其中 5 项靶点标准共有。待审条目与注册标准有重叠，不能把这些数字相加成互斥总体，也不能把全部历史条目当作当前规则。

[`derivation.py`](../../src/mas/core/derivation.py)组织生成，[`derivation_stages.py`](../../src/mas/core/derivation_stages.py)实现各阶段，[`pool.py`](../../src/mas/core/pool.py)保存变化和父项，[`criteria.py`](../../src/mas/core/criteria.py)与 [`adjudication.py`](../../src/mas/core/adjudication.py)检查可执行含义和批准依据。分子量示例保留合并父项，以及有来源支持的 `500 Da` 偏好界限；该次准备中的 HIA 预测仍处于 deferred 状态。

**核对：**每个保留量都有定义、路线、单位/依据、决策角色、证据和处置状态。合并需测量同一个量，保留父项与理由。见[修改硬/软条件](#change-hard-soft)与[标准参考](../components/criteria-and-review.md)。

<a id="assessment-and-qualification"></a>
## 7. 评估与资格：把证据转成候选判断

保存的 [Surufatinib 详情](../../examples/oral-multitarget/latest/results/surufatinib.json)记录六项准入要求全部满足：一项口服条件通过、五个必需靶点均有直接观测。口服单元为 `pass`、`value = true`、依据 `derived`，它来自有来源的临床布尔投影。靶点偏好按可用观测排序，没有增添缺乏支持的效力硬阈值。

FGFR1 的最终单元为 `available`、`7.6442605414788725 pChEMBL`、measured 依据，共四条来源 claim。精简 source-facts 文件只列部分支持记录。以下只读示例用生产函数转换其中一条：

```powershell
@'
import json, sys
from pathlib import Path
sys.path.insert(0, "src")  # Or use the installed project environment.
from mas.core.assessor import converted_claim
facts = json.loads(Path("examples/oral-multitarget/latest/source-facts.json")
                   .read_text(encoding="utf-8"))
original = facts["fgfr1_claims"][0]
converted, refusal = converted_claim(original, "pChEMBL")
assert refusal is None
print(original["value"], original["unit"])
print(converted["value"], converted["unit"])
print(converted["unit_conversion"]["value_as_reported"])
'@ | python -
```

预期输出为 `34 nM`、`7.468521082957745 pChEMBL` 和保留的原始值 `34`。单条换算与四条聚合的最终结果不同。`converted_claim()` 返回副本，不修改文件或原 claim。

[`assess_cell()`、`direct_evidence()` 和 `qualification()`](../../src/mas/core/assessor.py)先应用证据策略，再判定资格。条件要求明确失败时进入已排除。必需评估完成后，部分准入要求有依据进入准入证据不完整，所有要求均无依据则进入已排除。执行未完成和工具错误单独显示评估未完成。预测保留其依据类型，不计入准入所需的直接证据。人体口服 F% 单元保留 `unknown_missing`。**核对：**数值、verdict、直接依据与资格相互支持，并区分缺证、冲突、错误和跳过。见[评估参考](../components/assessment-and-qualification.md)。

<a id="ranking-and-explanations"></a>
## 8. 排序与解释：通过资格后再理解分数

[`assessor.preference_scores()`](../../src/mas/core/assessor.py)对合格总体评分，[`leaderboard.build_snapshot()`](../../src/mas/core/leaderboard.py)保存位置、资格、覆盖率及报告计数。配合候选详情读取 [score-details.csv](../../examples/oral-multitarget/latest/score-details.csv) 和 [score-details.json](../../examples/oral-multitarget/latest/score-details.json)，将每个贡献项追溯到评估和 claim。

保存的第一名位于十个合格候选中，直接偏好覆盖为 `10/17`；其余为 **1,305 个准入证据不完整、1,862 个因无准入依据被排除**。这些记录的冻结资格字段保留 `pending`，当前筛选字段给出具体分类与原因。完整遍历描述已记录的评估工作，证据完整程度需另看覆盖指标。可选叙述/符号模型各有来源和验证记录，解释仍须落到原评估。

**核对：**比较分数时使用相同冻结规则集、合格总体、归一化、覆盖下限和并列策略。修改候选库可改变归一化排序，即使某些观测没变。见[排序参考](../components/ranking-and-explanations.md)。

<a id="execution-and-reuse"></a>
## 9. 执行与复用：选择正确的重启边界

[`RunController`](../../src/mas/core/controller.py)执行 identity → assessment → snapshot，[`derivation_run.py`](../../src/mas/core/derivation_run.py)记录标准阶段检查点，工作台 [`WorkflowManager`](../../src/mas/ui/workflows.py)组织各阶段。[workflow.json](../../examples/oral-multitarget/latest/results/workflow.json)展示最终工作流，[overview.json](../../examples/oral-multitarget/latest/results/overview.json)保留两个快照。

Resume 继续未终止运行的已提交工作；continuation 在终止结果之后创建新运行。复用兼容评估需规则/属性引用、路线、评估器和证据/配置策略保持一致。在已有证据上从头生成则只传递选定事实和精确工具结果，初始不继承旧标准、批评、裁决、评估或排名判断。

**核对：**新生成开始前检查 `initial_pool_count = 0`、`initial_registry_count = 0`、`copies_existing_criteria = false` 和固定证据/工具清单。中断后使用保存的检查点。见 [Agent 运行指南](../agent-run.md)与[执行参考](../components/execution-and-reuse.md)。

<a id="evaluation-and-recovery"></a>
## 10. 评测与恢复率：区分要回答的科学问题

[`measurement.py`](../../src/mas/core/measurement.py)记录前瞻比较策略，[`recovery.py`](../../src/mas/core/recovery.py)按曝光及等价判定比较冻结标准集。[原始 CQA 对照](cqa-comparison.md)研究论文终点恢复情况，榜单研究候选资格与顺序，两者统计单位和结论不同。

[validation.json](../../examples/oral-multitarget/latest/results/validation.json)检查已发布导出、工作流与快照的一致性。可移植 [verification.json](../../examples/oral-multitarget/latest/reproduction/verification.json)记录生产引擎回放，应阅读实际状态、差异和源码摘要。即使固定结果回放一致，源码摘要不同仍说明当前实现与历史实现不同。

**核对：**明确本次比较是文件完整性、固定结果回放、独立标准生成、候选排序还是恢复率，分别记录失败和未知状态。B/恢复率是独立实验，新生成不会自动重测它。见[评测参考](../components/evaluation-and-recovery.md)。

<a id="domain-adapter"></a>
## 11. 领域适配器：让问题接上正确的数据

历史任务使用 [`drug/registration.py`](../../src/mas/adapters/drug/registration.py)，适配器为 `drug_prioritization@1`。本地身份、ChEMBL/GtoPdb 活性、计算描述符、文献及可选 ADMET 面板回答不同问题。学习型 ADMET 输出保留 predicted 依据。[`clinical_routes.py`](../../src/mas/adapters/drug/clinical_routes.py)创建口服布尔投影，并保留底层 claim。

载体/通用研究使用 [`UploadedEvidence`](../../src/mas/core/uploaded_evidence.py)绑定上传 ID、性质、单位、条件和行哈希。载体的粒径观测使用其实际领域语义。**核对：**实体类型、主要身份方案、供应商版本、能力和观测依据符合研究。见 [CSV 修改](#change-data)、[工具修改](#change-tool)和[适配器参考](../components/domain-adapters.md)。

<a id="workbench-and-cli"></a>
## 12. 工作台与 CLI：从不同视图查看同一记录

工作台路由 [`workbench_api.py`](../../src/mas/ui/workbench_api.py)与读取投影 [`read_model.py`](../../src/mas/ui/read_model.py)展示任务、阶段、证据和完整候选分页；CSV 导入位于 [`uploads.py`](../../src/mas/ui/uploads.py)。独立 [CLI](../../src/mas/cli/main.py)和 [Agent 运行器](../agent-run.md)使用同一科学核心，工作流入口各有约定。

界面默认英文，可切换中文并保存选择；研究任务、标准、证据、提示和运行记录使用英文，同时保留原输入/原文。集合展示名称与科学清单分别保存。**核对：**界面选中的任务/快照与导出 ID 相同，查看全部分页或 CSV 行数后再判断总体。见[工作台参考](../components/workbench-and-cli.md)。

## 修改下一次实验

修改时使用新的工作区/输出目录和任务身份。已发布 `examples/**` 及恢复的参考任务用于对照。将[配置示例](../../config/examples/)复制到新工作区，保留历史快照和数值。[Agent 运行指南](../agent-run.md)给出准备输入后的执行命令。

<a id="change-objective"></a>
### 修改目标或必需靶点

在新任务表单中替换目标、靶点和条件。下面是**纯合成任务示例**，展示如何写清问题：

```text
Objective: Compare EXAMPLE-A and EXAMPLE-B for a carrier formulation study.
Required observations: particle_size in nm by DLS at 25 C in water.
Hard condition: particle_size <= 150 nm under those conditions.
Preference: higher cell_viability at 24 h, 10 ug/mL, in assay DEMO-CELL.
Evidence: uploaded synthetic demonstration data only.
```

这些数值用于说明输入结构，不是科学阈值建议。真实研究需填写实际上下文和依据。更换靶点后重新判断证据覆盖，固定的口服多靶点证据并不自动覆盖新靶点。

**验证：**规范化后的 `objective_text`、原始输入、实体类型、标识符、性质/单位/条件及硬条件/偏好角色准确；必需补问先得到答案，再执行相关工作。预期产物是新任务/版本/绑定，排名以实际结果为准。

<a id="change-hard-soft"></a>
### 修改硬条件、偏好或阈值

决策要求改变时，优先在生成前修改新任务定义。开发中任务的标准编辑需要新属性/规则版本、新审查和新冻结/评估。[`criteria.revise_for_workbench()`](../../src/mas/core/criteria.py)接收 `changes = {"attribute": {...}, "rule": {...}}`、理由和 actor，清除旧批准依据，返回 `requires_new_freeze = true`。

对一条**已经有效的合成粒径标准**，可编辑规则片段如下：

```json
{
  "rule": {
    "rule_kind": "preference",
    "predicate_form": "ordering",
    "cutoff": null,
    "cutoff_basis": "none_evidence_insufficient",
    "on_missing": "unknown_no_penalty",
    "on_conflict": "unknown_no_penalty",
    "on_inapplicable": "unknown_no_penalty"
  }
}
```

这只是编辑片段，完整操作还需保留测量量、方向和路线，并通过标准编辑器/新任务流程提交科学理由。直接改导出 JSON 不会产生版本和审查。

**验证：**角色、方向、界限支持、审查处置、启用/延后状态、必需锚点和新冻结引用；重新评估受影响单元并查看资格计数。硬淘汰过高可触发诊断；仅为获得预定排名而改条件会改变研究问题。

<a id="change-data"></a>
### 更换候选 CSV 与测量 CSV

选择 **Use own data / 使用自有数据** 和实体类型，先导入候选，再导入观测。以下均为**未经科学评估的合成格式示例**：

```csv
candidate_id,name,description
EXAMPLE-A,Example carrier A,Synthetic tutorial candidate
EXAMPLE-B,Example carrier B,Synthetic tutorial candidate
```

```csv
candidate_id,property,value,unit,basis,conditions,source,summary
EXAMPLE-A,particle_size,120,nm,measured,DLS; water; 25 C,Synthetic tutorial,Demonstration only
EXAMPLE-B,particle_size,170,nm,measured,DLS; water; 25 C,Synthetic tutorial,Demonstration only
EXAMPLE-A,cell_viability,92,%,measured,24 h; 10 ug/mL; DEMO-CELL,Synthetic tutorial,Demonstration only
EXAMPLE-B,cell_viability,85,%,measured,24 h; 10 ug/mL; DEMO-CELL,Synthetic tutorial,Demonstration only
```

在预览中映射列、处理错误后保存。`candidate_id` 是精确文本，测量 ID 必须存在于所选库。数值需要单位，无量纲写 `1`；`basis` 允许 `measured`、`curated`、`predicted`、`simulated`、`derived`，应保留实际依据。缺失观测省略，零和 `false` 有效。修正后产生新的内容寻址数据集。当前每文件限制为 UTF-8、8 MB、50,000 行、64 列。详见 [CSV 指南](csv-input.md)。

**验证：**预览行数、精确 ID、数值/布尔类型、单位/依据/条件、来源、新上传哈希及选定数据版本。换候选总体需重新比较完整榜单/覆盖率；修改观测后需检查相关单元和归一化。

<a id="change-evidence"></a>
### 选择或扩充证据集合

固定证据实验显式选择集合，并保留 `evidence_mode = existing_only`。[`EvidenceCollections`](../../src/mas/ui/evidence_collections.py)中的名称、简介和主题是展示元数据，改名不会改变 claim 或覆盖范围。`manifest_ref`、来源任务、claim/来源数量和截止时间才标识所选科学输入。

新增观测时导入新测量版本，或在新任务中启用已获许可的文献/上传来源与检索。文档上传另有来源清单，记录身份、访问/许可和 LLM 阅读许可，见[配置](../configuration.md)和[证据参考](../components/evidence-and-reading.md)。新增来源属于新的证据实验。可移植包排除全文，保留文档引用并不表示全文字节已恢复。

**验证：**计数依据是 `pinned_fact_manifest` 还是任务已准入证据，来源 ID/版本、截止日期、原文位置/上下文及准入状态正确。`existing_only` 未命中时记录缺口，或提供新的有依据数据；保留先前 pending 结果供比较。

<a id="change-tool"></a>
### 新增或修改工具适配器

当前没有运行时 `tools.toml` 或任意导入开关。实现 `ToolContract` 和 `invoke(question_kind, inputs) -> ProviderResponse`，在组合入口注册，再将能力/问题类型绑定到领域路线。可从[最小供应商示例](../components/tools-and-providers.md#worked-example-a-local-provider)、[`drug/registration.py`](../../src/mas/adapters/drug/registration.py)或 [`UploadedEvidence`](../../src/mas/core/uploaded_evidence.py)开始。

例如接入本地粒径服务，需声明精确候选 ID 和条件输入，返回实际测量及来源/行身份；预测输出保留 predicted。行为改变时递增 `implementation_version`，输出 schema 改变时同步处理契约版本。保留数据版本、获取时间、许可、上游引用及明确的 empty/不可用/错误状态。能力声明和可执行标准路线需要一起更新。

**验证：**一条代表性已知观测、一条缺失观测，以及接入实际引入的故障模式。检查身份映射、单位/依据、来源和 broker 清单，确认旧缓存键不会冒充新实现。复用[药物适配器测试](../../tests/test_drug_adapter.py)或[工具回放测试](../../tests/test_broker_replay.py)，只有新增行为需要时补定向回归。通过后再用小规模真实输入运行。

<a id="change-model-budget"></a>
### 修改模型角色、预算、工作量或并发

将 [models.deepseek.toml](../../config/examples/models.deepseek.toml) 和 [mas.toml](../../config/examples/mas.toml)复制到新工作区。填写实际模型、base URL 和密钥环境变量/文件路径，然后在 `[roles]` 绑定角色。例如 `critic = "your_critic_provider"` 将批评角色交给该已定义供应商；角色名称不同本身不建立模型独立性。付费运行前查阅供应商当前型号和价格文档。

以下 TOML 示例申请一个较小的**新实验**：

```toml
[budget]
usd_max = 2.0
on_exhaust = "finalize_partial"
[assess]
workers = 2
[search]
volume = "mid"
[evaluation]
mode = "staged"
[evidence]
mode = "existing_only"
```

浏览器/Agent 工作流也接收提交的工作量和预算控制，应检查生效配置和新绑定。价格/usage 缺失时费用可能未知，最后一次获准调用可能越过已知预算上限。预算值本身不代表免费，也不保证精确账单。

下面的纯配置检查不打开 store，不调用供应商：

```powershell
@'
import sys
sys.path.insert(0, "src")
from mas.core import config
settings = config.resolve(project_file=None, environ={}, overrides={
    "budget.usd_max": 2.0, "assess.workers": 2})
print(settings.get("budget.usd_max"), settings.sources["budget.usd_max"])
print(settings.get("assess.workers"))
'@ | python -
```

预期输出 `2.0 override`，然后 `2`。完整配置文件使用[配置指南](../configuration.md)中的 `config validate`、`config show --explain` 和 `models show` 检查；供应商连通性与实际行为由另行记录的小规模真实调用验证。

**执行后验证：**新角色/供应商身份、生效设置层、要求从零时的初始 CQA 数量、各阶段新增/合并/删除/理由、终止状态、未解决项、完整候选导出、费用状态和合格总体排序。与固定结果比较时记录实际差异。新模型运行可能改善、变差、延后标准或因预算停止；保留这些结果，再据此选择下一次改动。
