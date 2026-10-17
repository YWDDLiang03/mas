# MAS 研究工作台

[English](README.md) | **简体中文**

MAS 根据证据形成研究标准，判断候选资格，并为合格候选排序。研究者提供目标、候选范围与证据，工作台将这些输入连接成可以持续观察、逐项核对的研究流程。

[安装环境](docs/zh/installation.md) · [使用指南](docs/zh/user-guide.md) · [完整教程](docs/zh/tutorial.md) · [组件详解](docs/components/README.md) · [v1.0.0 发布说明](docs/releases/v1.0.0.md)

## 研究流程

```mermaid
flowchart LR
    A[研究目标] --> B[准备证据]
    B --> C[提出标准]
    C --> D[审查与提炼]
    D -->|修订| C
    D --> E[固定评估方案]
    E --> F[判断候选资格]
    F --> G[合格候选排序]
    G --> H[核对来源并导出]
```

标准先展开，再收敛。每条标准明确测量内容、观测汇总方式，以及硬条件、偏好或参考用途。资格与评分分别计算，缺证继续保留未知状态。

浏览器支持自然语言任务、候选与测量 CSV 上传、持续进度、标准演化、按文献组织的证据、逐项评分解释和完整导出。界面默认英文，可切换中文；切换仅影响 UI，研究内容和来源保留原文。

![案例的实际运行进度](docs/assets/progress-settings.jpg)

## Windows 快速开始

核心服务要求 Python 3.11+，前端构建需要 Node.js 和 npm。首次安装检查使用 Windows、Python 3.14.2 与 Node.js 24.13.0。

```powershell
git clone --depth 1 https://github.com/YWDDLiang03/mas.git
cd mas
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix web/client ci
npm.cmd --prefix web/client run build
.\start_workbench.cmd -Store var\workspace\store -InitializeStore -AllowOperations -ActorKind human -ActorName "$env:USERNAME"
```

