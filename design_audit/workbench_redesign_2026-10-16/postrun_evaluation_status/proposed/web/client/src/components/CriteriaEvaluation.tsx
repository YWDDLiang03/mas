import type { CriterionEvaluation } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge } from './UI';

export function CriteriaEvaluation({ value, compact = false }: { value?: CriterionEvaluation; compact?: boolean }) {
  const { t } = useI18n();
  if (!value) return null;
  const labels = {
    enabled: t('Enabled', '已启用'), deferred: t('Deferred', '已延后'), pending: t('Pending', '待处理'),
    not_prepared: t('Not prepared', '尚未准备'), historical: t('Saved version', '历史版本'),
  };
  const reasons: Record<string, string> = {
    enabled: t('Included in the latest prepared evaluation.', '已纳入最近准备的评估。'),
    unresolved_review: t('Review remains unresolved; this criterion is not enabled.', '复核尚未解决，此标准暂未启用。'),
    non_executable_preference: t('The scoring condition is not executable yet.', '计分条件尚不可执行。'),
    capability_deferred: t('The required evidence route is deferred.', '所需证据路线已延后处理。'),
    review_pending: t('Listed as pending when this evaluation was prepared.', '准备本次评估时，此标准仍待复核。'),
    unregistered_proposal: t('This proposal has not been registered for evaluation.', '此提案尚未注册为评估标准。'),
    not_selected: t('Not included; an exclusion reason is not recorded.', '尚未纳入，未记录具体排除理由。'),
    not_prepared: t('No evaluation has been prepared for this task.', '此任务尚未准备评估。'),
    historical_view: t('See the saved version and its change history.', '查看此保存版本及其变化历史。'),
  };
  const summary = reasons[value.reason_kind] || t('See the recorded decision for the reason.', '具体理由请查看处理记录。');
  const badge = <Badge state={value.state === 'enabled' ? 'completed' : ['deferred', 'pending'].includes(value.state) ? 'pending' : undefined} label={labels[value.state]} />;
  return compact ? <>{badge}<p className="cell-note">{summary}</p></> : <section className="notice"><div className="row spread"><strong>{value.state === 'historical' ? t('Saved version', '历史版本') : t('Latest prepared evaluation', '最近准备的评估')}</strong>{badge}</div><p>{summary}</p><Audit data={value} title={t('Decision record', '处理记录')} /></section>;
}
