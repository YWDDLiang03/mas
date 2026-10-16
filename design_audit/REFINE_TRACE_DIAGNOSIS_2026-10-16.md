# Refine 耗时的只读机制诊断

本次只读取 `var/primary/store/store.db` 中 `run_01M50Q7SWTRAM3B7E1MHV0D8V7` 的 `agent.started/agent.finished` 和已验证为 proposer、`metadata.question = refine pool` 的 trace。SQLite 使用 `mode=ro`、`query_only=ON`。未读取 case、recovery、evaluator、排名、历史列表或 mapping；没有执行模型、文献检索、科研 stage，也未写真实 store 或调整 live 配置。下述时间为 journal 的 UTC 时间差。

## 已完成的两批证据

| 指标 | run seq 52 / `art_abf94850541a` | run seq 54 / `art_036d457c1fc5` |
|---|---:|---:|
| 条目数 | 20 | 14 |
| 开始→结束 UTC | 21:37:18.302→21:52:20.141 | 21:52:20.413→22:01:26.373 |
| 墙钟耗时，秒 | 901.84 | 545.96 |
| User prompt 字符数 | 167,426 | 181,358 |
| base / items / cited claims 字符数 | 24,666 / 123,276 / 19,434 | 24,666 / 120,427 / 36,215 |
| 单批去重后的 cited claims 数 | 53 | 87 |
| 初始→最终 max_tokens | 12,000→48,000 | 12,000→24,000 |
| trace 保存的 reasoning 段数 | 3 | 2 |
| 最终 JSON 字符数 | 86,917 | 29,419 |
| 最终 action 分布 | revise 20 | revise 3、withdraw 11 |
| 日志 usage input / output tokens | 60,838 / 19,995 | 109,150 / 31,372 |
| 最终 schema / truncated | 成功 / false | 成功 / false |

两个旧 trace 都没有逐次 `attempts` 或 `accounting`。`max_tokens_final` 和 reasoning 段数说明这不是一次普通 12,000 token 的完成；但这些旧记录不足以精确重建每次 provider 调用、每次截断或 schema repair 的费用。表中 usage 是当时事件所记读数，不能宣称包含所有尝试。没有输出模型 reasoning 内容。

## 可以核验的工程原因（运行中的归档实现）

1. `derivation_stages.BATCH['refine'] = 20` 按条目数量分批，没有输入字节预算。14 项的 prompt 比 20 项还大，说明仅减条目数无法稳定约束上下文。
2. 原 `derivation_stages._view` 原样放入完整 attribute 和 rule，`refine_stage` 再加 validator/critic findings 与整份 cited claim block。注册集输入含 registry 元数据，模型因而收到 `copied_from`、`inherited_by`、`proposed_by`、`status`、`version`、record ID/attribute ref 等无需重写的字段。仅两个对象内这些元数据约 21.4k / 15.6k 字符；同时 rule 内的 expected_change/falsification_test 又与外层重复。
3. 两批 attribute rationale 总计约 23.6k 字符，rule dissent 总计约 17.8k，critic findings 总计约 22.5k。证据和异议必须保留，但目前全量重述会叠加相同问题的解释。cited_block 已按 claim ID 去重，不能把重复检索当作此次主要原因。
4. `REVISER_SYSTEM` 和 `REVISION_SCHEMA` 只提供 revise/withdraw；`refine_stage` 让模型返回 proposal，然后合并旧 item 再校验。多数条目只是 critic findings 待处理，却要求整份 proposal 重写。第 1 批 20 项都重写，最终 JSON 86.9k 字符，超过初始 token 配额的实际风险已经发生。
5. `REVISER_SYSTEM` 继承整份 `PROPOSER_SYSTEM`，包含主动阈值提案指令；base_prompt 也包含完整 catalog 和 schema 说明。对于已有标准的定向修复，任务范围和重写成本都偏大。这是与代码一致的机制解释，无法仅凭两批记录估计各指令的独立因果贡献。
6. 第 1 批包含不能由现行 quantitative literature executor 执行的 categorical oral 文献条目。应继续明确 deferred/待审，不宜在每轮反复要求模型将其“修好”；将它改成无依据的定量指标并不能解决执行契约问题。未来的 task anchors protection 可避免研究 reduce 重写这类原任务锚点。

