import { useState } from 'react';
import { api } from '../api/client';
import type { EvidenceSource, Library, Overview, Stage, TaskInput } from '../api/types';
import { operationText, phaseText, useI18n } from '../i18n';
import { useResource } from '../hooks/useResource';
import { CriteriaEvolution, enabledCriteriaCount, stageCountScope } from '../components/CriteriaEvolution';
import { ResearchLink, type ResearchNavigate } from '../components/ResearchLinks';
import { Audit, Badge, dateText, Empty, ErrorNotice, Icon, Loading, Panel, valueText } from '../components/UI';

export function copyResearchSetup(input: TaskInput): TaskInput {
  return {
    title: input.title, objective: input.objective,
    targets: input.targets ? [...input.targets] : undefined, constraints: input.constraints,
    library_id: input.library_id, source_task_id: input.source_task_id,
    entity_type: input.entity_type, evidence_upload_id: input.evidence_upload_id,
    reference_candidate: input.reference_candidate,
    evidence_mode: input.evidence_mode, evaluation_mode: input.evaluation_mode,
  };
}

function changedCriterion(value: unknown): { name?: string; ref?: string } {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const record = value as Record<string, unknown>;
  const name = typeof record.name === 'string' && !/^(cri_|attr_|rule_)/.test(record.name) ? record.name : undefined;
  const ref = [record.detail_ref, record.rule_ref, record.attribute_ref].find(value => typeof value === 'string' && value);
  if (typeof ref === 'string') return { name, ref };
  return { name, ref: typeof record.criterion_id === 'string' && typeof record.version === 'number' ? `${record.criterion_id}@v${record.version}` : undefined };
}

export function StageTable({ stages, selected, onSelect }: { stages: Stage[]; selected?: string; onSelect?: (id: string) => void }) {
  const { t } = useI18n();
  return <div className="table-scroll stage-records"><table className="stage-table"><thead><tr><th>{t('Stage', '阶段')}</th><th>{t('Iteration', '迭代')}</th><th>{t('Before → after', '前 → 后')}</th><th>{t('Added', '新增')}</th><th>{t('Revised', '修改')}</th><th>{t('Merged', '合并')}</th><th>{t('Removed', '撤回')}</th><th>{t('State', '状态')}</th></tr></thead><tbody>{stages.map(stage => <tr key={stage.stage_id} className={selected === stage.stage_id ? 'selected' : ''}><td>{onSelect ? <button className="text-button" onClick={() => onSelect(stage.stage_id)}>{phaseText(stage.stage, t)}</button> : phaseText(stage.stage, t)}<p className="cell-note">{stageCountScope(stage, t)}</p></td><td className="numeric">{stage.iteration ?? '—'}</td><td className="numeric">{valueText(stage.before_count)} <span className="muted">→</span> <strong>{valueText(stage.after_count)}</strong></td><td className="numeric">{valueText(stage.added)}</td><td className="numeric">{valueText(stage.modified)}</td><td className="numeric">{valueText(stage.merged)}</td><td className="numeric">{valueText(stage.removed)}</td><td><Badge state={stage.state} /></td></tr>)}</tbody></table></div>;
}

