import { useCallback, useEffect, useRef, useState } from 'react';

export function useResource<T>(key: string | null, fetcher: (signal: AbortSignal) => Promise<T>, revision = 0) {
  const fetchRef = useRef(fetcher); fetchRef.current = fetcher;
  const [generation, setGeneration] = useState(0);
  const [record, setRecord] = useState<{ key: string | null; data?: T; error?: string; loading: boolean }>({ key, loading: !!key });
  useEffect(() => {
    if (!key) { setRecord({ key: null, loading: false }); return; }
    const controller = new AbortController();
    setRecord(previous => ({ key, data: previous.key === key ? previous.data : undefined, loading: true }));
    fetchRef.current(controller.signal).then(
      data => { if (!controller.signal.aborted) setRecord({ key, data, loading: false }); },
      error => { if (!controller.signal.aborted) setRecord(previous => ({ key, data: previous.key === key ? previous.data : undefined, error: error instanceof Error ? error.message : String(error), loading: false })); },
    );
    return () => controller.abort();
  }, [key, generation, revision]);
  const refresh = useCallback(() => setGeneration(value => value + 1), []);
  return { ...(record.key === key ? record : { key, loading: !!key }), refresh };
}
export function useDebounced(value: string, delay = 250) {
  const [settled, setSettled] = useState(value);
  useEffect(() => { const timer = setTimeout(() => setSettled(value), delay); return () => clearTimeout(timer); }, [value, delay]);
  return settled;
}
