# 可编辑汇报的制作来源

此目录保存本次九页汇报的文字、数据、截图和 JavaScript 制作代码。最终 PPT 的文字、表格和三张数据图为原生对象，截图使用实际浏览器记录。

- content.final.json：经独立核验的结果、标准计数、逐页讲稿和完整来源。不能用页面截图上的四舍五入数字替换原始数值。
- assets/：实际使用的五张截图。图片裁剪只改变显示区域，不改写截图内容。
- build.mjs：以 @oai/artifact-tool 生成及检查 PPTX。使用 Codex bundled Node、Python 和 presentation skill，字体为 Microsoft YaHei。

在原项目根目录重建前，需按 presentation skill 加载 bundled 依赖，并在本目录建立 node_modules 到其包目录的链接。用该 Node 运行本目录 build.mjs 即可。新候选文件、渲染及检查记录只落 var/fresh-browser-20261016/presentation-build；通过检查后再复制为交付文件。

最终内容来自 task_01M52CBE5GYPK9F0MCZYBMPH84、run_01M52Q4VRB00T5Z3QJW08SSV96、lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2。旧 snapshot1 的失败保留在备注，不因后续结果改写。载体 CSV 页面是已核验的合成工程示例。

公开交付不包含私有检查稿。普通内容修改可直接在演示文稿软件中完成；更改数据或研究结论仍须回到固定来源记录核对。