export function OverviewPage({ task, revision, enabled, onCriteria, onEdit, onOwnData, onNewWithSetup, libraries, evidenceSources, onResults, onNavigate }: {
  task: string; revision: number; enabled: boolean; onCriteria: () => void; onEdit: (input: TaskInput) => void;
  onOwnData: () => void; onNewWithSetup: (input: TaskInput) => void; libraries: Library[];
  evidenceSources: EvidenceSource[]; onResults: (snapshot: string) => void; onNavigate: ResearchNavigate;
}) {
  const { t, language } = useI18n();
  const [editing, setEditing] = useState(false);
  const [scope, setScope] = useState<TaskInput>();
  const [targets, setTargets] = useState('');
  const resource = useResource<Overview>(`${task}/overview`, signal => api.overview(task, signal), revision);
  const boundSourceId = resource.data?.input?.source_task_id || '';
  const boundSource = useResource<EvidenceSource>(boundSourceId && !evidenceSources.some(item => item.task_id === boundSourceId) ? `collection/${boundSourceId}` : null, signal => api.evidenceCollection(boundSourceId, signal), revision);
  if (!resource.data) return resource.error ? <ErrorNotice message={resource.error} retry={resource.refresh} /> : <Loading />;
  const data = resource.data;
  const library = libraries.find(item => item.id === data.input?.library_id);
  const evidenceSource = evidenceSources.find(item => item.task_id === data.input?.source_task_id) || boundSource.data;
  const snapshots = [...data.snapshots].sort((a, b) => (Date.parse(b.published_at) || 0) - (Date.parse(a.published_at) || 0));
  const latest = snapshots.find(snapshot => snapshot.snapshot_id === data.task.latest_snapshot_id) || snapshots[0];
  const evaluationCount = enabledCriteriaCount(data);
  const coreCount = data.summary.enabled_core_count;
  const recentChanges = [...data.recent_changes].sort((a, b) => (Date.parse(b.at || '') || 0) - (Date.parse(a.at || '') || 0)).slice(0, 5);
  function editScope() { if (data.input) { setScope({ ...data.input }); setTargets(data.input.targets?.join('\n') || ''); setEditing(true); } }
  return <>
    <ErrorNotice message={resource.error} retry={resource.refresh} />
    <section className="research-heading">
      <div className="research-heading-top"><div><div className="eyebrow">{t('Current research', '当前研究')}</div><h1>{data.task.title || t('Untitled research', '未命名研究')}</h1></div><div className="research-heading-actions">
        {latest ? <ResearchLink className="button primary" to={{ task, view: 'candidates', snapshot: latest.snapshot_id }} onNavigate={onNavigate}><Icon name="candidates" size={16} />{t('View results', '查看结果')}<Icon name="arrow" size={15} /></ResearchLink> : <button className="primary" onClick={onCriteria}>{t('Explore criteria', '查看标准')}<Icon name="arrow" size={15} /></button>}
        <details className="research-options"><summary>{t('Research options', '研究选项')}<Icon name="chevron" size={13} /></summary><div onClick={event => event.currentTarget.parentElement?.removeAttribute('open')}><button disabled={!enabled || !data.input} onClick={editScope}>{t('Edit objective & scope', '编辑目标与范围')}</button><button disabled={!enabled || !data.input} onClick={() => { const setup = data.new_study_input || data.input; if (setup) onNewWithSetup(copyResearchSetup(setup)); }}>{t('New study with this setup', '按此设置新建研究')}</button><button disabled={!enabled} onClick={onOwnData}>{t('Start with your own data', '使用自己的数据新建')}</button></div></details>
      </div></div>
      {editing && scope ? <div className="overview-scope-editor"><label>{t('Research objective', '研究目标')}<textarea rows={4} value={scope.objective} onChange={event => setScope({ ...scope, objective: event.target.value })} /></label><div className="form-columns"><label>{t('Targets or desired properties', '靶点或目标性质')}<textarea rows={3} value={targets} onChange={event => setTargets(event.target.value)} /></label><label>{t('Constraints', '研究约束')}<textarea rows={3} value={scope.constraints || ''} onChange={event => setScope({ ...scope, constraints: event.target.value })} /></label></div><p className="field-note">{t('Changes create a new research version. This task and its saved results stay available.', '修改将创建新研究版本，此任务及已保存结果继续保留。')}</p><div className="row"><button className="primary" disabled={!scope.objective.trim()} onClick={() => onEdit({ ...scope, targets: targets.split(/[\n,]+/).map(value => value.trim()).filter(Boolean) })}>{t('Continue with these changes', '使用修改后的内容继续')}</button><button onClick={() => setEditing(false)}>{t('Cancel', '取消')}</button></div></div> : <>
        <h2 className="scope-label">{t('Research objective', '研究目标')}</h2><p className="research-objective">{data.task.objective}</p>
        <details className="research-scope-details"><summary>{t('Targets, data & constraints', '靶点、数据与约束')}<span>{data.summary.candidate_count.toLocaleString()} {t('candidates', '个候选')}{data.input?.targets?.length ? ` · ${data.input.targets.length} ${t('targets / properties', '项靶点 / 性质')}` : ''}</span></summary><div className="scope-overview">
          {data.input?.targets?.length ? <div><span>{t('Targets / properties', '靶点 / 性质')}</span><div className="scope-tags">{data.input.targets.map((target, index) => <span key={index}>{target}</span>)}</div></div> : null}{data.input?.constraints && <div><span>{t('Constraints', '约束')}</span><p>{data.input.constraints}</p></div>}
          <div><span>{t('Candidate data', '候选数据')}</span><p>{library?.label || (data.input?.library_id?.startsWith('upload:') ? t('Uploaded candidate library', '上传的候选库') : t('Recorded candidate library', '已记录候选库'))} · {data.summary.candidate_count.toLocaleString()}</p></div>
          <div><span>{t('Evidence', '证据')}</span><p>{data.input?.evidence_upload_id ? t('Uploaded measurements', '上传的测量表') : evidenceSource?.label || t('Saved research evidence', '已保存的研究证据')}</p><ResearchLink to={{ task, view: 'evidence' }} onNavigate={onNavigate}>{t('Explore sources', '查看来源')} →</ResearchLink></div>
        </div><Audit data={data.task} title={t('Task record', '任务记录')} /></details>
      </>}
    </section>
    <div className="stat-grid overview-stats">
      <ResearchLink className="stat-card" to={{ task, view: 'criteria' }} onNavigate={onNavigate}><span>{coreCount != null ? t('Core criteria', '核心标准') : t('Registered criteria', '注册标准')}</span><strong>{coreCount ?? data.summary.active_registered_count ?? '—'}</strong><small>{data.summary.enabled_hard_count != null ? `${data.summary.enabled_hard_count} ${t('required', '硬条件')} · ${data.summary.enabled_preference_count ?? '—'} ${t('preferences', '排序偏好')}` : t('Explore the current criteria', '查看当前标准')}</small><Icon name="arrow" size={15} /></ResearchLink>
      <ResearchLink className="stat-card" to={{ task, view: 'candidates', snapshot: latest?.snapshot_id }} onNavigate={onNavigate}><span>{t('Candidates', '候选')}</span><strong>{data.summary.candidate_count.toLocaleString()}</strong><small>{t('In this research library', '本研究候选库')}</small><Icon name="arrow" size={15} /></ResearchLink>
      <ResearchLink className="stat-card" to={{ task, view: 'criteria' }} onNavigate={onNavigate}><span>{t('Awaiting review', '待复核')}</span><strong>{data.summary.pending_review_count ?? data.summary.pending_count ?? '—'}</strong><small>{t('Current review requests', '当前复核请求')}</small><Icon name="arrow" size={15} /></ResearchLink>
      <a className="stat-card" href="#saved-evaluations"><span>{t('Saved evaluations', '已保存评估')}</span><strong>{snapshots.length}</strong><small>{latest ? dateText(latest.published_at, language) : t('No results saved yet', '尚未保存结果')}</small><Icon name="arrow" size={15} /></a>
    </div>
    <Panel title={t('How the criteria took shape', '标准如何逐步形成')} caption={t('From the starting set to the latest recorded stage.', '从初始集合到最近记录的阶段。')} action={<ResearchLink className="button" to={{ task, view: 'criteria' }} onNavigate={onNavigate}>{t('Explore criteria', '查看标准')}<Icon name="arrow" size={14} /></ResearchLink>}>
      <CriteriaEvolution stages={data.stages} enabledCount={evaluationCount} summary={data.summary} />
      <div className="criteria-inventory"><span>{valueText(data.summary.active_registered_count)} {t('registered', '已注册')}</span><span>{valueText(data.summary.additional_unregistered_active_count)} {t('unregistered proposals', '未注册提案')}</span><span>{valueText(data.summary.deferred_count)} {t('deferred', '已延后')}</span>{data.summary.task_required_count != null && <span>{data.summary.task_required_count} {t('declared task requirements', '项已声明任务要求')}</span>}</div>
      {data.stages.length ? <details className="stage-inspector overview-stage-inspector"><summary>{t('Stage-by-stage record', '逐阶段记录')}<span>{data.stages.length} {t('stages', '个阶段')}</span></summary><p className="field-note">{t('Counts retain each stage’s recorded scope. A dash means no count was recorded.', '各阶段保留其记录的统计范围，横线表示未记录数量。')}</p><StageTable stages={data.stages} /></details> : <Empty title={t('No criterion stages recorded yet', '尚未记录标准阶段')}><p>{t('Counts will appear as the workflow generates and refines criteria.', '工作流生成和整理标准后，这里会显示真实数量。')}</p></Empty>}
    </Panel>
    <div className="two-columns overview-records"><Panel title={t('Recent changes', '最近变化')} action={<ResearchLink to={{ task, view: 'criteria' }} onNavigate={onNavigate}>{t('View criteria', '查看标准')} →</ResearchLink>}>
      {recentChanges.length ? <ol className="change-list">{recentChanges.map((change, index) => {
        const criterion = changedCriterion(change.after || change.before);
        return <li key={change.id || index}><span className="timeline-dot" /><div><div className="change-heading"><strong>{change.operation ? operationText(change.operation, t) : phaseText(change.stage, t)}</strong><small>{dateText(change.at, language)}</small></div>
          {criterion.ref && <ResearchLink className="change-criterion" to={{ task, view: 'criteria', item: criterion.ref }} onNavigate={onNavigate}>{criterion.name || t('Inspect the changed criterion', '查看变化的标准')} →</ResearchLink>}
          {change.operation && change.stage && <span className="change-stage">{phaseText(change.stage, t)}{change.iteration != null && change.iteration > 0 ? ` · ${t('round', '轮次')} ${change.iteration}` : ''}</span>}
          <details className="change-record"><summary>{t('Reason & record', '理由与记录')}</summary>{change.reason && <p>{change.reason}</p>}<Audit data={change} /></details></div></li>;
      })}</ol> : <Empty title={t('No changes recorded yet', '尚无变化记录')} />}
    </Panel><div id="saved-evaluations" className="section-anchor"><Panel title={t('Saved evaluations', '已保存评估')} caption={t('Open a saved result to inspect screening, ranking and evidence.', '打开已保存结果，查看筛选、排名与证据。')}>
      {snapshots.length ? <ul className="record-list">{snapshots.map(snapshot => <li key={snapshot.snapshot_id}><div>{snapshot.snapshot_id === latest?.snapshot_id && <span className="record-latest">{t('Latest', '最近一次')}</span>}<ResearchLink className="name-button" to={{ task, view: 'candidates', snapshot: snapshot.snapshot_id }} onNavigate={onNavigate}>{snapshot.label?.startsWith('lb_') ? t('Saved evaluation', '已保存评估') : snapshot.label || t('Saved evaluation', '已保存评估')}</ResearchLink><small>{dateText(snapshot.published_at, language)} · {snapshot.candidate_count ?? '—'} {t('candidates', '个候选')}</small></div><Badge label={snapshot.evaluation_mode === 'staged' ? t('Staged screening', '分阶段筛选') : snapshot.evaluation_mode === 'full' ? t('Full assessment', '完整评估') : snapshot.evaluation_mode || '—'} /><button type="button" className="icon-button" aria-label={t('Open this evaluation', '打开此评估')} onClick={() => onResults(snapshot.snapshot_id)}><Icon name="arrow" size={16} /></button></li>)}</ul> : <Empty title={t('Results will appear here', '结果将在此显示')}><p>{t('The current research has no saved candidate result yet.', '当前研究尚无已保存的候选结果。')}</p></Empty>}
    </Panel></div></div><Audit data={data} title={t('Full overview record', '完整总览记录')} />
  </>;
}
