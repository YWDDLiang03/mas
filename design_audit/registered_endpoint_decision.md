# Registered endpoint decision — recorded before the sweep

**Written 14 October 2026, before any board was produced for `task_01M4X892V1EAER2GHWE1RE19ZN`.**
Its purpose is to fix what counts as the result while the result is still unknown. The review's
§8.3 is explicit that this choice must not be made after observing the reference outcome, so it is
recorded in the repository with its reasoning rather than settled inside a later report.

## The choice

| | |
|---|---|
| **Primary rank endpoint** | the reference compound's position among **rankable** candidates on one named primary board, under the frozen scoring policy |
| **Rankable** | preference coverage at or above the registered floor of 0.5 |
| **Eligibility** | reported **separately**, and explicitly not claimed as task satisfaction |
| **Target** | top 5 |

So a `provisional` candidate can hold a registered rank, and the report must say in the same breath
whether every task requirement is established for it. A top-ranked provisional compound is a
ranking result, not a scientifically confirmed recommendation, and will not be described as one.

## Why this rather than requiring demonstrated eligibility

The alternative — requiring full task eligibility for the primary endpoint — is the stronger claim
and was considered. It is rejected for a reason that has nothing to do with which answer it would
produce:

The task admits an **approved or Phase III** oral compound. Oral route is a hard constraint. But the
only route field in the evidence catalog is ChEMBL's, which is derived from approved-product
records, so **no database in the catalog can establish the route of a Phase III compound**. Measured
on the universe: 1,262 of 3,177 candidates have no approval record at all. Making eligibility part
of the primary endpoint would therefore make the endpoint unanswerable for 40% of the population the
task declares eligible — the endpoint would be measuring source coverage, not the compound.

That is a defect in the evidence, and it is being addressed: a companion literature criterion now
asks whether a clinical report states oral administration, and the literature pass can answer it.
But the registration must not depend on a stage that has not yet run.

§8.3's own recommendation is the one adopted here: publish the named rank endpoint, and separately
whether the task requirements are established.

## What this decision does not do

- It does not lower the bar for the reference compound specifically. The floor, the board and the
  endpoint apply identically to all 3,177 candidates, and `provisional` rows are not privileged —
  the report will name the blocking unknown for every ranked candidate that has one.
- It does not make an unresolved hard rule disappear. Every candidate with an unknown on a hard
  rule stays `provisional`, and that state travels with the rank wherever it is reported.
- It does not settle the secondary question of whether all five receptors must be individually
  demonstrated. That is registered separately in the freeze policy's `rank_endpoint` detail, and if
  a required receptor is unknown for a candidate the per-target coverage must say so beside its
  rank — a good aggregate score cannot stand in for five-target engagement.

## Falsification, unchanged

A high rank under this endpoint still establishes nothing if the criteria behind it carry
unsupported thresholds, if they were shaped by exposure to the sealed historical list, or if the
derivation is not auditable. The endpoint fixes *what is measured*, not whether the measurement
means anything.
