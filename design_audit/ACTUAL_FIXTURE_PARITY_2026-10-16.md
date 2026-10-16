# 真实历史事实上的 full / staged 局部一致性

**结果：通过。** 固定 4 名真实候选、5 条原任务所需目标的排序规则，并实例化原任务明确写出的口服硬条件。full 与 staged 的资格状态、合格集合、合格顺序和分数一致。

| 指标 | full | staged |
|---|---:|---:|
| 处理记录数 | 24 | 24 |
| 实际评估单元 | 24 | 19 |
| 确定拒绝后跳过 | 0 | 5 |
| qualified | 2 | 2 |
| rejected | 1 | 1 |
| pending | 1 | 1 |
| 缺失/冲突单元 | 3 | 1 |

两名已知口服候选具备全部所需目标值；非口服候选有 3 个所需目标值；途径未知候选具备全部所需目标值。staged 对非口服候选确定拒绝后跳过其 5 个偏好单元，保留原因与处理记录；途径未知者继续评估全部目标。缺失数与跳过数分别报告。

证据来源为已完成的 `run_01M50X7EYSBXPDCP0SG859666R`（固定至 seq 112236）与已存在的 `var/primary/universe_chembl.json`。复用了 **110 条 source claims**；**18 个非空历史目标值**经当前 assessor 聚合后与原 assessment 数值一致。对两名合格候选另用独立的成对百分位算术核算等权分数，得到 0.0 与 1.0，与两次临时运行一致。

该历史 run 冻结的 9 条 scoring rules 全为 preference。此次验证的口服 gate 来自原任务的字面 hard constraint，规则为 `oral == true`；它在临时 store 中通过确定性的 `task_constraint_restated` 路径确认，没有人为添加数值阈值或专家审批。候选按事实可用性、口服状态和稳定 ID 选取，不使用历史排名。

适用性假设：口服状态取固定库的记录字段，沿用现有适配器语义——没有 first_approval 时的 false 仍作 unknown。记录字段作为局部工程验证的给药途径代理，不能据此独立确认每种临床方案的口服适用性。目标单位、方向、聚合和所用 claims 保持不变；临时比较采用等权偏好百分位。

结论限定于这份真实数据夹具上的执行模式一致性。新的 GUI 输入规范化、CQA 生成、完整文献流程及全库排序仍由新 workflow 的实际结果另行验收。源历史政策和旧榜单没有被重新解释为新政策结果。

运行方法（项目目录）：

```powershell
.venv\Scripts\python.exe design_audit\verify_actual_fixture_parity.py
```

脚本只以 SQLite `mode=ro` 和应用写保护读取 primary；所有新 profile、规则确认和 assessments 写入自动清理的临时 store。网络入口被禁止，模型 roster 为空，临时 journal 核对 model activity 为 0。脚本保留源 artifact/hash、实际候选、规则、claim 来源和后端关键文件 hash，见 `actual_fixture_parity_2026-10-16.json`。
