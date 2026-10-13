# Workstream 1 — Evidence and Decision-Policy Audit

Design only; no implementation code. 12 October 2026. Audited against the coordinator brief, the
package prompt and brief, and a read-only inspection of `Agentic-Doping-snapshot` at `0007ad10`. All
field lists are proposals, not implemented behaviour.

## Summary

1. No **task-context record** sits between flexible user input and evidence requests; the reference
   code goes from goal text straight to a scoring vocabulary, leaving candidate universe, evidence
   cutoff, and reference-outcome disclosure unrepresentable.
2. Its "target contract" fuses attribute, direction, weight, and scoring shape into one object and
   **silently discards proposals outside a fixed property menu**. It cannot express a hard exclusion,
   an applicability condition, units, or missing-vs-failed.
3. `review_state: "approved"` is written by the distiller itself and the memory gate keys on it;
   `human_review_state` is an untyped dict. The three approval kinds are not separated in code.
4. Evidence strength is one ordinal tier plus an LLM self-report, and "multi-source" support is
   inferred from distinct cache keys — a preprint plus its published version raises confidence.
   Independence and shared-experiment marking do not exist.
5. There is no per-criterion assessment record, only numeric scores, so the acceptance target's
   per-criterion reason per compound has no home.
6. Missing values are handled honestly in scoring, then backfilled by surrogates and a proxy fallback
   that would admit under-assessed candidates.
7. Directly reusable: preserved typed failures, the prompt-inclusion audit and context manifest, the
   cached-extraction status taxonomy, the scientific-identity key, the bounded invariant-repair loop.
8. **Most important change:** replace the fixed-vocabulary target contract with a two-record Criterion
   Registry (*attribute* + *rule*, versioned, per-field provenance, explicit `cutoff_basis`), and make
   every candidate decision a per-criterion assessment record carrying a structured reason.

---

## 1. Task-context normalization (item a)

### 1.1 No task-context record exists, and mode handling must not fall back to keyword matching

**Issue.** The prompt requires normalizing objective text, desired properties, evidence/data, candidate
sets, seeds, and constraints into an explicit task context; none is specified in the package, and
`analyze_goal_llm(text, …)` takes goal text plus two domain strings and returns scoring targets
directly, so candidate universe, evidence cutoff, declared reference outcome, and unknowns have nowhere
to live. Its modes are `conditional`/`unconditional`, and its always-available analysis is a substring
keyword table (including localized keywords) that the LLM path falls back to on any failure —
transplanted, exploratory mode becomes a disease-keyword lookup and the fallback emits domain priors
with the authority of derived criteria.

**Source / location.** `START_HERE_Audit_and_Optimize_Prompt_EN.md:21,54`; `Project_Brief_EN.md:15-20`;
`objective_analysis/analyze.py:33-122,367-432,813-847,1110-1117`; `evidence_ledger/enums.py:57-59`.

**Importance.** High — downstream records need a task-context identity to be comparable, and a keyword
fallback is the likeliest route by which undocumented domain assumptions re-enter.

**Recommended change.** A Task Context Normalizer record:

| Field | Allowed values / form |
|---|---|
| `task_context_id`, `version`, `created_by`, `created_at`, `supersedes` | identity and lineage; a human edit creates a new version and marks downstream results stale |
| `mode` | `conditional`, `exploratory` |
| `objective_text` | verbatim as supplied, never rewritten |
| `intended_outcome` | `{statement, origin: user/agent_proposed, status: given/proposed/confirmed}` |
| `scope_entities` *(adapter)* | `{entity_kind, identifier, identifier_scheme, role: required/optional/questioned, provenance}`; holds the five targets as *case configuration* |
| `candidate_universe` | `enumerated_set`, `named_library`, `seeded_expansion`, `undetermined` + `{source, size_if_known, access_path, as_of}` |
| `seed_candidates` | `{candidate_ref, reason_supplied, is_reference_outcome: true/false}` |
| `constraints` | `{text, kind: administration/population/availability/regulatory/resource/other, hardness: hard/soft/unclear, provenance}` |
| `supplied_evidence` | `{artifact_ref, kind, submitted_by, submitted_at, admitted: pending/admitted/rejected, limitation_note}` |
| `unknowns` | `{question, blocking: yes/no, owner: agent/tool/human, resolution_state}` |
| `evaluation_scope` | `{comparison_basis: all_pass_rule_set/ranked_score/both, abstention_allowed: true, evidence_cutoff_at, tool_availability_snapshot}` |
| `missing_info_requests` | `{field, why_needed_for_meaning, asked_at, answer, answered_by}` |

Only `objective_text`, `mode`, `evaluation_scope`, and either a candidate universe or a seed set are
mandatory; the rest are explicitly `undetermined` rather than absent. `undetermined` blocks admission,
not execution; an unresolved `blocking: yes` unknown yields `unresolved`, never acceptance. Conditional
mode means a user-supplied candidate universe plus at least one constraint or scope entity; exploratory
means those arrive as `agent_proposed` and need human confirmation before a hard rule depends on them.
No keyword fallback in the core: if derivation cannot run the run ends `unresolved` with reason
`derivation_unavailable`. An adapter may ship *criterion templates* — attribute definitions with empty
cutoffs and required evidence kinds — as proposals, never pre-approved criteria.

**Tradeoff.** Heavier than three arguments, and removing the fallback means some runs produce nothing.

**Unresolved uncertainty.** Which fields are genuinely blocking for a "meaningful" task; and whether
exploratory mode may remove a user-supplied scope entity or only flag it.

---

## 2. The common criterion contract (item b)

### 2.1 Attribute and rule must be two records; the reference contract cannot express exclusion, units, or applicability

**Issue.** The brief separates attribute/CQA from rule and requires hard exclusions separable from
preferences and exploratory considerations. The inspected contract is one dict — `property`,
`goal_role`, `desired_trend`, `target_range_eV`, `weight`, `rationale`, `scoring_logic`, `computed_by`,
`literature_justification`, `evidence_level` — in which everything is a weighted preference: no rule
kind, no applicability condition, no units field (the unit is baked into the key name), and
`evidence_level` hard-set to `"E0"` regardless of support. A property outside the vocabulary is dropped
by a bare `continue`, unrecorded.

**Source / location.** `objective_analysis/analyze.py:680-750` (esp. `:690-691`, `:708`);
`excerpts/10_fixed_vocabulary_target_contract.py.txt:11-12,29`; `02_Agentic_Doping_Reference_EN.md:26`.

**Importance.** High — the acceptance target needs evidence-linked criteria with rationales plus a
binary all-pass reading; a weights-only contract expresses neither.

**Recommended change.** Two records.

*Attribute (CQA):* `attribute_id`; `name`; `definition` (one measurable quantity or one qualitative
determination); `rationale`; `measurement_kind` = `quantitative` | `ordinal` | `categorical` |
`qualitative_determination`; `unit` + `unit_system` (required when quantitative, else
`not_applicable`); `direction` = `higher_better` | `lower_better` | `within_range` | `target_value` |
`non_directional` | `undetermined`; `applicability_conditions` = `{condition_text, scope_kind,
evaluable_by: rule_engine/human, if_unmet: inapplicable/unknown}`; `acceptable_value_sources` (ordered
evidence kinds); `supporting_claim_refs`; `conflicting_claim_refs`; `status` = `proposed` |
`under_review` | `confirmed` | `deprecated` | `rejected`; `version`; `derived_from`;
`field_provenance` (§2.3).

