import type { Bootstrap, CandidateDetail, CandidatesPage, Criterion, CriterionDetail, Draft, EntityType, Evidence, EvidenceDetail, EvidenceQuery, InterpretationPreparation, Overview, Page, RevisionResult, Settings, Snapshot, Stage, TaskInput, UploadKind, UploadPreview, UploadResult, Workflow } from './types';
import type { EvidenceCollection, EvidenceSourcePage, SourceKind } from './types';

const ROOT = '/api/workbench';
let operationToken = '';
export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); this.name = 'ApiError'; }
}
export function setOperationToken(token?: string) { operationToken = token || ''; }
function query(values: Record<string, string | number | undefined | null>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  return params.size ? `?${params}` : '';
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Accept', 'application/json');
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (init?.method && init.method !== 'GET') headers.set('X-MAS-Operation-Token', operationToken);
  const response = await fetch(ROOT + path, { ...init, headers, cache: 'no-store', credentials: 'same-origin' });
  const body = (response.headers.get('content-type') || '').includes('json') ? await response.json() : null;
  if (!response.ok) throw new ApiError(body?.error?.message || body?.message || `Request failed (${response.status})`, response.status, body?.error?.code);
  if (!body) throw new ApiError('The service returned an unexpected response.', response.status);
  return body as T;
}
const post = <T>(path: string, body: unknown = {}) => request<T>(path, { method: 'POST', body: JSON.stringify(body) });
const taskPath = (id: string) => `/tasks/${encodeURIComponent(id)}`;
export const api = {
  bootstrap: () => request<Bootstrap>('/bootstrap'),
  overview: (task: string, signal?: AbortSignal) => request<Overview>(taskPath(task) + '/overview', { signal }),
  saveDraft: (input: TaskInput, draft_id?: string) => post<Draft>('/drafts', { input, draft_id }),
  launch: (input: TaskInput, idempotency_key: string, draft_id?: string) => post<Workflow>('/workflows', { input, draft_id, idempotency_key }),
  uploadTemplateUrl: (kind: UploadKind) => ROOT + `/uploads/templates/${kind}.csv`,
  previewUpload: (input: { kind: UploadKind; filename?: string; content?: string; upload_id?: string; mapping?: Record<string, string | null>; entity_type?: EntityType; library_id?: string | null }) => post<UploadPreview>('/uploads/preview', input),
  commitUpload: (upload: string, input: { mapping: Record<string, string | null>; entity_type: EntityType; library_id?: string | null }) => post<UploadResult>('/uploads/' + encodeURIComponent(upload) + '/commit', input),
  workflows: () => request<{ items: Workflow[] }>('/workflows'),
  workflow: (id: string) => request<Workflow>('/workflows/' + encodeURIComponent(id)),
  command: (id: string, command: 'pause' | 'resume' | 'stop' | 'reevaluate') => post<Workflow>('/workflows/' + encodeURIComponent(id) + '/commands', { command }),
  answer: (id: string, answers: Record<string, string>) => post<Workflow>('/workflows/' + encodeURIComponent(id) + '/answers', { answers }),
  criteria: (task: string, options: { q?: string; state?: string; stage?: string; page?: number }, signal?: AbortSignal) => request<Page<Criterion>>(taskPath(task) + '/criteria' + query({ ...options, page_size: 50 }), { signal }),
  criterion: (task: string, id: string, signal?: AbortSignal, snapshot?: string) => request<CriterionDetail>(taskPath(task) + '/criteria/' + encodeURIComponent(id) + query({ snapshot }), { signal }),
  prepareInterpretation: (task: string, criterion_ref: string) => post<InterpretationPreparation>(taskPath(task) + '/research-briefs', { criterion_ref }),
  editCriterion: (task: string, id: string, changes: { name?: string; definition?: string; role?: string; direction?: string; cutoff?: unknown }, reason: string) => post<RevisionResult>(taskPath(task) + '/criteria/' + encodeURIComponent(id) + '/revisions', { changes, reason }),
  stages: (task: string, signal?: AbortSignal) => request<{ items: Stage[] }>(taskPath(task) + '/stages', { signal }),
  snapshots: (task: string, signal?: AbortSignal) => request<{ items: Snapshot[] }>(taskPath(task) + '/snapshots', { signal }),
  candidates: (task: string, options: { q?: string; status?: string; snapshot?: string; page?: number }, signal?: AbortSignal) => request<CandidatesPage>(taskPath(task) + '/candidates' + query({ ...options, page_size: 50 }), { signal }),
  candidate: (task: string, id: string, snapshot?: string, signal?: AbortSignal) => request<CandidateDetail>(taskPath(task) + '/candidates/' + encodeURIComponent(id) + query({ snapshot }), { signal }),
  csvUrl: (task: string, snapshot?: string | null) => ROOT + taskPath(task) + '/export.csv' + query({ snapshot }),
  evidence: (task: string, options: EvidenceQuery, signal?: AbortSignal) => request<Page<Evidence>>(taskPath(task) + '/evidence' + query({ ...options, page_size: 50 }), { signal }),
  evidenceSources: (task: string, options: EvidenceQuery & { kind?: SourceKind }, signal?: AbortSignal) => request<EvidenceSourcePage>(taskPath(task) + '/evidence-sources' + query({ ...options, page_size: 20 }), { signal }),
  evidenceCollection: (task: string, signal?: AbortSignal) => request<EvidenceCollection>('/evidence-collections/' + encodeURIComponent(task), { signal }),
  saveEvidenceCollection: (task: string, display: { label: string; description: string; topics: string[] }) => post<EvidenceCollection>('/evidence-collections/' + encodeURIComponent(task) + '/display', display),
  evidenceDetail: (task: string, claim: string, options: { snapshot?: string; criteria_page?: number; candidate_page?: number; link_page_size?: number } = {}, signal?: AbortSignal) => request<EvidenceDetail>(taskPath(task) + '/evidence/' + encodeURIComponent(claim) + query(options), { signal }),
  settings: (signal?: AbortSignal) => request<Settings>('/settings', { signal }),
  saveSettings: (settings: Record<string, unknown>) => post<Settings>('/settings', { settings }),
  eventsUrl: (after?: number) => ROOT + '/events' + query({ after }),
};