## 已实施的最小后续改动

在上述只读诊断之后，父任务授权后续进程采用以下两处源码变化：

- `_view` 现在只投影 `ATTRIBUTE_FIELDS` 与 `RULE_FIELDS`，另保留规则的 `applies_to_result_kind`、完整科学 `dissent`，保留 supporting claim IDs、falsification test 和非盲评时的 rationale/expected_change。将 pool/attribute/rule/source refs 与任务字段保留为紧凑 `refs`；不发送完整复制链、作者和审批元数据。原 store、pool item、来源/审批记录均不被修改。证据 route、证据种类和判定 basis、优先级、定义、方向、阈值、单位、变换和 bound_support 保持完整。
- 独立 `BATCH['refine']` 从 20 调整为 8；其余 stage 批量不变，仍遍历全部条目。完整 proposal 输出协议、merge 决策语义和科学阈值不变。

对上述两个已存 trace 的 notes 用当前 `_view` 离线投影，保持原 batch、base、claims 和 JSON 缩进，得到：

| 输入投影比较 | `art_abf94850541a` | `art_036d457c1fc5` |
|---|---:|---:|
| items 字符数：原→新 | 123,276→83,957 | 120,427→88,204 |
| items 减少 | 39,319（31.90%） | 32,223（26.76%） |
| 同批完整 prompt：原→新 | 167,426→128,107 | 181,358→149,135 |
| 同批完整 prompt 减少比例 | 23.48% | 17.77% |
| 后续按 8 切分的全部条目 | 8、8、4 | 8、6 |

这里重建的是旧 trace 中可用字段的投影，后续实际 prompt 还包含当前 pool/source 的紧凑 refs。supporting claim IDs 和 dissent 内容均核对未变；未生成新模型结果。字符减少不能当作实测 token、时间或费用下降，较小 batch 也会增加 base 的重复发送。

验证：`test_registered_reduction.py`、`test_criteria_pool.py`、`test_required_bindings.py`、`test_measurement_profile.py` 合计 **94 passed**（5.51 秒）。新增的两个定向行为验证覆盖：语义与证据不变/原记录不改/盲评不含 rationale，以及 19 个条目按 8、8、3 全部被处理。

当前运行中的 `run_01M50Q7SWTRAM3B7E1MHV0D8V7` 继续使用其启动时已归档的旧实现；此次源码只适用于后续进程，不能将现 run 的结果或耗时归因于新代码。

## 后续可选优化（未实施）

1. **继续根据实际大小控制成本。** 本次已完成确定性语义投影与较小固定批次。若后续需要进一步稳定上限，再按内容预算分批，保持全部条目与证据可用。
2. **修复只返回 patch。** 使用明确白名单字段的修订 schema，模型给 index、patch、reason、resolved finding refs。系统把 patch 应用到旧版本，再执行同样的 schema、证据、单位、bound_support、语义一致性校验；不允许模型改来源身份或制造审批。这减少重抄，并不放松校验。
3. **只把真正可修的问题送 refine。** 已知 unsupported executor 的条目明确 deferred，保留 evidence 和原因；已保护任务 anchors 不送研究重写。字段别名之类确定性变换由系统记录转换，科学含义变化继续交给复核。尚未解决的条目不能当作 pass 或隐藏在数量外。
4. **最后才按 prompt 字节/预计输出量分批。** 先投影、patch，再由内容预算分批，避免用固定 20 项代替实际成本约束。不要只提高 max_tokens、增加迭代或换更深推理来掩盖冗余。

以上可选项本次未做；没有更改此次 live process 的 prompts、batch size、模型配置或原 run 结果，也没有借 CQA 或排名选择科学标准、阈值或去留。
