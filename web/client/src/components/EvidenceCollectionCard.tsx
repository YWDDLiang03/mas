import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { EvidenceCollection, EvidenceSource } from '../api/types';
import { useResource } from '../hooks/useResource';
import { useI18n } from '../i18n';
import { Audit, ErrorNotice } from './UI';
import './EvidenceSources.css';

export function EvidenceCollectionCard({ taskId, initial, editable, onResolved, onSaved, bound = false }: {
  taskId: string; initial?: EvidenceSource; editable?: boolean; bound?: boolean;
  onResolved?: (collection: EvidenceCollection) => void; onSaved?: () => void;
}) {
  const { t, language } = useI18n();
  const resource = useResource<EvidenceCollection>(taskId ? `collection/${taskId}` : null, signal => api.evidenceCollection(taskId, signal));
  const [saved, setSaved] = useState<EvidenceCollection>();
  const [editing, setEditing] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [label, setLabel] = useState(''), [description, setDescription] = useState(''), [topics, setTopics] = useState('');
  const callback = useRef(onResolved); callback.current = onResolved;
  useEffect(() => { setSaved(undefined); setEditing(false); setError(''); }, [taskId]);
  const data = saved?.task_id === taskId ? saved : resource.data;
  useEffect(() => { if (data) callback.current?.(data); }, [data]);
  if (!taskId) return null;
  const display = data || initial;
  const canEdit = editable ?? data?.display_editable ?? false;
  const cutoff = display?.cutoff;
  const cutoffDate = cutoff ? new Date(cutoff.length === 10 ? cutoff + 'T00:00:00' : cutoff) : null;
  const cutoffLabel = cutoffDate && !Number.isNaN(cutoffDate.valueOf()) ? cutoffDate.toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : cutoff;
  function edit() { setLabel(display?.label || ''); setDescription(display?.description || ''); setTopics(display?.topics?.join('\n') || ''); setEditing(true); setError(''); }
  async function save() {
    if (busy) return;
    setBusy(true); setError('');
    try { const result = await api.saveEvidenceCollection(taskId, { label, description, topics: topics.split(/\n|,/).map(value => value.trim()).filter(Boolean) }); setSaved(result); setEditing(false); onSaved?.(); }
    catch (issue) { setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { setBusy(false); }
  }
  return <section className="collection-card"><header><div><span>{bound ? t('Bound evidence collection', '已绑定的证据集合') : t('Evidence collection', '证据集合')}</span><h3>{display?.label || t('Loading the saved collection…', '正在读取已保存集合…')}</h3></div>{canEdit && data && !editing && <button type="button" onClick={edit}>{t('Edit display details', '编辑显示信息')}</button>}</header>
    {bound && <p className="collection-identity-note">{t('This is the saved source selected for this research. Its evidence identity is preserved.', '这是本研究已选择的保存来源，证据身份保持不变。')}</p>}
    {display?.description && <p>{display.description}</p>}
    <div className="collection-facts"><span><strong>{display?.source_count?.toLocaleString() ?? '—'}</strong> {t('sources', '个来源')}</span><span><strong>{display?.claim_count?.toLocaleString() ?? '—'}</strong> {t('saved findings', '条保存发现')}</span><span>{t('Evidence cutoff', '证据截止')} <strong>{cutoffLabel || t('Not recorded', '未记录')}</strong></span></div>
    {display?.topics?.length ? <div className="collection-topics"><span>{t('Topics', '主题')}</span>{display.topics.map((topic, index) => <span key={index}>{topic}</span>)}</div> : null}
    {data?.counts_basis && <p className="collection-basis">{data.counts_basis === 'pinned_fact_manifest' ? t('Counts describe the saved input collection.', '数量来自已固定的输入集合。') : t('Counts describe admitted evidence saved with this research.', '数量来自本研究已接纳并保存的证据。')}{data.topics_basis === 'task_targets' && data.display_origin !== 'ui_metadata' && ` ${t('Topics follow the recorded task targets.', '主题来自已记录的任务靶点。')}`}</p>}
    {editing && <div className="collection-editor" onKeyDown={event => { if (event.key === 'Enter' && (event.target as HTMLElement).tagName === 'INPUT') { event.preventDefault(); void save(); } }}><label>{t('Collection name', '集合名称')}<input value={label} maxLength={80} onChange={event => setLabel(event.target.value)} /></label><label>{t('Short description', '简短介绍')}<textarea rows={3} value={description} maxLength={600} onChange={event => setDescription(event.target.value)} /></label><label>{t('Topics · one per line', '主题 · 每行一个')}<textarea rows={2} value={topics} onChange={event => setTopics(event.target.value)} /></label><p>{t('These display details do not change the research objective, evidence, cutoff or results.', '这些显示信息不改变研究目标、证据、截止时间或结果。')}</p><div className="row"><button type="button" className="primary" disabled={busy || !label.trim()} onClick={() => void save()}>{busy ? t('Saving…', '保存中…') : t('Save display details', '保存显示信息')}</button><button type="button" disabled={busy} onClick={() => setEditing(false)}>{t('Cancel', '取消')}</button></div></div>}
    <ErrorNotice message={error || resource.error} retry={resource.refresh} />{data && <Audit data={data} title={t('Collection identity & source record', '集合身份与来源记录')} />}
  </section>;
}
