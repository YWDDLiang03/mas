# Component walkthrough: inspect, change, and verify a research run

[中文](zh/component-walkthrough.md) · [One-command agent runs](agent-run.md) · [Component reference](components/README.md) · [Browser tutorial](tutorial.md)

This tutorial follows one saved research task through the actual components, then shows where to change the next experiment. Start with the read-only examples: they need Python's standard library, make no model or network requests, and do not open a research store. The component reference explains the full contracts; this page shows how those contracts meet in a concrete run.

## Choose the operation before changing anything

| Operation | Inputs and work | What the outcome means |
|---|---|---|
| Inspect published files | Read the JSON/CSV under `examples/oral-multitarget/latest` | Understand the recorded result and its provenance; no new screening occurs. |
| Restore and replay | Restore the portable records into a separate workspace; run the production qualification, preference scoring and snapshot builder | Check whether the current engine reproduces the fixed saved assessments and leaderboard. Criteria and observations stay fixed. |
| Generate again on pinned evidence | Create a new task with an empty criterion pool/registry, reuse the 3,157 pinned claims from 164 sources and the 68,886 historical tool facts | A new model experiment: new criteria, review, assessment and ranking. Compare its result with the saved run. |
| Research on changed inputs | Create a new task/workspace with your objective, data, sources, tools and model configuration | A different experiment whose inputs, costs and conclusions need their own record. |

Use [the agent-run guide](agent-run.md) for the executable restore, replay and new-run commands. Their shared implementation is [`reproduction.py`](../src/mas/core/reproduction.py): `import_bundle()` restores selected records, `verify_replay()` calls the real production engine, and `prepare_live()` prepares an evidence-only source for independent generation. The capsule is a selection of public records with declared exclusions, not a full database backup. Its [manifest](../examples/oral-multitarget/latest/reproduction/manifest.json) records hashes, dependencies, omitted documents/traces and unavailable historical references. Follow its distribution instructions when the large capsule is not already present.

