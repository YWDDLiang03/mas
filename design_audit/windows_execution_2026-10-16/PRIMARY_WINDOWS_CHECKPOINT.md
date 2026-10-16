# Windows 实际运行记录 — 2026-10-16

状态：A 排名目标已达成；B CQA 恢复目标未达成。UI 重设计按用户顺序保留到验收目标完成后。

## 已完成的 A 读数

- 参考化合物：Surufatinib，InChIKey `TTZSNFLLYPYKIL-UHFFFAOYSA-N`。
- 排名：**5 / 50 个可排名候选**；完整候选全集 3,177。
- 偏好覆盖率：8/11 = 0.72727；扫描完整性 100%。
- `clears_hard_rules=true`，`clears_mandated_criteria=false`；必需受体已回答4/5，CSF1R未知，状态provisional。
- 运行：`run_01M50KR3WM3ZBFKF6Z83BW77EX`；榜单：`lb_task_01M50JQYYQAMPBQTQ0N8YNQT22_1`。
- 评分集：`rules@v1`（11条评分标准、93条注册标准）；测量配置：`art_dc699649c378`；冻结核验通过。
- 该读数是保留既有结果背景的描述性继承运行，非独立盲法验证，不把排名作为临床推荐。

## B 的固定读数与可比性

原task的4/11保持不变。新的93条标准固定快照由隔离evaluator评价一次：exact 0、near-equivalent 1、missed 10（1/11）。新case为assisted/descriptive_inherited。

一致性审计发现：旧4项near中，有3项所引标准四facets完全不变，但在新评价变为missed；剩余1项虽然标准变化仍为near。3个减少项均不能归因于标准实质变化，其中2项是既有near边界未充分定义、1项旧对应依据偏宽。两份记录都保留，不能据此声称系统恢复能力下降，也不能改写任何一个已封存读数。

## 实际工程修改与执行

- 原库通过SQLite一致性快照迁移到Windows，4,530,724,864 bytes，SHA256与源一致，quick_check=ok。
- 新增不可变测量配置，固定评分集、scope、配置/源码hash、seed、截止日、重放来源；排名门槛0.5，资格门槛1.0，资格不再挡住注册排名。
- Windows工作台支持显式启用的受管后台运行/机器裁决、真实PID、取消子进程、日志和退出码；默认只读。
- 历史工具成功结果精确重放；PubChem整行选列以本地派生方式记录，保留源artifact/hash与检索时间，不伪装成新检索。
- 恢复比较的一次性与固定pin检查已下沉公共入口；继承case传播暴露谱系；隔离agent记录真实agent身份。
- A实际通过本机工作台HTTP操作接口启动。IAB backend不可用，Windows UI工具因无法可靠确认URL停止；没有声称执行过GUI点击验收。

## 验证和资源

相关回归分别验证测量配置、原端到端流程、工具重放/投影、case继承、recovery guard和UI。最末相关组合为77 passed；UI23 passed；继承/恢复30 passed。并非声称全项目无误。

本次两次DeepSeek机器裁决共8,539 input tokens、21,099 output tokens，按配置公开峰值单价估计$0.027880（不是账户实际账单）。实际响应模型为deepseek-flash；请求使用获授权legacy flash别名。新排名没有LLM调用。

## 产物

- `primary_reading.json`：A的四组必要数字。
- `primary_board.json`：完整真实榜单与测量配置核验。
- `execution_manifest.json`：迁移、固定读数与状态。
- `derived_snapshot_comparison.json`：公开标准快照的可比性分析。
- `var/provenance/windows-primary-20261016/`：运行时源码zip、实现身份、测量配置。
- `var/primary/recovery/<new-task>/`：evaluator-only明细，只读counts/manifest等安全摘要；不进入Git公开文件。

本机工作台：<http://127.0.0.1:8766/>。8765为既有VS Code转发，未更改。
