# Leaderboard Specification

Coordinating agent (drafting fork), 12 October 2026. Design only; no code. Component ids, record names, identifier prefixes, and vocabularies are those of `optimized_design.md` Section 0; record field lists are in its Sections 4.11, 4.12, 8.5, 8.6, and 9. This document specifies the leaderboard as the primary persistent output: task-scoped ranking, evidence-admission policy, candidate states, provenance, versioned updates, rank-change explanations, and the precision/coverage tradeoff. No entry, rank, or score below is a result; the two example entries use placeholder values and are labelled as such.

## 1. Purpose and position in the architecture

The leaderboard is a projection rendered by the Leaderboard Service (C12) over decisions it does not compute. Candidate states come from the Per-Candidate Assessor (C11) applying a confirmed rule-set version (`rules@v<n>`, owned by the Criterion Registry C10) to a frozen evidence snapshot (`evs_<task>_<n>`, owned by the Evidence Ledger C9). Every snapshot (`lb_<task>_<n>`) is an immutable artifact (C3) created by a `leaderboard.snapshot_published` event in the Event Journal (C1). The leaderboard therefore inherits the architecture's guarantees: nothing on it exists without a journaled cause, nothing on it is rewritten, and every material change links to a claim, a tool result, a human decision, or a rule change.

The leaderboard is also where the primary acceptance target is read: for the manuscript case, the question "was surufatinib admitted, under which rules, with which per-criterion reasons" is answered by a candidate entry and its assessment records, not by prose.

## 2. Task-scoped ranking

### 2.1 One leaderboard per comparable task context

Each leaderboard is a record `lbd_<task>_<k>` keyed by the task and its comparability key (the fields of §2.2); task-context versions that keep the key share it (design §4.12). Snapshots carry `task_context_id@v` as a mandatory field, and the Assessment Ledger carries it on every row, so cross-context aggregation is impossible by construction rather than by filter. Different diseases, endpoints, objectives, candidate universes, or constraint sets are different task contexts and are never merged into one ranking. The reference project's cross-run aggregation over all run directories under one goal profile is the behaviour this rule forbids.

### 2.2 Comparability of task contexts

Two task contexts are comparable (and therefore share a longitudinal leaderboard) only when all of the following match: `objective_text` (verbatim), `mode`, the set of `scope_entities[]` with `role: required`, the `candidate_universe` identity (same `kind`, `source`, and `as_of`, or a declared superset relation recorded as a universe version), `constraints[]` with `hardness: hard`, and `evaluation_scope.comparison_basis`. A change to any of these creates a new task context version (`task_x@v<n+1>`), and the old leaderboard is closed with a `supersedes` link rather than continued. Changes that do not break comparability and are recorded as versions within the same leaderboard: a new evidence cutoff (`evs_<n+1>`), a new confirmed rule-set version (`rules@v<n+1>`), a new strategy version (`strat@v<n+1>`), a human edit, or an evidence-refresh run. The task-input screen states which edits will open a new leaderboard before the user confirms them. The Continue dialog does the same for a run continuation (design §6.8).

### 2.3 What a leaderboard answers

For a user who enters a new objective: whether a comparable task context exists; the current qualified shortlist under the latest confirmed rules; each candidate's position, state, and reasons; and the sequence of snapshots with explained changes as evidence, rules, or decisions changed over time.

## 3. Evidence-admission policy

### 3.1 Precision first

A smaller defensible shortlist is preferred to a longer speculative one. `recommended` is reserved for candidates whose every applicable hard rule has a supported verdict backed by admitted claims of an acceptable kind, whose coverage clears the registered floor, and whose decision carries the independence level and human review the case configuration requires. No top-K quota exists; `admitted_n = 0` is a legitimate snapshot outcome with a stated reason.

### 3.2 The four-state evaluation table (binding, from C10)

