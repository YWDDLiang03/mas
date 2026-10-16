# Qualification-first 语义核对与候选页披露

核对仅依据代码、仓库计划和上层实现合同，没有读取候选结果、排名或 sealed 内容，没有运行模型/B，也没有改后台规则、评分或真实 store。

## 判定结论

当前 `qualification_first_v1` 有两层不同的门槛：

1. **资格**：至少存在适用且已核验的 hard condition；适用 hard conditions 必须有直接证据通过，未结清 hard review/缺失/冲突继续阻断；所有 required-scope rules 必须有直接证据。五个 target anchors 虽是 preferences，也处于后一项要求中。缺少 target 证据给 pending，不是数值 hard Fail；有 potency 值也不等于达成某个未声明 potency cutoff。
2. **排位**：必须 qualified 且有可计算 preference score，并达到冻结的 `ranking_coverage_floor`。本轮 workflow 使用设置值（当前计划为 0.5）；它是直接偏好证据的加权覆盖率，范围为全部适用 preferences。预测可辅助 score，但不增加直接证据覆盖率分子。

所以 **qualified、有 score、position=null 是现有实现允许的状态**。例如仅作结构性说明：五个 required target preferences 都有直接证据、hard condition 通过，另有六个辅助预测 preferences，均等权时直接偏好覆盖为 5/11，低于 0.5。这个例子没有使用真实候选或建议改门槛，只说明新增辅助预测可能扩大分母、影响可排位性。

本轮固定 anchors 结构中，五个 required target direct 要求已经使其 mandated coverage 达到 1.0，因此 `rank_requires_mandated_coverage=True` 基本重复该资格要求。它不把五项 preference 改写成 potency 数值硬阈值。将来若 mandated 集与 required-scope 集不同，两套集合需再次明确对照。

代码依据：

- `core/investigation.py` freeze 分支：`ranking_coverage_floor=settings['rank.coverage_floor']`、`eligibility_mandated_coverage_floor=1.0`、`rank_requires_mandated_coverage=True`。
- `core/controller.py::_finish`：从 frozen `required_binding_check.scope_bindings` 形成 required rule refs；调用 `assessor.qualification`；限定 qualified-only percentile population。
- `core/assessor.py::qualification`：`missing_direct_required_rule_refs` 阻断资格，与 hard Fail 分开。
- `core/assessor.py::preference_scores`：直接证据权重/适用 preference 总权重为覆盖率；score 按有可用值项计算。
- `core/leaderboard.py::build_snapshot`：资格、score、一般 preference coverage floor 和 mandated coverage 的最终排位筛选；记录 `rank_note`。

## 计划依据与实施选择

仓库 `AGENTS.md` 已批准流程写的是“先执行硬条件筛选，再对合格候选排序”；没有逐字规定“所有 required preference 必须有直接证据”。

本分工最初收到的上层实现合同明确写了“新运行硬条件已核验且所有 task required 有直接证据才主榜排名”，后续接口合同又提出“>=1 applicable 有效 hard（非预测）及 mandated 直接证据”。因此当前实现符合该技术合同；此前将其直接称作“用户已明确批准全部 required direct”是过强表述，不能用实现本身当作用户逐字批准的证据。

本次核对后，根任务明确选择：该任务同时涉及全部五靶点，保留 required target 直接证据要求，并在 UI 单独披露它与 hard 阈值的区别；保持 0.5 排名覆盖条件，不根据候选结果改规则。这是本轮明确记录的实施口径。更改这两层门槛应使用新的 prospective profile/binding，不能改写历史结果；本次没有进行任何后台政策修改。

## 已完成的 UI 修正

仅修改 `web/client/src/pages/CandidatesPage.tsx` 和必要 `api/types.ts`：

- 原 “Required criteria” 计数实际来自 `hard_passed/hard_total`，现准确标为 **Hard conditions / 硬条件**。
- 新列 **Required target evidence / 必需靶点证据**，使用 API 已有 `mandated_coverage`；详情优先显示原记录中 `raw.qualification.required_direct_answered / required_total`，并列出可解析的缺失标准名称。
- **Direct preference coverage / 直接偏好证据覆盖** 仅使用 `preference_coverage`，不再用 hard coverage 替代。
- 列表与详情显示 API 已有 `rank_note`；qualified 但没有 position 时，仍给出明确的未排位说明，避免有资格即必有名次的误读。
- 新政策提示区说明 required evidence 缺失与 hard Fail 的区别、available preference 不是 hard Pass，以及预测不增加直接证据覆盖。排名 floor 从选中 snapshot 的已有 reporting tuple 读取，不在前端硬编码 0.5。
- legacy 页面保留历史政策提示，不套用新的 direct-evidence 解释。

API 剩余边界：现有 CSV fields 没有 `rank_note`，所以 CSV 可能只导出 generic qualification reason；本次 UI 授权范围未改导出 API。若需完整导出未排位原因，应由 API owner 将已有 `rank_note` 纳入 CSV。

验证：`npm run build`（`tsc --noEmit && vite build`）通过；包括 root 已稳定的 ProgressRail/Criteria 页面改动。构建 JS 为 `index-C1yrFAHZ.js`。本次未读取实际候选页结果，不能将编译验证描述为真实榜单 GUI 验收。
