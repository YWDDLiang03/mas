import { useRef } from 'react';
import { api } from '../api/client';
import type { Bootstrap } from '../api/types';
import { useResource } from './useResource';

export function projectionReady(projection: Bootstrap['projection']) {
  return projection.syncing !== true && (projection.ready ?? projection.state === 'ready');
}

export function retainTaskList(previous: Bootstrap | undefined, incoming: Bootstrap): Bootstrap {
  if (!projectionReady(incoming.projection) && !incoming.tasks.length && previous?.tasks.length) {
    return { ...incoming, tasks: previous.tasks };
  }
  return incoming;
}

export function useBootstrap() {
  const previous = useRef<Bootstrap>();
  return useResource<Bootstrap>('bootstrap', async () => {
    const data = retainTaskList(previous.current, await api.bootstrap());
    previous.current = data;
    return data;
  });
}
