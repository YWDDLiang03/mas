# 结果前的 CQA 演化实例：logP 最佳区间

本记录仅涉及新任务 `task_01M52CBE5GYPK9F0MCZYBMPH84` 的标准演化与已保存原文。检查未读取候选结果，未调用模型，也未人工调整方向、阈值或排名。最终启用状态须以之后冻结的规则集为准。

跟踪对象：`cri_01M52ERBH5STHY9ZZXR1C9JSBM`。

| 版本 | 阶段 / 迭代 | 方向 | 比较字段 | 当时状态 |
|---|---|---|---|---|
| pool v1 | propose / 0 | within_range | `{"comparator":">=","unit":"log units","value":2}` | candidate |
| pool v2 | distill / 2 | within_range | `{"comparator":"range_membership","high":4,"low":2,"unit":"log units"}` | needs_refine |
| pool v3 | refine / 2 | lower_better | `null` | candidate |
| pool v4 | filter / 3 | lower_better | `null` | needs_refine |
| pool v5 | refine / 3 | within_range | `null` | candidate |
| pool v5 | promote / 0 | within_range | `null` | promoted |

v1 以原始 logP `>=2` 表示 `within_range`，缺少上界。实际纯评估反例表明，合成 logP=3 和 6 都得到 pass 及相同偏好贡献；原机械 readiness 没有阻断。结果前加入的通用检查只将缺少明确区间/目标距离执行合同的数值偏好判为未就绪，保留事实与原版本；它没有自动填入上界或修改候选结果。

v2 的 distill 明确指出缺上界，尝试写出 low=2/high=4，但使用了执行器不支持的 comparator。v3 的 refine 转为原值 `lower_better` 排序，并将最佳区间降为背景说明。该版本在机械上可执行，但没有新增支持“全域越低越好”的证据。

v3 唯一引用仍是 `claim_01M4YGKFT8T97H08A3RS5A2H24`，来自 DOI `10.3390/ijms27156590`、保存文档 `art_dcb8fb18db03` 的 `sec5.2.p3`。原文说明 logP 约 2–4 的平衡，并在同段指出过高 logP 伴随溶解度问题、过低 logP 则限制膜通透性。它不能单独建立无限制的 lower-is-better 平衡偏好。

v4 的第三轮 critic 指出了这一证据缺口，记录为 needs_refine。v5 恢复了 within_range，但仍没有可执行 cutoff 或 value_transform，机械 readiness 继续判为未就绪。此时不能把演化描述为“已正确实现 2–4 最佳区间”。

适合报告的结论是：**机械合同漏洞已在结果前阻断；科学解释的支持程度由后续复核分别处理，所有版本和理由保留。**

同性质检查仅覆盖这组 logP 项：当时 computed XLogP 的 band 候选也尚未就绪；RDKit logP 的单调候选引用的是脂溶性、难溶药物的食物增溶效应，适用条件仍须保留。没有冻结或候选评分时，不把多个提案直接称为重复计分；最终将按确切冻结 refs、quantity identity 和决策语义再核对，不仅凭名称合并不同算法或问题。

原始证据与运行级材料：

- `var/fresh-browser-20261016/raw-range-execution-proof.json`
- `var/fresh-browser-20261016/raw-range-readiness-patch/freeze-contract-proof.json`
- `var/fresh-browser-20261016/logp-source-support-before-results.json`
- `var/fresh-browser-20261016/raw-range-draft-trajectory.json`


截至 2026-10-16T15:12:31.946109+00:00，pool v5 已 promote 为注册提案：`attr_predicted-lipophilicity@v1`, `rule_predicted-lipophilicity@v1`。这是 pool 与 registry 两种版本体系，未将 v5 重标为 v1。注册提案仍不代表进入评分；其 range_membership 无 cutoff 的执行缺口须在冻结时明确延后。


最终冻结核对（仅规则，未读候选结果）：`rules@v1` 有 31 个执行条目、14 个 deferred。`rule_predicted-lipophilicity@v1` 因第三轮争议未解决而 withheld；`rule_lipophilicity-logp-within-optimal-kinase-inhibitor-range@v1` 因未声明可执行比较而 deferred。两者均未进入评分。只有 `rule_predicted-logp-rdkit@v1` 在 logP 项中启用，故此冻结没有多个 logP 条目同时计分；其食物效应来源的条件性限制仍应如实呈现，不能替代为已证的全域单调规律。

冻结中的硬规则仅为 documented oral administration，未使用 prediction route；五个原始靶点锚点均保留。证据：`var/fresh-browser-20261016/logp-freeze-pre-result-check.json`。这完成的是结果前的规则范围核对，新榜单数值和科学目标仍待完整结果审计。
