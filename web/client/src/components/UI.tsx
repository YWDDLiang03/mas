import { useEffect, useRef, type ReactNode } from 'react';
import type { Page } from '../api/types';
import { stateText, useI18n } from '../i18n';

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    overview: <><path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" /></>,
    criteria: <><path d="M8 4h12v17H4V4h4M8 2h8v5H8zM8 12h8M8 16h6" /></>,
    candidates: <><path d="M4 20v-7h4v7m4 0V4h4v16m4 0v-10h3v10M2 20h22" /></>,
    evidence: <><path d="M12 5C8 2 4 3 2 4v15c4-2 7-1 10 1 3-2 6-3 10-1V4c-4-2-7-1-10 1Zm0 0v15" /></>,
    settings: <><path d="M3 7h18M3 17h18M8 3v8M16 13v8" /></>,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />, close: <path d="m6 6 12 12M6 18 18 6" />,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
    plus: <path d="M12 4v16M4 12h16" />, download: <path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" />,
    upload: <path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5" />,
    pause: <path d="M8 5v14M16 5v14" />, play: <path d="m8 4 12 8-12 8z" />, stop: <path d="M5 5h14v14H5z" />,
    refresh: <path d="M20 6v5h-5M4 18v-5h5M5 8a8 8 0 0 1 13-3l2 3M4 16l2 3a8 8 0 0 0 13-3" />,
    check: <path d="m5 12 4 4L20 5" />, chevron: <path d="m9 5 7 7-7 7" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.overview}</svg>;
}
export function Badge({ state, label }: { state?: string; label?: string }) {
  const { t } = useI18n();
  const tone = ['completed', 'qualified', 'pass', 'confirmed', 'retained', 'measured'].includes(state || '') ? 'good' : ['failed', 'rejected', 'fail'].includes(state || '') ? 'bad' : ['running', 'pending', 'paused', 'waiting_input', 'proposed', 'unresolved'].includes(state || '') ? 'warn' : 'neutral';
  return <span className={`badge ${tone}`}>{label || stateText(state, t)}</span>;
}
export function Panel({ title, caption, action, children, className = '' }: { title?: ReactNode; caption?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{(title || action) && <header className="panel-heading"><div>{title && <h2>{title}</h2>}{caption && <p>{caption}</p>}</div>{action}</header>}{children}</section>;
}
export function Empty({ title, children }: { title: ReactNode; children?: ReactNode }) { return <div className="empty"><span className="empty-mark"><Icon name="evidence" size={24} /></span><h3>{title}</h3>{children && <div>{children}</div>}</div>; }
export function Loading() { const { t } = useI18n(); return <div className="loading" role="status"><span className="spinner" />{t('Reading research records…', '正在读取研究记录…')}</div>; }
export function ErrorNotice({ message, retry }: { message?: string; retry?: () => void }) {
  const { t } = useI18n();
  return message ? <div className="notice danger" role="alert"><div><strong>{t('Could not load this view', '此页面暂时无法读取')}</strong><p>{message}</p></div>{retry && <button onClick={retry}>{t('Try again', '重试')}</button>}</div> : null;
}
export function Audit({ data, title }: { data: unknown; title?: string }) { const { t } = useI18n(); return <details className="audit"><summary>{title || t('Record details', '记录详情')}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>; }
export function Search({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="search"><Icon name="search" /><input type="search" value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} aria-label={placeholder} /></label>; }
export function Pagination({ page, onChange }: { page: Pick<Page<unknown>, 'page' | 'page_size' | 'total' | 'has_more'>; onChange: (value: number) => void }) {
  const { t } = useI18n();
  const first = page.total ? (page.page - 1) * page.page_size + 1 : 0;
  return <div className="pagination"><span>{first}–{Math.min(page.page * page.page_size, page.total)} {t('of', '/')} {page.total}</span><div><button disabled={page.page <= 1} onClick={() => onChange(page.page - 1)}>{t('Previous', '上一页')}</button><span>{page.page} / {Math.max(1, Math.ceil(page.total / page.page_size))}</span><button disabled={!page.has_more} onClick={() => onChange(page.page + 1)}>{t('Next', '下一页')}</button></div></div>;
}
export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const { t } = useI18n();
  const element = useRef<HTMLElement>(null);
  const closeAction = useRef(onClose); closeAction.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element.current?.querySelector<HTMLButtonElement>('button')?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeAction.current();
      if (event.key !== 'Tab') return;
      const focusable = [...(element.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex="0"]') || [])].filter(item => item.getClientRects().length > 0);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', close);
    return () => { document.removeEventListener('keydown', close); document.body.style.overflow = previousOverflow; previous?.focus(); };
  }, []);
  return <div className="drawer-backdrop" onClick={event => { if (event.target === event.currentTarget) onClose(); }}><section ref={element} className="drawer" role="dialog" aria-modal="true" aria-label={title}><header className="drawer-heading"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label={t('Close details', '关闭详情')}><Icon name="close" /></button></header><div className="drawer-body">{children}</div></section></div>;
}
export function valueText(value: unknown): string { if (value == null) return '—'; if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(7))); if (typeof value === 'object') return JSON.stringify(value); return String(value); }
export function percent(value: number | null | undefined) { return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—'; }
export function dateText(value?: string | null, language: 'en' | 'zh' = 'en') { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
export function safeUrl(value?: string) { if (!value) return undefined; try { const url = new URL(value, location.origin); return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined; } catch { return undefined; } }