*Rule:* `rule_id`; `attribute_ref` + version; `rule_kind` = `hard_exclusion` | `preference` |
`exploratory_consideration`; `predicate_form` = `threshold` | `range_membership` | `ordering` |
`categorical_membership` | `qualitative_judgment`; `cutoff` = `{comparator, value, unit}` | `absent`;
`cutoff_basis` = `measured_distribution` | `regulatory_or_standard_reference` | `source_stated_value` |
`expert_set` | `none_evidence_insufficient` (the last a legal publishable state); `uncertainty_range` =
`{low, high, basis}` | `absent`; `on_missing`, `on_inapplicable`, `on_conflict` = `unknown_no_penalty`
| `unknown_blocks_recommendation` | `route_to_human` | `exclude` (`exclude` only for `hard_exclusion`,
only with a human decision reference); `weight` (preferences only); `applies_to_result_kind` =
`all_pass_set` | `ranked_score` | `both`; `status`; `version`; `confirmed_by`.

Never silently drop a proposal: an attribute the adapter cannot evaluate stays `proposed` with
`non_evaluable_reason` = `no_measurement_available` | `no_tool_adapter` | `unit_unresolved` |
`requires_expert_determination`, reported as a known limitation. This generalizes the reference
project's `noted_uncomputable` list — the right idea applied to too narrow a set.

**Tradeoff.** Two records double the registry surface and need a join for display; fusing them makes
the hard/soft distinction unrepresentable.

**Unresolved uncertainty.** Whether `qualitative_determination` attributes may carry hard exclusions
(expert dependency, §10).

### 2.2 Missing, inapplicable, conflicting, and qualitative are four states needing a declared table

**Issue.** The package requires missing and inapplicable to stay distinct from failed but gives no
semantics. In the reference scorer an unavailable value yields `desirability = None` and is then either
replaced by a surrogate retaining full weight or, if nothing is computable, by an average of cheap
proxies; conflict reaches no decision at all, though a per-paper `conflict` flag exists upstream and is
carried into the role projection.

**Source / location.** `evaluation_cascade/scoring.py:199-265`; `literature/models.py:34-35,44-46`;
`literature/visibility.py:169-170`; `Project_Brief_EN.md:32`; `00_coordinator_brief.md:48`.

**Importance.** High — without this table "fail" silently absorbs three other states.

**Recommended change.** One table, binding on all components:

| State | Definition | `hard_exclusion` | `preference` | `exploratory_consideration` |
|---|---|---|---|---|
| `supported_pass` | admitted value satisfies predicate | passes | contributes per weight | recorded |
| `supported_fail` | admitted value violates predicate | `rejected`, this rule as cause | contributes per weight | recorded |
| `missing` | applicable, no admitted value from an accepted source kind | `unknown`; capped at `provisional` | excluded from the sum; lowers reported coverage | recorded |
| `inapplicable` | an applicability condition is unmet | not evaluated; denominator reduced; never a penalty | removed from this candidate's weight basis | recorded |
| `conflicted` | two or more admitted claims of comparable standing oppose | `unknown` + mandatory human-queue item | excluded until resolved; conflict displayed | recorded |
| `qualitative_only` | only a categorical determination for a quantitative attribute | `unknown` unless `predicate_form = qualitative_judgment` | only via a declared ordinal mapping with its own `cutoff_basis` | recorded |

Two prohibitions follow: no surrogate may stand in for a `missing` value inside a criterion's verdict
(a surrogate is a different attribute and must appear as one), and no candidate may be scored when
every contributing attribute is `missing` or `inapplicable` — that candidate is `unassessed`.

**Tradeoff.** Many candidates will sit `unassessed`, which looks less productive than the reference
project; the brief prefers this.

**Unresolved uncertainty.** "Comparable standing" needs an operational rule; I propose equal source
status plus distinct independence groups, but ranking source statuses is an expert dependency.

### 2.3 Provenance is per-record, not per-field, and one ordinal tier does four jobs

**Issue.** `Provenance` is `{kind, ref, at}` with `kind` an unconstrained string whose allowed values
exist only as a trailing comment, attached to the whole candidate record rather than the field it
justifies. Evidence strength is the ordinal `EvidenceLevel` E0–E4, whose rungs mix method with
confirmation (abstract/LLM prior; schema-valid; local rule or single surrogate model; external holdout
or multi-model agreement; first-principles or wet-lab), where the brief lists ten orthogonal evidence
*kinds* and separately requires independence markers.

**Source / location.** `evidence_ledger/models.py:23-26,48-60`; `evidence_ledger/enums.py:12-20`;
`schemas/ledger_record_v1.json` `$defs.Provenance.kind`; `00_coordinator_brief.md:50,64`.

**Importance.** High — "a successful tool call does not validate a claim" is unenforceable while one
ordinal mixes "computed by a cheap rule" with "independently confirmed".

**Recommended change.** Four axes on every value and criterion field: `evidence_kind` (the brief's
ten-value closed list); `determination_basis` = `measured` | `predicted` | `asserted` | `derived` |
`absent`; `independence_group` (§4.3); `scope_match` = `direct` | `conditional` | `analogous` |
`out_of_scope` | `unknown` — the reference transfer-scope rank is a good existing instance of this axis
and should be kept as a pattern. Give each criterion field its own `{field_name, actor_kind:
agent/tool/human/adapter_default, actor_id, at, source_refs, supersedes}` entry, and promote
`Provenance.kind` to a closed enum defined once (§9.2).

**Tradeoff.** Multiplies record size and UI complexity; without it nobody can tell which parts of a
criterion an expert actually set — exactly what the rebuttal must show.

**Unresolved uncertainty.** Whether a composite ordinal should be derived for sorting without
re-introducing the conflation (leaderboard workstream).

---

## 3. Rule lifecycle (item c)

### 3.1 Lifecycle operations, confirmation, and propagation are named but unspecified

**Issue.** The package requires add/revise/merge/split/remove with reasons and sources, expert
confirmation creating a confirmed version, and propagation to inclusion and ordering. Nothing in the
inspected code versions a criterion set; the closest primitive is `knowledge_identity`, a five-part
scientific identity key that refuses to merge records across host, site, dopants, property, or
direction — the right mechanism, unused for criteria.

**Source / location.** `literature/quality.py:687-695`; `objective_analysis/analyze.py:698-750`;
`START_HERE…:56`; `03_Provided_Rebuttal_Draft_EN.md:9,20-21`.

**Importance.** High — the rebuttal's central claim is a recorded rule-evolution history.

**Recommended change.** One **criterion change record** per operation: `change_id`; `operation` =
`add` | `revise` | `merge` | `split` | `remove` | `reinstate`; `targets` (ids and versions in/out);
`reason_kind` = `new_evidence` | `conflict_resolved` | `redundancy_detected` |
`unit_or_direction_error` | `applicability_narrowed` | `cutoff_unsupported` | `expert_instruction` |
`scope_change`; `reason_text`; `source_refs` (claim refs; required for every reason kind except
`expert_instruction`); `proposed_by`; `critiqued_by`; `arbitration_outcome` = `accepted` | `rejected` |
`unresolved`; `human_decision_ref` (required for any transition into `confirmed`);
`effective_from_version`; `affected_candidates`; per affected candidate a `restage_action` =
`reassess_required` | `reusable_unchanged` | `newly_applicable` | `newly_inapplicable`.

Identity rules: `merge` requires equal definition, unit-normalized direction, and value source kinds,
using the `knowledge_identity` tuple pattern as the equality test; `split` requires each child to name
a distinct applicability set or measurement; `remove` must record whether the attribute was
*unsupported* or *superseded*, since only the first is a finding about the historical CQA list (§8).
Propagation: a rule-version change marks all assessments under the prior version `stale`, retains them
append-only, and re-derives candidate state. A changed `hard_exclusion` can only move candidates
between `recommended`/`provisional` and `rejected`; a changed `preference` weight can only reorder
within one result kind, and must emit a rank-change explanation naming the change record.

**Tradeoff.** Full restaging on every weight tweak is expensive; reassessing only candidates whose
verdict for the touched attribute is non-`inapplicable` is cheaper but needs a staleness proof.

**Unresolved uncertainty.** Whether a human may confirm a rule version while some criteria remain
`conflicted`.

