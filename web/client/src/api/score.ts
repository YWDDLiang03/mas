export interface ScoreRow {
  required_for_admission?: boolean;
  display_name?: string | null;
  rule_ref: string; attribute_ref: string; name: string; definition?: string;
  value: number | string | boolean | null; unit?: string | null; basis: string;
  direction?: string; predicate_form: string; cutoff?: { comparator: string; value: unknown; unit?: string } | null;
  aggregation?: string; value_transform?: Record<string, unknown> | null;
  weight: number; comparison_score: number | null; weighted_score: number | null; contribution: number | null;
  included_in_score: boolean; included_in_coverage: boolean; direct: boolean; suppressed: boolean;
  reason?: string; evidence_refs?: string[];
  normalization?: { kind: string; n?: number | null; worse?: number | null; equal?: number | null; formula?: string | null };
}
export interface ScoreDetails {
  available: boolean; unavailable_reason?: string; snapshot_id: string; candidate_ref: string; label: string;
  score: number | null; position: number | null; qualification: string; rule_set_ref: string; method: string;
  population_count: number; population_labels: string[]; score_numerator: number; score_denominator: number;
  coverage_numerator: number; coverage_denominator: number; coverage_floor: number; coverage: number | null;
  rows: ScoreRow[]; excluded_counts?: { hard: number; context: number; suppressed: number; unknown: number; inapplicable: number };
  validation?: { matches: boolean; score_matches: boolean; coverage_matches: boolean };
}
export async function scoreDetails(task: string, candidate: string, snapshot: string, signal?: AbortSignal): Promise<ScoreDetails> {
  const response = await fetch(`/api/workbench/tasks/${encodeURIComponent(task)}/scores/${encodeURIComponent(candidate)}?snapshot=${encodeURIComponent(snapshot)}`, { signal, cache: 'no-store' });
  const result = await response.json();
  if (!response.ok) throw new Error(result?.error?.message || 'Score details are not available.');
  return result;
}
