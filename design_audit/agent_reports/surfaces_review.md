# Review: two operator surfaces and the Windows host revision

Independent design reviewer, 13 October 2026. Design only; nothing run or installed.

**Verdict: not ready.** Two blocking findings (SR-01, SR-02), both fixable by text edits; with them and the material findings fixed, ready with fixes.

## Findings

**SR-01 — blocking — design §14.1 "Stop, sleep, and crash", §14.2 "Time", §15 service-host row; UI §15.7; ADR-36.**
Problem: (a) Sleep suspends the host but does not stop it. Nothing restarts, so "on restart" never fires, and the run wakes with a gap and calls that may have died. (b) Monotonic clocks differ between platforms on whether they count suspended time, so a sleep can be charged to `wall_clock_s` and end the run `budget_exhausted` → `unresolved`. (c) "Crash path unchanged" moves the run `retrying` → `running`. During a long expert wait, when a laptop is most likely to sleep, the run is `paused` or `waiting_human`, and §6.1 says `waiting_human` is left only on an `hd_`.
Fix: "A stop, or a suspend detected as a jump between the wall clock and a suspend-excluding monotonic clock beyond a registered threshold, is an abrupt stop. The new attempt restores the execution state at the last checkpoint: `paused` stays `paused`, `waiting_human` stays until an `hd_` arrives, and only `running` and `waiting_tool` steps are re-queued. `host_gap {…, kind: stop|suspend}` is never charged to any budget." Add sleep-without-restart and `waiting_human`-at-stop cases to S12.

**SR-02 — blocking — design §14.1 "Evaluator-only store", §2.4 last bullet, §8.6, §14 table; ADR-31.**
Problem: The comparison function runs in the host, so the host's account must be able to read the intake. If permissions are limited to the evaluator's account, the host must run as that account. On profile W everyone using that account (operator, confirming experts) can then read the files, so under the new rule all of them are `exposed` and the `independent` view is empty by construction on the user's requested profile. Nothing says so. The rule creates no record and no `seq`, so §8.6's "from that `seq`" cannot apply, and §8.6 and ADR-31 omit the channel. The access log that ADR-13 and ADR-31 depend on is not a §14 store, and the operator log row omits evaluator-only reads.
Fix: Choose and state one option. (1) Evaluator-only content is encrypted at rest under a key the evaluator supplies for each scan, comparison, or panel read; the host does not keep the key, and file access without it is not a read. (2) A `store_access_declaration` event at bind lists everyone with OS-level read access, each `exposed` from that `seq`. Add an "Access log" row to §14: journaled `evaluator_only.read {person_id, subject, via}` events, in the streams of SR-03.

**SR-03 — material — design §2.4 Command row and the "Effects" and "No last writer wins" bullets; §4.1 (`seq` per run); iteration §12 rule 9.**
Problem: `basis_seq` ("last `seq` its issuer applied") is undefined when a session watches several runs, and for subjects outside any run: task edits, submissions, review items after their run completed, Rerun Plans, and evaluator-only reads. No subscription delivers their events, and they have no journal (ADR-01). The line between stale-basis and not-permitted-in-state is unclear: "a run already cancelled" is given as stale basis.
Fix: "`basis = {stream, seq}`, where a stream is a run journal or a task journal (`task_<ulid>`, contiguous `seq`) for the non-run subjects above. `subscribe` accepts either. Each command kind declares a precondition: if it fails against the state the issuer saw, the outcome is `rejected_not_permitted_in_state`; if the stream advanced past `basis.seq` and the precondition no longer holds, the outcome is `rejected_stale_basis`."

**SR-04 — material — UI §15.6 row 4, §9.1; design §2.4, §4.1, §8.4, §12.3.**
Problem: `const_review_claim_lease` is defined only in a UI table, and it is called `control_only`, which is a case-field visibility, not one of the §8.4 `const_` scopes (`core_policy | adapter_policy | case_configuration`). No event records a claim, release, reassignment, or expiry, so `in_review` and `assigned_to` are not journal projections (ADR-01), and two surfaces could disagree on expiry. It is undefined whether a claim blocks others. The browser has no claim action, and the terminal has no release or reassign.
Fix: Add `human.review_claimed {person_id, lease_until}` and `human.review_claim_released {reason: released|reassigned|lease_expired}`; the expiry event is written by `scheduler`, also after a host gap. Register the constant in §8.4 with `scope: core_policy`. State that a decision by anyone else under a live claim is `rejected_not_permitted_in_state`. Add `review release|reassign` and a browser claim action.

