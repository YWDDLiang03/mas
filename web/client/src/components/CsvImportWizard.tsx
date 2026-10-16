import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { EntityType, UploadIssue, UploadKind, UploadPreview, UploadResult } from '../api/types';
import { useI18n } from '../i18n';
import { Audit, Icon, valueText } from './UI';

const MAX_CSV_BYTES = 8 * 1024 * 1024;

export function uploadFieldLabel(key: string, t: (en: string, zh: string) => string) {
  const labels: Record<string, [string, string]> = {
    candidate_id: ['Candidate ID', '候选编号'], name: ['Candidate name', '候选名称'], property: ['Property', '测量性质'],
    value: ['Value', '数值或类别'], unit: ['Unit', '单位'], basis: ['Evidence basis', '证据依据'],
    source: ['Source', '来源'], summary: ['Observation summary', '观测说明'], description: ['Description', '说明'], conditions: ['Conditions', '实验条件'],
    smiles: ['SMILES', 'SMILES'], inchikey: ['InChIKey', 'InChIKey'], chembl_id: ['ChEMBL ID', 'ChEMBL 编号'],
  };
  return labels[key] ? t(...labels[key]) : key;
}

function uploadMessage(message: string, t: (en: string, zh: string) => string) {
  const messages: Record<string, string> = {
    'This field is required.': '此字段为必填项。',
    'Use a candidate ID of at most 200 characters.': '候选编号最多 200 个字符。',
    'Candidate IDs must be unique. Measurements belong in the separate table.': '候选编号必须唯一，测量数据请放在独立测量表中。',
    'This ID is absent from the selected candidate library; names are not matched automatically.': '所选候选库中没有此编号；不会自动按名称匹配。',
    'Choose measured, curated, predicted, simulated or derived; evidence basis is not guessed.': '请填写 measured、curated、predicted、simulated 或 derived，不自动推断证据依据。',
    'A numeric observation needs a unit; use 1 for a dimensionless quantity.': '数值观测需要单位，无量纲的量请填写 1。',
    'Missing observations should be omitted, not represented as a measured category.': '请省略缺失观测，不将其作为已测量的类别填写。',
    'Use a finite number, true/false, or a recorded category; leave missing observations out.': '请填写有限数值、true/false 或实际记录的类别，省略缺失观测。',
    'Use a valid JSON object or plain text describing the conditions.': '实验条件可用有效 JSON 对象或原文描述。',
    'Select the candidate library these measurements describe.': '请选择这些测量所对应的候选库。',
    'Imported rows keep their declared evidence basis. Import checks structure and identity; research review remains separate.': '导入会保留声明的证据依据。导入校验核对表格结构和候选编号，研究复核另行进行。',
    'Some observations have no recorded experimental conditions. Their scope will remain unspecified.': '部分观测未记录实验条件，其适用范围将保持未说明。',
    'Candidate metadata alone is not measurement evidence. Add a measurement table or choose an evidence collection.': '候选元数据本身不是测量证据，请添加测量表或明确选择证据集合。',
  };
  if (/^Map the .+ field to a column\.$/.test(message)) return t(message, '请将此字段对应到一个 CSV 列。');
  return messages[message] ? t(message, messages[message]) : message;
}

