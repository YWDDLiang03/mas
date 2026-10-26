# TRIAGE terminology

[Decision definitions / 判定定义](decision-language.md) · [中文说明](../zh/decision-language.md) · [CSV catalog](terminology.csv) · [Alignment plan](system-alignment.md)

TRIAGE is a multi-agent workbench for evidence-driven candidate evaluation and prioritization in medical research. It supports configurable objectives, candidate types, source evidence and comparison rules. The complete retained example concerns therapeutic drug prioritization; general data handling does not establish validation for every medical task. MAS remains the repository and Python package name.

## Page titles

| Surface | English | 中文 |
|---|---|---|
| Browser title | TRIAGE · Medical research workbench | TRIAGE 医学研究工作台 |
| Overview | Study overview | 研究概览 |
| Criteria | Evaluation criteria | 评估标准 |
| Candidates | Eligibility and prioritization | 资格评估与优先排序 |
| Evidence | Evidence and sources | 证据与来源 |
| Settings | Research settings | 研究设置 |
| New study | Define a research study | 定义研究任务 |

## Vocabulary catalog

English is the display default. Chinese translates interface labels; research objectives, recorded criterion names and source text retain their original content. Legacy internal IDs and frozen fields remain compatible.

| Concept | Preferred English | 中文界面 | Meaning / usage |
|---|---|---|---|
| 系统 | Medical research workbench | 医学研究工作台 | 工作流与记录工具的总称 |
| 架构 | Multi-agent system / multi-agent workbench | 多智能体系统／多智能体工作台 | 描述角色组织；独立性另报 |
| 论文工作流 | Therapeutic prioritization workflow | 治疗候选优先排序流程 | 本例针对治疗药物候选 |
| 研究目标 | Research objective | 研究目标 | 研究者提出的问题与成功条件 |
| 研究任务 | Research task | 研究任务 | 含目标、范围、对象和约束的版本记录 |
| 一次执行 | Investigation / research run | 研究流程／本次运行 | Investigation 指整条研究流程；run 指一次绑定输入与设置的执行 |
| 任务约束 | Task constraint | 任务约束 | 来自任务授权的条件，不包装为文献独立发现 |
| 候选 | Candidate | 候选 | 通用对象；与 criterion proposal 区分 |
| 候选药物 | Drug candidate / candidate agent | 候选药物 | 这里可含已有批准药物的新用途，不暗示新分子实体 |
| 候选总体 | Candidate population | 候选总体 | 本次实际比较的完整集合 |
| 候选库 | Candidate library | 候选库 | 数据来源与版本；不自动代表完整药物空间 |
| 参考候选 | Disclosed reference candidate | 已披露参考候选 | 已知身份和既有结果的程度需交代 |
| 来源 | Source | 来源 | 文献、数据库、上传数据等来源实体 |
| 文献 | Literature / source document | 文献／来源文档 | 数据库记录不能统称文献；摘要与全文应区别 |
| 证据记录 | Evidence record / source-linked claim | 证据记录／关联来源的证据条目 | 可追溯的提取或记录；admitted 不等于科学真值已获验证 |
| 已纳入证据 | Admitted evidence | 已纳入证据 | 通过当前纳入与来源检查，可供后续判断 |
| 证据集合 | Evidence collection | 证据集合 | 固定来源与版本，避免暗示全面系统综述 |
| 证据快照 | Evidence snapshot | 证据快照 | 不可变的本次证据绑定 |
| 直接证据 | Direct evidence | 直接证据 | 按本次政策接受的观测、整理测量或允许的确定性计算；界面提供定义 |
| 整理测量 | Curated measurement | 数据库整理的测量值 | 标明实验条件与原始来源，不把数据库整理当作新实验 |
| 确定性计算 | Deterministic calculation / structure-derived descriptor | 确定性计算／结构计算描述符 | 分子量、RDKit logP 和结构警报计数等；与训练模型预测分开 |
| 模型预测 | Model prediction | 模型预测 | 必须标明预测端点，不能泛称实验结果 |
| 证据依据 | Evidence basis | 取值依据 | 回答值从测量、整理、计算还是预测得到 |
| 缺少直接证据 | Missing required direct evidence | 缺少必需直接证据 | 证据状态；不改写为性质测量失败 |
| 证据冲突 | Conflicting evidence | 证据冲突 | 与无数据、解释未决分开 |
| 未评估 | Not assessed | 未评估 | 与已评估但缺证分开 |
| 评估标准 | Evaluation criterion | 评估标准 | 通用主术语，建议替代界面的 CQA |
| 待议标准 | Criterion proposal | 标准提议 | 避免中文“候选”同时指药物和待议标准 |
| 标准池 | Criterion pool | 标准池 | 包含待议、修改、合并与未启用项 |
| 属性 | Attribute | 评估属性 | 定义测什么、单位、适用条件、证据及聚合 |
| 规则 | Decision rule | 决策规则 | 定义该属性怎样影响准入或排序 |
| 准入要求 | Eligibility requirement | 准入要求 | 包含条件要求与证据要求，全部必须满足；与计分用途独立。 |
| 条件要求 | Condition requirement | 条件要求 | 必须满足的数值、范围或类别。 |
| 证据要求 | Evidence requirement | 证据要求 | 准入时必须具备的可用直接观测；同一标准可同时用于评分。 |
| 加权排序标准 | Weighted prioritization criterion | 加权排序标准 | 合格候选之间的比较项 |
| 上下文观察 | Contextual observation | 参考观察项 | 辅助理解，不加准入或排序权重 |
| 未启用项 | Not used in this evaluation | 未纳入本次评估 | 必须给具体未启用理由；不等于已证伪 |
| 规则集 | Frozen evaluation framework | 已固定评估框架 | 冻结可执行版本，不暗示专家共识或临床验证 |
| 提出角色 | Criterion proposer | 标准提出智能体 | 提出可执行标准 |
| 批评角色 | Criterion critic | 标准审查智能体 | 指出缺陷和争议；不同于人类医学审稿人 |
| 裁决角色 | Adjudicator agent | 裁决智能体 | 记录机器裁决权限；不用 expert panel 或 clinical approval |
| 检索角色 | Literature retriever | 文献检索智能体 | 查询与来源覆盖 |
| 阅读角色 | Evidence reader / extractor | 证据阅读／提取智能体 | 提取可定位的条目 |
| 归纳角色 | Evidence summarizer | 证据归纳智能体 | 来源支持的归纳 |
| 评分 | Prioritization score | 优先排序得分 | 本框架内的比较量，不是临床疗效概率 |
| 得分明细 | Score contribution | 得分贡献 | 值、方向、权重与归一化贡献 |
| 排序 | Candidate ranking | 候选排序 | 依赖同一总体、框架、权重与政策 |
| 排名 | Rank | 名次 | 条件性相对位置 |
| 直接覆盖 | Direct-evidence coverage | 直接证据覆盖率 | 已由直接证据支持的适用排序权重之和／全部适用排序权重之和 |
| 必需证据覆盖 | Required-observation coverage | 必需观测覆盖率 | 准入所需观测分母；与 17 项排序分母分开 |
| 覆盖门槛 | Minimum direct-evidence coverage for ranking | 排名所需最低直接证据覆盖率 | 满足资格后，是否可赋予名次的单独条件 |
| 结果快照 | Result snapshot / ranking snapshot | 结果快照／排序快照 | 固定某次结果；不笼统称治疗建议 |
| 原始推荐状态 | Recommended (historical workflow state) | 已进入结果（历史状态） | 详情保留原始字段；主表优先展示资格与名次，不译成“临床推荐” |
| 原始暂定状态 | Provisional / review authority | 暂定／审查权限状态 | 与证据资格、分数、名次分别展示；不是尚未完成的临床评估 |
| 评分解释 | Score breakdown | 得分分解 | 解释计算过程 |
| 机制解释 | Literature-supported mechanistic interpretation | 文献支持的机制解读 | 来源支持的说明，与因果机制证实分开 |
| 提名结果 | Prioritized candidate / candidate for further evaluation | 优先候选／供进一步验证的候选 | 不译成最佳治疗或临床推荐 |
| 无名次 | Not ranked | 未排名 | 可能有分数但覆盖不足；原因必须可见 |
| 无可用推荐 | No rankable candidate / no recommendation | 无可排名候选／未形成推荐 | 保留失败原因 |
| 平台品牌 | TRIAGE | TRIAGE | MAS保留为代码库与包名；界面展示医学研究工作台。 |
| 候选准入 | Eligible | 具备资格 | 适用条件要求满足，必需直接观测齐全。 |
| 中间态 | Evidence incomplete | 准入证据不完整 | 部分任务要求有可用依据，其余尚有缺口，且没有条件要求失败。 |
| 部分支持 | Evidence incomplete | 准入证据不完整 | 一部分准入依据已建立，其余未建立；不称部分合格。 |
| 零项支持 | No admission support | 无准入依据 | 必需评估完成后，所有准入要求均无可用支持；候选被排除。 |
| 候选排除 | Excluded | 已排除 | 条件要求失败，或必需评估完成后无准入依据。 |
| 执行状态 | Assessment incomplete | 评估未完成 | 必需评估未完成、工具失败或记录不可用；不作为性质失败。 |
| 框架状态 | Criteria not ready | 条件未就绪 | 缺少有效规则、绑定或准备证明；与候选性质无关。 |
| 偏好谓词结果 | Scoring threshold met / not met | 满足／未满足计分阈值 | 只说明该排序项的比较结果，不直接排除候选。 |

