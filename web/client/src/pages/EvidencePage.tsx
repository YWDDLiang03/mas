import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { EvidenceDetail as EvidenceDetailData, EvidenceQuery, EvidenceSourcePage, SourceKind } from '../api/types';
import type { Route } from '../hooks/useRoute';
import { useI18n } from '../i18n';
import { useDebounced, useResource } from '../hooks/useResource';
import { useViewState } from '../hooks/useViewState';
import { useInterpretationRevision } from '../hooks/useInterpretation';
import { Audit, Drawer, Empty, ErrorNotice, Loading, Pagination, Panel, Search } from '../components/UI';
import { EvidenceCollectionCard } from '../components/EvidenceCollectionCard';
import { EvidenceSourceGroup } from '../components/EvidenceSourceGroup';
import { EvidenceDetail } from '../components/EvidenceDetail';
import { EvidenceConnectionScope, ResearchLink, type ResearchNavigate } from '../components/ResearchLinks';

export function EvidencePage({ task, revision, route, onNavigate }: { task: string; revision: number; route: Route; onNavigate: ResearchNavigate }) {
  const { t } = useI18n();
  const interpretationRevision = useInterpretationRevision();
  const contextKey = [route.criterion, route.candidate, route.source, route.snapshot].map(encodeURIComponent).join('|');
  const [filters, setFilters] = useViewState(task, 'evidence', { query: '', page: 1, kind: 'literature', kindSelected: false as boolean, expanded: '[]' }, contextKey === '|||' ? '' : contextKey);
  const { query, page } = filters;
  const setQuery = (query: string) => setFilters(current => ({ ...current, query, page: 1 }));
  const setPage = (page: number) => setFilters(current => ({ ...current, page }));
  const q = useDebounced(query);
  const pendingKind = useRef<SourceKind>();
  const [collapsedSource, setCollapsedSource] = useState('');
  useEffect(() => {
    if (pendingKind.current && !route.source && !route.item) {
      const kind = pendingKind.current; pendingKind.current = undefined;
      setFilters(current => ({ ...current, kind, kindSelected: true, page: 1, expanded: '[]' }));
    }
  }, [route.source, route.item, setFilters]);
  const scope = `${task}/${route.item}/${route.snapshot}`;
  const [linkPages, setLinkPages] = useState({ scope: '', criteria: 1, candidates: 1 });
  const criteriaPage = linkPages.scope === scope ? linkPages.criteria : 1;
  const candidatePage = linkPages.scope === scope ? linkPages.candidates : 1;
  const detail = useResource<EvidenceDetailData>(route.item ? `${scope}/${criteriaPage}/${candidatePage}` : null,
    signal => api.evidenceDetail(task, route.item, { snapshot: route.snapshot || undefined, criteria_page: criteriaPage,
      candidate_page: candidatePage, link_page_size: 10 }, signal), revision + interpretationRevision);
  const sourceId = route.source || (route.item ? detail.data?.source_id : '') || '';
  const kinds: { id: SourceKind; label: string }[] = [
    { id: 'literature', label: t('Literature & books', '文献与书籍') },
    { id: 'database', label: t('Databases & supplied data', '数据库与自有数据') },
    { id: 'model', label: t('Model records', '模型记录') },
    { id: 'other', label: t('Other sources', '其他来源') }, { id: 'all', label: t('All source types', '全部来源类型') },
  ];
  const kind = sourceId || (route.candidate && !filters.kindSelected) ? 'all' : kinds.some(item => item.id === filters.kind) ? filters.kind as SourceKind : 'literature';
  const evidenceQuery: EvidenceQuery = { q, criterion_ref: route.criterion || undefined,
    candidate_ref: route.candidate || undefined, source_id: sourceId || undefined, snapshot: route.snapshot || undefined };
  const resource = useResource<EvidenceSourcePage>(`${task}/evidence-sources/${q}/${contextKey}/${sourceId}/${kind}/${page}`,
    signal => api.evidenceSources(task, { ...evidenceQuery, kind, page }, signal), revision);
  const savedSnapshot = resource.data?.scope.snapshot_id || route.snapshot || undefined;
  const open = (claim: string, source = '') => onNavigate({ item: claim, source, snapshot: savedSnapshot || '' });
  const expanded: string[] = (() => { try { const value: unknown = JSON.parse(filters.expanded); return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; } catch { return []; } })();
  function toggle(source: string, value: boolean) { setFilters(current => ({ ...current, expanded: JSON.stringify(value ? [...new Set([...expanded, source])] : expanded.filter(item => item !== source)) })); }
  function selectKind(value: SourceKind) {
    if (route.source || route.item) { pendingKind.current = value; onNavigate({ source: '', item: '' }); }
    else setFilters(current => ({ ...current, kind: value, kindSelected: true, page: 1, expanded: '[]' }));
  }
  const criterionName = resource.data?.items.flatMap(record => record.criteria).find(record => record.detail_ref === route.criterion)?.name || detail.data?.links?.criteria.find(record => record.detail_ref === route.criterion)?.name;
  const candidateName = resource.data?.scope.candidate_label || detail.data?.links?.candidates.find(record => record.candidate_ref === route.candidate)?.label;
  const sourceName = resource.data?.items.find(record => record.source_id === route.source)?.title;
  const hasContext = !!(route.criterion || route.candidate || route.source || route.snapshot);
  return <><div className="page-heading"><div><div className="eyebrow">{t('Evidence library', '证据库')}</div><h1>{t('Evidence and sources', '证据与来源')}</h1><p>{t('Explore saved findings, study conditions and the criteria they support.', '查看保存的发现、实验条件与其支持的标准。')}</p></div><ResearchLink className="button" to={{ task, view: 'criteria', snapshot: route.snapshot }} onNavigate={onNavigate}>{t('Explore criteria', '查看标准')} →</ResearchLink></div>
    <EvidenceCollectionCard taskId={task} />
    {hasContext && <section className="evidence-scope"><div><strong>{t('Linked evidence', '关联证据')}</strong><p>{t('This view follows the selected research context.', '这里显示所选研究上下文中的关联证据。')}</p></div><div className="scope-filter-tags">{route.criterion && <span><ResearchLink to={{ task, view: 'criteria', item: route.criterion, snapshot: route.snapshot }} onNavigate={onNavigate}>{criterionName || t('Selected criterion', '所选标准')}</ResearchLink><button type="button" onClick={() => onNavigate({ criterion: '', item: '' })} aria-label={t('Clear criterion filter', '清除标准筛选')}>×</button></span>}{route.candidate && <span>{route.snapshot ? <ResearchLink to={{ task, view: 'candidates', item: route.candidate, snapshot: route.snapshot }} onNavigate={onNavigate}>{candidateName || t('Selected candidate', '所选候选')}</ResearchLink> : candidateName || t('Selected candidate', '所选候选')}<button type="button" onClick={() => onNavigate({ candidate: '', item: '' })} aria-label={t('Clear candidate filter', '清除候选筛选')}>×</button></span>}{route.source && <span>{sourceName || t('Selected source', '所选来源')}<button type="button" onClick={() => onNavigate({ source: '', item: '' })} aria-label={t('Clear source filter', '清除来源筛选')}>×</button></span>}{route.snapshot && <span>{t('Saved evaluation', '已保存评估')}<button type="button" onClick={() => onNavigate({ snapshot: '', item: '' })} aria-label={t('Clear saved evaluation scope', '清除评估范围')}>×</button></span>}</div><button type="button" onClick={() => onNavigate({ criterion: '', candidate: '', source: '', snapshot: '', item: '' })}>{t('Clear linked context', '清除关联范围')}</button></section>}
    <Panel title={t('Sources & findings', '来源与具体发现')}><div className="table-toolbar"><Search value={query} onChange={setQuery} placeholder={t('Search saved findings, sources and passages', '搜索保存的发现、来源与原文')} /><span className="subtle">{resource.data?.total ?? '—'} {t('sources', '个来源')}</span></div>
      <div className="source-kind-tabs" role="group" aria-label={t('Source types', '来源类型')}>{kinds.map(item => <button key={item.id} type="button" aria-pressed={kind === item.id} onClick={() => selectKind(item.id)}>{item.label}</button>)}</div>
      {route.criterion && !route.candidate && <p className="subtle">{t('Literature explains the criterion’s research basis. Database and model records show candidate observations used in its evaluation.', '文献说明标准的研究依据；数据库与模型记录展示该标准评估候选时使用的观测。')}</p>}
      <EvidenceConnectionScope scope={resource.data?.scope} /><ErrorNotice message={resource.error} retry={resource.refresh} />{!resource.data ? resource.loading && <Loading /> : resource.data.items.length ? <><div className="source-groups">{resource.data.items.map(record => <EvidenceSourceGroup key={record.source_id} record={record} task={task} query={evidenceQuery} open={(sourceId === record.source_id && collapsedSource !== record.source_id) || expanded.includes(record.source_id)} onToggle={value => { setCollapsedSource(value ? '' : record.source_id); toggle(record.source_id, value); }} onOpen={claim => open(claim, record.source_id)} onNavigate={onNavigate} revision={revision} />)}</div><Pagination page={resource.data} onChange={setPage} /></> : <Empty title={query || hasContext ? t('No source matches this scope', '此范围内没有匹配来源') : t('No sources of this type are recorded', '尚未记录此类型的来源')}><p>{t('Try another source type or change the filters. Only saved findings and their actual links are shown.', '可选择其他来源类型或调整筛选。这里只显示保存的发现与真实关联。')}</p></Empty>}
      <Audit data={{ ...evidenceQuery, kind, scope: resource.data?.scope }} title={t('Evidence scope record', '证据范围记录')} /></Panel>
    {route.item && <Drawer title={detail.data?.source?.title || detail.data?.title || t('Evidence & context', '证据与上下文')} onClose={() => onNavigate({ item: '' })}>{!detail.data ? detail.error ? <ErrorNotice message={detail.error} retry={detail.refresh} /> : <Loading /> : <EvidenceDetail detail={detail.data} task={task} snapshot={savedSnapshot} onNavigate={onNavigate} onEvidence={claim => open(claim)}
      onCriteriaPage={page => setLinkPages({ scope, criteria: page, candidates: candidatePage })}
      onCandidatePage={page => setLinkPages({ scope, criteria: criteriaPage, candidates: page })} />}</Drawer>}
  </>;
}
