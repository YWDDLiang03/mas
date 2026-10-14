# Improvement plan — post-audit, 2026-10-14

Written after verifying findings F1–F8 from `MAS_System_Revision_Master_Handoff_EN_20261014.md`
against commit `aec82a6` on this checkout. It states what the audit found, what blocks each of the
two acceptance measurements, and the work sequence with its gates. It supersedes the planning in
`situation_report.md` §9 and corrects several claims in that document (§6 below).

**The goal this plan serves:** build an agent that reconstructs a defensible scientific selection
process from a task statement, literature and public databases — deriving its own criteria,
grounding every scientific threshold in quoted evidence, producing a reasoned, sourced, ranked
answer whose derivation is auditable. **Criteria generation is the core competence.** The reference
compound's rank is a secondary readout.

---

## 1 Audit result: 8 of 8 findings confirmed — and all eight now repaired

**Status as of the end of 14 October 2026: F1-F9 are repaired, with a regression test each.** The
table below is kept as the audit record; the right-hand column now says how each was closed. F7 is
the exception worth reading carefully: it is *documented and pinned*, not enforced, because making
it a real boundary needs an authenticated principal this deployment does not have.

| # | closed by |
|---|---|
| F1 | `refine_count` persisted in `ITEM_FIELDS`, per lineage and cumulative across rounds; a merged child inherits its group's largest count |
| F2 | one shared `bound_support` validator, wired to proposal validation, promotion, revision, collapse and confirmation |
| F3 | authority computed from rule + attribute + transform + weighting, not the rule's two fields |
| F4 | revisions fully revalidated, tightening permitted only to a number the cited claims state, both versions and a diff recorded |
| F5 | `quantity_key` includes the declared transform; a shared retrieval identity is a hint, and the quantity must agree before a duplicate is refused |
| F6 | a registration reference must resolve, and `core/freeze.py` now writes one |
| F7 | **not enforced.** Documented in `review.decide` and pinned by a test asserting both halves — the rejections that hold, and the forged approval that still succeeds |
| F8 | each claim evaluated once; aggregation, predicate and conflict attribution read the same evaluation |
| F9 | `asserted` registered as a determination basis, kept out of the defaults |

Two gaps found beyond the eight: the eligibility criterion asked for an *approved* oral product when
the task admits approved **or Phase III**, and the proposer was offered `none_evidence_insufficient`
as a co-equal option and took it 39 times out of 40. Both repaired; the second is measured in §8.

### The audit record

Verified by source inspection and synthetic execution on this checkout, not accepted on report.

| # | Finding | Evidence obtained here | Priority |
|---|---|---|---|
| **F1** | Refinement state lost on persistence | `pool.ITEM_FIELDS` omits `refine_count`; `derivation_stages` reads it. The repair budget silently resets across a store reopen, so `max_refines` does not bound anything durably. | P1 |
| **F2** | Citation presence ≠ threshold support | `derivation.validate_proposal` contains **no numeric comparison at all** between a cutoff and its cited claim's value. A cutoff of 90 citing a claim stating 30 passes. | **P0** |
| **F3** | Transform bounds bypass authority | `criteria.needs_expert` reads only `rule["rule_kind"]` and `rule["cutoff_basis"]`; it never inspects `value_transform`. `expert_set` is a permitted transform basis. An expert-set bound therefore scores with zero review items. | **P0** |
| **F4** | Adjudicator revisions unvalidated | `adjudication._apply_revision` calls `check_rule` but no support validator, and enforces nothing about "weaker only". | **P0** |
| **F5** | Retrieval identity confused with quantity identity | `duplicate_of_registered` compares neither transform, direction, nor definition. `quantity_key` omits the transform, so a raw quantity and its derived transform can read as one. | P1 |
| **F6** | `prespecified` is unchecked | `confirm_rule_set` emits `acceptance_label = "exploratory" if acceptance_reasons else "prespecified"`, and `preregistration_ref` is an unvalidated parameter — nothing confirms the registration exists. | P1 |
| **F7** | Human approval trusts the caller | **Demonstrated:** a direct non-interactive call to `review.decide` with a fabricated `actor={"kind":"human"}` and `entry="interactive"` produced a valid record with `approval_kind: human_scientific_approval`. No signature or principal is verified. | P1 |
| **F8** | Explanations use raw values after transformed scoring | `assess_cell` computes verdicts on transformed values but attributes conflicts with `c.get("value")`, the raw observation, against a transformed-quantity cutoff. | **P0** |

**Three of these (F3, F4, F8) are in work committed during this session.** The `value_transform`
and adjudication slices were tested on their intended paths and missed the authority and
attribution interactions entirely. That is the strongest available argument for the automatic
contract gates in §3 WP8: a reviewer found in one pass what our tests did not.

---

## 2 What actually blocks each measurement

### Primary — criteria recovery
| Blocker | Why it blocks |
|---|---|
| The generator has never executed its full loop | Zero merges across all historical rounds; the adjudicator role never called; nine disputes unresolved. The 34 criteria are an incomplete pipeline's output and must not be frozen. |
| F2/F3/F4 unrepaired | A frozen criterion set containing an unsupported or unauthorised bound defeats the "every threshold traced to a quoted source" claim regardless of recovery count. |
| F1, F5 unrepaired | Bounded derivation is not reproducible, and consolidation cannot be defended. |
| No baseline export | No reviewer can assess criterion quality, so the independent-review gate cannot be passed. |

