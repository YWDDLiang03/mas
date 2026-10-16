# 离线测试 fixture 适配

本次只修改 tests，没有修改后台源码或当前运行的科学规则。调整解决测试依赖旧默认设置和旧界面边界的问题，不表示修复了新的产品算法缺陷。

原离线检查记录于 var/fresh-browser-20261016/offline-tests.log：631 passed、12 failed、15 deselected。

## 调整

- 文献并发与文档数下限测试显式使用 evaluation.mode=full、qualification.policy=legacy、evidence.mode=retrieve，继续验证实际读取 worker 数和每格文档下限。
- 校准降级测试显式选择 legacy，继续验证旧政策下 11/12 的淘汰比例、是否降为 preference、4/8 的 required 覆盖与排名边界。新资格政策仍只诊断、不会自动降级。
- Symbolic expression 端到端及其 UI fixture 显式选择 legacy/full/retrieve，继续验证旧流程的拟合表达式、留出验证与逐项解释。
- 仅两个调用 measurement.register 的 supplements 测试使用 test_measurement_profile.setup_task，去除与该 profile 检查无关、也未建立 anchor 的占位 T1。其他 supplements 测试继续使用原始 v1 setup_task，保留精确版本绑定和冻结不可修改的断言。
- CLI 文案断言适配现有“8 have incomplete mandated evidence and are not ranked”，继续要求准确的 floor、4/8 计数与缺失标准名称。
- UI 静态只读边界限定 legacy views/server/operations 和纯读投影模块。独立解释存储不再受“所有 UI 文件都不能写任何 store”的旧字符串断言约束。

## 实际边界验证

新增两个临时 SQLite 检查：

1. ReadModel 的 source connection 拒绝写表；sync 和 ReadAPI 读取成功，投影缓存保存 4 个候选，科学库完整 SQL 内容保持一致。cache 与 source 不能使用同一路径。
2. ResearchBriefService 拒绝科学库根目录及其祖先目录。使用本地 ScriptedAdapter 完成一次解释后，解释 artifact 只在独立 annotation store 出现，原科学 journal 和 artifacts 完整 SQL 内容均保持一致。

这里的模型是离线 ScriptedAdapter，没有真实 provider、网络请求或费用，也没有接触 primary store。

## 验证结果

目标子集为原 12 个失败项加上述 2 个边界项。首轮 12 passed、2 failed；剩余问题分别是 CLI 断言文案与新检查误写 fixture 候选数。定向修正后仅重跑这 2 项，结果 2 passed，1.23 秒。其余已通过检查未重复运行。

这次局部结果没有覆盖 supplements 共享 fixture 的其他使用者。随后主控全量复核得到 637 passed、8 failed、15 deselected（offline-tests-final.log）：前次全局替换 setup_task 使这些测试从 v2 开始，而 _bound_run 固定绑定 v1，导致一个预期 v2 追加断言和七个版本拒绝断言失效。这是此次测试修改引入的 fixture 回归，不能据前面的局部通过声称整个 suite 通过。

现已恢复通用 v1 setup_task，仅上述两个 measurement 场景选择清 T1 的 profile fixture。没有改成忽略版本或放宽 guard。完整重跑本次修改过的七个测试文件：test_bridge_and_parallel.py、test_calibration_guard.py、test_literature_sweep.py、test_supplements.py、test_symbolic.py、test_ui.py、test_workbench_evidence.py，结果 **117 passed，14.70 秒**。日志保存在 var/fresh-browser-20261016/offline-tests-fixture-subset.log。

该结果是七个文件的完整定向检查；全项目再次复核由主控单独记录。既有失败日志和局部执行记录均保留。

本次结束时后台 source SHA256：b7f38e2682426287c5fb7d0cdb5fcfefee901e6a3c6be86fb904a8c47db44476。只改测试，未改运行源码、规则、模型设置或真实科研记录。
