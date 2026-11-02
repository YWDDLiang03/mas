import { useId, useRef, useState } from 'react';
import { api } from '../api/client';
import type { Bootstrap, Draft, EntityType, EvidenceCollection, TaskInput, UploadKind, UploadResult, Workflow } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge, Icon } from './UI';
import { CdesOption } from './CdesOption';
import { CsvImportWizard } from './CsvImportWizard';
import { EvidenceCollectionCard } from './EvidenceCollectionCard';

export function GoalComposer({ bootstrap, initialInput, startWithData = false, onSaved, onLaunched, onDataChanged }: {
  bootstrap: Bootstrap; initialInput?: TaskInput; startWithData?: boolean;
  onSaved: (draft: Draft) => void; onLaunched: (workflow: Workflow) => void; onDataChanged?: () => void;
}) {
  const { t } = useI18n();
  const objectiveId = useId();
  const freshInput = (): TaskInput => ({ ...bootstrap.defaults, title: '', objective: '', entity_type: 'drug',
    revision_of_task_id: undefined, source_task_id: null, evidence_upload_id: null, targets: [], constraints: '', reference_candidate: '',
    ...(startWithData ? { library_id: null } : {}), evidence_mode: startWithData ? 'existing_only' : 'retrieve', evaluation_mode: 'staged' });
  const [input, setInput] = useState<TaskInput>(() => initialInput ? { ...initialInput } : freshInput());
  const [draftId, setDraftId] = useState<string>();
  const [targets, setTargets] = useState(initialInput?.targets?.join('\n') || '');
  const [busy, setBusy] = useState<'save' | 'launch' | null>(null), [message, setMessage] = useState('');
  const [importKind, setImportKind] = useState<UploadKind>('candidates');
  const [importOpen, setImportOpen] = useState(startWithData);
  const [uploadPending, setUploadPending] = useState(false);
  const [ownLibraries, setOwnLibraries] = useState<UploadResult[]>([]);
  const [measurements, setMeasurements] = useState<UploadResult>();
  const [collections, setCollections] = useState<Record<string, EvidenceCollection>>({});
  const inFlight = useRef(false);
  const submission = useRef<{ signature: string; key: string }>();
  const entityType = input.entity_type || 'drug';
  const targetList = targets.split(/[\n,]+/).map(target => target.trim()).filter(Boolean);
  const targetObjective = targetList.length ? `${entityType === 'drug' ? 'Identify candidate drugs in the selected library for the following target profile' : 'Compare candidates in the selected library for the following properties'}: ${targetList.join(', ')}. Assess the supplied requirements using available evidence.` : '';
  const objective = input.objective.trim() || targetObjective;
  const cdesCollections = bootstrap.prediction_modules?.cdes.collections || [];
  const cdesSource = input.cdes_source_id || (cdesCollections.length === 1 ? cdesCollections[0].id : '');
  const cdesNeedsSource = input.cdes_enabled && (!cdesSource || entityType !== 'drug');
  const missingSavedEvidence = input.evidence_mode === 'existing_only' && !input.source_task_id && !input.evidence_upload_id;
  const missingMeasurements = !!input.library_id?.startsWith('upload:') && !input.evidence_upload_id;
  const usesUploadedData = !!input.evidence_upload_id || !!input.library_id?.startsWith('upload:');
  const libraries = [...bootstrap.libraries, ...ownLibraries.filter(item => !bootstrap.libraries.some(library => library.id === item.library_id))
    .map(item => ({ id: item.library_id!, label: item.label, count: item.row_count, entity_type: item.entity_type }))]
    .filter(library => entityType === 'drug' || (library.id.startsWith('upload:') && (!library.entity_type || library.entity_type === entityType)));
  function change(update: Partial<TaskInput>) { setInput(previous => ({ ...previous, ...update })); setMessage(''); }
  function selectDraft(id: string) {
    const draft = bootstrap.drafts.find(item => item.draft_id === id);
    setDraftId(draft?.draft_id); setTargets(draft?.input.targets?.join('\n') || '');
    setInput(draft ? { ...draft.input } : freshInput()); setMeasurements(undefined);
    setImportOpen(!!draft?.input.evidence_upload_id || !!draft?.input.library_id?.startsWith('upload:'));
    setMessage(''); submission.current = undefined;
  }
  function setDomain(entity_type: EntityType) {
    change({ entity_type, cdes_enabled: false, cdes_source_id: null, library_id: null, source_task_id: null, evidence_upload_id: null, evidence_mode: 'existing_only' });
    setMeasurements(undefined); setImportKind('candidates'); setImportOpen(true);
  }
  function setLibrary(library_id: string | null) {
    change({ library_id, evidence_upload_id: null, ...(library_id?.startsWith('upload:') ? { source_task_id: null, evidence_mode: 'existing_only' } : {}) }); setMeasurements(undefined);
  }
  function imported(kind: UploadKind, result: UploadResult) {
    if (kind === 'candidates' && result.library_id) {
      setOwnLibraries(previous => [...previous.filter(item => item.library_id !== result.library_id), { ...result, entity_type: entityType }]);
      change({ library_id: result.library_id, source_task_id: null, evidence_upload_id: null, evidence_mode: 'existing_only' }); setMeasurements(undefined); setImportKind('measurements'); setMessage(t('Candidate library saved. Add its measurements next.', '候选库已保存，接下来添加对应测量。'));
    } else if (kind === 'measurements' && result.evidence_upload_id) {
      change({ evidence_upload_id: result.evidence_upload_id, source_task_id: null, evidence_mode: 'existing_only' }); setMeasurements(result);
    }
    onDataChanged?.();
  }
  async function submit(action: 'save' | 'launch') {
    if (inFlight.current || !objective || uploadPending || (action === 'launch' && (missingMeasurements || cdesNeedsSource || missingSavedEvidence))) return;
    inFlight.current = true; setBusy(action); setMessage('');
    const payload = { ...input, objective, original_objective: input.objective, objective_source: input.objective.trim() ? 'user_text' : 'targets_and_requirements', cdes_source_id: input.cdes_enabled ? cdesSource : null, entity_type: entityType, workers: bootstrap.defaults.workers, budget_usd: bootstrap.defaults.budget_usd,
      targets: targetList };
    try {
      if (action === 'save') { const draft = await api.saveDraft(payload, draftId); setDraftId(draft.draft_id); onSaved(draft); setMessage(t('Draft saved. Research has not started.', '草稿已保存，研究尚未启动。')); }
      else {
        const signature = JSON.stringify({ draftId, payload });
        if (!submission.current || submission.current.signature !== signature) submission.current = { signature, key: crypto.randomUUID() };
        const workflow = await api.launch(payload, submission.current.key, draftId);
        submission.current = undefined; onLaunched(workflow);
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { inFlight.current = false; setBusy(null); }
  }
  return <form className="goal-form" onSubmit={event => { event.preventDefault(); void submit('launch'); }}>
    <div className="composer-intro"><span className="composer-kicker">{t('Targets, requirements and data', '靶点、需求与数据')}</span><h2>{entityType === 'drug' ? t('Define the drug-selection task', '定义药物筛选任务') : t('Define the candidate comparison', '定义候选比较任务')}</h2><p>{t('Specify targets and requirements, choose a candidate library, and let the agents develop the evaluation criteria.', '给定靶点与需求，选择候选库，由智能体形成评价标准并开展比较。')}</p></div>
    {input.revision_of_task_id && <p className="notice">{t('Save changes as a new research version. Earlier tasks and results remain available.', '修改内容将作为新研究版本保存，早期任务与结果继续保留。')}</p>}
    {!!bootstrap.drafts?.length && <label>{t('Continue a saved draft', '继续编辑草稿')}<select value={draftId || ''} onChange={event => selectDraft(event.target.value)}><option value="">{t('New research', '新建研究')}</option>{bootstrap.drafts.map(draft => <option key={draft.draft_id} value={draft.draft_id}>{draft.input.title || draft.input.objective.slice(0, 90)}</option>)}</select></label>}
    <section className="research-scope"><h3>{t('1 · Targets and requirements', '1 · 靶点与需求')}</h3><div className="form-columns"><label>{entityType === 'drug' ? t('Target profile', '目标靶点') : t('Desired properties', '目标性质')}<textarea rows={3} value={targets} onChange={event => setTargets(event.target.value)} placeholder={t('One target or property per line', '每行一个靶点或性质')} /></label><label>{t('Requirements and preferences', '必需条件与偏好')}<textarea rows={3} value={input.constraints || ''} onChange={event => change({ constraints: event.target.value })} placeholder={t('Required properties, exclusions or experimental conditions', '必需性质、排除条件或实验条件')} /></label></div></section>
    <label className="goal-label" htmlFor={objectiveId}>{t('Research objective or context', '研究目标或背景')} <span>{t('optional when targets are supplied', '填写靶点后可选')}</span></label>
    <textarea id={objectiveId} className="goal-input" rows={3} value={input.objective} onChange={event => change({ objective: event.target.value })} placeholder={t('Add the indication, therapeutic intent or other context for this study.', '可补充适应证、治疗意图或其他研究背景。')} />
    <p className="field-note">{t('Targets and requirements define the task. Add context to guide evidence interpretation.', '靶点与需求定义任务，补充背景有助于智能体理解证据。')}</p>
    <div className="form-columns"><label>{t('Research title', '研究名称')} <span>{t('optional', '可选')}</span><input value={input.title || ''} onChange={event => change({ title: event.target.value })} /></label><label>{t('What are you comparing?', '比较对象类型')}<select value={entityType} onChange={event => setDomain(event.target.value as EntityType)}><option value="drug">{t('Drugs & small molecules', '药物与小分子')}</option><option value="carrier">{t('Carriers & formulations', '载体与制剂')}</option><option value="general">{t('Other candidates', '其他候选')}</option></select></label></div>

    <section className="research-data"><div className="research-data-heading"><div><h3>{t('2 · Candidate library and evidence', '2 · 候选库与证据')}</h3><p>{t('Choose the population and the observations the research may use.', '明确本次比较的候选范围，以及研究可使用的观测数据。')}</p></div><button type="button" onClick={() => { setImportKind('candidates'); setImportOpen(true); }}><Icon name="upload" size={15} />{t('Import CSV', '导入 CSV')}</button></div>
      <label>{t('Candidate database / library', '候选数据库 / 候选库')}<select value={input.library_id || ''} onChange={event => setLibrary(event.target.value || null)}><option value="">{entityType === 'drug' && !startWithData ? t('Use the configured library', '使用已配置的候选库') : t('Choose or import a candidate library', '选择或导入候选库')}</option>{libraries.map(library => <option key={library.id} value={library.id}>{library.label}{library.count != null ? ` · ${library.count.toLocaleString()}` : ''}</option>)}{input.library_id && !libraries.some(library => library.id === input.library_id) && <option value={input.library_id}>{t('Saved candidate library', '已保存候选库')}</option>}</select></label>
      {entityType !== 'drug' && <p className="notice">{t('This research uses your uploaded candidate properties and evidence. Drug-specific databases and ADMET lookups are not applied to carriers or other entities.', '此研究使用你上传的候选性质与证据。载体和其他对象不套用药物专用数据库或 ADMET 查询。')}</p>}
      <label>{t('Evidence strategy', '证据获取方式')}<select value={input.evidence_mode} onChange={event => change({ evidence_mode: event.target.value as TaskInput['evidence_mode'] })}><option value="existing_only">{t('Use saved or uploaded evidence', '使用已有或上传的证据')}</option>{entityType === 'drug' && !usesUploadedData && <option value="retrieve">{t('Search and read new evidence', '检索并阅读新证据')}</option>}</select></label>
      <label>{usesUploadedData ? t('Additional saved evidence', '补充已有证据') : t('Saved evidence collection', '已有证据集合')}{(usesUploadedData || input.evidence_mode === 'retrieve') && <span>{t('optional', '可选')}</span>}<select value={input.source_task_id || ''} onChange={event => change({ source_task_id: event.target.value || null })}><option value="">{usesUploadedData ? t('Use only the uploaded observations', '仅使用上传的观测数据') : input.evidence_mode === 'retrieve' ? t('Start with new evidence retrieval', '从新证据检索开始') : t('Choose a collection, or import measurements below', '选择证据集合，或在下方导入测量')}</option>{bootstrap.evidence_sources.map(source => <option key={source.task_id} value={source.task_id}>{collections[source.task_id]?.label || source.label}</option>)}{input.source_task_id && !bootstrap.evidence_sources.some(source => source.task_id === input.source_task_id) && <option value={input.source_task_id}>{collections[input.source_task_id]?.label || t('Previously bound evidence collection', '原已绑定证据集合')}</option>}</select></label>
      {input.source_task_id && <EvidenceCollectionCard taskId={input.source_task_id} initial={bootstrap.evidence_sources.find(source => source.task_id === input.source_task_id)} bound editable={bootstrap.operations_enabled !== false && !!bootstrap.operation_token} onResolved={collection => setCollections(previous => previous[collection.task_id]?.label === collection.label ? previous : { ...previous, [collection.task_id]: collection })} onSaved={onDataChanged} />}
      <div className="measurement-selection"><div><strong>{input.evidence_upload_id ? measurements?.label || t('Saved measurement table', '已保存测量表') : t('Have your own measurements?', '有自己的测量数据？')}</strong><p>{input.evidence_upload_id ? t('These observations are bound to the selected candidate library.', '这些观测已绑定所选候选库。') : t('Upload property values, experimental conditions and sources. Measured, derived and predicted values keep their separate basis.', '上传性质数值、实验条件和来源，实测、推导与预测依据分别保留。')}</p></div><button type="button" onClick={() => { setImportKind('measurements'); setImportOpen(true); }}>{input.evidence_upload_id ? t('Replace measurements', '替换测量表') : t('Add measurements CSV', '添加测量 CSV')}</button>{input.evidence_upload_id && <button type="button" className="text-button" onClick={() => { change({ evidence_upload_id: null }); setMeasurements(undefined); }}>{t('Remove', '移除')}</button>}</div>
      {importOpen && <div className="csv-workspace"><div className="row spread"><strong>{t('Import data step by step', '分步导入数据')}</strong><button type="button" className="text-button" onClick={() => { setImportOpen(false); setUploadPending(false); }}>{t('Close import', '收起导入')}</button></div><CsvImportWizard key={importKind} initialKind={importKind} entityType={entityType} libraryId={input.library_id} onCommitted={imported} onPending={setUploadPending} /></div>}
      {(input.library_id?.startsWith('upload:') || input.evidence_upload_id) && <Audit data={{ library_id: input.library_id, evidence_upload_id: input.evidence_upload_id, entity_type: entityType }} title={t('Selected data record', '所选数据记录')} />}
    </section>
    {entityType === 'drug' && <CdesOption checked={!!input.cdes_enabled} onChange={cdes_enabled => change({ cdes_enabled, cdes_source_id: cdesSource || null })} source={cdesSource} onSource={cdes_source_id => change({ cdes_source_id })} collections={cdesCollections} />}
    <section className="task-flow-preview"><h3>{t('Planned workflow', '本次流程')}</h3><div className="task-flow-steps"><span>{t('Targets & requirements', '靶点与需求')}</span><i>→</i><span>{t('Criteria & review', '标准生成与审查')}</span><i>→</i><span>{t('Database screening & ranking', '数据库筛选与排序')}</span>{input.cdes_enabled && <><i>→</i><span className="optional-step">CDES · {t('target profiles', '靶点分析')}</span></>}<i>→</i><span>{t('Results & sources', '结果与依据')}</span></div></section>
    {!input.objective.trim() && targetObjective && <p className="target-task-summary"><strong>{t('Task summary', '任务摘要')}</strong><br />{targetObjective}</p>}
    {cdesNeedsSource && <p className="notice">{t('Choose an available CDES collection or switch the optional module off.', '请选择可用的 CDES 集合，或关闭该可选模块。')}</p>}
    <details className="form-details"><summary>{t('Evaluation options', '评估选项')}</summary><div className="form-columns"><label>{t('Evaluation', '评估')}<select value={input.evaluation_mode} onChange={event => change({ evaluation_mode: event.target.value as TaskInput['evaluation_mode'] })}><option value="staged">{t('Staged screening', '分阶段筛选')}</option><option value="full">{t('Evaluate every condition', '评估每项条件')}</option></select></label></div><label>{t('Reference candidate', '参考候选')} <span>{t('optional', '可选')}</span><input value={input.reference_candidate || ''} onChange={event => change({ reference_candidate: event.target.value })} /></label><p className="field-note">{t('A reference for comparing results. It does not add ranking weight.', '用于结果对照的参考候选，不增加排名权重。')}</p></details>
    <div className="policy-note"><Badge label={input.evidence_mode === 'existing_only' ? t('Saved evidence', '已有证据') : t('Evidence retrieval', '检索证据')} /><Badge label={input.evaluation_mode === 'staged' ? t('Staged screening', '分阶段筛选') : t('Full assessment', '完整评估')} /><span>{t('Concurrency', '并发')} {bootstrap.defaults.workers ?? '—'} · {t('Cost cap', '费用上限')} {bootstrap.defaults.budget_usd != null ? `$${bootstrap.defaults.budget_usd}` : '—'}. {t('Predictions assist the assessment; they do not exclude candidates.', '预测辅助评估，不作为淘汰候选的硬条件。')}</span></div>
    {missingSavedEvidence && <p className="notice">{t('Select saved evidence or choose new evidence retrieval.', '请选择已有证据，或切换为新证据检索。')}</p>}
    {missingMeasurements && <p className="notice">{t('The candidate list is ready. Add observations for these candidates before starting the research.', '候选表已就绪，请先为这些候选添加观测数据，再开始研究。')}</p>}
    {uploadPending && <p className="field-note" role="status">{t('Finish or close the current CSV import before saving or starting.', '请先完成或收起当前 CSV 导入，再保存或开始研究。')}</p>}
    <div className="form-actions"><button type="button" disabled={!!busy || uploadPending || !objective} onClick={() => submit('save')}>{busy === 'save' ? t('Saving…', '保存中…') : t('Save draft', '保存草稿')}</button><button type="submit" className="primary" disabled={!!busy || uploadPending || missingMeasurements || cdesNeedsSource || missingSavedEvidence || !objective || (entityType !== 'drug' && !input.library_id)}><Icon name="play" size={15} />{busy === 'launch' ? t('Starting research…', '正在启动研究…') : t('Start research', '开始研究')}</button></div>
    {message && <p className="form-feedback" role="status">{message}</p>}
  </form>;
}
