import type { MouseEvent, ReactNode } from 'react';
import type { EvidenceLinks, EvidenceLinkScope, LinkedCandidate, LinkedCriterion } from '../api/types';
import { routeHref, type Route } from '../hooks/useRoute';
import { useI18n } from '../i18n';
import { dateText } from './UI';
import './ResearchLinks.css';

export type ResearchNavigate = (target: Partial<Route>) => void;

export function candidateRelationships(record: LinkedCandidate): string[] {
  return [...new Set(record.relationships?.length ? record.relationships : record.relationship ? [record.relationship] : [])];
}
export function criterionBasisOnly(records: LinkedCandidate[]): boolean {
  return records.length > 0 && records.every(record => {
    const roles = candidateRelationships(record);
    return roles.length > 0 && roles.every(role => role === 'criterion_basis');
  });
}
export function CandidateConnectionNote() {
  const { t } = useI18n();
  return <p className="candidate-connection-note">{t('The displayed candidates are linked through the criterion’s research basis.', '这里展示的候选通过标准的研究依据关联。')}</p>;
}

export function ResearchLink({ to, onNavigate, children, className }: { to: Partial<Route>; onNavigate?: ResearchNavigate; children: ReactNode; className?: string }) {
  const { language } = useI18n();
  const target = { item: '', snapshot: '', criterion: '', candidate: '', source: '', ...to };
  function follow(event: MouseEvent<HTMLAnchorElement>) {
    if (!onNavigate || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); onNavigate(target);
  }
  return <a className={className} href={routeHref(target, language)} onClick={follow}>{children}</a>;
}

export function CriterionLink({ record, task, onNavigate, snapshot }: { record: LinkedCriterion; task: string; onNavigate?: ResearchNavigate; snapshot?: string }) {
  const { t } = useI18n();
  const version = /@v(\d+)$/.exec(record.detail_ref)?.[1];
  return <ResearchLink to={{ view: 'criteria', task, item: record.detail_ref, snapshot }} onNavigate={onNavigate}>{record.name || t('Criterion', '标准')}{version && <small> · {record.detail_ref.startsWith('cri_') ? t('proposal', '提案') : t('criterion', '标准')} v{version}</small>}</ResearchLink>;
}

export function CandidateLink({ record, task, onNavigate }: { record: LinkedCandidate; task: string; onNavigate?: ResearchNavigate }) {
  const { t } = useI18n();
  const labels: Record<string, string> = {
    criterion_basis: t('Criterion basis', '标准依据'), used_in_assessment: t('Used for assessment value', '用于评估取值'),
    counter_evidence: t('Counter-evidence', '反证'), set_aside: t('Set aside for this value', '未用于本次取值'),
    supports_criterion: t('Criterion support', '标准支持'), multiple_recorded_uses: t('Multiple recorded uses', '多种已记录用途'),
  };
  const roles = candidateRelationships(record);
  return <ResearchLink to={record.snapshot_id ? { view: 'candidates', task, item: record.candidate_ref, snapshot: record.snapshot_id } : { view: 'evidence', task, candidate: record.candidate_ref }} onNavigate={onNavigate}>{record.label || t('Candidate', '候选')}{!record.snapshot_id && <small>{t(' · evidence', ' · 证据')}</small>}{roles.length > 0 && <small className="candidate-link-roles">{roles.map(role => <span key={role}>{labels[role] || role}</span>)}</small>}</ResearchLink>;
}

export function EvidenceConnectionScope({ scope }: { scope?: EvidenceLinkScope }) {
  const { t, language } = useI18n();
  if (!scope) return null;
  if (scope.mode === 'task_history') return <p className="subtle">{t('Connections across all saved runs', '全部已保存运行中的关联')}</p>;
  if (!scope.snapshot_id) return null;
  return <p className="subtle">{scope.mode === 'latest_snapshot' ? t('Connections in the latest saved evaluation', '最近保存评估中的关联') : t('Connections in the selected saved evaluation', '所选保存评估中的关联')}{scope.snapshot_published_at && <> · <time dateTime={scope.snapshot_published_at}>{dateText(scope.snapshot_published_at, language)}</time></>}</p>;
}

export function EvidenceConnections({ links, task, onNavigate, onShowAll, snapshot }: { links?: EvidenceLinks; task: string; onNavigate?: ResearchNavigate; onShowAll?: () => void; snapshot?: string }) {
  const { t } = useI18n();
  if (!links || (!links.counts.criteria && !links.counts.candidates)) return null;
  const uniqueCandidates = links.scope?.candidate_unit === 'unique_candidates';
  const viaCriteria = criterionBasisOnly(links.candidates);
  const linkedSnapshot = links.scope ? links.scope.snapshot_id || undefined : snapshot;
  return <div className="evidence-connections"><EvidenceConnectionScope scope={links.scope} />{links.criteria.length > 0 && <div><span>{t('Linked criterion versions', '关联标准版本')}</span><div>{links.criteria.map((record, index) => <CriterionLink key={`${record.detail_ref}/${index}`} record={record} task={task} onNavigate={onNavigate} snapshot={linkedSnapshot} />)}</div></div>}{links.candidates.length > 0 && <div><span>{viaCriteria ? uniqueCandidates ? t('Candidates linked via criteria', '通过标准关联的候选') : t('Assessment / run records linked via criteria', '通过标准关联的评估 / 运行记录') : uniqueCandidates ? t('Linked candidates', '关联候选') : t('Linked assessment / run records', '关联评估 / 运行记录')}</span>{viaCriteria && <CandidateConnectionNote />}<div>{links.candidates.map((record, index) => <CandidateLink key={`${record.candidate_ref}/${record.snapshot_id}/${index}`} record={record} task={task} onNavigate={onNavigate} />)}</div></div>}{onShowAll && (links.counts.criteria > links.criteria.length || links.counts.candidates > links.candidates.length) && <button type="button" className="text-button" onClick={onShowAll}>{t('View all connections', '查看全部关联')} · {links.counts.criteria} {t('criterion versions', '个标准版本')} · {links.counts.candidates} {uniqueCandidates ? t('unique candidates', '个独立候选') : t('assessment / run records', '条评估 / 运行记录')}</button>}</div>;
}
