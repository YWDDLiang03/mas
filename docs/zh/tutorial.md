# 实操教程：从研究问题到可回查的结果

[English](../tutorial.md) · [安装说明](installation.md) · [配置说明](../configuration.md) · [发布案例](../../examples/oral-multitarget/README.md)

直接执行请从[智能体一键运行](agent-run.md)开始。了解组件输入、实现位置及具体修改方法，请阅读[组件实操](component-walkthrough.md)。

本教程沿最新已完成的口服多靶点研究，说明研究者怎样操作、各角色做什么、如何回查结论。该次研究形成 **18 条启用决策规则**，Surufatinib 在 **10 个合格候选中排名第 1**，分数为 **0.7592592592592593**。完整导出有 **3,177 个候选**，其中 **1,305 个部分具备准入依据，1,862 个因无准入依据被排除**。

| 你的起点 | 使用方式 |
|---|---|
| 刚克隆仓库，希望查看案例 | 阅读固定导出与截图。第 0 步仅需 Python，不发起模型请求。 |
| 刚克隆仓库，希望恢复并核对案例 | 执行 `python scripts/agent_run.py replay --bootstrap --workspace var/agent-replay --open`，自动下载可选数据包并恢复最新研究及固定事实。 |
| 已恢复案例或已有原工作区 | 查看保存结果，或使用候选库和证据集合新建研究。第 1–11 步说明实际过程与对应操作。 |
| 刚克隆仓库，希望开展自己的研究 | 按安装说明建立空工作区、配置模型，然后按第 12 步导入自己的 CSV。 |

仓库提供固定导出，可选的 [168 MB 数据包](../../examples/oral-multitarget/latest/reproduction/README.md)补齐恢复最新研究及准备新研究所需的记录、事实和缓存。核对已保存结果不需要原私有数据库或 API key。文献全文与模型原始调用记录不在公开数据包中。下文截图于 2026 年 10 月 28 日在当前 Windows 工作台实拍，展示同一个保存案例。[当前界面与核对记录](current-status.md)列出来源版本。重新调用模型时，标准和结果按新的实际运行保存。

## 第 0 步：直接查看发布结果

先打开 [报告](../../examples/oral-multitarget/latest/results/report.md)、[任务](../../examples/oral-multitarget/latest/results/task.json)、[当前全部候选 CSV](../../examples/oral-multitarget/latest/selection/workbench-export.csv) 和 [Surufatinib 详情](../../examples/oral-multitarget/latest/results/surufatinib.json)。无需启动服务即可查看这些文件。

在仓库根目录运行以下 PowerShell 命令，使用 Python 标准库核对已保存结果：

```powershell
python -c "import csv,collections; from pathlib import Path; rows=list(csv.DictReader((Path('examples/oral-multitarget/latest/selection')/'workbench-export.csv').open(encoding='utf-8-sig',newline=''))); print('Exported candidates:',len(rows)); print('Selection:',dict(collections.Counter(r['selection_decision'] for r in rows)))"
python -c "import json; from pathlib import Path; r=json.loads((Path('examples/oral-multitarget/latest/results')/'surufatinib.json').read_text(encoding='utf-8'))['matches'][0]; print('Rank:',r['rank'],'Score:',r['score'],'Direct preference coverage:',r['preference_coverage'])"
```

当前导出共 **3,177 行**：`eligible: 10`、`evidence_incomplete: 1305`、`excluded: 1862`。Surufatinib 排名 `1`，分数 `0.7592592592592593`，直接覆盖 `0.5882352941176471`。以上命令读取已发布文件。

`selection_decision` 对应当前界面的分组，导出同时保留旧 `qualification` 字段以便追溯保存快照。[统一定义](decision-language.md)说明当前分组及具体原因。

## 第 1 步：在 Settings 中确定运行资源

完成[安装与模型配置](installation.md)后启动工作区：

```powershell
.\start_workbench.cmd -Store var\workspace\store -InitializeStore -Models var\workspace\store\models.toml -Config var\workspace\store\mas.toml -AllowOperations
```

