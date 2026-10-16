# Windows 最终验收 — 2026-10-16

**本轮按用户调整后的目标完成。** A 为 Surufatinib **5 / 50 rankable，3,177 总候选**；五项指定靶点证据齐全，偏好覆盖 8/9。B 为固定的 assisted 描述读数 **1/11**，按软指标报告。标准保留 59 条注册 + 5 条未注册待处理，9 条进入本次评分。

[最终报告](FINAL_ACCEPTANCE_2026-10-16.md)记录结果、实际 GUI 验收、真实故障与修复、设计分析、费用和可复现身份。

- [当前英文结果页](http://127.0.0.1:8769/leaderboard?task=task_01M50Q5EZE12GGDES5QNWR0JQX&snapshot=lb_task_01M50Q5EZE12GGDES5QNWR0JQX_1)
- [完整 GUI 下载 CSV](../../var/acceptance-mid/browser-leaderboard.csv) · [完整 JSON](../../var/acceptance-mid/leaderboard.json)
- [最终执行清单](final_execution_manifest.json) · [最终 A/B 摘要](mid_reading.json)
- [实际 GUI 验证](gui_verification.json) · [榜单离线复算：0 differences](leaderboard_replay.json)
- [实际来源转换和聚合](supplement_cell_trace.json) · [费用估计记录](cost_record.json)
- [最终 UI 源码身份](final_ui_implementation.json) · [UI 新增显示名的数值不变检查](post_evaluation_display_check.json)

原 A 保留在 [primary_reading.json](primary_reading.json)、[primary_board.json](primary_board.json) 和 [execution_manifest.json](execution_manifest.json)，没有覆盖为新结果。原报告与中间检查点见 [PRIMARY_WINDOWS_CHECKPOINT.md](PRIMARY_WINDOWS_CHECKPOINT.md) 和 [CHECKPOINT_BEFORE_FINAL.md](CHECKPOINT_BEFORE_FINAL.md)。

当前最终服务端口为 8769；8765 仍是用户原有 VS Code 转发。研究结果保持 exploratory/provisional：口服硬条件待专家决定，其他缺失与失败均保留。
