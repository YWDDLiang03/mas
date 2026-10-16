import type { ResearchBrief as Brief } from '../api/types';
import { useInterpretationPreparation } from '../hooks/useInterpretation';
import { useI18n } from '../i18n';
import { ResearchBrief } from './ResearchBrief';
import { Audit, Icon } from './UI';

export function CriterionResearchBrief({ task, criterionRef, brief, enabled, onEvidence }: {
  task: string; criterionRef: string; brief?: Brief; enabled: boolean; onEvidence: (claim: string) => void;
}) {
  const { t } = useI18n();
  const preparation = useInterpretationPreparation(task, criterionRef);
  const prepared = preparation.response?.overview.items.find(item => item.criterion_ref === criterionRef
    && item.input_hash === brief?.input_hash && item.status === 'ready');
  const reading = prepared || brief;
  const needsPreparation = !reading || ['missing', 'stale', 'error'].includes(reading.status);
  return <><ResearchBrief brief={reading} onEvidence={onEvidence} />{(needsPreparation || preparation.pending) && <section className="interpretation-prepare"><div><strong>{t('Research interpretation', '研究解读')}</strong><p>{t('Interpret the saved sources for this criterion version. This does not change or approve the criterion.', '解读此标准版本的已保存来源，不改变或批准该标准。')}</p></div>{enabled && <button type="button" className="primary" disabled={preparation.pending} onClick={() => void preparation.prepare()}><Icon name={preparation.pending ? 'refresh' : 'criteria'} size={14} />{preparation.pending ? t('Preparing…', '生成中…') : t('Prepare research interpretation', '生成研究解读')}</button>}{preparation.pending && <p className="field-note" role="status">{t('You can browse other records while this interpretation is prepared.', '生成期间可以继续浏览其他记录。')}</p>}{needsPreparation && preparation.error && <p className="inline-error" role="alert">{preparation.error}</p>}</section>}{preparation.response && <Audit data={{ criterion_ref: criterionRef, result: preparation.response.result, annotation_usage: preparation.response.overview.cost }} title={t('Interpretation usage & cost record', '解读用量与费用记录')} />}</>;
}
