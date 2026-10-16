# Pending patch: executable preference guard

**Deployment update:** applied at the saved Review checkpoint, after CQA derivation completed and before any freeze or candidate assessment. Integrated verification: 24 preference, measurement and qualification checks passed. The new backend archive is `var/provenance/workbench-v2/1d0272a80e953952`; the completed derivation retains its original implementation binding. Preparation notes below describe the earlier isolated checks.

## Confirmed fault

`check_rule` accepts `cutoff_basis=none_evidence_insufficient` before checking whether a preference has an executable predicate. `confirm_rule_set` can then admit a categorical, non-directional preference with `predicate_form=threshold` and `cutoff=None` through `auto:trigger_table`.

The isolated baseline used the current unmodified code and a real temporary Core store. A usable curated Boolean fact was True, the preference entered the confirmed scoring set, and `assessor.assess_cell` still produced `unknown_missing` with no used claim refs. Such a preference remains in the preference coverage denominator despite having no executable comparison.

No actual candidate results or primary store were read for this verification. The root task separately identified seven affected preferences before screening; that count is not a new measurement from this harness.

## Patch and contract

Apply-ready unified diff: [preference_execution_guard.patch](preference_execution_guard.patch).

- `criteria.preference_execution_problems(attribute, rule) -> list[str]` is pure. Only preferences are checked. A missing cutoff requires `ordering` with an explicit `higher_better` or `lower_better` direction. The guard does **not** require quantitative type or a physical unit: it preserves existing numeric categorical and unitless ordinal encodings. A declared comparison still passes the existing rule validator; no cutoff, direction, weight, approval or Pass value is invented.
- `criteria.preference_execution_findings(core, task_id, *, rule_set=None) -> list[dict]` is read-only. The default audits active registered proposals; a supplied frozen set audits its exact scoring entries.
- `confirm_rule_set` preserves affected registry records as active but puts them in `deferred[]` with `scope='rule'`, `reason_kind='non_executable_preference'`, original rule/attribute refs, readable reason and problems. They do not enter scoring or its coverage denominator. They are not disguised as a deferred tool capability.
- `measurement.register` refuses a **new** profile pointing to an old frozen scoring set that contains these invalid preferences. It makes no writes before refusing. Existing profiles and frozen rule sets remain readable and unchanged.
- `criteria.deferred_capabilities`, criterion export and CLI printing support this non-capability rule deferral. The two display changes avoid KeyError and explain the actual reason.
- Hard conditions are not processed by the new guard. Existing open hard review still blocks normal confirmation; `allow_pending=True` retains the original hard pending ref and review state. No review decision is fabricated or modified.

Files in the patch: `core/criteria.py`, `core/measurement.py`, `core/criteria_export.py`, the one affected CLI deferral-print line, and new `tests/test_preference_execution_guard.py`. No assessor, clinical oral, threshold, weight, workflow stage, or historical result is changed.

## Verification

[verification.json](verification.json) records:

- Original fault reproduced with the unmodified implementation and a persisted temporary store.
- Patched overlay holds the invalid preference out, explicitly defers it, and keeps its active registered record.
- Existing old profile and old rule-set hashes remain unchanged.
- A new profile over the old invalid set is refused without journal writes.
- A new confirmation contains the executable preference and defers the invalid one.
- Numeric ordering preservation is verified using the actual `UniverseRecordField` provider over a local synthetic fixture: catalog `max_phase` is a numeric 0–4 value in `phase`, and the current assessor can order its numeric value even with a categorical label; a numeric ordinal encoding without a unit also remains admitted and scored. No type-based restriction was added.
- The latest check count/time is recorded in `verification.json`: new deferral/ordering regressions plus existing prediction/hard-evidence, hard-adjudication and profile-binding regressions. No model, network or primary-store writes.
- Active source contents were checked against the preparation manifest and remain unchanged.

`git apply --check design_audit/pending_preference_execution_guard/preference_execution_guard.patch` passed. The patch has not been applied here. Once the root task applies it at the safe checkpoint, rerun the targeted tests against the active implementation and bind the new implementation identity before freeze/screen.

`build_patch.py` and `verify_patch.py` are preparation tools for the unmodified source snapshot; the `preview/` directory contains isolated source overlays, not runtime code. Do not use the baseline verifier to describe the already-patched implementation as reproducing the old fault.
