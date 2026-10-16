# 演示文稿来源

当前汇报共26页：正文24页，评分附录2页。正文以流程、反馈回路、判定分支、标准演化和分数构成解释研究；四处界面截图分别用于进度、榜单、证据与CSV导入。

`content.final.json` 保存每页主旨、讲稿、衔接和来源。`build.mjs` 生成可编辑流程图、图表和表格；`data/score-details.json` 保留原精度评分输入，`source-facts.json` 保留案例材料。图表工作簿按12位有效数字写入，图中标签另按显示格式舍入；最终分数与完整CSV使用原始精度。

## 重新制作

在仓库根目录创建 `var/ppt-build/`，将本目录的 `build.mjs` 复制进去；在该临时目录将 `node_modules` 链接到 bundled Node.js packages。设置 `MAS_PROJECT_ROOT` 为仓库根目录，用 bundled Node.js 执行临时脚本。加 `--final` 会进行最终导出；请将 `MAS_PPTX_OUTPUT` 设为一个新的完整文件路径，避免覆盖已交付文件。整个过程读取固定材料，不运行科研模型。

完成后删除临时目录里的候选PPT、完整渲染图与依赖链接，保留本目录和最终交付文件即可。