### 3.2 Unique all-pass and top-ranked are not distinguished, and the reference leaderboard merges task contexts

**Issue.** The historical result is a unique all-pass compound under a binary funnel, which the package
insists differs from a top-ranked compound under a score. The reference leaderboard has one result kind
— a sort by `(failed, -evidence_rank, -score, ratio_error)` — and `leaderboard_all` aggregates the
latest record of every candidate across *all* run directories and rescores them under one chosen goal
profile: the universal ranking the brief prohibits.

**Source / location.** `evidence_ledger/leaderboard.py:78-90,211-233`; `START_HERE…:80`;
`03_Provided_Rebuttal_Draft_EN.md:27`.

**Importance.** High — publishing a ranking where the claim is "unique all-pass" misstates the result,
and cross-objective aggregation makes any such statement unreproducible.

**Recommended change.** Snapshots carry `result_kind` = `all_pass_set` | `ranked_under_score` |
`both_reported`; for `all_pass_set` also `all_pass_count` and the `rule_set_version` evaluated; for
`ranked_under_score` the ordering method and weight vector. Require `task_context_id` on every ledger
and snapshot row so cross-context aggregation is impossible by construction, not by filter. Where both
are reported, the all-pass set is the primary claim and the ranking a secondary ordering of it. Report
`coverage_of_hard_rules` beside any uniqueness claim.

**Tradeoff.** Two result kinds complicate UI and wording; collapsing them produced the criticism being
rebutted.

**Unresolved uncertainty.** Whether a low-coverage all-pass candidate may be called "the only all-pass
compound" unqualified.

---

## 4. Evidence ledger and the source-agnostic workflow (item d)

### 4.1 Two ledgers are needed; the inspected "evidence ledger" is a candidate-state ledger with no claim links

**Issue.** `LedgerRecord` holds `candidate_id`, `ir_version`, `status`, `evidence_level`, numeric
`scores`, artifact paths, failure reason/detail, a provenance list, an untyped `human_review_state`,
`next_action`, `updated_at` — no claim, criterion reference, rule-set version, task context, or
evidence cutoff. "Latest" is decided by string comparison of ISO timestamps with `>=`, so equal
timestamps resolve by file order.

**Source / location.** `evidence_ledger/models.py:48-60`; `evidence_ledger/ledger.py:45-51`;
`excerpts/09_evidence_ledger.py.txt:24-29`.

**Importance.** High — an evidence-linked rationale needs a claim-level ledger the candidate ledger
references.

**Recommended change.** Separate a **Claim Ledger** from the **Assessment Ledger** (§5.1), the second
referencing the first. Claim record: `claim_id`; `source_ref`; `location` (§4.2); `claim_text` with a
`verbatim`/`paraphrase` marker; `normalized_statement`; `entities` (adapter-typed, with identifier
scheme); `scope` = `{population_or_system, conditions, measurement_context}`, each marked
`stated`/`inferred`; `evidence_kind`; `determination_basis`; `value`; `unit`; `unit_as_reported`;
`normalization_applied`; `direction_or_verdict`; `uncertainty` = `{form:
interval/sd/qualitative/absent, value}`; `polarity` = `supports` | `conflicts` | `inconclusive`,
relative to a named attribute; `independence_group`; `reading_depth` = `title_only` |
`title_abstract` | `full_text` | `supplementary` | `not_read`; `extraction_actor`;
`extraction_confidence` (labelled a model self-report, not a reliability estimate); `admission_state` =
`pending` | `admitted` | `quarantined` | `rejected` | `superseded`, plus `admission_reasons`;
`supersedes`. Keep latest-wins but order by `(sequence_number, updated_at)`; retain the existing
tolerance for crash-truncated lines.

**Tradeoff.** A large new artifact duplicating part of a paper cache; without it, "evidence-linked
rationale" degrades to a citation list.

**Unresolved uncertainty.** Whether polarity is stored per attribute (my proposal, more rows) or once
per claim and interpreted at read time.

### 4.2 Reading depth is tracked; exact passage locations and source status are absent

**Issue.** The required workflow is title screening, title-and-abstract screening, and full-text
reading, with exact locations for important claims and a recorded limitation when full text is
unavailable. The reference code records reading depth per claim (`source_kind`, default `"abstract"`),
keeps screening decisions for every fetched item, and reports a shortfall rather than padding — but
`PaperClaim` has **no locator field at all**, and source status is absent (`venue` is a free string;
nothing marks peer-reviewed versus preprint versus database entry). Its strongest asset here is the
cached-extraction status taxonomy (`current_good`, `current_no_doping_claims`, `legacy_good`,
`retryable_failure`, `mock_extraction`, `insufficient_source`, `not_useful`,
`invalid_current_provenance`, `legacy_low_quality`) with `reread_needed` and `prompt_safe` flags.

**Source / location.** `literature/models.py:17-55,82-83`; `literature/quality.py:374-473`;
`Project_Brief_EN.md:96-100`.

**Importance.** High — a rebuttal citing sources without passage locations cannot be checked, which is
the criticism being answered.

**Recommended change.** Source record: `source_id`; `identifiers` = `{scheme:
doi/pmid/accession/url/internal, value}`; `title`; `authors`; `issued_date`; `container`;
`source_status` = `peer_reviewed_paper` | `preprint` | `database_entry` | `technical_report` |
`curated_measurement` | `model_prediction_record` | `experiment_record` | `expert_statement`;
`version_label`; `supersedes_source`/`superseded_by_source`; `retraction_state` = `none` | `corrected`
| `retracted` | `expression_of_concern` | `unknown`; `access_state` = `full_text_available` |
`abstract_only` | `metadata_only` | `paywalled` | `fetch_failed`, plus `access_checked_at`;
`duplicate_of`.

Location record, required on any claim used by a `hard_exclusion` or quoted in a published rationale:
`{location_kind: page/section/table/figure/paragraph/record_field/line_range, locator_value,
quoted_span, span_checked_against_source: true/false}`. When `access_state` is not
`full_text_available`, `reading_depth` must be `title_only` or `title_abstract` and the assessment
carries `limitation_kind: full_text_unavailable`; no component may describe such a read as full text.
Reuse the existing status taxonomy and `prompt_safe` gate as the mechanism.

**Tradeoff.** Verified spans for hard exclusions are slow and will often route to a human; the
alternative is unverifiable exclusions.

**Unresolved uncertainty.** Whether `span_checked_against_source` can be met by a deterministic string
match in retrieved text or needs a human check per claim.

### 4.3 Independence and candidate identity have no representation

**Issue.** The distiller labels an entry `evidence_tier: "multi_source"` and adds a fixed `+0.05`
confidence whenever two distinct `cache_key`/`doi`/`title` values appear in its grounding — satisfied
by a preprint plus its published version, by two papers reporting one experiment, and by a review
citing a primary study; nothing records duplicate or shared-experiment relationships. Separately the
identity parser extracts element symbols with a narrow regex and whitelist, while the package itself
records that the supplied GDSC table has no match for the surufatinib aliases checked — an
ambiguous-name failure.

**Source / location.** `literature/quality.py:24-52,611-684` (esp. `:653-657`);
`04_Source_Inventory_EN.md:20-22`; `00_coordinator_brief.md:64`; `Project_Brief_EN.md:100`.

**Importance.** High — inflated independent support is how "more citations" becomes "better evidence",
and an unresolved alias either splits one candidate into two rows or misattributes a claim.

**Recommended change.** `independence_group`: `group_id`; `basis` = `same_underlying_experiment` |
`same_dataset` | `same_cohort_or_sample` | `same_model_run` | `shared_authorship_only` |
`assumed_distinct`; `member_claim_refs`; `determined_by`; `evidence_for_grouping`. Support counts are
computed over groups, never claim or source rows; `assumed_distinct` is a visible default, not a
confirmation; any replication bonus is forbidden unless two groups are not `assumed_distinct`;
preprint/published pairs collapse to one group via `supersedes_source`. Replace the fixed bonus with a
reported `independent_support_count`.

