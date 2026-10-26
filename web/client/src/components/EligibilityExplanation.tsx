import type { Candidate, SelectionReading, EligibilityReading, EligibilitySummary as Summary, EligibilityRequirements } from '../api/types';
import { useI18n } from '../i18n';
import { ResearchLink, type ResearchNavigate } from './ResearchLinks';

type Translate = (en: string, zh: string) => string;

export function selectionLabel(value: string | undefined, t: Translate) {
  return ({ eligible: t('Eligible', '符合准入要求'), evidence_incomplete: t('Evidence incomplete', '准入证据不完整'), excluded: t('Excluded', '已排除'), incomplete: t('Assessment incomplete', '评估未完成'), not_ready: t('Criteria not ready', '条件未就绪') } as Record<string, string>)[value || ''] || t('Assessment incomplete', '评估未完成');
}
export function eligibilityLabel(candidate: Pick<Candidate, 'selection'>, t: Translate) {
  return selectionLabel(candidate.selection?.decision, t);
}

export function eligibilityReason(reading: EligibilityReading | undefined, t: Translate, selection?: SelectionReading) {
  if (!reading) return '';
  if (selection?.reason_code === 'no_required_evidence') return t('Excluded: no admission requirement has usable support.', '已排除：本任务的准入要求均缺少可用依据。');
  if (selection?.decision === 'incomplete') return t('A required assessment is incomplete or failed. See the affected requirement below.', '有必需评估未完成或执行失败，请查看具体要求。');
  const labels: Record<string, string> = {
    required_evidence_conflicted: t('Conflicting evidence prevents a required determination.', '证据冲突使必需判定尚未成立。'),
    required_interpretation_unresolved: t('A required observation needs a defined interpretation method.', '必需观测还需明确判读方法。'),
    direct_evidence_requirement_not_met: t('Values are recorded, but the required direct evidence is unavailable.', '已有数值记录，仍缺少所需的直接证据。'),
    requirements_met: t('All eligibility requirements satisfied: conditions met and required direct evidence available.', '全部准入要求已满足：条件判定通过，必需直接证据齐全。'),
    mandatory_failure: t('Excluded: direct evidence establishes a required condition failure.', '已排除：直接证据确认未满足条件要求。'),
    mandatory_and_required_unresolved: t('Evidence is incomplete for required conditions and required observations.', '条件要求与必需观测的证据均不完整。'),
    mandatory_unresolved: t('Required observations are available; a required condition still needs evidence.', '必需观测已具备，仍需证据确认条件要求。'),
    required_observations_unresolved: t('Required conditions are met; required direct evidence is incomplete.', '条件要求已满足，必需直接证据仍有缺口。'),
    criteria_not_ready: t('Define and verify the task’s eligibility requirements before assessment.', '先定义并核验任务的准入要求，再进行评估。'),
    historical_policy: t('This historical result does not establish eligibility under the current policy.', '此历史结果未按当前政策确定资格。'),
    not_assessed: t('Eligibility has not been assessed.', '尚未评估资格。'),
    reason_not_recorded: t('A detailed eligibility reason was not recorded.', '未记录具体资格原因。'),
  };
  return labels[reading.reason_code] || reading.description;
}

export function evidenceProfileLabel(state: string | undefined, t: Translate) {
  const labels: Record<string, string> = {
    complete: t('Required evidence complete', '准入依据齐全'),
    partial: t('Partial admission support', '部分准入依据已具备'),
    none: t('No admission support', '无准入依据'),
    failed: t('Required condition failed', '条件要求已确认失败'),
    unknown: t('Evidence profile unavailable', '准入依据记录不完整'),
  };
  return labels[state || 'unknown'] || labels.unknown;
}

