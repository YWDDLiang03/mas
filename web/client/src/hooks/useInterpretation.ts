import { useSyncExternalStore } from 'react';
import { api } from '../api/client';
import type { InterpretationPreparation } from '../api/types';

interface PreparationState { pending: boolean; response?: InterpretationPreparation; error?: string }
const idle: PreparationState = { pending: false };
const records = new Map<string, PreparationState>();
const listeners = new Set<() => void>();
let revision = 0;
let settledRevision = 0;
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
function publish() { revision += 1; listeners.forEach(listener => listener()); }

/** Only an explicit button calls this POST. Requests survive SPA navigation. */
async function prepare(task: string, criterion: string) {
  const key = `${task}/${criterion}`;
  if (records.get(key)?.pending) return;
  records.set(key, { pending: true }); publish();
  try {
    const response = await api.prepareInterpretation(task, criterion);
    const issue = response.result.errors?.[0] || response.result.skipped?.[0]?.reason
      || (response.result.state === 'partial' ? response.result.reason : undefined);
    records.set(key, { pending: false, response, error: issue });
  } catch (issue) {
    records.set(key, { pending: false, error: issue instanceof Error ? issue.message : String(issue) });
  } finally { settledRevision += 1; publish(); }
}

export function useInterpretationPreparation(task: string, criterion: string) {
  useSyncExternalStore(subscribe, () => revision, () => 0);
  return { ...(records.get(`${task}/${criterion}`) || idle), prepare: () => prepare(task, criterion) };
}

/** Refresh interpretation-bearing reads after a request settles, without model calls. */
export function useInterpretationRevision() {
  return useSyncExternalStore(subscribe, () => settledRevision, () => 0);
}
