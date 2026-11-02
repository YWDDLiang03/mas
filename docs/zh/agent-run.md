# 从任务文件启动研究

[流程设计](design.md) · [文档导航](README.md)

准备本仓库和 Python 3.11+，复现公开案例时再加载可选复现包。使用**新的独立工作目录**。下面的命令从仓库根目录运行，适用于 PowerShell 和 Linux/macOS shell。

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

## 复现与新研究

保留案例当前显示 **10 个符合准入要求、1,305 个准入证据不完整、1,862 个已排除**。回放核对冻结资格字段（`qualified: 10`、`pending: 3167`、`rejected: 0`），工作台根据同一批评估生成当前分组和具体原因，详见[分类版本映射](../reference/system-alignment.md#classification-version)。

`replay` 下载约 168 MB 的可选 release 文件，按仓库 manifest 校验字节数和 SHA-256，导入公开不可变记录，然后调用生产环境的资格判断、偏好评分和榜单构建函数，逐候选比较全部榜单字段及相关汇总字段。复算使用保存的评估，原标准历史、运行身份、费用及预算继续关联相应记录。

`plan` 不调用模型，只准备可执行的完整输入。原任务会基于固定的 3,157 条 claim、164 个来源、68,886 条历史工具事实建立新的纯证据来源，起始 CQA 数量为零。`run` 建立独立研究任务，依次执行任务理解、标准提出/审查/提炼、裁决、冻结、候选筛选和结果发布；当前模型使用的是已保存事实。每项新研究记录自己的标准、结果、费用和优先候选。

新研究默认使用 **mid 文献及教材工作量、4 workers、10 美元预算和逐层筛选**。原案例与上传观测任务使用保存的证据，自有药物库任务默认检索新证据。`--workers`、`--budget-usd`、`--evaluation-mode full` 可修改本次工作流；历史记录中的原预算保持原值。来源缓存统一指向 `<workspace>/cache`。

## 配置模型和凭证

将[模型配置示例](../../config/examples/models.deepseek.toml)复制到仓库外，配置 provider、model 和角色绑定，再设置文件声明的环境变量，或用 `api_key_file` 指向已有密钥文件。真实运行要求 `proposer`、`critic`、`adjudicator` 绑定实际 API 模型。缺少角色或凭证时会在启动付费工作流前明确失败。密钥不会写入终端或回执。`plan` 和 `replay` 无需模型配置。

```powershell
# PowerShell：变量名应与自己的 models.toml 对应。
$env:DEEPSEEK_API_KEY = '<your-key>'
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models C:/Users/YOU/.config/mas/models.toml
```

`run` 启动所配置的模型，前台显示进度并输出 JSON 回执。费用记录区分估计、部分已知和未知，预算约束作用于可计费的金额。可选 `--config /path/mas.toml` 提供其他设置，研究使用所配置的提供者连接。

## 使用自己的药物库

使用 [task.library.example.json](../../config/examples/task.library.example.json)。`library_json` 指向自己的药物库文件，路径相对于任务 JSON。填写靶点与需求；已有靶点时，研究背景文字可选。

```json
{
  "input_mode": "library",
  "library_json": "drug-library.json",
  "targets": ["EGFR", "MET"],
  "constraints": "Documented oral administration is required.",
  "evidence_mode": "retrieve",
  "cdes_enabled": false,
  "workers": 4,
  "budget_usd": 10
}
```

药物库 JSON 包含非空 `universe` 数组，每个候选提供 `name`、`inchikey`、`chembl_id`，InChIKey 保持唯一。保留数据库来源 `source`、数据日期 `retrieved_at` 和已有产品或给药字段 `fields`。运行器会把带校验信息的副本保存到工作区。

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/target-study --task /path/task.json
python scripts/agent_run.py run --workspace var/target-study --task /path/task.json --models /path/models.toml
```

`library` 模式使用提供的候选范围、靶点与需求，从本研究的证据开始。`original` 模式用于沿公开案例的事实输入重新生成标准。

### 选择 CDES

任务 JSON 接受 `cdes_enabled` 和 `cdes_source_id`。开启 CDES 时，只有一个可用集合会自动选定；存在多个集合时，在工作台或任务文件中明确选择。集合在启动前固定，接入方法见[CDES 指南](../components/structure-predictions.md)。

CDES 在主评价之后增加靶点分析阶段，记录实际关联的药物–靶点组合及缺项。综合榜沿用其评价标准。当前实现通过部署接口读取提供的结果。

## 自己的任务、候选和测量数据

从 [task.custom.example.json](../../config/examples/task.custom.example.json) 开始。填写 `objective`、字符串数组 `targets`、文字 `constraints` 和 `entity_type`（`drug`、`carrier` 或 `general`），并给出 `candidates_csv`、`measurements_csv`。CSV 路径相对于任务 JSON 所在目录解析，与 shell 当前目录无关。[候选模板](../../config/examples/candidates.csv)和[测量模板](../../config/examples/measurements.csv)仅包含表头，必须填写自己的真实数据。运行器在准备研究前校验所提供的文件。

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/my-study --task /path/my-study/task.json
python scripts/agent_run.py run --bootstrap --workspace var/my-study --task /path/my-study/task.json --models /path/models.toml
```

默认按大小写精确匹配 CSV 表头，也可以显式映射。候选表字段为 `candidate_id`（必填）、`name`、`smiles`、`inchikey`、`chembl_id`、`description`。测量表必填字段为 `candidate_id`、`property`、`value`、`basis`；其余字段为 `unit`、`conditions`、`source`、`summary`。数值测量必须有单位，无量纲写 `1`。`basis` 必须明确填写 `measured`、`curated`、`predicted`、`simulated` 或 `derived`。已有观测按行提供，缺失观测留空缺。每条测量通过精确候选 ID 关联，实验条件可用原文或 JSON 对象保存。

```json
{
  "candidates_mapping": {"candidate_id": "Sample ID", "name": "Display name"},
  "measurements_mapping": {"candidate_id": "Sample ID", "property": "Endpoint", "value": "Result", "unit": "Units", "basis": "Evidence basis"}
}
```

将可选映射加入任务 JSON；左侧为标准字段，右侧为实际表头。入口通过真实的 `UploadStore.preview` 和 `commit` 校验，保留声明的证据类型及来源，在模型调用前拒绝无效行。候选描述和观测行分别承担相应作用。命令行也可以通过 `--objective "..."`、`--targets target1 target2`、`--constraints "..."`、`--entity-type general`、`--title "..."`、`--reference-candidate "exact ID or name"` 覆盖任务值；参考候选用于核对结果中的对应条目。

## 恢复、查看、导出与界面

中止或重启后重复**同一条 `run` 命令**。入口在提交前持久化请求身份，工作流数据库按该身份去重。暂停的研究沿用检查点及已用预算继续；已经完成、失败、取消或 unresolved 的研究返回已有结果，不会因重复命令悄悄开始新的付费研究。任务、模型或有效设置变化时需要明确加 `--new-run`。继续使用相同任务 JSON 和覆盖参数；重试省略 `--models` 时会沿用上次 TOML 路径。

```sh
python scripts/agent_run.py inspect --workspace var/agent-live
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models /path/models.toml --new-run
python scripts/agent_run.py serve --workspace var/agent-live --models /path/models.toml --port 8782 --open
```

`inspect`/`status` 只读工作流状态，不接管研究。其他入口命令持有操作系统工作目录锁，避免两个入口进程同时启动同一研究。一个工作目录使用一个管理进程；额外独立启动工作台可能干扰检查点归属。Ctrl+C 请求保存边界并等待当前工作达到边界，正在进行的模型请求可能需要等待 provider 超时。若模型发现必须补充的任务信息，回执会保留真实 `questions`；可以在工作台回答并继续，或修正任务后明确新建研究。

工作流完成后自动导出到 `<workspace>/exports/<workflow_id>/`，包含全部候选 JSON/CSV、CQA 历史和谱系、各阶段、任务、冻结运行绑定、模型计费、验证及报告。用 `--output /new/export/directory` 指定其他位置；重复运行复用同一结果的已有导出。未完成状态保存在 `agent-run-incomplete.json`，结果报告同时给出实际规则、证据和研究结论；当参考候选能唯一匹配时，回执另外给出其实际资格和前五情况。

默认界面地址为 `http://127.0.0.1:8782/`。在 `replay`/`run` 后加 `--serve` 可保持界面服务，`--open` 还会打开浏览器。同一目录先结束 `run` 再单独使用 `serve`。准备结果在 `agent-plan.json`，复现校验在 `agent-replay-receipt.json`，真实运行回执在 `agent-run-receipt.json`。退出码：`0` 成功/已完成，`2` 配置、输入或运行错误，`3` 已保存的真实研究未完成或需要处理，`4` 复算与记录不同。

## 本地复现包与下载缓存

```sh
python scripts/agent_run.py replay --workspace var/offline-replay --bundle /path/to/capsule-directory
python scripts/agent_run.py plan --workspace var/offline-live --bundle /path/to/capsule-directory --task config/examples/task.original.json
```

目录应含 `manifest.json` 及其声明的数据文件。导入接口校验全部哈希，复用相同数据包的已完成导入，也能依据 `.mas-import` 标记继续自己的中断导入。无关的非空工作区和发生冲突的文件保持原样并明确拒绝。下载默认缓存在目标目录之外的 `<repo>/var/downloads/reproduction/<sha256>/`，可用 `--download-cache /outside/cache` 修改。导入使用已完成下载且通过校验的文件。公开文件为 [v1.1.0 复现包](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/oral-multitarget-latest-public-20261028.jsonl.gz)，校验依据是[仓库 manifest](../../examples/oral-multitarget/latest/reproduction/manifest.json)。恢复工作区约需 3 GB，首次浏览器索引需要几分钟。

[English instructions](../agent-run.md)
