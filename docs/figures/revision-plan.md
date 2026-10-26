# 两张图的下一版执行方案

状态：修改方案已整理；现有PNG/PDF/PPT尚未按本方案重绘。本文采用[统一术语](../reference/terminology.md)和[通用准入规则](../reference/decision-language.md)。

## 总体组织

Figure 1说明通用医学研究工作台怎样运作；Figure 2说明当前保存案例得到了什么。通用区不出现口服、五靶点、3,177、50%或Surufatinib作为固定系统条件。案例区明确标注Recorded example。

保持英文、白底、浅蓝主色和纯色填充。所有文本、框、连接线与统计图保持可编辑。只画有具体对象或数据流含义的图形；不增加机器人、DNA、芯片等装饰。主图不出现C1/C2、任务ID、rules@v或开发模块名。

## Figure 1：TRIAGE workflow

### a. Criterion development

通用输入为Research objective、Candidate population和Evidence collection。主要路径为：

Research objective + Evidence collection → Proposer → Critic → Adjudicator → Evidence and definition checks → Frozen evaluation framework。

Critic到Proposer保留一条明确标为Review findings的反馈线；Proposer的职责写Draft and revise，Adjudicator写Merge or retain distinct criteria。记录卡仅保留Measure、Unit、Conditions、Source、Decision role。

固定框架中分三种用途：Mandatory requirements、Prioritization criteria、Contextual observations。指定必需观测是任务绑定条件，可同时落在排序标准上，用Required observations注释其绑定，不画成第四种互斥标准。

定义或审查未解决的条目从检查环节分支到Not used in this evaluation，副行Reasons and provenance retained。它位于固定框架之外。参考观察项仅连Interpretation，不连评分。

### b. Candidate assessment and prioritization

Candidate observations → Requirement assessment，随后有三个主要结果：

- Eligible：强制条件满足且必需观测可用，连接Weighted prioritization。
- Evidence incomplete：部分任务准入要求已有支持，其余缺口连到对应要求与来源。
- Excluded：两条原因线分别写Mandatory requirement not met和No admission support，指向具体要求与评估记录。

Assessment incomplete使用旁边的灰色执行提示；Criteria not ready放在框架准备阶段。它们不冒充第四、第五种科学性质结论。

Weighted prioritization → Score and evidence profile → Ranking coverage policy → Ranked candidates或Score reported; no rank。通用图只写saved coverage policy，不写50%。这一步处理已具备资格的候选，与Evidence incomplete使用独立分支。

图中如保留重新评估线，应标Additional evidence / new evaluation，并在图注明确它表示后续流程能力，未暗示当前案例进行了新检索。

### c. Recorded example

上行展示案例标准工作集：

**0 → 6 task requirements → 1,917 working items → 147 → 68 → 53 retained items**。

三轮收敛用一个括号标Three refinement rounds。0是空标准集，不是没有证据；6来自任务要求，不当作文献独立发现。最终53拆为18 enabled decision rules、13 contextual observations、22 items not used。18=1+17，31=18+13；22的9/5/8原因放图注。

下行将原来的六张巨大分子量卡片压缩成六张小记录卡：6 overlapping proposals → Merge and review → Molecular weight ≤500 Da。Surufatinib: 480.6 Da从独立观察框连到Criterion point = 1；旁注Structure-derived和One contribution to the weighted score。不能将此偏好阈值连到强制排除分支。

## Figure 2：Recorded oral multi-target study

### a. Eligibility and evidence completeness

输入3,177 candidates assessed，输出三个互斥分组：Eligible (10)、Evidence incomplete (1,305)、Excluded (1,862)。

- Eligible：口服要求满足，五项必需靶点观测齐全。
- Evidence incomplete：本例一部分准入要求已有依据，其余有缺口。
- Excluded：本例排除原因是No admission support；对应六项准入要求均无可用支持。

六项包括一个口服条件与五项观测要求。框内分别标注两类要求的满足数／可用数。采用等宽流程框；候选数量直接标数值。

口服×靶点观测完整性的另一种分组10／1,261／7／1,899放图注或补充资料；不要与1,305／1,862重复相加。