export function CsvImportWizard({ entityType, libraryId, initialKind = 'candidates', onCommitted, onPending }: {
  entityType: EntityType; libraryId?: string | null; initialKind?: UploadKind;
  onCommitted: (kind: UploadKind, result: UploadResult) => void;
  onPending?: (pending: boolean) => void;
}) {
  const { t } = useI18n();
  const [kind, setKind] = useState<UploadKind>(initialKind);
  const [pasted, setPasted] = useState(''), [pasteName, setPasteName] = useState('');
  const [preview, setPreview] = useState<UploadPreview>();
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [dirty, setDirty] = useState(false), [busy, setBusy] = useState(''), [error, setError] = useState('');
  const [saved, setSaved] = useState<UploadResult>();
  const fileInput = useRef<HTMLInputElement>(null);
  const requestVersion = useRef(0);
  useEffect(() => { onPending?.(!!busy || (!!preview && !saved)); }, [busy, preview, saved, onPending]);
  useEffect(() => {
    requestVersion.current += 1; setPreview(undefined); setMapping({}); setDirty(false); setSaved(undefined); setError(''); setBusy('');
    if (fileInput.current) fileInput.current.value = '';
  }, [kind, entityType, libraryId]);
  const needsLibrary = kind === 'measurements' && !libraryId;
  async function inspect(read: () => Promise<string>, filename: string) {
    const version = ++requestVersion.current;
    setBusy('preview'); setError(''); setSaved(undefined); setPreview(undefined);
    try {
      const content = await read();
      if (!content.trim()) throw new Error(t('This CSV is empty.', '此 CSV 文件为空。'));
      if (new TextEncoder().encode(content).length > MAX_CSV_BYTES) throw new Error(t('Use a CSV of up to 8 MiB.', '请使用不超过 8 MiB 的 CSV。'));
      const next = await api.previewUpload({ kind, filename, content, entity_type: entityType, library_id: libraryId });
      if (version !== requestVersion.current) return;
      setPreview(next); setMapping(next.mapping || {}); setDirty(false);
    } catch (issue) { if (version === requestVersion.current) setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { if (version === requestVersion.current) setBusy(''); }
  }
  async function validate() {
    if (!preview) return;
    const version = ++requestVersion.current;
    setBusy('mapping'); setError('');
    try {
      const next = await api.previewUpload({ kind, upload_id: preview.upload_id, mapping, entity_type: entityType, library_id: libraryId });
      if (version !== requestVersion.current) return;
      setPreview(next); setMapping(next.mapping || mapping); setDirty(false);
    } catch (issue) { if (version === requestVersion.current) setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { if (version === requestVersion.current) setBusy(''); }
  }
  async function commit() {
    if (!preview || dirty || !preview.can_commit || busy) return;
    const version = ++requestVersion.current;
    setBusy('commit'); setError('');
    try {
      const result = await api.commitUpload(preview.upload_id, { mapping, entity_type: entityType, library_id: libraryId });
      if (version !== requestVersion.current) return;
      setSaved(result); onCommitted(kind, result);
    } catch (issue) { if (version === requestVersion.current) setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { if (version === requestVersion.current) setBusy(''); }
  }
  const issueText = (issue: UploadIssue) => [
    issue.row_number != null || issue.row != null ? `${t('Row', '行')} ${issue.row_number ?? issue.row}` : '',
    issue.field ? uploadFieldLabel(issue.field, t) : '', uploadMessage(issue.message, t),
  ].filter(Boolean).join(' · ');
  const columns = preview?.field_schema.filter(field => !!preview.mapping[field.key]) || [];
  return <section className="csv-import" aria-label={t('Import research data', '导入研究数据')}>
    <div className="csv-step-head"><span className="csv-step-number">1</span><div><h3>{t('Choose what this CSV contains', '选择 CSV 的内容类型')}</h3><p>{t('Candidate lists define what will be compared. Measurements supply observations used to develop and assess criteria.', '候选表决定比较哪些对象；测量表提供用于生成与评估标准的观测数据。')}</p></div></div>
    <div className="csv-kind-options">{(['candidates', 'measurements'] as UploadKind[]).map(value => <button type="button" key={value} className={value === kind ? 'selected' : ''} aria-pressed={value === kind} onClick={() => setKind(value)}><Icon name={value === 'candidates' ? 'candidates' : 'evidence'} /><span><strong>{value === 'candidates' ? t('Candidate list', '候选表') : t('Measurements & evidence', '测量与证据表')}</strong><small>{value === 'candidates' ? t('One row per drug, carrier or other candidate', '每行一个药物、载体或其他候选') : t('One row per candidate × property observation', '每行一条候选 × 性质观测')}</small></span></button>)}</div>
    <div className="csv-help"><p>{kind === 'candidates' ? t('Required: a unique candidate ID. Names and identifiers are optional. Extra columns stay with the candidate as metadata.', '必需：唯一候选编号。名称和结构编号可选，额外列作为候选元数据保留。') : t('Required: candidate ID, property, value and evidence basis. Numeric measurements need a unit. Conditions and source keep each observation interpretable.', '必需：候选编号、性质、值和证据依据。数值测量需提供单位，实验条件和来源用于解释观测。')}</p><a className="button" href={api.uploadTemplateUrl(kind)} download><Icon name="download" size={14} />{t('Download CSV template', '下载 CSV 模板')}</a></div>
    {needsLibrary && <p className="notice">{t('Choose or import a candidate library first, so measurement IDs can be checked against it.', '请先选择或导入候选库，以便核对测量表中的候选编号。')}</p>}
    {kind === 'measurements' && <p className="field-note">{t('For the built-in drug library, use the exact InChIKey as candidate ID. For uploaded libraries, use the ID in your candidate CSV. Values and algorithms are never matched by similar names.', '内置药物库使用精确 InChIKey 作为候选编号，上传候选库使用候选 CSV 中的编号。不会按相似名称匹配数值或算法。')}</p>}
    <div className="csv-step-head"><span className="csv-step-number">2</span><div><h3>{t('Select a file and map its columns', '选择文件并对应列')}</h3><p>{t('UTF-8 CSV with a header row. The preview is checked before data can be used.', '使用带表头的 UTF-8 CSV。数据须先通过预览校验才能使用。')}</p></div></div>
    <label className="csv-file-label"><Icon name="upload" size={20} /><span>{busy === 'preview' ? t('Reading and checking your CSV…', '正在读取并校验 CSV…') : preview?.filename || t('Choose a CSV file', '选择 CSV 文件')}</span><input ref={fileInput} type="file" accept=".csv,text/csv" disabled={!!busy || needsLibrary} onChange={event => { const file = event.target.files?.[0]; if (!file) return; if (file.size > MAX_CSV_BYTES) { setError(t('Use a CSV of up to 8 MiB.', '请使用不超过 8 MiB 的 CSV。')); return; } void inspect(() => file.text(), file.name); }} /></label>
    <details className="csv-paste"><summary>{t('Paste CSV instead', '改为粘贴 CSV')}</summary><label>{t('File name for this data', '此数据的文件名称')}<input value={pasteName} onChange={event => setPasteName(event.target.value)} placeholder={`${kind}.csv`} disabled={!!busy} /></label><label>{t('CSV content', 'CSV 内容')}<textarea rows={7} value={pasted} onChange={event => setPasted(event.target.value)} placeholder={kind === 'candidates' ? 'candidate_id,name' : 'candidate_id,property,value,unit,basis,conditions,source,summary'} disabled={!!busy} spellCheck={false} /></label><button type="button" disabled={!!busy || needsLibrary || !pasted.trim()} onClick={() => void inspect(() => Promise.resolve(pasted), pasteName.trim() || `${kind}.csv`)}>{busy === 'preview' ? t('Checking…', '校验中…') : t('Preview pasted CSV', '预览粘贴的 CSV')}</button></details>
    {preview && <><div className="csv-mapping">{preview.field_schema.map(field => <label key={field.key}>{uploadFieldLabel(field.key, t)} {field.required && <span className="required-marker">*</span>}<select disabled={!!busy} value={mapping[field.key] || ''} onChange={event => { setMapping(previous => ({ ...previous, [field.key]: event.target.value })); setDirty(true); setSaved(undefined); }}><option value="">{field.required ? t('Choose a column', '选择对应列') : t('Not provided', '未提供')}</option>{preview.headers.map(header => <option key={header} value={header}>{header}</option>)}</select>{field.description && <small>{field.description}</small>}</label>)}</div><div className="row spread csv-validation-actions"><span className="subtle">{dirty ? t('Column mapping changed. Validate it to refresh the preview.', '列对应关系已修改，请校验后更新预览。') : t('Preview reflects the current column mapping.', '预览对应当前列映射。')}</span><button type="button" disabled={!!busy} onClick={() => void validate()}>{busy === 'mapping' ? t('Checking…', '校验中…') : t('Validate mapping', '校验列映射')}</button></div>
      <div className="csv-step-head"><span className="csv-step-number">3</span><div><h3>{t('Review and use this data', '核对并使用数据')}</h3><p>{preview.row_count.toLocaleString()} {t('rows', '行')} · {preview.valid_rows.toLocaleString()} {t('valid', '行有效')} · {t('Preview of up to 10 rows', '最多预览 10 行')}</p></div></div>
      {!!preview.errors?.length && <div className="csv-issues" role="alert"><strong>{t('Resolve these issues before using the file', '请先解决以下问题')} · {preview.error_count ?? preview.errors.length}</strong>{(preview.error_count ?? 0) > preview.errors.length && <p>{t('The first issues are shown below.', '下方显示前一部分问题。')}</p>}<ul>{preview.errors.map((issue, index) => <li key={index}>{issueText(issue)}</li>)}</ul></div>}
      {!!preview.warnings?.length && <details className="csv-warnings"><summary>{preview.warnings.length} {t('notes about this file', '条数据说明')}</summary><ul>{preview.warnings.map((issue, index) => <li key={index}>{typeof issue === 'string' ? uploadMessage(issue, t) : issueText(issue)}</li>)}</ul></details>}
      {columns.length > 0 && <div className={`table-scroll csv-preview ${dirty ? 'stale' : ''}`}><table><thead><tr><th>{t('Row', '行')}</th>{columns.map(field => <th key={field.key}>{uploadFieldLabel(field.key, t)}<small>{preview.mapping[field.key]}</small></th>)}</tr></thead><tbody>{preview.preview_rows.map(row => <tr key={row.row_number}><td className="numeric">{row.row_number}</td>{columns.map(field => <td key={field.key}>{valueText(row.values[field.key])}</td>)}</tr>)}</tbody></table></div>}
      {saved ? <p className="csv-ready" role="status"><Icon name="check" size={17} />{saved.label} · {saved.row_count.toLocaleString()} {t('rows ready. Research has not started.', '行已就绪，研究尚未开始。')}</p> : <div className="csv-commit"><p>{t('Using the file saves its validated data. Research starts only when you choose Start research.', '使用文件会保存已校验的数据，点击“开始研究”后才会启动研究。')}</p><button type="button" className="primary" disabled={!!busy || dirty || !preview.can_commit || needsLibrary} onClick={() => void commit()}>{busy === 'commit' ? t('Saving data…', '正在保存数据…') : kind === 'candidates' ? t('Use this candidate library', '使用此候选库') : t('Use these measurements', '使用这些测量')}</button></div>}<Audit data={{ upload_id: preview.upload_id, mapping, errors: preview.errors, warnings: preview.warnings }} title={t('Import record', '导入记录')} /></>}
    {error && <p className="inline-error" role="alert">{error}</p>}
  </section>;
}
