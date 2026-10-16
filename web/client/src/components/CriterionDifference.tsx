import { stateText, useI18n } from '../i18n';
import { valueText } from './UI';
import './CriterionDifference.css';

type RecordValue = Record<string, unknown>;
type Group = 'attribute' | 'rule' | 'proposal' | 'criterion';
const visibleFields = ['name', 'definition', 'role', 'rule_kind', 'direction', 'cutoff', 'unit', 'state',
  'acceptable_value_sources', 'acceptable_determination_bases', 'evidence_request', 'evidence_requests', 'attribute_ref', 'value'];
function object(value: unknown): RecordValue | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as RecordValue : undefined;
}
function groups(value: unknown): Partial<Record<Group, RecordValue>> {
  const record = object(value);
  if (!record) return value == null ? {} : { criterion: { value } };
  const nested: Partial<Record<Group, RecordValue>> = {};
  for (const key of ['attribute', 'rule'] as const) if (object(record[key])) nested[key] = object(record[key]);
  if (Object.keys(nested).length) return nested;
  return { [record.attribute_id ? 'attribute' : record.rule_id ? 'rule' : record.criterion_id ? 'proposal' : 'criterion']: record };
}
function comparable(value: unknown): string | undefined {
  if (Array.isArray(value)) return JSON.stringify(value.map(item => comparable(item)));
  const record = object(value);
  return record ? JSON.stringify(Object.keys(record).sort().map(key => [key, comparable(record[key])])) : JSON.stringify(value);
}

/** Strip only identified plan digests from the presentation; the caller keeps the original audit record. */
export function readableChangeReason(reason: unknown): string {
  if (typeof reason !== 'string') return '';
  return reason.replace(/(?:\s*[;·,]\s*|\s+)?\bplan(?:[_ -]?(?:hash|sha256))?\s*[:=]?\s*[a-f0-9]{64}\b/gi, '')
    .replace(/[;·,\s]+$/, '').trim();
}
export function CriterionChangeReason({ reason }: { reason: unknown }) {
  const text = readableChangeReason(reason);
  return text ? <p>{text}</p> : null;
}

