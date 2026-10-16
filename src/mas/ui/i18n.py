"""Translate interface literals only. Research records and form values are never translated."""

from __future__ import annotations

from contextvars import ContextVar
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit

LANGUAGE = ContextVar("mas_ui_language", default="en")

# The presentation source keeps its original Chinese literals. Only those literal
# fragments enter ui_template; dynamic task, criterion, evidence and model values do not.
_PAIRS = """
先查看保留、合并与待审状态，再整理标准并冻结新的运行方案。已有榜单继续保留其原规则版本。|Review retained, merged and pending criteria, then prepare a new measurement. Existing results keep their original rules.
仅复用确切化合物与靶点对应的测量。排除记录保留，缺失状态继续如实呈现。|Measurements apply only to the exact compound and target. Exclusions and missing values remain visible.
选择任务，整理标准，冻结方案，再完整运行。每个新读数拥有独立记录。|Choose a task, review its criteria, prepare a measurement and run the full candidate set.
专家决定通过终端录入；指定项目的机器裁决可从本机操作面板提交。|Expert decisions are recorded separately. A single item can be sent for machine review here.
字段会由系统按类型和范围校验，配置原子保存在本机，不包含密钥。|Save validated settings for subsequent work. Credentials are not included.
冻结后配置变化会触发漂移检查。需要改变政策时，创建新的方案。|The saved measurement fixes its settings. Prepare a new measurement to change them.
系统在现有标准上整理，结果会给出保留、合并、撤回和待审计数。|Review existing criteria and track what is retained, merged, retired or awaiting review.
运行可能访问证据服务并产生模型费用，实际使用会记录在预算中。|A run may access evidence services and incur model costs. Recorded usage appears in the budget.
在同一冻结规则下比较候选，排名、证据覆盖与资格同时呈现。|Compare candidates under the same saved rules, with coverage and eligibility alongside rank.
新任务会继承现有记录，原任务的榜单和冻结方案继续保留。|The new experiment inherits existing records. Previous results remain available.
语义判定口径执行存在差异，两个读数不作直接增减比较。|The semantic review differed between readings, so they are not a direct before-and-after comparison.
此任务已有冻结方案，创建新的继承任务后再附着补证。|This task already has a saved measurement. Create a new experiment to add evidence.
从研究目标到候选证据，在同一个工作区追踪每一步。|Follow the research question, criteria, runs and evidence in one workspace.
核验的真实测量绑定到当前新任务，再冻结测量方案。|verified measurements to this new task before preparing its measurement.
此任务已有冻结结果，先在上方创建继承任务再整理。|This task has saved results. Create a new experiment above to review its criteria.
份来源。已知缺口的来源选择作为探索性补证记录。| sources attached. Sources selected for a known gap are recorded as exploratory evidence.
分数只来自已评估值；缺失状态保留在证据详情中。|Scores use assessed values. Missing evidence remains visible in candidate details.
查看待处理项目、机器裁决与专家决定的实际记录。|Review pending items and recorded machine or expert decisions.
为本次新读数固定规则、证据范围和排名政策。|Save the rules, evidence scope and ranking policy for this measurement.
从已有任务继承一个新实验，保留已完成结果。|Start a new experiment from an existing task while keeping its results.
只使用选择的冻结方案，候选结果可逐项追溯。|Run the selected measurement and inspect the evidence behind every candidate.
把候选的排名、标准判定与原始证据放在一起。|Inspect the ranking, individual assessments and original evidence together.
此运行已记录当前状态，刷新可读取最新记录。|Refresh to read the latest recorded state.
修改仅影响后续操作，现有榜单保留原配置。|Changes apply to subsequent work. Existing results keep their original settings.
查看继承标准的状态、支持证据与合并沿革。|Review criterion states, supporting evidence and revision history.
作为补充读数保留，不阻塞当前研究流程。|Kept as a descriptive reading, without blocking the current workflow.
凭据仅显示读取方式，页面不会读取密钥。|Credentials remain private; only the configured source is shown.
追踪已记录的执行进度、证据判定与预算。|Track recorded progress, assessments and budget.
先冻结一个新的测量方案，再开始运行。|Prepare a new measurement before starting a run.
当前尚无通过证据核验的作用机制解释。|No evidence-checked mechanism explanation has been recorded yet.
按现有证据整理；实际结果将保留记录。|Review existing evidence and retain the resulting decisions.
活跃总量包含额外未注册的待处理条目。|The active total includes additional unregistered items awaiting review.
了解当前配置、模型分工与参数来源。|Configure the workspace and review model assignments.
追踪已记录的阶段、模型活动与预算。|Track recorded stages, model activity and cost.
真实进程状态、退出码和结果链接。|Follow active work and open its progress or results.
作用机制说明独立于排名与分数。|Mechanism explanations are separate from ranking and scoring.
结果快照 · 每份读数独立保留|Saved results · each reading remains available
保留每次运行的实际状态与结果|Every recorded run keeps its actual outcome
后，任务与结果会显示在这里。| to display its tasks and results here.
工作区暂无研究任务。接入已有|No research tasks are available. Open an existing
引文来自记录中的来源与定位。|Quotes retain their recorded source and location.
暂无可选择的已核验测量来源。|No verified measurement source is available.
选择任务查看标准、排名和证据|Choose a task to inspect its criteria, ranking and evidence
只展示真实开始与完成记录。|Shows recorded model start and finish events.
整理状态与计分集合独立展示|Criterion review and the scoring set are shown separately
记录；专家审批由终端录入。|. Expert approval is recorded separately.
这些记录保持机器裁决身份。|These decisions retain their machine-review status.
配置来源、提供方与完整记录|Configuration sources and full details
固定方案 · 可追溯证据|Saved measurement · traceable evidence
尚未从此工作区启动操作。|No work has been started from this workspace yet.
当前保留标准中的待审项目|Pending review among retained criteria
数据来自可追溯的研究记录|Based on traceable research records
注册、计分与待审分别统计|Registered, scoring and pending counts remain separate
请选择尚未绑定运行的方案|Choose an unused measurement
从复核队列选择对应项目|Select an item from the review queue
单项机器裁决与运行身份|Single-item review and operator details
完整候选范围 · 固定|Full candidate set · fixed
已完成 · 总量未确定| completed · total not fixed
标准整理接口暂未启用。|Criterion review is not available yet.
筛选本页候选名称或编号|Filter candidates on this page
资源与评估进度分别记录|Resource use and assessment progress are recorded separately
从当前任务创建新实验|Create a new experiment from this task
包含完成、失败与中断|Includes completed, failed and interrupted runs
基于已记录的研究状态|Based on recorded research state
已记录 · 冻结读数|Recorded · saved measurement
整理前后保持真实计数|Counts reflect the current record
模型估计费用（美元）|Estimated model cost (USD)
等待进一步处理的项目|Items awaiting further review
进行中的请求尚未计入|In-flight requests are not yet included
预设。推荐文献与教材| preset. Recommended literature and textbook
包含未知与失败状态|Includes unknown and failed assessments
包含每个参数的来源|With the source of each setting
可复用的工作区设置|Reusable workspace configuration
完整记录与追溯信息|Full record and provenance
按实际阶段结束记录|From recorded stage completions
按本次冻结规则计分|Scored under this measurement
搜索标准名称或定义|Search criterion names or definitions
撤回记录与原因保留|Retirement records and reasons remain available
暂无已记录的数据。|No data has been recorded yet.
正在读取操作状态…|Loading activity...
正在读取系统能力…|Checking availability...
等待下一条运行记录|Waiting for the next recorded event
记录本次规则与政策|Save the rules for this reading
证据范围与延后能力|Evidence scope
保留机器裁决身份|Machine-review status retained
历史标准近似恢复|Historical criteria recovered
可复现的候选顺序|Reproducible candidate order
可继续选择任务。| Continue by choosing a task.
可能影响后续运行|May affect subsequent work
合并沿革独立保留|Merge history remains available
已保存当前任务。|Current task saved.
已发布的候选榜单|Published candidate results
已接纳的证据记录|Admitted evidence records
暂无已接纳证据。|No admitted evidence is available.
未结清的复核记录|Unresolved review items
来自真实专家决定|Recorded expert decisions
来自运行状态记录|From recorded run states
此次延后文献检索|Defer literature retrieval for this reading
此次延后预测属性|Defer predicted properties for this reading
此运行绑定的规则|Rules bound to this run
缺失值保留为未知|Missing values remain unknown
选择真实测量来源|Choose verified measurements
任务保存失败：|Could not save the task: 
已记录估计费用|Recorded estimated cost
已记录模型用量|Recorded model usage
按当前榜单记录|As recorded in this result
排名覆盖门槛：|Ranking coverage floor: 
接入待处理标准|Load pending criteria
日志与追溯信息|Logs and details
服务启动时解析|Resolved for this workspace
本机操作已启用|Local actions enabled
本机研究工作台|Local research workspace
条历史条目 ·| historical items ·
查看进度与结果|Open progress and results
标准整理与压缩|Review and consolidate criteria
标准池沿革 ·|Criterion history ·
状态读取失败：|Could not load activity: 
等待进程输出…|Waiting for output...
轮，可提前停止| iterations; may stop early
运行与操作记录|Activity
运行并查看结果|Run and inspect results
进入整理工作区|Open criterion review
选择任务并继续|Choose a task and continue
选择已核验来源|Choose a verified source
配置研究工作区|Configure workspace
附着已核验测量|Add verified measurements
附着选择的补证|Add selected evidence
预设 · 配置| preset · configuration
偏好证据覆盖|Preference evidence coverage
冻结本次方案|Prepare evaluation
冻结测量方案|Prepare evaluation
切换研究任务|Change task
创建继承任务|Create new experiment
历史标准恢复|Historical criteria recovery
参考候选排名|Reference candidate ranking
后续操作使用|Subsequent work uses the
导出完整榜单|Export full results
已记录的任务|Recorded tasks
开始完整运行|Start full run
当前保留标准|Retained criteria
当前模型分工|Current model assignments
当前研究 ·|Current research ·
当前研究任务|Current research task
当前计分标准|Scoring criteria
必需标准资格|Required-criteria eligibility
提交机器裁决|Request machine review
整理研究标准|Refine criteria
最近模型活动|Recent model activity
未注册待处理|Unregistered pending items
本次标准整理|Current criterion review
机器裁决记录|Automated review history
条测量，排除| measurements; excluded
查看候选排名|Open ranking
查看全部标准|View all criteria
查看固定榜单|Open saved results
查看整理运行|Open review run
标准流程监控|Criterion workflow progress
等待完成记录|Awaiting finish record
运行中页面每|This page refreshes every
返回候选排名|Back to ranking
选择当前任务|Select current task
选择测量方案|Choose measurement
逐项标准判定|Individual assessments
附着测量补证|Add verified evidence
专家已决定|Expert decisions
交互与权限|Interaction and permissions
份结果快照| saved results
保存失败：|Save failed: 
候选与证据|Candidate and evidence
冻结规则集|Saved rules
原任务读数|Original reading
可排名候选|Rankable candidates
可追溯证据|Traceable evidence
工作区设置|Settings
已保存 ·|Saved ·
已启动 ·|started ·
已完成评估|assessments completed
已完成请求|Finished requests
已完成阶段|Completed stages
已开始请求|Started requests
已撤回标准|Retired criteria
已核验补证|Verified evidence
已记录用量|Recorded usage
已记录输入|Recorded input
已记录输出|Recorded output
并发候选数|Concurrent candidates
当前已附着|Currently attached:
当前阶段：|Current stage: 
待处理项目|Pending items
或规则引用| or criterion reference
把经过原文|Add source-span-
描述性参考|Descriptive reading
提交失败：|Request failed: 
新实验目的|Purpose of the new experiment
暂无任务。|No tasks are available.
暂无法确定|Unresolved
有条件研究|Conditional research
未记录引文|No quote was recorded
未选择任务|No task selected
本机工作区|Local workspace
机器已裁决|Automated decisions
机器裁决按|Machine decisions are recorded as
条注册标准| registered criteria
查看此快照|Open this result
模型与角色|Models and roles
正在提交…|Submitting...
沿革与详情|History and details
注册历史共|Historical registrations:
研究工作区|Research workspace
研究工作台|Research workspace
终止此进程|Stop this job
记录身份：|Recorded operator: 
评估完成度|Assessment completeness
评分表达式|Scoring expression
运行与操作|Run
运行工作区|Run workspace
配置与模型|Settings and models
配置工作区|Configure workspace
阅读与提取|Reading and extraction
预算与资源|Budget and resources
个阻塞项| blocking items
任务总览|Research
估计费用|Estimated cost
作用机制|Mechanism of action
保存配置|Save settings
保留注册|Retained registrations
候选排名|Results
候选排序|Ranking
候选榜单|Candidate results
候选评估|Candidate assessment
偏好分数|Preference score
偏好覆盖|Preference coverage
全体候选|All candidates
冻结方案|Prepare evaluation
判定数量|Assessments
参考候选|Reference candidate
启动时间|Started
固定种子|Seed
处理结果|Outcome
处理路径|Review route
复核原因|Reason for review
复核队列|Review queue
完整运行|Full run
尚未冻结|No saved rules
已运行）|already used)
已附着）|already added)
延后理由|Reason for deferral
当前任务|Current task
当前计分|Scoring
当前迭代|Current iteration
当前预设|Preset
待审标准|Criteria awaiting review
待审项目|Pending review
必需标准|Required criteria
支持证据|Supporting evidence
数据来源|Data sources
整理标准|Refine criteria
整理目的|Purpose of the review
方案依据|Measurement rationale
暂无任务|No tasks
最近活动|Latest activity
最近运行|Recent runs
本机操作|Local actions
本次撤回|Retired in this review
机器裁决|Automated review
查看运行|Open run
标准构建|Criterion development
模型角色|Model roles
注册标准|Registered criteria
活跃总量|Active total
测定依据|Determination basis
测量方案|Measurement
用途状态|Use
研究任务|Research tasks
研究标准|Criteria
研究运行|Research run
秒刷新。| seconds while running.
累计运行|All runs
终止原因|Termination reason
结果名称|Result name
结果快照|Saved results
裁决路径|Review route
计划评估|planned assessments
证据判定|Evidence assessments
证据检索|Evidence retrieval
证据缺失|Missing evidence
证据覆盖|Evidence coverage
运行参数|Run settings
运行失败|Failed
运行监控|Run progress
运行配置|Run settings
配置上限|Configured limit
配置参数|Settings
配置档案|Profile
阻塞项目|Blocking items
预先指定|Prespecified
预期作用|Expected effect
预测工具|Prediction tools
预算使用|Budget usage
预算记录|Budget
上一页|Previous
下一页|Next
个候选| candidates
主导航|Main navigation
份快照| saved results
共比较|Compared:
复核项|Review item
工作区|Workspace
工作台|Workspace
已使用|Used
已合并|Merged
已完成|Completed
已开始|Started
已排除|Excluded
已提出|Proposed
已撤回|Retired
已暂停|Paused
已注册|Registered
已筛除|Filtered out
已终止|Stopped
待复核|Pending review
待完善|Needs refinement
待解决|Unresolved
探索性|Exploratory
提供方|Provider
未排名|Unranked
未满足|Not met
未规定|Not specified
未评估|Unassessed
未通过|Not met
等待中|Queued
缺失：|Missing: 
规则集|Rules
资源量|workload
运行中|Running
退出码|Exit code
项参数| settings
上限|Limit
事件|Event
修订|Refine
候选|Candidate
分数|Score
判定|Assessment
刷新|Refresh
单位|Unit
变更|Changes
合并|Merge
失败|Failed
完成|Finished
开始|Started
排名|Rank
排除|Excluded
接纳|Accepted
推荐|Recommended
提炼|Distill
操作|Action
数值|Value
数量|Count
时间|Time
暂定|Provisional
条。| records.
查看|Open
标准|Criteria
模型|Model
注册|Register
状态|Status
筛查|Filter
类型|Type
结果|Results
角色|Role
证据|Evidence
说明|Notes
资源|Resource
输入|Input
输出|Output
运行|Run
迭代|Iteration
通过|Met
配置|Settings
阶段|Stage
项目|Item
默认|Default
共|Total
无|None
条| items
此|this
第|
轮| iterations
页| page
文献检索量|Literature workload
教材检索量|Textbook workload
每轮检索广度|Search breadth
检索轮数|Search rounds
每维度全文上限|Full texts per dimension
费用上限（美元）|Cost cap (USD)
预算耗尽处理|When budget is exhausted
交互方式|Interaction mode
排名覆盖门槛|Ranking coverage floor
必需标准资格门槛|Required-criteria eligibility floor
当前为只读模式。使用|This workspace is read-only. Use
启用本机操作。| to enable local actions.
任务、榜单、证据与复核队列可从上方导航查看。|Use the navigation to explore tasks, results, evidence and reviews.
选择一个运行查看进度。|Choose a run from the workspace to view its progress.
选择任务查看标准。|Choose a task to review its criteria.
此任务还没有注册标准。|No criteria have been registered for this task yet.
从排名中选择候选查看证据。|Choose a candidate from a ranking to inspect its evidence.
选择任务查看已保存结果。|Choose a task to view its saved results.
此任务还没有生成排名。可打开运行查看进度。|No ranking has been published for this task yet. Open its run to follow progress.
注册标准、标准池沿革和计分集合分别统计；计分较少不代表已完成标准整理。|Registered criteria, pool history and scoring criteria are counted separately. A smaller scoring set does not mean the registry has been reduced.
资格单独报告；必需标准覆盖不足的候选仍可能有排名。|Eligibility is reported separately; candidates missing required coverage may still be ranked.
此结果要求满足必需标准覆盖门槛才可排名。|This result requires required-criteria coverage for ranking.
迭代可能提前停止；阶段和模型活动按实际记录展示，不计算总百分比。|Iterations may stop early. Stages and model activity show recorded events without an overall percentage.
仅统计已完成请求中的已记录用量和估计费用。进行中的请求与未知费用未计入。|Only recorded usage and cost estimates from finished requests are included. In-flight requests and unknown charges are excluded.
历史用量可能仅记录最后一次修复尝试，按已记录值展示。|Historical usage may include only the final repair attempt and is shown as recorded.
未知|Unknown
已知小计|Known subtotal
已记录|Recorded
部分记录|Partial
完整记录|Complete
准备评估|Prepare evaluation
自动复核|Automated review
记录状态|Usage record
查看当前运行|Follow active run
复核选项|Review options
加载自动复核路径|Load automated review routes
设置已保存。请选择任务继续。|Settings saved. Choose a task to continue.
默认采用标准方案与适中的文献、教材阅读量。更改仅用于后续工作，已有结果保持原设置。|The default is Standard with Medium literature and textbook workloads. Changes apply to new work; existing results keep their settings.
设置检查通过后保存到本机，用于后续工作。|Validated settings are saved locally for future work.
少量|Light
适中|Medium
较多|Extensive
停止并保留已有结果|Stop and keep partial results
提醒后继续|Warn and continue
询问后继续|Ask before continuing
停止运行|Stop the run
检查点暂停|Pause at checkpoints
自动运行|Run automatically
证据阅读|Evidence reader
研究助理|Researcher
规划|Planner
审查|Reviewer
自动审查|Automated reviewer
摘要|Summarizer
准备评估前，可添加已核验的测量。|Add verified measurements before preparing the evaluation.
添加已核验的测量|Add verified measurements
添加选择的测量|Add selected measurements
份来源已添加。| sources attached.
来源说明|Source notes
此任务的操作记录|Activity for this task
此任务还没有操作记录。|No activity has been recorded for this task yet.
工作区历史|Workspace history
已有运行正在进行。|A run is already active for this task.
当前任务复核|Task review
工作区复核|Workspace review
查看当前任务及其运行中的复核项目。|Review items for the selected task and its runs.
未结束的运行记录|Open run records
已记录为排队、运行或暂停的记录|Records marked queued, running or paused
已记录状态|Recorded state
大量|Very extensive
交互引导|Interactive guidance
并行任务|Parallel work
证据检查|Evidence checks
教材阅读|Textbook reading
结果已保存，命令随后失败。|Command failed after result was saved.
查看已保存结果|Open saved result
旧版本复核记录|Earlier criterion requests
这些标准版本已被更新或撤回，原复核状态保留，不计入当前待审与阻塞项目。|These criterion versions were updated or retired. Their recorded review states are preserved and excluded from current pending and blocking counts.
记录详情|Record details
"""