`candidate_identity` (adapter-owned): `candidate_id`; `preferred_label`; `identifiers` = `{scheme,
value, scheme_authority, as_of}`; `aliases` = `{alias, alias_source, alias_kind:
code/brand/synonym/salt_form/transliteration}`; `identity_link_basis` = `exact_identifier_match` |
`authority_crosswalk` | `name_match_single_candidate` | `name_match_ambiguous` | `unresolved`;
`merge_history`; `identity_review_state`. A claim may ground an assessment only on an identifier match
or authority crosswalk; `name_match_ambiguous` routes to the human queue and the claim stays `pending`;
merging rows is human-confirmed with its own change record. Salt and formulation differences are
aliases, not separate candidates, unless an attribute's applicability depends on them.

**Tradeoff.** Grouping is partly judgment and identifier-only admission rejects literature naming only
a trade name — both raise expert load.

**Unresolved uncertainty.** Detecting shared experiments across differently worded papers is unsolved
in the inspected code; I treat it as an expert dependency. Canonical identifier authorities are a
tools-workstream decision.

### 4.4 Two routes drop sources from the evidence context unrecorded, defeating the selective-literature check

**Issue.** The prompt-assembly path audits omissions well in one respect: blocks are packed atomically,
each catalog entry carries `included_in_prompt`, `prompt_char_count`, and `omitted_reason`, and a
context manifest persists the block hash, prompt hash, and included source ids. But two filters run
*before* the catalog is built, so their omissions never appear: per-role ACL denial (`deny` wins in
`visible_to`) and the prompt-safety gate, which returns `None` and causes a `continue`.

**Source / location.** `literature/visibility.py:143-171,232-293,296-334`;
`literature/cache.py:614-622`; `objective_analysis/analyze.py:900-950,1037-1055`.

**Importance.** High — this manifest is the only credible defence against a selective-literature
accusation, and two of its blind spots are the ones an accuser would ask about.

**Recommended change.** Build the catalog first, from the unfiltered source set, and extend
`omitted_reason` with `acl_denied_for_role`, `extraction_not_prompt_safe`, `no_structured_claims`,
`budget_exceeded`, `superseded_by_newer_version`, `duplicate_of_included_source` — recording fact and
reason without content where hiding is intended. Persist an **evidence visibility manifest** per
decision (actor and role, task context, criterion or candidate under assessment, catalog size,
included ids, excluded ids with reasons, content hash) and surface `conflicting_sources_excluded`
separately. Make it a publication gate: a decision publishes only if the manifest exists, every
`conflicts`-polarity claim for the attributes involved is included or individually excluded with a
reason, and the conflicting-to-supporting ratio is reported. Add a `search_coverage_record` per
evidence request (queries, source families, date range, result counts, retrieval failures, whether the
requested minimum was met) — the gap-discovery excerpt already records `fetch_failed` per gap and the
report already carries `shortfall`.

**Tradeoff.** Counter-evidence retrieval per attribute multiplies search cost, and logging ACL denials
partly defeats per-role information hiding.

**Unresolved uncertainty.** Whether per-role ACL denial is desirable here at all (MAS-architecture
workstream).

---

## 5. Per-candidate assessment and reasons (item e)

### 5.1 There is no per-criterion assessment record; the acceptance target requires one

**Issue.** The acceptance target requires every candidate to receive a per-criterion record of
evidence, measured/predicted/missing value, pass/fail/unknown, and a concise reason. The reference
representation is `ScoreBreakdown` — eleven optional floats and a total — plus a per-property dict
inside the scorer's return value (`value`, `desirability`, `weight`, `trend`, `surrogate`,
`relative_to_host`) that is not persisted. There is no verdict field, no evidence link, and no reason
anywhere.

**Source / location.** `evidence_ledger/models.py:29-60`; `evaluation_cascade/scoring.py:227-241`;
`00_coordinator_brief.md:18-19`.

**Importance.** High — this record *is* the deliverable the rebuttal promises for the five-target case.

**Recommended change.** Assessment record, one per `(candidate, attribute_version, rule_version,
task_context, assessment_run)`: `assessment_id`; `candidate_ref`; `attribute_ref` + version;
`rule_ref` + version; `verdict` = `pass` | `fail` | `unknown_missing` | `unknown_conflicted` |
`inapplicable` | `not_assessed`; `value`; `unit`; `determination_basis`; `value_source_claim_refs`
(required unless `determination_basis = absent`); `conflicting_claim_refs`; `uncertainty`;
`applicability_evaluation`; `reason` (§5.2); `assessed_by` (agent/tool/human + id + model or tool
version); `assessed_at`; `tool_result_ref` or `tool_error_ref`; `staleness` = `current` |
`stale_rule_version` | `stale_evidence` | `superseded`; `human_override_ref`.

Candidate roll-up: `hard_rule_coverage` (assessed / applicable), `n_fail_hard`, `n_unknown_hard`,
`n_inapplicable`, `state` = `recommended` | `provisional` | `unassessed` | `rejected`, `state_reason`,
`blocking_unknowns`. Any hard-rule `fail` implies `rejected`; any hard-rule `unknown_*` caps at
`provisional`; `recommended` additionally requires a coverage floor set in the case configuration, not
the core.

**Tradeoff.** For a 3,171-compound library and a dozen criteria this is tens of thousands of rows per
snapshot; most are `not_assessed` and can be stored sparsely against an explicit default.

**Unresolved uncertainty.** Whether rows are materialized for the whole library or only for candidates
reaching assessment.

**Revised after cross-review:** `staleness` needs a fourth value, `stale_by_human_edit`, distinct from
`stale_rule_version`, so WS5's S8 edit-propagation scenario can separate the two causes.

### 5.2 "Reasonable reason" needs an operational definition with disqualifiers

**Issue.** The acceptance target and the rebuttal both rest on "reasonable" rationales, but nothing
defines the term, so a fluent paragraph would satisfy it. The reference code gets partway there by
requiring a claim to carry mechanism, result, or significance before entering durable memory, and by
overwriting model prose about scoring logic with the implementation's own description.

**Source / location.** `literature/quality.py:496-555`; `objective_analysis/analyze.py:711-714`;
`00_coordinator_brief.md:18,50-52`.

**Importance.** High — the acceptance criterion most open to being met rhetorically.

**Recommended change.** A reason is a record, not prose. Required fields: `verdict_restated` (an enum
value, so the text cannot disagree with the verdict); `attribute_ref` and `rule_ref` with versions;
`evidence_refs` (at least one admitted claim, or `determination_basis: absent` plus an
`absence_check_record` naming which source kinds were searched and when); `value_and_unit_as_used` with
`unit_normalization_note` when converted; `applicability_statement`; `counter_evidence_disposition` =
`none_found` | `found_and_outweighed` (with basis) | `found_and_unresolved` | `not_searched`;
`cutoff_basis` inherited from the rule; `uncertainty_statement`; `reason_text` (generated last,
constrained to restating the above).

A reason is invalid — and the assessment unpublishable — if: it has neither `evidence_refs` nor an
`absence_check_record`; its only reference is a model self-report, an LLM confidence statement, another
agent's verdict, or a `provisional` memory row; a cited claim's `scope_match` is `out_of_scope` or its
`admission_state` is not `admitted`; it cites a unit differing from the rule's without a normalization
note; a hard exclusion rests on a `title_only` read or on `not_searched` counter-evidence; the text
asserts a measurement where `determination_basis = predicted`; it names the known reference outcome as
a justification (§6.3); or it is identical across candidates whose cited claims differ.

**Tradeoff.** Less readable than a paragraph; the UI can render the fields into a sentence, as the
reference code already does for scoring logic.