**SR-05 — material — design §2.4 "No last writer wins"; UI §15.4 third wireframe, §15.6 row 3; versus §12.2.**
Problem: §12.2 says that when experts disagree, both records are kept and the subject stays `unresolved`. §2.4 records a disagreement "with `supersedes_decision_id`", which replaces the first decision. That is last-writer-wins by a second route, and "decide again" in the wireframe invites it.
Fix: "A disagreement is a new `hd_` with `disputes_decision_id`; the subject becomes `unresolved` and is labelled `disputed` until escalation. `supersedes_decision_id` is reserved for revising one's own decision or for deciding an escalation item." Change the wireframe to "record a disagreement or leave it".

**SR-06 — material — design §2.4 Query row and "Same visibility" bullet, §14.1 request checks; UI §15.3 (`recovery show`, `export`), §15.5.**
Problem: (a) A read of evaluator-only content changes state (the reader becomes `exposed`), yet it is a Query, and only state-changing requests need the header token. A cookie-carried GET started from another page could force an exposure and log it. `recovery show` lacks the panel's warning. (b) Exports, downloads, and line-delimited output put copies outside the store, and later readers of those copies go unlogged, which defeats exposure-from-access-logs; export is not one of ADR-13's enumerated readers. (c) Subscribe is not said to be role-filtered, and withholding events would create `seq` gaps.
Fix: "Every logged read (evaluator-only content, traces) is a Command with `command_id`, the token, and a confirmation on both surfaces. In v1 evaluator-only records are shown on screen only, with no export or line-delimited output. Subscribe applies the Query filter and sends a redacted frame that keeps each withheld event's `seq`. Cookies are `HttpOnly` and `SameSite=Strict`."

**SR-07 — material — UI §2 ("every … action … has a terminal equivalent"), §15.3; design §2.4 command list; T6.11.**
Problem: The parity claim is false. These browser actions have no terminal command: plan only (§3.1); attach the comparison artifact (§3.1); the Rules & criteria screen (only `rules diff` exists); exclude with reason, which creates an `hd_` (§7.1); assign to expert, request measurement, dispute, and submit better source (§8.1); add compound (§10); reassign (§9.1); open round and export a journal range (§5.1). `review decide` cannot pass `edits[]`. No command authors the case configuration, although no surface may open store files. Preregistration, `proto_`, `ops_`, and memory review are on neither surface. The `historical_list_exposure` declaration (ADR-31) appears only in the terminal wireframe; it is missing from browser §9.1 and from the `hd_` fields in §12.2.
Fix: Add `run plan`, `case new|edit|attach-intake`, `rules show [--history]`, `candidate exclude`, `claim dispute|assign|request-measurement`, `universe add`, `review … --edits-file`, `run round`, and `export --journal --from-seq --to-seq`. Align the §2.4 command list with §15.3. Add the exposure declaration to §12.2 and §9.1. List which C19 and C14 operations are out of surface in v1.

**SR-08 — material — design §0.4 roles, §2.4, §11.4, §14.1 token; UI §15.3; ADR-12.**
Problem: (a) There is no role × command matrix, and roles look self-declared, so `rejected_unauthorized` has no rule and the evaluator gate is only a declaration. (b) A script can loop `review decide --decision approve` and produce `human_scientific_approval` records that no human made. (c) The token file keeps out other OS accounts but not same-account processes, including `local_subprocess` tools. (d) Under `recorded_attestation`, one person with two session names gets around "reviewer other than the submitter" and per-person exposure. (e) `rerun approve` writes "`hd_` or `ops_`", but §12.1 and §12.2 make a Rerun Plan an `hd_` subject.
Fix: Add the matrix: an `hd_` requires `expert`; run and task commands require `operator`; evaluator-only reads require `evaluator`; traces require `expert` or `auditor`. Add: "An `hd_` command requires interactive confirmation and records `via.entry: interactive`. Tool subprocesses get no token and cannot read the token file. `ses_` records the OS account, and identities sharing one are linked and flagged in separation-of-duties checks." `rerun approve` writes `hd_` only.

