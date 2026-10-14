# Situation report — iteration 2, 2026-10-14

Written for a reviewer opening this repository without having followed the build. It states what
works, what has never worked, what is still wrong, and the decisions waiting on the project owner.
Numbers in it were measured against the live store `var/primary/store` on the date above, not
estimated. Where a claim is weaker than it looks, the report says so.

---

## 1. What this system is for

`mas` is an agent-centred, self-improving multi-agent system. The agent takes a task statement and
produces a *reasoned, sourced, ranked* answer: it derives its own criteria from retrieved
literature and databases, gathers evidence per criterion, and ranks candidates — with every
threshold traceable to a quoted source and every gap reported as a gap.

Its competences, in dependency order:

1. **Criteria generation** — the core. A pool grows from cited evidence (few → many), then is
   pruned (many → few) by deduplication, merging, debate between a proposer and a blind critic,
   and refinement. Everything downstream is only as good as this stage.
2. **Candidate establishment and evidence retrieval** — build the universe, resolve identity,
   answer each criterion from a declared source, distinguish measured from derived from predicted.
3. **Ranking** — score with uncertainty attached; refuse to rank below a coverage floor.
4. **Honest records** — journal-as-truth, replayable; no agent may fabricate an expert decision;
   anything software decided reads as decided by software.

### The acceptance case

The manuscript case is the instrument that measures the agent, not the objective. Over a
~3,177-compound approved/Phase-III universe and five required receptors (CSF1R `CHEMBL1844`,
VEGFR1 `CHEMBL1868`, VEGFR2 `CHEMBL279`, VEGFR3 `CHEMBL1955`, FGFR1 `CHEMBL3650`):

| validation | what it tests | status |
|---|---|---|
| **CQA recovery** — do the derived criteria match the 11 critical quality attributes the authors used? | criteria generation (competence 1) | not measured; list still sealed |
| **Reference compound rank** — does surufatinib reach the top 5? | the pipeline end to end | rank 10 of 34 published; 4 of 99 in an offline recompute |

**Both are one-shot measurements.** The 11-CQA list is firewalled: it lives in `CELL1.pdf`
Fig 1A panel d, which is kept out of this repository and out of the deriving agents' and the
coordinator's context. It is unsealed once, after the criteria freeze, by an isolated evaluator.
If it were used as feedback, recovery would measure copying rather than derivation. The same logic
governs the rank: a rank obtained by tuning toward surufatinib is not evidence about the agent.

The pre-MAS baseline this must beat: literature-chosen targets → a trained DTI predictor →
3,171 compounds → 140 by predicted probability > 0.9 on all five targets → a binary pass/fail gate
of 11 CQAs → 1 compound. No sourced thresholds, no per-compound reasons, no ranking, no literature
loop, no mechanism at screening time.

---

## 2. Repository state

- Branch `main`, 9 commits this iteration, all pushed to `git@github.com:YWDDLiang03/mas.git`.
- ~11,300 lines of Python in `src/mas/`; 113 source and design files.
- **237 tests passing**, 11 deselected (those 11 are live-network tests, run with `-m live`).
- Design deliverables in `design_audit/`; implementation in `src/mas/`; `var/` is git-ignored and
  holds the live store, so no run data is committed.

Test distribution, which is a fair map of where the engineering effort went:

| file | tests | |
|---|---|---|
| `test_adjudication.py` | 33 | autonomous resolution of the review queue |
| `test_symbolic.py` | 24 | symbolic-regression scoring |
| `test_criteria_pool.py` | 23 | the criteria generator |
| `test_ui.py` | 20 | browser workbench endpoints |
| `test_sources.py` | 19 | licence-gated source registry |
| `test_config_and_providers.py` | 16 | layered settings, model adapters |
| `test_foundation.py` | 16 | journal, artifacts, store |
| `test_drug_adapter.py` | 15 | ChEMBL / PubChem / IUPHAR adapters |
| `test_models_and_reading.py` | 15 | reading and extraction |
| `test_firewall.py` | 11 | evaluator-only and case-source exclusion |
| `test_evidence.py` | 11 | evidence gathering |
| `test_mechanism.py` | 11 | mechanism-of-action gate |
| others | 43 | records, end-to-end, bridge, derivation |

