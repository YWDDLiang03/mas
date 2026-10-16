# 注册标准修订历史：待运行结束后应用

**状态：prepared_not_applied。当前运行源码、前端产物、主库和缓存均未由本任务修改。**

补丁为 [registered_revision_history.patch](registered_revision_history.patch)，基线哈希在
[patch_manifest.json](patch_manifest.json)。仅涉及 `src/mas/ui/read_model.py` 和两个定向测试；
不修改标准、证据、评估、版本、裁决或科学运行。

## 修正行为

- 注册条目详情在查询时从 `criterion_versions` 沿实际 `supersedes` 链读取前版，
  不依赖可能跨版本变化的 alias；选定 v1 不会因此混入未来 v2/v3。
- 属性变化的 `before/after` 分别是前后属性原记录；规则变化的 `before/after`
  分别是前后规则原记录。规则关联的属性通过各自真实 `attribute_ref` 读取，
  不把最新属性字段拼进旧规则，也不把规则用途伪写进属性。
- `workbench_revision.reason` 优先于原 rationale；仅当其 `source_<kind>_ref`
  与本版 `supersedes` 一致时，才作为本次修订理由。后来版本复制的旧修订元数据
  不会被冒充成新修订原因。没有修订原因时保留真实 rationale，均不存在则为未知。
- 返回 `before_ref/after_ref/supersedes/reason_source/source_row` 以便检查依据。
  指定前版缺失或类型不符时，`before=null`、`predecessor_missing=true`，不推造前版。
- Pool/stage 详情保持原有确切 change 语义；注册条目中原有的 pool/stage 变更也原样保留。
  无 schema 变更，无缓存重建；现有前端的 Before/After 直接显示这些实际字段。

## 已做的最小验证

通过内存加载 proposed Python 实现，运行两个新临时 journal/cache 回归及一个原有
pool 版本/同版本阶段状态回归：**3 passed in 0.43s**。

真实查询仅通过 `SQLite mode=ro; query_only=ON`，没有构造/同步真实 ReadModel。
核对任务 `task_01M51AQ0JK0MYN47806ZD5XS1B`：

| 详情引用 | 确切行为 |
| --- | --- |
| `rule_predicted-acute-toxicity-ld50@v1` | 保留原 `higher_better` 与原定义，历史只含原 v1 属性/规则创建 |
| `rule_predicted-acute-toxicity-ld50@v2` | 属性比较为真实 v1 `higher_better` → v2 `lower_better`，并显示真实修订理由 |

原记录引用：v1 属性 `art_3500a4d69ae0`、规则 `art_56dabdccb249`；
v2 属性 `art_949fc848842c`、规则 `art_a40dd61271ed`。
缓存中的确切版本内容与源 artifacts payload 一致；事件 ID、版本链和理由见
[validation.json](validation.json)。未读取候选结果或重新评估任何案例。

`git apply --check --whitespace=error-all` 通过，基线源码哈希保持不变。

## 根任务确认可以部署后的步骤

以下均尚未执行：

```powershell
git apply --check --whitespace=error-all design_audit/workbench_redesign_2026-10-16/postrun_revision_history/registered_revision_history.patch
git apply design_audit/workbench_redesign_2026-10-16/postrun_revision_history/registered_revision_history.patch
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_registered_history_follows_exact_supersedes_without_mixing_record_kinds tests/test_read_model.py::test_registered_history_keeps_missing_predecessor_unknown tests/test_read_model.py::test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state -q
```

补丁不包含前端代码，无需为此重建前端。由根任务按当前运行边界决定重启展示服务，
随后打开上述 v2 详情确认 Before/After、真实修订理由与原 v1 详情。
上下文不匹配时先检查差异，不整份覆盖 proposed 文件。
