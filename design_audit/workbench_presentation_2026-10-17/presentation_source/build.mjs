import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {loadImage} from '@napi-rs/canvas';
const ROOT=process.env.MAS_PROJECT_ROOT || process.cwd();
const BUILD=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const OLD=ROOT+'/design_audit/workbench_presentation_2026-10-17';
const SKILL='C:/Users/admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs'));
const score=JSON.parse(await fs.readFile(OLD+'/presentation_source/data/score-details.json','utf8'));
const facts=JSON.parse(await fs.readFile(OLD+'/presentation_source/source-facts.json','utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const FONT='Microsoft YaHei';
const C={ink:'#20313F',muted:'#647583',blue:'#367DA9',dark:'#255978',light:'#DFEDF6',pale:'#F1F6F9',line:'#CEDBE4',gray:'#DCE2E6',rust:'#B57843',white:'#FFFFFF'};
const notes=[],charts=[],tables=[];
const source='来源：本项目已保存的最新研究 task_01M52CBE5GYPK9F0MCZYBMPH84，snapshot2，rules@v2。完整材料：design_audit/fresh_browser_2026-10-16/results-snapshot2/；本汇报固定输入见 presentation_source/data。';
function txt(s,v,x,y,w,h,sz=28,bold=false,color=C.ink,align='left'){
 const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=String(v);sh.text.style={typeface:FONT,fontSize:sz,bold,color,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};return sh;
}
function rect(s,x,y,w,h,fill=C.light,stroke='none'){return s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1.3}});}
function line(s,x,y,w,h=0,color=C.line,width=2){return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width}});}
function node(s,v,x,y,w,h=76,fill=C.light,sz=27){
 const sh=rect(s,x,y,w,h,fill);
 sh.text=v;sh.text.style={typeface:FONT,fontSize:sz,color:C.ink,alignment:'center',verticalAlignment:'middle',wrap:'square',autoFit:'none',insets:12};return sh;
}
function arrow(s,a,b,from='right',to='left',color=C.blue){return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:color,width:2.2},tail:{type:'triangle',width:'sm',length:'sm'}});}
function caption(s,v,y=620){txt(s,v,60,y,1140,60,24,false,C.muted);}
function page(title,point,talk,bridge,ref=source){
 const s=p.slides.add();s.background.fill=C.white;txt(s,title,60,40,1160,80,42,true);
 const n=p.slides.items.length;txt(s,String(n).padStart(2,'0'),1174,677,46,28,18,false,C.muted,'right');
 s.speakerNotes.text=talk+'\n\n'+bridge+'\n\n'+ref;
 notes.push({page:n,title,point,talk,bridge,source:ref});return s;
}
async function pic(s,file,x,y,w,h,pxCrop){
 const bytes=await fs.readFile(file),im=await loadImage(bytes);
 const cr=pxCrop||[0,0,im.width,im.height],sc=Math.min(w/cr[2],h/cr[3]);
 s.images.add({blob:new Uint8Array(bytes),contentType:bytes[0]===255?'image/jpeg':'image/png',alt:path.basename(file),fit:'contain',
 position:{left:x+(w-cr[2]*sc)/2,top:y+(h-cr[3]*sc)/2,width:cr[2]*sc,height:cr[3]*sc},
 crop:{left:cr[0]/im.width,top:cr[1]/im.height,right:1-(cr[0]+cr[2])/im.width,bottom:1-(cr[1]+cr[3])/im.height}});
}
function chart(s,type,cats,series,x,y,w,h,max,opts={}){
 // Native chart workbooks use 12 significant digits; exact inputs stay in data/score-details.json.
 const chartSeries=series.map(item=>({...item,values:item.values.map(v=>Number(v.toPrecision(12)))}));
 const ch=s.charts.add(type,{position:{left:x,top:y,width:w,height:h},categories:cats,series:chartSeries,hasLegend:false,
 chartFill:'none',plotAreaFill:'none',barOptions:{direction:'column',grouping:'clustered',gapWidth:80},
 xAxis:{textStyle:{fontSize:23,fill:C.ink},line:{fill:C.line,width:1}},
 yAxis:{min:0,max,textStyle:{fontSize:20,fill:C.muted},majorGridlines:{fill:C.line,width:.7},numberFormatCode:'0'},
 dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:26,fill:C.ink},numberFormatCode:'0'},...opts});
 applyPresentationChartFont(ch,{fontFamily:FONT});charts.push(p.slides.items.length);return ch;
}
function table(s,rows,y,h,widths){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:60,top:y,width:1160,height:h,values:rows,columnWidths:widths});
 t.styleOptions={headerRow:true,bandedRows:false};t.borders.assign({fill:C.line,width:.7});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.light:C.white;cell.text.style={typeface:FONT,fontSize:24,bold:r===0,color:C.ink,verticalAlignment:'middle'};}
 tables.push(p.slides.items.length);
}
function flowItems(s,items,x,y,w=210,gap=65,h=86){
 const ns=items.map((v,i)=>node(s,v,x+i*(w+gap),y,w,h));ns.slice(1).forEach((n,i)=>arrow(s,ns[i],n));return ns;
}
function shareRow(s,total,direct,pred,missing,x,y,w=1020,h=48){
 [direct,pred,missing].forEach((n,i)=>{const prev=[0,direct,direct+pred][i];if(n)rect(s,x+w*prev/total,y,w*n/total,h,[C.blue,'#A8CDE3',C.gray][i]);});
}

