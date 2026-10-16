import { useState } from 'react';
import { api } from '../api/client';
import type { Evidence, EvidenceDetail as EvidenceDetailData, Page } from '../api/types';
import type { Route } from '../hooks/useRoute';
import { useI18n } from '../i18n';
import { useDebounced, useResource } from '../hooks/useResource';
import { useViewState } from '../hooks/useViewState';
import { useInterpretationRevision } from '../hooks/useInterpretation';
import { Audit, Drawer, Empty, ErrorNotice, Loading, Pagination, Panel, Search } from '../components/UI';
import { EvidenceCard } from '../components/EvidenceCard';
import { EvidenceDetail } from '../components/EvidenceDetail';
import { ResearchLink, type ResearchNavigate } from '../components/ResearchLinks';

export function EvidencePage({ task, revision, route, onNavigate }: { task: string; revision: number; route: Route; onNavigate: ResearchNavigate }) {
  const { t } = useI18n();
  const interpretationRevision = useInterpretationRevision();
  const contextKey = [route.criterion, route.candidate, route.source, route.snapshot].map(encodeURIComponent).join('|');
  const [filters, setFilters] = useViewState(task, 'evidence', { query: '', page: 1 }, contextKey === '|||' ? '' : contextKey);
  const { query, page } = filters;
  const setQuery = (query: string) => setFilters(current => ({ ...current, query, page: 1 }));
  const setPage = (page: number) => setFilters(current => ({ ...current, page }));
  const q = useDebounced(query);
  const resource = useResource<Page<Evidence>>(`${task}/evidence/${q}/${contextKey}/${page}`, signal => api.evidence(task, { q, page,
    criterion_ref: route.criterion || undefined, candidate_ref: route.candidate || undefined,
    source_id: route.source || undefined, snapshot: route.snapshot || undefined }, signal), revision);
  const scope = `${task}/${route.item}/${route.snapshot}`;
  const [linkPages, setLinkPages] = useState({ scope: '', criteria: 1, candidates: 1 });
  const criteriaPage = linkPages.scope === scope ? linkPages.criteria : 1;
  const candidatePage = linkPages.scope === scope ? linkPages.candidates : 1;
  const detail = useResource<EvidenceDetailData>(route.item ? `${scope}/${criteriaPage}/${candidatePage}` : null,
    signal => api.evidenceDetail(task, route.item, { snapshot: route.snapshot || undefined, criteria_page: criteriaPage,
      candidate_page: candidatePage, link_page_size: 10 }, signal), revision + interpretationRevision);
  const open = (claim: string) => onNavigate({ item: claim });
  const criterionName = resource.data?.items.flatMap(record => record.links?.criteria || []).find(record => record.detail_ref === route.criterion)?.name;
  const candidateName = resource.data?.items.flatMap(record => record.links?.candidates || []).find(record => record.candidate_ref === route.candidate)?.label;
  const sourceName = resource.data?.items.find(record => record.source_id === route.source)?.source?.title;
  const hasContext = !!(route.criterion || route.candidate || route.source || route.snapshot);
  return <><div className="page-heading"><div><div className="eyebrow">{t('Evidence library', '证据库')}</div><h1>{t('Keep the reasoning close to its sources', '让判断与来源紧密相连')}</h1><p>{t('Understand each finding, its original context and the criteria or candidates that use it.', '查看每项发现的原始上下文，以及使用它的标准和候选。')}</p></div></div>
    {hasContext && <section className="evidence-scope"><div><strong>{t('Linked evidence', '关联证据')}</strong><p>{t('This view follows the selected research context.', '这里显示所选研究上下文中的关联证据。')}</p></div><div className="scope-filter-tags">{route.criterion && <span><ResearchLink to={{ task, view: 'criteria', item: route.criterion, snapshot: route.snapshot }} onNavigate={onNavigate}>{criterionName || t('Selected criterion', '所选标准')}</ResearchLink><button type="button" onClick={() => onNavigate({ criterion: '', item: '' })} aria-label={t('Clear criterion filter', '清除标准筛选')}>×</button></span>}{route.candidate && <span>{candidateName || t('Selected candidate', '所选候选')}<button type="button" onClick={() => onNavigate({ candidate: '', item: '' })} aria-label={t('Clear candidate filter', '清除候选筛选')}>×</button></span>}{route.source && <span>{sourceName || t('Selected source', '所选来源')}<button type="button" onClick={() => onNavigate({ source: '', item: '' })} aria-label={t('Clear source filter', '清除来源筛选')}>×</button></span>}{route.snapshot && <span>{t('Saved evaluation', '已保存评估')}<button type="button" onClick={() => onNavigate({ snapshot: '', item: '' })} aria-label={t('Clear saved evaluation scope', '清除评估范围')}>×</button></span>}</div><button type="button" onClick={() => onNavigate({ criterion: '', candidate: '', source: '', snapshot: '', item: '' })}>{t('Clear linked context', '清除关联范围')}</button></section>}
    <Panel title={t('Evidence for this research', '此研究的证据')}><div className="table-toolbar"><Search value={query} onChange={setQuery} placeholder={t('Search findings, sources and original passages', '搜索发现、来源与原文')} /><span className="subtle">{resource.data?.total ?? '—'} {t('records', '条记录')}</span></div><ErrorNotice message={resource.error} retry={resource.refresh} />{!resource.data ? resource.loading && <Loading /> : resource.data.items.length ? <><div className="evidence-grid">{resource.data.items.map((record, index) => <EvidenceCard key={`${record.claim_id}/${index}`} record={record} task={task} snapshot={route.snapshot} onOpen={open} onNavigate={onNavigate} />)}</div><Pagination page={resource.data} onChange={setPage} /></> : <Empty title={query || hasContext ? t('No evidence matches this scope', '此范围内没有匹配证据') : t('No evidence recorded yet', '尚无证据记录')}><p>{t('Only recorded findings and their actual links are shown.', '这里只显示已记录的发现与真实关联。')}</p></Empty>}<Audit data={{ criterion_ref: route.criterion || undefined, candidate_ref: route.candidate || undefined, source_id: route.source || undefined, snapshot: route.snapshot || undefined }} title={t('Evidence scope record', '证据范围记录')} /></Panel>
    {route.item && <Drawer title={detail.data?.source?.title || detail.data?.title || t('Evidence & context', '证据与上下文')} onClose={() => onNavigate({ item: '' })}>{!detail.data ? detail.error ? <ErrorNotice message={detail.error} retry={detail.refresh} /> : <Loading /> : <EvidenceDetail detail={detail.data} task={task} snapshot={route.snapshot} onNavigate={onNavigate} onEvidence={open}
      onCriteriaPage={page => setLinkPages({ scope, criteria: page, candidates: candidatePage })}
      onCandidatePage={page => setLinkPages({ scope, criteria: criteriaPage, candidates: page })} />}</Drawer>}
  </>;
}
