# 一条命令交给其他 agent 运行

准备本仓库、Python 3.11+ 和公开的可选复现包即可。无需原始私有数据库、论文 PDF、私有账户或操作日志。使用**新的独立工作目录**。下面的命令从仓库根目录运行，适用于 PowerShell 和 Linux/macOS shell。

```sh
# 使用真实资格、评分和排序引擎复算历史结果。
python scripts/agent_run.py replay --bootstrap --workspace var/agent-replay

# 在工作台查看同一结果；首次需要时自动构建界面。
python scripts/agent_run.py serve --bootstrap --workspace var/agent-replay --open

# 准备完整原任务输入，以及 CQA 为零的独立证据来源。
python scripts/agent_run.py plan --bootstrap --workspace var/agent-live --task config/examples/task.original.json

# 明确调用自己的模型，前台等待完整研究流程结束。
python scripts/agent_run.py run --bootstrap --workspace var/agent-live --task config/examples/task.original.json --models /absolute/path/models.toml
```

Windows 也可以使用 `agent-run.cmd replay --workspace var/agent-replay --open`；该入口自动添加 `--bootstrap`。首次建立 `.venv` 后会复用，只有缺少包或运行依赖时才安装。仅当启动 `serve`、`--serve` 或 `--open` 且尚无 `web/client/dist/index.html` 时需要 Node.js/npm 来构建界面，已有 Python 环境和界面构建会直接复用。

## 历史复现与新研究的边界