打开[本地工作台](http://127.0.0.1:8769/workbench/)。首次启动创建空工作区，不调用模型。开始研究前按[中文安装说明](docs/zh/installation.md)配置模型与外置密钥，再导入数据或选择来源。发布的结果文件不会自动恢复原研究数据库。

[配置说明](docs/configuration.md)介绍优先级、角色绑定、费用记录和可选预测环境。密钥、本地数据库和缓存不进入 Git。

## 功能与组件导航

每个组件页均说明职责、设计理由、输入输出、失败处理、实现函数和示例。组件详解采用英文；[架构文档](docs/architecture.md)列出原设计 C1–C20 的全部实现状态。

| 组件 | 设计关注点 | 主要实现 |
|---|---|---|
| [记录与存储](docs/components/foundation.md) | 保留历史并重建决定 | [Journal](src/mas/core/journal.py)、[Store](src/mas/core/store.py) |
| [任务与配置](docs/components/tasks-and-configuration.md) | 将自然语言整理成明确范围 | [Task](src/mas/core/task.py)、[Config](src/mas/core/config.py) |
| [模型与预算](docs/components/models-and-budgets.md) | 记录角色调用与已知、未知费用 | [Models](src/mas/core/models.py)、[Budget](src/mas/core/budget.py) |
| [工具与提供者](docs/components/tools-and-providers.md) | 将能力匹配到可检查结果 | [Broker](src/mas/core/broker.py)、[Adapters](src/mas/adapters/) |
| [证据与阅读](docs/components/evidence-and-reading.md) | 保存发现、条件和原文位置 | [Reading](src/mas/core/reading.py)、[Evidence](src/mas/core/evidence.py) |
| [标准与审查](docs/components/criteria-and-review.md) | 提议如何修订、合并并启用 | [Derivation](src/mas/core/derivation_stages.py)、[Adjudication](src/mas/core/adjudication.py) |
| [评估与资格](docs/components/assessment-and-qualification.md) | 区分硬失败、缺失与合格 | [Assessor](src/mas/core/assessor.py)、[Measurement](src/mas/core/measurement.py) |
| [排名与解释](docs/components/ranking-and-explanations.md) | 解释贡献与比较范围 | [Leaderboard](src/mas/core/leaderboard.py)、[Score details](src/mas/ui/score_details.py) |
| [运行与复用](docs/components/execution-and-reuse.md) | 中断后继续并复用有效观测 | [Controller](src/mas/core/controller.py)、[Workflows](src/mas/ui/workflows.py) |
| [科研评价与 CQA 对比](docs/components/evaluation-and-recovery.md) | 记录参考暴露与恢复口径 | [Freeze](src/mas/core/freeze.py)、[Recovery](src/mas/core/recovery.py) |
| [领域适配器](docs/components/domain-adapters.md) | 更换对象或来源需要改什么 | [Drug](src/mas/adapters/drug/)、[Literature](src/mas/adapters/literature/)、[Prediction](src/mas/adapters/predict/) |
| [工作台与 CLI](docs/components/workbench-and-cli.md) | 操作和查看同一套记录 | [前端](web/client/src/)、[Read model](src/mas/ui/read_model.py)、[CLI](src/mas/cli/main.py) |

## 使用自己的研究任务

1. 在 **Settings** 设置工作强度、并发和预算。
2. 选择 **New research** 或 **Use own data**，填写目标、必需观测与约束。
3. 选择或上传候选，再选择证据或上传测量。预览核对身份、单位、条件和依据类型。
4. 启动研究，观察阶段进度与标准演化；待处理内容保留原因。
5. 查看候选分区，通过 **Score** 与 **Evidence** 核对结果，导出全部候选。

[使用指南](docs/zh/user-guide.md)解释操作与状态。[CSV 指南](docs/zh/csv-input.md)提供明确标注为合成的格式示例及校验规则。系统内置药物来源工具；载体和其他研究需要相应数据与适用工具。已发布的完整科研案例是药物研究。

## 最新示例：口服多靶点药物优先级

[完整教程](docs/zh/tutorial.md)从 Settings 开始，展示任务、证据选择、CQA 生成和提炼、六条分子量提议合并、资格核验、首次未排名的原因与修正、得分计算、来源回查和导出。

| 保存结果 | 最新研究 |
|---|---:|
| 候选范围 | 3,177 |
| 固定生成输入 | 3,157 条事实 / 164 个来源 |
| 标准演化 | 0 → 6 项要求 → 1,917 个工作项 → 53 |
| 启用核心 | 18：1 条硬条件 + 17 条偏好 |
| 其他工作项 | 13 条参考 + 22 条未启用 |
| 候选分区 | 10 合格；3,167 待补证据 |
| Surufatinib | 第 1 / 10；分数 0.7592592593 |
| Surufatinib 直接偏好覆盖 | 10/17 |

另保留[全面研究](examples/oral-multitarget/comprehensive/results/)，其中 Surufatinib 排第 4。两次冻结标准不同，分数在各自方案内解释。[完整结果](examples/oral-multitarget/)保留全部候选及未知状态。教程区分查看发布结果、使用原本地输入重跑，以及用自己的 CSV 开展新研究。

### 原始 CQA 与系统 CQA 对比

原手稿的 **11 项人工选择的预测性质条件**不同于早期 59 条系统注册标准。[逐项对比](docs/zh/cqa-comparison.md)得到：2 个同名端点但决策改变，3 行相关而定义仍未确定，6 个端点缺少对应项。最新 18 条核心中有 1 个原始同名端点，没有完整复现原始 Pass/Fail 条件。这是事后描述性比较，与排名结果分开，不是新的盲测恢复率。

[比较 CSV](examples/oral-multitarget/cqa-comparison.csv) · [比较 JSON](examples/oral-multitarget/cqa-comparison.json) · [PPT 与讲稿](docs/presentation/README.md)

## v1.0 范围与开发

v1.0 提供有记录的研究流程、药物及来源适配器、上传流程、资格优先排名和本地工作台。原设计中的通用规划智能体、开放问题服务、分域记忆及策略升级归档尚未全部实现，[状态表](docs/architecture.md)说明具体边界。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix web/client run build
.\.venv\Scripts\python.exe scripts/check_publication.py
```

默认测试排除在线服务。[贡献指南](CONTRIBUTING.md)介绍相关检查与科学记录要求；[发布说明](docs/releases/v1.0.0.md)记录验证、保留产物和仓库整理范围。
