import type { CriterionEvaluation } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge } from './UI';

type Translate = (en: string, zh: string) => string;
export function dispositionLabel(code: string, t: Translate) {
  const labels: Record<string, [string, string]> = {
    mandatory_requirement: ['Mandatory requirement', '强制要求'],
    weighted_criterion: ['Weighted prioritization criterion', '加权排序标准'],
    context_only: ['Contextual observation', '参考观察项'],
    comparison_incomplete: ['Scoring definition incomplete', '计分定义不完整'],
    review_unresolved: ['Review unresolved', '审查意见未解决'],
    unit_mapping_unresolved: ['Unit conversion unresolved', '单位换算未确定'],
    alternative_policy_unresolved: ['Alternative policy unresolved', '替代判定方案未确定'],
    proposal_not_finalized: ['Proposal not finalized', '提议尚未定稿'],
    evidence_route_unavailable: ['Evidence route unavailable', '证据获取方式不可用'],
    evaluation_not_prepared: ['Evaluation not prepared', '尚未准备评估'],
    historical_version: ['Historical version', '历史版本'],
    evaluation_record_unavailable: ['Evaluation record unavailable', '评估用途记录缺失'],
    reason_not_recorded: ['Not used; reason unavailable', '未采用；具体原因缺失'],
  };
  return labels[code] ? t(...labels[code]) : code;
}

export function CriteriaEvaluation({ value, compact = false }: { value?: CriterionEvaluation; compact?: boolean }) {
  const { t } = useI18n();
  if (!value) return null;
  const code = value.explanation?.code || ({ enabled: 'weighted_criterion', non_executable_preference: 'comparison_incomplete', unresolved_review: 'review_unresolved', review_pending: 'review_unresolved', unregistered_proposal: 'proposal_not_finalized', capability_deferred: 'evidence_route_unavailable', not_prepared: 'evaluation_not_prepared', historical_view: 'historical_version', evaluation_record_unavailable: 'evaluation_record_unavailable' } as Record<string, string>)[value.reason_kind] || 'reason_not_recorded';
  const descriptions: Record<string, string> = {
    mandatory_requirement: t('Determines eligibility from direct evidence.', '依据直接证据判断资格。'),
    weighted_criterion: t('Contributes to eligible candidates’ prioritization scores.', '用于合格候选的优先级评分。'),
    context_only: t('Assessed for interpretation; no eligibility or ranking weight.', '用于解释结果，不影响资格与排名。'),
    comparison_incomplete: t('The threshold, range or accepted category is undefined; no score is assigned.', '缺少明确的阈值、范围或接受类别，本次不计分。'),
    review_unresolved: t('A review objection remains unresolved; withheld from this evaluation.', '审查意见未解决，本次不纳入评估。'),
    unit_mapping_unresolved: t('The proposed unit is incompatible with the available measurement route.', '提议单位与可用测量方式不兼容。'),
    alternative_policy_unresolved: t('This quantity already has a criterion. The alternative policy is unresolved and is not counted again.', '该性质已有标准，替代判定方案尚未解决，本次不重复计分。'),
    proposal_not_finalized: t('No validated evaluation definition is available; this proposal is not used.', '尚无有效的评估定义，本次未采用此提议。'),
    evidence_route_unavailable: t('The required evidence route is unavailable in this evaluation.', '本次评估无法使用所需的证据获取方式。'),
    evaluation_not_prepared: t('No evaluation framework has been prepared for this task.', '当前任务尚未准备评估框架。'),
    historical_version: t('Inspect the version history for its recorded use.', '查看版本历史，了解当时的用途。'),
    evaluation_record_unavailable: t('Criterion use is not available for the selected evaluation.', '所选评估的标准用途记录不可用。'),
    reason_not_recorded: t('Outside the evaluation set; no specific reason was recorded.', '未纳入评估集合；未记录具体原因。'),
  };
  const summary = descriptions[code] || value.explanation?.description;
  const badge = <Badge state={value.state === 'enabled' ? 'completed' : ['deferred', 'pending'].includes(value.state) ? 'pending' : undefined} label={dispositionLabel(code, t)} />;
  return compact ? <>{badge}<p className="cell-note">{summary}</p></> : <section className="notice"><div className="row spread"><strong>{value.scope === 'selected_evaluation' ? t('Use in the selected evaluation', '所选评估中的用途') : t('Use in the latest prepared evaluation', '最近准备的评估中的用途')}</strong>{badge}</div><p>{summary}</p><Audit data={value} title={t('Recorded decision & review', '判定与审查记录')} /></section>;
}
