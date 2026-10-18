import { useState } from 'react';
import type { Evidence, EvidenceQuery, EvidenceSourceGroup as Group, Page } from '../api/types';
import { api } from '../api/client';
import { useResource } from '../hooks/useResource';
import { useViewState } from '../hooks/useViewState';
import { useI18n } from '../i18n';
import { Audit, Empty, ErrorNotice, Pagination, safeUrl } from './UI';
import { EvidenceFindingGroup, groupSavedFindings } from './EvidenceFindingGroup';
import { CriterionLink, type ResearchNavigate } from './ResearchLinks';
import './EvidenceSources.css';

export function EvidenceSourceGroup({ record, task, query, open, onToggle, onOpen, onNavigate, revision }: {
  record: Group; task: string; query: EvidenceQuery; open: boolean; onToggle: (open: boolean) => void;
  onOpen: (claim: string) => void; onNavigate: ResearchNavigate; revision: number;
}) {
  const { t } = useI18n();
  const [allCriteria, setAllCriteria] = useState(false);
  const snapshot = record.scope.snapshot_id || undefined;
  const context = [record.source_id, snapshot || '', query.q || '', query.criterion_ref || '', query.candidate_ref || ''].join('|');
  const [filters, setFilters] = useViewState(task, 'source-findings', { page: 1 }, context);
  const resource = useResource<Page<Evidence>>(open ? `${task}/source/${context}/${filters.page}` : null,
    signal => api.evidence(task, { ...query, source_id: record.source_id, snapshot, page: filters.page }, signal), revision);
  const identifier = /^src_(doi|pmid|pubmed|pmc|pmcid)_(.+)$/i.exec(record.source_id);
  const recordedTitle = record.title || (identifier ? `${identifier[1].toLowerCase() === 'doi' ? 'DOI' : 'PubMed'}: ${identifier[2]}` : t('Saved source', '已保存来源'));
  const activity = /^tool_drug_chembl_bioactivity record chembl_activity_(\d+)/.exec(recordedTitle);
  const binding = /^tool_drug_gtopdb_affinity record gtopdb_interaction_(\d+)/.exec(recordedTitle);
  const pubchem = /^tool_drug_pubchem_property record pubchem_cid_(\d+)$/.exec(recordedTitle);
  const title = activity ? `ChEMBL · ${t('activity', '活性记录')} ${activity[1]}`
    : binding ? `Guide to Pharmacology · ${t('binding record', '结合记录')} ${binding[1]}`
    : pubchem ? `PubChem · ${t('compound', '化合物')} CID ${pubchem[1]}`
    : recordedTitle.startsWith('tool_compute_admet_descriptors record ') ? t('Structure descriptor calculation', '结构性质计算')
    : recordedTitle.startsWith('tool_drug_admet_ai record ') ? t('ADMET-AI prediction record', 'ADMET-AI 预测记录')
    : recordedTitle;
  const kindLabel = record.kind === 'literature' ? t('Literature', '文献') : record.kind === 'model' ? t('Model record', '模型记录') : record.kind === 'database' ? t('Database or supplied record', '数据库或自有记录') : t('Other saved source', '其他保存来源');
  const subjects = [...new Set([...record.populations, ...record.subjects])];
  const url = safeUrl(record.url || undefined);
  const currentCriteria = record.criteria_scope && record.criteria_scope !== 'task_history';
  const visibleCriteria = allCriteria ? record.criteria : record.criteria.slice(0, 3);
  function roleLabels(roles: string[]) {
    const labels: Record<string, string> = { criterion_basis: t('Research basis', '研究依据'), supports_criterion: t('Research basis', '研究依据'),
      used_in_assessment: t('Assessment value', '评估取值'), derived_used_in_assessment: t('Assessment value through a derived claim', '经推导证据用于取值'),
      counter_evidence: t('Counter-evidence', '反证'), derived_counter_evidence: t('Counter-evidence through a derived claim', '经推导证据作为反证'),
      set_aside: t('Some values set aside', '部分取值未采用'), derived_set_aside: t('Some values set aside', '部分取值未采用') };
    return [...new Set(roles.filter(role => role !== 'set_aside' && role !== 'derived_set_aside').map(role => labels[role] || role))].join(' · ');
  }
  const basisOnly = record.criteria.length > 0 && record.criteria.every(criterion => {
    const roles = (criterion.relationships || [criterion.relationship]).filter(Boolean);
    return roles.length > 0 && roles.every(role => role === 'criterion_basis' || role === 'supports_criterion');
  });
  return <article className="source-group"><header><div><span className="source-kind">{kindLabel}</span><h2>{title}</h2></div><span className="source-findings-count">{record.claim_count.toLocaleString()} {t('findings in this view', '条范围内发现')}</span></header>
    <div className="source-study"><span>{t('Recorded study subjects', '已记录的研究对象')}</span><p className="source-subject-preview">{subjects.length ? subjects.join(' · ') : t('Not recorded in the saved context.', '保存上下文中未记录。')}</p>{(subjects.length > 0 || record.assays.length > 0) && <details className="source-study-details"><summary>{t('Study subjects & methods', '研究对象与方法')}</summary>{subjects.length > 0 && <p>{subjects.join(' · ')}</p>}{record.assays.length > 0 && <p><strong>{t('Methods', '方法')}</strong> {record.assays.join(' · ')}</p>}{record.context_sampled && <small>{t('Context examples from the saved findings; full conditions stay with each record.', '上下文示例来自保存的发现，完整条件保留在每条记录中。')}</small>}</details>}</div>
    <div className="source-criteria"><span>{currentCriteria ? t('Linked enabled criteria', '关联本次启用标准') : t('Linked criterion versions · task history', '关联标准版本 · 研究历史')} <strong>{record.criteria_count.toLocaleString()}</strong></span>{record.criteria.length ? <div>{visibleCriteria.map((criterion, index) => <span className="source-criterion-use" key={`${criterion.detail_ref}/${index}`}><CriterionLink record={criterion} task={task} snapshot={snapshot} onNavigate={onNavigate} /><small>{roleLabels(criterion.relationships || (criterion.relationship ? [criterion.relationship] : []))}</small></span>)}</div> : <p>{t('No enabled criterion link in this view.', '此范围无启用标准关联。')}</p>}{record.criteria.length > 3 && <button type="button" className="text-button" onClick={() => setAllCriteria(value => !value)}>{allCriteria ? t('Show fewer criteria', '收起部分标准') : t('Show all linked criteria', '显示全部关联标准')}</button>}{basisOnly && <p className="subtle">{t('These links describe the criteria’s research basis. They do not mean this source measured every candidate.', '这些关联表示标准的研究依据，不代表该来源测量了每个候选。')}</p>}{record.criteria_count > record.criteria.length && <small>{t('Open individual findings to inspect their complete criterion connections.', '展开具体发现，可查看其完整标准关联。')}</small>}</div>
    <div className="source-actions"><button type="button" aria-expanded={open} onClick={() => onToggle(!open)}>{open ? t('Hide findings', '收起发现') : t('Explore findings', '展开具体发现')} · {record.claim_count.toLocaleString()}</button>{url && <a href={url} target="_blank" rel="noopener noreferrer">{t('Original source', '原始来源')} ↗</a>}</div>
    {open && <div className="source-findings"><ErrorNotice message={resource.error} retry={resource.refresh} />{resource.loading && !resource.data && <p>{t('Loading saved findings…', '正在读取保存的发现…')}</p>}{resource.data?.items.length ? <>{groupSavedFindings(resource.data.items).map((records, index) => <EvidenceFindingGroup key={`${records[0].claim_id}/${index}`} records={records} task={task} snapshot={snapshot} onOpen={onOpen} onNavigate={onNavigate} />)}<Pagination page={resource.data} onChange={page => setFilters({ page })} /></> : resource.data && <Empty title={t('No finding matches this scope', '此范围内没有匹配发现')} />}</div>}
    <Audit data={record} title={t('Source grouping record', '来源分组记录')} />
  </article>;
}
