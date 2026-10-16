import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { loadImage } from '@napi-rs/canvas';

process.env.RUNTIME_NODE_MODULES??='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE??='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,'../../..');
const BUILD=path.join(ROOT,'var/fresh-browser-20261016/presentation-build');
const FINAL_DIR=path.join(ROOT,'design_audit/fresh_browser_2026-10-16');
const SKILL='C:/Users/admin/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PYTHON='C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const {applyPresentationChartFont, finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const args=process.argv.slice(2);
const draft=args.includes('--draft');
const dataFile=args.find(a=>a.endsWith('.json')) ?? path.join(HERE,'content.final.json');
const data=JSON.parse(await fs.readFile(dataFile,'utf8'));
if(!draft){
 const r=data.result;
 if(!data.verified || !r?.task_id || !r?.run_id || !r?.snapshot_id || !data.conclusion) throw new Error('Final export requires the verified fresh task, run, snapshot and conclusion.');
 if(!data.cqa?.evolution?.length || !Number.isInteger(data.cqa.active_total) || !Number.isInteger(data.cqa.executable_total)) throw new Error('The fresh criterion evolution and active/executable totals are required.');
 const n=r.population;
 if(!n || [n.total,n.qualified,n.rejected,n.pending,n.not_assessed??0].some(v=>!Number.isInteger(v)||v<0) || n.total!==n.qualified+n.rejected+n.pending+(n.not_assessed??0)) throw new Error('Candidate population counts must be complete and add up.');
 if(['hard_passed','hard_total','required_answered','required_total'].some(k=>!Number.isInteger(r[k]))) throw new Error('Qualification evidence numerators and denominators are required.');
 for(const name of ['settings','evidence','progress','csv']) if(!data.assets?.[name]?.path) throw new Error('Missing final screenshot: '+name);
}
const FONT='Microsoft YaHei';
const C={ink:'#183A59',muted:'#546C80',blue:'#2D80B9',light:'#EAF4FC',line:'#C4D9E8',white:'#FFFFFF',green:'#2F8270',amber:'#A57435'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const notes=[];
function text(s,value,x,y,w,h,size=28,bold=false,color=C.ink,align='left'){
 const shape=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=String(value);
 shape.text.style={typeface:FONT,fontSize:size,bold,color,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};
 return shape;
}
function page(title,sourceNote=''){
 const slide=p.slides.add();
 slide.background.fill=C.white;
 text(slide,title,64,42,1150,94,43,true);
 text(slide,String(p.slides.items.length).padStart(2,'0'),1182,674,46,26,17,false,C.muted,'right');
 if(draft) text(slide,'版式预览，结果等待本轮验收',64,675,900,24,16,false,C.muted);
 const narration=data.narration?.[p.slides.items.length-1]??'';
 slide.speakerNotes.text=narration+(narration?'\n\n来源与口径\n':'')+sourceNote;
 notes.push({page:p.slides.items.length,title,narration,source:sourceNote});
 return slide;
}
async function picture(slide,key,x,y,w,h){
 const record=data.assets?.[key];
 if(!record?.path){text(slide,'本轮截图待补充',x,y+Math.max(0,h/2-22),w,60,25,false,C.muted,'center');return;}
 const imagePath=path.isAbsolute(record.path)?record.path:path.resolve(path.dirname(dataFile),record.path);
 const bytes=await fs.readFile(imagePath);
 const dimensions=await loadImage(bytes);
 const crop=record.crop??{left:0,top:0,right:0,bottom:0};
 const visibleW=dimensions.width*(1-crop.left-crop.right);
 const visibleH=dimensions.height*(1-crop.top-crop.bottom);
 const scale=Math.min(w/visibleW,h/visibleH);
 const drawW=visibleW*scale,drawH=visibleH*scale;
 const drawX=x+(w-drawW)/2,drawY=y+(h-drawH)/2;
 slide.images.add({blob:new Uint8Array(bytes),contentType:record.path.toLowerCase().endsWith('.png')?'image/png':'image/jpeg',
   alt:record.alt??record.caption??key,fit:'contain',position:{left:drawX,top:drawY,width:drawW,height:drawH},...(record.crop?{crop:record.crop}:{})});
 if(record.caption) text(slide,record.caption,x,drawY+drawH+8,w,30,19,false,C.muted);
}
function table(slide,values,x,y,w,h,widths){
 const t=slide.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});
 t.styleOptions={headerRow:true,bandedRows:false};
 t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);
  cell.fill=r===0?C.light:C.white;
  cell.text.style={typeface:FONT,fontSize:r===0?25:24,bold:r===0,color:C.ink,verticalAlignment:'middle'};
 }
 return t;
}
function chart(slide,categories,values,x,y,w,h,{direction='column',color=C.blue,max}={}){
 const c=slide.charts.add('bar',{position:{left:x,top:y,width:w,height:h},categories,
   series:[{name:'数量',values,fill:color}],barOptions:{direction,grouping:'clustered',gapWidth:85},
   hasLegend:false,chartFill:'none',plotAreaFill:'none',
   xAxis:{textStyle:{fontSize:21,fill:C.muted},line:{fill:C.line,width:1}},
   yAxis:{min:0,...(max?{max,majorUnit:max===1?0.5:undefined}:{}),textStyle:{fontSize:18,fill:C.muted},majorGridlines:{fill:C.line,width:1},numberFormatCode:max===1?'0.0':'0'},
   dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0',textStyle:{fontSize:23,bold:true,fill:C.ink}}});
 applyPresentationChartFont(c,{fontFamily:FONT});
 return c;
}
const result=data.result??{};
const current='本轮结果待核验';
const cqaVerified=data.cqa?.verified===true;
if(cqaVerified && (data.cqa.core_total+data.cqa.context_total+data.cqa.pending_total!==data.cqa.working_total ||
 data.cqa.deferred_total+data.cqa.unregistered_pending_total!==data.cqa.pending_total ||
 data.cqa.core_total+data.cqa.context_total!==data.cqa.executable_total ||
 data.cqa.review_pending_subset>data.cqa.deferred_total)) throw new Error('CQA counts mix incompatible populations or double count review pending.');
{
 const s=page('MAS Research 研究工作台',data.sources?.summary??'本轮结果只在完成验收后填入。');
 s.background.fill=C.light;
 text(s,'浏览器全流程与研究者使用体验',68,166,1110,100,52,true);
 const conclusion=data.verified?data.conclusion:current;
 text(s,conclusion,68,304,1110,125,42,true,C.blue);
 if(data.verified) text(s,'当前冻结标准下的研究优先级',68,459,1110,48,28,false,C.muted);
 text(s,data.report_date??'2026 年 10 月 17 日',68,574,1000,40,25,false,C.muted);
}
{
 const s=page('研究任务与运行设置',data.sources?.task??'来源：本轮研究目标、保存的 Settings 截图。');
 text(s,'单一口服候选\n同时覆盖五个目标',64,170,420,112,34,true);
 text(s,'CSF1R\nVEGFR1、VEGFR2、VEGFR3\nFGFR1',64,304,425,156,28,false);
 text(s,'标准从空集合开始\n文献与教材设置均为 Medium',64,506,420,94,27,false,C.muted);
 await picture(s,'settings',525,156,700,412);
}
{
 const s=page('筛选标准的展开与提炼',data.sources?.evolution??'来源：本轮标准推导的逐阶段记录。数量口径必须保持一致。');
 const ev=data.cqa?.evolution;
 if(ev?.length){chart(s,ev.map(x=>x.label),ev.map(x=>x.count),64,178,825,405);}
 else text(s,'等待本轮阶段记录\n完成后展示真实数量变化',84,284,800,130,34,false,C.muted);
 text(s,cqaVerified?String(data.cqa.core_total):'待核验',934,181,290,88,64,true,C.blue);
 text(s,'核心决策标准',934,275,290,48,29,true);
 text(s,cqaVerified?'1 条硬条件，17 条偏好':'核心标准数待核验',934,327,290,50,22,false,C.muted);
 text(s,cqaVerified?String(data.cqa.context_total)+' 条背景观察':'背景观察待核验',934,415,290,58,31,true);
 text(s,cqaVerified?String(data.cqa.pending_total)+' 条待处理记录':'待处理记录单列',934,511,290,58,31,true);
 if(cqaVerified) text(s,'工作记录口径包含待处理项，最终 53 条均保留',64,603,825,39,23,false,C.muted);
}
{
 const s=page('资格与偏好的不同作用',data.sources?.policy??'来源：本轮冻结的资格和评分规则。预测不能提供硬条件或 required scope 的直接证据。');
 table(s,[['判断层次','研究含义','对候选的影响'],
  ['硬条件','满足已核验的任务要求','明确失败则淘汰'],
  ['必需目标证据','各目标均有直接证据','缺证据保持待定'],
  ['连续偏好','比较可用性质的优劣','在合格集内排序'],
  ['背景观察','有值与可判读分开','仅作参考，不计分']],64,173,1152,354,[205,475,472]);
 text(s,'排名要求直接偏好证据达到 50%，预测只辅助偏好',64,570,1152,55,28,false,C.muted);
}
{
 const s=page('本轮候选筛选与排名',data.sources?.result??'来源：新任务完成后保存的 leaderboard snapshot；不替用旧榜单。');
 if(data.verified || result.observed_ui){
  const counts=result.population;
  chart(s,['合格','明确淘汰','证据待定','未评估'],[counts.qualified,counts.rejected,counts.pending,counts.not_assessed??0],64,180,600,372);
  text(s,'Surufatinib',740,174,470,50,34,true);
  text(s,String(result.rank)+' / '+String(counts.qualified),740,243,470,92,66,true,C.blue);
  text(s,'合格候选中的名次',740,350,470,48,27,false,C.muted);
  text(s,'硬条件 '+result.hard_passed+'/'+result.hard_total+'\n必需目标直接证据 '+result.required_answered+'/'+result.required_total+
   (result.direct_preference_answered!==undefined?'\n直接偏好证据 '+result.direct_preference_answered+'/'+result.preference_total+'（'+(100*result.direct_preference_answered/result.preference_total).toFixed(1)+'%）':''),740,424,470,143,27,false);
  if(!data.verified) text(s,'浏览器已显示，等待独立核验',740,570,470,38,20,false,C.amber);
  else text(s,'偏好分数 '+Number(result.score).toFixed(4),740,570,470,38,25,false,C.muted);
  text(s,'固定候选库 '+counts.total+' 个候选',64,590,1100,45,26,false,C.muted);
 }else text(s,current+'\n本页只使用新一轮完成后的结果',80,245,1100,150,39,false,C.muted);
}
{
 const s=page('证据原文与判断依据',data.sources?.evidence??'来源：本轮证据页面和对应原文位置。');
 await picture(s,'evidence',64,164,755,410);
 text(s,data.evidence?.headline??'证据与解释分开呈现',866,179,350,94,31,true);
 text(s,data.evidence?.body??'来源与原文\n候选归属\n单位与实验条件\n对应的判断结果',866,310,350,242,27,false);
 if(data.evidence?.limitation) text(s,data.evidence.limitation,64,621,1152,40,22,false,C.muted);
}
{
 const s=page('研究过程在浏览器中可见',data.sources?.experience??'来源：本轮浏览器截图和已核对的工作台交互。');
 if(data.assets?.cqa_counts?.path){
  await picture(s,'progress',64,160,1152,212);
  await picture(s,'cqa_counts',64,430,1152,212);
 }else{
  await picture(s,'progress',64,170,775,432);
  text(s,'当前阶段与活动\n已完成的工作量\n费用和运行状态',885,184,330,202,29,true);
  text(s,'标准修改与判断理由\n都保留可回查记录',885,446,330,108,27,false,C.muted);
 }
}
{
 const s=page('自带候选和测量数据',data.sources?.generic??'来源：var/workbench-usability/generic-source-audit.json。合成工程数据，非真实实验结果。');
 await picture(s,'csv',64,167,696,393);
 text(s,'载体 CSV 能力示例',814,170,401,58,30,true);
 chart(s,['载体 A','载体 B'],[1,0],805,258,415,245,{max:1});
 text(s,'合成工程数据\n通过硬条件后，合格集内排序',814,538,401,82,25,false,C.muted);
 text(s,'候选编号、性质、单位、条件和来源完整保留',64,611,1152,44,26,false);
}
{
 const s=page('交付与适用范围',data.sources?.delivery??'最终文件以本轮完成后的交付目录为准。');
 text(s,'可编辑汇报 PPT\n简洁中文结果报告\n候选清单与可回查证据',64,181,585,223,34,true);
 text(s,'人体实测 F% 与 Tmax\n仍缺对应证据',704,184,510,147,32,false);
 text(s,'4 项背景已有值，仍需判读\n食物影响 AUC 仍缺对应证据',704,399,510,151,27,false,C.muted);
 text(s,data.verified?'研究筛选与证据核对之后，仍需研究者开展实验和临床判断':'本轮完成后填写最终交付信息',64,583,1152,48,27,false,C.muted);
}
await fs.mkdir(BUILD,{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const slide=p.slides.items[i];
 const png=await p.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(BUILD,'slide-'+String(i+1).padStart(2,'0')+'.png'),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(BUILD,draft?'layout-preview.pptx':'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
await fs.writeFile(path.join(BUILD,'slide-notes.json'),JSON.stringify(notes,null,2));
if(!draft){
 const tag=Date.now();
 const target=path.join(BUILD,'final-output','finalized-'+tag+'-'+(data.output_filename??'MAS_研究工作台_浏览器验收汇报.pptx'));
 await fs.mkdir(path.dirname(target),{recursive:true});
 const final=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:target,
   explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[4],requiredNativeChartOwnerSlides:[3,5,8],
   materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[FONT]},
   pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
   layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
   layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','4'],
   verifyArtifactToolImport:true,receiptPath:path.join(BUILD,'final-validation-'+tag+'.json')});
 await fs.writeFile(path.join(BUILD,'latest-finalized.json'),JSON.stringify(final,null,2));
 console.log(JSON.stringify({final,slides:9}));
}else console.log(JSON.stringify({draft:candidate,slides:9,verified:false}));