### Secondary — reference rank
| Blocker | Why it blocks |
|---|---|
| **Task eligibility is stricter than the task** | The adapter maps the oral constraint to *Approved oral route on record*. The task permits **approved or Phase III**. 1,262 compounds sit on an unknown hard predicate, and the reference compound can only ever be `provisional`. This is a faithfulness defect, not a tuning opportunity. |
| F8 unrepaired | Per-candidate reasons can contradict the verdict they explain, so the audit trail fails even where the score is right. |
| 26 literature criteria never evaluated | Not evidence of failure — a missing execution stage. Needs a registered, budgeted second stage. |
| No freeze machinery (F6) | Without a validated registration, no result can be claimed as the designated one-shot outcome. |

---

## 3 Work sequence

Each package states what it contributes to the goal, per the handoff's requirement.

| Order | Package | Contribution to the goal | Gate |
|---|---|---|---|
| 1 | **WP0** Export the 34 criteria with full provenance; reconcile the 72/34/40/13/8/9/26 counts | Makes criterion quality reviewable at all — the precondition for the independent-review gate | A reviewer can distinguish what scored from what was proposed, disputed, merged or deferred |
| 2 | **WP2** F2–F4: one shared bound-support validator; authority computed from rule + attribute + transform; full revision revalidation | Establishes "every scientific threshold is traceable and authorised" as enforced rather than asserted | The 30→90 substitution is refused; an expert-set transform bound cannot score |
| 3 | **WP1/WP5** F1 (persist refinement state), F8 (reasons reuse the evaluated values) | Reproducible bounded derivation; explanations that match their verdicts | Same item reaches the same decision across a store reopen; the transformed-conflict fixture attributes correctly |
| 4 | **WP3** F5: separate retrieval / measurement / decision identity | Consolidation becomes defensible instead of coincidental | Raw and transformed quantities survive; cross-source equivalents consolidate; unrelated outcomes sharing a unit stay separate |
| 5 | **WP6** Split development status / oral route / target engagement | Faithful task semantics; removes the systematic unknown on 1,262 candidates | Eligibility reflects approved-or-Phase-III oral; unknowns retained, not promoted |
| 6 | **WP4** Pooling strata, species vs assay host, experiment deduplication, intervals | Evidence compatibility stops resting on a shared log unit | Incompatible endpoints do not enter one median; two curations of one experiment count once |
| 7 | **WP8** Automatic contract gates on promotion, confirmation, publication | The agent audits its own run instead of relying on a reviewer | Audit findings block the appropriate path by severity |
| 8 | **WP7** Deployment authority boundary (F7) | Either enforce the human-approval boundary or narrow the public claim | Permitted agent routes cannot mint approval or read evaluator material |
| 9 | **WP9/WP10** Freeze machinery, then clean derivation in a fresh registry, independent review, freeze, registered screen, one-time CQA intake | The two measurements become claimable | Freeze verification succeeds; both endpoints reported once |

**Deferred deliberately:** second provider, symbolic regression, further affinity sources, browser
features. All are subordinate to the goal and none is on the critical path.

---

## 4 Honest expectations

- **The reference rank will probably move, possibly down.** A properly merged pool will be smaller
  and differently composed; the eligibility repair changes which candidates are rankable at all. A
  rank produced by a validated generator is worth more than a better rank on criteria from a
  pipeline whose merge stage never ran.
- **The current rank 4 is not an acceptance result.** It is 99 rankable of 3,177, every row
  `provisional`, on pre-repair criteria, outside any freeze.
- **CQA recovery may be low.** The historical list is not necessarily scientifically complete, and
  recovery is to be reported descriptively unless a pass threshold is registered before unsealing.
  A low recovery with sound, sourced criteria is a reportable result, not a failure to hide.

---

## 5 Scientific choices still requiring owner or domain judgment

1. **Does the primary rank endpoint require demonstrated task eligibility, or is a diagnostic
   board that includes `provisional` candidates the registered endpoint?** This must be fixed
   before the result is observed. It directly determines whether an unresolved oral-route unknown
   disqualifies the reference compound.
2. **What does "engaging" a required receptor mean numerically**, and must all five be
   individually demonstrated rather than compensated by a good aggregate? The task says five
   targets; the current score can rank a candidate highly with one target unknown.
3. **Acceptance policy for oral-route evidence** when sources disagree or are silent — reconcile,
   or leave unknown.
4. **Whether a minimum recovery count** constitutes binary primary success; if so it must be
   registered before unsealing.

---

## 6 Corrections to previously published claims

`situation_report.md` and statements made during this session overstate what is enforced. These are
to be corrected in place, not quietly dropped.

| Published claim | Correction |
|---|---|
| "No agent can create an expert decision; `new_id("hd")` is in exactly one file" | **False as an invariant.** F7 demonstrated a valid approval record from a direct call. The claim holds only under a declared, enforced caller boundary that does not yet exist. |
| "A change benefiting only the reference compound must be tuning" | Beneficiary count is not the scientific test. The orthologue substitution was correctly declined, but on species and endpoint grounds, not because one candidate benefited. |
| "No quoted span backing a bound was ever machine-verified" | Conflates two separate checks. Quote matching (`quote_verified`, `span_checked_against_source`) and semantic support (`verification_status`) are distinct fields and operations. |
| "A configured stage with zero transitions is a defect" | A legitimate no-op is acceptable. What must be demonstrated is stage *reachability*, not forced change. |
| "Rank 4 means the database pass condition is met" | It was 99 rankable of 3,177, provisional, pre-repair, unfrozen. |
| Known-answer debugging framed as the methodological defect | The owner accepts it explicitly. The test is whether a repair has independent justification and applies consistently. |

---

## 7 Firewall status

The eleven historical CQAs have **not** been read by the coordinator or any deriving agent as of
this document. The owner has offered access; it was declined for now because reading the list
would mechanically void the primary measurement, which is the project's stated goal. If access is
later taken, an exposure declaration must be recorded and the recovery report must state that it
was measured post-exposure rather than blind.
