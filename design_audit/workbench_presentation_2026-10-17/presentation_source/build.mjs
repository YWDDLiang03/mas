import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import {loadImage} from '@napi-rs/canvas';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,'../../..');
const SKILL='C:/Users/admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const RUNTIME_NODE='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe';
const RUNTIME_NODE_MODULES='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const RUNTIME_PYTHON='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE=RUNTIME_NODE;
process.env.RUNTIME_NODE_MODULES=RUNTIME_NODE_MODULES;
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const draft=process.argv.includes('--draft');
const finalRequested=process.argv.includes('--final');
const score=JSON.parse(await fs.readFile(path.join(HERE,'data/score-details.json'),'utf8'));
const facts=JSON.parse(await fs.readFile(path.join(HERE,'source-facts.json'),'utf8'));
const assetFile=path.join(HERE,'assets.json');
const assets=JSON.parse(await fs.readFile(assetFile,'utf8').catch(()=>'{"settings":{"path":"../../../fresh-browser-20261016/browser/24-formal-settings-mid.jpg"}}'));
const FONT='Microsoft YaHei';
const C={ink:'#202D37',muted:'#53616B',blue:'#397DB1',light:'#EAF3F9',line:'#CFD9E1',white:'#FFFFFF'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const notes=[],tableOwners=[],chartOwners=[];
const S={
 design:'设计背景：MAS_MultiAgent_Design_Audit_EN_20261012/01_Concept_Overview_EN.md；design_audit/optimized_design.md §§5、8、9。具体功能按当前实现与下列实际记录解释，历史设计中的计划不作为已成功能力。',
 task:'实际任务：design_audit/fresh_browser_2026-10-16/results-snapshot2/task.json；task_01M52CBE5GYPK9F0MCZYBMPH84。此任务是reference_disclosed；生成阶段排除了明确提及参考候选的事实。',
 evidence:'事实来源：results-snapshot2/surufatinib.json 中 detail.evidence；原文、locator、claim/source hash及reading depth保留。事实manifest为'+facts.task.evidence_fact_manifest_ref+'。',
 cqa:'实际CQA：design_audit/fresh_browser_2026-10-16/results-snapshot2/cqa.json、source-cqa-history.json、stages.json；工作记录口径active_registered_plus_unregistered_proposals。',
 score:'实际评分复算：var/usability-score-20261017/new-suruf-score-details.json/.csv；snapshot='+score.snapshot_id+'；run='+score.run_id+'；rules@v2；source score='+score.source_score+'。',
 result:'独立核算：design_audit/fresh_browser_2026-10-16/audit/snapshot2-summary.md、snapshot2-audit.json；34/34检查通过。评估3177×31=98487单元；snapshot '+score.snapshot_id+'。',
 csv:'合成工程示例：design_audit/workbench_usability_2026-10-16/FINAL_ACCEPTANCE.md；var/workbench-usability/fixtures/carriers.csv与carrier-measurements.csv。数据明确为synthetic engineering fixture，不是实验证据。'
};
function text(s,value,x,y,w,h,size=28,bold=false,color=C.ink,align='left'){
 const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=String(value);sh.text.style={typeface:FONT,fontSize:size,bold,color,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};return sh;
}
function page(title,narration,source){
 const s=p.slides.add();s.background.fill=C.white;
 text(s,title,58,36,1164,74,42,true);
 text(s,String(p.slides.items.length).padStart(2,'0'),1170,678,54,25,17,false,C.muted,'right');
 s.speakerNotes.text=narration+'\n\n来源与口径\n'+source;
 notes.push({page:p.slides.items.length,title,narration,source});return s;
}
function para(s,content,y=124,h=100,size=29,x=60,w=1160,color=C.ink){return text(s,content,x,y,w,h,size,false,color);}
function table(s,rows,x=60,y=206,w=1160,h=350,widths,fs=25){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width:w,height:h,values:rows,columnWidths:widths});
 t.styleOptions={headerRow:true,bandedRows:false};t.borders.assign({fill:C.line,width:.7,style:'solid'});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.light:C.white;
  cell.text.style={typeface:FONT,fontSize:fs,bold:r===0,color:C.ink,verticalAlignment:'middle'};
 }
 tableOwners.push(p.slides.items.length);return t;
}
function caption(s,v,y=610,h=52){text(s,v,60,y,1150,h,23,false,C.muted);}
async function picture(s,key,x,y,w,h){
 const a=assets[key];
 if(!a?.path){if(finalRequested)throw new Error('Missing required final screenshot: '+key);text(s,'截图位置：'+key,x,y,w,h,27,false,C.muted);return;}
 const f=path.isAbsolute(a.path)?a.path:path.resolve(HERE,a.path);
 const bytes=await fs.readFile(f),d=await loadImage(bytes),crop=a.crop??{left:0,right:0,top:0,bottom:0};
 const vw=d.width*(1-crop.left-crop.right),vh=d.height*(1-crop.top-crop.bottom),sc=Math.min(w/vw,h/vh);
 const contentType=bytes[0]===0xff&&bytes[1]===0xd8?'image/jpeg':'image/png';
 s.images.add({blob:new Uint8Array(bytes),contentType,alt:a.alt??key,fit:'contain',position:{left:x+(w-vw*sc)/2,top:y+(h-vh*sc)/2,width:vw*sc,height:vh*sc},...(a.crop?{crop:a.crop}:{})});
}
function chart(s,categories,values,x,y,w,h){
 const c=s.charts.add('bar',{position:{left:x,top:y,width:w,height:h},categories,series:[{name:'工作记录',values,fill:C.blue}],barOptions:{direction:'column',grouping:'clustered',gapWidth:65},hasLegend:false,chartFill:'none',plotAreaFill:'none',
  xAxis:{textStyle:{fontSize:21,fill:C.ink},line:{fill:C.line,width:1}},yAxis:{min:0,max:2000,majorUnit:500,textStyle:{fontSize:19,fill:C.muted},majorGridlines:{fill:C.line,width:.7},numberFormatCode:'0'},
  dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0',textStyle:{fontSize:23,fill:C.ink}}});
 applyPresentationChartFont(c,{fontFamily:FONT});chartOwners.push(p.slides.items.length);return c;
}
function num(v,n=4){return v==null?'缺证':Number(v).toFixed(n).replace(/0+$/,'').replace(/\.$/,'');}
const short={
 'CSF1R curated potency':'CSF1R 效力','FGFR1 curated potency':'FGFR1 效力','VEGFR1 curated potency':'VEGFR1 效力','VEGFR2 curated potency':'VEGFR2 效力','VEGFR3 curated potency':'VEGFR3 效力',
 'Molecular weight (Da)':'分子量','Predicted logP (RDKit)':'RDKit logP','Predicted BRENK alert count':'BRENK 结构警报','Predicted NIH alert count':'NIH 结构警报','Predicted PAINS alert count':'PAINS 结构警报',
 'Predicted blood-brain barrier penetration probability (BBB_Martins)':'血脑屏障渗透概率','Predicted CYP1A2 inhibition probability':'CYP1A2 抑制概率','Predicted CYP2C19 inhibition probability':'CYP2C19 抑制概率','Predicted CYP2C9 inhibition probability':'CYP2C9 抑制概率','Predicted CYP2C9 substrate probability':'CYP2C9 底物概率',
 'Oral bioavailability (human, measured F%)':'人体实测 F%','Time to maximum plasma concentration (Tmax, median of reported values)':'人体实测 Tmax'
};
const pref=Object.fromEntries(score.contributions.map(x=>[short[x.name]??x.name,x]));
function scoreRows(names){return [['偏好','实际值','证据类型','比较分 d','总分贡献'],...names.map(name=>{const c=pref[name];if(!c)throw new Error(name);let v=c.assessed_value==null?'缺证':num(c.assessed_value)+(c.unit==='pChEMBL'?' pChEMBL':c.unit==='Da'?' Da':c.unit==='count'?' 个':'');return [name,v,{measured:'实测汇总',derived:'结构计算',predicted:'模型预测',absent:'缺证'}[c.determination_basis],c.desirability==null?'不计':Number(c.desirability).toFixed(4),c.final_score_contribution==null?'不计':Number(c.final_score_contribution).toFixed(5)];})];}
if(score.contributions.length!==17||score.score_denominator!==15||Math.abs(score.score_numerator/15-score.source_score)>1e-12)throw new Error('Score source contract changed');
if(score.contributions.some(c=>c.weight!==1)||score.qualified_cohort.length!==10||score.rank!==1)throw new Error('The displayed equal-weight cohort contract changed');
if(Math.abs(score.contributions.reduce((a,c)=>a+(c.score_numerator_contribution??0),0)-11.38888888888889)>1e-12)throw new Error('Displayed score sum changed');
if(facts.candidate.qualification_record.hard_passed!==1||facts.candidate.qualification_record.required_direct_answered!==5)throw new Error('Displayed qualification facts changed');

{
 const s=page('MAS 研究工作台','这份汇报先介绍一次研究的完整流程，再说明各组件如何交换任务、证据、标准和结果，最后用最新的口服多靶点研究走完相同流程。研究者可以从候选结论回到逐项结果、实际采用的证据和保存的原文。',S.design+'\n'+S.result);
 text(s,'流程、组件与一次完整研究',60,178,1160,95,45,true);
 para(s,'研究目标与候选库输入后，系统建立有证据来源的标准，\n完成审查、逐项评估和排序，并保存修改理由与未知项。',326,150,32);
 text(s,'实例：单一口服药物的多靶点研究',60,533,1160,52,30,false,C.blue);
 caption(s,'2026 年 10 月 17 日',622);
}
{
 const s=page('完整研究流程','工作流程有八个阶段。研究者先指定目标、候选和材料。系统固定证据，提出标准，通过批评、修订和合并形成工作集。审查与冻结明确本次使用哪些规则。随后系统逐项读取候选事实，先判资格再排序。结果包含未解决项、来源位置和完整导出。修改标准会保存新版本，并据此建立新的评估结果。',S.design+'\n'+S.task+'\n当前流程：README.md Research workbench。');
 table(s,[['阶段','输入与处理','产物'],['1 设置与任务','目标、条件、范围、候选库','结构化任务'],['2 证据准备','固定来源、事实与可用工具记录','可回查的事实集合'],['3 标准提出','按研究维度提出属性及用途','候选标准（CQA）池'],['4 批评与提炼','检查、明确、修订、合并','带谱系的当前工作集'],['5 审查与冻结','处理争议，核对可执行规则','固定评估方案及延后清单'],['6 逐项评估','为候选读取事实并应用规则','值、判定、原因和证据'],['7 资格与排序','先满足门槛，再计算偏好分','合格榜与待补清单'],['8 回查与继续','看原文、改标准、补充材料','新版本和新结果快照']],60,132,1160,493,[225,560,375],25);
}
{
 const s=page('任务输入与规范化','规范化组件将用户原话转换成明确的任务字段。实际任务要求单一口服药物，并同时涉及五个靶点。口服是明确硬条件，五个靶点构成必须回答的范围。靶点效力可以排序，但任务没有给出统一数值截点。自有数据的性质、条件或单位无法准确对应时，工作台提出具体问题，用户补充回答后继续。',S.task+'\n实现：src/mas/core/investigation.py task normalization；上传任务按property catalog核对。');
 para(s,'“寻找可口服、同时涉及 CSF1R、VEGFR1、VEGFR2、\nVEGFR3 和 FGFR1 的单一药物。”',128,107,31);
 table(s,[['原始要求','规范化后的用途','输出'],['口服给药','硬条件','有明确产品或人类临床口服记录'],['五个靶点','必需研究范围','每个靶点均要有直接证据'],['更合适的药理性质','排序偏好','从证据提出可比较的性质'],['含糊的性质或条件','待回答问题','具体补问后重新核对']],60,270,1160,300,[300,340,520],26);
 caption(s,'输出固定研究范围，后续标准与评估都引用这一任务版本。',606);
}
{
 const s=page('证据集合与候选库','候选库定义评谁，证据集合定义依据什么。本轮从空CQA开始，复用已固定的事实与历史工具结果。生成阶段排除了明确提及参考候选的事实；任务仍披露参考候选及研究范围，采用披露参考候选身份的口径。候选评估按同一事实政策处理全库，保留原来源及证据类别。',S.task+'\n'+S.cqa+'\n本轮evidence stage：claims_reused=3021、criteria_copied=0、documents_read=0、new_searches=0。');
 para(s,'候选库定义评谁，证据集合定义依据什么。',130,54,31);
 table(s,[['材料','包含的内容','本轮处理'],['候选库','稳定身份与可读名称','固定 3,177 个药物'],['文献事实','发现、数值、单位、条件与原文位置','复用已保存材料'],['工具事实','登记字段、测量、结构计算或预测','保留原方法与版本'],['标准生成材料','按目标与研究维度分配事实','排除明确提及参考候选的事实']],60,220,1160,322,[240,520,400],26);
 caption(s,'本轮复用既有文献与计算记录，CQA 从空集合重新建立。',588);
}
{
 const s=page('一条证据记录','以保存文献中的一条测量为例。原文报告sulfatinib对FGFR1和CSF-1R的IC50分别为34和5nM。系统为两个靶点分别保存结构化事实，并保留同一段原文与位置。这里展示FGFR1的34nM；最终候选值按冻结标准与其他合格记录汇总，在案例后段列出具体计算。该原文是体外激酶实验，实验条件的缺项继续保留。',S.evidence+'\nFGFR1 claim_supp_0fc07290141d48a811fe3d11；source src_doi_10.1038/s42004-023-01084-0；locator sec2.1.p1。原文alias sulfatinib保留。');
 para(s,'“sulfatinib demonstrated potent inhibition of FGFR1 and CSF-1R,\nwith IC50 values of 34 and 5 nM, respectively”',129,116,29);
 table(s,[['记录字段','FGFR1 例子'],['研究对象与性质','Surufatinib，FGFR1 的 IC50'],['值与单位','34 nM'],['实验背景','体外激酶实验，条件缺项继续保留'],['原文位置与来源','期刊论文的已保存段落'],['后续使用','按标准转换与汇总，连同原始记录回查']],60,287,1160,306,[300,860],26);
 caption(s,'原文报告、计算使用的数值与研究解释分别保存。',620);
}
{
 const s=page('提出、批评与裁决的分工','Proposer根据任务与事实提出属性、用途、来源路线和检验想法。Critic检查证据支持、单位、适用性、重复及反例，给出具体问题。Proposer再回应可修的问题。Adjudicator处理持续争议或来源解释，记录接受、拒绝或未解决的理由。确定性校验负责格式、引用及执行定义，模型同意也要经过这些检查。实际分子量项经历了经验线解释与复核，该决定保留为机器审查记录。',S.design+'\n'+S.cqa+'\nMW相关：rule_molecular-weight-da@v1；machine review adj_01M52MB0NDN2S5WEDHXP14CPJ8。');
 table(s,[['角色','收到什么','做什么','交回什么'],['Proposer','任务、事实与属性模板','提出属性、规则并修订','提议与依据'],['Critic','提议及其可引用材料','指出支持、条件或反例问题','具体发现与处理建议'],['Adjudicator','争议、原文和解释','核对推断及适用性','决定、理由与剩余争议']],60,143,1160,297,[210,300,360,290],26);
 para(s,'分子量例子：500 Da 来自经验范围。\n批评后，修订明确其偏好用途与适用性，再由机器复核。',491,116,30);
}
{
 const s=page('属性与决策规则','CQA在这里是研究中需要测量和判断的性质。属性记录测什么、单位、条件、证据路线和汇总方法；规则记录怎样比较及怎样处理缺失。以分子量为例，结构计算得到Da数值，冻结规则把500Da经验线用于偏好。CSF1R没有数值截点，但有明确连续排序方向，仍可执行。',S.cqa+'\n分子量attribute/rule_molecular-weight-da@v1；CSF1R attribute/rule_csf1r-curated-potency@v1。');
 table(s,[['内容','分子量实例','CSF1R 实例'],['属性是什么','结构计算分子量','直接效力测量的 pChEMBL'],['单位与汇总','Da，按声明的中位数汇总','pChEMBL，中位数'],['规则用途','偏好','偏好，兼具必需范围绑定'],['比较方式','≤500 Da 的阈值比较','越高越优的连续排序'],['缺失处理','保留缺证状态','缺直接证据阻断本任务资格']],60,143,1160,410,[250,445,465],26);
 caption(s,'CQA 指研究中需要判断的性质。属性定义测什么，规则说明怎样使用。',600);
}
{
 const s=page('CQA 池的提炼操作','提出阶段先保留有依据的候选想法，提炼阶段逐项处理。Filter核对是否已有标准覆盖、是否有支持和有效读取路线，再由Critic批评。Distill明确性质、方向和适用范围。Refine回应已记录的问题。Merge把同一量和用途的提议合成一个项并保留来源谱系。未解决的内容在池内或审查区继续保留。',S.cqa+'\n当前操作定义：src/mas/core/derivation_stages.py propose/filter_stage/distill_stage/refine_stage/merge_stage。');
 table(s,[['操作','作用','一个具体例子'],['Filter 检查','识别缺支持、无效路线及已有覆盖','已注册靶点效力覆盖相同测量提议'],['Distill 明确','把宽泛表述变成具体测量','logP 区间提议补出 2–4 上下界'],['Refine 修订','回应单位、来源或解释问题','分子量经验线补明适用依据'],['Merge 合并','整合同量、同用途的提议与来源','多个分子量提议合成一个项']],60,147,1160,365,[245,460,455],26);
 para(s,'每次修改、合并和移除都有理由，原提议与父版本仍可查。',558,80,29);
}
{
 const s=page('实际谱系：分子量的合并与修订','最新研究第二轮合并了六个分子量提议，测量性质、路线、单位和方向一致。它们对经验线和汇总方式有不同表述，合并项保留来源，并明确按中位数汇总实际值。这里合并的是提议及来源，候选的实际值按声明方法另外汇总。第三轮Critic指出反例支持不足。Refine补充经验解释与适用性，机器审查随后接受这条偏好线。每一步都保留父项、版本和理由。',S.cqa+'\n六父项与merge child cri_01M52KSFQBB9B84Y16HNPGBCM2@v1；filter@v2、refine@v3；最终attr/rule_molecular-weight-da@v1。支持claim_01M4YGKFS9V8MZAS1VB9ACXDYD等3条；machine bound interpretation granted。');
 table(s,[['阶段','发生了什么','保存的结果'],['第二轮 Merge','六个同量/用途提议整合来源','合并提议与六个原提议关联'],['第三轮 Critic','追问反例与经验线的依据','具体发现和待修问题'],['第三轮 Refine','明确 500 Da 为偏好经验解释','新版本、引用和适用说明'],['审查与冻结','核对解释及支持记录','机器复核接受后启用']],60,144,1160,355,[225,545,390],26);
 para(s,'候选结构计算值为 480.6 Da。数值汇总与提议合并分别记录。',555,75,29);
}
{
 const s=page('硬条件、偏好与参考项','用途决定一项标准怎样影响结果。口服记录是任务明确要求的硬条件；靶点效力和结构性质作为偏好，帮助合格者排序；Food-AUC等参考项提供背景。五个必需靶点的直接证据要求单独核对。参考项有数值和有可执行判读方法也分别记录，四项已有预测值的参考仍等待判读方法。',S.cqa+'\n'+S.score+'\ncontext状态说明：design_audit/fresh_browser_2026-10-16/audit/context-method-explanation-fix-proof.json。');
 table(s,[['用途','实际例子','有值后怎样使用','缺失的影响'],['硬条件','明确口服给药','核验是否满足要求','本例阻断资格'],['必需范围','五个靶点的直接证据','逐个确认范围已回答','进入待补证据'],['排序偏好','效力、分子量等','比较分进入加权平均','保留缺证与覆盖率'],['参考项','Food-AUC 等','显示值、条件和判读状态','保留参考缺项']],60,144,1160,365,[210,270,350,330],25);
 caption(s,'连续偏好有值后参与比较，硬条件另作资格判断。',570);
}
{
 const s=page('审查与冻结','冻结将当前工作标准转换成一次评估固定使用的规则集。它核对任务要求、来源和单位、比较方式、边界解释及未解决复核，输出启用项和延后清单。实际logP提议原称2到4最佳区间，却一度只有大于等于2；后续修订的依据与执行定义仍未一致，因此两条最佳区间提议最终没有进入这次评分。它们的失败版本和理由仍在。',S.cqa+'\ndesign_audit/fresh_browser_2026-10-16/cqa-logp-evolution.md；pool cri_01M52ERBH5STHY9ZZXR1C9JSBM；rule_predicted-lipophilicity与rule_lipophilicity-logp-within-optimal-kinase-inhibitor-range最终deferred。');
 table(s,[['冻结核对','输出'],['任务要求是否完整绑定','固定硬条件与必需范围'],['测量和单位是否可执行','确切属性、规则及证据路线'],['阈值和解释是否有支持','来源、适用性和审查理由'],['争议和未完成定义是否结清','启用或明确延后']],60,143,1160,300,[600,560],27);
 para(s,'logP 实例：描述 2–4 最佳区间，原提议只写 ≥2。\n后续定义与支持仍未一致，最终进入延后清单。',489,123,30);
}
{
 const s=page('工具执行与证据类型','工具组件接到标准的具体问题，再读取相应候选事实。读取结果携带单位、输入、方法、实现版本及来源。记录中的实测、结构计算和训练模型预测分别保留。实际四个RDKit描述符原被统一标成预测，复核算法后用新版本改为结构计算；原数值、方向、阈值和旧快照均保留。同量有直接证据时优先使用，预测辅助偏好。',S.evidence+'\nADMET-AI 2.0.1官方physchem源码审阅与机械迁移：scripts/correct_descriptor_basis.py；tool_compute_admet_descriptors implementation admet-ai-2.0.1-rdkit-descriptor-projection-1。');
 table(s,[['类型','实际例子','证据含义'],['实测或整理的测量','靶点 IC50、pChEMBL','保留实验来源、单位和条件'],['确定性结构计算','分子量、RDKit logP、结构警报计数','从分子结构按固定算法计算'],['训练模型预测','CYP 抑制概率、BBB 概率','保存模型输出及方法版本']],60,146,1160,300,[310,450,400],27);
 para(s,'缺少工具、读不到事实或单位与条件不匹配时，\n结果保留具体未知原因。',493,119,30);
}
{
 const s=page('逐层筛选与两种评估模式','筛选首先核对适用且经过审查的硬条件和必需直接证据。明确硬失败进入淘汰；缺证、冲突或未解决硬审查进入待补；没有有效硬条件时为未就绪。分阶段模式（staged）只在确认硬失败后跳过后续昂贵评估并记录原因；未知仍继续检查其他门槛。合成载体例子中C的细胞活率55%低于80%硬要求，随后四格明确跳过。该例已经离线核对完整模式（full）和分阶段模式的合格集与排序一致。',S.csv+'\n规则语义：src/mas/core/assessor.py qualification；Controller staged skip。载体示例15cells，staged实际11evaluated+4skipped。');
 table(s,[['当前事实','资格状态','后续处理'],['硬条件直接通过，必需证据齐全','合格','计算全部可用偏好'],['硬条件有明确直接失败','淘汰','分阶段记录原因并跳过后续项'],['硬条件或必需证据缺失、冲突','待补','继续检查其他门槛，列出缺项'],['缺少适用且已审查的硬条件','未就绪','先完成硬条件定义与审查']],60,147,1160,330,[490,190,480],26);
 para(s,'合成载体 C：细胞活率 55% < 80%，明确淘汰，后续 4 格跳过。',513,75,29);
 caption(s,'完整模式评完全部单元。分阶段模式节省硬失败后的工作，保留跳过原因。',620);
}
{
 const s=page('偏好分数与直接证据覆盖率','阈值偏好按通过或失败给1或0。连续偏好先在有值的合格候选中排序，换成0到1的经验分位；并列取平均位置，比较组包含该项有值的合格候选。分数用有可用值的偏好加权平均。直接证据覆盖率另算，分母包含全部适用偏好。实际BRENK中两个候选更差、八个候选并列，比较分为0.611111，对本轮总分贡献0.040741。NIH和PAINS都是十个候选同为零，各比较分0.5。',S.score+'\n冻结ranking_coverage_floor=0.5；qualified_tied_empirical_percentile；所有17偏好权重均为1。n=1时实现比较分为1。');
 para(s,'连续偏好比较分 d = [较差候选数 + (并列候选数 − 1) / 2] / (n − 1)',133,66,29);
 para(s,'n 为该项有值的合格候选数，并列取平均位置',194,35,23,60,1160,C.muted);
 para(s,'最终分数 = Σ(w × d) / Σ(有可用值的 w)',258,58,30);
 para(s,'直接覆盖率 = 直接证据权重 / 全部适用偏好权重',339,57,30);
 table(s,[['BRENK 实际算例','计算'],['n=10，2 个更差，8 个并列','d = (2 + 3.5) / 9 = 0.611111'],['本轮可用偏好权重合计 15','对总分贡献 = d / 15 = 0.040741']],60,423,1160,167,[530,630],27);
 caption(s,'本轮直接覆盖须达到 50% 才排位，预测仅辅助分数。',624);
}
{
 const s=page('研究者工作台','工作台把任务输入、持续进度、标准历史、候选结果与证据回查放在同一个研究上下文。用户切换页面后仍能看到当前阶段和活动。暂停在活动边界保存状态；标准编辑保留新版本，历史快照继续可读。阶段轨道显示当前活动与已完成阶段。研究者可以进入标准历史核对变化，或从候选逐项结果进入实际证据。','实际UI记录：README.md Research workbench；design_audit/fresh_browser_2026-10-16/UI_REVIEW.md；最终截图见assets.json。');
 await picture(s,'workbench',60,131,1160,454);
 caption(s,'常驻阶段与活动进度；标准历史、候选结果和证据在同一任务中连接。',607);
}
{
 const s=page('实例起点：口服多靶点研究','最新实例从浏览器Settings和New research开始。配置均为mid，四个并发工作者。候选库有3177个药物。口服是硬条件，CSF1R、VEGFR1、VEGFR2、VEGFR3和FGFR1是必需范围。新任务没有继承旧标准，固定证据后重新提出CQA。原输入披露Surufatinib为参考候选；生成排除明确提及它的事实，候选评估仍按统一规则。',S.task+'\n配置原始截图24-formal-settings-mid.jpg；正式科学运行记录费用约$4.2101，费用记录保持。');
 text(s,'研究目标',60,143,430,45,31,true);
 text(s,'单一口服候选\n同时涉及五个靶点\n\n候选库 3,177 个药物\n标准从空集合开始',60,214,445,262,30,false);
 await picture(s,'settings',530,135,690,420);
 caption(s,'本轮配置均为 mid，4 并发，复用固定已有证据。',611);
}
{
 const s=page('实例中的标准展开与三轮提炼','初始6项任务绑定包含五靶点与口服。按目标覆盖、口服相关性质、代谢稳定性和安全性提出1911条提议，加上任务绑定达到1917工作项。三轮提炼后依次剩147、68和53个当前工作项。这里每个数量都采用同一工作记录口径，含尚待处理的记录。数量变化可回到具体修改、合并和移除，例如前述分子量六父合并。',S.cqa+'\n精确stage after：0,6,293,504,1192,1917,1373,1337,291,147,109,97,78,68,63,62,53,53；promote=53。');
 chart(s,['起点','任务绑定','目标覆盖','口服性质','代谢稳定','安全性','第一轮后','第二轮后','第三轮后'],[0,6,293,504,1192,1917,147,68,53],60,139,1160,414);
 para(s,'1,917 = 6 项任务绑定 + 1,911 条提议',575,53,29);
 caption(s,'口径为当前注册标准与未注册提议合计，含待处理项。',636,30);
}
{
 const s=page('实例中的冻结方案','最终53个工作项包括45个已注册和8个未注册提议。本次评估启用31条，即1个硬条件、17个偏好与13个参考。其余22个没有进入评估，包括14个已注册延后和8个未注册待处理。5个未解决复核是14中的子集。延后原因包括执行定义不完整和审查未解。最佳logP区间与机制engagement项给出了具体例子。',S.cqa+'\nvar/fresh-browser-20261016/frozen-criteria-summary.json/.csv；53refs唯一。规则集rules@v2保留同样计数，四描述符仅版本迁移。');
 table(s,[['当前用途或状态','数量','这次怎样处理'],['硬条件','1','评估口服要求'],['排序偏好','17','其中有值项用于分数'],['参考项','13','显示观测及判读状态'],['已注册延后','14','9 项执行定义未全，5 项审查未解'],['未注册待处理','8','保留问题与原提议']],60,142,1160,373,[320,140,700],27);
 para(s,'31 条启用 + 22 条待处理 = 53 个当前工作项',561,54,29);
 caption(s,'5 项审查未解属于 14 项已注册延后标准。',630,31);
}
{
 const s=page('实例中的口服与必需靶点证据','口服硬条件由保存的人类临床给药句支持。句中的250mg是给药信息，是否口服的判断来自明确的orally表述及候选归属。五个必需靶点都有直接测量记录，任务范围5/5已回答。表中的pChEMBL是按冻结属性汇总的值，有的来自多条测量。它们进入效力排序；本任务把这些效力值用于排序，未设置统一的效力硬阈值。',S.evidence+'\n口服示例claim_01M52QZFZHBESVFSHMK8TX8AGV，DOI10.1080/07853890.2026.2698360，sec2.3.p1。'+S.score);
 para(s,'“In both cohorts, surufatinib was administered orally\nat 250 mg once daily.”',129,100,29);
 table(s,[['必需靶点','汇总效力（pChEMBL）','证据'],['CSF1R','8.3010','直接测量'],['VEGFR1','8.8500','直接测量'],['VEGFR2','7.6800','直接测量'],['VEGFR3','9.0000','直接测量'],['FGFR1','7.6443','4 条直接记录汇总']],60,278,1160,303,[330,420,410],26);
 caption(s,'口服要求 1/1，五靶点直接记录 5/5，实验条件随来源保留。',617);
}
{
 const names=['CSF1R 效力','VEGFR1 效力','VEGFR2 效力','VEGFR3 效力','FGFR1 效力','分子量','RDKit logP','BRENK 结构警报','NIH 结构警报'];
 const s=page('实例评分明细：靶点与结构性质','这张表列出17个偏好中的9个。每项权重都为1。总分贡献为该项标准化比较分除以15。五个靶点按合格且有值者计算分位数。分子量480.6Da满足500Da偏好线，所以比较分为1。RDKit和结构警报是确定性计算。BRENK有八人并列，因此比较分为0.6111；NIH的十个候选同为零，比较分为0.5。准确值、路线和每条原始观察都在附带评分表和保存记录中。',S.score+'\n'+names.map(n=>pref[n].rule_ref).join('\n'));
 table(s,scoreRows(names),60,137,1160,438,[285,235,200,200,240],24);
 caption(s,'本轮权重 w 均为 1；总分贡献 = w × d / 15。',609);
}
{
 const names=['PAINS 结构警报','血脑屏障渗透概率','CYP1A2 抑制概率','CYP2C19 抑制概率','CYP2C9 抑制概率','CYP2C9 底物概率','人体实测 F%','人体实测 Tmax'];
 const s=page('实例评分明细：预测与缺证','这张表列余下8个偏好。五项模型预测参与辅助分数，但不增加直接证据覆盖。F%和Tmax缺证，保留在适用偏好的17项分母中；它们不进入本轮有值项的分数分母。15个有值项的比较分合计11.3888888889，除以权重总和15得到0.7592592593。直接证据另有10项，除以17得到58.82%，高于冻结的50%排位要求。',S.score+'\n'+names.map(n=>pref[n].rule_ref).join('\n'));
 table(s,scoreRows(names),60,131,1160,385,[285,235,200,200,240],24);
 para(s,'分数 = 11.3888889 / 15 = 0.7592593',543,46,30);
 caption(s,'直接覆盖率 = 10 / 17 = 58.82%　　5 项预测仅辅助分数',605,48);
 caption(s,'表中数值四舍五入，最终总分按原精度计算。',651,27);
}
{
 const s=page('实例结果与保留的首次记录','最终3177个候选中10个合格并排名，3167个待补证据，明确淘汰和未评估均为零。Surufatinib排名1/10，分数0.7593。首次保存结果有6个合格候选，均未达到排位要求；Surufatinib的直接偏好覆盖为6/17，约35%，因此没有名次。后续纠正了已有事实复用与四个结构描述符的证据分类，另存第二快照。硬条件、权重和覆盖要求未改。排名表示当前冻结标准下的研究优先级。',S.result+'\n首次snapshot1保留：direct6/17；最终snapshot2 direct10/17；所有旧artifact hashes核对。');
 table(s,[['候选状态','数量','结果含义'],['合格并排名','10','硬条件及必需证据齐全，达到排名覆盖'],['待补证据','3,167','列出缺失或未解决的要求'],['明确淘汰 / 未评估','0 / 0','按本次固定方案记录']],60,144,1160,251,[320,180,660],27);
 para(s,'Surufatinib：1 / 10，分数 0.7593',430,63,34);
 para(s,'首次快照：6 个合格、0 个排位，Suruf 直接覆盖 6/17。\n纠正已有事实复用与描述符分类后，第二快照直接覆盖 10/17。',525,106,27);
 caption(s,'当前冻结标准下的研究优先级。部分结构偏好的用途依据较间接。',647,30);
}
{
 const s=page('结果怎样回到来源','候选逐项结果连接实际采用的证据，证据再连接保存的原文和上下文。FGFR1汇总采用四条记录：34nM原文转换为pChEMBL约7.4685，另有7.82、7.82及7.2800，按中位数得到7.6443。新的证据分组将测量数值、结构计算和支持研究用途的文献分开展示。部分结构偏好的用途依据较间接，研究者可以据此判断下一步验证。',S.evidence+'\n'+S.score+'\nFGFR1 raw values:[34nM,7.82pChEMBL,7.82pChEMBL,7.28000020980835pChEMBL]；34nM转换=-log10(34e-9)；median=7.6442605414788725。');
 await picture(s,'evidence',60,119,1160,531);
 caption(s,'原文、34 nM 发现与实际评估关联',652,27);
}
{
 const s=page('自有数据与下一步研究','自有数据入口接受稳定候选ID及逐条观测，保留性质、值、单位、条件和来源。合成载体示例里，粒径来自DLS条件，细胞活率是硬要求，递送效率用于排序，表面电荷只有记录要求而无方向偏好。上传的依据类型保留用户的声明。药物实例后续可补人F%、Tmax和Food-AUC，明确四项参考的判读方法，并检验间接结构偏好的研究价值。交付包括可编辑汇报、讲稿、完整候选、评分明细及标准和证据历史。',S.csv+'\n原药物未知项与context状态：'+S.result);
 table(s,[['自有测量字段','合成载体例子'],['候选 ID、性质与数值','DEMO-A，粒径，100 nm'],['实验条件','DLS，水分散液，25 °C'],['来源及位置','上传文件与行号，明确标注合成来源'],['标准用途','活率硬条件，粒径与递送效率排序，电荷参考']],60,144,1160,297,[350,810],26);
 para(s,'药物研究下一步：补 F%、Tmax、Food-AUC 证据，\n明确参考项判读，并验证间接结构偏好的实际价值。',488,117,29);
}

await fs.mkdir(path.join(HERE,'preview'),{recursive:true});
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(HERE,'preview',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(HERE,'slide-notes.json'),JSON.stringify(notes,null,2)+'\n');
await fs.writeFile(path.join(HERE,'content.final.json'),JSON.stringify({created:'2026-10-17',title:'MAS研究工作台：流程、组件与一次完整研究',slides:notes,sourceScore:score,assets},null,2)+'\n');
const candidatePath=path.join(HERE,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
if(!draft){
 const stamp=Date.now(),finalPath=path.join(HERE,'final-output',`finalized-${stamp}-MAS_研究工作台_流程组件与实例_20261017.pptx`),receiptPath=path.join(HERE,`validation-${stamp}.json`);
 await fs.mkdir(path.dirname(finalPath),{recursive:true});
 const result=await finalizePresentation({workspaceDir:ROOT,candidatePath,finalPath,pythonExecutable:RUNTIME_PYTHON,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  explicitTotalSlideCount:24,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:chartOwners,materializeLiteralChartWorkbooks:true,
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath});
 await fs.writeFile(path.join(HERE,'latest-finalized.json'),JSON.stringify({finalPath,receiptPath,...result},null,2)+'\n');
 console.log(JSON.stringify({slides:p.slides.items.length,finalPath,sha256:result.finalSha256}));
}else console.log(JSON.stringify({slides:p.slides.items.length,candidatePath,draft:true}));
