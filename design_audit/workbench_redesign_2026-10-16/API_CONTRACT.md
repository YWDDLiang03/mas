# Workbench v2 implementation contract

Local origin `/api/workbench`. English keys/data; UI may translate labels only. Errors return `{error: {code, message}}`; operations use existing Origin + X-MAS-Operation-Token protection. `GET /bootstrap` supplies `operation_token` to the local UI (never render it). All IDs opaque. Root owns server/investigation manager, windows_runtime owns `web/client`, read_models owns read projections, inheritance_case owns screening semantics.

## Shared types

- Task: `{task_id,title,objective,state?,candidate_count?,criteria_count?,latest_snapshot_id?,workflow_id?}`.
- Page: `{items,total,page,page_size,has_more,as_of?}`. Default page_size 50; filters apply before paging.
- Workflow: `{workflow_id,task_id,draft_id?,title,state,phase,phase_label?,message,started_at,updated_at,finished_at?,progress:{completed,planned,denominator_kind},budget:{used_usd,limit_usd,cost_status},phases:[{id,label,state,started_at?,finished_at?,counts?}],questions:[{id,prompt}],run_id?,snapshot_id?,error?,can_pause,can_resume,can_stop}`. States queued/running/waiting_input/paused/completed/unresolved/failed/cancelled. Unknown percent denominator is null. `phase` is task/evidence/propose/refine/review/freeze/screen/results.
- TaskInput: `{title?,objective,targets?:string[],constraints?:string,library_id?,source_task_id?,evidence_mode:'existing_only'|'retrieve',evaluation_mode:'staged'|'full',workers?:number,budget_usd?:number}`. Default evidence existing_only, evaluation staged, workers4, budget10. Constraints free text, normalized by server; target strings labels. Saved drafts carry this input unchanged.
- Criterion summary: `{criterion_id,version,name,definition?,state,role,unit?,direction?,cutoff?,evidence_count?,parents?:string[],children?:string[],stage?,iteration?,reason?,rule_ref?,attribute_ref?}`. Detail additionally `{history:[{id,stage,iteration,operation,before?,after?,reason,actor?,at?,sources?:[]}],sources:[{source_id,title?,quote?,locator?,url?}],supporting_claims?,critic_findings?,lineage?:{nodes:[],edges:[]}}`. Keep raw fields in a collapsed details block, not main labels.
- Stage: `{stage_id,run_id,stage,iteration,state,started_at?,finished_at?,before_count?,after_count?,added?,modified?,merged?,removed?,pending?,counts_known:boolean}`. Stage selection filters delta/criteria; unknown counts stay null.
- Candidate: `{candidate_ref,label,qualification:'qualified'|'pending'|'rejected'|'unassessed',position,score,hard_passed?,hard_total?,preference_coverage?,evidence_coverage?,reason?,state?,measured_count?,predicted_count?}`. Detail adds `{assessments:[{name,attribute_ref,rule_ref,role,verdict,value,unit,basis,reason,evidence:[]}],evidence:[{claim_id,source_id,title?,quote?,locator?,url?,value?,unit?}],...}`. Backend may expose aliases for old fields; new UI uses these normalized fields.

## Endpoints

- `GET /bootstrap` → `{tasks:Task[],drafts:[{draft_id,input:TaskInput,updated_at}],libraries:[{id,label,count}],evidence_sources:[{task_id,label,claim_count?}],current_task_id,workflows:Workflow[],operation_token,defaults:TaskInput,projection:{state,updated_at?}}`.
- `POST /drafts` `{draft_id?,input:TaskInput}` → `{draft_id,input,updated_at}`. Draft is operational input, not a scientific task yet.
- `POST /workflows` `{input:TaskInput,draft_id?,idempotency_key}` → Workflow. Normalization creates a scientific task once meaningful, then runs all phases. Watch task_id change from null to task_. No old CQA registry is copied.
- `GET /workflows` → `{items:Workflow[]}`; `GET /workflows/{id}` → Workflow.
- `POST /workflows/{id}/commands` `{command:'pause'|'resume'|'stop'}` → Workflow.
- `POST /workflows/{id}/answers` `{answers:{question_id:string}}` → Workflow.
- `GET /events?after=<integer>` is SSE. Events have integer id and `data: {kind:'workflow'|'projection'|'heartbeat',workflow?:Workflow,task_id?,cursor}`. Send latest workflow on connection and deltas, heartbeat15s. Native EventSource reconnect accepts Last-Event-ID. Client lightweight workflow poll2s fallback, never page reload.
- `GET /tasks/{task}/overview` → `{task:Task,summary:{candidate_count,criteria_count,hard_count?,preference_count?,pending_count?},workflow?:Workflow,stages:Stage[],snapshots:[],recent_changes:[]}`.
- `GET /tasks/{task}/stages` → `{items:Stage[]}`.
- `GET /tasks/{task}/criteria?page=&page_size=&q=&state=&stage=` → Page of Criterion summaries. `stage` is stage_id.
- `GET /tasks/{task}/criteria/{id}` → Criterion detail. Ref supports opaque lineage or attr/rule ref.
- `POST /tasks/{task}/criteria/{id}/revisions` `{changes:{name?,definition?,role?,direction?,cutoff?},reason}` → `{task_id,version?,workflow?:Workflow,message}`. Root records a versioned change/continuation; never mutates prior frozen results.
- `GET /tasks/{task}/snapshots` → `{items:[{snapshot_id,published_at,run_id,label?,evaluation_mode?,candidate_count?}]}`.
- `GET /tasks/{task}/candidates?snapshot=&status=qualified|pending|rejected|unassessed|all&q=&page=&page_size=` → Page plus `{snapshot_id,counts:{qualified,pending,rejected,unassessed,total},evaluation_mode,progress?,legacy_rank_only?}`.
- `GET /tasks/{task}/candidates/{id}?snapshot=` → Candidate detail.
- `GET /tasks/{task}/evidence?q=&page=&page_size=` → Page of `{claim_id,source_id,title?,quote?,locator?,url?,basis?,candidate_ref?}`.
- `GET /tasks/{task}/export.csv?snapshot=` streams all rows, independent of current UI filters. Includes qualification, mode, rank, reason/skip/missingness.
- `GET /settings` → existing OperationManager configuration `{preset,fields:[{key,label,value,kind,choices,minimum,maximum,doc}],config_hash,message}` plus provider status if available. `POST /settings` `{settings:{key:value}}` saves through existing manager.

## Read-model Python integration

`ReadModel(store_root, cache_path=None)` owns derived cache only. `sync()` incremental; `status()` readiness; `tasks()`, `overview(task)`, `stages(task)`, `criteria(task, page=1,page_size=50,q='',state='',stage='')`, `criterion(task,id)`, `snapshots(task)`, `candidates(task,snapshot=None,status='qualified',q='',page=1,page_size=50)`, `candidate(task,id,snapshot=None)`, `evidence(task,q='',page=1,page_size=50)`. Implement compatible names or send exact aliases promptly. No refresh/sync on every reader request; root background loop calls sync.

## Screening integration

New profiles explicitly opt into qualification-first and evaluation_mode, preserving historical records. Existing_only forbids new literature retrieval and uses pinned admitted claims/tool results, not previous verdicts. Root workflow passes a shared budget and cooperative control callback into generation and screening. Core agent sends the exact signatures before root wiring.