| Evidence situation for a (candidate, rule) | `hard_exclusion` | `preference` | `exploratory_consideration` |
|---|---|---|---|
| admitted value satisfies predicate (`pass`) | passes | contributes per weight | recorded |
| admitted value violates predicate (`fail`) | candidate `rejected`, this rule as cause | contributes per weight | recorded |
| applicable, no admitted value of an acceptable kind (`unknown_missing`) | `unknown`; candidate capped at `provisional` | excluded from the sum; lowers reported coverage | recorded |
| applicability condition unmet (`inapplicable`) | not evaluated; denominator reduced; never a penalty | removed from the weight basis | recorded |
| two or more admitted claims of comparable standing oppose (`unknown_conflicted`) | `unknown`; mandatory review-queue item (`q_`) | excluded until resolved; conflict displayed | recorded |
| only a categorical determination for a quantitative attribute (`qualitative_only`) | `unknown` unless `predicate_form = qualitative_judgment` | only through a declared ordinal mapping with its own `cutoff_basis` | recorded |

Two prohibitions: no surrogate may stand in for a missing value inside a verdict (a surrogate is a separate attribute with its own rule), and no candidate is scored when every contributing attribute is `unknown_missing` or `inapplicable` (that candidate is `unassessed`).

### 3.3 Coverage gate

`hard_rule_coverage = applicable hard rules holding a value-bearing verdict (pass or fail) ÷ applicable hard rules` (rules with `inapplicable` verdicts are excluded from both numerator and denominator). `recommended` requires `hard_rule_coverage ≥ const_coverage_floor`. The floor is a registered constant in the case configuration (`const_` record with `scope: case_configuration`) and is included in the `evidence_admission_predicate_hash` of the rule-set version, so changing it requires an Expert Decision (`hd_`) and is never a promotable strategy change. Its value is a registered placeholder — to be set before evaluation.

### 3.4 Required independence level and human review

The case configuration declares, per candidate state, the minimum `independence_level` of the admitting decision (`none`, `heterogeneous_model`, `deterministic_plus_model`, `human_reviewed`) and whether an `hd_` reference is required. For the primary case, `recommended` requires `human_reviewed`. Independence is read from the decision's Independence Declaration (C7), never inferred from role names; a critique with `saw_proposer_rationale = true` or a same-model marker cannot raise the level.

### 3.5 Reason disqualifiers

An assessment whose Reason record (`rsn_`) fails any disqualifier is unpublishable and the candidate cannot be `recommended` on that rule: no `evidence_refs[]` and no absence check; sole reference is a model self-report, an LLM confidence statement, another agent's verdict, or a `provisional` memory item; a cited claim with `scope_match: out_of_scope` or `admission_state ≠ admitted`; unit mismatch without a normalization note; a hard exclusion resting on a `title_only` read or `not_searched` counter-evidence; text asserting a measurement where `determination_basis = predicted`; naming the disclosed reference outcome as justification; identical `evidence_refs[]` and `value` under differing verdicts across candidates. Legitimately shared reasons (a library-wide hard exclusion) carry a `reason_template_id` instead of being disqualified.

### 3.6 Abstention

A snapshot with no `recommended` entry carries `result_kind: no_recommendation` and one reason: `insufficient_coverage`, `all_candidates_excluded`, `unresolved_conflicts`, or `evidence_unavailable`. Abstention is counted in the reporting tuple (Section 7) so that an always-empty shortlist cannot trivially win any evaluation.

## 4. Candidate states and transitions

| State | Meaning | Entered when | Left when |
|---|---|---|---|
| `unassessed` | no applicable hard rule has an assessed verdict, or identity unresolved | universe intake; `name_match_ambiguous`; every contributing attribute `unknown_missing`/`inapplicable` | first assessed hard-rule verdict; identity resolved |
| `provisional` | assessed but not admissible: an `unknown_*` on a hard rule, coverage below the floor, missing independence level or required `hd_` | roll-up computes `n_unknown_hard > 0`, or coverage below floor, or `awaiting_human_review` | all hard rules `pass` with coverage and review satisfied (→ `recommended`); any hard-rule `fail` (→ `rejected`) |
| `recommended` | every applicable hard rule `pass`; coverage ≥ floor; no `unknown_conflicted` on a hard rule; at least one admitted claim per hard rule with `determination_basis` in the attribute's `acceptable_value_sources`; required independence level and `hd_` present | roll-up and C18 decision | new evidence or rule version produces a `fail` or `unknown_*` on a hard rule; human edit |
| `rejected` | at least one applicable hard rule `fail` with a supported verdict | roll-up | the failing rule is removed, revised, or its supporting claim is quarantined or superseded (→ re-assessment) |

