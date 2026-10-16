import type { CriterionSource, Evidence } from '../api/types';
import { stateText, useI18n } from '../i18n';
import { Audit, Badge, safeUrl, valueText } from './UI';
import { EvidenceConnections, ResearchLink, type ResearchNavigate } from './ResearchLinks';

function sourceLabel(id: string, fallback: string) {
  const identifier = /^src_(doi|pmid|pubmed|pmcid|pmc)_(.+)$/i.exec(id);
  if (!identifier) return fallback;
  const scheme = identifier[1].toLowerCase();
  const label = scheme === 'doi' ? 'DOI' : scheme === 'pmcid' || scheme === 'pmc' ? 'PubMed Central' : 'PubMed';
  return `${label}: ${identifier[2]}`;
}

interface UploadedMeasurement {
  measurement_id: string; candidate_id: string; property_id: string; basis: string;
  value: string | number | boolean | null; property_label?: string; unit?: string | null;
  conditions?: Record<string, unknown> | string; declared_source?: string; source_locator?: string;
  row_number?: number; provenance?: { filename?: string };
}

function uploadedMeasurement(excerpt?: string | null): UploadedMeasurement | null {
  if (!excerpt) return null;
  try {
    const row: unknown = JSON.parse(excerpt);
    if (!row || typeof row !== 'object' || Array.isArray(row)) return null;
    const fields = row as Record<string, unknown>;
    if (!['measurement_id', 'candidate_id', 'property_id', 'basis'].every(key => typeof fields[key] === 'string' && fields[key] !== '')) return null;
    if (!Object.hasOwn(fields, 'value') || !(fields.value === null || ['string', 'number', 'boolean'].includes(typeof fields.value))) return null;
    return fields as unknown as UploadedMeasurement;
  } catch { return null; }
}

export function EvidenceCard({ record, task, onOpen, onNavigate, snapshot }: {
  record: Evidence | CriterionSource; task?: string; onOpen?: (claim: string) => void; onNavigate?: ResearchNavigate; snapshot?: string;
}) {
  const { t } = useI18n();
  const source = record.source;
  const url = safeUrl(source?.url || record.url);
  const evidence = record as Partial<Evidence>;
  const originalTitle = source?.title || record.title;
  const title = originalTitle?.trim() && originalTitle !== record.source_id ? originalTitle : sourceLabel(record.source_id, t('Source', '来源'));
  const excerpt = source?.excerpt || record.quote;
  const measurement = uploadedMeasurement(excerpt);
  const locator = source?.locator || record.locator;
  const open = record.claim_id && onOpen ? () => onOpen(record.claim_id!) : undefined;
  const conditions = measurement?.conditions;
  const owner = measurement && record.links?.candidates.find(candidate => candidate.candidate_ref === measurement.candidate_id);
  return <article className="evidence-card">
    <header><div>{record.summary?.text ? <><span className="evidence-record-label">{t('Recorded finding', '已记录发现')}</span><h3>{record.summary.text}</h3><p className="evidence-source-title">{title}</p></> : <h3>{title}</h3>}{locator && <p>{locator}</p>}</div>{evidence.basis && <Badge state={evidence.basis} label={stateText(evidence.basis, t)} />}</header>
    {measurement ? <dl className="measurement-facts">
      <div><dt>{t('Observation for', '观测对象')}</dt><dd>{owner?.label && owner.label !== measurement.candidate_id ? `${owner.label} · ${measurement.candidate_id}` : measurement.candidate_id}</dd></div>
      <div><dt>{t('Property', '测量属性')}</dt><dd>{typeof measurement.property_label === 'string' ? measurement.property_label : measurement.property_id}</dd></div>
      <div><dt>{t('Observed value', '观测值')}</dt><dd className="numeric">{valueText(evidence.value ?? measurement.value)} {evidence.unit ?? measurement.unit}</dd></div>
      <div className="measurement-conditions"><dt>{t('Conditions', '条件')}</dt><dd>{typeof conditions === 'string' ? conditions : conditions && typeof conditions === 'object' && !Array.isArray(conditions) && Object.keys(conditions).length ? <dl>{Object.entries(conditions).map(([key, value]) => <div key={key}>{key !== 'description' && <dt>{key}</dt>}<dd>{valueText(value)}</dd></div>)}</dl> : t('Not recorded', '未记录')}</dd></div>
      <div><dt>{t('Declared basis', '声明的依据类型')}</dt><dd>{stateText(measurement.basis, t)}</dd></div>
      <div><dt>{t('Source', '来源')}</dt><dd>{measurement.declared_source || measurement.provenance?.filename || title}</dd></div>
      <div><dt>{t('Row locator', '数据行位置')}</dt><dd>{measurement.source_locator || locator || (typeof measurement.row_number === 'number' ? `${t('CSV row', 'CSV 行')} ${measurement.row_number}` : t('Not recorded', '未记录'))}</dd></div>
    </dl> : <>{excerpt && <blockquote>{excerpt}</blockquote>}{evidence.value != null && <p className="numeric evidence-value">{valueText(evidence.value)} {evidence.unit}</p>}</>}
    {task && <EvidenceConnections links={record.links} task={task} snapshot={snapshot} onNavigate={onNavigate} onShowAll={open} />}
    <footer>{open ? <button type="button" className="text-button" onClick={open}>{t('Read evidence & context', '查看证据与上下文')} →</button> : record.claim_id && task ? <ResearchLink className="text-button" to={{ task, view: 'evidence', item: record.claim_id, snapshot }} onNavigate={onNavigate}>{t('Read evidence & context', '查看证据与上下文')} →</ResearchLink> : null}{url && <a href={url} target="_blank" rel="noopener noreferrer">{t('Open source', '打开来源')} ↗</a>}<Audit data={record} title={t('Source record', '来源记录')} /></footer>
  </article>;
}