**Unresolved uncertainty.** The disqualifier list should be pressure-tested against real criteria before
being frozen.

---

## 6. Automated checks and admission policy (item f)

### 6.1 Cutoff provenance and registry invariants: reuse the existing repair loop, replace what it checks

**Issue.** The package requires checks for arbitrary thresholds, duplicate criteria, inconsistent
units, and weak exclusions. The inspected code carries undocumented decision constants —
extraction-confidence floors of `0.45` (stated) and `0.70` (inferred), an analogy cap of `0.55`, the
`+0.05` replication bonus with a `0.95` ceiling, an injectability floor of `0.45`, a primary-weight
floor of `0.45` and cap of `0.70`, a composition tolerance of "one percentage point or 25 % relative" —
none distinguishable in the record from a scientific cutoff. Conversely `_goal_semantics_issues` is the
right *shape*: it audits a model analysis against measurement invariants (property identity, registered
direction, role labelling, weight hierarchy) without goal keywords, feeding a bounded three-attempt
repair loop that falls back to a guardrail rather than accepting a bad analysis.

**Source / location.** `literature/quality.py:162,173-216,532-534,541,653-657,687-695,710-714`;
`objective_analysis/analyze.py:128-130,175-212,215-282,761-810`; `START_HERE…:58`.

**Importance.** High — the criticism being rebutted *is* undocumented thresholds, and these are the
checks a reviewer will run against the revised manuscript.

**Recommended change.** Register every numeric constant affecting a published verdict: `constant_id`;
`scope` = `core_policy` | `adapter_policy` | `case_configuration`; `value`; `unit`; `cutoff_basis`
(same enum as rules); `set_by`; `set_at`; `sensitivity_tested` (yes/no + protocol ref). Then four
registry invariants, each producing a typed critique artifact, never a silent correction.
*Arbitrary cutoff* — fail any rule whose `cutoff` is present while `cutoff_basis` is `expert_set`
without a `human_decision_ref`, or `none_evidence_insufficient` with a populated value; flag two rules
on one attribute whose cutoffs differ by less than their own `uncertainty_range`.
*Duplicate* — flag as merge candidates two attributes whose `(definition_normalized, unit_normalized,
direction, acceptable_value_sources)` tuple matches, or whose verdicts agree on more than a configured
share of assessed candidates, reporting the overlap; use the `knowledge_identity` tuple pattern and an
ordered exact-phrase normalizer, never substring matching.
*Units* — every quantitative attribute needs `unit` and `unit_system`, every cutoff needs the
attribute's unit or a recorded conversion, and a unitless cutoff on a quantitative attribute is a hard
validation failure. *Weak exclusion* — a `hard_exclusion` fails review if its `cutoff_basis` is
`source_stated_value` from a single independence group, or its claims' `scope_match` is `analogous`, or
it would reject more than a configured share of the universe while resting on `predicted` values. Keep
the bounded-repair pattern: failed invariants return to the proposer, at most N revisions, then
`unresolved` — never silent acceptance.

**Tradeoff.** Registering engineering constants alongside scientific ones is noisy; `scope` keeps review
effort where it matters, and verdict-agreement duplicate detection needs enough assessed candidates to
mean anything.

**Unresolved uncertainty.** The overlap share that triggers a merge proposal; I recommend merges are
only ever proposed, never applied automatically.

### 6.2 Admission must be coverage-gated; preserved failures are the reference project's strongest pattern

**Issue.** Policy is precision-first, with a valid empty recommended set and no top-K quota. The
reference scorer defeats this twice: it substitutes a surrogate desirability for a missing value while
keeping full weight, marked only by a boolean, and when no target is observable at all it scores the
candidate on an average of cheap proxies so it "still ranks"; weight-based coverage is computed and
reported but gates nothing. Failure preservation, by contrast, is done well — a typed `FailureReason`
enum with nineteen classes, failures appended never deleted, failed rows sinking but visible, a bounded
loop preserving `completed`/`killed`/`exhausted` — yet *criterion* proposals get none of it: an
attribute outside the vocabulary vanishes at a bare `continue`.

**Source / location.** `evaluation_cascade/scoring.py:199-265`; `evidence_ledger/enums.py:33-54`;
`evidence_ledger/leaderboard.py:81-90`; `objective_analysis/analyze.py:690-691`; `START_HERE…:58`;
`Project_Brief_EN.md:58`.

**Importance.** High — surrogates and proxy fallbacks are the most direct route to a long speculative
shortlist.

**Recommended change.** `recommended` requires: every applicable `hard_exclusion` verdict `pass`;
`hard_rule_coverage` at or above a case-configured floor; no `unknown_conflicted` on any hard rule; and
at least one admitted claim per hard rule whose `determination_basis` is in the attribute's
`acceptable_value_sources`. Failing only coverage yields `provisional`; no assessed criteria yields
`unassessed`, visible only in a separate exploratory view labelled not evidence-qualified. Surrogates
are allowed only as separate attributes with their own rules and `cutoff_basis`; the proxy fallback is
removed. An empty recommended set renders with a reason = `insufficient_coverage` |
`all_candidates_excluded` | `unresolved_conflicts` | `evidence_unavailable`. Extend failure
preservation to criterion proposals with `rejection_reason` = `no_evidence` |
`single_non_independent_source` | `unit_unresolved` | `duplicate_of` | `out_of_scope_for_objective` |
`not_measurable_with_available_sources` | `expert_rejected` | `conflicting_evidence_unresolved` |
`superseded_by`, retained at `status: rejected` and shown in the rule-history view. Map the loop
outcome `exhausted` to `unresolved` consistently; the progress note already flags that the trace API
renames it.

**Tradeoff.** The primary case may yield an empty or single-entry recommended set with a large
`provisional` tier; the brief treats that as a correct outcome and a finding.

**Unresolved uncertainty.** The coverage floor is a case-configuration value and an expert dependency; I
deliberately propose no number.

### 6.3 Dependence on the known case outcome needs a mechanical firewall, not a norm

**Issue.** Surufatinib is a disclosed reference outcome that must not become a hard-coded answer. The
reference project has the right idea in its strategy-content guardrails — rejecting candidate
identities, observed score thresholds, and scientific conclusions disguised as reusable methods — and
in keeping run outcomes out of durable lessons; those cover memory, not criterion derivation.

**Source / location.** `02_Agentic_Doping_Reference_EN.md:21` (the package's description of excerpts 06
and 08, which I did not read directly); `00_coordinator_brief.md:20-21`; `Project_Brief_EN.md:24`.

**Importance.** High — criteria derived with the answer in view make the case result uninterpretable.

**Recommended change.** (i) Record the disclosure once, in `seed_candidates[].is_reference_outcome`.
(ii) Derive criteria in a **reference-blind configuration**: derivation agents' evidence context
excludes claims whose only subject is the reference candidate, with the exclusion counted in the
visibility manifest. (iii) An automated check scans every definition, rationale, cutoff, and reason
text for the reference candidate's identifiers and aliases, failing the entry if found outside an
explicit comparison artifact. (iv) Record `derivation_configuration` = `reference_blind` |
`reference_disclosed` | `outcome_informed_exploratory` on every criterion version; only
`reference_blind` versions may support an acceptance claim, and `outcome_informed_exploratory` must be
labelled wherever it appears. (v) Emit an `outcome_dependence_report` per snapshot: leave-one-out, how
many hard rules would change the reference candidate's verdict if each were removed, without tuning.

**Tradeoff.** Blinding forfeits legitimate information in the manuscript's own literature and may lower
historical-CQA recovery; the leave-one-out report recovers some diagnostic value.

**Unresolved uncertainty.** Full blinding is probably unachievable because the objective text and
five-target configuration themselves narrow the space toward the known compound; the design should say
so rather than claim blindness.

---

## 7. Interface for domain-expert judgment (item g)

### 7.1 The reference code writes its own `approved`, and the human-review field is untyped