Transition rules: every transition is a candidate change record (`chg_`) with `cause` set to a `claim_id`, `tool_result` id, `hd_`, or rule change record; a transition without a cause renders as a defect (`explanation_status: unexplained`). A changed hard exclusion can only move candidates between `recommended`/`provisional` and `rejected`; a changed preference weight can only reorder within one result kind. Exploratory considerations never change state. Reaching a budget limit leaves candidates `unassessed` or `provisional`, never silently resolved.

## 5. Result kinds and wording

Every snapshot states its `result_kind`:

- `all_pass_set`: the set of candidates with no hard-rule `fail` and no hard-rule `unknown_*`; `all_pass_count` is recorded. A unique all-pass candidate is reported as "the only candidate with no failing or unknown hard-rule verdict under `rules@v<n>` with coverage ≥ floor", together with `coverage_of_hard_rules`; a low-coverage uniqueness claim may not be worded unqualified.
- `ranked_under_score`: an ordering of candidates by the registered `ordering_method` (kind, weight vector, tie-break, owned by C10 and recorded on the snapshot). A top-ranked candidate is reported as "top-ranked under ordering method M at `rules@v<n>`", never as "the only" anything.
- `both_reported`: the all-pass set is the primary claim; the ranking is a secondary ordering of candidates, shown separately.
- `no_recommendation`: abstention with reason.

The historical manuscript result was a unique all-pass outcome under a binary funnel; the rebuttal wording must follow whichever result kind the actual run produces.

## 6. Snapshot record and per-candidate entry

### 6.1 Snapshot (`lb_<task>_<n>`)