**SR-09 — material — design §12.4, §14.2 "Paths"; UI §15.3 `submit --path`.**
Problem: `host_path` reads any path a session names, with the host account's rights. That includes the store root (the evaluator-only store among them, bypassing ADR-13's log), the token file, and, on Windows, network or device paths that reach other machines. Parsed content is shown to the submitter and can become agent-visible after admission.
Fix: "`host_path` is resolved (links and junctions followed) and accepted only inside operator-registered intake directories. Paths in the store root or the token location, and network or device paths, are `rejected_invalid`." Add a §15 row and an S12 case.

**SR-10 — material — design §14.1 first paragraph, §14.2 "Paths"; ADR-36; T0.7.**
Problem: (a) A store root in a cloud-synced Windows folder, or on a profile-X compute node's network home directory, leaves the machine (evaluator-only content included), and a local lock cannot stop a second host elsewhere. (b) Lock release after a crash is unspecified; a stale lock file would make every restart `store_locked`. (c) Windows antivirus and indexers hold new files open, so write-once and atomic replace can fail transiently. (d) File names "from identifiers" can include adapter identities (`cand_<identity>`, `asm_…`) that are case-significant, contain characters Windows rejects, or are too long. "Cannot collide" holds only for hash-derived names.
Fix: "The store root must be local and non-synced; otherwise the host refuses to start (`store_root_unsupported`). The lock is an OS lock released when the process ends. Transient sharing violations are retried a bounded number of times, then treated as C1 write failures. File names come only from content hashes or a lowercase identifier hash." Register both start-refusal codes in §0.4.

**SR-11 — material — design §0.4 last sentence, §4.16, §14.2, §2.3, §7.1; `tools.md` §1.**
Problem: (a) A "deterministic" local tool can produce different numbers on Linux and Windows builds of one `implementation_version`; with the platform never in a fingerprint, C16 reuses them across platforms as `reused_valid`. (b) Nothing covers continuing a run after moving its store root to the other platform, even though the immutable binding holds the original host's manifest. (c) `supported_platforms[]` cannot express "unchecked", so filled-in values read as verified.
Fix: "Tool results record `executed_on {platform, execution_location}`, which enters the fingerprint unless the tool declares `platform_independent_output` (replay recomputes from recorded values, so S12 holds). A continuation re-resolves the manifest and is refused on mismatch." Add `platform_support_basis: checked | upstream_documented | unchecked` to §7.1; the `tools.md` tools are `unchecked` for Windows.

**SR-12 — material — design §14.1 request checks and "Session start"; UI §15.1; U-15.**
Problem: (a) Only profile W's launcher can start a session. Chrome on L, profile X, and U-15's second person have no way to get a token. (b) On X, Host and Origin carry the forwarded Windows port and possibly `localhost`, so a strict check either refuses the workbench or gets dropped. (c) "Does not persist in browser history" overclaims, and on Linux a launcher's command line is visible to other users. (d) The origin check must cover the WebSocket handshake and refuse `Origin: null`. (e) On a shared Linux node loopback is reachable by all local users, so the token is the real boundary.
Fix: "`session open --browser`, run by the host account, prints a single-use, short-lived address, and can issue one for another person. Allowed Host and Origin values: `127.0.0.1`, `[::1]`, or `localhost` with the host port or a registered forwarded port, on every request. The SSH forward binds to Windows loopback." Replace the history claim with "cannot be reused".

**SR-13 — material — design §2.4 opening paragraph, §0.1, §0.3, §14, §15 Component column; `module.md` §13.**
Problem: "Not a twenty-first component" is incoherent as written. The host owns records (`ses_`, `cmd_`), a store, vocabularies, and failure rows filed under "Component", and it decides accept, duplicate, and unauthorized. "Runtime infrastructure" is not a §0.1 category. `cmd_` has no fields, and applied commands exist only as `actor.via`, so `duplicate` has no durable basis across restarts or for commands that emit no event. A reused `command_id` with a different payload would return another command's result.
Fix: Add to §0.1: "Host infrastructure (service host, Operator API) owns `ses_`, `cmd_`, and the operator log, and has no authority over any C1–C20 record." Define `cmd_ {command_id, session_id, kind, subject, basis, payload_hash, outcome, result_ref, received_at}`, written durably before acknowledgement. A different `payload_hash` under the same id is `rejected_invalid`.

