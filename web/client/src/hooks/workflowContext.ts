import type { Workflow } from '../api/types';

const activeStates = new Set(['queued', 'running', 'paused', 'waiting_input']);

/** A new workflow may be followed before its task exists; other task controls stay scoped. */
export function visibleWorkflow(workflows: Workflow[], taskId: string, followingId: string): Workflow | null {
  if (followingId) return workflows.find(workflow => workflow.workflow_id === followingId) || null;
  if (!taskId) return null;
  const current = workflows.filter(workflow => workflow.task_id === taskId);
  return current.find(workflow => activeStates.has(workflow.state)) || current[0] || null;
}
