# 评估前 quantity 与执行语义核验

任务 `task_01M51AQ0JK0MYN47806ZD5XS1B`。核验读取公共 task 注册、pool 支持与原始 claim；未读取候选评估、B 或 case。真实 source 只读，未执行规则修订或模型调用。

## 已证问题与待处理状态

源记录为 43 条当前注册、0 条冻结评分，43 条均无显式 quantity_id。最终评分集合尚未形成；本报告不将注册条目称为已评分结果。

| 标准 ref | 定义 | 当前执行 | 最小处理 |
|---|---|---|---|
| rule_predicted-acute-toxicity-ld50@v1 | log(1/(mol/kg))，却声称越大越安全 | higher_better、max，无变换；偏好方向反向 | 根代理已通过真实 GUI 排队 lower_better 修订；尚未应用，不由本脚本修改 |
| rule_multi-target-coverage-breadth@v1 | 五个靶点各自 median 的最小值 | 所有 route 原始值直接 pooled min；未按靶点分组 | 新 readiness patch 将此复合量 defer，独立靶点标准保留 |
| rule_relative-potency-across-required-targets@v1 | 五个靶点各自 median 的 max−min | 所有 route 原始值 pooled median；无 spread 运算 | 同上，保留原注册与理由，待有明确分组执行器再处理 |

`assessor.assess_cell` 将所有 usable claim 的 value 展平，仅执行 min/max/median；value_transform 也只作用于每个原始值。以纯合成的五靶数据 `[1,9] / [8] / [7] / [6] / [5]` 验证：目标 min-of-medians=5、spread=3，而现有 assessor 分别输出 1、6.5。未使用任何真实候选值。

## 直接与预测是否双计

确切关联对为 `rule_measured-human-plasma-protein-binding@v1` 与 `rule_predicted-plasma-protein-binding-rate@v1`：两者都声明 human plasma protein binding %、lower_better、无变换的 ordering；直接值采用 median，PPBR_AZ 预测采用 max。前者无 open review，后者仍 open review。

两者 quantity_identity 不同，因此当前 direct 优先逻辑不会把 PPBR_AZ 自动当作该直接量的缺证补充。其原因是无 quantity_id 时回退 evidence_key：literature 取 name+unit，其余取工具 routes。来源不同即得不同 key；代码没有语义量推断。

该对属于同端点而操作聚合仍有差别，需明确共享 measurand、物种/基质/条件与预测 fallback 聚合政策后再绑定，不能直接合并 median 与 max。最小一般性方向是为已证等价的量声明可审计的 quantity_id，并按相同条件约定 direct 优先、prediction 只补缺；此轮未写任何 identity 或科学版本。43 条中未找到完整执行量与决策合同完全一致的 direct/pred 配对，不声称已发生完全相同操作量双计。

其余相近配对保留差异：human F% 与 any-species F% 的物种及聚合不同；F% 与 Bioavailability_Ma 概率的量/单位不同；PubChem XLogP、RDKit logP、AstraZeneca 预测没有相同方法/条件证明；XLogP band distance 与 raw XLogP 的变换/用途不同。也不把 oral 硬资格与 oral preference 称为两个重复的 preference 票。

## 未应用补丁与验证

`post_run_multi_target_readiness.patch` 只对不同 target_chembl_id 数大于 1 的数值 preference 增加 readiness 检查。同一 target 的多数据库 route、五个独立任务靶点、oral gate 均保留。按实际不同 target 数检查，不按 route 数、标准 ID 或名称筛选。

显式 `aggregation_scope='pooled_observations'` 的合同是：既有 min/max/median 直接作用于原始观察集合，完全不声称按靶点汇总、成员齐全或计算 spread/ratio。此字段需显式声明并通过 schema 校验；补丁不会替当前两条复合量添加它。分组计算仍未实现，保留 deferred 理由与 target 成员。

补丁代码仅在内存执行，临时 Core 验证五个独立 anchors 与显式 raw pool 能冻结，两个无分组合同的复合量进入 deferred，原注册版本不变。真实 43 条只读对照，新增 defer 恰好上述两条；五个任务靶点与 oral gate 全不受影响。完整属性、规则、pool 支持、127 条原支持 claim、source catalog、ADMET 端点及验证记录见 `quantity_readiness_audit.json`。
