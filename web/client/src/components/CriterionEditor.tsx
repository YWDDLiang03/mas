import { useState } from 'react';
import { api } from '../api/client';
import type { CriterionDetail, RevisionResult } from '../api/types';
import { stateText, useI18n } from '../i18n';
import { Audit } from './UI';

const comparators = ['>=', '<=', '>', '<', '=='] as const;
interface NumericCutoff { comparator: string; value: number; unit?: string }
export function thresholdModel(detail: CriterionDetail) {
  const cutoff = detail.cutoff && typeof detail.cutoff === 'object' ? detail.cutoff as Record<string, unknown> : null;
  const rawRule = detail.raw?.rule && typeof detail.raw.rule === 'object' ? detail.raw.rule as Record<string, unknown> : detail.raw;
  const predicate = rawRule?.predicate_form;
  const numeric = !!cutoff && typeof cutoff.value === 'number' && Number.isFinite(cutoff.value) && comparators.some(value => value === cutoff.comparator);
  const complex = (detail.cutoff != null && !numeric) || (typeof predicate === 'string' && !['threshold', 'ordering'].includes(predicate));
  return { numeric, canEdit: !complex && (numeric || !!detail.unit), cutoff: numeric ? cutoff as unknown as NumericCutoff : null };
}

export function CriterionEditor({ task, detail, onSaved }: { task: string; detail: CriterionDetail; onSaved: (value: RevisionResult) => void }) {
  const { t } = useI18n();
  const threshold = thresholdModel(detail);
  const [name, setName] = useState(detail.name), [definition, setDefinition] = useState(detail.definition || ''), [reason, setReason] = useState('');
  const [role, setRole] = useState(detail.role), [direction, setDirection] = useState(detail.direction || '');
  const [enabled, setEnabled] = useState(threshold.numeric), [comparator, setComparator] = useState(threshold.cutoff?.comparator || '>='), [value, setValue] = useState(threshold.cutoff ? String(threshold.cutoff.value) : ''), [unit, setUnit] = useState(threshold.cutoff?.unit || detail.unit || '');
  const [thresholdDirty, setThresholdDirty] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const directions: [string, string, string][] = [
    ['higher_better', 'Higher is better', '越高越好'], ['lower_better', 'Lower is better', '越低越好'],
    ['within_range', 'Within a range', '在范围内'], ['target_value', 'Near a target value', '接近目标值'],
    ['non_directional', 'No ordering preference', '无排序偏好'], ['undetermined', 'Not determined', '尚未确定'],
  ];
  return <form className="revision-form" onSubmit={async event => {
    event.preventDefault(); if (busy) return; setBusy(true); setError('');
    const changes: { name?: string; definition?: string; role?: string; direction?: string; cutoff?: unknown } = {};
    if (name !== detail.name) changes.name = name;
    if (definition !== (detail.definition || '')) changes.definition = definition;
    if (role !== detail.role) changes.role = role;
    if (direction && direction !== detail.direction) changes.direction = direction;
    if (threshold.canEdit && thresholdDirty) {
      const cutoff = enabled ? { ...(detail.cutoff && typeof detail.cutoff === 'object' ? detail.cutoff : {}), comparator, value: Number(value), ...(unit ? { unit } : {}) } : null;
      if (JSON.stringify(cutoff) !== JSON.stringify(detail.cutoff ?? null)) changes.cutoff = cutoff;
    }
    try {
      if (!Object.keys(changes).length) { setError(t('Change a criterion field before saving a new version.', '请先修改标准内容，再保存新版本。')); return; }
      onSaved(await api.editCriterion(task, detail.criterion_id, changes, reason));
    } catch (issue) { setError(issue instanceof Error ? issue.message : String(issue)); }
    finally { setBusy(false); }
  }}>
    <p className="notice">{t('Save a new version. Changed rules receive a new review; earlier criteria and frozen results stay available.', '保存为新版本。修改后的规则会重新复核，早期标准与已冻结结果继续保留。')}</p>
    <label>{t('Name', '名称')}<input value={name} onChange={event => setName(event.target.value)} required /></label>
    <label>{t('Definition', '定义')}<textarea value={definition} rows={4} onChange={event => setDefinition(event.target.value)} /></label>
    <div className="form-columns"><label>{t('Role', '用途')}<select value={role} onChange={event => setRole(event.target.value)}>{['hard_exclusion', 'preference', 'exploratory_consideration'].map(value => <option key={value} value={value}>{stateText(value, t)}</option>)}</select></label><label>{t('Direction', '方向')}<select value={direction} onChange={event => setDirection(event.target.value)}><option value="">{t('Keep the existing direction', '保留原方向')}</option>{directions.map(([value, en, zh]) => <option key={value} value={value}>{t(en, zh)}</option>)}</select></label></div>
    {threshold.canEdit ? <fieldset className="threshold-fields"><legend>{t('Numeric threshold', '数值阈值')}</legend><label className="checkbox-label"><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); setThresholdDirty(true); }} />{t('Use a numeric threshold', '使用数值阈值')}</label>{enabled && <div className="threshold-controls"><label>{t('Comparison', '比较方式')}<select value={comparator} onChange={event => { setComparator(event.target.value); setThresholdDirty(true); }}>{comparators.map(value => <option key={value} value={value}>{value}</option>)}</select></label><label>{t('Value', '数值')}<input type="number" step="any" value={value} onChange={event => { setValue(event.target.value); setThresholdDirty(true); }} required /></label><label>{t('Unit', '单位')}<input value={unit} onChange={event => { setUnit(event.target.value); setThresholdDirty(true); }} required={!!detail.unit} /></label></div>}</fieldset> : <div className="notice"><p>{t('This criterion uses a complex or non-numeric condition. Its original condition will be preserved.', '此标准使用复杂或非数值条件，将保留原条件。')}</p><Audit data={detail.cutoff} title={t('Existing condition', '原条件')} /></div>}
    <label>{t('Reason for this change', '修改理由')}<textarea value={reason} rows={2} onChange={event => setReason(event.target.value)} required /></label>
    <button className="primary" disabled={busy || !name.trim() || !reason.trim() || (threshold.canEdit && enabled && (!value.trim() || !Number.isFinite(Number(value))))}>{busy ? t('Saving…', '保存中…') : t('Save new version', '保存新版本')}</button>
    {error && <p className="inline-error" role="alert">{error}</p>}
  </form>;
}
