# 安装与首次启动

MAS 可以从新的空工作区启动。源码仓库不携带保留研究的运行数据库、私人 API 密钥或候选库；已发布结果可独立查看，新研究可以导入自己的候选和证据。

## Windows 环境

- 核心服务需要 **Python 3.11 或更高版本**。可选预测器使用独立环境，不随核心依赖安装。
- 浏览器客户端使用 Node.js 与 npm 构建，建议安装 **Node.js 22 或 24 LTS**。当前锁定的 Vite 5.4.21 声明接受 `^18.0.0 || >=20.0.0`；维护状态参见 [Node.js 官方发布列表](https://nodejs.org/en/about/previous-releases)。
- 使用本机可写目录保存 SQLite 工作区。解压源码或用 Git 克隆后，在仓库根目录打开 PowerShell。

## 安装

```powershell
python --version
node --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix web/client ci
npm.cmd --prefix web/client run build
```

`requirements.txt` 安装当前源码和 `pyproject.toml` 中的开发依赖，等价于 `pip install -e ".[dev]"`。命令直接使用虚拟环境解释器，无需激活环境；`npm.cmd` 可避开 PowerShell 对 `npm.ps1` 的执行策略限制。更新前端源码后重新构建客户端。

## 首次打开空工作区

```powershell
.\start_workbench.cmd -Store var\workspace\store -InitializeStore -AllowOperations -NoBrowser -ActorKind human -ActorName "$env:USERNAME"
```

打开 [http://127.0.0.1:8769/workbench/](http://127.0.0.1:8769/workbench/)。首次任务列表、候选库和证据集合为空属于正常状态。初始化只创建表结构与通用模型配置示例，不创建候选、研究任务或科学结果。已有数据库保持原样；后续启动可省略 `-InitializeStore`。按 **Ctrl+C** 停止服务后再修改模型配置。

初始化产生的 `models.toml` 是等待外部代理答复的 exchange 示例。实际 API 研究请复制以下 DeepSeek 配置。首次打开空界面、查看 Settings 和解析配置不调用模型。

## 配置模型

```powershell
Copy-Item config\examples\models.deepseek.toml var\workspace\store\models.toml
Copy-Item config\examples\mas.toml var\workspace\store\mas.toml
.\.venv\Scripts\python.exe -m mas.cli.main --store var/workspace/store --config var/workspace/store/mas.toml config validate
.\.venv\Scripts\python.exe -m mas.cli.main --store var/workspace/store models show
```

在当前 PowerShell 会话中输入密钥，避免把明文密钥写进命令历史：

```powershell
$masCredential = Get-Credential -UserName 'DeepSeek' -Message 'Enter your DeepSeek API key in the password field'
$env:DEEPSEEK_API_KEY = $masCredential.GetNetworkCredential().Password
Remove-Variable masCredential
.\start_workbench.cmd -Store var\workspace\store -Models var\workspace\store\models.toml -Config var\workspace\store\mas.toml -AllowOperations -ActorKind human -ActorName "$env:USERNAME"
```

配置示例使用 [DeepSeek 官方 API](https://api-docs.deepseek.com/) 的 `deepseek-flash`，并提供仓库外 `api_key_file` 路径占位符。环境变量非空时优先使用环境变量，否则读取密钥文件。TOML 中的 `${ENV_VAR}`、`%ENV_VAR%` 不会自动展开；密钥文件请用实际绝对路径或 `~`。模型文件解析检查不验证账号权限；实际调用时才验证 API 访问。

该示例用于新的研究。最新保留研究在运行记录中使用历史模型 ID `deepseek-v4-flash`；解释或导出该研究时保留当时记录的身份。采用当前 API ID 配置新任务不会改写历史运行，也不构成重新执行后的结果。

## 导入自己的数据

先在 **Settings** 选择工作量、并行数和预算，再进入 **Use own data**，选择候选类型，导入候选 CSV、确认列映射，并导入对应测量 CSV。可从 [空表头模板](../../config/examples/) 开始填写真实数据；保留候选 ID、单位、实验条件、来源和 `measured` / `predicted` 证据类型。支持药物、载体及一般候选；字段、格式示例和预览纠错参见 [CSV 导入指南](csv-input.md)。

填写研究目标、必须具备的观测、硬条件和排序偏好。全新工作区没有继承证据：使用已有证据模式时，需要已保存的证据集合或上传测量；新文献研究应明确选择检索。开始研究会执行所选工作流，并可能产生模型费用和外部证据检索请求。界面语言切换只影响展示，原始输入保留，研究任务、标准和模型记录使用英文。

`-AllowOperations` 开启 Settings 修改、上传、创建任务和研究工作流控制；被记为人类专家决定的操作仍通过终端确认。简单示例让各模型角色共用同一服务；角色名称不代表独立模型审查。示例未填单价，费用可能为未知；设置预算前应核对供应商计费，并按当前价格填写配置中的可选 token 单价。

## 只读查看与路径

省略 `-AllowOperations` 使用旧版只读界面，拒绝写入请求：

```powershell
.\start_workbench.cmd -Store var\workspace\store -NoBrowser
```

现代 React 工作台目前需要 `-AllowOperations`，路径为 `/workbench/`。两种模式均只监听本机回环地址。端口冲突时加 `-Port 8781`，不必停止其他服务。

启动器优先使用本仓库 `.venv/Scripts/python.exe`，也支持 `-Python <绝对路径>`。相对 `-Store`、`-Models`、`-Config` 和解释器文件路径按仓库根目录解析，即使从其他目录调用也可定位构建资源。直接调用 `python -m mas.cli.main` 时，相对路径按当前目录解析。移动工作区时将数据库目录及同级上传、工作流和展示元数据一起移动。

缺少 `store.db` 时，新工作区加 `-InitializeStore`；已有研究则指定其实际目录。缺少客户端时重新执行 npm 安装和构建。出现 `auth_missing` 时，检查启动服务的进程是否有密钥变量，或密钥文件路径是否正确。未更换初始化时的 exchange 模型配置，会等待外部代理响应。

详细参数、覆盖优先级、来源工具、系统提示词位置以及可选 ADMET 环境见 [配置说明](../configuration.md)；其他系统的直接 Python 启动命令见 [英文安装文档](../installation.md)。v1 的工具与提示词在 Python 源码中注册，当前没有动态加载 `tools.toml` 或提示词 TOML 的接口。

2026-10-17 的安装验证使用 Windows、核心 Python 3.14.2、Node.js 24.13.0，覆盖前端构建、示例解析及独立端口的临时空工作区启动。此次检查未调用付费模型、未检索外部研究证据，也未安装验证新的 ADMET 环境。历史预测器记录使用 Python 3.11.17 与 `admet_ai` 2.0.1；准备预测环境时应使用独立兼容解释器，并在目标机器实际执行 `predict check`。
