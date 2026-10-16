# 待科学运行完成后应用：标准列表范围修正

**部署更新：已应用。** 根任务在 CQA 生成完成、Review 已保存且尚未冻结评估方案的检查点停止预览服务，将此查询/展示补丁与评分可执行性守卫一并部署；无需重新生成标准或重跑旧案例。20 项查询模型测试、TypeScript 和构建通过，真实浏览器已验证父 v1 链接、阶段搜索保留及 Added=6。后端归档为 `var/provenance/workbench-v2/1d0272a80e953952`。下文保留补丁准备时的范围与验证说明。

补丁：[working_criteria.patch](working_criteria.patch)。适用基线见
[patch_manifest.json](patch_manifest.json)；准备时使用的是当前工作区文件，不能假设 Git HEAD 与工作区相同。

## 最小行为变化

- 前端默认使用 `state=working`，显示 **Working criteria / 当前标准**。
  没有冻结方案时，仍展示当前注册标准与未解决工作提案。
  已有冻结方案时，只列最近 `criterion.version_approved` 的 `entries`，含硬条件和偏好规则。
  这是“最近准备的评估”，并不跟随 Candidates 页面选择的历史榜单快照。
- **Pending / 待处理** 使用服务端条件：当前未注册提案、当前注册待复核项，
  以及有冻结方案时未入选该方案的当前规则。退休、合并和已失效版本不计入当前 Pending。
  若某条已启用规则仍有未结复核，它会同时出现在 Working 与 Pending；两者不是可相加的互斥计数。
- 搜索、角色筛选、`count(*)` 和分页都在同一条服务端筛选范围上执行。
  不在前端删掉分页后的行，`total / has_more` 保持真实。
- 旧 `state=active` API 仍保留原有的广泛当前工作集语义。
  新界面会把此前保存的 `active` 偏好迁移为 `working` 并回第一页；明确保存的其他筛选保持。
- “全部版本 / merged / retired”和阶段历史筛选保留。
  选中阶段时仍显示该阶段的变化；清除阶段后回到 Working。
- 冻结启用条目从已有 `criterion_versions` 缓存重建确切属性和规则版本；
  后续 v2 不会把冻结 v1 从主列表抹掉。冻结列表的详情入口使用确切 `rule@v`，
  详情也读取该版本。无需修改缓存 schema 或科学记录。
- 表格现在明确传 `detail_ref`：注册条目优先确切 `rule@v`；普通 pool 使用 `cri@v`；
  阶段历史使用 `change:<原变化ID>`，因为同一 pool 版本也可能在后续阶段改变状态。
  这些确切引用不会再通过 alias 静默落到最新版本。旧版详情只读，可明确跳转到当前版本后编辑。
- mandated 阶段的 Added 从该阶段边界内的任务绑定规则创建事件核对；一对属性/规则算一项，
  不把 6 项重复算成 12 个事件。返回 `added_count_basis` 与 `added_event_refs` 保留来源依据。
  缺失阶段边界、缺少创建依据或结果引用无法核实时，Added 返回 `null`，现有界面显示横线。
  对已存在的旧缓存，这项修正查询时计算，无需重建索引或补写历史事件。
- 谱系节点读取缓存中的确切版本，提供真实名称、版本、定义、状态及 `detail_ref`。
  父/子标准可点击打开其保存版本；链接只改变当前详情，不清除已选阶段、搜索或分页。
  缺少原记录时明确显示“Record missing / 记录缺失”，保留引用供检查。
  新合并 child 的 `before=null` 仍表示创建；原父提案通过谱系展示和版本链接访问，
  不把父内容伪造成 child 的旧版本，也不补写合并历史。

补丁仅包含查询投影、界面选项/标签，以及四个相关回归测试。
不修改证据、资格、阈值、分数、既有规则或冻结记录。

## 已做的隔离验证

- 四个临时 SQLite journal/cache 测试通过：未冻结的工作集、冻结后的范围、
  冻结 v1 对后来 v2 的保真、Pending 分类、筛选先于分页、pool 旧版本和同版本旧阶段状态，
  mandated 六项新增、旧缓存即时修正和不可核实时返回未知，以及合并谱系的确切父版本、
  后来修订不会替换原定义、子版本链接和缺失记录标记。
- 只读历史缓存验证（`mode=ro; query_only=ON`）：

| 历史任务 | 原 active 总数 | Working 冻结启用数 | Pending 数 |
| --- | ---: | ---: | ---: |
| `…NQT22` | 97 | 11 | 88 |
| `…R0JQX` | 64 | 9 | 55 |

Working 的引用集合与原冻结 `entries` 完全一致。以上是只读列表计数，不是重新评估案例。
`…NQT22` 有 2 项同时属于启用集合和待复核集合，因此 11 + 88 不应与 97 作加总比较。
- 前端通过严格 TypeScript 检查和内存中的浏览器 bundle；未写入正在提供服务的 `dist`。
- 只读核对一个真实历史阶段行：表格 v1、base ID 原本打开 v4，使用补丁的 `detail_ref` 后正确返回 v1。
- 只读核对真实任务 `…D5XS1B` 的 mandated 阶段：原记录 before=0、after=6，
  结果 artifact `art_2106cf34bc6e` 的 6 个规则引用与阶段内 6 个创建事件完全一致。
  补丁读投影返回 Added=6，原缓存 Added=0 和源 journal 均保持原样；具体事件在 `validation.json` 中。
- 只读核对真实 child `cri_01M51GW2QDP58C6CYM8PA889PT@v1`：两条父引用均解析出
  “CSF1R engagement on record”的原 v1 定义和 merged 状态；点击目标返回相同版本与定义。
  新 child 的 merge 记录 `before=null` 保持不变，证据见 `validation.json` 的 `exact_lineage`。
- `git apply --check` 通过；运行中源码和产物的哈希保持不变。

详细结果见 [validation.json](validation.json) 和 [frontend-validation.json](frontend-validation.json)。

## 根任务确认运行结束后的应用步骤

在仓库根目录执行；先核对补丁上下文仍匹配。以下步骤尚未执行：

```powershell
git apply --check design_audit/workbench_redesign_2026-10-16/postrun_criteria_scope/working_criteria.patch
git apply design_audit/workbench_redesign_2026-10-16/postrun_criteria_scope/working_criteria.patch
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_working_scope_pins_frozen_versions_and_pending_filters_before_paging -q
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state -q
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_mandated_added_uses_created_bindings_and_repairs_legacy_cache_on_read -q
.\.venv\Scripts\python.exe -m pytest tests/test_read_model.py::test_lineage_nodes_resolve_saved_versions_and_preserve_new_child_history -q
npm --prefix web/client run build
```

之后由根任务重启展示服务并进行真实 GUI 验收：确认当前新任务的默认 Working 数量与最终冻结启用数一致；
Pending 仍可访问；搜索、翻页、刷新恢复和历史阶段筛选正常。无需启动科学工作流。

如上下文因后续修改不匹配，先审查差异；不要把 `proposed/` 文件整份覆盖当前源码。