**SR-14 — minor — design §2.4, §18; `post_handoff_decisions.md` D6; U-15.**
Problem: A Linux terminal reaches only Linux hosts, and a Windows host only Chrome. If the user meant one store reachable from both, v1 does not support it and does not say so.
Fix: Add to D6 and U-15: "v1 supports a Linux terminal on Linux hosts (L, X) and Chrome on a Windows host (W). A Linux terminal against a Windows host is not supported; confirm with the user."

**SR-15 — minor — design §14.2 "Canonical bytes", §12.4.**
Problem: LF canonicalization would change the bytes of uploaded evidence. Without it, the same CSV with CRLF and with LF gets two `src_upload_` ids. Unicode normalization is unspecified, and §12.4 has no field for the path's platform.
Fix: "Records are hashed in canonical form. Files are hashed on raw bytes (`content_hash`), and text files also get a `text_hash` (UTF-8, NFC, LF) for duplicate detection." Add `path_platform` to §12.4.

**SR-16 — minor — UI §15.4, §13.**
Problem: Run watch claims "the same rows" as the browser monitor but silently drops ELAPSED, `critic-1`, and the `not_attempted … (not a failure)` row, which breaks parity rule 4. Raw ids (`waiting_tool`, `not_exposed`) appear where rule 1 requires `ui_label`. The surfaces say "stop" and "cancel" for one action. `applied` → "done" (positive) can read as a finished run.
Fix: Restore the rows or add "… 1 more (show all)", render labels, use "cancel" on both surfaces, and label `applied` "applied".

**SR-17 — minor — stale references.**
(a) S11 and S12 are never scheduled: E1 in `evaluation_plan.md` §12, T7.4, design §13.5, and the `module.md` runner all say "S1–S10". Add both to E1. (b) `module.md` has `service.stopping`, but the design defines only `service.started {prior_stop}`. (c) The C2 §4.2 label domains lack `surface`, `host_platform`, and `command_outcome`, and session roles have no labels in UI §13. (d) Iteration §9 states replay equality as fact; write "must replay (checked by S12; not tested)". (e) `collaboration_log.md` has no record of this revision. (f) The §2.4 validators and the `module.md` depends-on list omit C8, which validates follow-up commands.

## Checked and found sound

- New prefixes unique; outcome values match §0.4 and UI §13; `actor.via` identical in §4.1 and iteration §2.1.
- `run wait` returns success only for `completed`; the other end states each get a distinct status (ADR-02, ADR-33).
- Effects only from events (ADR-12); no surface reads store files (ADR-13).
- `requires_other_environment` → `not_attempted` → `unknown_missing`, never `fail`, matching §7.3 and ADR-33.
- Loopback, Host-header check, header token, self-contained assets: sound base.
- Tab resubscription; records never cached.
- Terminal wireframes are at most 76 columns, carry the placeholder disclaimer, and show a percentage only for `enumerated_fixed`.
- No Windows testing is claimed (`tools.md` §9, U-14, `resources.md` §4).

## Contribution record

- **Files read:** `optimized_design.md` §0–§2.4, §4.1–4.6, §4.15–4.20, §6–§8, §11–§12, §14–§18; `ui_ux_spec.md` in full; ADR-01–03, 12, 13, 24, 31, 33, 35, 36, U-08, U-13–U-15; `module.md` UI table, new entry, runner; iteration spec §1.2, §2.1, §9, §12; `evaluation_plan.md` §2, §8.4, §12; `task.md` T0.7, T3.7, T6.x, T7.4; `tools.md` §1, §9; `resources.md` §4; protocol §2.4 row; `post_handoff_decisions.md` D6; headings of `collaboration_log.md` and `audit_report.md`.
- **Searches run:** the new names (`const_review_claim_lease`, `store_locked`, `service.*`, `host_gap`, `lease`); `supersedes_decision_id`; intake modes; "access log"; Windows, Linux, browser, server, terminal, web, and UI across all deliverables; "S1–S10"; wireframe widths.
- **Approximate time:** 50 minutes. Nothing run or installed.