TRANSLATIONS = dict(line.split("|", 1) for line in _PAIRS.strip().splitlines())
_ORDERED = sorted(TRANSLATIONS.items(), key=lambda pair: len(pair[0]), reverse=True)
_REVERSE = {english: chinese for chinese, english in TRANSLATIONS.items() if english}


def ui_template(text: str) -> str:
    if LANGUAGE.get() == "zh":
        return text.replace("冻结本次方案", "准备评估").replace("冻结测量方案", "准备评估").replace("冻结方案", "准备评估").replace("机器裁决", "自动复核")
    for chinese, english in _ORDERED:
        text = text.replace(chinese, english)
    return text.replace("（", "(").replace("）", ")").replace("：", ": ").replace("，", ", ").replace("。", ".")


def label(text: str) -> str:
    """Localize a known interface label returned by a metadata API."""
    return _REVERSE.get(text, text) if LANGUAGE.get() == "zh" else ui_template(text)


def language_for(target: str, headers: dict[str, str] | None = None) -> tuple[str, bool]:
    requested = (parse_qs(urlsplit(target).query).get("lang") or [None])[0]
    if requested in ("en", "zh"):
        return requested, True
    cookies = SimpleCookie()
    try:
        cookies.load(next((value for key, value in (headers or {}).items() if key.lower() == "cookie"), ""))
    except Exception:
        return "en", False
    saved = cookies.get("mas_ui_language")
    return (saved.value if saved and saved.value in ("en", "zh") else "en"), False
