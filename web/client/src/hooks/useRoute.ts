import { useCallback, useEffect, useRef, useState } from 'react';

export type View = 'overview' | 'criteria' | 'candidates' | 'evidence' | 'settings';
export interface Route { view: View; task: string; item: string; snapshot: string; criterion: string; candidate: string; source: string }
const views = new Set(['overview', 'criteria', 'candidates', 'evidence', 'settings']);
function readRoute(): Route {
  const params = new URLSearchParams(location.search);
  return { view: views.has(params.get('view') || '') ? params.get('view') as View : 'overview', task: params.get('task') || '', item: params.get('item') || '', snapshot: params.get('snapshot') || '', criterion: params.get('criterion') || '', candidate: params.get('candidate') || '', source: params.get('source') || '' };
}
export function routeHref(route: Partial<Route>, language: string) {
  const params = new URLSearchParams({ view: route.view || 'overview', lang: language });
  for (const key of ['task', 'item', 'snapshot', 'criterion', 'candidate', 'source'] as const) if (route[key]) params.set(key, route[key]!);
  return `${location.pathname}?${params}`;
}
export function useRoute() {
  const [route, setRoute] = useState<Route>(readRoute);
  const current = useRef(route);
  useEffect(() => { const pop = () => { const next = readRoute(); current.current = next; setRoute(next); }; addEventListener('popstate', pop); return () => removeEventListener('popstate', pop); }, []);
  const navigate = useCallback((change: Partial<Route>, replace = false) => {
    const next = { ...current.current, ...change };
    const url = new URL(location.href);
    url.searchParams.set('view', next.view);
    for (const key of ['task', 'item', 'snapshot', 'criterion', 'candidate', 'source'] as const) { if (next[key]) url.searchParams.set(key, next[key]); else url.searchParams.delete(key); }
    if (replace) history.replaceState(history.state, '', url); else history.pushState(null, '', url);
    current.current = next;
    setRoute(next);
  }, []);
  return { route, navigate };
}
