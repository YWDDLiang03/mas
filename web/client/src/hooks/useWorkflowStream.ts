import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { StreamEvent, Workflow } from '../api/types';

export function useWorkflowStream(initial: Workflow[] | undefined, enabled: boolean) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [connection, setConnection] = useState<'connecting' | 'live' | 'polling'>('connecting');
  const [revision, setRevision] = useState(0);
  const cursor = useRef<number>();
  const live = useRef(false);
  const upsert = useCallback((workflow: Workflow) => {
    setWorkflows(previous => {
      const old = previous.find(row => row.workflow_id === workflow.workflow_id);
      if (old && old.updated_at > workflow.updated_at) return previous;
      // A replayed event at the same timestamp may predate newly derived API
      // fields. Keep those fields while applying the event's recorded values.
      return [{ ...old, ...workflow }, ...previous.filter(row => row.workflow_id !== workflow.workflow_id)].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    });
  }, []);
  useEffect(() => { if (initial) initial.forEach(upsert); }, [initial, upsert]);
  useEffect(() => {
    if (!enabled) return;
    let stopped = false, polling = false;
    const source = new EventSource(api.eventsUrl(cursor.current));
    source.onopen = () => { live.current = true; setConnection('live'); };
    const receive = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent;
        if (Number.isFinite(data.cursor)) cursor.current = data.cursor;
        if (data.workflow) upsert(data.workflow);
        if (data.kind !== 'heartbeat') setRevision(value => value + 1);
      } catch { /* An incomplete event is retried through the read endpoint. */ }
    };
    source.onmessage = receive;
    source.addEventListener('workflow', receive as EventListener);
    source.addEventListener('projection', receive as EventListener);
    source.onerror = () => { live.current = false; setConnection('polling'); };
    const interval = setInterval(async () => {
      if (live.current || polling) return;
      polling = true;
      try {
        const data = await api.workflows();
        if (!stopped) { data.items.forEach(upsert); setRevision(value => value + 1); }
      } catch { /* The persistent connection indicator stays visible while unavailable. */ }
      finally { polling = false; }
    }, 2000);
    return () => { stopped = true; source.close(); clearInterval(interval); live.current = false; };
  }, [enabled, upsert]);
  return { workflows, upsert, connection, revision };
}
