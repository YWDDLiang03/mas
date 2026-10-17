# Workbench, read projections and command line

[Components](README.md) · [Execution](execution-and-reuse.md) · [Models](models-and-budgets.md)

MAS offers two operator surfaces over the same research records: a local React workbench for investigations and inspection, and the `mas` command line for explicit operations and scripting. The workbench keeps an indexed projection so large candidate/evidence tables do not require replaying every unrelated run on each request. This is C17 plus the local host and composition infrastructure.

## Inputs and outputs

| Boundary | Inputs | Outputs |
|---|---|---|
| Browser form | Research goal, library, evidence selection, constraints, mode, budget, uploads | Draft/workflow request, clarification answers, progress and saved result |
| Workbench read API | Task/resource ID, snapshot, filters and pagination | Projection data for overview, criteria, candidates, scores, evidence and sources |
| Local operation API | Same-origin request with operation token and allowed command | Validated workflow/settings/revision action and recorded outcome |
| CLI | Explicit subcommand/options and configuration | Core records, terminal summaries, source/model diagnostics and exports |
| File model bridge | JSON request/response files | `ModelResponse` with answering identity |

## Application structure and rationale

[`ui/server.py`](../../src/mas/ui/server.py) supplies a threaded local HTTP server, request routing, SSE progress and loopback validation. [`WorkbenchAPI`](../../src/mas/ui/workbench_api.py) serves `/workbench/` assets and `/api/workbench/` application resources. The built client is loaded from `web/client/dist`, with `MAS_WORKBENCH_ASSET_DIR` as an explicit alternate asset directory.

[`WorkflowManager`](../../src/mas/ui/workflows.py) persists drafts, idempotent workflow starts, phase checkpoints, budget usage and pause/resume/stop/reevaluate commands. [`core/investigation.execute()`](../../src/mas/core/investigation.py) performs normalization, evidence selection, derivation, machine review, freeze and screening through the scientific components. A finished workflow can contain separate derivation and screening run IDs; its convenience status does not replace those scientific records.

[`OperationManager`](../../src/mas/ui/operations.py) validates/saves settings and supports an allowlist of CLI-backed local jobs, recording their actual process output and failures. Modern investigation workflows additionally use the workflow worker thread and core composition. A user revision appends a criterion version; `apply_revision()` preserves old frozen refs and starts a new review/evaluation workflow when needed.

This split lets a browser display work without writing raw SQL to scientific tables. The command-owning component performs the scientific validation. Display edits and summaries stay in separate annotation stores.

## Read projection

[`projection.progress()`](../../src/mas/core/projection.py) folds a run's events into execution/progress state, scoped denominators, stage/step/exchange records and budget/accounting. Percentages are meaningful only when the denominator is fixed; budget is a separate quantity.

[`ReadModel`](../../src/mas/ui/read_model.py) opens the scientific store read-only and incrementally updates a separate SQLite cache from public event prefixes. Its background sync is owned by the host. Requests use independent read connections and load large claim/assessment artifacts on demand. The cache can be rebuilt; it is not the authoritative journal. `MAS_WORKBENCH_READ_CACHE` can name an alternate cache file.

[`ReadAPI`](../../src/mas/ui/read_api.py) translates query parameters into paginated resource reads. Candidate/evidence/score links carry the selected snapshot, so inspecting a historical board uses its historical assessment relationships. [`evidence_read.py`](../../src/mas/ui/evidence_read.py), [`evidence_groups.py`](../../src/mas/ui/evidence_groups.py) and [`evidence_collections.py`](../../src/mas/ui/evidence_collections.py) expose source/claim/criterion/candidate relationships and selectable saved collections. [`score_details.py`](../../src/mas/ui/score_details.py) explains the actual recorded scoring inputs.

`ResearchBriefService` in [`research_briefs.py`](../../src/mas/ui/research_briefs.py) stores optional generated interpretations separately from scientific records. GET requests read saved briefs; generation is an explicit POST action with its own bounded cost. Citations are restricted to the selected criterion's inputs. [`WorkspaceDisplay`](../../src/mas/ui/workspace_display.py) keeps user-facing titles/labels apart from immutable scientific artifacts.

## API map

These routes describe the local application, not a versioned public remote-service SDK. Exact payloads are implemented in `WorkbenchAPI`, `ReadAPI` and the client [`api/types.ts`](../../web/client/src/api/types.ts).