## Terms that require an explicit scope

- **CQA** is a legacy project label, not the general name for every evaluation criterion. In ICH Q8(R2), Critical Quality Attributes concern properties controlled to ensure pharmaceutical product quality. We use **evaluation criteria** for the general workflow. This is an editorial choice to avoid a domain collision, not a claim that the abbreviation is prohibited. [ICH Q8(R2), section 2.2](https://database.ich.org/sites/default/files/Q8_R2_Guideline.pdf)
- **Direct-evidence coverage** retains the paper's wording. Accepted bases and the measured/curated/derived/predicted breakdown must accompany it. It is not synonymous with experimental or clinical measurement coverage.
- **Available target observation** concerns evidence availability. **Target engagement**, **effective inhibition** and **clinical response** require their own evidence and must not be inferred from an eligibility label.
- **Frozen** means a fixed evaluation version. **Agent reviewed** and **human reviewed** describe different sources of judgment. Neither freezing nor a machine decision implies clinical validation.
- **Prioritized candidate** means a research ranking result under the saved framework. The historical internal value `recommended` is not a clinical recommendation.
- **Candidate**, **criterion proposal**, **source**, **evidence record**, **assessment** and **result snapshot** are different objects; their counts are not interchangeable.

## Stable counting names

Use **working items** for the expanding and refining pool; **enabled decision rules** for the unique criteria used in admission or prioritization; **assessed items** when contextual observations are also included. A condition-met count, required-observation count, available-score denominator and direct-evidence coverage denominator each name their own scope.

The oral example has 53 retained working items, 18 enabled decision rules, 31 assessed items, 17 prioritization criteria and 15 available score contributions. These are different denominators. Their definitions, rather than the example's numerical values, are shared across studies.

## Historical titles with updated evidence bases

A criterion whose recorded title begins with Predicted can have a later version that accepts only derived values. For such a version, the interface provides a calculated display title while retaining the original name in the record. The rule is based on declared evidence bases, not on a hard-coded list of descriptors. Standards permitting predicted or mixed bases retain their original title.

Eligibility and scoring are overlapping uses. In the recorded case, five target criteria are both required evidence and scored criteria: 6 eligibility requirements + 17 scoring criteria − 5 shared criteria = 18 unique decision rules.
