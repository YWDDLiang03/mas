import type { ResearchBrief as Brief } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Badge, dateText } from './UI';

export function ResearchBrief({ brief, onEvidence }: { brief?: Brief; onEvidence?: (claim: string) => void }) {
  const { t, language } = useI18n();
  if (!brief) return null;
  if (brief.status === 'missing' || brief.status === 'error') return <details className="research-brief unavailable"><summary>{t('AI interpretation', 'AI 解读')} · {t('Not available', '暂无')}</summary><p>{t('The recorded criterion and evidence remain available below.', '仍可在下方查看已记录的标准与证据。')}</p><Audit data={brief} /></details>;
  const sections = [
    { key: 'conclusion' as const, label: t('What it tells us', '结论') },
    { key: 'task_implication' as const, label: t('Why it matters here', '与本研究的关系') },
    { key: 'conditions' as const, label: t('Conditions & scope', '条件与范围') },
    { key: 'limitations' as const, label: t('Limits to the interpretation', '解读边界') },
  ];
  const claims = [...new Set(sections.flatMap(section => brief.sections?.[section.key]?.flatMap(item => item.claim_refs) || []))];
  return <section className={`research-brief ${brief.status}`}><header><div><span className="eyebrow">{brief.status === 'task_backed' ? t('Task requirement', '任务要求') : t('AI interpretation', 'AI 解读')}</span><h3>{brief.status === 'task_backed' ? t('What this task requires', '这项任务的要求') : t('A source-linked research reading', '有来源依据的研究解读')}</h3></div><Badge label={brief.status === 'stale' ? t('Earlier version', '早期版本') : brief.status === 'task_backed' ? t('From task context', '来自任务目标') : t('Source linked', '关联来源')} /></header>{brief.status === 'stale' && <p className="notice">{t('This interpretation belongs to an earlier saved input. Refer to the current criterion and its source evidence.', '此解读对应早期保存的输入，请以当前标准及其来源证据为准。')}</p>}<div className="brief-sections">{sections.map(section => brief.sections?.[section.key]?.length ? <div key={section.key}><h4>{section.label}</h4>{brief.sections[section.key]!.map((item, index) => <div key={index}><p>{item.text}</p>{item.claim_refs.length > 0 && <div className="brief-citations">{item.claim_refs.map(ref => onEvidence ? <button type="button" className="text-button" key={ref} onClick={() => onEvidence(ref)}>{t('Evidence', '证据')} {claims.indexOf(ref) + 1}</button> : <span key={ref}>{t('Evidence', '证据')} {claims.indexOf(ref) + 1}</span>)}</div>}{!item.claim_refs.length && !!item.task_refs?.length && <small>{t('Based on the declared task requirement.', '依据已声明的任务要求。')}</small>}</div>)}</div> : null)}</div><footer>{brief.generated_at && <small>{dateText(brief.generated_at, language)}</small>}{brief.model_id && <small>{brief.model_id}</small>}<Audit data={brief} title={t('Interpretation record & citations', '解读记录与引用')} /></footer></section>;
}
