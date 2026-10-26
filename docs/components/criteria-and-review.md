# Criteria, pool evolution and review authority

[Practical walkthrough](../component-walkthrough.md#criteria-and-review) · [中文实操](../zh/component-walkthrough.md#criteria-and-review)

[Components](README.md) · [Evidence](evidence-and-reading.md) · [Assessment](assessment-and-qualification.md)

This subsystem converts research evidence into executable decision criteria without losing the proposals, disagreements and reductions that produced them. It implements the criterion-focused proposer–critic protocol (C7), criterion registry (C10), and the current machine/compatibility review paths of C18.


[Criterion-use terminology](../reference/decision-language.md#criterion-use) distinguishes decision rules, contextual observations and withheld work. The interface shows why each withheld item is absent from an evaluation; record retention and evaluation use are separate.

## Purpose and contract

MAS separates an **attribute**, which defines a measurement, from a **rule**, which gives that measurement decision semantics. One attribute might ask for median curated potency against a declared target in pChEMBL units. A rule can rank that value, compare it with a supported bound, or retain it as an exploratory consideration. A meaningful property does not automatically justify a hard exclusion threshold.

| Record | Defines |
|---|---|
| Attribute | Operational definition, measurement kind, unit, direction, acceptable evidence/bases, aggregation and evidence route(s) |
| Rule | Attribute version, rule kind, predicate, cutoff/basis, missing/conflict behavior and decision provenance |
| Pool item | Versioned candidate criterion with state, source claims, revisions and parent/child lineage |
| Review/adjudication | Subject version, findings, route, outcome and actual authority |
| Confirmed rule set | Executable entries and ordering method, pending/deferred/withheld items, authority and acceptance label |

[`criteria.py`](../../src/mas/core/criteria.py) owns `check_attribute`, `check_rule`, `propose`, `record_version`, `load` and `confirm_rule_set`. [`bound_support.py`](../../src/mas/core/bound_support.py) checks decision-bearing bounds and transform parameters against their stated sources and authority. `preference_execution_problems()` prevents a syntactically valid preference from entering scoring with no executable reduction or direction.

## Derivation mechanism and rationale

[`derivation.enumerate_dimension()`](../../src/mas/core/derivation.py) gathers evidence by research dimension. `objective_criteria()` uses adapter templates to bind requirements already in the task. `validate_proposal()` checks references, evidence compatibility and executable tool routes before a proposal can enter the registry.

The iterative path in [`derivation_run.py`](../../src/mas/core/derivation_run.py) opens a derivation run, records its inputs and stages, and uses [`derivation_stages.py`](../../src/mas/core/derivation_stages.py) to evolve the pool:

1. `propose()` expands candidate criteria from the dimension's evidence.
2. `filter_stage()` runs validator and critic checks and routes items needing work to refinement.
3. `distill_stage()` sharpens operational meaning while preserving provenance.
4. `refine_stage()` repairs flagged items within their bounded attempt budget.
5. `merge_stage()` asks whether compatible items measure one quantity or justify an explicit family consolidation.
6. `promote()` registers surviving proposals with their review state and source lineage.

The configured default order is filter → distill → refine → merge, repeated for bounded iterations. Refining before merge lets repaired items participate in that iteration's reduction. Stage records retain pool counts and decisions, including unchanged, refused, merged-away and deferred items. Target criterion counts are an effort goal; keeping meaningful independent criteria takes precedence over forcing a count.

[`pool.Pool`](../../src/mas/core/pool.py) records add, revise, state-change, merge and consolidate operations. `fold()` reconstructs current items and `trajectory()` exposes stage evolution. Revisions append versions rather than erasing a failed proposal. `reduce_pool()` and `reduce_registered()` can refine/consolidate already gathered criteria without a new literature search; [`existing_research.derive()`](../../src/mas/core/existing_research.py) can start with an empty pool over a pinned evidence bank.

## Duplicate measurements and family consolidation

Two database routes for the same quantity should support one measurement instead of contributing two independent votes. `quantity_key`, duplicate checks and route compatibility identify the operational quantity, unit, direction and subject. The merge path retains its parents' evidence/authority and refuses invented routes or citations. A family consolidation names what it subsumes and declares an aggregation the assessor can actually execute.

[`collapse.py`](../../src/mas/core/collapse.py) handles compatible duplicates already in the registry. It checks agreement of decision kind/predicate/cutoff, writes new attribute and rule versions, and preserves merged-away history. Its authority is recorded as software status. It does not decide a scientific disagreement between different cutoffs. `retire_rule()` and registry inventory functions preserve the distinction between inactive history and active scoring.

## Review and authority

[`adjudication.route_of()`](../../src/mas/core/adjudication.py) selects the applicable deterministic/model review route. `adjudicate()` and `adjudicate_open()` record machine decisions, supported bound interpretations, revisions, unresolved disputes and deferrals. Task constraints can be restated from their exact task authority; unsupported hard requirements remain open when they cannot be justified. [`review_attempts.review_once()`](../../src/mas/core/review_attempts.py) retains attempts so resume does not repeatedly buy the same unresolved review.

Machine decisions carry `approval_kind: agent_verdict` and `authority: machine_adjudication`. `confirm_rule_set()` labels machine-adjudicated/fitted/interpreted sets as exploratory and lists the applicable reasons. Pending hard conditions remain visible; current qualification cannot silently treat them as cleared. The modern workbench runs this machine path.

[`review.py`](../../src/mas/core/review.py) retains queue records and interactive human decisions for the compatibility CLI. `decide()` requires a human actor and interactive entry and records historical-list exposure. These are process guards; the release has no authenticated identity service protecting the function from a process with Python/filesystem access. Queue claims, full submission lifecycle and a modern browser human-approval workflow are not part of the shipped path.

## Failure semantics

An invariant failure raises `InvariantViolation` with a finding class. A pool item can remain `needs_refine` or `deferred_next_round`; exhausting repair effort preserves it rather than accepting it. A proposed merge may be refused or kept separate. Missing capability, unsupported bound, unclear interpretation and unresolved review are reported separately. Freezing a set retains exclusions/deferred routes and does not rewrite an unresolved review as approval.

## Worked example: two curations, one criterion

**Illustrative:** two proposals measure pChEMBL potency at the same target, one through ChEMBL and one through GtoPdb, both using the median with the same direction. A valid merge creates one attribute with both evidence routes, retains both source lineages and uses one rule. This increases evidence availability without doubling the preference's weight or the required-criterion denominator. If the rules disagree on a cutoff, deterministic collapse refuses the group; a recorded adjudication must resolve the decision semantics before a combined rule can score.

## Existing verification

[`test_criteria_pool.py`](../../tests/test_criteria_pool.py) covers stage order, bounded repair, duplicate detection, family aggregation, merge provenance and resumable proposals. [`test_registered_reduction.py`](../../tests/test_registered_reduction.py) checks reduction over registered criteria. [`test_adjudication.py`](../../tests/test_adjudication.py), [`test_bound_support.py`](../../tests/test_bound_support.py) and [`test_unresolved_review_freeze.py`](../../tests/test_unresolved_review_freeze.py) cover authority, supported bounds and pending reviews. [`test_criteria_export.py`](../../tests/test_criteria_export.py) checks reviewer-facing exports.
