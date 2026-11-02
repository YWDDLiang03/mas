import type { CdesCollection } from '../api/types';
import { useI18n } from '../i18n';
import './CdesOption.css';

export function CdesOption({ checked, onChange, source, onSource, collections = [], disabled = false, defaultScope = false }: {
  checked: boolean; onChange: (checked: boolean) => void; source?: string | null;
  onSource?: (source: string) => void; collections?: CdesCollection[]; disabled?: boolean; defaultScope?: boolean;
}) {
  const { t } = useI18n();
  const selected = collections.find(item => item.id === source);
  return <section className="cdes-option" aria-label={t('Optional CDES module', '可选 CDES 模块')}>
    <div className="cdes-option-heading"><div><span className="cdes-optional-label">{t('Optional analysis', '可选分析')}</span><h3>{t('CDES target profiles', 'CDES 靶点分析')}</h3><p>{defaultScope ? t('Default for new drug studies. Each study can choose its own setting.', '新建药物研究的默认设置，每项研究可单独选择。') : t('Add structure-based interaction profiles for the targets in this study.', '为本研究的靶点补充结构相互作用分析。')}</p></div><button type="button" role="switch" aria-label={t('Use CDES', '使用 CDES')} aria-checked={checked} disabled={disabled} className={`module-switch ${checked ? 'on' : ''}`} onClick={() => onChange(!checked)}><span />{checked ? t('On', '开启') : t('Off', '关闭')}</button></div>
    {checked && <div className="cdes-source"><p>{t('Current source: saved CDES results.', '当前来源为已保存的 CDES 结果。')}</p>{onSource && <label>{t('Prediction collection', '预测集合')}<select value={source || ''} onChange={event => onSource(event.target.value)} disabled={disabled}><option value="">{t('Choose a collection', '选择结果集合')}</option>{collections.map(item => <option key={item.id} value={item.id}>{item.label} · {item.candidate_count.toLocaleString()}</option>)}</select></label>}{selected && <div className="cdes-coverage"><strong>{t('Available targets', '已有结果的靶点')}</strong><span>{selected.targets.join(' · ')}</span></div>}{collections.length === 0 && <p className="field-note">{t('Add a saved prediction collection before using CDES in a new study.', '在新研究中启用 CDES 前，需先添加预测结果集合。')}</p>}</div>}
  </section>;
}