保留案例当前显示 **10 个符合准入要求、1,305 个准入证据不完整、1,862 个已排除**。回放核对冻结资格字段（`qualified: 10`、`pending: 3167`、`rejected: 0`），工作台根据同一批评估生成当前分组和具体原因，详见[分类版本映射](../reference/system-alignment.md#classification-version)。

`replay` 下载约 168 MB 的可选 release 文件，按仓库 manifest 校验字节数和 SHA-256，导入公开不可变记录，然后调用生产环境的资格判断、偏好评分和榜单构建函数，逐候选比较全部榜单字段及相关汇总字段。**新增模型调用为零，新增检索为零，不生成新 CQA**。历史失败、原始运行身份、费用及预算报告保留原值。结果一致说明可以从已保存的评估复算同一榜单；此前模型与标准生成轨迹属于历史记录。

`plan` 不调用模型，只准备可执行的完整输入。原任务会基于固定的 3,157 条 claim、164 个来源、68,886 条历史工具事实建立新的纯证据来源，起始 CQA 数量为零。`run` 建立独立研究任务，依次执行任务理解、标准提出/审查/提炼、裁决、冻结、候选筛选和结果发布；当前模型使用的是已保存事实。这是新的反事实研究轨迹，标准、结果、费用和赢家都可能变化，Surufatinib 是否合格或排名第一需要查看实际结果。

新研究默认使用 **mid 文献及教材工作量、4 workers、10 美元预算、逐层筛选、仅使用已有证据**。`--workers`、`--budget-usd`、`--evaluation-mode full` 可修改本次工作流；历史记录中的原预算保持原值。来源缓存统一指向 `<workspace>/cache`。

## 配置模型和凭证

将[模型配置示例](../../config/examples/models.deepseek.toml)复制到仓库外，配置 provider、model 和角色绑定，再设置文件声明的环境变量，或用 `api_key_file` 指向已有密钥文件。真实运行要求 `proposer`、`critic`、`adjudicator` 绑定实际 API 模型。缺少角色或凭证时会在启动付费工作流前明确失败。密钥不会写入终端或回执。`plan` 和 `replay` 无需模型配置。

```powershell
# PowerShell：变量名应与自己的 models.toml 对应。
$env:DEEPSEEK_API_KEY = '<your-key>'
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models C:/Users/YOU/.config/mas/models.toml
```

`run` 本身就是调用所配置模型的明确指令，无需再次确认。命令前台等待，stderr 输出可读进度，stdout 输出 JSON 回执。实际费用缺少价格或 token 信息时保留未知或部分已知；预算上限与已记录费用是不同字段。可选 `--config /path/mas.toml` 提供其他 MAS 参数。环境准备只检查本地条件，provider 连通性由真实研究请求检验。

## 自己的任务、候选和测量数据

从 [task.custom.example.json](../../config/examples/task.custom.example.json) 开始。填写 `objective`、字符串数组 `targets`、文字 `constraints` 和 `entity_type`（`drug`、`carrier` 或 `general`），并给出 `candidates_csv`、`measurements_csv`。CSV 路径相对于任务 JSON 所在目录解析，与 shell 当前目录无关。[候选模板](../../config/examples/candidates.csv)和[测量模板](../../config/examples/measurements.csv)仅包含表头，必须填写自己的真实数据。缺少文件或测量时会失败，不会生成观察值或退回原始化合物库。

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/my-study --task /path/my-study/task.json
python scripts/agent_run.py run --bootstrap --workspace var/my-study --task /path/my-study/task.json --models /path/models.toml
```

默认按大小写精确匹配 CSV 表头，也可以显式映射。候选表字段为 `candidate_id`（必填）、`name`、`smiles`、`inchikey`、`chembl_id`、`description`。测量表必填字段为 `candidate_id`、`property`、`value`、`basis`；其余字段为 `unit`、`conditions`、`source`、`summary`。数值测量必须有单位，无量纲写 `1`。`basis` 必须明确填写 `measured`、`curated`、`predicted`、`simulated` 或 `derived`。缺失观察直接省略，不能写成 `NaN`、`unknown` 或编造数值。每条测量通过精确候选 ID 关联，实验条件可用原文或 JSON 对象保存。

```json
{
  "candidates_mapping": {"candidate_id": "Sample ID", "name": "Display name"},
  "measurements_mapping": {"candidate_id": "Sample ID", "property": "Endpoint", "value": "Result", "unit": "Units", "basis": "Evidence basis"}
}
```

将可选映射加入任务 JSON；左侧为标准字段，右侧为实际表头。入口通过真实的 `UploadStore.preview` 和 `commit` 校验，保留声明的证据类型及来源，在模型调用前拒绝无效行。候选描述自身不会变成测量证据。命令行也可以通过 `--objective "..."`、`--targets target1 target2`、`--constraints "..."`、`--entity-type general`、`--title "..."`、`--reference-candidate "exact ID or name"` 覆盖任务值；参考候选用于核对实际结果，不会被强制设为赢家。

## 恢复、查看、导出与界面

中止或重启后重复**同一条 `run` 命令**。入口在提交前持久化请求身份，工作流数据库按该身份去重。暂停的研究沿用检查点及已用预算继续；已经完成、失败、取消或 unresolved 的研究返回已有结果，不会因重复命令悄悄开始新的付费研究。任务、模型或有效设置变化时需要明确加 `--new-run`。继续使用相同任务 JSON 和覆盖参数；重试省略 `--models` 时会沿用上次 TOML 路径。

```sh
python scripts/agent_run.py inspect --workspace var/agent-live
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models /path/models.toml --new-run
python scripts/agent_run.py serve --workspace var/agent-live --models /path/models.toml --port 8782 --open
```

`inspect`/`status` 只读工作流状态，不接管研究。其他入口命令持有操作系统工作目录锁，避免两个入口进程同时启动同一研究。一个工作目录使用一个管理进程；额外独立启动工作台可能干扰检查点归属。Ctrl+C 请求保存边界并等待当前工作达到边界，正在进行的模型请求可能需要等待 provider 超时。若模型发现必须补充的任务信息，回执会保留真实 `questions`；可以在工作台回答并继续，或修正任务后明确新建研究。

工作流完成后自动导出到 `<workspace>/exports/<workflow_id>/`，包含全部候选 JSON/CSV、CQA 历史和谱系、各阶段、任务、冻结运行绑定、模型计费、验证及报告。用 `--output /new/export/directory` 指定其他位置；重复运行复用同一结果的已有导出。未完成状态保存在 `agent-run-incomplete.json`，不宣称存在最终结果。流程完成与科学成功分别报告；当参考候选能唯一匹配时，回执另外给出其实际资格和前五情况。

默认界面地址为 `http://127.0.0.1:8782/`。在 `replay`/`run` 后加 `--serve` 可保持界面服务，`--open` 还会打开浏览器。同一目录先结束 `run` 再单独使用 `serve`。准备结果在 `agent-plan.json`，复现校验在 `agent-replay-receipt.json`，真实运行回执在 `agent-run-receipt.json`。退出码：`0` 成功/已完成，`2` 配置、输入或运行错误，`3` 已保存的真实研究未完成或需要处理，`4` 复算与记录不同。

## 本地复现包与下载缓存

```sh
python scripts/agent_run.py replay --workspace var/offline-replay --bundle /path/to/capsule-directory
python scripts/agent_run.py plan --workspace var/offline-live --bundle /path/to/capsule-directory --task config/examples/task.original.json
```

目录应含 `manifest.json` 及其声明的数据文件。导入接口校验全部哈希，复用相同数据包的已完成导入，也能依据 `.mas-import` 标记继续自己的中断导入。无关的非空工作区和发生冲突的文件保持原样并明确拒绝。下载默认缓存在目标目录之外的 `<repo>/var/downloads/reproduction/<sha256>/`，可用 `--download-cache /outside/cache` 修改。中断下载不会发布为可导入文件，损坏缓存不会进入研究库。公开文件为 [v1.1.0 复现包](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/oral-multitarget-latest-v1.jsonl.gz)，校验依据是[仓库 manifest](../../examples/oral-multitarget/latest/reproduction/manifest.json)。恢复工作区约需 3 GB，首次浏览器索引需要几分钟。

[English instructions](../agent-run.md)