The replay target is task `task_01M52CBE5GYPK9F0MCZYBMPH84`, run `run_01M52Q4VRB00T5Z3QJW08SSV96`, snapshot `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`, `rules@v2`. The study has 3,177 candidates, 18 unique enabled decision rules and 13 contextual observations. Six eligibility requirements comprise one oral condition and five required target observations; those five target criteria also belong to the 17 scoring criteria, so `6 + 17 − 5 = 18`. Current selection reports **10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded**. Surufatinib is rank 1, score `0.7592592592592593`, direct preference coverage `10/17`. The frozen source retains `qualified: 10`, `pending: 3167`, `rejected: 0`; [the classification mapping](reference/system-alignment.md#classification-version) explains the current display. A new model investigation records its own outcomes.

<a id="read-records"></a>
## 1. Foundation: identify the records you are reading

**Input → output:** the task/run IDs select immutable versions and artifacts; exports expose those records in files. Begin with [task.json](../examples/oral-multitarget/latest/results/task.json), [run-bindings.json](../examples/oral-multitarget/latest/results/run-bindings.json), [snapshot.json](../examples/oral-multitarget/latest/results/snapshot.json) and [source-facts.json](../examples/oral-multitarget/latest/source-facts.json).

Run this PowerShell block at the repository root. It reads only published files:

```powershell
@'
import csv, json
from collections import Counter
from pathlib import Path
root = Path("examples/oral-multitarget/latest")
task = json.loads((root / "results/task.json").read_text(encoding="utf-8"))
bindings = json.loads((root / "results/run-bindings.json").read_text(encoding="utf-8"))
rows = list(csv.DictReader((root / "results/candidates.csv").open(
    encoding="utf-8-sig", newline="")))
print(task["task_context_id"], task["version"])
print("Candidates:", len(rows), dict(Counter(row["qualification"] for row in rows)))
print("Pinned tool facts:", bindings["run_01M52Q4VRB00T5Z3QJW08SSV96"]
      ["tool_replay"]["cache_entries"])
'@ | python -
```

Expected: task version `3`; `3177`, `{'qualified': 10, 'pending': 3167}`; `68886`. JSON object order is not scientific identity. [`canonical.py`](../src/mas/core/canonical.py), [`ArtifactStore`](../src/mas/core/artifacts.py) and [`Journal`](../src/mas/core/journal.py) establish content hashes and event lineage. File SHA-256 checks belong to the export/portable manifest; artifact IDs hash canonical artifact envelopes.

**Check before continuing:** selected task, run and snapshot agree. Keep snapshot `_1` and its failure/correction history when interpreting `_2`. See [foundation reference](components/foundation.md).

<a id="task-and-config"></a>
## 2. Task and configuration: turn the objective into a bound experiment

The saved English objective asks for one orally administered agent engaging CSF1R, VEGFR1/2/3 and FGFR1. `original_user_input` retains the entered fields. `scope_entities` binds the five target identifiers; `constraints[0]` records oral administration as hard, with `provenance = user_task_normalized`. The reference candidate is disclosed in `seed_candidates`; its name does not supply evidence.

[`investigation.py`](../src/mas/core/investigation.py) normalizes workbench input; [`task.record_version()`](../src/mas/core/task.py) validates and versions the result. [`config.resolve()`](../src/mas/core/config.py) resolves settings and their winning layers. Screening binds task/rule versions, settings, adapter, providers and implementation into a run. Read the final evaluation's binding in `run-bindings.json` rather than treating the current Settings screen as its historical configuration.

**Check:** five required target identities, the oral hard condition, `existing_only`, `staged`, worker count and recorded budget match the intended experiment. A changed objective belongs to a new task; see [change the objective](#change-objective) and [task/configuration reference](components/tasks-and-configuration.md).

<a id="model-and-budget"></a>
## 3. Model roles and budget: see who interpreted the evidence

Models normalize tasks, read evidence, propose/refine criteria, criticize and adjudicate. [`ModelRoster` and `call_role()`](../src/mas/core/models.py) bind roles to concrete providers, record actual requests/responses and charge attempts including repair/retry work. Different role names can share one model.

Read [model-accounting.json](../examples/oral-multitarget/latest/results/model-accounting.json), the saved run bindings and [workflow.json](../examples/oral-multitarget/latest/results/workflow.json). The workflow records a USD `5.5` envelope and `4.210147199999997` used with `cost_status = recorded_estimate`. The historical model identity is `deepseek-v4-flash`; a current provider selection belongs to the new run. Portable records omit raw model traces as declared in their manifest, so the bundle does not expose every original prompt.

**Check:** distinguish provider/model identity, role, attempt count, known cost and unknown cost. Replaying fixed assessments makes zero new model calls; independent criterion generation spends according to its own provider/configuration. See [change models and budget](#change-model-budget) and [reference](components/models-and-budgets.md).

<a id="tools-and-replay"></a>
## 4. Tools and providers: answer one exact question

For FGFR1, a route asks for potency observations at the declared target. The [`Broker`](../src/mas/core/broker.py) resolves a registered capability plus question kind, checks required inputs and versions, and returns an outcome and provenance. Tool success supplies observations; the assessor later decides their use.

The final binding's `tool_replay` contains 68,886 completed `ok`/`empty` facts. Matching includes tool ID, contract version, implementation version, question kind and normalized input. One source run was cancelled; its successfully completed tool results are pinned at terminal sequence `92831`. The cancellation remains part of the source record. `failed`/`partial` attempts are excluded from the exact fact cache. PubChem row projection has its own explicit policy.

**Check:** a replay hit retains its original date/source/version. An `existing_only` miss becomes `existing_evidence_unavailable`; it must not silently become a fresh remote lookup. Use [tool customization](#change-tool) for an integration and [tools reference](components/tools-and-providers.md) for outcomes.

<a id="evidence-and-reading"></a>
## 5. Evidence and reading: follow a claim back to its location

The new derivation began on a pinned fact collection, with 3,157 claims and 164 sources selected from source task `task_01M51AQ0JK0MYN47806ZD5XS1B`. Its first recorded evidence stage reused 3,021 claims after that stage's selection, read zero new documents, ran zero new searches and copied zero criteria. These are different count scopes; do not replace one with the other.

The compact [source-facts.json](../examples/oral-multitarget/latest/source-facts.json) contains useful worked paths:

| Path | Actual retained record | What to inspect |
|---|---|---|
| Oral administration | `claim_01M52QZFZHBESVFSHMK8TX8AGV`, source DOI `10.1080/07853890.2026.2698360`, locator `sec2.3.p1` | Recorded source passage, Boolean route projection, original clinical context, and link to `rule_documented-oral-administration@v1`. |
| FGFR1 potency | `claim_supp_0fc07290141d48a811fe3d11`, source DOI `10.1038/s42004-023-01084-0`, locator `sec2.1.p1` | Saved `34 nM` value, measured basis, target/assay context, document/claim artifact refs and `span_checked_against_source`. |

These describe saved evidence; this tutorial does not newly retrieve or authenticate the publications. The FGFR1 record retains unknown ATP concentration, target-specific protein concentration and incubation time. A located quotation and `verification_status` answer different questions; preserve both.

[`reading.py`](../src/mas/core/reading.py) extracts located claims; [`evidence.py`](../src/mas/core/evidence.py) handles admission; [`existing_research.py`](../src/mas/core/existing_research.py) pins facts and source sequences. **Check:** candidate/target identity, basis, units, conditions, original passage/locator and source version survive projection. See [change evidence](#change-evidence) and [reference](components/evidence-and-reading.md).

<a id="criteria-and-review"></a>
## 6. Criteria and review: trace expansion, reduction and authority

Inspect [stages.json](../examples/oral-multitarget/latest/results/stages.json), [cqa.json](../examples/oral-multitarget/latest/results/cqa.json) and [source-cqa-history.json](../examples/oral-multitarget/latest/results/source-cqa-history.json). The initial criterion pool and registry were both zero. Six task-mandated criteria were recorded first. Four proposal dimensions expanded the active count to `293 → 504 → 1192 → 1917`. Three filter/distill/refine/merge rounds reduced it to `147 → 68 → 53` at their merge boundaries.

The resulting populations have distinct meanings: 53 active entries, 45 registered entries, 18 unique enabled decision rules and 13 contextual observations. The 18 rules serve six admission requirements and 17 scoring criteria, with five shared target criteria. Pending review overlaps registered criteria. Never sum those groups as disjoint populations or describe every historical item as a current rule.

[`derivation.py`](../src/mas/core/derivation.py) coordinates generation; [`derivation_stages.py`](../src/mas/core/derivation_stages.py) implements the actual stages; [`pool.py`](../src/mas/core/pool.py) records changes/parents; [`criteria.py`](../src/mas/core/criteria.py) and [`adjudication.py`](../src/mas/core/adjudication.py) check executable meaning and authority. The molecular-weight example retains its merge parents and a source-supported `500 Da` preference bound. HIA prediction remains deferred in this saved preparation; its row is not an enabled hard screen.

**Check:** each retained quantity has a definition, route, unit/basis, decision role, evidence and disposition. A merge needs one quantity and retained parents/reasons. See [hard/soft changes](#change-hard-soft) and [reference](components/criteria-and-review.md).

<a id="assessment-and-qualification"></a>
## 7. Assessment and qualification: turn evidence into a candidate decision

The saved Surufatinib [detail](../examples/oral-multitarget/latest/results/surufatinib.json) records all six eligibility requirements satisfied: one oral condition and five required direct target observations. The oral cell is `pass`, `value = true`, basis `derived`: this is a traceable Boolean projection from a clinical source. The target preferences order usable observations without adding unsupported potency cutoffs.

For FGFR1, the saved assessment is `available`, `7.6442605414788725 pChEMBL`, measured basis, with four source claims. The compact source-facts file shows selected supporting claims, not the full four-claim aggregate. This read-only example calls the production conversion on one saved claim:

```powershell
@'
import json, sys
from pathlib import Path
sys.path.insert(0, "src")  # Or use the installed project environment.
from mas.core.assessor import converted_claim
facts = json.loads(Path("examples/oral-multitarget/latest/source-facts.json")
                   .read_text(encoding="utf-8"))
original = facts["fgfr1_claims"][0]
converted, refusal = converted_claim(original, "pChEMBL")
assert refusal is None
print(original["value"], original["unit"])
print(converted["value"], converted["unit"])
print(converted["unit_conversion"]["value_as_reported"])
'@ | python -
```

Expected: `34 nM`, `7.468521082957745 pChEMBL`, and retained original value `34`. The single converted value differs from the saved four-claim aggregate by design. `converted_claim()` returns a copy; it does not change the input file or claim.

[`assess_cell()`, `direct_evidence()` and `qualification()`](../src/mas/core/assessor.py) apply evidence policy before qualification. A confirmed condition failure leads to Excluded. Completed assessments with partial admission support lead to Evidence incomplete; completed assessments with no admission support lead to Excluded. Unfinished work and tool errors retain an Assessment incomplete state. Predictions retain their basis and do not establish direct admission evidence. The human oral F% cell stays `unknown_missing`. **Check:** value, verdict, direct evidence and qualification agree, with missing/conflict/error/skipped states kept distinct. See [reference](components/assessment-and-qualification.md).

<a id="ranking-and-explanations"></a>
## 8. Ranking and explanations: explain the score after qualification

[`assessor.preference_scores()`](../src/mas/core/assessor.py) scores the qualified population; [`leaderboard.build_snapshot()`](../src/mas/core/leaderboard.py) preserves positions, qualification, coverage and reporting counts. Read [score-details.csv](../examples/oral-multitarget/latest/score-details.csv) and [score-details.json](../examples/oral-multitarget/latest/score-details.json) alongside the candidate detail. Follow each contributing criterion back through its assessment and claim refs.

The saved rank of 1 is among ten eligible candidates, with direct preference coverage `10/17`. The remaining candidates are **1,305 Evidence incomplete** and **1,862 Excluded for no admission support**. Their frozen qualification field remains `pending`; the current selection fields record the more specific decision and reason. Full sweep completion describes recorded evaluation work, not universal evidence completeness. Optional narrative/symbolic components have their own source and validation records; their explanations cannot replace the underlying assessments.

**Check:** use the same frozen rule set, eligible population, normalization, coverage floor and tie policy when comparing scores. A candidate-library change can change normalized ranks even for unchanged observations. See [reference](components/ranking-and-explanations.md).

<a id="execution-and-reuse"></a>
## 9. Execution and reuse: pick the right restart boundary

[`RunController`](../src/mas/core/controller.py) executes identity → assessment → snapshot; [`derivation_run.py`](../src/mas/core/derivation_run.py) records criterion-stage checkpoints. The workbench [`WorkflowManager`](../src/mas/ui/workflows.py) coordinates phases. Read [workflow.json](../examples/oral-multitarget/latest/results/workflow.json) for the terminal workflow and [overview.json](../examples/oral-multitarget/latest/results/overview.json) for both snapshots.

Resume continues a nonterminal run's committed work. Continuation creates a new run after a terminal result. Compatible cell reuse needs unchanged rule/attribute refs, routes, assessor and evidence/configuration policy. Fresh generation on existing evidence transfers selected facts and exact tool results; it starts with zero inherited criteria, critiques, adjudications, assessments or rank decisions.

**Check:** before a new generation, inspect `initial_pool_count = 0`, `initial_registry_count = 0`, `copies_existing_criteria = false` and the pinned evidence/tool manifests. After interruption, use the saved checkpoint instead of manually editing stage counts. See [agent-run guide](agent-run.md) and [reference](components/execution-and-reuse.md).

<a id="evaluation-and-recovery"></a>
## 10. Evaluation and recovery: compare the right scientific question

[`measurement.py`](../src/mas/core/measurement.py) records prospective comparison policy; [`recovery.py`](../src/mas/core/recovery.py) compares frozen criterion sets under declared exposure/equivalence judgments. The [original-CQA comparison](reference/cqa-comparison.md) concerns recovery of manuscript endpoints. The saved leaderboard concerns candidate qualification and ordering. They use different units and conclusions.

For the published run, [validation.json](../examples/oral-multitarget/latest/results/validation.json) checks export/workflow/snapshot consistency. Portable [verification.json](../examples/oral-multitarget/latest/reproduction/verification.json) records the production-engine replay result; inspect its actual status/differences and source digest. A code digest mismatch tells you the current implementation differs from the historical one even when fixed-result replay agrees.

**Check:** name the comparison: file integrity, fixed-result replay, independently generated criteria, candidate ranking, or recovery. Record failures and unknown states under that comparison. B/recovery measurement is a separate experiment and is not automatically repeated by a new generation. See [reference](components/evaluation-and-recovery.md).

<a id="domain-adapter"></a>
## 11. Domain adapters: bind a question to the right data

The saved task uses [`drug/registration.py`](../src/mas/adapters/drug/registration.py), adapter `drug_prioritization@1`. Local library identity, ChEMBL/GtoPdb activity, computed descriptors, literature and optional saved ADMET panels answer distinct questions. A learned ADMET estimate retains predicted basis. The [`clinical_routes.py`](../src/mas/adapters/drug/clinical_routes.py) projection creates the oral Boolean while retaining its underlying claim.

For carrier/general work, [`UploadedEvidence`](../src/mas/core/uploaded_evidence.py) binds exact uploaded IDs, properties, units, conditions and row hashes. Selecting a carrier entity does not give its particle-size observations the drug target vocabulary. **Check:** entity type, primary identity scheme, provider version, capability and observation basis match the intended domain. See [CSV customization](#change-data), [tool customization](#change-tool) and [reference](components/domain-adapters.md).

<a id="workbench-and-cli"></a>
## 12. Workbench and CLI: inspect the same records through different views

The workbench routes in [`workbench_api.py`](../src/mas/ui/workbench_api.py) and read projections in [`read_model.py`](../src/mas/ui/read_model.py) expose tasks, stages, evidence and complete candidate pages. CSV import lives in [`uploads.py`](../src/mas/ui/uploads.py). The standalone [`CLI`](../src/mas/cli/main.py) and [agent runner](agent-run.md) use the same scientific core but have different workflow entry points.

The interface defaults to English and can save a 中文 display choice. Research tasks, criteria, evidence, prompts and run records remain English while retaining original input/source text. Display-only collection labels live separately from scientific manifests. **Check:** the task/snapshot selected in the UI matches the exported IDs; count all pages/CSV rows when inspecting the full population. See [reference](components/workbench-and-cli.md).

## Customize the next experiment

Use a new workspace/output directory and new task identity for changes. Keep published `examples/**` and the restored reference task as comparison inputs. Copy [configuration examples](../config/examples/) into your workspace; do not edit a retained snapshot or write replacement values into its JSON. [Agent-run commands](agent-run.md) define how to run the prepared inputs.

<a id="change-objective"></a>
### Change the objective or required targets

In a new workbench task, replace the objective, targets and conditions. For example, this **synthetic task specification** illustrates a narrower question:

```text
Objective: Compare EXAMPLE-A and EXAMPLE-B for a carrier formulation study.
Required observations: particle_size in nm by DLS at 25 C in water.
Hard condition: particle_size <= 150 nm under those conditions.
Preference: higher cell_viability at 24 h, 10 ug/mL, in assay DEMO-CELL.
Evidence: uploaded synthetic demonstration data only.
```

These values teach input structure; they are not recommended scientific thresholds. State actual context and evidence for a real study. A changed target set needs its own evidence sufficiency review: pinned oral multi-target facts do not imply coverage of a new target.

**Verify:** normalized `objective_text`, original input, entity type, identifiers, property/unit/conditions and hard/preference roles. Resolve a required clarification before dependent execution. Expected outcome: a new task/version/binding, not a particular rank.

<a id="change-hard-soft"></a>
### Change a hard condition, preference, or cutoff

Change the task specification before generation when the decision requirement changes. In a developing task, a criterion edit must create a new attribute/rule version, fresh review and new freeze/evaluation. [`criteria.revise_for_workbench()`](../src/mas/core/criteria.py) accepts `changes = {"attribute": {...}, "rule": {...}}`, a reason and actor; it clears old authority and returns `requires_new_freeze = true`.

For a **synthetic, already valid size criterion**, the editable rule fragment is:

```json
{
  "rule": {
    "rule_kind": "preference",
    "predicate_form": "ordering",
    "cutoff": null,
    "cutoff_basis": "none_evidence_insufficient",
    "on_missing": "unknown_no_penalty",
    "on_conflict": "unknown_no_penalty",
    "on_inapplicable": "unknown_no_penalty"
  }
}
```

That fragment alone is not a full rule or API request. It illustrates replacing the decision role while retaining the criterion's quantity/direction/route. Supply a substantive scientific reason and use the criterion editor/new-task workflow. Editing JSON in an export performs no versioning or review.

**Verify:** the new role, direction, bound support, review disposition, enabled/deferred state, required anchors and new frozen refs. Re-evaluate affected cells and inspect qualification counts. High rejection can prompt diagnosis; changing a hard condition solely to obtain a desired candidate rank changes the study question.

<a id="change-data"></a>
### Replace candidate and measurement CSV files

Choose **Use own data**, select the domain and import candidates before observations. These files are **synthetic format examples**, with no scientific evaluation:

```csv
candidate_id,name,description
EXAMPLE-A,Example carrier A,Synthetic tutorial candidate
EXAMPLE-B,Example carrier B,Synthetic tutorial candidate
```

```csv
candidate_id,property,value,unit,basis,conditions,source,summary
EXAMPLE-A,particle_size,120,nm,measured,DLS; water; 25 C,Synthetic tutorial,Demonstration only
EXAMPLE-B,particle_size,170,nm,measured,DLS; water; 25 C,Synthetic tutorial,Demonstration only
EXAMPLE-A,cell_viability,92,%,measured,24 h; 10 ug/mL; DEMO-CELL,Synthetic tutorial,Demonstration only
EXAMPLE-B,cell_viability,85,%,measured,24 h; 10 ug/mL; DEMO-CELL,Synthetic tutorial,Demonstration only
```

Map columns in preview, resolve errors, then save. `candidate_id` is exact text; every measurement ID must exist in the selected library. Numeric values need units (`1` for dimensionless quantities); `basis` is one of `measured`, `curated`, `predicted`, `simulated`, `derived`. Preserve the actual basis. Omit missing observations; zero and `false` are valid. Corrections create a new content-addressed dataset identity. Current limits are UTF-8, 8 MB, 50,000 rows and 64 columns per file. See [CSV guide](csv-input.md).

**Verify:** preview row count, exact IDs, numeric/Boolean types, units/basis/conditions, source strings, new upload hash and selected library/measurement versions. A changed candidate population needs a new full leaderboard/coverage comparison; a changed measurement requires checking affected cells and normalization.

<a id="change-evidence"></a>
### Select or extend an evidence collection

For a pinned-evidence experiment, choose its collection explicitly and keep `evidence_mode = existing_only`. The collection's label/description/topics are editable display metadata in [`EvidenceCollections`](../src/mas/ui/evidence_collections.py); renaming it changes neither claims nor scientific coverage. Its `manifest_ref`, source task, claim/source counts and cutoff identify the evidence you actually selected.

For new observations, import a revised measurement dataset or use a new task with permitted literature/upload sources and retrieval enabled. Document uploads use a separate source manifest with source identity, access/license and LLM-ingestion permission; see [configuration](configuration.md) and [evidence reference](components/evidence-and-reading.md). Adding a source is a new evidence experiment; the portable capsule excludes full texts, so a saved document ref does not by itself make its bytes available.

**Verify:** counts basis (`pinned_fact_manifest` versus admitted task evidence), selected source ID/version, evidence cutoff, locator/quote/context and admission state. On `existing_only` misses, record the gap or supply a new evidenced dataset. Keep the earlier pending result for comparison.

<a id="change-tool"></a>
### Add or change a tool adapter

There is no runtime `tools.toml` or arbitrary import switch. Implement a provider's `ToolContract` and `invoke(question_kind, inputs) -> ProviderResponse`, register it in the composition root, and bind its capability/question kind in a domain route. Start with [the provider example](components/tools-and-providers.md#worked-example-a-local-provider), [`drug/registration.py`](../src/mas/adapters/drug/registration.py) or [`UploadedEvidence`](../src/mas/core/uploaded_evidence.py).

For a local experimental-size service, declare the exact identifier and conditions in required inputs, return the actual measurement with source/row identity, and label predicted output as predicted. Increment `implementation_version` when behavior changes; changing an output schema also needs a compatible contract version. Preserve data version, retrieval date, license, upstream refs and typed `empty`/absence/error outcomes. Update the executable criterion route as well as the capability declaration.

**Verify:** one representative known observation, one absent observation and any real failure mode introduced by the integration. Check identity mapping, unit/basis, source and broker manifest; confirm old replay keys do not masquerade as the changed implementation. Reuse relevant existing tests such as [drug adapter](../tests/test_drug_adapter.py) or [broker replay](../tests/test_broker_replay.py), adding a focused regression only for a new behavior. Then evaluate a small real input before a larger new run.

<a id="change-model-budget"></a>
### Change model roles, budget, workload, or concurrency

Copy [models.deepseek.toml](../config/examples/models.deepseek.toml) and [mas.toml](../config/examples/mas.toml) into your new workspace. Configure the provider's actual model/base URL and credential environment-variable/key-file path, then bind role names under `[roles]`. To send criticism to a separately configured provider, set `critic = "your_critic_provider"`; that provider must exist. Distinct names alone do not establish model independence. Consult the provider's current model/pricing documentation before a paid run.

For example, these ordinary TOML settings request a smaller **new experiment**:

```toml
[budget]
usd_max = 2.0
on_exhaust = "finalize_partial"
[assess]
workers = 2
[search]
volume = "mid"
[evaluation]
mode = "staged"
[evidence]
mode = "existing_only"
```

The browser/agent workflow also receives submitted workload/budget controls; inspect the effective configuration and new binding rather than assuming every standalone CLI setting controls every workflow. Provider prices/usage can leave cost unknown, and the final permitted call can cross a known spend cap. A USD envelope is not evidence of a free run or a guaranteed exact charge.

This pure configuration check uses no store or provider:

```powershell
@'
import sys
sys.path.insert(0, "src")
from mas.core import config
settings = config.resolve(project_file=None, environ={}, overrides={
    "budget.usd_max": 2.0, "assess.workers": 2})
print(settings.get("budget.usd_max"), settings.sources["budget.usd_max"])
print(settings.get("assess.workers"))
'@ | python -
```

Expected: `2.0 override`, then `2`. For complete editable files, use `config validate`, `config show --explain` and `models show` from the [configuration guide](configuration.md). They are configuration checks; a separately recorded small live run tests provider connectivity/behavior.

**Verify after execution:** new role/provider identities, actual settings layers, initial zero-CQA counts where requested, stage additions/merges/removals/reasons, terminal state, unresolved work, complete candidate export, cost status and qualified-population ranking. Compare with the pinned result as a scientific observation. A new model run may improve, worsen, defer criteria or stop on budget; preserve that outcome and use it to decide the next change.
