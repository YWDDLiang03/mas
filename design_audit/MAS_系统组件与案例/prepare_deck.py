"""Prepare the approved deck. Image jobs exclude original screenshots and exact data pages."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SKILL = Path('C:/Users/admin/.codex/skills/codex-ppt/scripts')
SAMPLE = ROOT / 'origin_image/slide_08.png'

# title, exact visible diagram labels, composition. Detailed arguments live in speech.md.
BRIEFS = {
1: ('MAS：从研究问题到候选选择',
    ['通用研究系统', '研究问题', '证据与标准', '候选结果', '每个决定都有依据'],
    'Cover, substantial white space. Large MAS title top left. Across the lower center one continuous path from a question document, through evidence and a clearly drawn criteria review loop, to a short ranked list. Three labeled stations, not three disconnected cards. Small subtitle 通用研究系统 below title. The last phrase is a restrained small caption. No drug names or numerical results.'),
2: ('材料很多，比较依据仍需建立',
    ['对象不同', '条件不同', '测量不同', '哪些结果可以比较？', '用什么标准做选择？'],
    'Problem figure. Three sparse research records at left with visibly different object/condition/measurement glyphs converge toward two large questions at right. Differences in experimental context should be visible through separate labeled small marks; no scientific numerical facts, no decorative science background. Two questions are the visual emphasis.'),
3: ('输入问题、候选与证据，输出完整研究结果',
    ['研究目标', '候选名单', '文献与测量', 'MAS', '核心标准', '候选排序', '依据与缺项'],
    'Input-output diagram: three distinct inputs on left feed a single central MAS research process. On right three actual outputs fan out. Candidates icon is a set of distinct entities, literature icon is documents with observations. Keep input and output roles visually clear, no extra explanatory sentences.'),
4: ('先形成标准，再应用标准',
    ['理解任务', '准备证据', '提出标准', '审查提炼', '解决争议', '固定方案', '评估候选', '发布结果', '形成标准', '应用标准', '修订'],
    'Eight-stage two-row process with clear reading order: first row left to right 理解任务 → 准备证据 → 提出标准 → 审查提炼. A connector continues to second row reading left to right 解决争议 → 固定方案 → 评估候选 → 发布结果. Label the first row 形成标准; second row has fixed plan and application. One returning revision arrow from 审查提炼 back to 提出标准. Do not add a misleading extra loop from results to old rules. Generous spacing; 8 concise labels only.'),
5: ('通用流程、领域工具与具体任务分开配置',
    ['具体任务', '目标 · 约束 · 候选 · 证据', '领域工具', '药物：靶点活性、结构性质', '载体：粒径、递送效率', '通用流程', '形成标准 → 审查 → 筛选 → 排序', '载体为应用示意'],
    'Three horizontal layers with modest arrows connecting them. Upper narrow layer case-specific task. Middle layer two swappable domain adapters, drug and carrier, visually plug into the same lower broad reusable workflow. Make the core visually stable and domains interchangeable. The carrier qualifier is a small note next to its example. No claims that all domains have been validated.'),
6: ('先把自然语言整理成明确的研究任务',
    ['示例任务', '比较载体的递送表现与安全性', '研究对象', '载体', '目标性质', '递送效率', '条件与约束', '实验条件、必要限制', '关键缺项', '补充后继续', '研究步骤'],
    'Left a single short natural language task. Center a decomposition into research object, target property, and conditions/constraints, with precise pointers to phrases. Right the resulting research steps. A small separate downward missing-information branch returns after supplementation. This is a schematic carrier example, no numeric thresholds or invented acceptance results.'),
7: ('一条证据，要保留它成立的条件',
    ['来源原文', '对象', '性质与数值', '单位', '实验条件', '原文位置', '同一文献归组', '不同条件分别保留'],
    'Evidence anatomy. One source document at left, zoomed observation in center, with four clear labeled pointers for object, property/value, unit, experimental conditions and a page-location marker linking back to the document. At bottom two observations under one source bracket illustrate same paper, different conditions. No invented numeric measurements, no lengthy fake quote.'),
8: ('多智能体协作，让标准经过质疑与修订', [], 'Reuse approved sample unchanged.'),
9: ('CQA 说明测什么，规则说明怎样决定',
    ['属性定义', '测量对象 · 单位 · 条件', '决策规则', '硬条件 / 偏好 / 参考', '阈值或比较方向', '来源与版本', '可执行标准', '示例：载体粒径'],
    'Exploded criterion anatomy. One central criterion sheet labeled 可执行标准 receives two clearly different halves: 属性定义 (what is measured) and 决策规则 (how used). A source/version tab attaches underneath. Use carrier size as an explicitly marked example, but no invented value or universal threshold. Enough whitespace, no huge multirow form.'),
10: ('提炼让每条标准承担独立的判断作用',
    ['候选提议', '检查支持', '明确测量', '回应质疑', '合并重复', '核心标准', '待处理', '保留原提议与变化理由'],
    'A branching process rather than a funnel: several small proposal documents enter four sequential operations 检查支持 → 明确测量 → 回应质疑 → 合并重复. Show two duplicates joining into one near 合并重复 and an unresolved branch leaving toward 待处理. Remaining independent criteria continue to 核心标准. Preserve a subtle backward provenance line. No counts or percentages.'),
11: ('按标准获取观测，保留每种结果的依据',
    ['研究标准', '已有测量', '确定性计算', '模型预测', '候选观测', '缺证或失败：记录原因', '预测作为辅助依据'],
    'Three-lane acquisition diagram: one research criterion branches to measurement lookup, deterministic calculation, and model prediction, each lane has a different clear functional line icon. Lanes reconverge at candidate observations, while evidence-type tags remain visible. A small gray exception branch records absence/errors. Prediction lane is a lighter blue and has the short helper annotation; do not imply predictions count as measured.'),
12: ('先判断资格，再比较偏好',
    ['硬条件与必需证据', '硬条件明确失败', '淘汰', '缺失或冲突', '待补证据', '满足资格', '检查直接证据覆盖', '覆盖足够', '偏好排序', '覆盖不足', '合格，暂不排名'],
    'A readable qualification decision tree. Start at hard conditions plus required evidence; branch left to rejected only for explicit hard failure, right to pending for missing/conflict, and down to qualified if satisfied. Qualified then checks direct evidence coverage; sufficient leads to preference ranking, insufficient to qualified but unranked. Do not collapse pending into failure. Distinct blue qualified and neutral gray missing states. No green/red dominant palette.'),
13: ('进度同时说明做到哪一步、正在处理什么',
    ['全流程阶段', '当前阶段', '当前批次', '最近活动', '时间与预算', '暂停 · 继续 · 停止', '分母未知时展示当前工作'],
    'Conceptual two-level progress illustration, NOT a fake UI screenshot. Top a process rail with completed stages and one current stage. A magnifying bracket expands the active stage into current batches, with status and budget callouts. Unknown denominator drawn as an open-ended progress segment and exact short note. No numeric percentage, no fake clocks. White space and minimal shapes.'),
14: ('从名次一路回查到原文',
    ['候选名次', '单项得分', '标准版本', '原始观测', '来源原文', '版本 1', '版本 2', '保留原结果', '复用有效证据'],
    'Five-item left-to-right provenance chain labeled candidate rank → per-criterion score → criterion version → raw observations → original source; arrows show inspection direction toward source. Below criterion version, a small two-version branch preserves both results and shares unchanged evidence. Do not suggest replacing old scientific records. Main chain prominent, version reuse small and explanatory.'),
15: ('本次案例：寻找口服、多靶点的候选药物',
    ['单一口服药物', 'CSF1R', 'VEGFR1', 'VEGFR2', 'VEGFR3', 'FGFR1', '已有候选库与证据', '参考候选：Surufatinib'],
    'Case opening, one central pill/document marked 单一口服药物 connects to five labeled target nodes. A small input tray below says existing candidates and evidence. Reference candidate disclosed in a modest note. This is a task-scope map, not a disease mechanism diagram. Do not show efficacy arrows, tissues, cells, or clinical claims.'),
22: ('分子量标准经历合并、质疑与修订',
    ['六条同类提议', '合并', '保留父项与来源', '审查适用性', '补充经验依据', '启用为偏好', '分子量 ≤ 500 Da'],
    'Actual lineage summary: six small original proposal sheets at left merge into one middle sheet. After merging, a reviewer question mark leads to revision and then final criterion at right. Final large text 启用为偏好 with 分子量 ≤ 500 Da beneath. Clearly show merge followed by review/revision, not just deduplication. Avoid implying it is an exclusion hard cutoff. No invented parent IDs or fabricated quotes.'),
24: ('固定评估方案，再逐项检查候选',
    ['固定方案', '1 条硬条件', '17 条偏好', '13 条参考', '3,177 个候选', '资格核验', '偏好评估', '保存结果', '本次没有明确硬失败', '前序失败后跳过：0'],
    'One frozen-plan document atop a three-stage candidate evaluation pathway 资格核验 → 偏好评估 → 保存结果. Candidate population comes from left. A small hard-failure branch indicates skip-after-rejection as a mechanism, but annotate exact actual outcome 本次没有明确硬失败 and 前序失败后跳过：0. Do not draw actual candidates disappearing or claim all candidates passed. A frozen plan has 1 hard +17 prefs +13 context.'),
26: ('修正证据读取后，另存新的评估结果',
    ['首次结果', '直接覆盖 6/17', '暂不排名', '复用已有事实', '校正四项计算结果的依据分类', '新结果', '直接覆盖 10/17', '达到排位要求', '阈值、权重与覆盖门槛保持不变'],
    'Before-to-after figure. Left sparse earlier result 6/17 and unranked. Middle two precisely labeled correction actions, not a developer/debugging screen. Right 10/17 and ready to rank. A common fixed-rule bracket spans both states, with unchanged thresholds/weights/coverage floor sentence. No fake screenshots; no claim that whole candidate comparison cohort stayed fixed.'),
31: ('本次完成了标准生成、候选比较与依据回查',
    ['从零形成标准', '18 条核心标准', '通过启用硬条件', 'Surufatinib：1 / 10', '依据可回查', '待补：人类实测 F%、Tmax'],
    'Conclusion anchored to the research flow. Three connected milestones standards → candidate choice → evidence inspection, with 18 core criteria and Surufatinib 1/10 clearly attached to relevant milestone. A small open next-evidence branch says human measured F%, Tmax. No victory trophy or absolute clinical superiority claim. Clean blue, spacious.'),
}

native = {
16: ('在 Settings 设定本次运行方式','screenshot'),
17: ('新建任务，写清目标、靶点与约束','screenshot'),
18: ('选择候选库与固定证据集合','screenshot'),
19: ('启动后，沿进度条观察当前工作','screenshot'),
20: ('从空标准集开始，按研究维度展开','data'),
21: ('三轮提炼，让工作项从 1,917 收敛到 53','data'),
23: ('53 个工作项，各自承担不同用途','screenshot'),
25: ('Surufatinib 的口服条件通过，五靶点证据齐全','screenshot'),
27: ('展开 Score，逐项解释 0.7593 的来源','screenshot'),
28: ('Surufatinib 在 10 个合格候选中排名第一','screenshot'),
29: ('从 FGFR1 得分回到文献与原始观测','screenshot'),
30: ('导出完整候选结果与对应依据','screenshot'),
32: ('换成自己的候选和证据，沿用研究流程','screenshot'),
33: ('评分明细：靶点、结构性质与缺项','table'),
34: ('评分明细：结构警示与预测参考','table'),
}

def main():
    method=json.loads((ROOT/'sample_08_record.json').read_text('utf-8'))
    method.update(sample_approved=True,full_deck_generation_authorized=True,status='accepted')
    (ROOT/'sample_08_record.json').write_text(json.dumps(method,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    gen_method={
      'backend_used':'built-in image tool','tool_name':'image_gen__imagegen','mode':'generate',
      'prompt_source':'sample_08_prompt.txt','size':'16:9 landscape; native tool defaults',
      'model_config':'built-in defaults; model and quality not exposed',
      'approved_sample_path':str(SAMPLE),
      'input_context_preparation':'Inspect local style reference with view_image; pass it as style-only reference. No screenshot is sent for synthetic redrawing.',
      'handoff_rule':'Use this same built-in image backend; report a blocker if unavailable.'}
    spec={
      'deck_name':ROOT.name,'language':'Chinese','goal':'Explain the general MAS system, each component and its design reasons, then walk through the saved oral multi-target case from settings to final export.',
      'selected_image_backend':'built-in image tool','max_concurrent_slides':3,
      'sample_generation_method':gen_method,
      'approved_style_reference':{'path':str(SAMPLE),'role':'approved sample style only','fidelity':'Keep the white/pale-blue scientific diagram style; vary layout by content.'},
      'style':{'name':'白底浅蓝科学示意图','visual_direction':'Match approved sample. Restrained scientific slide, substantial whitespace, dark navy Chinese typography, sky-blue outlines and arrows, pale-blue fills. Small functional line icons only.',
               'color_palette':'white #FFFFFF, navy #082646, blue #2086D5, pale blue #E6F3FD, gray #8290A0',
               'typography':'Large accurate Simplified Chinese sans-serif; title top left, about 40pt equivalent; labels about 22–26pt; little text.',
               'finish':'Flat, crisp, no decoration, no 3D, no robots, no shadow, no page number.'},
      'deck_context':{'source_summary':'MAS organizes evidence into reviewed criteria, then fixes rules to assess and rank qualified candidates. This is research prioritization, not clinical prescribing.',
          'core_claim':'Research question → evidence → criteria and review → qualification → ranking → source inspection.',
          'canonical_terms':['提出者','审查者','裁决者','研究标准','硬条件','偏好','参考','待补证据'],
          'scope':'Only render text explicitly requested in this slide. Carrier examples are illustrative, not validated runs. Source-wide context is for understanding, not extra on-slide prose.'},
      'rendering_policy':{'user_instruction':'该用真实截图的直接用截图，机制部分用图讲清楚，别堆文字',
          'image_jobs':'Concept and mechanism slides use the confirmed image tool and mandatory slide workers.',
          'native_pages':'Original screenshots are embedded byte-for-byte as PowerPoint pictures with native headings/callouts; exact charts and appendix tables are assembled from source numbers. These are explicit user-directed exceptions to all-pages-as-generated-images. They are not recorded as image model output.'},
      'slides':[], 'all_slides':[]}
    for n in range(1,35):
        if n in BRIEFS:
            title,labels,composition=BRIEFS[n]
            s={'number':n,'title':title,'role':'scientific explanatory diagram','intent':'Make one research mechanism understandable visually.',
              'key_points':labels,'local_context':{'exact_on_slide_text':labels,'layout_and_facts':composition},
              'layout':{'composition':composition,'spacing':'White canvas with generous margins and no text collisions; choose diagram geometry for this particular content.'},
              'visual_elements':{'main_visual':composition},
              'constraints':['Render exactly one finished 16:9 full slide.','Use the provided image only as a style reference, not an edit target. Create the specified new content.',
                'No bullet paragraphs, table, long explanation, slide number, logo, watermarks, slogan or invented facts.',
                'Only render the given title and exact labels. Do not print context, filenames, prompts, English role metadata or this instruction.',
                'Diagrams must use correct directed arrows and readable Chinese. Do not shrink labels to fit; simplify graphical detail.',
                'Use functional diagrams, not a repeated grid of large rectangular cards.'],
              'sample_approved':n==8,'use_approved_style_reference':n!=8}
            spec['slides'].append(s)
            spec['all_slides'].append({'number':n,'title':title,'render_mode':'generated','source':f'origin_image/slide_{n:02}.png'})
        else:
            title,kind=native[n]
            spec['all_slides'].append({'number':n,'title':title,'render_mode':kind})
    (ROOT/'deck_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    subprocess.run([sys.executable,str(SKILL/'prepare_slide_prompts.py'),'--spec',str(ROOT/'deck_spec.json'),'--out-dir',str(ROOT),'--selected-backend','built-in image tool','--max-concurrent-slides','3'],check=True)

if __name__=='__main__': main()
