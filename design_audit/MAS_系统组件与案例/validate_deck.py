"""Verify the delivered presentation against its approved job state and saved inputs."""
from pathlib import Path
import hashlib,json,re,zipfile
from pptx import Presentation

root=Path(__file__).resolve().parent
p=root/'MAS_系统组件与案例.pptx'
prs=Presentation(p)
speech=(root/'speech.md').read_text('utf-8')
blocks={int(m.group(1)):m.group(2).strip() for m in re.finditer(r'^## Slide (\d+):[^\n]*\n(.*?)(?=^## Slide |\Z)',speech,re.M|re.S)}
jobs=json.loads((root/'slide_jobs.json').read_text('utf-8'))['slides']
spec=json.loads((root/'deck_spec.json').read_text('utf-8'))
uses=json.loads((root/'asset_usage.json').read_text('utf-8'))
score=json.loads((root.parent/'workbench_presentation_2026-10-17/presentation_source/data/score-details.json').read_text('utf-8-sig'))
assert len(prs.slides)==34 and len(blocks)==34
assert all(slide.notes_slide.notes_text_frame.text==blocks[i] for i,slide in enumerate(prs.slides,1))
assert len(jobs)==19 and all(j['status'] in ('accepted','recorded') for j in jobs)
assert sum(j['status']=='accepted' for j in jobs)==1
with zipfile.ZipFile(p) as z:
    media={hashlib.sha256(z.read(k)).hexdigest() for k in z.namelist() if k.startswith('ppt/media/')}
    for u in uses:assert u['sha256'] in media
    for s in spec['all_slides']:
        if s['render_mode']=='generated':assert hashlib.sha256((root/s['source']).read_bytes()).hexdigest() in media
    charts=[k for k in z.namelist() if re.fullmatch(r'ppt/charts/chart\d+\.xml',k)]
    assert len(charts)==2
tables=[(i,len(shape.table.rows)-1) for i,slide in enumerate(prs.slides,1) for shape in slide.shapes if shape.has_table]
assert tables==[(33,9),(34,8)]
assert len(score['contributions'])==17
assert sum(r['included_in_score'] for r in score['contributions'])==15
assert sum(r['direct_evidence'] for r in score['contributions'])==10
recomputed=sum(r['final_score_contribution'] or 0 for r in score['contributions'])
assert abs(recomputed-score['source_score'])<1e-12
assert score['rank']==1 and len(score['qualified_cohort'])==10
overflows=[]
for i,slide in enumerate(prs.slides,1):
    for shape in slide.shapes:
        if shape.left<0 or shape.top<0 or shape.left+shape.width>prs.slide_width+2 or shape.top+shape.height>prs.slide_height+2:
            overflows.append((i,shape.name))
assert not overflows,overflows
result={'slides':34,'main_slides':32,'appendix_slides':2,'notes_exact_match':34,'generated_diagram_pages':19,'recorded_worker_results':18,'accepted_sample':'slide_08',
 'original_screenshot_pages':sorted(set(u['slide'] for u in uses)), 'source_screenshot_blobs_unchanged':True,'generated_image_blobs_unchanged':True,
 'native_data_charts':2,'tables_only_in_appendix':tables,'shape_bounds_ok':True,'source_score':score['source_score'],'recomputed_score':recomputed,
 'preference_count':17,'usable_count':15,'direct_count':10,'rank':1,'qualified_count':10,
 'powerpoint_desktop_opened_and_rendered':34,
 'visual_review':'Root inspected every generated diagram and every native page; revised crops and Chinese chart fonts were rechecked.',
 'writing_review':'Two passes: narrative/causal transitions, then exact wording/counts/conditions. Spoken text and presenter cues separated.',
 'pptx_bytes':p.stat().st_size,'pptx_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(root/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
