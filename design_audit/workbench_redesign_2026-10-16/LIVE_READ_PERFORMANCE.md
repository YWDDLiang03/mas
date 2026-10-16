# 实际运行中的读取性能观察

工作流 `wf_b2743fc600ca463c88c337fcfc30cdb1`；任务 `task_01M517XWKC3EMVGNK0RD06C5SS`；生成运行 `run_01M517Y8KEYDK6JTTPJ4HD663K`。

冻结后端源码 SHA-256：`3e08789394f1f67705143e41988fcede9c3ba82d073deab7692706436343c93d`。观察只使用 GET 与源库 SQLite `mode=ro`，未修改源码、主库、设置或启动额外模型调用。

采样时间为 2026-10-16T02:18:40.333+00:00 与 2026-10-16T02:19:40.637+00:00，间隔至少 60 秒；每个接口每组请求两次。两次工作流均为 `running / propose`。

| 查询 | 就绪缓存直接调用基线 P95（毫秒） | 运行中 HTTP 最小（毫秒） | 运行中 HTTP 最大（毫秒） | HTTP 样本数 |
|---|---:|---:|---:|---:|
| Overview | 5.543 | 22.551 | 40.399 | 4 |
| Criteria page | 4.595 | 5.505 | 30.901 | 4 |
| Stages | 4.493 | 4.939 | 22.280 | 4 |
| Snapshots | 3.458 | 4.779 | 30.543 | 4 |
| Candidates page | 4.932 | 4.824 | 25.716 | 4 |
| Evidence page | 5.213 | 6.807 | 28.996 | 4 |

基线来自 [read_model_benchmark.json](read_model_benchmark.json)，为直接调用读取模型的 50 次样本；本次是包含 HTTP 处理的运行中小样本，两个口径分别保留，不把小样本最大值当作 P95。

两次 source tail 与查询投影水位均为 `1261078`，投影 `ready=true`、`error=null`。六类接口全部成功，最大观察 HTTP 耗时为 **40.399 毫秒**；未发现查询阻塞。

新增事件到查询可见的延迟在本观察窗口内没有形成可测样本：两次间隔内没有新的源事件提交。最后事件为 `agent.started`，记录时间 `2026-10-16T02:16:34.541Z`。JSON 中该事件到采样时已可见的宽上界只是事件年龄，不用于宣称投影传播耗时。

运行费用采用工作流 API 的已记录状态：{"used_usd": 0.0025857, "limit_usd": 10.0, "cost_status": "recorded_estimate"}。该快照不推测进行中的请求最终费用。

详细请求时间、返回大小、行数与水位见 [live_projection_observation.json](live_projection_observation.json)。本观察已结束；付费研究继续由主任务负责。
