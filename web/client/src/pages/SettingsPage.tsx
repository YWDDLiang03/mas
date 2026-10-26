import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Primitive, SettingField, Settings } from '../api/types';
import { useI18n } from '../i18n';
import { useResource } from '../hooks/useResource';
import { Audit, Badge, ErrorNotice, Loading, Panel } from '../components/UI';

function secret(field: SettingField) { return field.secret || /api.?key|password|secret|token/i.test(field.key); }
export function SettingsPage({ enabled, onSaved }: { enabled: boolean; onSaved: () => void }) {
  const { t } = useI18n();
  const resource = useResource<Settings>('settings', signal => api.settings(signal));
  const [values, setValues] = useState<Record<string, Primitive>>({}), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  useEffect(() => { if (resource.data) setValues(Object.fromEntries(resource.data.fields.filter(field => !secret(field)).map(field => [field.key, field.value]))); }, [resource.data]);
  const labels: Record<string, [string, string]> = {
    'search.volume': ['Literature workload', '文献阅读量'], 'textbook.volume': ['Textbook workload', '教材阅读量'], 'assess.workers': ['Concurrent candidates', '并发评估候选数'],
    'search.breadth': ['Search breadth', '搜索广度'], 'search.depth': ['Search rounds', '搜索轮数'], 'read.max_papers_full_read': ['Full texts per topic', '每主题全文数'],
    'budget.usd_max': ['Cost cap (USD)', '费用上限（美元）'], 'budget.on_exhaust': ['When the budget is exhausted', '预算耗尽时'],
    'interaction.mode': ['Interaction mode', '交互方式'], 'rank.coverage_floor': ['Ranking coverage floor', '排名覆盖下限'], 'rank.mandated_coverage_floor': ['Required-criteria eligibility floor', '必需标准资格下限'],
  };
  const choices: Record<string, [string, string]> = {
    low: ['Light', '少量'], mid: ['Medium', '适中'], high: ['Extensive', '较多'], xhigh: ['Very extensive', '大量'],
    finalize_partial: ['Stop and keep partial results', '停止并保留部分结果'], warn_continue: ['Warn and continue', '提示后继续'], ask: ['Ask before continuing', '询问后继续'], abort: ['Stop the run', '停止运行'],
    autonomous: ['Run automatically', '自动运行'], checkpoint: ['Pause at checkpoints', '在检查点暂停'], interactive: ['Interactive guidance', '交互引导'],
  };
  if (!resource.data) return resource.error ? <ErrorNotice message={resource.error} retry={resource.refresh} /> : <Loading />;
  const primaryKeys = new Set(['search.volume', 'textbook.volume', 'assess.workers', 'budget.usd_max']);
  const renderField = (field: SettingField) => {
    const label = labels[field.key] ? t(...labels[field.key]) : field.label;
    const disabled = !enabled || field.editable === false;
    return <label key={field.key}>{label}{secret(field) ? <span className="credential-status"><Badge state={field.configured ? 'completed' : 'unknown'} label={field.configured ? t('Configured', '已配置') : t('Not configured', '未配置')} /></span> : field.choices?.length ? <select value={String(values[field.key] ?? '')} disabled={disabled} onChange={event => setValues(previous => ({ ...previous, [field.key]: event.target.value }))}>{field.choices.map(choice => { const value = typeof choice === 'string' ? choice : choice.value; const display = choices[value] ? t(...choices[value]) : typeof choice === 'string' ? choice : choice.label || choice.value; return <option value={value} key={value}>{display}</option>; })}</select> : ['boolean', 'bool'].includes(field.kind) ? <input type="checkbox" checked={values[field.key] === true} disabled={disabled} onChange={event => setValues(previous => ({ ...previous, [field.key]: event.target.checked }))} /> : <input type={['int', 'float', 'integer', 'number'].includes(field.kind) ? 'number' : 'text'} value={String(values[field.key] ?? '')} min={field.minimum} max={field.maximum} step={field.kind === 'float' ? 'any' : 1} disabled={disabled} onChange={event => setValues(previous => ({ ...previous, [field.key]: ['int', 'float', 'integer', 'number'].includes(field.kind) ? Number(event.target.value) : event.target.value }))} />}</label>;
  
  };
  return <><div className="page-heading"><div><div className="eyebrow">{t('Workspace settings', '工作区设置')}</div><h1>{t('Research settings', '研究设置')}</h1><p>{t('Changes apply to future work. Saved evaluations retain their original configuration.', '更改用于后续工作。已保存评估保留原来的配置。')}</p></div><Badge label={resource.data.preset || 'standard'} /></div><Panel title={t('Research settings', '研究设置')} caption={t('Choose reading effort, parallel work and a cost limit.', '设置阅读量、并发任务与费用上限。')}><form onSubmit={async event => { event.preventDefault(); if (busy) return; setBusy(true); setError(''); setMessage(''); try { await api.saveSettings(values); setMessage(t('Settings saved.', '设置已保存。')); resource.refresh(); onSaved(); } catch (issue) { setError(issue instanceof Error ? issue.message : String(issue)); } finally { setBusy(false); } }}><div className="settings-grid">{resource.data.fields.filter(field => primaryKeys.has(field.key)).map(renderField)}</div><details className="form-details"><summary>{t('Advanced settings', '高级设置')}</summary><div className="settings-grid">{resource.data.fields.filter(field => !primaryKeys.has(field.key)).map(renderField)}</div></details><div className="form-actions"><button className="primary" disabled={!enabled || busy}>{busy ? t('Saving…', '保存中…') : t('Save settings', '保存设置')}</button></div>{!enabled && <p className="subtle">{t('Settings are read-only in this workspace.', '此工作区的设置当前只读。')}</p>}{message && <p className="form-feedback" role="status">{message}</p>}{error && <p className="inline-error" role="alert">{error}</p>}</form></Panel><Audit data={{ ...resource.data, fields: resource.data.fields.map(field => secret(field) ? { ...field, value: undefined } : field) }} title={t('Configuration details', '配置详情')} /></>;
}