| Method / path | Responsibility |
|---|---|
| `GET /api/workbench/bootstrap` | Tasks, libraries, evidence collections, workflow states and defaults |
| `GET /api/workbench/settings` | Resolved settings and model-role display |
| `GET /api/workbench/tasks/{task}/overview` | Task context and saved evaluations |
| `GET /api/workbench/tasks/{task}/{resource}` | Criteria, candidates, evidence, evidence-sources, snapshots, stages and saved briefs |
| `GET /api/workbench/tasks/{task}/scores/{candidate}` | Recorded score details |
| `GET /api/workbench/tasks/{task}/export.csv` | All candidate rows for selected snapshot |
| `POST /api/workbench/drafts` | Save a research draft |
| `POST /api/workbench/workflows` | Start one investigation with an idempotency key |
| `POST /api/workbench/workflows/{workflow}/answers` | Supply requested clarification |
| `POST /api/workbench/workflows/{workflow}/commands` | Pause, resume, stop or reevaluate |
| `POST /api/workbench/uploads/preview` | Parse/map candidate or observation CSV before commit |
| `POST /api/workbench/uploads/{preview}/commit` | Commit the selected mapping as an immutable dataset |
| `POST /api/workbench/tasks/{task}/criteria/{criterion}/revisions` | Append a criterion revision and trigger appropriate review |
| `POST /api/workbench/tasks/{task}/research-briefs` | Explicitly generate a criterion interpretation |

The compatibility read surface and `/api/operations` also remain in the server. In the standard modern mode, familiar top-level URLs redirect into the workbench. Start with `--legacy-ui` to inspect the historical read interface.

## Command line responsibilities

[`cli/main.py`](../../src/mas/cli/main.py) registers the actual command tree. `task` creates/shows/lists/inherits/shortlists tasks; `criteria` derives, reduces, audits bindings and exports; `rules` freezes/reads sets; `review` lists/adjudicates/reopens and retains interactive human decisions; `measurement` registers profiles; `run` starts/shows/resumes; `board`, `candidate` and `score` inspect saved results. `config`, `models`, `sources` and `predict` diagnose the installation, while `recovery` runs the evaluator-only intake/report path.

`mas bridge` delegates to [`cli/bridge.py`](../../src/mas/cli/bridge.py). `next` atomically claims an unanswered model request, `answer` publishes schema data/text with model and answering identity, and `status` reports pending work. File exchange does not launch an external worker or grant that worker scientific approval authority.

## Language, host and failure behavior

The React client defaults to English. [`i18n.tsx`](../../web/client/src/i18n.tsx) saves EN/中文 preference in `mas.language` and carries `lang` in navigation. Interface text and dates adapt to that display preference; research tasks, criteria, evidence, model prompts and stored run content remain English, retaining original user/source text. The compatibility UI has a separate cookie-backed language handler in [`ui/i18n.py`](../../src/mas/ui/i18n.py).

The host binds loopback. Mutation requests require `X-MAS-Operation-Token` and the expected origin. `--allow-operations` enables local controls; default read serving does not grant a multi-user role system. Unknown resources return not-found responses; invalid input returns validation errors; an unavailable projection returns preparing/unavailable status. A missing client build returns an explicit missing-build response. Provider and subprocess failures remain their actual failures in the operation/run records.

CSV export includes qualification, evaluation mode, position, score, hard-condition counts, evidence/preference coverage, missing/skipped reasons and snapshot ID. Pagination limits display size; exporting the selected snapshot retains the full candidate population.

## Worked example: inspect a fixed saved evaluation

**Illustrative** request flow, using placeholder IDs from the local workspace:

```text
GET /api/workbench/tasks/task_example/snapshots
GET /api/workbench/tasks/task_example/candidates?snapshot=lb_example&page=1
GET /api/workbench/tasks/task_example/candidates/cand_example?snapshot=lb_example
GET /api/workbench/tasks/task_example/evidence?candidate_ref=cand_example&snapshot=lb_example
GET /api/workbench/tasks/task_example/export.csv?snapshot=lb_example
```

Keeping `snapshot` in every link makes the candidate verdict, its evidence links and the export refer to the same saved evaluation even after a new run publishes another board. These GETs inspect records; they do not start fresh research or model calls.

## Existing verification

[`test_read_model.py`](../../tests/test_read_model.py) checks incremental/rebuildable projections. [`test_ui.py`](../../tests/test_ui.py) covers loopback, operation token/origin, read-only scientific access, pagination/export and language separation. [`test_workbench_evidence.py`](../../tests/test_workbench_evidence.py), [`test_workbench_uploads.py`](../../tests/test_workbench_uploads.py), [`test_workbench_recompute.py`](../../tests/test_workbench_recompute.py) and [`test_workflow_reevaluation.py`](../../tests/test_workflow_reevaluation.py) check concrete application behavior. GUI acceptance and live scientific runs are separate evidence categories from these local integration tests.