---

## 3. What works

**Journal-as-truth.** Append-only SQLite with hash-chained events, content-addressed artifacts,
an exclusive OS lock for writers and a genuine read-only path (`Core.open(..., read_only=True)`)
that refuses writes. Verified in practice: this session read a store continuously while a sweep
held its write lock.

**A criteria pool with navigable lineage.** Pool items are lineages (`cri_<ulid>`) that keep
their identity across revisions and rounds. Every transition is one `criterion.change_recorded`
event carrying the operation, the reason kind, the targets in and out, and the source claims.
`mas criteria pool --trajectory` replays them per stage per iteration:

```
round  it stage      +new  revised  merged  dropped  promoted   live  why
    1   0 propose      72                                         72  new_evidence 72
    1   1 filter                71                                72  critic_findings 47, validator 24
    1   1 refine                14               6                66  refined 14, withdrawn_by_reviser 6
    4   1 filter                46                                63  critic_findings 46
    4   1 refine                38              24                39  refined 31, withdrawn 24
    4   2 refine                27               5                34  refined 27, withdrawn 5
    4   0 promote                                         34      34  accepted 25, disputed 9
```

**A real end-to-end run.** 3,177 compounds from ChEMBL, identity via PubChem, potency from ChEMBL
and IUPHAR/BPS, computed descriptors from PubChem, literature from Europe PMC and PubMed with
quote-verified extraction. A full sweep assesses ~44,500 cells in roughly 40 minutes.

**Honesty invariants that survive inspection.**
- `new_id("hd")` appears in exactly one file (`core/review.py`), and that function requires
  `actor.kind == "human"` with `entry == "interactive"`. **This is a code path, not an enforced
  boundary, and an earlier version of this report overstated it.** Both fields are caller-supplied
  strings: a direct non-interactive call to `review.decide` with a fabricated actor produced a
  valid record carrying `approval_kind: human_scientific_approval`. The CLI does gate on `/dev/tty`,
  so the claim holds for a person using the CLI; it does not hold against an agent that can call
  Python or write the store. Either the deployment boundary is enforced (F7 / WP7) or the public
  claim must be narrowed to restricted model outputs mediated by a trusted controller.
- Absence is reported as absence. The system does not predict a missing measurement (ADR-49).
- Scores do not reward completeness: a missing value leaves both numerator and denominator, and
  coverage is reported separately.
- Rule sets carry `acceptance_label: exploratory` with reasons naming exactly what software did.

