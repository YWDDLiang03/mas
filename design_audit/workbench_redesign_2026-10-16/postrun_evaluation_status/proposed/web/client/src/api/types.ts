/** The v2 API contract. Research text and identifiers remain verbatim. */
export type WorkflowState = 'queued' | 'running' | 'waiting_input' | 'paused' | 'completed' | 'unresolved' | 'failed' | 'cancelled';
export type CandidatePartition = 'qualified' | 'pending' | 'rejected' | 'unassessed';
export type AccountingStatus = 'complete' | 'recorded' | 'partial' | 'unknown';
export type Primitive = string | number | boolean | null;
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; has_more: boolean; as_of?: string }
export interface Task { task_id: string; title: string; objective: string; state?: string; candidate_count?: number; criteria_count?: number; latest_snapshot_id?: string | null; workflow_id?: string | null }
export interface TaskInput { title?: string; objective: string; targets?: string[]; constraints?: string; library_id?: string | null; source_task_id?: string | null; revision_of_task_id?: string; reference_candidate?: string; evidence_mode: 'existing_only' | 'retrieve'; evaluation_mode: 'staged' | 'full'; workers?: number; budget_usd?: number }
export interface Draft { draft_id: string; input: TaskInput; updated_at: string }
export interface WorkflowPhase { id: string; label: string; state: string; started_at?: string | null; finished_at?: string | null; counts?: Record<string, number | null> }
export interface Workflow {
  workflow_id: string; task_id: string | null; draft_id?: string | null; title: string; state: WorkflowState;
  phase: string; phase_label?: string; message: string; started_at: string; updated_at: string; last_activity_at?: string | null; finished_at?: string | null;
  progress: { completed: number | null; planned: number | null; denominator_kind: string | null };
  budget: { used_usd: number | null; limit_usd: number | null; cost_status: AccountingStatus };
  phases: WorkflowPhase[]; questions: { id: string; prompt: string }[];
  run_id?: string | null; snapshot_id?: string | null; error?: string | { code?: string; message?: string } | null;
  can_pause: boolean; can_resume: boolean; can_stop: boolean; can_reevaluate?: boolean;
}
export interface Library { id: string; label: string; count?: number }
export interface EvidenceSource { task_id: string; label: string; claim_count?: number }
export interface Bootstrap { tasks: Task[]; drafts: Draft[]; libraries: Library[]; evidence_sources: EvidenceSource[]; current_task_id?: string | null; workflows: Workflow[]; operation_token?: string; defaults: TaskInput; projection: { state: string; ready?: boolean; syncing?: boolean; updated_at?: string }; operations_enabled?: boolean }
export interface Stage { stage_id: string; run_id: string; stage: string; iteration: number | null; state: string; started_at?: string | null; finished_at?: string | null; before_count: number | null; after_count: number | null; added?: number | null; modified?: number | null; merged?: number | null; removed?: number | null; pending?: number | null; counts_known: boolean; count_basis?: string; counts_basis?: string }
export interface Snapshot { snapshot_id: string; published_at: string; run_id: string; label?: string; evaluation_mode?: string; candidate_count?: number; reporting_tuple?: { ranking_coverage_floor?: number | null; mandated_coverage_floor?: number | null } }
export interface Change { id?: string; stage?: string; iteration?: number | null; operation?: string; before?: unknown; after?: unknown; reason?: string; actor?: unknown; at?: string; sources?: unknown[] }
export interface Overview { task: Task; input?: TaskInput; summary: { candidate_count: number; criteria_count: number; active_registered_count?: number; additional_unregistered_active_count?: number; total_active_count?: number; scoring_count?: number; latest_frozen_rule_set_ref?: string | null; deferred_count?: number; registered_pending_count?: number; pending_review_count?: number; historical_pending_review_count?: number; historical_registered_count?: number; retired_latest_count?: number; hard_count?: number; preference_count?: number; pending_count?: number; task_required_count?: number }; workflow?: Workflow | null; stages: Stage[]; snapshots: Snapshot[]; recent_changes: Change[] }
export interface CriterionEvaluation { state: 'enabled' | 'deferred' | 'pending' | 'not_prepared' | 'historical'; scope: string; rule_set_ref?: string | null; prepared_at?: string | null; reason_kind: string; reason?: string | null; basis?: Record<string, unknown> }
export interface Criterion { evaluation?: CriterionEvaluation; criterion_id: string; detail_ref?: string; version: number; name: string; definition?: string; state: string; role: string; unit?: string | null; direction?: string | null; cutoff?: unknown; evidence_count?: number; parents?: string[]; children?: string[]; stage?: string; iteration?: number; reason?: string; rule_ref?: string; attribute_ref?: string }
export interface CriterionSource { source_id: string; title?: string; quote?: string; locator?: string; url?: string }
export interface LineageNode { id?: string; ref?: string; detail_ref?: string; criterion_id?: string; name?: string; version?: number; definition?: string; state?: string; operation?: string; relation?: string; missing?: boolean; parents?: string[] }
export interface CriterionDetail extends Criterion { historical_version?: boolean; current_ref?: string | null; history: Change[]; sources: CriterionSource[]; supporting_claims?: unknown[]; critic_findings?: unknown[]; lineage?: { nodes: LineageNode[]; edges: { source: string; target: string; operation?: string }[] }; editable?: boolean; raw?: Record<string, unknown> }
export interface Candidate { candidate_ref: string; label: string; qualification: CandidatePartition; position: number | null; score: number | null; hard_passed?: number | null; hard_total?: number | null; preference_coverage?: number | null; evidence_coverage?: number | null; mandated_coverage?: number | null; rank_note?: string | null; reason?: string; state?: string; measured_count?: number; predicted_count?: number }
export interface Assessment { name: string; attribute_ref: string; rule_ref: string; role: string; verdict: string; value: unknown; unit?: string | null; basis: string; reason: string; evidence: string[]; counter_evidence?: string[] }
export interface Evidence { claim_id: string; source_id: string; title?: string; quote?: string; locator?: string; url?: string; basis?: string; candidate_ref?: string; value?: unknown; unit?: string | null }
export interface CandidatesPage extends Page<Candidate> { snapshot_id: string | null; counts: Record<CandidatePartition, number> & { total: number }; evaluation_mode: string; progress?: unknown; legacy_rank_only?: boolean }
export interface CandidateDetail extends Candidate { assessments: Assessment[]; evidence: Evidence[]; snapshot_id?: string; legacy_rank_only?: boolean; raw?: { qualification?: { required_total?: number; required_direct_answered?: number; missing_direct_required_rule_refs?: string[] }; [key: string]: unknown }; mechanism?: string | { sentences?: { text: string }[] } | null }
export interface SettingChoice { value: string; label?: string }
export interface SettingField { key: string; label: string; value: Primitive; kind: string; choices?: (string | SettingChoice)[]; minimum?: number; maximum?: number; doc?: string; secret?: boolean; configured?: boolean; editable?: boolean }
export interface Settings { preset: string; fields: SettingField[]; config_hash?: string; message?: string; providers?: unknown; model_roles?: { role: string; model_id: string }[] }
export interface RevisionResult { task_id: string; version?: number; workflow?: Workflow; message: string }
export interface StreamEvent { kind: 'workflow' | 'projection' | 'heartbeat'; workflow?: Workflow; task_id?: string; cursor: number }
