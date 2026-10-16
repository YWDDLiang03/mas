import { useCallback, useEffect, useRef, useState, type SetStateAction } from 'react';

type ViewState = Record<string, string | number | boolean>;
type DataView = 'criteria' | 'candidates' | 'evidence';

export function viewStateKey(task: string, view: DataView, scope = '') {
  return `mas.view-state.v1:${encodeURIComponent(task)}:${view}${scope ? ':' + encodeURIComponent(scope) : ''}`;
}

export function restoreViewState<T extends ViewState>(raw: string | null, defaults: T): T {
  const restored = { ...defaults };
  try {
    const saved: unknown = raw ? JSON.parse(raw) : null;
    if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return restored;
    for (const key of Object.keys(defaults)) {
      const value = (saved as Record<string, unknown>)[key];
      if (typeof value !== typeof defaults[key]) continue;
      if (typeof value === 'number' && (!Number.isInteger(value) || value < 1)) continue;
      (restored as Record<string, unknown>)[key] = value;
    }
  } catch { /* A missing or obsolete preference never prevents opening research. */ }
  return restored;
}

function readState<T extends ViewState>(key: string, defaults: T): T {
  try { return restoreViewState(localStorage.getItem(key), defaults); }
  catch { return { ...defaults }; }
}

/** Only view filters and selection are stored; scientific records stay on the service. */
export function useViewState<T extends ViewState>(task: string, view: DataView, defaults: T, scope = '') {
  const key = viewStateKey(task, view, scope);
  const defaultRef = useRef(defaults); defaultRef.current = defaults;
  const [record, setRecord] = useState(() => ({ key, value: readState(key, defaults) }));
  useEffect(() => {
    if (record.key !== key) setRecord({ key, value: readState(key, defaultRef.current) });
  }, [key, record.key]);
  useEffect(() => {
    if (record.key !== key) return;
    try { localStorage.setItem(key, JSON.stringify(record.value)); } catch { /* Filtering still works if preference storage is unavailable. */ }
  }, [key, record]);
  const update = useCallback((next: SetStateAction<T>) => {
    setRecord(previous => {
      const current = previous.key === key ? previous.value : readState(key, defaultRef.current);
      return { key, value: typeof next === 'function' ? next(current) : next };
    });
  }, [key]);
  return [record.key === key ? record.value : readState(key, defaultRef.current), update] as const;
}