// 01: Establish the decision, not a list of presentation sections.
{
 const s=page('MAS 研究工作台','先建立共同判断依据，再形成可回查的候选优先名单。','研究者最终要决定先验证哪些候选。MAS把这个决定拆成可检查的步骤：明确研究目标，依据证据形成标准，再判断候选资格和优先顺序。每个结论都保留回到标准和原文的路径。','先看这类研究为什么需要建立共同的判断依据。');
 txt(s,'先形成研究标准\n再筛选和排序',60,180,680,170,56,true);
 const a=node(s,'研究问题',80,440,230,85),b=node(s,'可执行标准',470,440,260,85,C.light),c=node(s,'候选优先名单',890,440,300,85,C.light);
 arrow(s,a,b);arrow(s,b,c);txt(s,'目标与证据',330,388,220,35,24,false,C.muted);txt(s,'资格与偏好',760,388,220,35,24,false,C.muted);
 caption(s,'口服多靶点研究实例 · 2026 年 10 月 17 日',613);
}
// 02: Explain why the criteria-building stage exists.
{
 const s=page('候选比较需要共同的判断依据','文献和工具给出不同性质的观察，必须先明确怎样比较。','同一项研究会同时遇到体外效力、临床给药记录、结构性质和模型预测。这些观察的单位、适用条件和用途不同。只有先明确哪些决定资格、哪些用于排序，候选之间的比较才有一致含义。','共同依据怎样建立，决定了后续整个流程。');
 const ys=[165,275,385],labels=['文献：体外 IC50、实验条件','记录：给药途径、研究对象','计算：结构性质、预测概率'];
 const inputs=labels.map((v,i)=>node(s,v,60,ys[i],410,78,C.pale,26));
 const criteria=node(s,'统一到研究问题\n明确性质、条件与用途',650,255,540,150,C.light,32);
 inputs.forEach(n=>arrow(s,n,criteria));txt(s,'这些观察回答的问题不同',60,510,470,50,29,true);
 caption(s,'研究目标：在满足要求的候选中，确定优先验证对象');
}
// 03: Full process and the feedback loop.
{
 const s=page('完整研究流程','标准先形成并固定，候选随后按同一方案评估。','流程从研究目标和固定证据开始。系统先充分提出候选标准，经过质疑、修改与合并形成工作集，再审查哪些标准可以执行。候选评估使用固定方案，先判资格再算偏好，最后给出结果及其来源。','首先需要把研究者的原话转成明确的要求。');
 const n=flowItems(s,['目标与证据','提出标准','批评与提炼','审查并固定'],60,190,225,70,100);
 const e=node(s,'候选评估',945,415,225,100),q=node(s,'资格与排序',650,415,225,100),r=node(s,'结果与来源',355,415,225,100);
 arrow(s,n[3],e,'bottom','top');arrow(s,e,q,'left','right');arrow(s,q,r,'left','right');
 arrow(s,n[2],n[1],'top','top',C.muted);txt(s,'回应问题，继续修订',345,126,470,35,23,false,C.muted,'center');
 txt(s,'输入',60,150,130,30,22,false,C.muted);txt(s,'输出',355,540,225,32,22,false,C.muted,'center');
 caption(s,'实质修改产生新版本；已保存结果仍能回查');
}
// 04: Show the task-to-requirement mapping spatially.
{
 const s=page('研究目标如何变成明确要求','口服是硬条件，五个靶点是必须回答的研究范围。','以口服多靶点研究为例。口服给药是明确的硬条件。CSF1R、VEGFR1、VEGFR2、VEGFR3和FGFR1要求都有直接证据，效力值再参与偏好比较。任务没有给出统一效力截点，系统因此保留连续排序的含义。','要求明确后，还需要把分散材料整理成可引用的证据。');
 txt(s,'寻找可口服、同时涉及五个靶点的单一药物',75,155,1130,85,36,true);
 const top=node(s,'原始研究目标',475,250,300,65,C.pale),hard=node(s,'口服给药\n硬条件',95,400,400,120),scope=node(s,'CSF1R · VEGFR1/2/3 · FGFR1\n必需直接证据',700,400,490,120,C.light,27);
 arrow(s,top,hard,'bottom','top');arrow(s,top,scope,'bottom','top');
 caption(s,'性质、单位或条件存在关键歧义时，再请求补充');
}
// 05: An actual evidence specimen, with annotations rather than a field table.
{
 const s=page('一条证据同时保留数值和实验背景','34 nM只有连同靶点、方法和来源，才有可使用的含义。','保存文献报告sulfatinib抑制FGFR1的IC50为34 nM。系统把靶点和数值分别绑定，并保留体外激酶实验、原文及段落位置。同一段还报告CSF1R为5 nM，两项分别记录，不能因为共享引文就混为一个测量。','形成事实记录后，多智能体才能讨论它支持什么样的标准。',source+'\n原文：DOI 10.1038/s42004-023-01084-0，sec2.1.p1；FGFR1绑定值34 nM。');
 txt(s,'Surufatinib → FGFR1',60,175,660,60,38,true);txt(s,'IC50',60,245,180,45,28,false,C.muted);txt(s,'34 nM',60,285,660,100,78,true,C.blue);
 line(s,60,385,660);txt(s,'体外激酶实验',60,418,610,42,31,true);txt(s,'ADP-Glo · 三倍稀释 · 三次重复',60,472,650,50,26);
 txt(s,'原文',840,165,360,35,25,true);txt(s,'“...potent inhibition of FGFR1\nand CSF-1R, with IC50 values\nof 34 and 5 nM, respectively”',840,220,370,185,25);
 txt(s,'同一句原文，两条靶点记录',840,456,370,76,27,true,C.blue);
 caption(s,'原文位置、实验条件和缺失条件随证据保存');
}
// 06: A change-producing feedback sequence.
{
 const s=page('多智能体通过反馈修改同一条提议','角色分工的作用体现在提议如何改变，以及争议是否被保留。','提出者先根据任务和事实给出标准。批评者追问依据和适用性，提出者再回应问题并修改。持续争议交给裁决角色，决定和理由一起保存。分子量例子中，500 Da最终被解释为偏好经验线；另一条logP提议则没有通过这一过程。','这些反馈必须落到明确的属性和决策规则中。');
 const a=node(s,'Proposer\n提出 500 Da 偏好线',60,185,330,115),b=node(s,'Critic\n追问经验线的适用依据',475,185,330,115),c=node(s,'Proposer\n补充解释与用途',475,430,330,115),d=node(s,'Adjudicator\n复核争议与来源',890,430,330,115);
 arrow(s,a,b);arrow(s,b,c,'bottom','top');arrow(s,c,d);arrow(s,c,a,'left','bottom',C.muted);
 txt(s,'需要回答的问题',870,190,350,40,25,true,C.muted);txt(s,'这条经验范围\n为什么适合当前用途？',870,245,350,110,32);
 caption(s,'接受、拒绝和未解决都保留理由；模型意见还需经过规则校验');
}
// 07: Distinguish measurement from its use.
{
 const s=page('CQA 与规则：测什么，怎样用','同一测量可以承担不同用途，执行时必须服从固定规则。','CQA在这里指研究中需要判断的性质。属性规定测量和汇总方式，规则规定怎样影响决定。本次分子量使用500 Da阈值偏好，满足即得比较分1；CSF1R使用连续排序。两个均低于500 Da的候选不会因这一阈值继续拉开分差。','提炼过程要把含糊或重复的提议整理成这样的完整定义。');
 txt(s,'测量与条件',70,155,470,55,32,true);txt(s,'固定决策规则',740,155,470,55,32,true);
 const a=node(s,'分子量\n结构计算 · Da',70,250,410,110,C.pale),b=node(s,'≤ 500 Da：比较分为 1\n阈值偏好',735,250,475,110);
 const c=node(s,'CSF1R 效力\n直接测量汇总 · pChEMBL',70,440,410,110,C.pale,26),d=node(s,'数值越高，比较分越高\n连续排序',735,440,475,110);
 arrow(s,a,b);arrow(s,c,d);caption(s,'CQA 定义研究性质；决策规则规定怎样使用该性质');
}
// 08: Each operation has a distinct effect, in a cycle.
{
 const s=page('提炼分别处理支持、定义、问题和重复','数量收敛来自具体处理，不来自单纯设定保留数量。','Filter先识别支持不足、读取路线无效或已有覆盖的问题。Distill把宽泛表述变成具体测量。Refine回应审查意见。Merge整合同一性质和用途的提议及来源。不同条件或不同决策含义继续区分，每次修改都能找到原提议。','分子量的六条提议提供了一个可回查的合并实例。');
 const n=flowItems(s,['Filter\n筛查','Distill\n明确','Refine\n修订','Merge\n合并'],60,260,225,70,120);
 ['核验证据支持','定义测量与范围','回应审查意见','整合同量同用途'].forEach((v,i)=>txt(s,v,60+i*295,430,225,110,27,false,C.ink,'center'));
 arrow(s,n[3],n[0],'top','top',C.muted);txt(s,'复核仍有问题的项，进入下一轮',340,160,590,55,29,true,C.blue,'center');
 caption(s,'原始提议、每次修订及合并去向均保留');
}
// 09: Real lineage, without inventing six different property labels.
{
 const s=page('分子量：六条提议合成一个判断项','合并整理的是提议和支持来源，随后还需修订与审查。','第二轮中，六条分子量提议在测量性质和用途上重合，因此合成一个项并保留父项来源。第三轮批评指出反例支持不足，修订补充500 Da的经验解释及适用性。机器复核接受后进入本次方案。候选数值的中位数汇总是另一项已声明计算。','合并后仍可能存在未解决问题，因此还需要冻结前审查。');
 txt(s,'第二轮合并',60,145,330,40,28,true);
 const leaves=[];for(let i=0;i<6;i++){const n=node(s,'分子量提议 '+(i+1),60,212+i*61,235,43,C.pale,23);leaves.push(n);}
 const m=node(s,'分子量\n来源与父项保留',425,315,300,110,C.light,29);leaves.forEach(n=>arrow(s,n,m));
 const r=node(s,'第三轮修订\n明确 500 Da 的偏好解释',885,220,335,115,C.light,27),f=node(s,'复核后启用\n≤500 Da 的阈值偏好',885,455,335,115,C.light,27);
 arrow(s,m,r);arrow(s,r,f,'bottom','top');
 caption(s,'候选结构计算值：480.6 Da；观测汇总按标准另行计算',646);
}
// 10: A concrete mismatch is more explanatory than a checklist.
{
 const s=page('比较方式不完整的提议暂缓启用','“2–4最佳”与“至少2”表达了不同判断，审查必须识别差异。','一条logP提议描述2到4的最佳区间，但曾只写了大于等于2。两者对大于4的候选给出不同解释。后续定义与支持仍未一致，所以这条最佳区间提议保留在待处理区。本次采用的另一个RDKit logP连续偏好是不同规则。','完成审查的标准固定下来，随后才能对所有候选应用相同判断。');
 const x=360,unit=160;
 txt(s,'logP 提议',60,135,250,45,27,true,C.blue);
 txt(s,'提议描述',60,210,250,45,30,true);txt(s,'2–4 最佳区间',60,265,260,55,27);
 rect(s,x+2*unit,237,2*unit,38,C.light);line(s,x,288,5*unit,0,C.muted);[0,1,2,3,4,5].forEach(v=>txt(s,String(v),x+v*unit-13,300,40,35,24));
 txt(s,'曾有的规则',60,405,250,45,30,true);txt(s,'只写 ≥2',60,460,250,55,27);
 rect(s,x+2*unit,432,3*unit,38,'#EADACA');line(s,x,483,5*unit,0,C.muted);[0,1,2,3,4,5].forEach(v=>txt(s,String(v),x+v*unit-13,495,40,35,24));
 s.shapes.add({geometry:'rightArrow',position:{left:1140,top:432,width:45,height:38},fill:'#EADACA',line:{fill:'none',width:0}});
 caption(s,'本例结果：暂缓启用，保留提议、修改过程与待解问题');
}
// Evidence execution keeps the provenance class attached to each value.
{
 const s=page('工具把标准变成候选的可用观测','读取、计算和预测的结果保留各自依据，缺证继续保持未知。','固定标准先确定需要什么性质、单位和条件，工具再寻找相应记录。已有测量、结构计算与模型预测分别保存。取得数值表示已有数据，是否满足硬条件仍需按规则判断。同一性质已有直接值时，预测保留为旁证。','取得这些观测以后，系统才能逐项判断资格。');
 const a=node(s,'实验与数据库\n例：靶点 IC50',60,165,365,100,C.pale),b=node(s,'确定性结构计算\n例：分子量、RDKit 警报',60,325,365,100,C.pale,26),c=node(s,'模型预测\n例：CYP 抑制概率',60,485,365,100,C.pale);
 const out=node(s,'逐项观测\n数值 · 单位 · 条件 · 依据',675,285,545,150,C.light,31);
 [a,b,c].forEach(n=>arrow(s,n,out));
 txt(s,'缺证或工具失败 → 记录具体未知原因',675,505,545,90,28,false,C.muted);
 caption(s,'同一性质已有直接证据时，预测只作旁证');
}
// 11: Actual decision tree, with pending distinct from rejection.
{
 const s=page('先判资格，再给合格者排名','硬失败、缺证和合格是不同结果，合格也可能暂时没有名次。','先检查已启用的硬条件，再检查任务要求的直接证据。明确硬失败才淘汰；缺证或冲突进入待补。满足资格后，偏好覆盖率决定能否排位。本轮五个靶点要求直接记录齐全，并没有额外统一效力截点。','资格解决能否进入比较，评分解决合格候选之间怎样比较。');
 const a=node(s,'有效硬条件\n已就绪？',60,180,230,95),b=node(s,'硬条件通过\n且必需证据齐全？',415,180,370,95),c=node(s,'合格',980,180,220,95);
 arrow(s,a,b);arrow(s,b,c);txt(s,'是',330,170,60,35,25,false,C.blue);txt(s,'是',866,170,60,35,25,false,C.blue);
 const na=node(s,'条件未就绪',60,430,230,80,C.gray),rej=node(s,'硬条件明确失败 → 淘汰\n缺证或冲突 → 待补',415,405,370,125,C.pale,26),rank=node(s,'覆盖达到要求 → 排名\n覆盖不足 → 暂无名次',905,405,315,125,C.light,25);
 arrow(s,a,na,'bottom','top',C.muted);arrow(s,b,rej,'bottom','top',C.muted);arrow(s,c,rank,'bottom','top');
 caption(s,'逐层模式：明确硬失败后跳过后续昂贵评估，并记录原因');
}
// 12: One formula worked through; coverage remains a separate gate.
{
 const s=page('分数说明相对偏好，覆盖率说明证据充分程度','分数和直接证据覆盖使用不同分母，不能混成一个指标。','连续偏好在合格且有值的候选中排序，相同值取平均位置。以BRENK为例，10个有值候选中2个更差、8个并列，比较分是0.6111。各项按权重平均得到总分。直接覆盖率另按全部适用偏好计算，模型预测不增加其分子。','这两种计算会在最新运行的首次结果和最终结果中产生可见差别。');
 txt(s,'一项偏好怎样变成分数',60,165,650,45,31,true);
 txt(s,'BRENK：0 个结构警报',60,245,620,48,30);
 txt(s,'10 个有值合格候选\n2 个更差，8 个并列',60,315,620,100,31);
 txt(s,'比较分 = (2 + 7/2) ÷ 9 = 0.6111',60,466,700,60,31,true,C.blue);
 line(s,810,170,0,370);
 txt(s,'另一个问题',870,170,350,42,27,false,C.muted);txt(s,'直接证据\n是否足够？',870,235,350,110,39,true);
 txt(s,'直接证据权重\n÷ 全部适用偏好权重',870,392,350,110,29);
 txt(s,'本次排位门槛：50%',870,540,350,44,26,true,C.blue);
 caption(s,'阈值偏好满足时取 1，不满足取 0；最终分数为有值偏好的加权平均');
}
// 13: A readable crop of the real running progress.
{
 const s=page('进度同时说明当前阶段和当前工作量','全流程阶段与局部批次进度要一起看。','实际运行画面中，目标和证据两个阶段已经完成，系统正在生成标准。当前安全性任务完成17个证据批次，共18个。局部94%的批次进度与全流程完成比例不同，研究者还可以查看最近活动与消耗。','用这个工作台，下面走完最新一次口服多靶点研究。',source+'\n截图：本次运行期间保存的24-formal-settings-mid.jpg，未重构界面。');
 await pic(s,OLD+'/presentation_source/assets/24-formal-settings-mid.jpg',60,150,1160,375,[278,8,942,303]);
 txt(s,'全流程：已完成 2 / 8 个阶段',60,565,610,55,32,true);
 txt(s,'当前工作：17 / 18 个批次',700,565,520,55,32,true,C.blue);
}
// 14: Fixed experimental setup.
{
 const s=page('本次运行：口服、多靶点、已有证据','这次重新形成标准，但不重新搜索文献或计算预测。','这次从浏览器Settings和新建研究开始，设置均为mid，四个并发工作者。候选库固定为3177个药物，输入事实集合包含3157条事实、164个来源。标准从空集合重新建立。任务披露Surufatinib为参考候选，生成阶段排除明确提及它的事实，候选评估仍采用统一方案。','空标准集会先展开，再通过数轮处理收敛。');
 txt(s,'单一口服候选\n同时涉及 CSF1R、VEGFR1/2/3、FGFR1',60,155,1150,110,37,true);
 const a=node(s,'3,177 个候选\n固定候选库',60,360,330,120,C.pale),b=node(s,'3,157 条事实\n164 个来源',475,360,330,120,C.pale),c=node(s,'空标准集\n重新提出与提炼',890,360,330,120,C.light);
 arrow(s,b,c);txt(s,'设置：mid · 4 并发',60,285,1050,50,29,false,C.blue);
 caption(s,'身份已披露；3,157 条事实中有 136 条点名参考候选，提议阶段排除这些事实');
}
// 15: Same denominator across growth and contraction.
{
 const s=page('标准先充分展开，再经过三轮提炼','工作记录由0增至1917，再收敛到53；数量下降需要具体理由。','开始时只有六项任务绑定。按研究维度提出1911条候选提议，总工作记录达到1917。三轮提炼后依次剩147、68和53个工作项。这一口径始终包含已注册标准和未注册提议，下一页再区分它们的最终用途。','53个工作项并不都参加筛选或评分。');
 txt(s,'提出阶段',60,135,540,40,29,true);txt(s,'三轮提炼',720,135,500,40,29,true);
 chart(s,'bar',['任务绑定','目标覆盖','口服性质','代谢稳定','安全性'],[{name:'工作项',values:[6,293,504,1192,1917],fill:C.blue}],50,195,620,355,2200);
 chart(s,'bar',['提炼前','第一轮','第二轮','第三轮'],[{name:'工作项',values:[1917,147,68,53],fill:C.blue}],710,195,520,355,2200);
 caption(s,'0 → 6 项任务绑定 + 1,911 条提议 → 53 个当前工作项；均采用同一计数口径');
}
// 16: Composition diagram.
{
 const s=page('53 个工作项中，18 条承担核心决定','18条核心标准、13条参考项和22条待处理项承担不同角色。','18条核心标准包括口服硬条件和17条偏好，五靶点已包含在偏好中。13条参考项保存观察和判读状态。22条未启用项中，14条已注册但延后，8条尚未注册。五项未解决复核属于14条延后的子集。','核心方案固定后，可以具体查看Surufatinib怎样通过资格核验。');
 const total=node(s,'53 个工作项',470,145,340,88);
 const a=node(s,'18 条核心标准',60,355,340,92,C.light,33),b=node(s,'13 条参考项',470,355,340,92,C.pale,33),c=node(s,'22 条待处理',880,355,340,92,C.gray,33);
 [a,b,c].forEach(n=>arrow(s,total,n,'bottom','top'));
 txt(s,'1 项硬条件\n17 项排序偏好',60,485,340,100,29,false,C.ink,'center');
 txt(s,'补充观察与判读状态\n不计入排序分数',470,485,340,100,27,false,C.ink,'center');
 txt(s,'14 项延后 + 8 项未注册\n保留原因与原提议',880,485,340,100,26,false,C.ink,'center');
}
// 17: Eligibility evidence and the five observed values.
{
 const s=page('Surufatinib 的口服与五靶点证据齐全','口服硬条件1/1通过，必需靶点直接证据5/5齐全。','人类临床记录明确写明Surufatinib口服给药，因此口服硬条件通过。五个必需靶点均有直接效力记录，覆盖要求也满足。图中为固定标准汇总的pChEMBL，用于后续偏好比较；本任务没有统一的效力硬阈值。','通过资格后，还要检查直接证据是否足以支撑排名。',source+'\n口服来源：DOI 10.1080/07853890.2026.2698360，sec2.3.p1；数值来自score-details相应规则。');
 txt(s,'口服条件通过',60,165,430,55,34,true,C.blue);
 txt(s,'“surufatinib was\nadministered orally\nat 250 mg once daily.”',60,255,450,150,31);
 txt(s,'临床给药记录\n口服要求 1 / 1',60,460,450,90,31,true);
 const vals=['CSF1R','VEGFR1','VEGFR2','VEGFR3','FGFR1'].map(t=>score.contributions.find(v=>v.name===t+' curated potency').assessed_value);
 chart(s,'bar',['CSF1R','VEGFR1','VEGFR2','VEGFR3','FGFR1'],[{name:'pChEMBL',values:vals,fill:C.blue}],560,180,660,365,10,{yAxis:{min:0,max:10,majorUnit:2,numberFormatCode:'0',textStyle:{fontSize:20,fill:C.muted},majorGridlines:{fill:C.line,width:.7}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00',textStyle:{fontSize:24,fill:C.ink}}});
 txt(s,'直接证据 5 / 5 · 图示单位 pChEMBL',565,560,650,45,26,true);
}
// 18: Failure precedes the corrected saved result.
{
 const s=page('首次没有名次，问题出在证据读取与分类','修复改变了可用证据和比较集合，门槛与权重保持原样。','第一次保存时，Surufatinib只有6项直接偏好证据，低于50%的排位要求，因此没有名次。检查发现已有事实未被正确复用，四项确定性结构描述符又被归入预测。修正后另存结果，直接覆盖达到10/17。合格比较组也随可用事实发生变化，最终分位数按新的合格组计算。','最终分数可以继续拆到各类偏好的实际贡献。');
 txt(s,'首次结果：6 / 17 = 35.3%',60,165,1120,50,33,true);
 shareRow(s,17,6,0,11,60,245,1160,52);txt(s,'低于 50% 排位要求，暂无名次',60,315,1120,40,27,false,C.muted);
 txt(s,'修正后：10 / 17 = 58.8%',60,427,1120,50,33,true,C.blue);
 shareRow(s,17,10,0,7,60,505,1160,52);
 txt(s,'蓝色：计入直接覆盖　灰色：未计入直接覆盖',60,574,1160,35,24,false,C.muted);
 caption(s,'已保存事实重新复用；4 项结构计算按其真实方法分类。门槛与权重未改',626);
}
// 19: Native contribution chart instead of 17 rows.
{
 const s=page('最终分数由三类偏好共同构成','15个有值偏好贡献0.7593，另两项缺证保留在覆盖分母中。','本轮偏好权重均为1。有值的15项进入平均，缺值的F%和Tmax没有补零。五靶点、五项结构计算和五项模型预测分别贡献约0.30370、0.21852和0.23704，合计0.75926。直接证据覆盖另算10/17，完整逐项数值在附录。','由此得到的是当前方案下合格候选的相对优先级。');
 const group=(fn)=>score.contributions.filter(fn).reduce((a,b)=>a+(b.final_score_contribution||0),0);
 const vals=[group(v=>v.name.includes('curated potency')),group(v=>v.determination_basis==='derived'),group(v=>v.determination_basis==='predicted')];
 chart(s,'bar',['五靶点','五项结构计算','五项模型预测'],[{name:'总分贡献',values:vals,fill:C.blue}],60,185,740,355,.4,{yAxis:{min:0,max:.4,majorUnit:.1,numberFormatCode:'0.0',textStyle:{fontSize:22,fill:C.muted},majorGridlines:{fill:C.line,width:.7}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00000',textStyle:{fontSize:27,fill:C.ink}}});
 txt(s,'0.7593',900,215,320,100,66,true,C.blue);txt(s,'11.388889 ÷ 15',875,345,345,60,32,true);
 txt(s,'直接覆盖 10 / 17\nF% 与 Tmax 仍缺证',875,440,345,95,28);
 caption(s,'对总分的贡献 = 比较分 × 权重 ÷ 有值偏好权重之和');
}
// 20: Actual result screenshot, focused on the first three rows.
{
 const s=page('Surufatinib 在 10 个合格候选中排名第 1','其余3167个候选是待补证据，不能画成已经淘汰。','完整候选库有3177项。最终10项符合资格且达到排位要求，Surufatinib排在第一。其他3167项仍待补证据，明确淘汰和未评估均为零。这里展示工作台实际合格榜前三名，完整列表可导出。','研究者还可以从这一名次回查实际采用的证据。',source+'\n截图：本轮制作时只读打开已保存snapshot2，未重跑。');
 await pic(s,OLD+'/presentation_source/assets/leaderboard.jpg',60,175,780,405,[296,336,435,212]);
 txt(s,'10 个合格并排名',895,200,325,100,37,true,C.blue);txt(s,'3,167 个待补证据',895,350,325,100,32);
 txt(s,'明确淘汰 0\n未评估 0',895,505,325,90,27,false,C.muted);
 caption(s,'实际合格榜节选；排名表示当前固定标准下的研究优先级');
}
// 21: Real evidence screenshot paired with the exact aggregation chain.
{
 const s=page('排名可以回到原文和实际计算','单条34nM原文并不等于最终汇总值，转换和聚合必须说清楚。','FGFR1原文报告34 nM，换算为pChEMBL约7.4685。本次固定标准还采用7.2800、7.82和7.82三条直接记录。四条值排序后取中位数，得到7.6443。研究者可以回看原文、实验条件和其他来源，再判断这种汇总是否适合后续验证。','同样的记录方式也适用于研究者上传自己的测量。',source+'\nFGFR1数值严格取score-details中rule_fgfr1-curated-potency@v1的raw_observations，未按共用引文混入CSF1R 5 nM。');
 await pic(s,OLD+'/presentation_source/assets/evidence-fgfr1-grouped.png',60,155,1160,225,[318,550,1035,198]);
 const a=node(s,'FGFR1：34 nM',60,460,245,75,C.pale),b=node(s,'换算为 7.4685',380,460,245,75,C.light),c=node(s,'4 条直接记录\n取中位数',700,440,245,115,C.light),d=node(s,'7.6443',1020,460,200,75,C.light,32);
 arrow(s,a,b);arrow(s,b,c);arrow(s,c,d);
 caption(s,'参与汇总的值：7.2800、7.4685、7.82、7.82 pChEMBL');
}
// 22: Generalization anchored in a real import UI.
{
 const s=page('更换药物或载体，沿用相同研究流程','候选、性质、条件和来源由用户数据决定，药物预测工具不强套到载体。','自有数据入口分别接收候选名单和逐条观测。每条测量需要候选身份、性质、数值、单位和依据，并保留条件与来源。换成载体时，研究问题可以是粒径、细胞活率和递送效率；后续仍经历标准形成、资格筛选和排序。','当前药物结果接下来需要补充哪些材料，也应从这些具体缺项出发。');
 await pic(s,OLD+'/presentation_source/assets/csv-import.jpg',60,150,1160,350,[414,274,816,205]);
 txt(s,'候选 ID → 性质与数值 → 单位与条件 → 来源与依据',60,540,1160,55,31,true,C.blue);
 caption(s,'载体示例：粒径来自 DLS 测量，细胞活率可作为硬要求，递送效率用于排序');
}
// 23: Close with the bounded conclusion and concrete next evidence.
{
 const s=page('当前结果支持优先验证，后续证据仍有明确缺口','系统交付的是有来源的优先名单，并指出下一步需要回答的问题。','这次研究形成了18条核心标准，并把Surufatinib排到10个合格候选的第一位。它给出了可回查的研究优先顺序。下一步应补人类实测F%、Tmax和Food-AUC，明确四项参考观察的判读方式，并检验间接结构偏好是否真能区分候选。','附录保留全部17项评分明细，供需要逐项核对时查阅。');
 txt(s,'已得到',60,160,480,45,28,false,C.muted);txt(s,'18 条核心标准\n10 个合格候选\n可回查的排名依据',60,235,540,245,41,true);
 line(s,685,165,0,380);
 txt(s,'下一步需要的证据',755,160,465,50,31,true);
 txt(s,'补 F%、Tmax、Food-AUC\n\n明确 4 项参考观察的判读\n\n检验结构偏好的实际区分能力',755,252,465,300,29);
 caption(s,'结论对应本次固定的研究标准与证据范围');
}
// Appendices retain exact coverage without dominating the talk.
const short={'CSF1R curated potency':'CSF1R','FGFR1 curated potency':'FGFR1','VEGFR1 curated potency':'VEGFR1','VEGFR2 curated potency':'VEGFR2','VEGFR3 curated potency':'VEGFR3','Molecular weight (Da)':'分子量','Predicted logP (RDKit)':'RDKit logP','Predicted BRENK alert count':'BRENK 警报','Predicted NIH alert count':'NIH 警报','Predicted PAINS alert count':'PAINS 警报','Predicted blood-brain barrier penetration probability (BBB_Martins)':'BBB 渗透概率','Predicted CYP1A2 inhibition probability':'CYP1A2 抑制概率','Predicted CYP2C19 inhibition probability':'CYP2C19 抑制概率','Predicted CYP2C9 inhibition probability':'CYP2C9 抑制概率','Predicted CYP2C9 substrate probability':'CYP2C9 底物概率','Oral bioavailability (human, measured F%)':'人体实测 F%','Time to maximum plasma concentration (Tmax, median of reported values)':'人体实测 Tmax'};
const order=['CSF1R','VEGFR1','VEGFR2','VEGFR3','FGFR1','分子量','RDKit logP','BRENK 警报','NIH 警报','PAINS 警报','BBB 渗透概率','CYP1A2 抑制概率','CYP2C19 抑制概率','CYP2C9 抑制概率','CYP2C9 底物概率','人体实测 F%','人体实测 Tmax'];
const items=order.map(n=>score.contributions.find(v=>short[v.name]===n));
for(let k=0;k<2;k++){
 const s=page('附录：17 项偏好评分明细 '+(k+1)+'/2','完整保留实际值、证据类型与每项贡献。','表中各项权重均为1。比较分按本次合格且有值的候选计算，总分贡献为比较分除以15。缺值项仍保留在17项直接覆盖分母中。','数值经显示舍入，实际总分使用原始精度。');
 const rows=[['偏好','实际值','依据','比较分','总分贡献'],...items.slice(k?9:0,k?17:9).map(v=>[short[v.name],v.assessed_value==null?'缺证':Number(v.assessed_value.toFixed(4)).toString()+(v.unit==='pChEMBL'?' pChEMBL':v.unit==='Da'?' Da':v.unit==='count'?' 个':''),{measured:'实测汇总',derived:'结构计算',predicted:'模型预测',absent:'缺证'}[v.determination_basis]||'缺证',v.desirability==null?'不计':v.desirability.toFixed(4),v.final_score_contribution==null?'不计':v.final_score_contribution.toFixed(5)])];
 table(s,rows,145,k?430:475,[305,260,180,180,235]);caption(s,k?'总分 0.7592593；直接证据覆盖 10/17 = 58.82%':'各项权重为 1；总分贡献 = 比较分 ÷ 15',k?610:634);
}
await fs.mkdir(BUILD+'/preview',{recursive:true});
await fs.writeFile(BUILD+'/story.json',JSON.stringify(notes,null,2));
await fs.writeFile(BUILD+'/逐页主旨与讲稿.md','# MAS：逐页主旨与讲稿\n\n'+notes.map(n=>'## '+n.page+'. '+n.title+'\n\n本页主旨：'+n.point+'\n\n'+n.talk+'\n\n'+n.bridge+'\n').join('\n'));
const picks=process.env.SLIDES?process.env.SLIDES.split(',').map(Number):p.slides.items.map((_,i)=>i+1);
for(const i of picks){const png=await p.export({slide:p.slides.items[i-1],format:'png',scale:1});await fs.writeFile(BUILD+'/preview/'+String(i).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));}
await (await PresentationFile.exportPptx(p)).save(BUILD+'/candidate.pptx');
if(process.argv.includes('--final')){
 const finalPath=process.env.MAS_PPTX_OUTPUT || OLD+'/MAS_流程机制与案例_20261017.pptx';
 await finalizePresentation({workspaceDir:ROOT,candidatePath:BUILD+'/candidate.pptx',finalPath,pythonExecutable:PY,integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[...new Set(charts)],fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,materializeLiteralChartWorkbooks:true,receiptPath:BUILD+'/final-validation.json'});
 const final=await PresentationFile.importPptx(await FileBlob.load(finalPath));await fs.mkdir(BUILD+'/final-preview',{recursive:true});
 for(let i=0;i<final.slides.items.length;i++){const png=await final.export({slide:final.slides.items[i],format:'png',scale:1});await fs.writeFile(BUILD+'/final-preview/'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));}
 console.log('FINAL '+finalPath);
}
console.log(JSON.stringify({slides:p.slides.items.length,nativeTables:tables,nativeCharts:charts}));
