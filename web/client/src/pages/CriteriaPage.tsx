import { useEffect, useRef } from 'react';
import { api } from '../api/client';
import type { Criterion, CriterionDetail, Overview, Page, RevisionResult } from '../api/types';
import { operationText, phaseText, stateText, useI18n } from '../i18n';
import { useDebounced, useResource } from '../hooks/useResource';
import { useViewState } from '../hooks/useViewState';
import { Audit, Badge, dateText, Drawer, Empty, ErrorNotice, Loading, Pagination, Panel, Search, valueText } from '../components/UI';
import { EvidenceCard } from '../components/EvidenceCard';
import { StageTable } from './OverviewPage';
import { CriteriaEvolution, enabledCriteriaCount, stageCountScope } from '../components/CriteriaEvolution';
import { CriterionEditor } from '../components/CriterionEditor';
import { CriterionResearchBrief } from '../components/CriterionResearchBrief';
import { useInterpretationRevision } from '../hooks/useInterpretation';
import { ResearchLink, type ResearchNavigate } from '../components/ResearchLinks';
import { CriteriaEvaluation } from '../components/CriteriaEvaluation';
import { CriterionChangeReason, CriterionDifference, criterionExplanationText } from '../components/CriterionDifference';

export function criterionDetailRef(criterion: Criterion) {
  if (criterion.detail_ref) return criterion.detail_ref;
  if (criterion.criterion_id.startsWith('cri_') && !criterion.criterion_id.includes('@v')) return `${criterion.criterion_id}@v${criterion.version}`;
  return criterion.rule_ref || criterion.attribute_ref || criterion.criterion_id;
}

type CriteriaViewPage = Page<Criterion> & { criteria_scope?: string; rule_set_ref?: string };