**Issue.** The brief separates agent verdict, software status field, and human scientific approval, and
forbids inferring the third from the first two. In the inspected code the distiller emits
`"quality_status": "eligible", "review_state": "approved", "evidence_kind": "literature"`, and the
injection gate admits exactly `review_state in {"approved", "verified"}` — so an LLM-distilled entry
self-certifies into the state the gate treats as approved, while the candidate record's human review is
an untyped `Optional[dict]`. The memory layer does render `PROVISIONAL` versus `APPROVED` in prompts, so
the vocabulary exists; the authority boundary does not.

**Source / location.** `literature/quality.py:611-684` (esp. `:681-684`), `:698-714`;
`evidence_ledger/models.py:58`; `objective_analysis/analyze.py:996-1012`; `00_coordinator_brief.md:52`;
`02_Agentic_Doping_Reference_EN.md:32`.

**Importance.** High — the clearest instance in the inspected code of the exact conflation the brief
forbids; it would silently invalidate the rebuttal's human-review claim.

**Recommended change.** Three disjoint fields, never interchangeable: `agent_verdict` = `proposed` |
`critiqued` | `revised` | `arbitrated_accept` | `arbitrated_reject` | `unresolved` (agent-writable);
`pipeline_status` = `pending` | `validated_schema` | `computed` | `failed` | `stale`
(software-writable); `expert_decision` (writable only through the Human Review Queue). Automated gates
may reference the first two only; publishing a `recommended` candidate or a `confirmed` rule version
must reference `expert_decision` and nothing else.

*Expert decision record:* `decision_id`; `queue_item_ref`; `subject` = `attribute_version` |
`rule_version` | `rule_set_version` | `claim_admission` | `candidate_state` | `identity_merge` |
`conflict_resolution` | `unit_correction` | `cutoff_setting`; `decision` = `approve` |
`approve_with_edits` | `reject` | `defer_more_evidence` | `escalate` | `abstain`; `edits` (field-level
before/after); `reason_text` (required except for approving an unedited proposal); `expert_identity`
plus `identity_basis` (authenticated account / recorded attestation); `declared_scope_of_expertise`;
`decided_at`; `sources_consulted`; `confidence_qualifier` = `stated_certain` | `stated_tentative` |
`not_stated`; `supersedes`; `downstream_invalidation` (computed stale assessments).

*Queue triggers (expert decision required before publication):* any `hard_exclusion` entering
`confirmed`; any cutoff with `cutoff_basis: expert_set`; any `unknown_conflicted` on a hard rule; any
`name_match_ambiguous` identity; any attribute merge or removal; any unit normalization that changes a
verdict; any `expert_statement` or unreviewed-preprint claim used by a hard rule; any `recommended`
publication; any `outcome_informed_exploratory` criterion version. *Proceeds automatically (recorded,
reversible):* retrieval, screening, extraction, duplicate detection, inapplicability evaluation,
preference-weight proposals, exploratory-consideration additions, and assessment recomputation after a
confirmed rule change.

**Tradeoff.** Plausibly dozens of decisions for the primary case, making throughput depend on expert
availability; the alternative is an unsubstantiable human-review claim.

**Unresolved uncertainty.** Whether one named expert suffices for a `hard_exclusion`, and how to
represent expert-versus-expert disagreement — I propose retaining both and leaving the rule
`unresolved`.

---

## 8. Historical eleven CQAs as a comparison reference (item h)

### 8.1 Intake record and recovery comparison, both typed and firewalled

**Issue.** The eleven CQAs are not listed in the manuscript main text, while the acceptance target
requires recovering most of them; without an intake record the comparison is unfalsifiable, and
informally pasting the authors' list into a derivation prompt would seed generation with the answer.
The brief also asks for the comparison to be recorded as recovered with evidence-backed rationale /
merged / split / removed with reason / newly added, with no format given.

**Source / location.** `00_coordinator_brief.md:18-21,76`; `01_Concept_Overview_EN.md:17`;
`03_Provided_Rebuttal_Draft_EN.md:21`; `START_HERE…:31`.

**Importance.** High — the first acceptance criterion cannot be evaluated without both records, and
this is the artifact that will be quoted in the rebuttal.

**Recommended change.** *Historical criterion intake record*, in the case configuration, flagged
`comparison_reference_only`: `intake_id`; `provided_by`; `provided_at`; `provenance_form` =
`manuscript_main_text` | `manuscript_supplement` | `author_supplied_list` | `reconstructed_from_code` |
`verbal_report`; `verbatim_items` (ordered, each `{label, definition_as_given, dimension_as_given,
threshold_as_given, unit_as_given, direction_as_given, notes}`); `completeness_attestation` =
`complete` | `partial` | `unknown`; `ambiguities` = `{item_ref, question, resolved_by, resolution}`;
`access_restriction: visible_to_comparison_agent_only`. Firewall: readable only by the comparison
component and the review queue, excluded by construction from every derivation agent's context, with
that exclusion asserted per derivation decision (`historical_criteria_excluded: true`).

*Recovery comparison record*, one per historical item plus one per unmatched derived attribute:
`comparison_id`; `historical_item_ref`; `derived_attribute_refs` (zero or more); `mapping_kind` =
`recovered_equivalent` | `recovered_with_narrower_applicability` | `recovered_with_different_cutoff` |
`merged_into` | `split_into` | `not_recovered_no_evidence` | `not_recovered_out_of_scope` |
`deliberately_removed` | `newly_added_not_in_history`; `match_basis` = `definition_and_unit_match` |
`definition_match_unit_differs` | `verdict_agreement_on_assessed_candidates` |
`expert_judged_equivalent`; `agreement_evidence` (candidates where historical and derived rules agree,
disagree, or cannot be compared); `rationale_refs`; `reason_text`; `judged_by` (comparison agent id
plus an expert decision ref whenever `match_basis` is `expert_judged_equivalent`); the derived
version's `derivation_configuration` (must be `reference_blind` for an acceptance claim). Per-snapshot
summary: `n_historical`, `n_recovered`, `n_merged`, `n_split`, `n_not_recovered`, `n_newly_added`, each
with ids. A `not_recovered_no_evidence` item is a statement about the historical criterion's
documentation, not a system failure, and must be worded that way.

**Tradeoff.** A strict firewall makes the comparison purely post-hoc and unable to help the agents —
that is the point, and iterating against it must be labelled `outcome_informed_exploratory`.

**Unresolved uncertainty.** Whether the authors can attest `complete`; if not, "most of the historical
CQAs" must be restated as a fraction of a partial list. Also whether "recovers most" is measured on
item count or decision impact — I recommend reporting both.

---

## 9. Reuse versus redesign in the inspected code (item i)

### 9.1 Reuse/redesign inventory

**Issue.** The package asserts reusable patterns without separating transferable mechanism from
materials-specific policy.

**Source / location.** Row locations below; repo `Agentic-Doping-snapshot` at `0007ad10`.

**Importance.** High — this is the handoff to the architecture and tools workstreams.