Bound to: `task_context_id@v`, `run_id`, `round_id`, `rules@v`, `strat@v`, `evidence_snapshot_id` (`evs_`), `evidence_cutoff`, `result_kind`, `ordering_method`, `tool_availability_snapshot`. Contains: `all_pass_count?`, `candidate_entries[]`, `parent_snapshot_id`, `change_records[]` against the parent snapshot (the parent run's last snapshot within a run chain, otherwise the previous snapshot of the same task; design §6.8), `tool_coverage` per dimension (`n_measured`, `n_predicted_only`, `n_nothing`, `providers[]`), `reporting_tuple`, `interaction_estimate_provider` (for example `none`), `independence_level_summary`, `human_review_summary`, `outcome_dependence_report_ref?`, `published_at`, `projection_hash`, `journal_seq`. Snapshots are write-once; a correction is a new snapshot with a change record whose cause is the correcting decision.

### 6.2 Candidate entry

| Field | Content |
|---|---|
| `candidate_ref`, `identity_labels` | `cand_<identity>`; preferred label and identifier set from the identity service; `identity_link_basis` |
| `state`, `state_reason` | one of four states; the roll-up's reason (for example `hard_rule_unknown: attr_x@v`) |
| `position?` | only for `ranked_under_score`; absent for all-pass reporting |
| `relevance_to_objective` | which scope entities and constraints the candidate was assessed against |
| `per_criterion_refs[]` | one `asm_` per applicable rule, each with verdict, value, `value_kind`, `determination_basis`, reason, evidence refs, review state, `reuse.decision` |
| `coverage` | `hard_rule_coverage`, `n_fail_hard`, `n_unknown_hard`, `n_inapplicable` |
| `missing[]` | attributes with `unknown_missing` and the `absence_check_record` or tool absence reason behind each |
| `counter_evidence_refs[]` | conflicting claims and their disposition |
| `uncertainty_summary` | per-criterion uncertainty bands where a quantitative band exists; otherwise "no band" |
| `measured_vs_predicted_counts` | how many verdicts rest on `measured`/`curated` versus `predicted`/`simulated`/`derived` values |
| `provenance_summary` | `independent_support_count` over independence groups; `shared_experiment_groups` |
| `evaluation_completeness` | assessed ÷ applicable, all rule kinds |
| `review_status` | `none`, `requested`, `human_approved`, `human_rejected`, `disputed`; the approval slot shows an `hd_` reference or "no human review yet" |
| `reason_for_position_or_state` | the structured reason naming the decisive rules and the change record that last moved the candidate |
| `reused_vs_re_evaluated_counts` | per-criterion records reused from a prior snapshot (with fingerprint) versus newly evaluated |
| `independence_level` | from the admitting decision's declaration |

## 7. Reporting tuple and the precision/coverage/abstention tradeoff

Every snapshot (and every evaluation arm per task) emits one atomic tuple: `admitted_n`, `precision_among_admitted` (undefined and rendered as "undefined (admitted_n = 0)" when nothing is admitted; computable only with expert review or labels), `coverage_fraction` (candidates whose every applicable hard rule holds a value-bearing verdict, `pass` or `fail`, ÷ candidate universe, bound to the `hard_rule_coverage` denominator), `sweep_completeness` (attempted cells ÷ required cells in the bound `sweep_scope`; a cell holding `unknown_missing` counts as attempted, never as covered), `abstention_n_by_reason` (`unknown_missing`, `unknown_conflicted`, `not_assessed`), `incorrect_exclusion_rate?` and `unsupported_claim_rate?` (present only when an expert sample exists), `budget` (tokens by role, tool calls, wall clock, human-review minutes). Precision is never rendered without coverage and abstention from the same tuple. Raising the coverage floor moves candidates into `provisional`, which raises precision and lowers coverage; because the floor is inside the admission-predicate hash, that move is an expert decision, not a strategy improvement.

## 8. Tool coverage disclosure

Without an interaction-prediction backend, target-coverage values exist only for candidate–target pairs that curated sources document, so `unknown_missing` will be the most common verdict for most of a large library. Every snapshot therefore shows, per criterion dimension, how many candidates have a measured or curated value, how many have a prediction only, how many have nothing, and which providers supplied what; and it states `interaction_estimate_provider`. A snapshot that looks like a screen but is a lookup over a small annotated subset must read as such.

## 9. Versioned updates and rank-change explanations

### 9.1 What can change a leaderboard

| Driver | Enters as | Produces |
|---|---|---|
| new paper or database release | evidence-refresh run: new `run_`, same task context, new `evs_` | new snapshot with change records whose causes are the new `claim_` ids |
| corrected data (retraction, correction, superseding version) | source record update (`retraction_state`, `supersedes_source`) → claims `superseded` or `quarantined` → stale marks via C16 | re-assessment of dependents; change records with cause = superseding claim |
| tool output (new predictor run, optional backend arrival) | `tool_result` with provenance → claims with `value_kind: predicted` | change records; `tool_coverage` delta; never a state change on its own for a hard rule requiring measured values |
| expert decision | `hd_` on a rule version, claim admission, identity merge, candidate state | `rules@v<n+1>` or claim change; stale marks; Rerun Plan; change records with cause = `hd_` |
| experimental feedback | submission (`sub_`) → provisional claim → `hd_` admission | as for expert decision |

New evidence may raise, lower, remove, or leave a candidate unranked. Each change record carries `operation` (admit, exclude, demote, promote, unrank, rank_changed, status_changed, score_changed), `fields_changed[] {field, before, after}`, `cause`, `actor`, `at`, and `explanation_status`.

### 9.2 What never changes a state by itself

More citations for an already-supported claim (support is counted over independence groups, and a preprint plus its published version is one group); repeated copies of one underlying experiment; a higher preference score (ordering may change within a result kind, state may not); a stable winner across snapshots (stability is not accuracy); an agent's increased confidence; agreement among agent roles. Each of these appears, if at all, as a descriptive field, never as a `cause`.

### 9.3 Human edits

Human edits create new versions (`rules@v<n+1>`, `task_@v<n+1>`, or claim revisions) with attributed `hd_` records; earlier snapshots remain inspectable; the difference view shows criterion changes (added, modified, merged, split, removed, with before/after thresholds, units, applicability) and candidate changes (admitted, excluded, demoted, promoted, unranked, rank or score or status changed) each linked to its cause. A Rerun Plan from C16 states which assessments are stale, which rerun, and which are reused; the next snapshot labels each per-criterion record `reused` or `re_evaluated`.

### 9.4 Submissions do not become facts by being submitted

Expert feedback, uploaded files, local paths, and textual results enter through the submission lifecycle (`received → parsed → identity_resolved → review_pending → accepted_as_evidence | accepted_with_reservations | rejected | withdrawn`) as provisional claims with mandatory provenance, experimental context, units, and a negative-result direction; no evidence level is assigned on write; admission requires an `hd_` by a reviewer other than the submitter; only admitted claims can be a `cause`. Computational outputs stay distinguishable from experimental observations through `evidence_kind` and `determination_basis`.

## 10. Uncertainty and calibration

Where a quantitative uncertainty band exists on an admitted claim (interval, stated standard deviation), the per-criterion record carries it and the entry's `uncertainty_summary` reports it; a verdict near a cutoff shows the band beside the cutoff. Where only a model class probability exists, it is displayed as the model's score with its `data_version`, labelled "class probability, not calibrated risk" unless a calibration record from the Evaluation and Promotion Authority (C19) exists for that model version and domain. An LLM confidence statement is never shown as a reliability estimate: it is a self-report with no calibration set, no operating point, and no independence from the reasoning it describes; it is stored on the claim as `extraction_confidence` with that label and is excluded from every admission rule and metric.

## 11. Views and filters

| View | Content | Rule |
|---|---|---|
| Qualified shortlist | `recommended` entries | each shows the `hd_` reference and independence level; "no human review yet" when absent |
| Provisional tier | `provisional` entries with the blocking unknown or missing review named | separate from the shortlist; never summed with it |
| Not evidence-qualified | `unassessed` and exploratory candidates | labelled "not evidence-qualified"; no position shown |
| Rejected | `rejected` entries with the causing rule, claim, and change record | appealable: a rejection resting on a recalled exclusion lesson cites it |
| Candidate detail | all entry fields plus every per-criterion record, reason, evidence links, review state, reuse label | the per-compound page the acceptance target requires |
| Difference | `lb_<n>` versus `lb_<m>`: criterion changes and candidate changes with causes | unexplained material changes render as defects |
| Longitudinal | snapshots of one leaderboard (`lbd_`) over time with the rules, strategy, cutoff, and result kind of each; branches of a run chain shown as separate lines through `parent_snapshot_id` | no cross-task rows |

Filters: objective and scope entities (within one task), target coverage (per target), drug class or adapter-typed class, candidate source (universe, seed, human-added), rule-set version, evidence status (measured, predicted, missing), evaluation completeness band, review status, independence level, value kind per dimension, and any adapter-declared property. Filters never change a state; they select rows.

## 12. Illustrative entries (placeholders, not results)

The two entries below show field shape only. Values marked `⟨…⟩` are placeholders; the compound names appear in the case configuration as seed or universe members; no value is a measurement, prediction, or finding.

**Example A — a `recommended` entry (illustrative shape).**

| Field | Placeholder value |
|---|---|
| `candidate_ref` | `cand_⟨identity-key⟩` (preferred label: surufatinib; `identity_link_basis: exact_identifier_match`) |
| snapshot binding | `lb_⟨task⟩_1` · `rules@v1` · `strat@v1` · `evs_⟨task⟩_1` · `result_kind: both_reported` |
| `state` / `state_reason` | `recommended` / `all_hard_rules_pass; coverage ≥ floor; hd_⟨id⟩` |
| `position?` | shown only in the secondary ranking view: ⟨n⟩ of ⟨m⟩ assessed under ordering method ⟨M⟩ |
| per-criterion records | `attr_⟨dim1⟩@v1` pass · `value_kind: curated` · `evidence_refs: claim_⟨a⟩, claim_⟨b⟩` (two independence groups) · review `human_approved`; `attr_⟨dim2⟩@v1` pass · `value_kind: measured` · unit normalization note · review `human_approved`; `attr_⟨dim3⟩@v1` inapplicable · condition ⟨c⟩ unmet; `attr_⟨dim4⟩@v1` pass · `value_kind: predicted` · counter-evidence `claim_⟨d⟩` `found_and_outweighed` with basis ⟨…⟩ |
| `coverage` | `hard_rule_coverage ⟨k/k⟩`; `n_fail_hard 0`; `n_unknown_hard 0`; `n_inapplicable 1` |
| `missing[]` | none on hard rules; ⟨one⟩ preference attribute `unknown_missing` with absence check ⟨sources searched, date⟩ |
| `provenance_summary` | `independent_support_count ⟨g⟩`; `shared_experiment_groups ⟨h⟩` |
| `measured_vs_predicted_counts` | ⟨x⟩ measured/curated · ⟨y⟩ predicted |
| `review_status` | `human_approved` — `hd_⟨id⟩`, role ⟨expert role⟩, ⟨date⟩ |
| `independence_level` | `human_reviewed` (checks: deterministic_rule, cross_family_model_critique, human_expert_review) |
| `reason_for_position_or_state` | "no failing or unknown hard-rule verdict under rules@v1; decisive rules ⟨list⟩; last moved by chg_⟨id⟩ (cause hd_⟨id⟩)" |
| `reused_vs_re_evaluated_counts` | first snapshot: all `re_evaluated` |

**Example B — a `provisional` entry with an unknown hard rule (illustrative shape).**

| Field | Placeholder value |
|---|---|
| `candidate_ref` | `cand_⟨identity-key⟩` (preferred label: ⟨a universe member⟩) |
| `state` / `state_reason` | `provisional` / `hard_rule_unknown: attr_⟨dim1⟩@v1 (unknown_missing)` |
| per-criterion records | `attr_⟨dim1⟩@v1` `unknown_missing` · required value kind `measured\|curated` · tool results: `not_attempted` (`absence_reason: no_record_found`, providers ⟨p1, p2⟩) and `empty` · absence check ⟨sources, date⟩; `attr_⟨dim2⟩@v1` pass · `value_kind: predicted`; `attr_⟨dim4⟩@v1` pass · `value_kind: curated` |
| `coverage` | `hard_rule_coverage ⟨(k−1)/k⟩`; `n_unknown_hard 1` |
| `missing[]` | `attr_⟨dim1⟩`: no curated interaction record for ⟨target⟩; `required_inputs_manifest`: an interaction-prediction provider or a curated measurement |
| `review_status` | `none` — "no human review yet" |
| `independence_level` | `deterministic_plus_model` |
| `reason_for_position_or_state` | "capped at provisional by one unknown hard-rule verdict; would become admissible if a measured or curated value of ⟨dim1⟩ were admitted; open question `oq_⟨id⟩` registered (`consequential_missing_measurement`)" |
| `position?` | not shown (provisional entries are not ranked in the shortlist view) |

The second entry illustrates the expected shape of most entries on the no-CDES route: capped by missing measurements rather than excluded, with the missing measurement registered as an open question that could justify a targeted computation or an evidence-refresh run.

## 13. Invariants (checkable at publication)

1. Every snapshot has `task_context_id@v`, `rules@v`, `strat@v`, `evs_`, `result_kind`, `ordering_method`, `reporting_tuple`, `tool_coverage`, and a `journal_seq`.
2. Every `recommended` entry references an `hd_` where the case configuration requires one, has `n_unknown_hard = 0`, `n_fail_hard = 0`, coverage ≥ floor, and no disqualified reason.
3. Every state transition between snapshots has a change record with a non-null `cause`.
4. No row exists without a task context; no view sums entries across task contexts.
5. Precision is absent or marked undefined whenever `admitted_n = 0`; coverage and abstention are always present.
6. No field displays an LLM confidence statement as a reliability estimate.
7. `unassessed` and exploratory candidates never carry a position.
8. A unique all-pass claim is accompanied by `coverage_of_hard_rules`; a top-ranked claim names its ordering method.

Sources: `optimized_design.md` Sections 0, 4.10–4.12, 8.5, 8.6, 9, 16, 17; `agent_reports/evidence_and_policy.md` §3.2, §5, §6, §8 and its cross-review; `agent_reports/evaluation_and_improvement.md` Findings 7–9 and cross-review; `agent_reports/tools_and_data.md` Finding 8; `agent_reports/human_review_and_ui.md` §5.4–5.6; governing prompt §4.2.
