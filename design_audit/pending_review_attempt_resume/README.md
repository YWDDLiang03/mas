# Durable workflow review attempts — pending patch

The repeated paid work is confirmed at task pin **7968** for `task_01M51AQ0JK0MYN47806ZD5XS1B`. Two pairs of completed logical adjudications have identical full prompt hashes and unique review-item/rule/attribute bindings:

| Item | Rule version | Before pause | After resume | Recorded verdict |
|---|---|---|---|---|
| `q_01M51HP6K70XY79D02XKE50VK4` | `rule_measured-oral-bioavailability-f-any-species@v1` | finished seq7949, `art_7abb9efffd0c` | finished seq7962, `art_a61956efa182` | uphold_objection both times |
| `q_01M51HPDR11AX9654VZ36W7Q8B` | `rule_vegfr2-engagement-on-record@v1` | finished seq7953, `art_215a1a488304` | finished seq7966, `art_5a0b2dc79b14` | revise both times |

The later two requests recorded **USD0.0442584 estimated cost** in total. All costs and original provider attempts remain in the journal; the patch neither deletes them nor reclassifies them as unpaid. These are separate successful logical requests, not schema repair subattempts. At the pin there were six completed adjudicator requests and one unfinished request; the latter was not used as completed evidence.

Root cause: `investigation.py` initializes `handled=set()` on each review-phase entry. Qualification-first adjudication can produce a complete model response and then raise `AdjudicationError` to keep the criterion unresolved. That path leaves the item open and records no durable review-attempt receipt, so Resume calls the model again.

## Contract

Apply-ready diff: [review_attempt_resume.patch](review_attempt_resume.patch). Only a new `core/review_attempts.py`, the workflow import/call, and independent tests are included. The scientific adjudication implementation is unchanged.

`review_attempts.review_once(core, item, *, roster=None, budget=None, settings=None, qualification_policy=None)` returns a durable attempt with `outcome=resolved|unresolved`, `reason_text`, original item/rule/attribute refs, source agent request/trace refs, and `reused`. An unresolved result leaves the queue item unresolved; it is never an approval.

Cache identity contains task context version/hash, item/subject, exact rule and attribute version/hash, critic inspection bundle, cited claim IDs/hashes, qualification policy, relevant predictor review settings and reviewer binding. A task or CQA revision can be reviewed again. Existing criteria, adjudication IDs and frozen results are unchanged.

Completed attempts use a typed `review_attempt` artifact and existing `decision.recorded` event with `record_kind=review_attempt`. This event carries no `adjudication_id` or human decision, so the review fold cannot mistake a receipt for approval. Reuse emits an explicit `review_attempt_reused` link to the original receipt. Real successful adjudications retain their actual `adj_` reference.

`AdjudicationError` is saved with its original reason after a complete attempt. `ModelError` and `InterruptedError` propagate and are not saved as completed attempts. Unfinished starts cannot supply a legacy trace or completed receipt. Existing usage accounting remains based on original model events; a reused receipt does not emit a new model request or incur another model charge.

## Conservative recovery of existing records

The workflow already has old complete responses without receipts. Recovery is limited to a qualification-first proposer/critic dispute whose pending result can be determined safely:

- Same explicit task context version, unique complete criterion view, exact system/schema/prompt/claims/critic findings, max tokens and temperature, and matching original model family/model ID.
- Only `agent.finished` with `schema_ok=true`, `outcome=ok`, no truncation and a complete trace is considered. Unfinished requests are not read for a response.
- The earliest complete exact response is used, never a preferred result selected from later retries.
- `uphold_objection`, `cannot_resolve`, or a revision deterministically refused by the existing `_apply_revision` can be retained as unresolved. A potentially applicable old revision or approval is not guessed or silently applied. Existing successful machine decisions already close their queue items and do not re-enter the workflow pending list.
- Original model reasoning and source request/trace/sequence references remain attached. A pending reason reconstructed from a legacy trace is explicitly labelled as reconstruction; it is not presented as an old persisted error string.

The [real legacy match probe](real_legacy_match.json) matched both actual items above at the fixed pin, without persisting an attempt or writing primary. The probe uses public finished-actor metadata; deployed `review_once` additionally compares against its configured roster. The [original bounded audit](../review_resume_audit_7968_2026-10-16.json) retains the source facts.

## Verification and application

The isolated overlay passed **5 tests in0.40s**, using real temporary Core journals and scripted models. Checks cover resolved/unresolved durable receipts, receipt readability through a reopened Core, zero second model calls, exact old completed trace recovery for objections/refused revisions, original unresolved reason preservation, task/CQA version invalidation, and interruption/unfinished-request exclusion. No network, paid model, primary write, candidate ranking or sealed data was used.

`git apply --check design_audit/pending_review_attempt_resume/review_attempt_resume.patch` passed. Patch SHA256: `8089B178AC2AE399BCB995EBB64FDD3B7BFE0C53FA52F05E90D2FDA2E52FE3CE`.

The patch was not applied by this agent. Root owns safe-checkpoint application, targeted testing, source archive/new implementation binding, and resumption of the existing workflow with its already completed CQA stages and cumulative cost history.