| Element | Location | Verdict | Why |
|---|---|---|---|
| Append-only JSONL ledger; failures never deleted | `ledger.py:22-51` | Reuse as pattern | Crash-tolerant trail; add sequence numbers, task-context keys |
| Typed `FailureReason`; failures preserved, visibly sunk | `enums.py:33-54`; `leaderboard.py:81-90` | Reuse, repopulate | Mechanism right, values materials-specific |
| Prompt-inclusion audit; whole-block packing | `visibility.py:296-334` | Reuse as design | Best defence against selective-literature claims |
| Context manifest with block/prompt hashes, source ids | `analyze.py:900-950,1037-1055` | Reuse as design | Proves what the model could see |
| Cached-extraction status taxonomy; `prompt_safe` | `quality.py:374-473` | Reuse as pattern | Near the required limitation record |
| Scientific identity key refusing cross-subject merges | `quality.py:687-695` | Reuse as pattern | Becomes the duplicate-criterion test |
| Ordered exact-phrase metric normalizer | `quality.py:173-216` | Reuse as pattern | Correct name normalization |
| Transfer-scope ranking | `visibility.py:24-31,52-76` | Reuse as pattern | Becomes `scope_match` |
| Invariant audit + bounded repair, then guardrail | `analyze.py:215-282,761-810` | Reuse as pattern | The critic loop the registry needs |
| Aggregate-claim suppression; per-source attribution | `visibility.py:88-127`; `quality.py:611-631` | Reuse as pattern | Stops one row bypassing per-source provenance |
| Weight-based coverage reported separately | `scoring.py:252-254` | Reuse as pattern | Right instinct; must gate admission |
| Shortfall reported not padded; all screenings kept | `literature/models.py:82-83` | Reuse as pattern | Precision-first already present |
| Fixed vocabulary, silent drop of unknown proposals | `analyze.py:690-691`; excerpt 10 | Redesign | Loses open-ended proposals unrecorded |
| Fused target object; `evidence_level` hard-set `E0` | `analyze.py:698-710` | Redesign | No rule kinds, applicability, units; support not derived |
| Single ordinal `EvidenceLevel` E0–E4 | `enums.py:12-20` | Redesign | Conflates method, confirmation, validation |
| `review_state: "approved"` written by the distiller | `quality.py:681-684,698-714` | Redesign (urgent) | Software-assigned approval read as approval |
| `human_review_state` untyped; `Provenance.kind` free string | `models.py:23-26,58` | Redesign | Must be typed once |
| Multi-source tier from cache keys; `+0.05` bonus | `quality.py:653-657` | Redesign | Counts duplicates as independent |
| Surrogate and proxy fallback keeping full weight | `scoring.py:222-228,257-265` | Redesign | Admits under-assessed candidates |
| `CandidateStatus` as pipeline stages | `enums.py:22-30` | Redesign | Needs the four decision states |
| `leaderboard_all` across runs, one profile | `leaderboard.py:220-233` | Redesign | Prohibited universal ranking |
| Keyword goal table and rule-table fallback | `analyze.py:33-122,1110-1117` | Do not transfer | Smuggles undocumented priors |
| Claim has no passage locator | `literature/models.py:38-55` | Redesign | Locations required for important claims |
| `useful is not True` blocks grounding | `quality.py:476-493` | Redesign | A screened-out source cannot ground a conflict |

**Tradeoff.** The redesign column is longer, which may read as rejecting the reference project; the
honest reading is that its *mechanisms* transfer well while its vocabularies and scoring policies are
materials-specific by design, as the package's own limits section says.

**Unresolved uncertainty.** I did not inspect the orchestration, web, harness, or flywheel packages, so
run-level reuse judgments belong to the MAS-architecture workstream.

### 9.2 Controlled vocabularies are duplicated and have already drifted

**Issue.** `FailureReason` in `evidence_ledger/enums.py:40` includes `chemically_invalid`; the published
`schemas/ledger_record_v1.json` `$defs.FailureReason` does not. Two copies, one stale.

**Source / location.** `evidence_ledger/enums.py:33-54`; `schemas/ledger_record_v1.json`
`$defs.FailureReason` (compared directly in this session).

**Importance.** Medium — small here, but the proposed design adds many controlled vocabularies, and
drift between a validator and a published schema would undermine every audit built on them.

**Recommended change.** One vocabulary registry as the single source: `vocabulary_id`; `version`;
`values` (each with definition and `introduced_in_version`); `deprecations`. Schemas, validators, and UI
labels are generated from it; every persisted record carries the vocabulary version it was written
against; a check fails any persisted value absent from that version.

**Tradeoff.** Extra build machinery for a design-phase project.

**Unresolved uncertainty.** None material.

---

## 10. Named expert dependencies (no biology proposed here)

Each surfaces as a review-queue item using the §7.1 record: (1) which attributes may carry hard
exclusions at all; (2) every cutoff and its `cutoff_basis`, including whether evidence supports a number
or only a range, and whether a qualitative determination may exclude; (3) applicability conditions per
attribute and what `inapplicable` means for the objective; (4) relative standing of source statuses and
what makes conflicting claims "comparable"; (5) independence grouping where shared experiments or
datasets are suspected; (6) candidate identity equivalence across salt forms, formulations, codes, and
ambiguous names; (7) unit and endpoint normalization across heterogeneous measurement contexts; (8) the
hard-rule coverage floor for `recommended`, and whether predicted values may ever satisfy a hard rule;
(9) equivalence judgments in the recovery comparison; (10) whether the five-target configuration is a
constraint or a questioned hypothesis in a given case configuration.

---

## Cross-review of evaluation_and_improvement.md

WS5's determination — containment engineering in the inspected code, no measurement — is consistent
with everything I inspected independently.

**1. Agreements.**
- F6: the `uses` counter measures circulation, not benefit — the same error class as the LLM
  self-reported `confidence` my §2.3 bars from being a reliability estimate.
- F5: content policy must belong to the *store*, not the caller — structurally identical to my §4.4
  finding that pre-catalog filters produce invisible omissions; its candidate-universe and
  outcome-reference scans are my §6.3 check (iii), so build one implementation.
- F7: precision is undefined at `admitted_n = 0` and must be emitted atomically with coverage and
  abstention — the reporting form my §6.2 gate needs.
- F10 item (2), the admission-predicate invariant, is the peer report's strongest proposal.
- F11: describe the prior art narrowly — matches my §9.1 split row for row.
- F12: the evaluation authority must not own criterion approval — my §7.1 three-field separation.
- F3's exclusion of role agreement as progress, and F2's `memory_mode ∈ cold|frozen|warm`.

**2. Objections.**
- **F8, artefact location.** WS5 stores the historical list *in the Criterion Registry* with
  `visibility = evaluator_only`, making the blind an access-control property of the store the deriving
  agents read. That is the failure I documented at `literature/cache.py:614-622` and
  `literature/visibility.py:251,272-274`, where a per-role `deny` is the only barrier and denied items
  vanish from the audit. Alternative (my §8.1): the intake record lives in the **case configuration**,
  outside the registry, readable only by the comparison component.
- **F8, proof form.** "Access logged, so the event journal can prove no deriving run read it" proves
  only that no read occurred *through the logged interface*; the inspected code had two unlogged drop
  paths (my §4.4). Require the positive assertion `historical_criteria_excluded: true` in each
  derivation decision's visibility manifest, not an absence of log entries.
- **F8, categories.** Their `recovered` collapses what my §8.1 separates as
  `recovered_with_different_cutoff` and `recovered_with_narrower_applicability` — a criterion
  recovered at a different cutoff is not the same claim, and that is what the rebuttal turns on.
  Their `removed` omits my §3.1 split of *unsupported* from *superseded*. Adopt my enum, folding in
  their rule-role match field.
- **F9, expected state.** Pre-registering `Expected state ∈ recommended|provisional` for the known
  reference outcome writes the answer into the case register, against their own F10 item (4) and my
  §6.3 firewall. Alternative: register the decisive criteria *to be reported* and the recording rule
  for every outcome, with no expected state; my §6.3 leave-one-out report supplies the diagnostic
  that field was reaching for.
- **F2, evaluator kind.** `evaluator_kind ∈ human_expert|rule_based|llm_judge` is admissible only with
  my §7.1 constraint stated on it: a non-human evaluator record may never be written to
  `expert_decision`.

**3. Interface conflicts and resolutions.**
- *Historical-CQA artefact* — relocate out of the Criterion Registry into case configuration; keep
  their logging and scoring; add the positive exclusion assertion.