export function EligibilitySummary({ value, kind = 'evidence_incomplete', profile = '', onProfile }: { value?: Summary; kind?: 'evidence_incomplete' | 'excluded'; profile?: string; onProfile?: (value: string) => void }) {
  const { t } = useI18n();
  if (!value || !value.total) return null;
  const labels: Record<string, string> = {
    mandatory_failure: t('Required condition not met', '条件要求未满足'),
    required_evidence_conflicted: t('Required evidence conflicts', '必需证据冲突'),
    required_interpretation_unresolved: t('Required interpretation unresolved', '必需判读方法未确定'),
    direct_evidence_requirement_not_met: t('Required direct basis unavailable', '所需直接依据不可用'),
    required_observations_unresolved: t('Required observations missing', '缺少必需观测证据'),
    mandatory_unresolved: t('Evidence for a required condition missing', '缺少条件要求的确认依据'),
    mandatory_and_required_unresolved: t('Evidence gaps in both kinds of requirements', '两类准入要求均有证据缺口'),
  };
  const title = kind === 'evidence_incomplete' ? t('What is established, and what is missing', '已具备哪些依据，还缺少什么') : t('Exclusion reasons', '排除原因');
  return <section className="eligibility-summary" aria-label={title}>
    <h2>{title}</h2>
    {kind === 'evidence_incomplete' ? <>
      <p>{t('Inspect which admission requirements are established and which still need evidence.', '查看哪些准入要求已有依据、哪些还需补证。')}</p>
      <p className="field-note">{t('The table shows required conditions met and required observations available for each candidate.', '下表分别显示每个候选满足的条件要求与可用的必需观测。')}</p>
    </> : <>
      <p>{t('Candidates are excluded when a required condition fails or no admission requirement has usable support.', '条件要求失败，或准入要求均无可用依据时，候选被排除。')}</p>
      <div className="eligibility-groups">{['none', 'failed'].filter(state => (value.profile_counts?.[state] || 0) > 0).map(state => <div key={state}><strong>{value.profile_counts?.[state].toLocaleString()}</strong><span>{evidenceProfileLabel(state, t)}</span></div>)}</div>
    </>}
    <details><summary>{t('Specific evidence gaps and requirements', '具体证据缺口与要求')}</summary>
      <div className="eligibility-groups">{Object.entries(value.groups).filter(([key, count]) => labels[key] && count > 0).map(([key, count]) => <div key={key}><strong>{count.toLocaleString()}</strong><span>{labels[key]}</span></div>)}</div>
      <p className="field-note">{t('The reason groups above are mutually exclusive. The per-requirement counts below may overlap.', '上方原因分组互不重叠；下方逐项要求的计数可能重叠。')}</p>
      <ul>{value.requirements.map(item => <li key={`${item.role}/${item.rule_ref}`}><span>{item.name}</span><b>{item.count.toLocaleString()}</b></li>)}</ul>
    </details>
  </section>;
}

export function EligibilityExplanation({ value, selection, requirements, task, snapshot, onNavigate }: { value?: EligibilityReading; requirements?: EligibilityRequirements; selection?: SelectionReading; task: string; snapshot: string; onNavigate: ResearchNavigate }) {
  const { t } = useI18n();
  if (!value) return null;
  const labels: Record<string, string> = {
    no_usable_direct_evidence: t('No usable direct evidence', '缺少可用的直接证据'),
    direct_evidence_unresolved: t('Direct-evidence requirement unresolved', '直接证据要求未确定'),
    confirmed_failure: t('Confirmed failure', '已确认未满足'),
    conflicting_evidence: t('Conflicting evidence', '证据冲突'),
    interpretation_unresolved: t('Interpretation unresolved', '判读方法未确定'),
    assessment_record_unavailable: t('Assessment record unavailable', '评估记录不可用'),
    tool_error: t('Evidence retrieval or assessment failed', '证据获取或评估失败'),
    not_assessed: t('Not assessed', '尚未评估'), not_applicable: t('Not applicable', '不适用'),
  };
  return <section className="eligibility-explanation"><h3>{t('Eligibility requirements', '准入要求')}{requirements ? ` · ${requirements.total}` : ''}</h3>{requirements && <p>{requirements.condition_count} {t(requirements.condition_count === 1 ? 'condition check' : 'condition checks', '项条件判定')} · {requirements.evidence_count} {t('evidence requirements', '项证据要求')}{requirements.condition_evidence_overlap > 0 && <> · {requirements.condition_evidence_overlap} {t('shared condition/evidence requirements', '项同时属于条件和证据要求')}</>}{requirements.scoring_overlap_count > 0 && <> · {requirements.scoring_overlap_count} {t('also used in scoring', '项同时用于计分')}</>}</p>}{value.evidence_profile && <p className={`evidence-profile-label ${value.evidence_profile.state}`}>{evidenceProfileLabel(value.evidence_profile.state, t)}</p>}<p>{eligibilityReason(value, t, selection)}</p>
    {value.issues.length > 0 && <ul>{value.issues.map(item => <li key={`${item.role}/${item.rule_ref}`}>
      <ResearchLink to={{ task, view: 'criteria', item: item.rule_ref, snapshot }} onNavigate={onNavigate}>{item.name}</ResearchLink>
      <span>{labels[item.issue] || item.issue}</span>
      {item.recorded_reason && <details><summary>{t('Recorded assessment', '查看判定记录')}</summary><p>{item.recorded_reason}</p></details>}
    </li>)}</ul>}
  </section>;
}