export function CriterionDifference({ before, after }: { before: unknown; after: unknown }) {
  const { t } = useI18n();
  const left = groups(before), right = groups(after);
  const labels: Record<string, string> = {
    name: t('Name', '名称'), definition: t('Definition', '定义'), role: t('Role', '用途'), rule_kind: t('Role', '用途'),
    direction: t('Direction', '方向'), cutoff: t('Threshold', '阈值'), unit: t('Unit', '单位'), state: t('State', '状态'),
    acceptable_value_sources: t('Accepted evidence types', '接受的证据类型'),
    acceptable_determination_bases: t('Accepted evidence bases', '接受的依据类型'),
    evidence_request: t('Evidence route', '证据获取路线'), evidence_requests: t('Evidence routes', '证据获取路线'),
    attribute_ref: t('Linked attribute version', '关联属性版本'), value: t('Value', '内容'),
  };
  const kinds: Record<Group, string> = {
    attribute: t('Attribute definition', '属性定义'), rule: t('Evaluation rule', '评估规则'),
    proposal: t('Criterion proposal', '标准提案'), criterion: t('Criterion', '标准'),
  };
  const sourceKinds: Record<string, string> = {
    model_prediction: t('Model prediction', '模型预测'), database_entry: t('Database record', '数据库记录'),
    peer_reviewed: t('Peer-reviewed source', '同行评审来源'), curated_measurement: t('Curated measurement', '整理的测量记录'),
    reference_text: t('Reference text', '参考资料'), user_supplied_document: t('Supplied document', '用户提供的文档'),
  };
  function route(value: unknown, index: number) {
    const record = object(value);
    if (!record) return <span key={index}>{valueText(value)}</span>;
    const names: Record<string, string> = {
      admet_prediction: t('ADMET model prediction', 'ADMET 模型预测'),
      admet_computed_property: t('Saved RDKit descriptor', '已保存 RDKit 描述符'),
      computed_property: t('Recorded computed property', '已记录的计算性质'),
      pchembl_values: t('Recorded target measurements', '已记录的靶点测量'),
      gtopdb_affinity: t('Recorded affinity values', '已记录的亲和力'),
      record_field: t('Recorded field', '已记录字段'), search: t('Literature search', '文献检索'),
    };
    const parameters = object(record.parameters) || {};
    const capabilities: Record<string, string> = {
      predicted_property_lookup: t('Property prediction', '性质预测'), property_estimate: t('Property estimate', '性质估计'),
      interaction_evidence_lookup: t('Target interaction lookup', '靶点相互作用查询'),
      record_field_lookup: t('Recorded field lookup', '记录字段查询'), literature_retrieval: t('Literature retrieval', '文献获取'),
    };
    const parameterLabels: Record<string, string> = {
      endpoint: t('Endpoint', '端点'), property: t('Property', '性质'), field: t('Field', '字段'),
      target_chembl_id: t('Target ID', '靶点标识'), query_template: t('Query template', '检索式'),
      relevance_terms: t('Search terms', '检索词'), search_limit: t('Source limit', '来源数量上限'),
    };
    return <div className="criterion-diff-route" key={index}><strong>{names[String(record.question_kind)] || valueText(record.question_kind || record.capability)}</strong><dl>{record.capability != null && <div><dt>{t('Operation', '操作类型')}</dt><dd>{capabilities[String(record.capability)] || valueText(record.capability)}</dd></div>}{record.identifier_scheme != null && <div><dt>{t('Identifier', '标识方式')}</dt><dd>{record.identifier_scheme === 'inchikey' ? 'InChIKey' : valueText(record.identifier_scheme)}</dd></div>}{Object.entries(parameters).map(([key, value]) => <div key={key}><dt>{parameterLabels[key] || key}</dt><dd>{Array.isArray(value) ? value.map(valueText).join(' · ') : valueText(value)}</dd></div>)}</dl></div>;
  }
  function display(field: string, value: unknown, other: unknown) {
    if (value === undefined || value === null) return '—';
    if (field === 'evidence_request' || field === 'evidence_requests') return <div className="criterion-diff-routes">{(Array.isArray(value) ? value : [value]).map(route)}</div>;
    if (field === 'acceptable_value_sources' || field === 'acceptable_determination_bases') {
      const values = Array.isArray(value) ? value : [value];
      return <ul className="criterion-diff-values">{values.map((item, index) => <li key={index}>{typeof item === 'string' ? field === 'acceptable_value_sources' ? sourceKinds[item] || item : stateText(item, t) : valueText(item)}</li>)}</ul>;
    }
    if (field === 'attribute_ref' && typeof value === 'string' && typeof other === 'string'
      && value.split('@v')[0] === other.split('@v')[0]) return `v${value.split('@v')[1] || '—'}`;
    return ['role', 'rule_kind', 'direction', 'state'].includes(field) && typeof value === 'string' ? stateText(value, t) : valueText(value);
  }
  return <>{([...new Set([...Object.keys(left), ...Object.keys(right)])] as Group[]).map(group => {
    const before = left[group] || {}, after = right[group] || {};
    const changed = visibleFields.filter(field => comparable(before[field]) !== comparable(after[field]));
    if (!changed.length) return null;
    const version = (record: RecordValue) => record.version == null ? '—' : `v${record.version}`;
    return <section className="criterion-diff-group" key={group}><h4>{kinds[group]}{(before.version != null || after.version != null) && <span> · {version(before)} → {version(after)}</span>}</h4><div className="difference"><div className="difference-head"><span>{t('Before', '之前')}</span><span>{t('After', '之后')}</span></div>{changed.map(field => <div className="difference-row" key={field}><span><small>{labels[field]}</small>{display(field, before[field], after[field])}</span><span><small>{labels[field]}</small>{display(field, after[field], before[field])}</span></div>)}</div></section>;
  })}</>;
}
