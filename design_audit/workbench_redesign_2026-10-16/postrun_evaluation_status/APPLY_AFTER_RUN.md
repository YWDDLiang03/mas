# 最近准备评估的标准状态与理由（待应用）

**状态：prepared_not_applied。** 当前科学运行正在 screen；本补丁尚未应用。
当前源码、主库、缓存、展示服务及 `dist` 均未由本次工作修改。

补丁：[latest_evaluation_status.patch](latest_evaluation_status.patch)。
适用基线见 [patch_manifest.json](patch_manifest.json)。

## 最小行为变化

- 原 `state`、`reason`、历史版本和 pool/stage 记录全部保留。
  新增独立 `evaluation` DTO，明确其作用域为最近准备的评估，携带真实 `rule_set_ref` 和准备时间。
- 列表保留“Recorded state / 已记录状态”列，另列“Latest evaluation / 最近评估”；
  详情展示同一评估状态和简短说明，原机器理由、队列引用、attempt/receipt 引用及冻结原记录放入
  “Decision record / 处理记录”。不把机器复核冒充人工审批。
- 精确版本在最近冻结 `entries` 中为 enabled；未启用且在规则级 `deferred` 中为 deferred；
  明确的冻结 pending 或尚未注册的当前提案显示 pending。仅 route 被延后而规则仍在 entries 时仍为 enabled，
  具体路线延后记录保留在依据中。
- 当前条目尚无冻结记录时显示 not_prepared。历史版本若未在最近冻结中被明确列入、延后或标记 pending，
  只显示 saved version，不推断它过去是否启用。阶段快照保留阶段语义，不套用当前评估状态。
- 冻结原因和当时的复核详情来自现有缓存 frozen body。每个查询仅建立一次索引并读取一次当前队列，
  单行投影不再解析历史 journal。详情保留冻结时的 review/attempt 原记录；另列的队列状态明确标为 current_registry_queue。
  无 schema 变更、无缓存重建、无证据或评分计算。

本补丁涉及 6 个文件：read_model、CriteriaPage、API types、新 CriteriaEvaluation 组件、
一个定向回归，以及 `scripts/accept_workbench_run.py` 的 DTO 比较接线。
未修改来源、阈值、资格、评分、排序或冻结记录。

## 实际只读核对

任务 `task_01M51AQ0JK0MYN47806ZD5XS1B`，最近冻结 `rules@v2`：
源 artifact `art_039fe32dbd20`，事件 `evt_01M51NVTF4CJSHW8FT122RK6FS`。
冻结仍为 **24 条 enabled、19 条 deferred**。

- `rule_molecular-weight-oral-absorption@v2` 原注册状态仍为 active；
  evaluation 为 deferred / unresolved_review，原因与源冻结完全一致。
  队列 `q_01M51NM0S3QQCPBPQVRVAT18NF` 与尝试 `art_5ccd24da9d66` 保留；
  原记录说明 cutoff_basis=source_stated_value 的截点仍需专家判断，不能据此宣称已启用。
- `rule_csf1r-curated-potency@v1` 明确为 enabled，依据为最近冻结的确切 entries。
- `rule_molecular-weight-oral-absorption@v1` 作为 saved_version 展示，不编造历史未启用状态。

完整证据见 [validation.json](validation.json)。实际库、缓存均以 SQLite `mode=ro; query_only=ON` 打开，
没有构造/同步真实 ReadModel，也没有读取候选结果。

## 定向验证与验收兼容

- 一个新回归覆盖未准备、真实型 unresolved defer、enabled 锚点、旧版本作用域、pool stage 作用域。
  复用 pool exact-version 和 registered supersedes 两个既有回归：**3 passed in 0.51s**。
- 严格 TypeScript 在虚拟 proposed 文件上通过；未构建或写入 `dist`。
- 准备的 acceptance 脚本对直接缓存 DTO 使用与 API 相同的边界投影，没有忽略或剥除 evaluation。
  真实缓存全部 **1,840 个条目**与新 API DTO 精确一致。
- 验收脚本另外增加独立源冻结检查：对每个当前注册条目的 state、rule_set_ref、原 reason 做比较。
  本次 **43 条当前注册规则**全部与源冻结匹配，避免共享投影函数掩盖状态差异。
- `git apply --check --whitespace=error-all` 通过，活动源码哈希未变。

## 根任务确认可以应用之后

以下步骤尚未执行；当前 run 不应为了展示补丁中断：

```powershell
git apply --check --whitespace=error-all design_audit/workbench_redesign_2026-10-16/postrun_evaluation_status/latest_evaluation_status.patch
git apply design_audit/workbench_redesign_2026-10-16/postrun_evaluation_status/latest_evaluation_status.patch
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_latest_evaluation_status_preserves_registry_history_and_frozen_reasons -q
npm --prefix web/client run build
```

再由根任务按安全边界重启展示服务，实际检查 Pending/MW v2、启用锚点和旧 v1。
最终 completed workflow 的正常 acceptance 需保留新增的独立源检查。
若补丁上下文发生变化，先审查差异，不整份覆盖 proposed 文件。