该命令假定已按安装文档复制并配置模型与设置文件。打开[工作台](http://127.0.0.1:8769/workbench/)，进入 **Settings / 设置**。已有工作区应替换为其实际库和配置路径。

将两个工作量控件均设为 **Medium / 适中**（`mid`），并发上限设为 **4**，预算设为 **10 美元**，点击 **Save settings / 保存设置**。当前标签为 **Literature workload / 文献阅读量** 和 **Textbook workload / 教材阅读量**。修改用于后续工作，已有结果保留原配置。

| 设置 | 最新保存研究 | 新任务示例或默认值 |
|---|---:|---:|
| 工作量 | `mid` | `mid` |
| 并发评估候选数 | 4 | 4 |
| 费用上限 | **5.50 美元** | **10.00 美元** |
| 证据方式 | 仅使用保存证据 | 按实际输入选择已有、上传或明确检索 |
| 评估方式 | 分阶段筛选 | 分阶段筛选 |

使用同一本地输入重复历史资源条件时可设置 5.50；新研究按自己的资源条件选择。保存研究记录的模型费用为 **估计 4.2101472 美元**，并非供应商最终账单。历史模型身份为 `deepseek-v4-flash`，为新任务配置模型不会修改这一身份。

![当前设置与保存研究的进度](../assets/current/settings.jpg)

画面同时显示后续研究的设置与已完成案例的进度记录。English / 中文切换界面显示，科研记录与来源原文保留其记录语言。

## 第 2 步：新建任务，准确描述决策目标

选择 **New research / 新建研究**，比较对象选 **Drugs & small molecules / 药物与小分子**。沿本案例操作时，研究目标原文为：

```text
Identify a single orally administered agent that concurrently engages the tumour-microenvironment targets CSF1R, VEGFR1, VEGFR2, VEGFR3 and FGFR1, with a pharmacological profile suitable for clinical development. Use the saved evidence to develop and refine meaningful research criteria, then screen and rank the recorded compound library.
```

在 **Targets or desired properties / 靶点或目标性质** 中每行填写一个：

```text
CSF1R
VEGFR1
VEGFR2
VEGFR3
FGFR1
```

在 **Constraints / 研究约束** 中填写：

```text
Oral administration is required.
```

为研究填写清楚的名称。展开 **Evaluation options / 评估选项**，选择 **Use saved or uploaded evidence / 使用已有或上传的证据**、**Staged screening / 分阶段筛选**。选中恢复的案例后，也可从 **研究选项 → 按此设置新建研究** 打开可编辑表单；提交后从空标准集开始。

研究者提出目标与约束；任务规范化角色将其转为带靶点身份和口服条件的英文版本记录。研究者无需预先写出最终评估标准。若必要要求无法对应到性质、单位或条件，按工作流出现的针对性补问完善输入。

![研究目标、五靶点与口服条件](../assets/current/new-study.jpg)

截图展示提交前的新研究表单，背景为已保存的研究。

## 第 3 步：分别绑定候选范围和固定证据

在 **Candidates & evidence / 候选与证据** 中选择 **3,177 个化合物**的记录库，历史工作区中的库 ID 为 `universe_chembl.json`。再选择包含 **3,157 条保留事实、164 个来源**的证据集合，显示截止日期为 **2026 年 10 月 15 日**。集合选择器显示名称、来源数、记录数和截止时间；名称与简介可在显示设置中编辑。

![候选库与固定证据集合](../assets/current/evidence-selection.jpg)

候选库限定比较谁，集合限定哪些保存材料用于标准生成。集合名称和简介仅为显示信息。以上数量属于固定输入清单，不是候选评估所用全部历史工具观测的数量。

新研究从空标准集开始，使用 **3,021 条证据记录**形成提议。原集合包含 3,157 条记录，其中 136 条提到候选名称的记录未进入本次生成子集。候选评估采用固定后的评价框架及其绑定来源。

执行 `replay` 或 `plan` 后，恢复的工作台会提供准备好的证据集合和候选库。在 **研究选项 → 按此设置新建研究** 中，新的任务绑定这份只含事实、评估标准为空的集合。原研究仍保存原来源身份。空工作区要先提供输入才会出现可选集合；自己的数据按第 12 步上传。

## 第 4 步：启动一次，按正确层级观察进度

核对范围、证据方式与上限后点击 **Start research / 开始研究**，系统执行配置的工作流并可能产生付费模型请求。**Save draft / 保存草稿**只保存输入。

控制器依次协调理解任务、准备证据、提出标准、审查提炼、处理决策、固定方案、候选评估和发布。已有证据模式复用绑定事实，不代表又做了一轮文献检索或全文阅读。

**Proposer / 提议者**提出有证据支持的标准；**Critic / 审查者**质疑相关性、定义、阈值和反证；提议者作出修订，**Adjudicator / 裁决者**按记录政策处理合并与争议。控制器管理阶段切换和结束，工具提供评估需要的记录观测。角色分工本身不代表使用了独立模型供应商。

展开 **Workflow & run details / 工作流与运行详情**，查看阶段、最近活动、耗时和费用估计。运行中的批次计数对应当前阶段。下图的保存案例已完成 **8/8 个阶段**，同时展示该次记录的耗时与费用。

![已完成案例在当前界面的阶段进度](../assets/current/progress.jpg)

## 第 5 步：跟踪展开和三轮提炼

进入 **Criteria / 标准**及阶段、历史视图。本次工作项数量为：

```text
0 → 6 项任务要求 → 293 → 504 → 1,192 → 1,917
  → 第一轮后 147 → 第二轮后 68 → 第三轮后 53
```

六项要求是五靶点效力和已记录口服给药。随后按靶点覆盖、口服性质、代谢稳定性、安全性四个维度展开。计数包含已注册标准与未注册工作提案，不直接表示最终评分规则数。

| 阶段 | 角色做什么 | 阶段结束数量 |
|---|---|---:|
| 绑定任务要求 | 保留五靶点与口服条件 | 6 |
| 提议靶点覆盖 | 展开靶点相关量 | 293 |
| 提议口服性质 | 展开吸收与暴露相关量 | 504 |
| 提议代谢稳定性 | 展开处置与相互作用相关量 | 1,192 |
| 提议安全性 | 展开安全性相关量 | 1,917 |
| 第一轮：filter → distill → refine → merge | 查支持、明确量、回应质疑、合并重复 | 1,373 → 1,337 → 291 → 147 |
| 第二轮，同样顺序 | 修订支持并继续收敛 | 109 → 97 → 78 → 68 |
| 第三轮，同样顺序 | 处理剩余定义与重复 | 63 → 62 → 53 → 53 |

阅读每次变更的理由与父项。合并保留输入，移除说明退出原因。[阶段记录](../../examples/oral-multitarget/latest/results/stages.json)与[标准历史](../../examples/oral-multitarget/latest/results/source-cqa-history.json)保留真实转换。

![当前标准及不同角色](../assets/current/criteria.jpg)

## 第 6 步：打开分子量，查看形成沿革

在标准页搜索 **Molecular weight (Da)**，打开 **Lineage / 形成沿革**、版本历史、规则和关联证据。第二轮把六项提议合为一项，因为它们通过同一结构描述符路径测量分子量，并具有相同偏好方向；Da 与 g/mol 在这里描述对应的分子质量数值尺度。合并项保留六个父项和中位数汇总方式。

第三轮审查质疑反证支持。提议者补充 Lipinski 与小分子激酶抑制剂讨论，明确记录把 **500 Da 经验边界**作为偏好线的解释。工作沿革为 `cri_01M52KSFQBB9B84Y16HNPGBCM2@v1 → @v2 → @v3`，随后注册为 `attr_molecular-weight-da@v1` 和 `rule_molecular-weight-da@v1`。

最终规则是**分子量 ≤ 500 Da 的阈值偏好**。满足时获得该项比较分，超过影响这一偏好而不独立硬淘汰。两项都低于 500 Da 时，该阈值不会进一步区分它们。Surufatinib 的记录值是 **480.6 Da**，依据为明确推导。

这个过程把六项提议、合并、质疑、修订和可执行规则连起来；只看最终名称无法看到这些判断。

## 第 7 步：固定方案，查看准入、计分与参考用途

评估前的 **Save evaluation rules / 保存评估规则**固定版本、可接受证据路径、范围和比较政策。最终保存评估采用 **`rules@v2`**。

| 最终工作项 | 条数 | 用途 |
|---|---:|---|
| 条件要求 | 1 | 必须具备口服给药记录 |
| 必需靶点证据＋计分 | 5 | 各靶点必须有可用直接观测，效力值同时参与排序 |
| 其他加权排序标准 | 12 | 参与排序 |
| 参考观察项 | 13 | 辅助理解结果 |
| 已注册但延后 | 14 | 未解决或不可执行的规则暂不评估 |
| 未注册待定提案 | 8 | 保留在注册评估集外的工作项 |

因此 **53 = 18 条启用决策规则 + 13 条参考观察项 + 22 条未纳入本次评估的条目**，而进入评估的 **31 = 18 + 13**。五条未解决复核是延后项的子集，不能再加五条。未解决的 logP 区间提案与启用的连续 RDKit logP 偏好是不同规则。

**六项准入要求全部必须满足**：一项口服条件，以及五个靶点各自的直接观测要求。五项靶点标准也属于 **17 项计分标准**，因此 **6＋17−5＝18 条独立决策规则**。靶点效力值用于排序，保存的准入判断要求直接证据可用，并未设置共同效力截点。预测保留其依据类型，单列于直接证据覆盖之外。

## 第 8 步：评估候选并查看准入依据

进入 **Candidates / 候选**。分阶段模式先查硬条件，硬失败后记录后续跳过。本次**没有明确硬失败**，**前序失败后跳过为 0**；共有 **98,487 个记录单元 = 3,177 × 31**，其中包含未知。全库处理完成不表示每格都有证据。

对 Surufatinib 打开 **Evidence / 证据**，检查资格：口服 **1/1 通过**，必需靶点 **5/5 有直接观测**，最终直接偏好覆盖 **10/17 = 58.82%**。

当前选中快照为 `_2`（`rules@v2`），直接覆盖 **10/17**，排名门槛为保存方案中的 **50%**。[保存概览](../../examples/oral-multitarget/latest/results/overview.json)保留早期评估及其关联，供追溯研究过程。

## 第 9 步：看榜单并展开分数

合格组有 **10 项**，Surufatinib **第 1**，随后为 Pazopanib、Axitinib。其余候选中，**1,305 个部分具备准入依据，1,862 个因无准入依据被排除**。已确认条件失败为 0，评估未完成为 0。原始导出保留历史 pending 字段，当前界面按[统一定义](decision-language.md)解释。

![合格候选榜](../assets/current/candidates.jpg)

点击 Surufatinib 的 **Score / 分数**，查看逐项数值、依据、比较分、权重和贡献：

```text
17 项适用偏好；15 项有值；每项权重 1
比较分合计 11.38888888888889 ÷ 有值权重合计 15
= 0.7592592592592593
```

15 项由五项靶点偏好、五项结构计算、五项预测组成。人体实测口服 F% 和 Tmax 仍缺失。缺值项不进入分数平均，但保留在适用覆盖分母，因此**分数分母是 15，覆盖分母是 17**。允许使用的预测可贡献分数，直接覆盖的分子贡献仍为零。

连续偏好比较合格且有值的候选，较好数值获较高分，并列取平均位置：

```text
d = [W + (E - 1)/2] / (N - 1)
```

N 是有值候选数，W 是较差数值个数，E 是包含当前候选的并列个数。BRENK 的 N=10、W=2、E=8，比较分 **0.611111**，总分贡献为 `0.611111/15`。阈值偏好满足记 1、不满足记 0。展开 **Calculation & evidence / 计算与证据**核对该行方法。

![评分明细与直接证据覆盖](../assets/current/score-details.jpg)

## 第 10 步：从 FGFR1 分数回到原始观测

在 FGFR1 评分行点击 **Open the evidence for this preference / 查看此项偏好的证据**，或在候选证据中选择 **FGFR1 curated potency**。展开来源组、具体发现与原文上下文。

一篇关联论文在 `sec2.1.p1` 报告 **FGFR1 IC50 = 34 nM**：*Structural basis and selectivity of sulfatinib binding to FGFR and CSF-1R*，DOI `10.1038/s42004-023-01084-0`。记录保留 ADP-Glo 激酶抑制与 FGFR1 激酶结构域等条件，也保留 ATP 浓度等未知项。

| 原始记录 | 用于汇总的 pChEMBL 数值 |
|---|---:|
| 文献 IC50 34 nM | `-log10(34 × 10^-9)` = 7.46852108296 |
| GtoPdb interaction 9769 | 7.28000020981 |
| ChEMBL activity 26132415 | 7.82 |
| ChEMBL activity 26187720 | 7.82 |

四值排序取中位数：`(7.46852108296 + 7.82)/2 ≈ 7.64426054148`，即保存评估值。单条 34 nM 与四记录汇总处于不同解释层级。四条记录本身不代表四次独立实验；判断是否适合合并时，应继续核对底层来源及条件。

![FGFR1 关联证据](../assets/current/evidence-fgfr1.jpg)

没有本地工作台时，可从 [surufatinib.json](../../examples/oral-multitarget/latest/results/surufatinib.json)中的评估、来源 ID 和位置引用进行核对。

## 第 11 步：导出全部候选，保留研究身份

点击 **Export all candidates / 导出全部候选**。导出范围是完整候选库，不只是当前页或合格十项。核对 **3,177 行 CSV**，使用表格时保留快照引用。第 0 步可检查发布包内的实际导出。

将[文件清单](../../examples/oral-multitarget/latest/results/manifest.json)、[验证结果](../../examples/oral-multitarget/latest/results/validation.json)、[工作流](../../examples/oral-multitarget/latest/results/workflow.json)、[标准](../../examples/oral-multitarget/latest/results/cqa.json)和[标准历史](../../examples/oral-multitarget/latest/results/source-cqa-history.json)一并保留。比较后续修改时继续保存缺证、冲突与早期结果。

最终固定身份为任务 `task_01M52CBE5GYPK9F0MCZYBMPH84`、快照 `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`、运行 `run_01M52Q4VRB00T5Z3QJW08SSV96`。

[标准比较指南](cqa-comparison.md)使用独立的合成基线，说明怎样比较量、条件和决策用途。

## 第 12 步：使用自己的 CSV 开始研究

空工作区选择 **Use own data / 使用自己的数据**，再选药物与小分子、载体与制剂或其他候选。将[候选模板](../../config/examples/candidates.csv)和[测量模板](../../config/examples/measurements.csv)填入真实数据；发布模板只有表头。

1. 导入或粘贴**候选 CSV**，映射并校验列。`candidate_id` 必须唯一，点击 **Use this candidate library / 使用此候选库**保存。
2. 保持该库选中，再导入**测量 CSV**。每行需要 `candidate_id`、`property`、`value`、`basis`；数字观测还须单位。ID 精确匹配，前导零有意义。
3. 根据真实观测声明 `measured`、`curated`、`predicted`、`simulated` 或 `derived`，补充实验条件与来源。不同条件保持不同观测。缺失观测省略；实测零和 `false` 是有效值。
4. 修复映射或校验问题，点击 **Use these measurements / 使用这些测量**。保存数据不会启动研究；修改数据产生新的不可变数据集身份。
5. 写出目标、必需观测、硬条件、偏好及单位、条件。仅在工作区实际存在时选择补充已有证据。
6. 检查 Settings、证据/评估方式与费用上限，点击 **Start research / 开始研究**。按上述标准、资格、分数与来源路径，阅读自己的实际记录。

![CSV 映射与校验](../assets/current/csv-import.jpg)

截图使用两条明确标注的合成载体记录说明文件格式。本轮只检查预览，没有导入这些记录或启动研究。

通用上传流程按输入行的精确性质和条件评估；专用药物库流程使用声明的药物工具能力与证据路径。自己的数据形成新研究，数量、费用和结论均按实际记录报告。新的语言模型运行不保证产生本教程的 1,917 个提议、53 个工作项或相同排名。