**Autonomous operation without borrowed authority.** Five adjudication routes resolve the queue
with no person: `task_constraint_restated` (the authority is the user's own task text, cited by
field and version, no model call); `definition_restated` (an attribute's own promoted definition,
with every bound traced to a cited claim); `no_authority_available` (an `expert_set` cutoff is
never auto-approved — the rule stops scoring); `irreversible_without_authority` (a hard exclusion
is demoted to a preference rather than applied, so no candidate is silently removed);
`adjudicated_dispute` (a third model family, blind to the proposer's rationale). A person reverses
any of it with `mas review reopen` or `mas criteria dedupe --withdraw`.

---

## 4. What has never worked

**This is the central finding of the iteration.** The criteria generator has never executed its
full loop.

- The **`merge` stage performed zero merges** across every round ever run, and the `adjudicator`
  role was never called once. Cause: `filter` moves every item with a validator or critic finding
  to `needs_refine`; `distill` and `merge` read only `candidate`; `refine` is what returns a
  repaired item to `candidate` — and merge ran *before* refine. The pool it could see was whatever
  filter happened not to flag, which on this case was nothing.
- **Debate never concludes.** Proposer/critic disagreements are deferred to the review queue
  rather than settled. Nine remain open.
- Therefore the 34 promoted criteria are the output of an incomplete generator, and **ten of them
  covered five quantities**: for each required receptor, one attribute bound to ChEMBL
  (`question_kind: pchembl_values`) and another to IUPHAR (`gtopdb_affinity`), with identical
  definition in substance, unit (pChEMBL), direction, aggregation (`median`), acceptable sources
  and `target_chembl_id`. Every receptor was scored twice; a compound well covered by one curation
  received double credit; and five quantities that do not exist inflated the coverage denominator,
  so 34 of 3,177 compounds cleared the 0.5 ranking floor where 99 clear it once each receptor is
  one quantity.

---

## 5. Defects that reached a published board

All four are fixed, each with a regression test that fails on the old code.

| defect | symptom | commit |
|---|---|---|
| ordering rules took the best value, not the declared `median` | the board rewarded having been assayed often — sorafenib's 125 curated VEGFR2 measurements beat surufatinib's 2 | `1b527e6` |
| `merge` ran before `refine` | the merge stage was structurally dead | `2bc0abd` |
| duplicate detection and merge grouping keyed on `question_kind`, i.e. *which database answers* | 10 registered rules for 5 quantities | `798d4bc` |
| attributes defined a derived quantity and no mechanism existed to express it | "the excess in g/mol above 500 g/mol" ranked raw molecular weight | `9ca8efc`, `ed582cd` |

**Every one was found by a human reading the system's output. The system raised none of them**,
although each is detectable from the store alone: a configured stage that recorded no transitions;
two promoted attributes sharing a quantity key; an attribute declaring `median` while the code
takes a maximum; a definition naming a derived quantity with no transform declared. That gap —
the agent not auditing its own run — is the clearest weakness in the design as built.

### Methodological criticism, as the project owner framed it

The defects above were found by looking at the reference compound's rank and asking why it was not
higher. **An earlier version of this section called that the methodological defect; the project
owner's standing instruction is that it is not.** Using a known answer to locate an implementation
problem is ordinary debugging. The test of a repair is whether it has an independent technical or
scientific justification and is applied consistently to every candidate -- not how many candidates
it happens to help. A correct repair can benefit one candidate; a change touching many can still be
unjustified.

The real boundary is answer-directed adjustment without independent justification: choosing a
scientific cutoff, an evidence substitution, a weight or a board because it delivers the desired
reference rank. By that standard the orthologue substitution in §7 was correctly declined, but the
reasoning given there was wrong -- the valid ground is species and endpoint mismatch, not that one
candidate benefited.

What does remain a real weakness is that the system raised none of these findings itself, although
each was detectable from stored data alone: a configured stage that recorded no transitions, two
promoted attributes sharing a quantity key, a declared aggregation the code ignored, a definition
naming a derived quantity with no transform declared.

## 6. Outstanding problems

| problem | measured detail | consequence |
|---|---|---|
| **semantic support is never assessed** | every claim backing a criterion bound is `admitted` with `location.span_checked_against_source: true` and `quote_verified`, but `verification_status: unverified` | **an earlier version of this report conflated two separate checks.** Quote matching ran and passed; what was never run is any judgement that the passage *supports* the bound. Measured since: the 500 g/mol bound traces to one end of a range the source reports as observed practice (380–500 Da), so it cannot become a sourced threshold under the bound-support contract |
| **coverage variance ignored in ranking** | compounds rank at coverage 0.50 (4 of 8 criteria) beside surufatinib at 0.88 | a mean over 4 criteria is compared to a mean over 7 as an equivalent point estimate; this currently *flatters* the reference compound |
| **`recommended` unreachable for the reference compound** | ChEMBL records `oral: false, first_approval: null, max_phase: 3.0` for surufatinib; IUPHAR records `Approved: yes`. 229 of 3,177 universe compounds have this gap, 2 of the 34 ranked | surufatinib stays `provisional` on an unknown hard rule — ranked, never recommended |
| **26 of 40 criteria never evaluated** | they are literature-bound; sweeps so far deferred `literature_retrieval` | includes the two receptor-coverage criteria, which are the legitimate route for CSF1R evidence |
| **no upstream check on declared-but-unapplied fields** | nothing refuses an attribute whose definition names a derived quantity while declaring no transform | the transform defects were repaired one queue item at a time, after the fact |
| **concurrent sessions** | commit `798d4bc` was made by a subagent against an explicit instruction not to commit, sweeping unrelated work in with it | provenance of that commit is mixed; its content was reviewed and kept |

---

## 7. A change that was declined

Surufatinib's missing CSF1R potency does exist in ChEMBL — on `CHEMBL5570` (*mouse* Csf1r),
IC50 79 nM, from a cellular RAW264.7 AKT-phosphorylation assay. Human CSF1R (`CHEMBL1844`) has
zero activities for it. Widening the required-receptor binding to orthologues would fill that cell.

**It was declined on species and endpoint grounds.** Target species must stay separate from
assay-host species, and a non-human orthologue measured in a cellular phenotypic assay does not
answer a criterion about human biochemical potency. Human cellular engagement could legitimately
support a separately *defined* cellular criterion; it cannot silently fill a missing human
biochemical cell. **Declined, and recorded here rather than quietly dropped.**

An earlier version of this section argued instead that the change was illegitimate because, measured
across the 34 ranked compounds, **exactly one gained a required-receptor cell from orthologue data:
surufatinib and no other.** *That reasoning is retracted.* Beneficiary count is not a scientific
test -- a correct repair may help exactly one candidate, and a change helping many can still be
unjustified. The 1-of-34 measurement stays here as a fact about the evidence landscape, not as the
reason for the decision.

The approval-record gap in the table above was a different case and **has since been repaired**: the
eligibility criterion asked for an *approved* oral product when the task admits an approved **or
Phase III** compound, so it could never be satisfied by half the population the task declares
eligible. The genuinely unapproved Phase-III compounds (cediranib, motesanib, dovitinib, linifanib,
brivanib, semaxanib, vatalanib, orantinib, lestaurtinib, sitravatinib) remain unapproved in both
sources, which is why adding a second status source does not launder them.

---

## 8. Current numbers

Offline recompute over the stored claims, with the baseline row reproducing the published board
exactly (same rank, score, coverage and top six), which is what makes the other rows trustworthy:

| scenario | scoring rules | ranked set | surufatinib |
|---|---|---|---|
| as published | 13 | 34 | **10** · score 0.582 · cov 0.69 |
| + the MW/logP transforms the definitions already describe | 13 | 34 | **7** · 0.677 |
| the 5 duplicate IUPHAR rules deleted | 8 | 96 | **6** · 0.620 |
| both sources **pooled** per receptor (keeps IUPHAR) | 8 | 99 | **8** · 0.608 |
| **pooled + transforms** | 8 | 99 | **4** · 0.729 · cov 0.88 |

The deletion row is reported for completeness and is *not* the chosen path: deleting an
independent curation to improve a rank is not defensible. Pooling keeps IUPHAR's evidence and
removes the double count, and costs surufatinib two places relative to deletion, because its
IUPHAR VEGFR2 value (7.68) is below ChEMBL's median (8.31).

**Applied to the live store:** all five receptor attributes are now `@v2` declaring both curations;
the five duplicates are merged away; both transforms are declared; `rules@v3` is confirmed with 9
scoring rules (was 13), `pending_but_scoring: 0`, label `exploratory`. A confirming sweep
(`run_01M4WYBBYWD518XGX2CYP74FK1`) was still running when this report was written, so **rank 4 is
an offline figure the pipeline has not yet reproduced.**

The collapse's refusal rules earned their place immediately. Of 8 candidate groups it accepted the
5 receptor groups and refused 3 that would have been destructive:

- `Rate of grade 3 or higher treatment-related adverse events` would have absorbed **seven**
  unrelated safety criteria (discontinuation rate, hypertension, proteinuria, hand-foot skin
  reaction, haemorrhage, serum phosphate elevation, central serous retinopathy) on nothing but a
  shared unit and direction;
- `Number of required receptors named as covered in the literature` would have merged with
  `Number of required receptors with measured rather than predicted engagement`;
- `Food effect on systemic exposure` would have merged with `Transporter-mediated change in
  systemic exposure`.

All three share a quantity key whose subject is empty, which is a unit and a direction and
identifies no measurement. The refusal was argued for by the agent that built the collapse,
against its own feature.

---

## 9. What is needed to finish

In dependency order. Nothing after the freeze may change the criteria.

1. **Judge a criteria set by its internal properties** — pool grew from cited evidence; each
   configured pruning stage did measurable work; no two survivors measure the same quantity; every
   bound traces to a verified span; every route binds to a real provider; all task dimensions
   represented. With the CQA list still sealed, this is the *only* legitimate feedback signal.
   (In progress.)
2. **Make debate conclude in-run** rather than deferring to a queue.
3. **Re-derive on a clean task context** with the same specification. On the existing task the 34
   promoted criteria make fresh proposals hit `duplicate_of_registered`, so merge would stay dead
   and the generator would remain unvalidated.
4. **Freeze the criteria.**
5. **Then** candidates → retrieval → ranking, reporting the reference compound's rank as a readout.
6. **Then** unseal the 11 CQAs once, via an isolated evaluator, and compute the recovery matching
   report with an exposure declaration.
7. **Then** round 2 with a different provider, so the change records show what the provider swap
   altered; and the execution tutorial.

**Expected cost of doing it in this order:** a properly merged pool will be smaller and different,
and the reference compound's rank may get *worse* than 4. That is the right trade — a rank produced
by a generator that can be defended is worth more than a better rank on criteria from a pipeline
whose merge stage never ran.

---

## 10. Decisions required from the project owner

### Sequencing
1. Re-derive on a **clean task context** (fresh registry, same specification)? Recommended, for the
   reason in §9.3.
2. Keep the existing task as a frozen baseline for comparison, or retire it?
3. Is **round 2 on a second provider** in scope for this iteration, or deferred until the generator
   is validated?
4. Derivation size — last round was 4 dimensions × 3 inner iterations → 72 proposals. Same, or
   wider?

### The criteria generator
5. **Debate resolution:** should a dispute surviving revision be settled in-run by the adjudicator,
   or should the criterion simply stay exploratory and not score?
6. **Independence:** the design wants the adjudicator on a different model family from both
   proposer and critic. With Claude subagents playing all three roles they are one family. Is that
   acceptable, or should the second provider be the third family?
7. **Span verification:** build machine checking of quoted spans against source text before the
   freeze? It affects every criterion bound.
8. Should "definition names a derived quantity but declares no transform" **block** promotion, or
   only warn?

### Evidence
9. **Literature evidence pass** — on the ~99 ranked compounds only, or skip it this round? Skipping
   leaves 26 criteria permanently unevaluable, including the two receptor-coverage criteria.
10. Build the **second approval source** (IUPHAR `Approved`, WHO ATC) so `recommended` becomes
    reachable?
11. Add further affinity sources (BindingDB, PubChem BioAssay)? Measured: they add little for these
    five human targets specifically.

### Ranking
12. **Coverage variance** — fix it (raise the floor, shrink scores toward the pool mean, or rank
    within coverage strata), or leave it and report? It currently flatters the reference compound,
    so the method should be chosen before its effect is measured.
13. Enable **symbolic-regression scoring** for the ranking run, or keep the weighted-preference
    baseline?
14. Keep the ranking coverage floor at 0.5?

### The seal
15. **Freeze point** — after the clean re-derivation passes the audit, or only after both rounds?
16. Confirm the **CQA transcription mechanism**: a fresh isolated subagent reads `CELL1.pdf`
    Fig 1A panel d into an evaluator-only intake, after the freeze, once. The list has not been
    seen by the coordinator or any deriving agent and will not be until the seal is lifted.

### Process
17. Should one session be the **only writer** to this repository, or is concurrent work expected?
18. Keep maintaining the **browser workbench** headlessly as features land?