export function CriteriaPage({ task, item, revision, enabled, onOpen, onClose, onRevision, onEditTask, onNavigate, snapshot = '' }: { snapshot?: string; onNavigate: ResearchNavigate; task: string; item: string; revision: number; enabled: boolean; onOpen: (id: string) => void; onClose: () => void; onRevision: (result: RevisionResult) => void; onEditTask: () => void }) {
  const { t, language } = useI18n();
  const interpretationRevision = useInterpretationRevision();
  const overviewSection = useRef<HTMLDivElement>(null);
  const evidenceSection = useRef<HTMLElement>(null);
  const historySection = useRef<HTMLElement>(null);
  const lineageSection = useRef<HTMLElement>(null);
  function jump(section: 'overview' | 'evidence' | 'history' | 'lineage') {
    const target = { overview: overviewSection, evidence: evidenceSection, history: historySection, lineage: lineageSection }[section].current;
    target?.scrollIntoView({ block: 'start', behavior: 'auto' });
    target?.focus({ preventScroll: true });
  }
  const [filters, setFilters] = useViewState(task, 'criteria', { query: '', state: 'working', stage: '', page: 1 });
  const { query, stage } = filters;
  const state = filters.state === 'active' ? 'working' : filters.state;
  const page = filters.state === 'active' ? 1 : filters.page;
  useEffect(() => {
    if (filters.state === 'active') setFilters(current => ({ ...current, state: 'working', page: 1 }));
  }, [filters.state, setFilters]);
  const setQuery = (query: string) => setFilters(current => ({ ...current, query, page: 1 }));
  const setState = (state: string) => setFilters(current => ({ ...current, state, page: 1 }));
  const setStage = (stage: string) => setFilters(current => ({ ...current, stage, page: 1 }));
  const setPage = (page: number) => setFilters(current => ({ ...current, page }));
  const q = useDebounced(query);
  const resource = useResource<CriteriaViewPage>(`${task}/criteria/${q}/${state}/${stage}/${page}`, signal => api.criteria(task, { q, state, stage, page }, signal), revision);
  const overview = useResource<Overview>(`${task}/overview`, signal => api.overview(task, signal), revision);
  const stages = overview.data?.stages || [];
  const detail = useResource<CriterionDetail>(item ? `${task}/criteria/${item}/${snapshot}` : null, signal => api.criterion(task, item, signal, snapshot || undefined), revision + interpretationRevision);
  const stageSelected = stages.find(value => value.stage_id === stage);
  const scopeCaption = state === 'working'
    ? resource.data?.criteria_scope === 'frozen'
      ? t('Criteria enabled in the latest prepared evaluation. Pending work is listed separately.', '最近准备的评估所启用的标准。待处理工作单独列出。')
      : t('The current working set while criteria are being developed.', '标准生成与整理中的当前工作集。')
    : state === 'pending'
      ? resource.data?.rule_set_ref
        ? t('Unregistered proposals, open reviews and current rules outside the prepared evaluation.', '未注册提案、待复核项目，以及未入选本次评估的当前规则。')
        : t('Unregistered proposals and current review items.', '未注册提案和当前待复核项目。')
      : t('Open a criterion to explore its evidence and changes.', '打开一条标准，查看其证据与变化。');
  function openEvidence(claim = '') {
    if (!detail.data) return;
    const query = detail.data.evidence_query;
    onNavigate({ task, view: 'evidence', item: claim, criterion: query?.criterion_ref || criterionDetailRef(detail.data),
      candidate: query?.candidate_ref || '', source: query?.source_id || '', snapshot: query?.snapshot || '' });
  }
  const lineageNames = new Map(detail.data?.lineage?.nodes.map(node => [node.id || node.ref, node.name || t('Record missing', '记录缺失')]));
  function explanationText(value: string) {
    const explanation = detail.data?.explanation;
    return explanation?.derived && explanation.method === 'recorded_criterion_projection' ? criterionExplanationText(value, t) : value;
  }

  return <><div className="page-heading"><div><div className="eyebrow">{t('Criteria workspace', '标准工作区')}</div><h1>{t('Research criteria', '研究标准')}</h1><p>{t('See what screens and ranks candidates. Open a criterion to inspect its research basis.', '查看筛选与排序候选的依据，打开标准追踪其研究来源。')}</p></div><ResearchLink className="button" to={{ task, view: 'evidence', snapshot }} onNavigate={onNavigate}>{t('Explore evidence', '查看证据')} →</ResearchLink></div>
    <ErrorNotice message={overview.error} retry={overview.refresh} /><div className="criteria-summary-strip" aria-label={t('Prepared evaluation roles', '已准备评估的标准用途')}><div><strong>{overview.data?.summary.enabled_hard_count ?? '—'}</strong><span>{t('Required', '硬条件')}<small>{t('Screen candidates', '筛选候选')}</small></span></div><div><strong>{overview.data?.summary.enabled_preference_count ?? '—'}</strong><span>{t('Preferences', '排序偏好')}<small>{t('Rank eligible candidates', '排序合格候选')}</small></span></div><div><strong>{overview.data?.summary.enabled_context_count ?? '—'}</strong><span>{t('Context only', '仅供参考')}<small>{t('No screening or ranking weight', '不参与淘汰或计分')}</small></span></div><div><strong>{overview.data?.summary.pending_review_count ?? overview.data?.summary.pending_count ?? '—'}</strong><span>{t('Awaiting review', '待复核')}<small>{t('Current review requests', '当前复核请求')}</small></span></div></div>
    <details className="criteria-development"><summary>{t('How these criteria developed', '标准的形成过程')}<span>{overview.data ? stages.length : '—'} {t('recorded stages', '个已记录阶段')}</span></summary>
    <Panel title={t('Criteria evolution', '标准演化')} caption={t('How the criteria expand and become more focused after each completed stage.', '查看每个已完成阶段如何展开和提炼标准。')} className="criteria-evolution-panel"><CriteriaEvolution stages={stages} enabledCount={enabledCriteriaCount(overview.data)} summary={overview.data?.summary} /></Panel>
    <details className="stage-inspector"><summary>{t('Stage changes', '阶段变化')} <span>{overview.data ? stages.length : '—'}</span></summary>{stages.length ? <StageTable stages={stages} selected={stage} onSelect={id => { setStage(id === stage ? '' : id); setState(id === stage ? 'working' : ''); setPage(1); }} /> : <p className="subtle">{t('Stage counts will appear when recorded.', '阶段数量记录后会在这里显示。')}</p>}</details></details>
    <Panel title={t('Research criteria', '研究标准')} caption={stageSelected ? `${phaseText(stageSelected.stage, t)} · ${t('iteration', '迭代')} ${stageSelected.iteration ?? '—'} · ${valueText(stageSelected.before_count)} → ${valueText(stageSelected.after_count)} · ${stageCountScope(stageSelected, t)}` : scopeCaption}><div className="table-toolbar"><Search value={query} onChange={value => { setQuery(value); setPage(1); }} placeholder={t('Search all criteria', '搜索全部标准')} /><label className="inline-select"><span className="sr-only">{t('State', '状态')}</span><select value={state} onChange={event => { setState(event.target.value); setPage(1); }}><option value="">{t('All versions', '全部版本')}</option><option value="working">{t('Working criteria', '当前标准')}</option><option value="pending">{t('Pending', '待处理')}</option>{['merged', 'retired'].map(value => <option key={value} value={value}>{stateText(value, t)}</option>)}</select></label>{stage && <button onClick={() => { setStage(''); setState('working'); setPage(1); }}>{t('Clear stage filter', '清除阶段筛选')}</button>}</div><ErrorNotice message={resource.error} retry={resource.refresh} />{!resource.data ? resource.loading && <Loading /> : resource.data.items.length ? <><div className="table-scroll"><table className="criteria-table"><thead><tr><th>{t('Criterion', '标准')}</th><th>{t('Role', '用途')}</th><th>{t('Recorded state', '已记录状态')}</th><th>{t('Latest evaluation', '最近评估')}</th><th>{t('Evidence', '证据')}</th><th>{t('Version', '版本')}</th><th>{t('Stage', '阶段')}</th></tr></thead><tbody>{resource.data.items.map(criterion => <tr key={`${criterion.criterion_id}/${criterion.version}`}><td><button className="name-button" onClick={() => onOpen(criterionDetailRef(criterion))}>{criterion.name}</button>{criterion.definition && <p className="cell-note clamp-two">{criterion.definition}</p>}</td><td>{stateText(criterion.role, t)}</td><td><Badge state={criterion.state} /></td><td><CriteriaEvaluation value={criterion.evaluation} compact /></td><td className="numeric">{criterion.evidence_count == null ? '—' : <ResearchLink to={{ task, view: 'evidence', criterion: criterionDetailRef(criterion), snapshot }} onNavigate={onNavigate}><span className="sr-only">{t('Evidence for', '标准证据')} {criterion.name}: </span>{criterion.evidence_count}</ResearchLink>}</td><td className="numeric">v{criterion.version}</td><td>{phaseText(criterion.stage, t)}{criterion.iteration != null && criterion.iteration > 0 && <span className="cell-note"> · {criterion.iteration}</span>}</td></tr>)}</tbody></table></div><Pagination page={resource.data} onChange={setPage} /></> : <Empty title={q || (state && state !== 'working') || stage ? t('No criteria match these filters', '没有匹配此筛选的标准') : t('Criteria have not been generated yet', '尚未生成标准')}><p>{t('This view uses the selected task’s actual criterion records.', '这里显示所选任务实际记录的标准。')}</p></Empty>}</Panel>
    {item && <Drawer title={detail.data?.name || t('Criterion details', '标准详情')} onClose={onClose}>{!detail.data ? detail.error ? <ErrorNotice message={detail.error} retry={detail.refresh} /> : <Loading /> : <><nav className="detail-jump-nav" aria-label={t('Criterion sections', '标准章节')}><button type="button" onClick={() => jump('overview')}>{t('Overview', '概览')}</button><button type="button" onClick={() => jump('evidence')}>{t('Supporting sources', '支持来源')}</button><button type="button" onClick={() => jump('history')}>{t('Changes', '变化')}</button><button type="button" onClick={() => jump('lineage')}>{t('Lineage', '沿革')}</button><button type="button" onClick={() => openEvidence()}>{t('Open linked evidence', '打开关联证据')} →</button></nav><div ref={overviewSection} tabIndex={-1} className="evidence-detail-anchor"><div className="detail-meta"><Badge state={detail.data.state} /><Badge label={stateText(detail.data.role, t)} /><span>v{detail.data.version}</span><span>{detail.data.unit}</span></div><p className="detail-definition">{detail.data.definition}</p><CriteriaEvaluation value={detail.data.evaluation} /><CriterionResearchBrief task={task} criterionRef={criterionDetailRef(detail.data)} brief={detail.data.research_brief} enabled={enabled} onEvidence={openEvidence} />{detail.data.explanation && <section className="criterion-guide"><h3>{t('How to use this criterion', '如何理解和使用此标准')}</h3><dl><div><dt>{t('Decision question', '决策问题')}</dt><dd>{detail.data.explanation.decision_question}</dd></div><div><dt>{t('How it is evaluated', '如何评估')}</dt><dd>{detail.data.explanation.how_evaluated}</dd></div><div><dt>{t('Why it is included', '纳入依据')}</dt><dd>{detail.data.explanation.why_included}</dd></div></dl>{!!detail.data.explanation.scope.length && <div><h4>{t('Scope', '适用范围')}</h4><ul className="research-notes">{detail.data.explanation.scope.map((value, index) => <li key={index}>{index === 0 ? value : explanationText(value)}</li>)}</ul></div>}{!!detail.data.explanation.limitations.length && <div><h4>{t('Limitations', '限制')}</h4><ul className="research-notes">{detail.data.explanation.limitations.map((value, index) => <li key={index}>{explanationText(value)}</li>)}</ul></div>}<button type="button" onClick={() => openEvidence()}>{t('Explore the linked evidence', '查看关联证据')} →</button></section>}{detail.data.reason && <CriterionChangeReason reason={detail.data.reason} />}
      </div><section className="detail-section evidence-detail-anchor" ref={lineageSection} tabIndex={-1}><h3>{t('Lineage', '形成沿革')}</h3>{detail.data.lineage?.nodes?.length ? <ol className="lineage-list">{detail.data.lineage.nodes.map((node, index) => <li key={node.id || node.ref || index}><span className="timeline-dot" /><div className="detail-meta">{node.relation && <small>{node.relation === 'parent' ? t('Parent criterion', '父标准') : node.relation === 'child' ? t('Child criterion', '子标准') : t('Selected version', '当前查看版本')}</small>}{node.version != null && <span>v{node.version}</span>}{node.state && <Badge state={node.state} />}</div>{node.detail_ref && !node.missing ? <button className="name-button" onClick={() => onOpen(node.detail_ref!)}>{node.name || t('Criterion', '标准')}</button> : <strong>{node.name || t('Record missing', '记录缺失')}</strong>}{node.definition && <p>{node.definition}</p>}{node.missing && <Audit data={{ ref: node.ref }} title={t('Missing record reference', '缺失记录的引用')} />}{node.operation && <p>{operationText(node.operation, t)}</p>}</li>)}</ol> : (detail.data.parents?.length || detail.data.children?.length) ? <Audit data={{ parents: detail.data.parents, children: detail.data.children }} title={t('Linked criterion versions', '关联的标准版本')} /> : <p className="subtle">{t('No earlier lineage is recorded for this criterion.', '此标准尚无早期沿革记录。')}</p>}</section>
      {detail.data.lineage?.edges?.length ? <div className="lineage-edges">{detail.data.lineage.edges.map((edge, index) => <p key={index}><span>{lineageNames.get(edge.source) || t('Earlier criterion', '早期标准')}</span><span aria-hidden="true"> → </span><span>{lineageNames.get(edge.target) || t('Later criterion', '后续标准')}</span></p>)}</div> : null}
      <section className="detail-section evidence-detail-anchor" ref={historySection} tabIndex={-1}><h3>{t('Changes and reasoning', '变化与理由')}</h3>{detail.data.history?.length ? detail.data.history.map((change, index) => <article className="history-entry" key={change.id || index}><div className="row spread"><strong>{change.operation ? operationText(change.operation, t) : phaseText(change.stage, t)}</strong><small>{dateText(change.at, language)}</small></div><CriterionChangeReason reason={change.reason} /><CriterionDifference before={change.before} after={change.after} /><Audit data={change} /></article>) : <p className="subtle">{t('No version changes are recorded yet.', '尚无版本变化记录。')}</p>}</section>
      <section className="detail-section evidence-detail-anchor" ref={evidenceSection} tabIndex={-1}><div className="row spread"><h3>{t('Supporting sources', '支持来源')}</h3><button type="button" className="text-button" onClick={() => openEvidence()}>{t('View in evidence library', '在证据库中查看')} →</button></div>{!detail.data.sources?.length && detail.data.explanation?.evidence_support?.map((text, index) => <p key={index}>{text.replace(/^claim_[A-Za-z0-9_-]+:\s*/, '')}</p>)}{detail.data.sources?.length ? detail.data.sources.map((source, index) => <EvidenceCard key={`${source.source_id}/${index}`} record={source} task={task} snapshot={snapshot} onOpen={openEvidence} onNavigate={onNavigate} />) : <p className="subtle">{t('No supporting source is linked yet.', '尚未关联支持来源。')}</p>}</section>
      {detail.data.historical_version && <div className="notice"><p>{t('This saved version is read-only. Open the current criterion to make changes.', '此保存版本只供查看。需要修改时，请打开当前标准。')}</p>{detail.data.current_ref && <button onClick={() => onOpen(detail.data!.current_ref!)}>{t('Open current criterion', '打开当前标准')}</button>}</div>}{enabled && !detail.data.historical_version && detail.data.editable === false && <div className="notice"><p>{t('Task requirements are edited through the research objective, so they keep their required status.', '任务要求通过研究目标修改，以保留其必需性质。')}</p><button onClick={onEditTask}>{t('Edit task', '编辑任务')}</button></div>}{enabled && !detail.data.historical_version && detail.data.editable !== false && <details className="detail-section"><summary>{t('Edit as a new version', '编辑并保存新版本')}</summary><CriterionEditor key={`${detail.data.criterion_id}/${detail.data.version}`} task={task} detail={detail.data} onSaved={result => { resource.refresh(); detail.refresh(); onRevision(result); }} /></details>}<Audit data={detail.data} /></>}</Drawer>}</>;
}
