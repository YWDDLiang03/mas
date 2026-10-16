import { useRef } from 'react';
import type { EvidenceDetail as Detail } from '../api/types';
import { stateText, useI18n } from '../i18n';
import { Audit, Pagination, safeUrl } from './UI';
import { EvidenceCard } from './EvidenceCard';
import { CandidateConnectionNote, CandidateLink, CriterionLink, criterionBasisOnly, EvidenceConnectionScope, type ResearchNavigate } from './ResearchLinks';
import { ResearchBrief } from './ResearchBrief';

export function EvidenceDetail({ detail, task, onNavigate, onEvidence, onCriteriaPage, onCandidatePage, snapshot }: {
  detail: Detail; task: string; snapshot?: string; onNavigate: ResearchNavigate; onEvidence: (claim: string) => void;
  onCriteriaPage: (page: number) => void; onCandidatePage: (page: number) => void;
}) {
  const { t } = useI18n();
  const summarySection = useRef<HTMLDivElement>(null);
  const originalSection = useRef<HTMLElement>(null);
  const connectionsSection = useRef<HTMLElement>(null);
  const savedPassage = useRef<HTMLDetailsElement>(null);
  const citedPassage = useRef<HTMLDivElement>(null);
  function jump(section: 'summary' | 'original' | 'connections') {
    if (section === 'original' && savedPassage.current) savedPassage.current.open = true;
    const target = section === 'summary' ? summarySection.current : section === 'original' ? citedPassage.current || originalSection.current : connectionsSection.current;
    target?.scrollIntoView({ block: 'start', behavior: 'auto' });
    target?.focus({ preventScroll: true });
  }
  const context = detail.context;
  const fields = context ? [
    [t('Population / material', '研究人群 / 材料'), context.population], [t('Assay / method', '实验 / 方法'), context.assay],
    [t('Conditions', '实验条件'), context.conditions], [t('Units', '单位'), context.units],
    [t('Evidence kind', '证据类型'), context.evidence_kind ? stateText(context.evidence_kind, t) : null], [t('Reading depth', '阅读深度'), context.reading_depth ? stateText(context.reading_depth, t) : null],
    [t('Verification', '核验记录'), context.verification_status ? stateText(context.verification_status, t) : null],
  ].filter(([, value]) => !!value) : [];
  const passage = detail.source;
  const hasPassages = !!(passage?.passage || passage?.before || passage?.after);
  const url = safeUrl(passage?.url || detail.url);
  const linkScope = detail.candidate_usage?.scope || detail.links?.scope;
  const candidateUnit = detail.candidate_usage?.unit || linkScope?.candidate_unit;
  const viaCriteria = criterionBasisOnly(detail.candidate_usage?.items || []);
  const criterionSnapshot = detail.criteria_usage?.scope ? detail.criteria_usage.scope.snapshot_id || undefined : detail.links?.scope ? detail.links.scope.snapshot_id || undefined : snapshot;
  return <><nav className="detail-jump-nav" aria-label={t('Evidence sections', '证据章节')}><button type="button" onClick={() => jump('summary')}>{t('Finding', '发现')}</button><button type="button" onClick={() => jump('original')}>{t('Original passage', '原文段落')}</button><button type="button" onClick={() => jump('connections')}>{t('Connections', '关联用途')}</button></nav><div ref={summarySection} tabIndex={-1} className="evidence-detail-anchor"><EvidenceCard record={detail} task={task} snapshot={snapshot} onNavigate={onNavigate} /></div>
    {detail.research_relevance?.text && <section className="detail-section"><h3>{t('Role in this research', '在本研究中的作用')}</h3><p>{detail.research_relevance.text}</p>{detail.research_relevance.scope_note && <p className="subtle">{detail.research_relevance.scope_note}</p>}</section>}
    {fields.length > 0 && <section className="detail-section"><h3>{t('What was observed', '观测条件')}</h3><dl className="evidence-context-grid">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>}
    {!!context?.limitations?.length && <section className="detail-section"><h3>{t('Limitations recorded with this evidence', '随证据记录的限制')}</h3><ul className="research-notes">{context.limitations.map((value, index) => <li key={index}>{value}</li>)}</ul></section>}
    <section className="detail-section evidence-detail-anchor" ref={originalSection} tabIndex={-1}><h3>{t('Original passage & surrounding context', '原文与相邻上下文')}</h3>{hasPassages ? <details className="saved-passage" ref={savedPassage}><summary>{t('Read the saved passage', '阅读已保存段落')}</summary>{[passage?.before, passage?.passage, passage?.after].map((record, index) => record && <div key={record.passage_id || index} ref={index === 1 ? citedPassage : undefined} tabIndex={index === 1 ? -1 : undefined} className={index === 1 ? 'cited-passage evidence-detail-anchor' : ''}><strong>{index === 0 ? t('Before the cited passage', '引用段落之前') : index === 1 ? t('Cited passage', '引用段落') : t('After the cited passage', '引用段落之后')}</strong>{record.section_path?.length > 0 && <small>{record.section_path.join(' › ')}</small>}<p>{record.text}</p></div>)}</details> : <p className="subtle">{t('Only the saved excerpt is available; no surrounding passage is recorded.', '当前仅有已保存的引用片段，未记录相邻原文。')}</p>}{url && <a href={url} target="_blank" rel="noopener noreferrer">{t('Open the original source', '打开原始来源')} ↗</a>}</section>
    {!!detail.research_briefs?.length && <section className="detail-section"><h3>{t('Research interpretations using this evidence', '使用此证据的研究解读')}</h3>{detail.research_briefs.map((brief, index) => <ResearchBrief key={`${brief.criterion_ref}/${index}`} brief={brief} onEvidence={onEvidence} />)}</section>}
    <section className="detail-section evidence-detail-anchor" ref={connectionsSection} tabIndex={-1}><h3>{t('Criterion versions using this evidence', '使用此证据的标准版本')} <span className="count">{detail.criteria_usage?.total ?? detail.links?.counts.criteria ?? '—'}</span></h3>{detail.criteria_usage?.items.length ? <><ul className="linked-record-list">{detail.criteria_usage.items.map((record, index) => <li key={`${record.detail_ref}/${index}`}><CriterionLink record={record} task={task} snapshot={criterionSnapshot} onNavigate={onNavigate} /></li>)}</ul><Pagination page={detail.criteria_usage} onChange={onCriteriaPage} /></> : <p className="subtle">{t('No recorded criterion use is linked here.', '这里没有关联的标准使用记录。')}</p>}</section>
    <section className="detail-section"><h3>{viaCriteria ? candidateUnit === 'unique_candidates' ? t('Candidates linked via criteria', '通过标准关联的候选') : t('Assessment / run records linked via criteria', '通过标准关联的评估 / 运行记录') : candidateUnit === 'unique_candidates' ? t('Candidates using this evidence', '使用此证据的独立候选') : t('Assessment / run records using this evidence', '使用此证据的评估 / 运行记录')} <span className="count">{detail.candidate_usage?.total ?? detail.links?.counts.candidates ?? '—'}</span></h3><EvidenceConnectionScope scope={linkScope} />{viaCriteria && <CandidateConnectionNote />}{detail.candidate_usage?.items.length ? <><ul className="linked-record-list">{detail.candidate_usage.items.map((record, index) => <li key={`${record.candidate_ref}/${record.snapshot_id}/${index}`}><CandidateLink record={record} task={task} onNavigate={onNavigate} />{!record.snapshot_id && <small>{t('Evidence is recorded; no saved candidate result is linked.', '已有证据记录，尚未关联已保存的候选结果。')}</small>}</li>)}</ul><Pagination page={detail.candidate_usage} onChange={onCandidatePage} /></> : <p className="subtle">{t('No recorded candidate assessment is linked here.', '这里没有关联的候选评估记录。')}</p>}</section>
    <Audit data={detail} title={t('Full evidence record', '完整证据记录')} />
  </>;
}