### b. Ranking of eligible candidates

保留十个候选的水平条形图，横轴Prioritization score，突出Surufatinib第1名。使用保存分数，不新造误差条或疗效概率。图注明确相同评估框架、合格比较集合、15项可用等权贡献。

### c. Surufatinib: eligibility and scoring evidence

准入部分分为Oral requirement: Met和Required target observations: Available, 5/5。五个靶点的对勾改为Available标签或有说明的观测标记，避免被读成药效阈值通过。效力数值标Recorded potency aggregates (pChEMBL)。

评分证据使用17格：Measured / curated (5)、Derived (5)、Predicted (5)、Missing (2)。前两组共同括到Direct-evidence coverage: 10/17 (58.8%)；另标本例Ranking floor: 50%。只有前两组进入覆盖分子，15个有值项进入评分平均。

初始6/17（35.3%）无排名与修正后10/17的历史放图注，不画成同一次最终评估的并行结果。

## 统一的连接语义

实线表示记录、观测或决策输入；虚线表示审查反馈或后续重新评估。框的颜色区分用途或状态，不替代文字定义。每个数量都标明集合：working items、decision rules、assessed items、candidates或scoring criteria。

## 英文图注工作稿

**Figure 1. TRIAGE develops evaluation criteria and prioritizes candidates for medical research.** **a,** A research objective and source-linked evidence guide criterion proposal, critique and adjudication. Evidence and definition checks establish a fixed evaluation framework. Mandatory requirements govern eligibility, prioritization criteria define comparisons, and contextual observations support interpretation. Items outside the evaluation retain their reasons and provenance. **b,** Candidate observations are assessed against task-specific requirements. Eligible candidates meet applicable mandatory conditions and provide the required observations. Evidence incomplete candidates have some admission requirements supported and retain links to the remaining gaps. A failed mandatory condition or no admission support produces exclusion, with the reason and affected requirements recorded. Execution status is recorded independently. Eligible candidates receive a score and evidence profile, and the saved coverage policy determines whether a rank is assigned. **c,** Recorded oral multi-target example. An empty criterion set receives six task requirements and expands to 1,917 working items. Three refinement rounds retain 147, 68 and 53 items. The final working set contains 18 enabled decision rules, 13 contextual observations and 22 items outside the evaluation. The molecular-weight example shows six overlapping proposals consolidated into one scoring criterion; the structure-derived value of 480.6 Da yields one criterion point under the ≤500 Da preference. Values and thresholds in c belong to this case.

**Figure 2. Surufatinib ranks first in the recorded oral multi-target evaluation.** **a,** Of 3,177 assessed compounds, 10 meet the oral-administration requirement and have direct observations for all five required targets. A further 1,305 candidates are partially documented; 1,862 are excluded because none of their admission requirements has usable support. The six admission checks comprise one oral condition and five observation requirements; no common potency cutoff is applied across the targets. **b,** Prioritization scores for the ten eligible candidates under the fixed framework. Surufatinib ranks first with a score of 0.7592592593. **c,** Surufatinib's eligibility evidence and scoring-evidence basis. Five target measurements or curated measurements and five permitted deterministic calculations provide direct coverage of 10/17 (58.8%). Five further criteria use predictions and two lack usable values. Fifteen equally weighted available contributions enter the score; all 17 applicable criteria enter the coverage denominator. The reference candidate was disclosed, and these panels describe saved computational results.

## 落图检查清单

1. 方法区中的疾病、靶点、候选数、阈值和参考药名全部来自显式案例区。
2. 中间态表示部分准入依据已具备；完成评估后无准入依据归入Excluded。
3. Excluded的原因连接具体强制失败或无准入依据；排序偏好显示各自的得分贡献。
4. 来源、标准用途、审查反馈和排序门槛均有明确连接，不使用装饰性无含义箭头。
5. 18／31／53、10／17／15等数量各自带分母含义。
6. 文本、箭头、数值可编辑，无渐变；缩放到论文双栏宽度后检查文字和细线可读性。

本轮交付为图示修改方案，正文保持原文件。
