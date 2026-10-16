import { useId, useRef, useState } from 'react';
import { api } from '../api/client';
import type { Bootstrap, Draft, EntityType, EvidenceCollection, TaskInput, UploadKind, UploadResult, Workflow } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge, Icon } from './UI';
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
    ...(startWithData ? { library_id: null } : {}), evidence_mode: 'existing_only', evaluation_mode: 'staged' });
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
    change({ entity_type, library_id: null, source_task_id: null, evidence_upload_id: null, evidence_mode: 'existing_only' });
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
    if (inFlight.current || !input.objective.trim() || uploadPending || (action === 'launch' && missingMeasurements)) return;
    inFlight.current = true; setBusy(action); setMessage('');
    const payload = { ...input, entity_type: entityType, workers: bootstrap.defaults.workers, budget_usd: bootstrap.defaults.budget_usd,
      targets: targets.split(/[\n,]+/).map(target => target.trim()).filter(Boolean) };
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
    <div className="composer-intro"><span className="composer-kicker">{t('Your research, your data', '自定义目标，使用自己的数据')}</span><h2>{t('Start with a question', '从研究问题开始')}</h2><p>{t('Describe what you want to compare. Then choose a saved library or import candidates and measurements.', '先说明希望比较和解决的问题，再选择已有候选库或导入候选与测量数据。')}</p></div>
    {input.revision_of_task_id && <p className="notice">{t('Save changes as a new research version. Earlier tasks and results remain available.', '修改内容将作为新研究版本保存，早期任务与结果继续保留。')}</p>}
    {!!bootstrap.drafts?.length && <label>{t('Continue a saved draft', '继续编辑草稿')}<select value={draftId || ''} onChange={event => selectDraft(event.target.value)}><option value="">{t('New research', '新建研究')}</option>{bootstrap.drafts.map(draft => <option key={draft.draft_id} value={draft.draft_id}>{draft.input.title || draft.input.objective.slice(0, 90)}</option>)}</select></label>}
    <label className="goal-label" htmlFor={objectiveId}>{t('Research objective', '研究目标')}</label>
    <textarea id={objectiveId} className="goal-input" rows={5} value={input.objective} onChange={event => change({ objective: event.target.value })} placeholder={t('What should a useful candidate achieve? Which properties or constraints matter?', '有价值的候选应达到什么目标？哪些性质或约束最重要？')} required />
    <p className="field-note">{t('Your wording is preserved. Criteria are developed from an empty set for the new research.', '保留你的目标原文，新研究从空标准集合开始生成。')}</p>
    <div className="form-columns"><label>{t('Research title', '研究名称')} <span>{t('optional', '可选')}</span><input value={input.title || ''} onChange={event => change({ title: event.target.value })} /></label><label>{t('What are you comparing?', '比较对象类型')}<select value={entityType} onChange={event => setDomain(event.target.value as EntityType)}><option value="drug">{t('Drugs & small molecules', '药物与小分子')}</option><option value="carrier">{t('Carriers & formulations', '载体与制剂')}</option><option value="general">{t('Other candidates', '其他候选')}</option></select></label></div>
    <section className="research-scope"><h3>{t('Research scope', '研究范围')}</h3><div className="form-columns"><label>{entityType === 'drug' ? t('Targets or desired properties', '靶点或目标性质') : t('Desired properties', '目标性质')}<textarea rows={3} value={targets} onChange={event => setTargets(event.target.value)} placeholder={t('One target or property per line', '每行一个靶点或性质')} /></label><label>{t('Constraints', '研究约束')}<textarea rows={3} value={input.constraints || ''} onChange={event => change({ constraints: event.target.value })} placeholder={t('Required properties, exclusions or experimental conditions', '必需性质、排除条件或实验条件')} /></label></div></section>
    <section className="research-data"><div className="research-data-heading"><div><h3>{t('Candidates & evidence', '候选与证据')}</h3><p>{t('Choose the population and the observations the research may use.', '明确本次比较的候选范围，以及研究可使用的观测数据。')}</p></div><button type="button" onClick={() => { setImportKind('candidates'); setImportOpen(true); }}><Icon name="upload" size={15} />{t('Import CSV', '导入 CSV')}</button></div>
      <label>{t('Candidate library', '候选库')}<select value={input.library_id || ''} onChange={event => setLibrary(event.target.value || null)}><option value="">{entityType === 'drug' && !startWithData ? t('Use the configured library', '使用已配置的候选库') : t('Choose or import a candidate library', '选择或导入候选库')}</option>{libraries.map(library => <option key={library.id} value={library.id}>{library.label}{library.count != null ? ` · ${library.count.toLocaleString()}` : ''}</option>)}{input.library_id && !libraries.some(library => library.id === input.library_id) && <option value={input.library_id}>{t('Saved candidate library', '已保存候选库')}</option>}</select></label>
      {entityType !== 'drug' && <p className="notice">{t('This research uses your uploaded candidate properties and evidence. Drug-specific databases and ADMET lookups are not applied to carriers or other entities.', '此研究使用你上传的候选性质与证据。载体和其他对象不套用药物专用数据库或 ADMET 查询。')}</p>}
      <label>{usesUploadedData ? t('Additional saved evidence', '补充已有证据') : t('Saved evidence collection', '已有证据集合')}{usesUploadedData && <span>{t('optional', '可选')}</span>}<select value={input.source_task_id || ''} onChange={event => change({ source_task_id: event.target.value || null })}><option value="">{usesUploadedData ? t('Use only the uploaded observations', '仅使用上传的观测数据') : t('Choose a collection, or import measurements below', '选择证据集合，或在下方导入测量')}</option>{bootstrap.evidence_sources.map(source => <option key={source.task_id} value={source.task_id}>{collections[source.task_id]?.label || source.label}</option>)}{input.source_task_id && !bootstrap.evidence_sources.some(source => source.task_id === input.source_task_id) && <option value={input.source_task_id}>{collections[input.source_task_id]?.label || t('Previously bound evidence collection', '原已绑定证据集合')}</option>}</select></label>
      {input.source_task_id && <EvidenceCollectionCard taskId={input.source_task_id} initial={bootstrap.evidence_sources.find(source => source.task_id === input.source_task_id)} bound editable={bootstrap.operations_enabled !== false && !!bootstrap.operation_token} onResolved={collection => setCollections(previous => previous[collection.task_id]?.label === collection.label ? previous : { ...previous, [collection.task_id]: collection })} onSaved={onDataChanged} />}
      <div className="measurement-selection"><div><strong>{input.evidence_upload_id ? measurements?.label || t('Saved measurement table', '已保存测量表') : t('Have your own measurements?', '有自己的测量数据？')}</strong><p>{input.evidence_upload_id ? t('These observations are bound to the selected candidate library.', '这些观测已绑定所选候选库。') : t('Upload property values, experimental conditions and sources. Measured, derived and predicted values keep their separate basis.', '上传性质数值、实验条件和来源，实测、推导与预测依据分别保留。')}</p></div><button type="button" onClick={() => { setImportKind('measurements'); setImportOpen(true); }}>{input.evidence_upload_id ? t('Replace measurements', '替换测量表') : t('Add measurements CSV', '添加测量 CSV')}</button>{input.evidence_upload_id && <button type="button" className="text-button" onClick={() => { change({ evidence_upload_id: null }); setMeasurements(undefined); }}>{t('Remove', '移除')}</button>}</div>
      {importOpen && <div className="csv-workspace"><div className="row spread"><strong>{t('Import data step by step', '分步导入数据')}</strong><button type="button" className="text-button" onClick={() => { setImportOpen(false); setUploadPending(false); }}>{t('Close import', '收起导入')}</button></div><CsvImportWizard key={importKind} initialKind={importKind} entityType={entityType} libraryId={input.library_id} onCommitted={imported} onPending={setUploadPending} /></div>}
      {(input.library_id?.startsWith('upload:') || input.evidence_upload_id) && <Audit data={{ library_id: input.library_id, evidence_upload_id: input.evidence_upload_id, entity_type: entityType }} title={t('Selected data record', '所选数据记录')} />}
    </section>
    <details className="form-details"><summary>{t('Evaluation options', '评估选项')}</summary><div className="form-columns"><label>{t('Evidence', '证据')}<select value={input.evidence_mode} onChange={event => change({ evidence_mode: event.target.value as TaskInput['evidence_mode'] })}><option value="existing_only">{t('Use saved or uploaded evidence', '使用已有或上传的证据')}</option>{entityType === 'drug' && !usesUploadedData && <option value="retrieve">{t('Search and read new evidence', '检索并阅读新证据')}</option>}</select></label><label>{t('Evaluation', '评估')}<select value={input.evaluation_mode} onChange={event => change({ evaluation_mode: event.target.value as TaskInput['evaluation_mode'] })}><option value="staged">{t('Staged screening', '分阶段筛选')}</option><option value="full">{t('Evaluate every condition', '评估每项条件')}</option></select></label></div><label>{t('Reference candidate', '参考候选')} <span>{t('optional', '可选')}</span><input value={input.reference_candidate || ''} onChange={event => change({ reference_candidate: event.target.value })} /></label><p className="field-note">{t('A reference for comparing results. It does not add ranking weight.', '用于结果对照的参考候选，不增加排名权重。')}</p></details>
    <div className="policy-note"><Badge label={input.evidence_mode === 'existing_only' ? t('Saved evidence', '已有证据') : t('Evidence retrieval', '检索证据')} /><Badge label={input.evaluation_mode === 'staged' ? t('Staged screening', '分阶段筛选') : t('Full assessment', '完整评估')} /><span>{t('Concurrency', '并发')} {bootstrap.defaults.workers ?? '—'} · {t('Cost cap', '费用上限')} {bootstrap.defaults.budget_usd != null ? `$${bootstrap.defaults.budget_usd}` : '—'}. {t('Predictions assist the assessment; they do not exclude candidates.', '预测辅助评估，不作为淘汰候选的硬条件。')}</span></div>
    {missingMeasurements && <p className="notice">{t('The candidate list is ready. Add observations for these candidates before starting the research.', '候选表已就绪，请先为这些候选添加观测数据，再开始研究。')}</p>}
    {uploadPending && <p className="field-note" role="status">{t('Finish or close the current CSV import before saving or starting.', '请先完成或收起当前 CSV 导入，再保存或开始研究。')}</p>}
    <div className="form-actions"><button type="button" disabled={!!busy || uploadPending || !input.objective.trim()} onClick={() => submit('save')}>{busy === 'save' ? t('Saving…', '保存中…') : t('Save draft', '保存草稿')}</button><button type="submit" className="primary" disabled={!!busy || uploadPending || missingMeasurements || !input.objective.trim() || (entityType !== 'drug' && !input.library_id)}><Icon name="play" size={15} />{busy === 'launch' ? t('Starting research…', '正在启动研究…') : t('Start research', '开始研究')}</button></div>
    {message && <p className="form-feedback" role="status">{message}</p>}
  </form>;
}