- *Two-stage pre-registration (F9's uncertainty, addressed to me)* — compatible, and I confirm it.
  Stage 1, before derivation, registers rule *semantics*: `rule_kind`, `predicate_form`, the permitted
  `cutoff_basis` set, the three on-state policies, `applies_to_result_kind`, and the §6.2 coverage
  floor. Stage 2, on expert confirmation and before any assessment row, registers the concrete
  `attribute_version` and `rule_version` ids. Their "criterion version" is my `rule_set_version`;
  their `protocol_id` joins my `confirmed_by`.
- *F12's seam (a strategy change disguised as a criterion change)* — resolve by typing, not by
  committee. No `reason_kind` in my §3.1 criterion change record can carry a retrieval, review, or
  tool-selection change, and their `change_class` enumerates those; so a change bearing a
  `change_class` may not be written as a criterion change record. Compute their
  `evidence_admission_predicate_hash` over named fields of mine — `acceptable_value_sources`, the
  three on-state policies, the permitted `cutoff_basis` set, and the coverage floor — so any movement
  in the hash is mechanically a policy change needing expert approval. That closes the seam.
- *Conflict-state vocabulary* — their `open`/`resolved`/`irreducible` versus my `unknown_conflicted`
  verdict: keep their conflict record as a separate object linked from my `conflicting_claim_refs`,
  with `irreducible` mapping to an expert `abstain`.
- *De-duplication (F3)* — "source identity not text" still counts a preprint and its published version
  as two; de-duplicate by my §4.3 `independence_group`. In P0+ best-of-*n* (F1), apply my §5.2
  disqualifier or the arm rewards reason elaboration.

**4. Dependencies.** My §6.2 coverage floor and §2.1 `acceptable_value_sources` become inputs to their
admission-predicate hash; if adopted I would add `admission_predicate_version` to the rule record so
the hash has a stable referent. My §6.3 `derivation_configuration` becomes a manifest field, and if
`memory_mode` is adopted a reference-blind derivation must run `cold` or `frozen` — otherwise a warm
provisional row carries the answer forward, their F5 risk crossed with my firewall. Their S5 and S8
scenarios consume my §5.1 record unchanged.

**5. Proposed resolutions.**

| Topic | My position | WS5 position | Resolution | Confidence |
|---|---|---|---|---|
| Historical-CQA artefact | Case-configuration intake record | In Criterion Registry, `evaluator_only` | Relocate; keep their log and scoring | High |
| Proof of blinding | Positive per-decision assertion | Absence of log entries | Assertion, log as corroboration | High |
| Recovery categories | Nine-value `mapping_kind` | Six categories | My enum + their role-match field | High |
| Surufatinib expectation | No expected state | Prespecified expected state | Register criteria and recording rules only | Medium-high |
| Pre-registration staging | Semantics, then ids | Policy, then criterion version | Compatible as stated above | High |
| Strategy/criterion seam | Typing rule + predicate hash | Seam flagged, deferred to me | Adopt the typing rule | Medium-high |
| Evaluator kinds | `expert_decision` human-only | Three kinds in manifest | Keep field, add write constraint | High |
| Replication counting | Independence groups | Source identity | Independence groups | High |

---

## Contribution record

**Agent identity as known to me.** Workstream 1, "Evidence and Decision-Policy Auditor", a subagent
launched by this audit's coordinating agent; running as Claude Fable 5.1 (`claude-fable-5-1`) under
Claude Code. No numeric subagent identifier was supplied to me.

**Start / end.** Main report: start 2026-10-12T13:04:53+00:00, end 2026-10-12T13:31 UTC (both from the
system clock in this session). Two earlier drafts exceeded the word bound and were rewritten; the
session was then interrupted by a usage limit, and the coordinator accepted the report at 7,108 words
with no further trimming. Cross-review wave: 2026-10-12T17:12:59+00:00 to 2026-10-12T17:21 UTC,
roughly eight minutes, of which the peer read was the larger part.

**Cross-review.** Read in full, once:
`/home/yiwei3_duke/anny/mas/design_audit/agent_reports/evaluation_and_improvement.md` (Workstream 5,
333 lines), at 17:13 UTC, md5 `678a50f427913f19a65712d2c5e394db`. That file's checksum changed twice
over the next three minutes, so WS5 was still editing it; my review reflects the 333-line version I
read and not any later addition. I did not edit the peer file and did not
re-verify its code citations against the repository — where I dispute a WS5 proposal I cite my own
session's reads, not theirs. I appended the `## Cross-review of evaluation_and_improvement.md` section
above and one `Revised after cross-review:` line under §5.1; no other earlier finding was altered.

**Output file written** (the only file written outside the session scratchpad):
`/home/yiwei3_duke/anny/mas/design_audit/agent_reports/evidence_and_policy.md`. Scratch note:
`<session scratchpad>/ws1/citations.txt`.

**Package files read in full.** `/home/yiwei3_duke/anny/mas/design_audit/agent_reports/00_coordinator_brief.md`;
and under `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/`:
`START_HERE_Audit_and_Optimize_Prompt_EN.md`, `Project_Brief_EN.md`, `01_Concept_Overview_EN.md`,
`02_Agentic_Doping_Reference_EN.md`, `03_Provided_Rebuttal_Draft_EN.md`, `04_Source_Inventory_EN.md`,
and `agentic_doping_reference/excerpts/` files `01_claim_admission.py.txt`, `02_gap_discovery.py.txt`,
`09_evidence_ledger.py.txt`, `10_fixed_vocabulary_target_contract.py.txt`.

**Repository inspected, read-only, unmodified** (`git status --porcelain` clean at finish):
`/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot`, commit
`0007ad104755aec56cbc2479db6cf68c0e05b237` (2026-08-12, verified by `git log`). Under
`src/agentic_doping/`: `literature/quality.py` (714 lines, full); `literature/visibility.py` (346,
full); `objective_analysis/analyze.py` (1117, full); `evidence_ledger/enums.py`, `models.py`,
`ledger.py`, `leaderboard.py` (all full; `__init__.py` empty); `schemas/ledger_record_v1.json` (first 60
lines plus targeted inspection of `$defs.FailureReason`); `schemas/doping_ir.py` (first 80 lines, skim).
Additional targeted reads to substantiate findings: `evaluation_cascade/scoring.py:177-290`,
`literature/models.py:17-83`, `literature/cache.py:614-644`.

**Not read / not accessed.** `05_Delivery_Checks_EN.md`,
`06_Agentic_Doping_Original_Prompt_English_Translation.md`,
`07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`, the package manifests, and excerpts 03–08
and 11 — outside my assigned reading list. Where I cite excerpts 06 and 08 (§6.3) I cite the package's
description of them in `02_Agentic_Doping_Reference_EN.md:21`, not the source, and say so. The five
reference PDFs including the manuscript were not opened: manuscript facts here come from
`00_coordinator_brief.md:76` as instructed, and the scratchpad `pdf_text/` extracts named in the brief
were not present in my session's scratchpad. `supporting_data/` was not opened; its limits are cited
from `04_Source_Inventory_EN.md`. Not inspected: `reference_repos/Agentic-Doping` (`main`),
`deepseek-harness`, `ARIS`, `dgm`; and within the snapshot the `orchestration/`, `web/`, `harness/`,
`flywheel/`, `knowledge/`, `dual_agent/`, and `pipelines/` packages — so this report makes no reuse
claims about run control, memory internals, or the proposal-review loop implementation beyond what the
package states.

**Web lookups.** None; no searches run and no URLs fetched.

**Tools used.** Bash (read-only `ls`, `cat`, `sed`, `grep`, `wc`, `awk`, `git log`, `git status`,
`date`, plus one `mkdir` and one scratch-note write in the session scratchpad), Read, Write (this
report only).

**Honesty notes.** Every code citation was read in this session at the stated commit; no line reference
is from memory. All field lists, enums, and checks are design proposals, not implemented behaviour.
Nothing here reports an executed screening, ranking, threshold, or experimental result. No reference
repository file was modified and no code was written anywhere.
