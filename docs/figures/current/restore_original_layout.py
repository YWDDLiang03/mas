"""Update the accepted workflow in place, retaining its original geometry."""
from copy import deepcopy
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

OUT=Path(__file__).resolve().parent
BASE=OUT/'workflow_layout_reference.pptx'
prs=Presentation(BASE);slide=prs.slides[0]
original={s.shape_id:(s.left,s.top,s.width,s.height) for s in slide.shapes}
by_name={s.name:s for s in slide.shapes}
changed_geometry=set()

def px(value):return Inches(value/96)

def replace(name,text,size=None,bold=None,color=None,align=None,y=None,h=None):
    shape=by_name[name]
    tf=shape.text_frame
    ppr=deepcopy(tf.paragraphs[0]._p.pPr)
    rpr=deepcopy(tf.paragraphs[0].runs[0]._r.rPr) if tf.paragraphs[0].runs else None
    tf.text=text
    for p in tf.paragraphs:
        if ppr is not None:
            if p._p.pPr is not None:p._p.remove(p._p.pPr)
            p._p.insert(0,deepcopy(ppr))
        if align is not None:p.alignment=align
        for r in p.runs:
            if r._r.rPr is not None:r._r.remove(r._r.rPr)
            if rpr is not None:r._r.insert(0,deepcopy(rpr))
            if size is not None:r.font.size=Pt(size)
            if bold is not None:r.font.bold=bold
            if color is not None:r.font.color.rgb=RGBColor.from_string(color)
    if y is not None:shape.top=px(y);changed_geometry.add(shape.shape_id)
    if h is not None:shape.height=px(h);changed_geometry.add(shape.shape_id)
    return shape

def duplicate(shape,name,behind_text=False):
    element=deepcopy(shape._element)
    meta=element.xpath('.//p:cNvPr')[0]
    meta.set('id',str(max(s.shape_id for s in slide.shapes)+1));meta.set('name',name)
    tree=slide.shapes._spTree
    if behind_text:tree.insert(tree.index(shape._element)+1,element)
    else:tree.insert_element_before(element,'p:extLst')
    new=next(s for s in slide.shapes if s.name==name);by_name[name]=new;return new

replace('TextBox 152','Recorded task example')
replace('TextBox 171','Not used (22)')
replace('TextBox 174','Condition\nrequirement (1)')
replace('TextBox 188','3 rounds: 147 → 68 → 53',size=11.25)
replace('TextBox 189','53 = 18 enabled decision rules + 13 contextual observations + 22 items not used')
replace('TextBox 192','Eligibility requirements (6)')
replace('TextBox 193','All required: 1 oral condition + 5 target-evidence requirements')
replace('TextBox 200','17 scored; 5 also required for admission',size=10.5)
replace('TextBox 204','≥ 50%')
replace('TextBox 217','Scoring threshold: ≤ 500 Da')
replace('TextBox 223','480.6 Da ≤ 500 Da')

# The original left-hand outcome box accommodates the two current non-ranked
# groups. All panel boundaries, input boxes and the eligible/ranking path stay put.
old_box=next(s for s in slide.shapes if all(abs(v/914400*96-w)<.1
    for v,w in zip((s.left,s.top,s.width,s.height),(1012,286,240,124))))
lower=duplicate(old_box,'Excluded outcome',behind_text=True)
lower.top=px(353);lower.height=px(57)
lower.fill.solid();lower.fill.fore_color.rgb=RGBColor.from_string('FBEFF0')
lower.line.color.rgb=RGBColor.from_string('AE5260')
old_box.height=px(55);changed_geometry.add(old_box.shape_id)
old_box.fill.solid();old_box.fill.fore_color.rgb=RGBColor.from_string('FCF5E8')
old_box.line.color.rgb=RGBColor.from_string('A47B32')
replace('TextBox 194','Evidence incomplete (1,305)',size=12.75,color='956C29',y=290,h=27)
replace('TextBox 195','Partial support; no condition failed',size=10.5,color='63717C',y=317,h=21)
replace('TextBox 196','Excluded (1,862)',size=13.75,bold=True,color='AE5260',align=PP_ALIGN.CENTER,y=356,h=27)
duplicate(by_name['TextBox 195'],'Excluded reason')
replace('Excluded reason','Condition failed or no admission support',size=10,y=383,h=22,color='63717C')
for i,(a,b) in enumerate(zip([(1261,260),(1261,381)],[(1261,381),(1252,381)])):
    line=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,px(a[0]),px(a[1]),px(b[0]),px(b[1]))
    line.name=f'Added exclusion branch {i}';line.line.color.rgb=RGBColor.from_string('31516B');line.line.width=Pt(.75)
    if i==1:
        end=OxmlElement('a:tailEnd');end.set('type','triangle');end.set('w','sm');end.set('len','sm');line.line._get_or_add_ln().append(end)

# Five task-bound target criteria supply required evidence as well as scores.
# The local branch uses existing whitespace; all original boxes keep position.
evidence_path=[(998,292),(1007,292),(1007,261),(1055,261),(1055,245)]
for i,(a,b) in enumerate(zip(evidence_path,evidence_path[1:])):
    line=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,px(a[0]),px(a[1]),px(b[0]),px(b[1]))
    line.name=f'Required evidence from scored criteria {i}'
    line.line.color.rgb=RGBColor.from_string('267549');line.line.width=Pt(.75)
    if i==len(evidence_path)-2:
        end=OxmlElement('a:tailEnd');end.set('type','triangle');end.set('w','sm');end.set('len','sm');line.line._get_or_add_ln().append(end)

for shape in slide.shapes:
    for effect in shape._element.xpath('.//a:effectRef'):effect.set('idx','0')
    props=shape._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}spPr')
    if props is not None and props.find('{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst') is None:
        props.append(OxmlElement('a:effectLst'))

unplanned=[]
for shape in slide.shapes:
    if shape.shape_id in original and shape.shape_id not in changed_geometry:
        if original[shape.shape_id]!=(shape.left,shape.top,shape.width,shape.height):unplanned.append(shape.name)
assert not unplanned,unplanned
slide.notes_slide.notes_text_frame.text=json.loads((OUT/'captions.json').read_text(encoding='utf-8'))['figure_1_workflow']
prs.save(OUT/'TRIAGE_workflow_editable.pptx')
(OUT/'workflow-layout-preservation.json').write_text(json.dumps({'reference':str(BASE.name),
    'original_shapes':len(original),'original_geometries_retained':len(set(original)-changed_geometry),
    'local_outcome_geometries_updated':len(set(original)&changed_geometry),'unplanned_geometry_changes':unplanned,
    'page_inches':[16,10+2/3],'panel_layout':'a upper left; b upper right; c below',
    'updates':'Original outcome area split locally; panel geometry, six proposal cards, criterion and observation paths retained.'},indent=2)+'\n',encoding='utf-8')
print('Workflow restored to its original three-panel layout.')
