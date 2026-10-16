# Evidence context and research interpretation backend

Implemented as a read projection and a separate annotation service. Scientific task versions, facts, assessments, snapshots, qualification and ranking are unchanged. The primary store is opened with SQLite `mode=ro`.

The independent upgraded cache is `var/primary/workbench-linked-read.db`. It was copied consistently from the previous query cache and retains all 9 public tasks. It is ready at source cursor 1616362. Keep the old service on its old cache until switching deployment; do not let two projector versions write the same cache.

## Read endpoints

All routes below are relative to the modern workbench task API.

- `GET tasks/{task}/evidence`: `q`, `page`, `page_size` (default 50), `criterion_ref`, `attribute_ref`, `rule_ref`, `candidate_ref`, `source_id`, `claim_id`, `snapshot`.
- `GET tasks/{task}/evidence/{claim}`: `snapshot`, `criteria_page`, `candidate_page`, `link_page_size`; exact admitted public claim in this task only.
- `GET tasks/{task}/criteria/{exact_ref}?snapshot=...`: adds `explanation`, `evidence_query`, exact `attribute_record`/`rule_record`, optional cached `research_brief`.
- `GET tasks/{task}/research-briefs`: frozen-core status counts and annotation-store cumulative usage. `.../research-briefs/{exact_ref}` returns one exact-input interpretation.

Evidence retains its original fields, adding separate `summary`, `source`, `context`, `links`, and detail `research_relevance`, `criteria_usage`, `candidate_usage`, `research_briefs`. `summary.method=recorded_fact_projection` and `research_relevance.method=recorded_usage_projection` are deterministic displays, not model syntheses. `source.excerpt` is the saved quotation. `source.passage/before/after` are saved document passages, available only on detail; missing or ambiguous original context stays explicitly missing.

Links contain exact criterion `detail_ref`, readable name, attribute/rule refs, and candidate label/ref, run and nullable snapshot. Lineage preserves `via_claim_refs` and typed relationships. A `criterion_basis` relation is general rationale and does not claim a candidate measurement. List previews show 3 links with actual totals. Under a `candidate_ref` filter, `links.scope` records the selected candidate and snapshot, and previews/counts apply to that candidate plus criterion support.

Connection queries default to the latest saved snapshot. Explicit `snapshot` retains that historical scope and its exact versions. `links.scope` exposes `mode`, resolved `snapshot_id`, real `snapshot_published_at`, `candidate_unit` and `criteria_unit`. Candidate counts in a snapshot are unique candidates; criteria counts are exact criterion/proposal versions. A task with no snapshot falls back to task history with the explicit unit `candidate_run_records`, also returned as `candidate_usage.unit`; it must not be labeled as unique candidates. `criteria_usage.unit` is `criterion_versions`. The actual prior 7531 figure was 1177 cancelled-run records plus two groups of 3177 completed-run records; the corrected default is 3177 unique candidates in snapshot 2. Source quotes and brief input hashes are unchanged. Verification is recorded in `var/workbench-v2-acceptance/evidence-connection-scope-check.json`.

Candidate assessment links retain the exact original rule version and selected snapshot. No missing snapshot is relabeled as the latest result. Historical snapshot scope is implemented using assessment validity intervals. For both actual snapshots, every selected link row matches the previous latest-assessment SQL exactly.

## Explicit annotation generation

The host wires the service once; GET endpoints never call a model:

```python
from mas.core.investigation import investigation_roster
from mas.ui.research_briefs import ResearchBriefService

service = ResearchBriefService(
    operations.working_directory / "var/workbench-annotations",
    api.model,
    investigation_roster(operations),
    max_usd=0.50,
)
api.model.brief_service = service

# Root executes this explicit action after deployment, once:
result = service.generate("task_01M51AQ0JK0MYN47806ZD5XS1B")
```

`generate()` defaults to the current exact frozen refs. The inspected task has 24 entries: 6 task-backed anchors and 18 evidence-backed model inputs; every evidence-backed input has saved original passages. Each whole criterion stays within one batch and has its own citation whitelist. Every generated paragraph must cite that criterion's input claims. Task-backed anchors use actual task refs and have no fabricated claim IDs. English interpretations separate conclusion, task implication, applicability conditions and limitations from original text.

The independent Core annotation store records requests, provider attempts, final usage, input artifacts, failed outputs and successful brief artifacts. Global cumulative spending is restored across calls, tasks and restarts; a final receipt replaces its provider-attempt subtotals. Before each actual provider attempt, known tariffs and conservative input/output bounds must fit the remaining $0.50 cap. Unknown or in-flight spending stops further generation. Quota or citation failures produce an explicit partial result; they do not enter source facts or change CQA. Cached results are keyed by task, exact criterion version and hashes of supporting claims/source context. Stale inputs are not served as current interpretations.

Current preparation status: 0 ready, 18 missing, 6 task-backed; annotation spending $0.00. No real model call was made by the read-layer implementation or checks.

## Verification

`tests/test_workbench_evidence.py` and `tests/test_read_model.py`: 30 passed. Checks include saved original context, exact-version bidirectional filters and pagination, private-context exclusion, incremental/backfill consistency, old-snapshot assessment supersession, per-criterion citation validation, cumulative annotation cap restoration and no double billing in a temporary store.

Actual-task report: `var/workbench-v2-acceptance/evidence-context-final-check.json`. Five local samples per new query (small-sample nearest-rank P95): unfiltered evidence 19.820 ms; text query 180.839 ms; exact criterion 38.545 ms; Surufatinib context 166.834 ms; exact source 151.848 ms. Each returned at most 50 records. These are local ReadModel measurements, separate from the previous 50-sample HTTP acceptance. The initial slow profile is preserved in `evidence-context-upgrade-check.json`.

Snapshot 1: 166308 exact link row IDs equal; snapshot 2: 166311 equal. Brief/detail input hashes match for both logP v2 refs. `research-brief-prepared-manifest.json` records all 24 exact refs and input sizes without making model calls.
