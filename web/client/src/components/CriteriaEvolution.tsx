import type { Overview, Stage } from '../api/types';
import { useI18n } from '../i18n';
import { valueText } from './UI';

export function stageCountScope(stage: Stage | undefined, t: (en: string, zh: string) => string) {
  const basis = stage?.count_basis || stage?.counts_basis;
  if (basis === 'active_registered_plus_unregistered_proposals') return t('Requirements and proposed criteria', '任务要求与候选标准');
  if (basis === 'journal_pool_boundaries' || basis === 'working_proposals') return t('Proposed criteria', '候选标准');
  if (basis === 'active_registered' || basis === 'registered_criteria') return t('Established criteria', '已确立标准');
  return t('Criteria counted at this stage', '此阶段统计的标准');
}

export function enabledCriteriaCount(overview: Overview | undefined): number | null {
  return overview?.summary.latest_frozen_rule_set_ref && overview.summary.scoring_count != null
    ? overview.summary.scoring_count : null;
}

export function CriteriaEvolution({ stages, enabledCount, summary }: { stages: Stage[]; enabledCount?: number | null; summary?: Overview['summary'] }) {
  const { t } = useI18n();
  const first = stages.find(stage => stage.before_count != null);
  const generated = stages.filter(stage => (['propose', 'generate'].includes(stage.stage) || stage.stage.startsWith('propose:')) && stage.after_count != null).reduce<Stage | undefined>((peak, stage) => !peak || stage.after_count! > peak.after_count! ? stage : peak, undefined);
  const mandated = stages.find(stage => ['mandated', 'task_requirements'].includes(stage.stage) && stage.after_count != null);
  const last = [...stages].reverse().find(stage => stage.after_count != null);
  return <><div className="criteria-journey" aria-label={t('Recorded criterion evolution', '已记录的标准演化')}><div><span>{t('At entry', '进入时')}</span><strong>{valueText(first?.before_count)}</strong><small>{stageCountScope(first, t)}</small></div><span className="journey-arrow" aria-hidden="true">→</span>{mandated && <><div><span>{t('Task requirements', '任务要求')}</span><strong>{valueText(mandated.after_count)}</strong><small>{stageCountScope(mandated, t)}</small></div><span className="journey-arrow" aria-hidden="true">→</span></>}<div><span>{t('Peak at saved stages', '已保存阶段峰值')}</span><strong>{valueText(generated?.after_count)}</strong><small>{stageCountScope(generated, t)}</small></div><span className="journey-arrow" aria-hidden="true">→</span><div className="journey-final"><span>{t('After latest stage', '最近阶段后')}</span><strong>{valueText(last?.after_count)}</strong><small>{stageCountScope(last, t)}</small></div></div>{enabledCount != null && <div className="evaluation-count"><span>{t('Enabled for evaluation', '本次启用')}</span><strong>{valueText(enabledCount)}</strong><small>{t('Prepared evaluation criteria', '本次已保存的评估标准')}</small>{summary?.enabled_core_count != null && <div className="criteria-role-breakdown"><span><b>{summary.enabled_core_count}</b> {t('core criteria', '核心标准')}<small>{summary.enabled_hard_count} {t('required', '硬条件')} · {summary.enabled_preference_count} {t('preferences', '排序偏好')}</small></span><span><b>{summary.enabled_context_count}</b> {t('context only', '仅供参考')}<small>{t('No screening or ranking weight', '不参与淘汰或计分')}</small></span><span><b>{summary.not_enabled_count}</b> {t('not enabled', '尚未启用')}<small>{t('Retained for further review', '保留供后续审查')}</small></span></div>}</div>}</>;
}
