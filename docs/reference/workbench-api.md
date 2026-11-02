# Workbench inputs and result resources

[Configuration](../configuration.md) · [Agent runner](../agent-run.md) · [CDES component](../components/structure-predictions.md)

The local browser uses `/api/workbench/`. The server runs with local operations enabled for settings, uploads, task creation and workflow control. The browser obtains its operation token from bootstrap and sends it in `X-MAS-Operation-Token` with a same-origin request. Clients keep that token in the local session.

## Study input

The `input` object used by drafts and new workflows includes:

| Field | Purpose |
|---|---|
| `title`, `objective` | Readable study title and the research question |
| `targets`, `constraints` | Task-defined target profile and requirements |
| `entity_type` | `drug`, `carrier` or `general` |
| `library_id` | Selected workspace library or uploaded candidate set |
| `source_task_id`, `evidence_upload_id` | Selected saved evidence collection or observation upload |
| `evidence_mode` | `retrieve` or `existing_only` |
| `evaluation_mode` | `staged` or `full` |
| `workers`, `budget_usd` | Concurrency and study budget |
| `cdes_enabled`, `cdes_source_id` | Optional CDES choice and supplied collection |
| `original_objective`, `objective_source` | Original input and the origin of the displayed objective |

The browser prepares an objective from targets and requirements when its optional context field is empty. Programmatic clients supply the resulting objective, or use the agent runner's drug-library mode. Saved-evidence mode requires the selected collection or uploaded observations. A retrieval study can start from its own task and library.

## Control resources

| Request | Result |
|---|---|
| `GET /bootstrap` | Available tasks, libraries, collections, defaults and projection status |
| `GET /settings` | Current configuration and optional-module choices |
| `POST /settings` | Save the supplied `settings` mapping for future work |
| `POST /drafts` | Save a study `input` for later completion |
| `POST /workflows` | Start the supplied `input`; an `idempotency_key` identifies the request |
| `GET /workflows/{id}` | Current stage, progress, costs and recorded outputs |
| `POST /workflows/{id}/commands` | Submit a `command`: `pause`, `resume`, `stop` or `reevaluate` |
| `POST /workflows/{id}/answers` | Supply the requested task clarification in `answers` |
| `POST /tasks/{task}/structure-module` | Set the completed study's CDES view using `enabled` |

See [`workbench_api.py`](../../src/mas/ui/workbench_api.py) for routing and [`workflows.py`](../../src/mas/ui/workflows.py) for state transitions and command requirements.

## Result resources

Under `/tasks/{task}/`, `overview`, `criteria`, `candidates`, `evidence-sources` and `scores/{candidate}` provide the research views. Lists accept server-side search and pagination. The `snapshot` parameter selects a saved evaluation. `export.csv` returns the complete candidate result.

The [CDES resource table](../components/structure-predictions.md#read-and-export) documents target profiles, candidate detail, matching tables and complete CSV/JSON/ZIP exports. Scientific observations, criterion scores and interaction predictions retain their own evidence bases and units.
