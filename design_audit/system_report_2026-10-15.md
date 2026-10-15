# System report and handoff — 2026-10-15

Written at the end of a long session for the agent who picks this up next. It has three parts:

1. **This front section** — where the project stands tonight, what to run next, and what is known
   to be missing.
2. **Module reference** (§4) — every module of `src/mas`, what it does, its entry points, the
   records it owns, and the invariants a changer must not break. Written against commit `9912dbb`.
3. **Pointers** (§5) — the run log, the test log, the development log, and the design documents.

**Repository**: `git@github.com:YWDDLiang03/mas.git`, branch `main`. **Live store** (git-ignored):
`var/primary/store/` — one SQLite journal store (`store.db`, ~2.1 GB), the model rosters, the
prediction caches, and the bridge queues (`llm_exchange_r3*`).

**The case**: `task_01M4X892V1EAER2GHWE1RE19ZN`, chain `chain_01M4X89HR1DAKPDS9PB32SS062`. The
registered endpoint (`design_audit/registered_endpoint_decision.md`) is the reference compound's
rank among rankable candidates on one named primary board **under the frozen scoring policy**,
with eligibility reported separately. A frozen rule set already exists (`rules@v1`, confirmed
2026-10-14 20:58:43) with its preregistration.

## 1. Where tonight's run stands

**Round 10** (`run_01M4ZJZJM6NADXR9MPJN479F43`, continuing the chain from round 9, DeepSeek roster,
`research.max_documents = 1`) — the round that carries the chain's inherited evidence into the pool.
It **completed** (14:21:38, `termination_reason: round_limit_reached`):

- **enumerate** (2 m 10 s): one document per dimension, shared by the read cache; 58 new claims.
- **propose** (4 dimensions; **3,681 claims considered**, 12 slices): **+93 criteria** —
  target_coverage +38, oral_bioavailability +20, metabolic_stability +13, toxicological_safety +22 —
  with 175 alternatives considered and rejected with reasons.
- **prune, iteration 1**: filter `kept 9 / to_refine 84`; distill `kept 9`; refine `revised 59 /
  withdrawn 19 / still_failing 6`; **merge `consolidated: 3`** — *the first consolidations in the
  project's history* (every prior round: `merged: 0`, `consolidated: 0`): 7 per-receptor potency
  criteria → **"Weakest required-receptor potency across the five tumour-microenvironment
  targets"**; 3 oral-bioavailability benchmarks → 1; 5 CTCAE grade ≥3 toxicity incidences →
  **"Worst reported treatment-emergent toxicity burden"**. Their adjudicator reasons are quoted in
  the iteration log §3.
- **prune, iteration 2**: filter `kept 12 / to_refine 44`; distill `kept 12`; refine
  (`batches_unresolved: 2` — failures counted, not hidden); **merge `consolidated: 1`**.
- **prune, iteration 3**: filter `kept 15 / to_refine 35`; distill `kept 11 / revised 4`;
  refine `revised 33 / withdrawn 1 / deferred 3`; **merge `consolidated: 2`** — six consolidations
  in the round.
- **promote**: `accepted: 28 / disputed: 14 / deferred: 0`. The disputed set includes the two
  consolidated, paper-shaped criteria named above (they await an expert decision; they are in the
  review queue, not in the scoring set).

**After the round** (endgame, this session): the criteria package was exported to
`design_audit/current_task_2026-10-15/`; the registry holds **93 registered criteria** (86 promoted
over the chain + 7 template-written) out of 208 pool lineages, with 41 literature-bound rules
deferred; **`rules@v2` was confirmed** (exploratory, pending items listed) as the freeze; the
registered screen ran as `run_01M4ZZ4Z5KN0ZTET43J9E3GFR6` (`--seed 0 --workers 4`).

**State at the time this package was committed, and the deferral decision that followed.** Screen
attempt 1 (`run_01M4ZZ4Z5KN0ZTET43J9E3GFR6`) ran under `rules@v2`; its assess stage planned
**171,558 candidate×rule cells** (3,177 candidates — six times the Oct-14 sweep's cells, because the
criteria set grew from 40 registered to 93), and it crawled: the run attempted a per-candidate
literature pass, the literature sources rate-limited it (569 `rate_limited` errors in fifteen
minutes), and it moved at ~6 cells/min. It was stopped at 16:32. **`rules@v3` was then confirmed
with `literature_retrieval` deferred** — the same holding-out the Oct-14 baseline used, and the
decision `improvement_plan.md` explicitly left to the project owner ("the literature evidence pass:
on the ~99 ranked compounds only, or skip it this round?"). The literature pass remains **not run**
and is reported as outstanding; the deferral is a policy recorded in the frozen set, not a code
change. Screen attempt 2 (`run_01M506J2Q5GK32R0GQ7R035M90`, `--seed 0 --workers 4`, `rules@v3`) is
running as of this commit.

**The board and the reference compound's rank are not in this commit**; they are added in a
follow-up commit when attempt 2 completes, and nothing in this document estimates them. The
criteria package under `design_audit/current_task_2026-10-15/` was exported before any board
existed (`with_board=True` will pick it up on the re-export that follows).

## 2. What to run next, in order

The endgame commands, in order (identical to the iteration log's §7):

1. `criteria export TASK` — write the reviewable criteria package into `design_audit/`.
2. `review adjudicate TASK` — resolve the open queue items (DeepSeek roster, unattended).
3. `rules confirm TASK` — freeze `rules@v2` over the new criteria (`--allow-pending` only if it
   refuses; the set then records which items were pending and reads `exploratory`).
4. `run start TASK --seed 0 --workers 4` — the registered screen over the 3,177-candidate universe.
   (The Oct-14 21:03 attempt ended after 1,913 candidates without completing; run it to
   `run.completed` this time.)
5. `board show TASK --all` — the rank readout for the reference compound.
6. `recovery intake TASK --from <sealed list>.json` then `recovery report TASK` — the CQA recovery
   measurement. **The list is evaluator-only and still sealed**; the template is at
   `/home/yiwei3_duke/anny/cqa_intake_template.json` (outside the repository, deliberately).

## 3. Known gaps, stated plainly

- **Merge/consolidate does not reduce.** The last completed reduce round (Oct 14, `run_01M4Y0ZAY…`)
  went 45 → 33 promoted with `merged: 0`, `consolidated: 0`; five groups were refused on schema
  (adjudicator output failing its own validator: missing `attribute.name`, missing
  `applicability_rationale`, no supporting claims cited) and three were kept separate as genuinely
  distinct quantities. Nothing was fixed today by operator instruction; the reduction-to-a-small-set
  question is open and the failure mode is specific and reproducible from the stage records.
- **Provider flakiness.** DeepSeek intermittently stalls mid-body (documented in
  `models_round3.toml`); today it caused reader hangs of 6+ minutes and rate-limited finder calls.
  The roster's timeouts now fail these fast (`deepseek_exact` 120 s, `deepseek_reasoning` 600 s).
- **Reading depth in rounds 6–11 is deliberately shallow** (`max_documents` 20 → 1) and round 5's
  reading was served partly by a substituted model for exactly one document (all recorded in the
  iteration log §4). The inherited-claims mechanism (below) is what carries the deeper round-5
  reading into the pool.
- **The old serving session is unrecoverable as-is** (422 request-shape error independent of the
  account hold); a new session must be used.
- `mas_audit.md` announces a sealed Section 6 that is absent from the file (found while drafting
  the docs section).

## 4. Module reference

Every module of `src/mas` (49 files, ~22,700 lines) at commit `9912dbb`. Entries state what the module is, entry points with `file:line`, the records it owns, current state, and the invariants a changer must not break. The five subsections are independent and follow dependency order.

### Module section A — core foundation modules

Read at commit `9912dbb` (main, clean tree) on 2026-10-15. Files were read in full; line numbers are from that commit. Design-doc section numbers quoted below come from the modules' own docstrings, not from the design docs.

### `journal` — `src/mas/core/journal.py`
- **What it is**:
  - The event journal (C1): append-only streams stored in the store's `events` table (journal.py:1-6).
  - One contiguous `seq` space per stream, assigned by the write path at insert time (journal.py:121-126).
  - Declared "the only source of truth (ADR-01)"; every other view is a fold over committed events (journal.py:3-4).
  - Streams are run/task/group/case plus the store-level `eval` stream (journal.py:20-21).
- **Entry points**:
  - `Event` — frozen dataclass, journal.py:24-58.
    - Fields include `state_from`/`state_to`, `termination_reason`, `question`, `summary`, `progress`, `budget`, `artifact_links`, `visibility`, `vocabulary_version` (journal.py:33-47).
    - `to_record` — journal.py:49-52; `from_record` — journal.py:54-58.
  - `actor(kind, actor_id, role=None, **extra)` — journal.py:61-66; validates `actor_kind` against vocab (journal.py:63) and drops `None` extras (journal.py:65).
  - `_check_stream` — journal.py:69-71; accepts exact `"eval"` or a prefix in `("run_", "task_", "grp_", "case_")` (`STREAM_PREFIXES[:-1]`, journal.py:70).
  - `Journal.append` — journal.py:78-114; validates event kind, actor kind, visibility, both execution states and the termination reason before taking the lock (journal.py:100-107), then delegates under `store.write_lock` (journal.py:109).
  - `Journal._append_locked` — journal.py:116-156.
    - `BEGIN IMMEDIATE` (119); `seq = max(seq)+1` for the stream (121, 126).
    - `payload_hash = sha256_hex(payload)` (133); insert of the canonical body plus `body_hash` (147-151); `ROLLBACK` on any `BaseException` (153-155).
  - `Journal.replay(stream_id, from_seq=1, to_seq=None)` — journal.py:158-166.
  - `last_seq` — journal.py:168-170; `streams(prefix)` — journal.py:172-176; `of_type(event_type, stream_prefix)` — journal.py:178-186; `verify(stream_id)` — journal.py:188-198.
- **Records/artifacts it owns**:
  - Rows of the `events` table only (insert at journal.py:147-151).
  - Event kinds are closed by `vocab.EVENT_KINDS` (83 kinds, vocab.py:310-337).
  - Every row carries `body` (canonical JSON) and `body_hash` (sha256 of the record, journal.py:150).
  - `visibility` is a vocab domain value (journal.py:46, vocab.py:191).
- **Current state**:
  - Implemented and tested: contiguity per stream, append-only enforcement, kind/state/stream validation and payload-hash round-trip are pinned in tests/test_foundation.py:107-150.
  - `criteria_export` re-verifies a stream on open (`self._journal.verify(stream_id)`, criteria_export.py:112).
  - `grp_` streams are accepted by `_check_stream` and `group.*` kinds are registered (vocab.py:327), but no code path in `src/mas` appends to a `grp_` stream or emits a `group.*` event as of this reading (grep repo-wide; `grp_default` at task.py:11 is a task-context field, not a stream).
  - The `case_` stream is written by recovery (recovery.py:126-127, 242).
- **Handoff notes**:
  - Single-writer invariant: every append must hold `store.write_lock` and take `BEGIN IMMEDIATE` on the same SQLite connection (journal.py:109, 119).
    - Any SQL writing `events` outside this path can interleave and break `seq` contiguity, which `verify` treats as corruption (journal.py:194-195).
    - `store.db` runs with `isolation_level=None` (store.py:198), i.e. autocommit — transaction control is the caller's job, as done here.
  - `verify` re-hashes the whole stored body but never recomputes `payload_hash` separately (journal.py:191-197); payload integrity rides on `body_hash` only.
  - `parent_seq`/`cause_seq` are stored on the event but only `broker.py` ever sets them (broker.py:206, 212, 220, 226, 237, 285) and nothing in `src/mas` reads them (grep for `.parent_seq`/`.cause_seq` outside this file returns no reader) — the causal-link fields are write-only today.
  - `Event.from_record` rebuilds via `cls(**record)` (journal.py:58): a record missing a newer field silently takes the dataclass default, including `vocabulary_version = vocab.VOCABULARY_VERSION` (journal.py:47) — old events read back under the current vocabulary version.

### `artifacts` — `src/mas/core/artifacts.py`
- **What it is**:
  - The artifact store (C3): content-addressed, write-once envelopes in the store's `artifacts` table (artifacts.py:1).
  - An artifact id is `art_` plus the first 12 hex chars of the sha256 of the canonical envelope `{kind, schema_version, vocabulary_version, payload}` (artifacts.py:20-27).
- **Entry points**:
  - `ArtifactStore` — artifacts.py:14-17.
  - `put(kind, payload, *, schema_version=1) -> str` — artifacts.py:18-29.
    - Stores identical content to the same id (docstring artifacts.py:19); takes `store.write_lock` (28); delegates to `_put_locked`.
  - `_put_locked` — artifacts.py:31-42.
    - Existing id with a different digest raises `ValueError("artifact id collision ...")` (34-36); otherwise a single INSERT (38-41).
  - `get(artifact_id)` — artifacts.py:44-48, returns the whole envelope, `KeyError` if absent.
  - `payload(artifact_id)` — artifacts.py:50-51; `of_kind(kind)` — artifacts.py:53-55, `(artifact_id, payload)` ordered by `created_at`.
- **Records/artifacts it owns**:
  - Rows of `artifacts` (schema at store.py:38-44, index on `kind` at store.py:45).
  - The `kind` argument is not validated against any registry (artifacts.py:18) — kinds are free strings.
  - Kinds written across the tree include `tool_result` (broker.py:281), `config_layers` (controller.py:147, derivation_run.py:155), `run_binding`, `derivation_record`, `trace` (models.py:484) and the two constants `INTAKE_KIND`/`COMPARISON_KIND` (recovery.py:54-55, 237, 782).
- **Current state**:
  - Implemented and tested: content addressing, dedupe and the write-once trigger are pinned in tests/test_foundation.py:155-163.
  - Two consumers withhold `tool_result` and `trace` artifacts from export (`WITHHELD_ARTIFACT_KINDS`, criteria_export.py:64).
  - No method re-verifies a stored body against the `sha256` column on read; integrity is checked only on insert (unclear from the code whether another surface re-verifies).
- **Handoff notes**:
  - The digest covers `vocabulary_version` (artifacts.py:23): bumping `vocab.VOCABULARY_VERSION` changes the id of identical payloads — identity is (content, kind, schema version, vocabulary version).
  - Write-once is enforced twice: this module never updates (only INSERT, artifacts.py:38-41) and SQLite triggers abort UPDATE/DELETE (store.py:58-61).
  - `_put_locked` opens no transaction of its own (contrast journal.py:119); it relies on `store.write_lock` (artifacts.py:28) and SQLite autocommit. Safe only while the lock is held.
  - Truncation to 48 bits (artifacts.py:27) makes collision detection the only guard; a collision raises rather than overwriting (34-36).
  - `get` re-parses the stored body with `json.loads` (artifacts.py:48) and returns the envelope; `payload()` is the accessor most callers want (artifacts.py:50-51).

### `store` — `src/mas/core/store.py`
- **What it is**:
  - The store root (design §14, §14.1): one SQLite database plus a root lock file, opened by one service host at a time (store.py:1-7).
  - Journal events and artifacts are made append-only by SQLite triggers, so no code path can rewrite or delete them (store.py:3-4).
  - A root can also be opened read-only, taking no lock, so a second surface can read a store a host is writing (store.py:9-13).
- **Entry points**:
  - `SCHEMA` — store.py:25-66: tables `events` (26-35), `artifacts` (38-44), `operator_log` (47-52); indexes `events_by_type` (36), `artifacts_by_kind` (45); six append-only triggers (54-65).
  - `StoreError(code, message)` — store.py:73-76; message is `"{code}: {message}"`. Codes in this file: `store_locked` (127), `read_only` (157, 161, 164), `store_root_missing` (189, 213), `store_root_unsupported` (192).
  - `unsupported_root_reason(path)` — store.py:96-105; refuses roots under sync-client folders (markers store.py:69) or on network filesystems (store.py:70, 103-105).
    - `_mount_fstype` reads `/proc/mounts` (Linux only; `None` elsewhere) — store.py:79-93.
  - `_RootLock` — store.py:108-143: exclusive OS lock on `<root>/store.lock` via `fcntl.flock` or Windows `msvcrt.locking` (115-128), released in `release` (130-143).
  - `_ReadOnlyConnection` — store.py:146-167.
    - Inspects the first SQL token: only `select|explain|with` and `pragma` without `=` are allowed (149, 155-157).
    - `executescript`/`executemany` always refused (160-164).
  - `Store` — store.py:170-179; in-process writer lock is `write_lock` (store.py:179).
  - `Store.open(root, *, create=True, allow_unsupported_root=False, read_only=False)` — store.py:181-206; `_open_read_only` — store.py:208-215 (SQLite URI `?mode=ro`, store.py:214); `close` — store.py:217-221; context manager — store.py:223-227.
- **Records/artifacts it owns**:
  - `store.db` and `store.lock` inside the root (store.py:198, 112), plus the three tables above.
  - `operator_log` is created with append-only triggers but no code path in `src/mas` inserts into it (grep for `operator_log` matches only store.py:47-65) — nothing writes it as of this reading; whether it is reserved for a future surface is unclear from the code.
- **Current state**:
  - Implemented and tested: a second host on the same root is refused (tests/test_foundation.py:87-98); sync-folder roots are refused (100-102); the append-only triggers are exercised at tests/test_foundation.py:120-128 and 155-163.
  - Read-only roots are the live path for the browser workbench (ui/server.py:173) and criteria export (criteria_export.py:118-120).
- **Handoff notes**:
  - PRAGMAs at open: `journal_mode=WAL`, `synchronous=FULL`, `foreign_keys=ON` (store.py:199-201).
    - The connection is `check_same_thread=False` (store.py:198), so Python-level serialization is `write_lock` (store.py:179), not sqlite3's thread check.
  - Read-only means: no creation (`create and not read_only`, store.py:186), no lock, and a connection whose writes raise `StoreError("read_only", ...)` before SQLite is reached (store.py:154-164).
    - The token check is a heuristic; SQLite's own read-only URI (store.py:214) is the actual backstop.
  - The root lock is released by the OS if the process dies (store.py:5-7), so a crash leaves no stale lock; `close` closes the connection first, then releases (store.py:217-221).
  - The unsupported-root test is a lowercased substring match on the resolved path (store.py:98-101) — a directory merely named like a sync folder is refused.
  - `allow_unsupported_root=True` bypasses that refusal (store.py:191-192).

### `runtime` — `src/mas/core/runtime.py`
- **What it is**:
  - The open core: one `Core` object bundling a store root with its journal and artifact store (runtime.py:1).
  - It is a plain dataclass of three fields, built only through `open` (runtime.py:13-24).
  - It is the composition point that decides which objects share one SQLite connection and one write lock (runtime.py:24, store.py:179).
- **Entry points**:
  - `Core` dataclass — runtime.py:13-17 (`store`, `journal`, `artifacts`).
  - `Core.open(root, *, read_only=False, **store_options)` — runtime.py:19-24.
    - Forwards `**store_options` to `Store.open` (runtime.py:23).
    - Constructs `Journal` and `ArtifactStore` over the store (runtime.py:24).
  - `read_only` property — runtime.py:26-28.
  - `close` — runtime.py:30-31.
  - Context manager (`__enter__`/`__exit__`) — runtime.py:33-37.
- **Records/artifacts it owns**:
  - None of its own; the docstring defines the root as holding "one store root with its journal and artifact store" (runtime.py:1).
  - Everything the journal and artifact store write is reachable through `core.journal` and `core.artifacts` (runtime.py:14-16).
- **Current state**:
  - Implemented; the universal handle passed through the codebase (cli/main.py:157, 261; ui/server.py:173; criteria_export.py:120).
  - Core modules take a `Core` rather than a `Store` (broker.py:120, projection.py:15).
  - Tests build several `Core`/`Store` objects over different roots in one process (tests/conftest.py:8 and 15 define the `store` and `core` fixtures).
- **Handoff notes**:
  - Read-only is a property of the store, not of the Core (runtime.py:27-28): there is no per-call read-only mode.
    - Any code given a `Core` inherits the flag, and every write raises `StoreError("read_only", ...)` (store.py:157).
  - `Store.open`'s `create` default is `True` (store.py:182) — opening a nonexistent path not in read-only mode creates the directory.
  - `Core.open(read_only=True)` refuses a root whose `store.db` is missing (store.py:212-213) rather than creating one.
  - Nothing here holds global state; closing the Core releases the root lock through `Store.close` (runtime.py:30-31, store.py:217-221).

### `canonical` — `src/mas/core/canonical.py`
- **What it is**:
  - One canonical serialization and hashing form for every hashed record: UTF-8, NFC, LF line endings inside strings, sorted keys, no insignificant whitespace, shortest round-trip float formatting (canonical.py:1-8).
  - Record hashes, payload hashes, fingerprints and projection hashes use it; files people supply are hashed on raw bytes instead (canonical.py:6-7).
- **Entry points**:
  - `CANONICAL_FORM_VERSION = "canon-1"` — canonical.py:18.
  - `_normalize` — canonical.py:21-45.
    - Rejects non-finite floats (27-28); normalizes `\r\n`/`\r` to `\n` and NFC-normalizes strings (30-32).
    - Requires string dict keys (36-37); refuses keys colliding after NFC (39-40); raises `TypeError` for any other type (45).
  - `canonical_bytes` — canonical.py:48-56 (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, `allow_nan=False`); `canonical_text` — canonical.py:59-60.
  - `sha256_hex(value)` — canonical.py:63-65.
  - `raw_sha256(data)` — canonical.py:68-70 (`content_hash`, design §12.4); `text_sha256(text)` — canonical.py:73-75 (`text_hash`, design §14.2).
- **Records/artifacts it owns**:
  - No storage and no writes.
  - It defines the bytes that `events.body_hash` (journal.py:150), `artifact_id` (artifacts.py:26), `Config.hash` (config.py:362) and `constants_hash` (constants.py:76) are computed over.
- **Current state**:
  - Implemented and tested: key-order/LF equivalence, NFC equivalence, refusal of NaN and non-string keys, and the raw-vs-text hash split are pinned in tests/test_foundation.py:16-38.
  - `CANONICAL_FORM_VERSION` is defined here and referenced nowhere else in `src` or `tests` (grep), so nothing stamps or compares it today.
  - `raw_sha256`/`text_sha256` have no call site in `src/mas` outside this module as of this reading (grep); they are exercised only by tests/test_foundation.py:37-38.
- **Handoff notes**:
  - `bool` is checked before `int` (canonical.py:22-24) so `True` can never serialize as `1`.
  - Adding a new value type to any hashed payload requires adding it to `_normalize` first, or hashing raises `TypeError` (canonical.py:45) — deliberate, not an accident of `json.dumps`.
  - NaN/infinity have no canonical form and raise `ValueError` (canonical.py:27-28).
    - A payload that could carry one (e.g. a float from a model) must be sanitized before it reaches a hash or an artifact.
  - Two logically different dicts whose keys collide after NFC normalization raise (canonical.py:39-40) rather than silently dropping one.
  - `raw_sha256` is the only function that hashes input bytes unchanged, and it is the one intended for user-supplied files (canonical.py:68-70).

### `clock` — `src/mas/core/clock.py`
- **What it is**:
  - Time helpers for the core: a UTC wall-clock string (`utc_now`) and a monotonic reading for durations (`monotonic_s`) (clock.py:1, 9-16).
  - The module exists so that timestamp formatting lives in one place (design §14.2 per the docstring, clock.py:1).
  - Both functions are pure; the module holds no state.
- **Entry points**:
  - `utc_now()` — clock.py:9-12.
    - `%Y-%m-%dT%H:%M:%S.` plus `microsecond // 1000` zero-padded to 3 digits plus `Z` (clock.py:12).
  - `monotonic_s()` — clock.py:15-16: `time.monotonic()`.
- **Records/artifacts it owns**:
  - No storage and no writes.
  - Its strings become `recorded_at` on events (journal.py:122, 128) and `created_at` on artifacts (artifacts.py:40).
  - They also become `requested_at`/`retrieved_at` in broker provenance (broker.py:252, 257).
  - Payload fields named `recorded_at` elsewhere come from here too (recovery.py:235).
- **Current state**:
  - Implemented; `utc_now` is imported by journal.py:16, artifacts.py:10 and broker.py:18.
  - `monotonic_s` has no caller anywhere in `src` (grep) — broker measures latency with `time.monotonic()` directly (broker.py:197, 238).
  - So `monotonic_s` is currently dead code.
- **Handoff notes**:
  - `utc_now` truncates to milliseconds (clock.py:12): two calls inside one millisecond compare equal.
    - It must not be used for ordering within a stream — `seq` is the order (journal.py:159, 165).
  - The format is fixed-width with a `Z` suffix, so lexicographic comparison orders timestamps correctly.
    - Any change to precision must keep that fixed width, since views sort by these strings (artifacts.py:54 `ORDER BY created_at`).
  - Timestamps are wall-clock UTC, not monotonic.
    - Durations must use `monotonic_s` (or `time.monotonic`, as the broker does), never differences of `utc_now` strings.

### `ids` — `src/mas/core/ids.py`
- **What it is**:
  - Opaque identifiers: a registered type prefix plus a 26-character ULID (`prefix_<ULID>`, ids.py:1, 26-40).
  - Prefixes are registered in the module and an identifier with any other prefix is refused (ids.py:11-12, 37-39).
  - Also `base@vN` versioned references and a slug function for slug-based ids (ids.py:47-69).
- **Entry points**:
  - `PREFIXES` — ids.py:12-23, a frozenset of 52 prefixes.
    - Comments mark the iteration-2 and later additions (`cri`, `expr`, `adj`, `clp`, `hci`, `cal`, ids.py:17-22).
  - `ulid(timestamp_ms=None)` — ids.py:26-34: 48-bit milliseconds + 80 random bits rendered in Crockford base32 (9, 29-34).
  - `new_id(prefix)` — ids.py:37-40; raises `ValueError` on an unregistered prefix (38-39).
  - `prefix_of(identifier)` — ids.py:43-44 (split on the first `_`).
  - `versioned(base, version)` — ids.py:47-51.
  - `split_version(ref)` — ids.py:54-61 (regex `^(?P<base>.+)@v(?P<version>\d+)$`).
  - `slug(text)` — ids.py:64-69.
- **Records/artifacts it owns**:
  - No storage; it fixes the spelling of every id used in events, artifacts and payloads.
  - Examples: `new_id("evt")` (journal.py:126), `new_id("inv")` (broker.py:189), `new_id("task")` (task.py:37).
- **Current state**:
  - Implemented and tested (tests/test_foundation.py:43-56): ULID length/order, unregistered prefix refused, versioned round-trip, slug.
  - Some registered prefixes have no constructor call in `src` (grep for `new_id("ses")`/`"mem_"`/`"oq_"` finds none) — reserved ahead of use, or leftover; unclear from the code.
  - `versioned`/`split_version` have no caller in `src` outside this module either.
  - Versioned refs are built by f-string elsewhere (controller.py:155, `f"{task_id}@v{context['version']}"`), duplicating the format this module defines.
- **Handoff notes**:
  - Adding an id family requires editing `PREFIXES` (ids.py:12); `new_id` is the only sanctioned constructor and refuses otherwise (38-39).
  - `ulid` is time-sortable across milliseconds but not monotonic within one millisecond (80 random bits, ids.py:29) — id order is not event order; `seq` is.
  - `prefix_of` splits on the first underscore (ids.py:44), so a prefix must not contain `_`.
  - `slug` replaces runs of non-`[a-z0-9]` with `-`, strips edges, and refuses empty results (ids.py:64-69).
    - This matches the docstring's `attr_<slug>`/`grp_<slug>` spelling (ids.py:65-68).
  - `split_version` matches greedily on `.` before `@v` (ids.py:54-61), so a base containing `@v` would split at the last occurrence; whether that is intended is unclear from the code.

### `vocab` — `src/mas/core/vocab.py`
- **What it is**:
  - The state registry (C2): the closed vocabularies of design §0.4 with their UI labels and tones, validated on write (vocab.py:1-6).
  - A value outside a registered domain raises `VocabularyViolation` (vocab.py:13-14, 346-354).
  - It also holds the closed set of event kinds (vocab.py:308-337) and the completion-event set (vocab.py:339-343).
  - Labels and tones come from `ui_ux_spec.md` §13 so no surface remaps a state (vocab.py:4-5).
- **Entry points**:
  - `VOCABULARY_VERSION = "vocab-1"` — vocab.py:10 (stamped into every event, journal.py:47, and every artifact envelope, artifacts.py:23).
  - `DOMAINS: dict[str, dict[str, tuple[str, str]]]` — vocab.py:25-296 (55 domains as of this reading).
    - `_domain` gives values a de-underscored label and `"neutral"` tone (17-18); `_labelled` takes explicit `(label, tone)` pairs (21-22).
  - `require(domain, value)` — vocab.py:346-354; `require_event_kind(kind)` — vocab.py:357-360; `label` — vocab.py:363-365; `tone` — vocab.py:368-370; `is_terminal(state)` — vocab.py:373-375.
  - State sets: `TERMINAL_EXECUTION_STATES` (301), `RUN_STATES` (302-305), `RUN_TERMINAL_STATES` (306).
  - `EVENT_KINDS` — 83 kinds, vocab.py:310-337; `COMPLETION_EVENTS` — 8 kinds, vocab.py:340-343.
- **Records/artifacts it owns**:
  - No storage; it is the write-time gate. Callers: `journal.append` validates event kind, actor kind, visibility, both execution states and termination reason (journal.py:100-107).
  - The broker validates `tool_outcome` and `absence_reason` (broker.py:229, 272); `task.validate` validates `task_mode` (task.py:24).
  - Review and adjudication validate their own domains (review.py, adjudication.py).
- **Current state**:
  - Implemented; the registry is the single validation point and it is versioned (vocab.py:10).
  - Several domains carry long why-comments recording measured defects and why a value is or is not registered: `evidence_kind` (68-91, the `peer_reviewed_primary` defect of 14 October 2026), `machine_adjudicated` (143-145), `adjudication_route` (153-164), `bound_grant_verdict` (165-172), `criterion_change_operation` (230-239), `criterion_family_aggregation` (240-271, six values removed the day they were added).
  - Known registry/consumer mismatch: `group.*` kinds are registered (vocab.py:327) with no emitter (see `journal` above).
- **Handoff notes**:
  - `verdict.pass_` is the Python-safe spelling; vocab.py:299 restores the registered value `"pass"` by pop/insert — do not reorder or reformat that line, and never register a domain value literally named `pass_`.
  - `label`/`tone` call `require` first (vocab.py:364, 369), so a surface cannot render an unregistered state.
  - `COMPLETION_EVENTS` is documented as "the only events that may increase a `completed` counter" (vocab.py:339); a new event intended to count toward completion must be added there.
  - `evidence_kind` (vocab.py:92-101) is deliberately not computed from installed adapters: the why-comment (73-91) says the closed list means "no such kind anywhere" while `evidence.producible_evidence_kinds` answers "no tool for it here".
    - A test (`tests/test_predict_admet.py` per that comment) pins the two together; the core may not import an adapter to compute the domain.
  - Adding a domain value is a vocabulary change: `VOCABULARY_VERSION` should move with it, and that changes artifact ids for identical payloads (artifacts.py:23).
  - `_domain` also fixes the tone to `"neutral"` for the values it builds (17-18); a value that needs `attention` or `negative` must be declared through `_labelled`.

### `constants` — `src/mas/core/constants.py`
- **What it is**:
  - Registered constants (design §8.4): every number that can affect a published verdict or a host behaviour is registered as a `constant.registered` event in a scope, and read back by latest registration (constants.py:1, 43-63).
  - `CORE_DEFAULTS` supplies the value for a run that registered nothing (constants.py:13-40).
- **Entry points**:
  - `SCOPES = ("core_policy", "adapter_policy", "case_configuration")` — constants.py:11.
  - `CORE_DEFAULTS: dict[str, tuple[Any, str]]` — constants.py:14-40; 18 entries as of this reading (7 core-policy/host constants, `const_mandated_coverage_floor`, 10 symbolic-regression constants).
  - `register(core, const_id, value, *, unit, scope, cutoff_basis, set_by, stream_id=EVAL_STREAM)` — constants.py:43-53.
    - Refuses ids not starting `const_` (45-46) and unknown scopes (47-48).
    - Appends `constant.registered` to the eval stream by default (44, 51).
  - `current(core, const_id, stream_ids=(EVAL_STREAM,))` — constants.py:56-63; returns the latest registration, scanning streams in the given order.
  - `value(core, const_id, stream_ids)` — constants.py:66-72; falls back to `CORE_DEFAULTS`, then raises `KeyError` (70-72).
  - `constants_hash(records)` — constants.py:75-76; sha256 over the records sorted by `const_id`.
- **Records/artifacts it owns**:
  - `constant.registered` events on the eval stream (or a caller-supplied stream).
  - Payload is `{const_id, scope, value, unit, cutoff_basis, set_by, sensitivity_tested}` (constants.py:49-50).
- **Current state**:
  - Implemented; registered values are the run's numbers: the settings layer registers every setting carrying a `const_id` before a run uses it (config.py:470-481, called at controller.py:178-179 and derivation_run.py:170-171).
  - The broker reads `const_tool_retry_limit` (broker.py:195); the ranking floors are read per run (controller.py:610-614); the symbolic-regression step reads its whole knob set from `(EVAL_STREAM, run_id)` (sr_stage.py:669-676).
  - `sensitivity_tested` is written only as `{"yes": False}` (constants.py:50) and no code path updates it (grep: the only occurrence in `src` is that line).
- **Handoff notes**:
  - `value()` never fails silently: an unregistered id must exist in `CORE_DEFAULTS` or be registered, else `KeyError` (constants.py:72) — adding a constant means touching this dict or guaranteeing registration.
  - Resolution order is streams in argument order (later stream wins) then later `seq` within a stream (constants.py:58-62).
    - A run-scoped registration therefore must be in a stream listed after the eval stream to override it — which is why controller.py:611-614 and sr_stage.py:669 pass `(EVAL_STREAM, run_id)`.
  - `constants_hash` sorts by `const_id` (constants.py:76), so the hash is independent of registration order.
  - `register` writes `set_by` both as a payload field and as the event actor (constants.py:49-51); `cutoff_basis` is free text from the caller (config.py:475-476 passes `operator_configuration`).
  - `current` replays every listed stream in full on each call (constants.py:59-62); there is no cache in this module, so a hot path reading many constants repeatedly pays for it (sr_stage reads nine at once, sr_stage.py:675-676).

### `config` — `src/mas/core/config.py`
- **What it is**:
  - Layered run settings (design §14.1): flat dotted keys with a declared type/range/choices, resolved through `code defaults -> preset -> ./mas.toml -> profile -> MAS__SECTION__KEY env -> --set k=v` (lowest precedence first, config.py:4-6).
  - The resolved values are hashed, and `layer_record()` says which layer produced each value (config.py:14-15).
  - The command line deliberately outranks the environment (config.py:8-9).
  - `providers` and `roles` stay free-form tables and are merged table-by-table in the same layer order (config.py:11-12).
- **Entry points**:
  - `LAYERS` — config.py:28; `ENV_PREFIX = "MAS__"` (30), `PROJECT_FILE = "mas.toml"` (31), `PROFILE_DIR = ~/.config/mas/profiles` (32); `ConfigError` — config.py:35-36.
  - `Setting` — config.py:39-48 (`default`, `doc`, `minimum`, `maximum`, `choices`, `unit`, `const_id`, `item_type`); `SETTINGS` — config.py:58-235, with the comment "Every setting here is read by the code" (config.py:56).
  - `PRESETS` — config.py:239-254 (`quick`, `standard`, `deep`); `CHECKPOINTS` — config.py:237.
  - `_flatten` — config.py:259-268; `_coerce` — config.py:271-289; `_check` — config.py:292-313; `_env_overrides` — config.py:316-325; `parse_overrides` — config.py:328-339; `_load_toml` — config.py:379-383.
  - `Config` — config.py:342-376.
    - `__getitem__`, `get`, `section` — config.py:351-359.
    - `hash` — config.py:361-362 (sha256 over values+providers+roles).
    - `layer_record` — config.py:364-368 (every value with the layer that produced it).
    - `registered_constants` — config.py:370-373; `non_default` — config.py:375-376.
  - `resolve(*, preset, project_file, profile, profile_dir, overrides, environ, extra_tables)` — config.py:386-436.
  - `validate` — config.py:439-465; `register_constants(core, config, *, by, stream_id=None)` — config.py:470-481; `estimate(config, *, dimensions, candidates)` — config.py:484-504 (offline `--dry-run` estimate; no network, no model calls).
- **Records/artifacts it owns**:
  - Reads `./mas.toml` (config.py:31, 411-419) and `<profile_dir>/<profile>.toml` (412-418); writes nothing itself.
  - `layer_record()` is stored as the `config_layers` artifact (controller.py:147, derivation_run.py:155).
  - `register_constants` writes `constant.registered` events with `scope="core_policy"` and `cutoff_basis="operator_configuration"` (config.py:475-479).
- **Current state**:
  - Implemented and tested: layering precedence, type/range/unknown-key refusal, cross-field checks, hash/layer record, role binding and the soft-cap behaviour are pinned in tests/test_config_and_providers.py:22-96.
  - The configured stage order is pinned against the library default (tests/test_config_and_providers.py:256); the literature volume bands at 278.
  - `validate` imports `mas.adapters.literature.registry` inside the function (config.py:457-461) — a core-to-adapter dependency at validation time, against the core package docstring "no domain vocabulary" (src/mas/core/__init__.py:1).
  - No module outside `config.py` reads `interaction.mode` or `interaction.checkpoints` (grep over `src/mas`).
  - Nothing writes a run or step state `paused` or `waiting_human` (no literal occurrence in `src/mas`; the only variable-driven `state_to=` sites can produce only `unresolved` or `completed`, controller.py:629-631, derivation_run.py:243-244) — the checkpoint-pause behaviour these settings describe is validated but not wired into the run path as of this reading.
- **Handoff notes**:
  - Precedence is fixed by the code order at config.py:410-426: project, then profile, then `extra_tables` (in dict order), then environment, then `overrides`. Moving a layer changes reproducibility (config.py:8-9).
  - `_coerce` types from `type(setting.default)` (config.py:275): a setting whose default is an `int` cannot be given a fractional value from env/CLI unless the default is a float.
    - `_check` widens int→float for float settings (295-296) but `_coerce` does not, so the default's declared type is the contract.
  - `sources[key]` records the winning layer (config.py:403), which is what `layer_record()` and `non_default()` rely on (364-376).
  - `resolve` applies one implication: `interaction.mode == "autonomous"` sets `interaction.autonomous_adjudication` true unless that key was explicitly set by any layer (config.py:427-432) — an explicit `false` beside autonomous mode is honoured.
  - `validate` cross-checks are not additive with `_check`: select+holdout ≤ 0.7; `rank.method == "symbolic_expression"` requires `sr.mode` ≠ off; checkpoints must be known; autonomous mode cannot list checkpoints and cannot coexist with autonomous adjudication (config.py:442-456).
  - `Config.hash` covers values+providers+roles and not layer provenance (config.py:361-362): two runs reaching the same values by different layers hash equal, and `layer_record()` is what separates them.
  - Long why-comments encode decisions a new agent must not silently reverse: `search.volume`/`textbook.volume` bands (config.py:76-83); the `criteria.stages` merge-order defect and its test pin (126-136); `assess.max_reference_exclusion_share` (149-163); `rank.mandated_coverage_floor` (170-180); `concurrency.read_workers` and why it carries no `const_id` (210-223).

### `budget` — `src/mas/core/budget.py`
- **What it is**:
  - The budget and cost accountant (C6): per-class caps charged before work for countable classes (tool calls, model turns), and recorded after the fact for provider spend, whose cost is known only on return (budget.py:1-7).
  - Whether reaching a cap stops a run is per class: soft classes keep going and report each threshold crossed; hard classes refuse further work (budget.py:4-7).
- **Entry points**:
  - `Budget(envelope=None, *, soft_kinds=(), warn_at=None)` — budget.py:16-27.
    - Only positive numeric caps are kept (21-22), so `0` or a non-number means "uncapped but counted" (docstring budget.py:17).
  - `try_charge(kind, amount=1)` — budget.py:29-36: returns `False` only for a hard class over its cap (33-34); a soft class always charges and returns `True`.
  - `allows(kind)` — budget.py:42-44; `remaining(kind)` — budget.py:63-65 (None when uncapped); `exhausted(kind)` — budget.py:67-69.
  - `record(kind, amount)` — budget.py:46-61: charges after the fact and returns the threshold levels newly crossed, each at most once per Budget instance (55-61).
  - `snapshot()` — budget.py:71-73.
  - `from_config(config, *, envelope=None)` — budget.py:76-82.
    - Reads `budget.usd_max`, `budget.llm_turns`, `budget.tool_calls` (78-79); lets an explicit envelope win per class (80).
    - Marks `usd` soft only under `budget.on_exhaust == "warn_continue"` (81).
- **Records/artifacts it owns**:
  - No events or artifacts; `snapshot()` is embedded in run summaries (derivation_run.py:237 sets `record["budget"] = budget.snapshot()`).
  - The event field `Event.budget` (journal.py:44) carries the latest budget state for the projection fold (projection.py:28).
- **Current state**:
  - Implemented and used on the live paths: the CLI builds the per-run budget (cli/main.py:313-319, 375-380).
  - The broker charges `tool_calls` before a call and maps refusal to `absence_reason="budget_exceeded"` (broker.py:186-188).
  - The model adapter charges `llm_turns` before a turn (models.py:450, 475) and `usd` after, reporting crossed levels and whether the run continues (models.py:497-502).
  - Soft-cap warn-and-continue versus hard-cap refusal is pinned in tests/test_config_and_providers.py:96.
- **Handoff notes**:
  - Charge-before-work is the invariant for countable classes: the broker checks before recording `tool.requested`, and retries are covered by the single charge (broker.py:186).
  - `record()` is deliberately non-refusing (budget.py:46); spend is discovered after the call, so the accountant reports and the caller decides via `allows()` (models.py:502) — do not make `record` refuse.
  - Caps are copied at construction (budget.py:21-22); mutating the envelope dict afterwards has no effect. `soft_kinds` is a frozenset (24); `warn_at` may be `None` (25), in which case only `cap` is reportable.
  - The instance lock (budget.py:27-28) guards `try_charge` and `record`; `remaining`/`exhausted`/`snapshot` read without it, so a snapshot taken concurrently may be one charge stale (unclear from the code whether a caller depends on that).
  - A budget is passed as `Any` and the broker only requires `try_charge` (broker.py:186); the model adapter guards `hasattr(budget, "allows")` (models.py:452) and `hasattr(budget, "record")` (models.py:495) — a duck-typed budget must provide at least those.

### `broker` — `src/mas/core/broker.py`
- **What it is**:
  - The tool broker and capability registry (C13): tools are resolved by capability and question kind, never by name (broker.py:1-7).
  - Every call passes pre-checks, is retried only for retryable error classes, and returns one of the registered outcomes with a provenance block (broker.py:3-5).
  - The docstring states the broker never writes claim status: a successful call is not a validation (broker.py:6-7).
- **Entry points**:
  - Domain-neutral kinds: `CAPABILITY_KINDS` (8 kinds, broker.py:24-27), `RETRYABLE` error classes (28), `STRENGTH_ORDER` (29), `VALUE_KIND_STRENGTH` (30).
  - `ToolContract` — broker.py:33-59.
    - Validates `capability_kind` and `claim_strength_ceiling` in `__post_init__` (55-59).
    - Carries versions, purpose, `evidence_kind_produced`, `determinism`, `cost_latency_class`, `timeout_ms`, `license_id`, `side_effect_class`, `execution_location`, platform support and `required_inputs`/`identity_inputs` (42-53).
  - `ToolError` — broker.py:62-70 (runtime failure after pre-checks; retryable default from `RETRYABLE`, 69).
  - `ToolAbsent` — broker.py:73-80 (pre-check failure; carries `absence_reason` and `required_inputs_manifest`).
  - `ProviderResponse` — broker.py:83-91; `Provider` protocol — broker.py:94-97; `ToolResult` — broker.py:100-116 (`.ok` is `outcome in ("ok", "partial")`, 114-116).
  - `Broker(core, *, sleep=time.sleep, platform="linux")` — broker.py:119-125.
  - `register` — broker.py:128-129; `contracts` — 131-132; `manifest()` — 134-138 (used at controller.py:166 for the run's tool-availability snapshot).
  - `resolve(capability, question_kind)` — broker.py:140-144 (matches either the adapter capability id or the core capability kind).
  - `call(stream_id, capability, question_kind, inputs, *, requesting_actor, ids=None, budget=None, required_value_kind=None, tool_ids=None)` — broker.py:147-168.
    - `tool_ids` restricts/orders providers (154-156); `required_value_kind` filters by `claim_strength_ceiling` (157-159).
    - No providers → a recorded `not_attempted` with `absence_reason="not_configured"` (160-162); returns the first attempted result, else the last decline (163-168).
  - `_call_one` — broker.py:170-242: cache lookup (172-174), missing-input pre-check (175-182), platform check (183-185), budget charge (186-188), `tool.requested` event (190-194), retry loop (198-239), result caching for ok/partial/empty (240-242).
  - `_record` — broker.py:244-290: builds invocation and provenance (247-264), puts the `tool_result` artifact (281), appends `tool.returned` or `tool.errored` (282-289).
- **Records/artifacts it owns**:
  - `tool_result` artifacts (broker.py:281) with payload fields `invocation`, `outcome`, `values`, `records`, `provenance`, `error`, `absence_reason`, `required_inputs_manifest`, `warnings`, `evidence_kind`, `claim_strength_ceiling`, `supports_claim: None`, `record_state: "returned"` (273-280).
  - Events `tool.requested` (190), `tool.retry_scheduled` (211), `tool.returned`/`tool.errored` (282).
  - Result ids are `res_<invocation_id>` (266).
- **Current state**:
  - Implemented and the most-exercised core module in tests: retry delays and retryable classes, platform refusal, absence reasons, outcome and ceiling validation are covered across tests/test_evidence.py:33-74, 235-368, tests/test_drug_adapter.py:461-471, tests/test_calibration_guard.py:249, 364, tests/test_symbolic.py:652, 713.
  - Live callers: `reading.py` (search 419-422, read 472-474, both with `tool_ids`) and `evidence.py:419-420` (per-route calls; a `budget_exceeded` decline raises `BudgetBlocked` so a cell is not assessed on a partial route set, evidence.py:421-425).
- **Handoff notes**:
  - Provenance is assembled from the contract plus the response (broker.py:255-264); a provider cannot set those fields itself — a new provider returns a `ProviderResponse` only (83-97).
  - The response values are checked for one thing: a `value_kind` stronger than the contract's `claim_strength_ceiling` raises `ValueError` after the call (broker.py:230-233).
    - That is an unmatched-provider contract violation and is not recorded as a failed result; it propagates.
  - Non-`ToolError`/`ToolAbsent` exceptions from a provider are caught and recorded as `internal_error` so a provider bug never crashes the run (broker.py:222-227).
  - Retries: only when `error.retryable` and `attempt < const_tool_retry_limit` (read from registered constants, broker.py:195, 209); delay is `min(30, 0.5*2^(n-1))` times a 0.5–1.5 jitter (210); each retry appends `tool.retry_scheduled` with the delay (211-213).
  - The result cache is in-memory per `Broker` (broker.py:125), keyed by tool id + contract version + question kind + canonical input hash (172).
    - A cache hit returns the earlier `ToolResult` with no new event and no new artifact (173-174), so a replayed call is not separately journaled; whether that is intended is unclear from the code.
  - `ToolResult.ok` treats `empty` as not ok (broker.py:115) while the cache stores `empty` too (240); callers distinguishing "no records" from "failed" must read `outcome`, as `evidence.py:429` does.
  - `resolve` matches case-sensitively on exact strings for capability and question kind (broker.py:141-144); registering a provider whose capability no caller names is silent (no validation against a registry here).
  - The broker is the only writer of `parent_seq` today (broker.py:206, 212, 220, 226, 237, 285) — see the `journal` section.

### `projection` — `src/mas/core/projection.py`
- **What it is**:
  - The progress projection (C17): a pure fold over one run's journal producing the progress view (projection.py:1).
  - It deliberately reports no cross-stage percentage: each scope carries its own denominator kind, a percentage is given only for `enumerated_fixed`, and the budget is a separate meter (projection.py:3-4).
- **Entry points**:
  - `progress(core, run_id) -> dict` — projection.py:15-43, the module's only function.
  - Fold inputs: latest `run.*` state with `state_to` and termination reason (23-25); `event.progress` rows keyed by scope (26-27); latest `event.budget` (28-29).
  - Fold inputs, continued: counts of `candidate.assessed` `payload["verdict"]` (30-32); latest `leaderboard.snapshot_published` `payload["snapshot_id"]` (33-34).
  - Percent is computed only when `denominator_kind == "enumerated_fixed"` and `planned` is truthy (38-39).
  - Returns state, `state_label` via `vocab.label("execution", state)` (41), termination reason, rows, budget, verdict counts, `last_activity_at`, `snapshot_id` (41-43).
- **Records/artifacts it owns**:
  - None; it reads the `progress` and `budget` fields of events (journal.py:43-44) and the payloads of `candidate.assessed` and `leaderboard.snapshot_published` (vocab.py:323).
- **Current state**:
  - Implemented; used by the CLI (cli/main.py:670) and the browser view (ui/views.py:322-323).
  - Pinned by tests/test_ui.py:212 ("the run page is the progress projection with the budget apart").
  - Progress payload writers today are all in `controller.py` (122, 249, 274, 282, 287, 330, 495), each emitting `scope` and `denominator_kind` with `completed`/`planned`.
- **Handoff notes**:
  - The fold is whole-stream: `core.journal.replay(run_id)` from seq 1 on every call (projection.py:21); there is no incremental or cached projection in this module.
  - Scope rows are last-write-wins keyed by `progress["scope"]` (projection.py:27) — a writer must keep the same scope string across updates or the view shows two rows for one activity.
  - Rows come out in first-seen order, not sorted; whether a caller should sort is unresolved in the code (cli/main.py:670 and ui/views.py:323 render as returned).
  - `vocab.label("execution", state)` at projection.py:41 will raise `VocabularyViolation` if a state ever reached the journal unvalidated — the fold assumes `journal.append`'s validation (journal.py:103-105) held.
  - The percent division is guarded by the truthiness test at projection.py:38, so a scope with `planned = 0` renders without a `percent` key rather than raising; consumers must treat `percent` as optional.

## Module map (dependency order, leaf → top)

1. `clock` (clock.py:1-16), `canonical` (canonical.py:1-75), `ids` (ids.py:1-69), `vocab` (vocab.py:1-375) — leaves; no intra-package imports.
2. `store` (store.py:16-23) — the only persistence layer; imported by everything below.
3. `journal` (journal.py:14-18) and `artifacts` (artifacts.py:8-11) — append-only layers over `store`, validated by `vocab` and hashed by `canonical`.
4. `runtime` (runtime.py:8-24) — composes `store` + `journal` + `artifacts`; `budget` (budget.py:10-14) — leaf in practice: imports nothing from the package, consumed by `broker` and the model adapter.
5. `constants` (constants.py:7-9) and `config` (config.py:26) feed run settings in; `projection` (projection.py:11-12) and `broker` (broker.py:16-21) are the top consumers, both reading the journal through `runtime.Core`.

### Section B — criteria derivation and registry core (src/mas/core)

Read-only survey of /home/yiwei3_duke/anny/mas at 2026-10-15; line numbers are current at this commit.

### `task.py` — `src/mas/core/task.py`

- **What it is**: Task Context Normalizer (C4): explicit, versioned task contexts (design §4.4) (task.py:1).
  A context records the objective, mode, evaluation scope and candidate universe a derivation is bound to;
  the context is immutable once recorded, so consumers see a version, not an editable row.
- **Entry points**:
  - `validate` (task.py:18) — mandatory objective_text/mode/evaluation_scope, vocab domain `task_mode`,
    candidate universe and seed requirements, and for a conditional mode constraints/scope_entities.
  - `record_version` (task.py:33) — appends the version.
  - `latest_version` (task.py:55); `get` (task.py:62); `list_tasks` (task.py:70).
  - `blocking_unknowns` (task.py:79) — the unknowns that block scoring.
  - `TaskContextInvalid` (task.py:14).
  - `DEFAULT_GROUP = "grp_default"` (task.py:11).
- **Records/artifacts it owns**:
  - event `task.version_recorded` (task.py:48); artifact kind `task_context` (task.py:47).
  - vocabulary domain `task_mode` (required in `validate`, task.py:18-25).
- **Current state**: implemented and small (81 lines).
  `validate` returns a problem list rather than raising (task.py:18).
- **Handoff notes**:
  - contexts are append-only versions — `record_version` never edits (task.py:33); consumers read
    `latest_version`/`get` (e.g. criteria_export.py:558-559).
  - the task id doubles as the journal stream that every pool/review/registry fold replays
    (pool.py:75, review.py:40, criteria_export.py:125).
  - `blocking_unknowns` is the only place the module says what is still missing; scoring gates should ask it
    rather than re-deriving unknowns.

### `criteria.py` — `src/mas/core/criteria.py`

- **What it is**: Criterion Registry (C10): Attribute and Rule records, invariants, confirmed rule sets
  (design §4.10) (criteria.py:1). An attribute describes a measurement (name, unit, direction, evidence
  routes, optional transform); a rule is the executable predicate over it; `confirm_rule_set` assembles the
  versioned set of rules allowed to score.
- **Entry points**:
  - `check_attribute` (criteria.py:289), `check_rule` (criteria.py:388) — deterministic invariants.
  - `propose` (criteria.py:428) — returns `attr_ref@v`/`rule_ref@v`; `record_version` (criteria.py:478).
  - `authority_requirements` (criteria.py:502) — the trigger table; `needs_expert` (criteria.py:552).
  - `confirm_rule_set` (criteria.py:646); `rule_set` (criteria.py:974); `registered_attributes` (criteria.py:982);
    `evidence_key` (criteria.py:991).
  - `evidence_routes` (criteria.py:212); `route_key` (criteria.py:238); `is_literature_bound` (criteria.py:254);
    `is_task_mandated` (criteria.py:274).
  - `basis_precedence`/`check_basis_precedence` (criteria.py:94/110); `apply_value_transform` (criteria.py:181).
  - deferrals: `deferral_scope`/`deferred_capabilities`/`route_summary` (criteria.py:597/606/640).
- **Records/artifacts it owns**:
  - vocabularies: MEASUREMENT_KINDS (criteria.py:12), DIRECTIONS (13), RULE_KINDS (14), CUTOFF_BASES (24),
    COMPARATORS (26), ON_STATE_POLICIES (27), AGGREGATIONS (28), POOLABLE_AGGREGATIONS (33),
    DETERMINATION_BASES (56), EVIDENCE_KINDS (61), PRECEDENCE_FIELD (91), VALUE_TRANSFORMS (156),
    DEFERRAL_SCOPES (594).
  - events `criterion.version_proposed` / `criterion.version_approved` (read at criteria_export.py:147, 160).
  - the rule-set record with entries/deferred/machine_adjudicated/collapsed_away/pending/pending_but_scoring
    and the bounds_* sections (criteria.py:646-960).
- **Current state**: implemented, with stated refusals:
  - a mixed literature route is refused unless the attribute is quantitative with a unit and a poolable
    aggregation (criteria.py:351-379); more than one literature route is refused (criteria.py:380-385).
  - `confirm_rule_set` raises `InvariantViolation("unconfirmed")` when open review items exist and
    `allow_pending` is false (criteria.py:703-704), and refuses an empty set (criteria.py:872-875).
  - unmet authority becomes a review item via `authority_requirements` (trigger table, criteria.py:502).
- **Handoff notes**:
  - `POOLABLE_AGGREGATIONS` excludes `consensus` (criteria.py:33 vs 28) — only max/min/median may be reduced
    over a family, which the merge gate relies on.
  - a transform's numbers are parameters, not cutoffs (criteria_export.py:309-333);
    `determination_basis_precedence` (criteria.py:91) is part of the operational quantity
    (criteria_export.py:381-388).
  - review items are raised through review.py — this module never writes an `hd_` decision.

### `pool.py` — `src/mas/core/pool.py`

- **What it is**: the criteria pool: items are lineages (`cri_<ulid>`), every transition is one
  `criterion.change_recorded` event (operation, targets_in/out, reason, claims), nothing is deleted, state is
  `fold()` replaying the task stream, and there are no model calls (pool.py:1-15).
  A reduction writes one record per parent (`merged_away`) and one for the child (pool.py:1-15).
- **Entry points**:
  - `fold` (pool.py:75) → id → {version, state, item, parents, children, history, promoted_as}.
  - `active` (pool.py:100); `pool_hash` (pool.py:104).
  - class `Pool` (pool.py:108) with `at` (115), `add` (122), `revise` (130), `set_state` (140),
    `merge` (152), `consolidate` (175).
  - `trajectory` (pool.py:190) — per round/iteration/stage added/revised/merged_away/removed/reinstated/
    promoted/reasons/live_after.
- **Records/artifacts it owns**:
  - event `criterion.change_recorded`.
  - `ACTIVE_STATES` = candidate/needs_refine/deferred_next_round (pool.py:26); `promoted` as a final state
    (read at criteria_export.py:951).
  - `ITEM_FIELDS` (pool.py:41-42); `REDUCTION_OPERATIONS` = ("merge","consolidate") (pool.py:48);
    `STAGE_ORDER` = propose/filter/distill/refine/merge/promote (pool.py:187).
- **Current state**: implemented and intentionally minimal (223 lines).
  - persist-why comments: `refine_count` and `consolidation` are persisted item fields because a later
    revision must not lose the why (pool.py:27-40).
  - `trajectory` orders stages by phase (propose = −1, promote = 1) so rows do not sort by reason
    (pool.py:219-223).
- **Handoff notes**:
  - append-only — never write state directly; every mutation goes through `Pool`/`_record` (pool.py:55-73)
    so that `fold` reproduces it exactly.
  - `consolidate` is `merge` with `operation="consolidate"` and `reason_kind="family_consolidated"`
    (pool.py:175).
  - the pool records reductions but enforces no field-inheritance policy — that lives in
    `derivation_stages.REDUCTION_FIELDS`.

### `derivation.py` — `src/mas/core/derivation.py`

- **What it is**: the five-step derivation flow: enumerate per dimension; propose; validate deterministically;
  blind critique; deterministic adjudication; one revision round (derivation.py:1-16).
  It hosts the proposer/critic/reviser schemas and prompts and the deterministic proposal validator.
- **Entry points**:
  - `enumerate_dimension` (derivation.py:256); `validate_proposal` (derivation.py:393).
  - `objective_criteria` (derivation.py:464) — writes task-mandated criteria with
    `derived_from {task_context, field}`.
  - legacy `derive` (derivation.py:488); `reading_order` (derivation.py:196); `research_params` (derivation.py:238).
- **Records/artifacts it owns**:
  - schemas PROPOSAL_SCHEMA (derivation.py:29), CRITIQUE_SCHEMA (42, checks enum includes
    candidate_symmetric_scrutiny), REVISION_SCHEMA (126), REVISION_CHECKS (141).
  - prompts PROPOSER_SYSTEM (55, "SET A CUTOFF WHENEVER…" 69, interpretation instruction 87),
    CRITIC_SYSTEM (115), REVISER_SYSTEM (134).
  - field tables ATTRIBUTE_FIELDS (158), SCHEMA_BLOCK_FORMS (165), RULE_FIELDS (188); DEFAULT_RESEARCH (211),
    SEARCH_VOLUME (229), TEXTBOOK_VOLUME (235).
  - artifact `visibility_manifest` (370) recording what the round saw; enumerate stop reasons
    document_cap/no_new_records/saturated/depth_reached.
- **Current state**: implemented.
  - a `ModelError` on one document is skipped and counted rather than failing the round (derivation.py:323-335).
  - `validate_proposal` checks registry invariants, cited claims, `bound_support.validate`, catalog binding
    per route, determination-basis acceptance, literature-bound must be quantitative with a unit, and the
    reference-candidate scan (derivation.py:393-455).
- **Handoff notes**:
  - the critique is blind and exactly one revision round exists (derivation.py:1-16); `REVISION_CHECKS` is the
    closed checklist (derivation.py:141).
  - everything `validate_proposal` does is deterministic, so a proposal that fails it never reaches a model
    again; model calls happen only here, in derivation_stages and in adjudication.

### `derivation_stages.py` — `src/mas/core/derivation_stages.py`

- **What it is**: the stage-by-stage derivation: PROPOSE recall-first; FILTER deterministic then blind critic;
  DISTILL; MERGE deterministic pairing then adjudicator, with reductions citing only parents' claims and
  inheriting agreed quantity/bound support via `REDUCTION_FIELDS`; REFINE; PROMOTE final blind check then
  `criteria.propose` (derivation_stages.py:1-25).
- **Entry points**:
  - `propose` (507), `filter_stage` (640), `distill_stage` (687), `merge_stage` (1235), `refine_stage` (1384),
    `promote` (1453), `STAGES` dict (1433).
  - `StageContext` (331); `quantity_key` (750); `merge_groups` (773); `_consolidation` (876).
  - `duplicate_of_registered`/`duplicate_reason` (538/596); `_revised` (452); `_supported_as_its_parents` (1125);
    `_reach_beyond_parents` (1222).
- **Records/artifacts it owns**:
  - pool change records via `pool.Pool`; `merge_stage` stats groups/merged/consolidated/kept_separate/refused/
    not_reduced, with each refusal reason recorded (1253-1258).
  - a consolidation writes `executes_as_aggregation` onto the attribute the assessor will run (1341).
  - `REDUCTION_FIELDS` classification table GROUPED/AGREED/AGREED_IN_A_MERGE/WITH_THE_BOUND/DECIDED/
    DECIDED_IF/GATE (96-171); MERGE_SCHEMA (204); `FAMILY_AGGREGATIONS` (70); MERGE_GROUP_MAX = 8 (300);
    BATCH = {critic 30, distill 25, refine 20, propose 400} (296).
- **Current state**: implemented; stated refusals:
  - `_consolidation` refuses fewer than 2 members, multi-dimension groups, an empty or redundant
    `shared_property`, and a `family_aggregation` the assessor cannot execute
    (`assessor.family_aggregation_execution`, 876).
  - `_revised` refuses a revision of a consolidated criterion that changes what it measures (452);
    `propose` refuses an entry only on the reference-candidate scan (507).
  - batch `ModelError`s are tolerated except `quota_exhausted` (319).
- **Handoff notes**:
  - `quantity_key` = (capabilities, canonical_unit, direction, subject, canonical value_transform) (750);
    `question_kind` is deliberately excluded (752-758) and the transform included (F5, 759-766).
  - `merge_groups` groups same-subject/evidence_key entries unconditionally; subject-less entries group only
    within bucket+dimension (804-820).
  - `worst_member` = max under lower_better, min under higher_better (adjudicator prompt, 276-279).
  - the adjudicator declares a family reduction but the merge gate writes the executed aggregation; the two
    must not be allowed to part (see criteria_export.py:1124-1134).

### `derivation_run.py` — `src/mas/core/derivation_run.py`

- **What it is**: a derivation run is a `run_` stream with `run_purpose: criteria_derivation`; later rounds
  continue a run through `continues_run_id` (derivation_run.py:1-20).
  It orchestrates the per-round loop and can re-derive without reading: `reduce_pool` = prune + promote of an
  earlier pool.
- **Entry points**:
  - `derive_iterative` (321); `reduce_pool` (253); `_inherited_claims_by_dimension` (70).
  - `_stage_recorder` (111); `_open_run` (132); `_close_run` (218); `_prune` (192); `record_of` (404).
  - `DEFAULT_STAGES` (40); `DerivationError` (43).
- **Records/artifacts it owns**:
  - events `run.created` / `run.continued` / `run.started` / `round.opened` / `round.closed` / `run.completed` /
    `run.unresolved` / `run.failed` (397) / `stage.opened` / `stage.closed`.
  - artifact kind `derivation_stage` recording each stage's input/output pool hash (111-131).
  - run binding fields chain_id, continues_run_id, round_index, role_bindings, settings,
    `derivation_configuration: "reference_disclosed"` and the known-reference-outcome disclosure (158-159);
    pool_states/pool_hash/termination_reason/independence/budget/continuation_decision in the close record
    (218-252).
- **Current state**: implemented.
  - `DEFAULT_STAGES = ("filter","distill","refine","merge")` (40), with the WHY comment that merge must run
    last: with merge before refine the manuscript case grouped 0 items across two iterations and the
    adjudicator role was never called (35-39).
  - termination is `diminishing_information_gain` on a stall, else `round_limit_reached` (192-217);
    `quota_exhausted` becomes `budget_exhausted`; `_fail` records `run.failed` (397).
  - `reduce_pool` refuses a cross-task pool (282-284) and marks its binding `reads_new_evidence: False` (295).
- **Handoff notes**:
  - `_inherited_claims_by_dimension` (70) groups the chain's admitted claims by the dimension each was read
    for, placing a claim in the span opened by a round's `plan queries: <focus>` question against
    `recorded_at` (91-100); a claim falling in no span is offered to every dimension, because dropping it
    would be the worse error and a round that never opened a dimension has no span (105-107, 83-84).
  - WHY grouped rather than whole: operator instruction to finish quickly, 15 October 2026 — the inherited set
    was 2,234 claims (round 5's 1,771 + round 6's 463), and offering all of it to all four dimensions cost 24
    proposer calls against 8, most of the difference being round 5's 1,489 target-coverage claims (79-84).

### `collapse.py` — `src/mas/core/collapse.py`

- **What it is**: deterministic (no model call) collapse of promoted criteria that measure the same quantity
  under one `quantity_key`: several registrations of one quantity become one attribute reading every route
  (collapse.py:1-41).
  Measured in the header: ten promoted rules over five quantities, 34 → 99 compounds clearing the 0.5 floor.
- **Entry points**:
  - `plan` (171); `_group_plan` (216); `_apply` (298) — records a new attribute version and a new rule version.
  - `collapse` (368, dry_run defaults True); `records` (387); `live` (400).
  - `superseded_attributes` (404); `surviving_rules` (415); `withdraw` (427).
  - COLLAPSE actor (59); RULE_AGREEMENT (64); RULE_DEFAULTS (65); `CollapseError` (70).
- **Records/artifacts it owns**:
  - `clp_` collapse records with `approval_kind: software_status`, `confirmed_by_a_person: False` and a
    separate `ran_by` (collapse.py:36-40, 58).
  - pool change-record vocabulary is reused but the record is not marked `pool` (33-34).
  - two registry versions per survivor because the sweep loads the attribute the rule names (1-41).
- **Current state**: implemented with a dry-run default (368). `plan` refuses:
  - already-withdrawn collapses (179-182), expert-approved rules (186-188), more than one rule naming the
    attribute (223), groups whose members are the same base version (229), groups with no subject parameters
    (242-246); the survivor is support-checked before absorbing (204-211).
  - `_apply` raises a new review item when the survivor needs an expert (327); `withdraw` raises CollapseError
    without a reason or when already withdrawn (427).
- **Handoff notes**:
  - it is a software write with no person, which `approval_kind`/`confirmed_by_a_person` is there to make
    unmistakable.
  - `superseded_attributes` is keyed by the exact attribute version (404); `surviving_rules` counts withdrawn
    collapses too (415).
  - because a collapse changes routes, any consumer should print `routes_before`/`routes_after`
    (criteria_export.py:785-790).

### `bound_support.py` — `src/mas/core/bound_support.py`

- **What it is**: the §5.4 bound-support check: given an attribute/rule and the claims cited behind it, decide
  whether a stated numeric bound is actually supported, splitting a declared interpretation from a mechanical
  derivation (bound_support.py:1-61).
  Written against three defects: R4 (a cutoff of 90 against a claim of 30), R3 (transform basis `expert_set`
  bypassing `needs_expert`), R7 (">=30" applied as ">=90") (1-61). Pure: no write, no model, no network (57-60).
- **Entry points**:
  - `validate` (505; `grants` argument 507; returns bounds/findings/states/blocking/review_paths/
    unsupported_paths/grantable_paths/granted_paths/claims_resolved).
  - `interpretation` (287; outcomes not_declared/incomplete/unreadable/circular/contradicts_the_rule/declared).
  - `support_records` (357); `claims_stating` (203); `stated_ranges` (239); `range_endpoint` (257).
  - `messages` (673); `resolve_claims` (679); `revision_relation` (797); `field_diff` (751).
- **Records/artifacts it owns**:
  - states `STATES` (97-98) with BLOCKING_STATES (100) and REVIEW_STATES (103).
  - vocabularies STATEMENT_KINDS (72), SOURCED_BASES (74), AUTHORITY_BASES (82), UNBOUNDED_BASES (84),
    CONVERSION_KINDS (86), CENSORING (90), INTERPRETATION_FIELDS (111), INFERENCES (116-119),
    INTERPRETATIONS (124), REFUSED_INTERPRETATIONS (125).
  - revision relations `RELATIONS` = neutral/weaker/stronger/not_decidable (730) over `REVISABLE_FIELDS` (718).
- **Current state**: implemented.
  - a granted interpretation yields `interpretation_granted`, never `sourced_threshold` (46-55); the
    range-endpoint rule is stated with the 500 g/mol case (46-55); an interpretation needs a non-circular
    justification of at least 4 words (133, 141).
  - `resolve_claims` returning None means unresolvable and the bound is left unaudited (679).
- **Handoff notes**:
  - purity is a contract (57-60) — callers do the journalling.
  - `validate`'s `grants` argument is how a machine adjudication's granted interpretation (route 6) is
    admitted without re-declaring it.
  - the strength tables (_KIND_STRENGTH 722, _POLICY_STRENGTH 724, _DIRECTION 727, _STRICTNESS 729) are what
    make weaker/stronger mechanical; a field added to `REVISABLE_FIELDS` needs an entry in those tables.

### `criteria_export.py` — `src/mas/core/criteria_export.py`

- **What it is**: exports the registered criteria of one task as a reviewable snapshot into the repository,
  because the live store (`var/primary/store`) is git-ignored and a checkout shows none of the 40 registered
  criteria, 127 bound claims or 9 open disputes (criteria_export.py:1-9).
  It pins one journal sequence through `_PinnedJournal` so all five folds see the same state (11-15), and it
  refuses to tidy: the snapshot is labelled `historical_baseline_pre_repair` (43, 17-21).
- **Entry points**:
  - `open_read_only` (118); `pinned` (123); `snapshot` (551).
  - `render_markdown` (1353); `render_reconciliation` (1514); `manifest` (1638); `write` (1678).
  - `_PinnedJournal` (74); `_card` (649); `_matching_facets` (356); `_recovery_comparison_set` (796);
    `_lifecycle` (874); `_counts` (932); `ExportError` (70).
- **Records/artifacts it owns**:
  - four files: `derived_criteria_review.md`, `derived_criteria_review.json`, `derived_criteria_manifest.json`
    (written last, it carries the digests of the others, 52-56), `criteria_count_reconciliation.md` (54-57).
  - `BASELINE_LABEL`/`BASELINE_STATEMENT` (43-50); `EXPORT_SCHEMA_VERSION = 1` (38).
  - `WITHHELD_ARTIFACT_KINDS = ("tool_result","trace")` (64) — model traces and whole provider responses stay
    private, quoted spans/locators/source hashes are published (59-63, 630-632).
- **Current state**: implemented as a reader only:
  - `_PinnedJournal.append` raises "the export reads; it never appends" (114-115); `pinned` raises for a task
    with no events or a seq outside 1..last (126-130).
  - the reconciliation answers the project's quoted counts (72, 34, 40, 13, 8, 9, 26, 5), each with its
    population (8-9, 1536-1552).
  - `_use` keys scoring status off the rule-set entry, not the `deferred[]` list — the why-comment records
    that keying it off the list reported a scoring rule as deferred (509-519).
- **Handoff notes**:
  - determinism is a contract — the snapshot carries no export timestamp, so two exports of one sequence hash
    identically (553-556), and `manifest` digests the payload excluding `exported_at` (1667-1674).
  - `_claim_locations` is one indexed pass because a per-claim lookup over 36,282 admission events would
    reread a 1.9 GB table (165-171).
  - `_claim_view` keeps quote_check and semantic_support apart because every cited claim here carries
    `span_checked_against_source: true` while carrying `verification_status: unverified` (236-246).
  - `_matching_facets.gaps` lists absences and never reconstructs the absent value (367-369); `_family_reduction`
    re-derives the executed aggregation from the attribute rather than copying the declared one (1124-1134).

### `adjudication.py` — `src/mas/core/adjudication.py`

- **What it is**: machine adjudication of open review items through seven named routes (adjudication.py:1-92):
  1 task_constraint_restated, 2 no_authority_available, 3 irreversible_without_authority, 4 dispute_adjudicated,
  5 definition_restated, 6 bound_interpretation_granted, 7 predictor_boundary_adopted.
  Route 6 exists because the recovery measurement found 0/11 recoverable without a way to grant a declared
  interpretation (1-92).
- **Entry points**:
  - `route_of` (624, conservative ordering: route 7 before routes 3 and 6, route 6 ahead of route 3);
    `route_preview` (688).
  - `restated_constraint` (183); `stated_quantity` (289); `restated_definition` (336);
    `grantable_interpretation` (394); `predictor_boundary` (473); `granted_bounds` (565).
  - `_record_rule_version` (726); `_record_attribute_version` (751); `independence` (777); `_apply_revision` (917).
  - `adjudicate` (988); `adjudicate_open` (1233); `records` (1259); `by_rule_version` (1265); `reopen` (1279).
- **Records/artifacts it owns**:
  - `adj_` records with `approval_kind: agent_verdict` — never an expert approval (criteria_export.py:1003-1005).
  - `ROUTES` (123), `ROUTE_EFFECT` (111-122), VERDICTS (124), GRANT_VERDICTS (128), RESOLUTIONS (133-135),
    MACHINE actor (138).
  - ADJUDICATOR_SYSTEM (140), ADJUDICATION_SCHEMA (153), BOUND_GRANT_SYSTEM (364), BOUND_GRANT_SCHEMA (385);
    gating floors MIN_GATING_AUROC = 0.70 (449), MIN_GATING_R2 = 0.50 (450), GATING_METRICS (454),
    MODEL_BASES (458), PROVENANCE_KEYS (463).
- **Current state**: implemented.
  - a demotion is written as a new rule version because the assessor reads `rule_kind` from the rule record
    (83-85); route 5 writes two versions (87-91).
  - `adjudicate` composes the routes and still demotes an approval whose rule is `expert_set` or a hard
    exclusion the task did not mandate (1117-1142), with route 6 as the stated exception; `_apply_revision`
    holds the refusal classes and is the R7 fix (917).
- **Handoff notes**:
  - route order is policy and conservative (624).
  - a machine adjudication never writes an `hd_` decision — it records a `decision.recorded` event that
    `review.items` folds into state `machine_adjudicated` (review.py:56-67).
  - `by_rule_version` is keyed by the version after the adjudication (1265), so a lookup on the pointed-at rule
    finds it.
  - `predictor_boundary` requires a holdout metric above the floors (449-463): predicted evidence may not set a
    gating boundary without one.

### `review.py` — `src/mas/core/review.py`

- **What it is**: the human review queue.
  An `hd_` decision is created only by a person confirming at a terminal;
  machine adjudication is a separate record and a separate state (review.py:1-8).
  `items` folds the stream, and the module never creates an `hd_` itself.
- **Entry points**:
  - `request` (26, vocab "hd_subject_kind", event `human.review_requested`).
  - `items` (40).
  - `decide` (71).
  - `ReviewError` (20).
- **Records/artifacts it owns**:
  - events `human.review_requested` / `human.review_decided` / `human.review_withdrawn`.
  - `items` additionally folds `decision.recorded` events carrying an `adjudication_id` into state
    `machine_adjudicated` (56-67), so a machine resolution is visible in the same queue
    without being an `hd_` decision.
- **Current state**: implemented and deliberately minimal (118 lines).
  `decide` refuses a non-human actor (95-96), a non-interactive entry (97-98),
  and a non-open item (99-100).
- **Handoff notes**:
  - the F7 note (74-92) states this is "a process boundary, not a security boundary", names a demonstrated
    bypass, and says a real boundary needs an authenticated principal.
    Do not describe it as a security control.
  - anything needing a human decision must go through `decide` with a human actor.
    Anything else is machine adjudication and belongs in adjudication.py, not here.

### Module map (dependency order)

1. `task.py` and `review.py` — leaves: the versioned task context everything is scoped to, and the queue primitives other modules raise items through.
2. `pool.py` and `criteria.py` — the two stores; criteria holds the registry vocabulary and invariants and raises review items.
3. `bound_support.py` feeds `derivation.py` — pure bound checking, then the proposer/critic schemas and deterministic proposal validation.
4. `derivation_stages.py` (pool + criteria + bound_support), `derivation_run.py` (rounds and stages, merge last), `collapse.py` (criteria + pool) — the derivation and reduction layer.
5. `adjudication.py` (review + criteria + bound_support) and `criteria_export.py` — which imports all of the above (criteria_export.py:31-36) and publishes the pinned snapshot.

### Section C — Core modules: evidence, assessment, the board, the freeze, and recovery

Scope: read-only survey of `/home/yiwei3_duke/anny/mas` at `main` (`9912dbb`).
Paths are relative to the repo root; line numbers are from the working tree at the time of reading.
"Unclear from the code" marks anything the code does not settle.

### `reading` — `src/mas/core/reading.py`

- **What it is**: The literature sub-system: query planning, search, document read, passage
  selection, summarisation and claim extraction. Its load-bearing part is the admission decision
  inside `extract_claims`, which turns each extracted claim into `admitted` or `quarantined`
  before it reaches the ledger (`reading.py:722`). It journals nothing itself; it returns records
  and stores artifacts.

- **Entry points**:
  - `plan_queries` `reading.py:364`; `search` `reading.py:397` (stores the `search_coverage` artifact at `:452`).
  - `read` `reading.py:466` (stores `document` at `:493`); `select_passages:497`; `summarize:550` (stores `summary` at `:569`).
  - `extract_claims:630` — the admission gate; hands each claim to `ledger.record_claim` at `:724`.
  - Matching/guard helpers: `normalize_for_match:39`, `quote_found:48`, `value_in_quote:63`,
    `names_entity:76`, `subject_terms:146`, `value_like_numbers:167`, `_clauses:188`,
    `attribution_problem:219`, `is_case_source:295`.

- **Records/artifacts it owns**: artifact kinds `search_coverage`, `document`, `summary` (the
  `claim` artifact is created by the ledger on its behalf); vocabulary domain
  `literature_admission_reason`, validated at `:723`.
  - Reason strings it issues: `quote_verified`, `value_in_quote`, `candidate_named_in_quote`,
    `candidate_named_in_passage`.
  - Problem strings: `passage_not_found`, `quote_not_found_in_passage`, `value_not_in_quote`,
    `candidate_not_named_in_source`, `attribution_ambiguous` (`:669-696`).

- **Current state**: implemented; the admission checks are the densest logic in the module.
  - Verbatim-span check: the quoted span must occur in the selected passage, else
    `quote_not_found_in_passage` (`:671-677`).
  - Value-in-quote: each numeric field (`value`, `value_low`, `value_high`) must appear in the
    span, else `value_not_in_quote` (`:678-682`).
  - Candidate naming: named in the quote, or named in the passage provided no competing entity is
    named in the quote (`:683-691`).
  - `attribution_problem:219` — three ordered checks, documented in its docstring: a competing
    attribute's subject in the clause carrying the number; an arm comparison the number's clause
    does not tie to the candidate; a second value of this attribute's kind in the span. Check 1
    fires on a *competing* subject, never on the absence of its own, and the docstring records the
    measured claim that repair exists to recover (`:219-243`).
  - Case-source exclusion `is_case_source:295` — identifier match (doi/pmid/pmcid, or an upload's
    `sha256`), title Jaccard >= 0.85, title containment >= 0.90 of the shorter title with
    `containment_min_tokens=6`; the docstring records why Jaccard alone lets the manuscript's own
    supplement in.
  - Every extracted claim leaves with `verification_status: "unverified"`,
    `span_checked_against_source`, and the failing check's reviewer-readable note in
    `attribution_check` (`:704-718`).

- **Handoff notes**: quarantine is not rejection — the claim is recorded and readable; only
  scoring is refused, and `assessor.usable_claims` is what enforces that. `admit` and `problems`
  are independent gates (`:722`): with `admit=False` even a clean claim quarantines. The
  thresholds in `attribution_problem` and `is_case_source` were tuned against measured claims (the
  docstrings cite 253 claims and four true observations refused by one shared word), so a
  threshold change silently changes which numbers a cell may ever score and should be
  re-measured, not adjusted by taste.

### `evidence` — `src/mas/core/evidence.py`

- **What it is**: Per-candidate×attribute evidence gathering: it takes a rule's declared routes,
  queries the tools the route offers, converts tool results into ledger claims, and returns the
  claims one cell may be assessed on. It writes no journal events and no artifacts itself — every
  source and claim goes through the ledger (`evidence.py:102`, `:130`).

- **Entry points**:
  - `gather:381` — the per-cell entry point; unions the claims the routes produced (`:431`).
  - `producible_evidence_kinds:49`; `determination_basis:71`.
  - `claims_from_tool_result:91` — tool result to claim, via `ledger.put_source` (`:102`) and
    `ledger.record_claim` (`:130`).
  - `literature_query:137`; `name_like:151`; `LiteratureCache:156` (`once:182`);
    `LiteratureReading:201`; `search_labels:236`; `_select_documents:251`; `read_literature:282`.
  - `DB_BASIS:45` — the basis a database-sourced claim defaults to; `BudgetBlocked:38`.

- **Records/artifacts it owns**: none directly.
  - The quarantine reasons it chooses are `identity_not_grounded` and `provenance_incomplete`
    (`:113-116`), written through `ledger.record_claim` like any other.
  - A model output is registered as a source with a source status that says no record holder
    stands behind it (`:104-108`, why-comment).

- **Current state**: implemented.
  - The database-first / literature-last ordering is not here; it is the controller's
    (`controller.py:31-32`), and the literature pass calls `evidence.read_literature` and
    `evidence.gather` (`controller.py:377`, `:442`), turning `BudgetBlocked` into a refusal
    (`controller.py:388`, `:458`).
  - The claim payload it builds carries `scope_match`, `reading_depth`, `verification_status`,
    evidence kind and determination basis, which is what the assessor's acceptance checks read.

- **Handoff notes**:
  - A change to `producible_evidence_kinds` changes what a route may return and therefore which
    cells can reach a value-bearing verdict at all.
  - The `LiteratureCache` is per-run state, so a resumed run must not assume it is warm.
  - Budget refusals are the controller's to turn into `not_assessed` with reason
    `budget_exhausted` — this module only raises.

### `ledger` — `src/mas/core/ledger.py`

- **What it is**: The evidence ledger: sources, claims with admission state, and frozen evidence
  snapshots (`evs_<task>_<n>`). It is the only module that journals claims; every other module
  reads them back through `claims()`.

- **Entry points**:
  - `ADMISSION_STATES:12`; `SOURCE_STATUSES:13`; `ACCESS_STATES:18`; `READING_DEPTHS:19`.
  - `put_source:22`; `record_claim:35`; `claims:60`; `freeze_snapshot:77`.

- **Records/artifacts it owns**:
  - Artifacts `source` (`:31`), `claim` (`:47`), `evidence_snapshot` (`:86`).
  - Events `evidence.admitted` / `evidence.quarantined` (selected at `:48`, appended at `:49`)
    and `evidence.snapshot_frozen` (`:87`).
  - Snapshot id `evs_{task_id}_{n}` (`:82`); the snapshot record carries `claim_ids` (sorted),
    `cutoff_at`, `tool_availability_snapshot` and `hash = sha256_hex(record)` (`:84-85`).

- **Current state**: implemented; 92 lines, deliberately narrow.
  - `record_claim:35` refuses a claim without `location.location_kind` and `locator_value`
    (`:41-42`) and one whose `reading_depth` is outside `READING_DEPTHS` (`:43-44`).
  - The event payload carries only references — claim id, artifact id, state, reasons,
    candidate/attribute/source refs — never the statement (`:49-56`).
  - `freeze_snapshot:77` numbers snapshots by counting existing `evidence.snapshot_frozen` events
    with the same `task_id` across all streams (`:80-82`).
  - `claims:60` replays claim events in the given streams and filters by candidate, attribute and
    (by default) admission state (`admitted_only=True`, `:61`): quarantined claims are visible only
    with `admitted_only=False`, which is how `mechanism` reads them.

- **Handoff notes**:
  - To read what a claim says, fetch the claim artifact; the journal alone will not show it.
  - There is no path that rewrites a claim's admission state, so a claim whose state changes must
    be recorded as a new claim (`superseded` is a label for such a new claim, not an update).
  - Snapshot ids are counts, so importing claims into a store that already has snapshots changes
    the next id; the `hash` is what identifies the content.

### `identity` — `src/mas/core/identity.py`

- **What it is**: Candidate identity resolution over the task's universe, driven by the adapter's
  declared primary identifier scheme. Every member leaves `resolve_universe` with an identity
  record; an ambiguous name match opens a non-blocking review request rather than a guess.

- **Entry points**: `LINK_BASES:16`; `candidate_id:20`; `resolve_universe:24`; `is_resolved:67`.

- **Records/artifacts it owns**:
  - Artifact `identity_record` (`:57`); event `identity.resolved` (`:58`) carrying candidate id,
    input label, link basis and the artifact id.
  - Review request kind `identity_merge` with `blocking=False` for an ambiguous match (`:55-56`).

- **Current state**: implemented, 68 lines.
  - A single hit with the scheme's identifier present resolves to `cand_<scheme>-<value>` with
    basis `exact_identifier_match` / `authority_crosswalk` / `name_match_single_candidate`
    (`:34-45`).
  - A hit lacking the primary identifier downgrades to `unresolved` and a name-derived id, even
    though a hit existed (`:38-39`).
  - No hit reads `unresolved`; more than one hit reads `name_match_ambiguous` with
    `identity_review_state: "pending"` and the offered candidates kept on the record (`:46-53`).
  - `is_resolved:67` is the three positive bases; both `unresolved` and `name_match_ambiguous` are
    unresolved.

- **Handoff notes**:
  - `assessor.assess_cell` maps `resolved=False` to `not_assessed` with reason
    `identity_unresolved` (`assessor.py:395-399`), so an unresolved identity is a refused verdict,
    not a missing value — it counts as an unknown hard rule and holds the candidate at
    `provisional`.
  - Changing what counts as resolved here changes pass/fail on every downstream board, and the
    `LINK_BASES` vocabulary is the contract the review UI reads.

### `assessor` — `src/mas/core/assessor.py`

- **What it is**: The scoring core. `assess_cell` turns one candidate's claims for one rule into a
  verdict, a reason record and a value; `roll_up` turns a candidate's cells into a state; the rest
  derives what the board and the symbolic-regression stage read (mandated coverage, calibration
  guard, preference scores, feature values, expression scores). All of it is pure — no journal
  events, no artifacts (0 `journal.append` calls in 914 lines).

- **Entry points**:
  - `assess_cell:370` returns `(assessment, reason)`; its docstring says "Pure: no I/O".
  - `roll_up:565`; `ASSESSOR_VERSION = "assessor-1":19`; `SET_ASIDE_REASONS:31`; `BASIS_STRENGTH:46`;
    `UNIT_SYNONYMS:49`; `UNIT_CONVERSIONS:108`; `converted_claim:121`.
  - `FAMILY_AGGREGATION_EXECUTION:196`; `source_document_shortfall:236`; `declares_predicted:253`;
    `basis_used:263`; `usable_claims:287`.
  - `MIN_CALIBRATION_REFERENCE = 10:662`; `DEFAULT_MAX_REFERENCE_EXCLUSION = 0.90:665`;
    `clears_mandated:668`; `DEFAULT_MANDATED_COVERAGE_FLOOR = 1.0:712`; `mandated_coverage:715`;
    `calibration_guard:784`; `preference_scores:840`; `feature_values:887`; `expression_scores:903`.

- **Verdict semantics (`assess_cell`) — the part to get right**:
  - `not_assessed` is a refusal to decide, not a missing measurement: reached when a `not_assessed_reason` is supplied or the identity is unresolved, with reason `not_assessed_reason or "identity_unresolved"` (`:395-399`); such a cell never filters its claims at all (`:379`), and the controller is what produces the reason values (a route not searched; `budget_exhausted` at `controller.py:431`, `:435`).
  - `unknown_missing` = assessed, but no usable claim survived: claims are set aside with a named reason from `SET_ASIDE_REASONS` (`:31-40`) rather than dropped — "the claims are set aside rather than dropped: they stay in the ledger" (`:380-384`) — and the reason text ends "this is not a failure" (`:544-549`).
  - `unknown_conflicted` = usable claims land on both sides of the cutoff and the declared aggregation is `consensus` (`:441-444`); with any other aggregation the disagreement is recorded as `found_and_outweighed` and the cell still returns a value-bearing pass/fail with the counter-evidence claim ids (`:446-460`).
  - `pass` / `fail` against the cutoff after the attribute's `value_transform` per claim before aggregation (`:406-415`); an ordering preference with no cutoff is always `pass` when it has values — "an ordering rule ranks, it never fails" (`:426-438`). `inapplicable` is excluded from every population count (`:574-575`, `:696`); the source-document floor is applied before any verdict, so it decides whether the cell may even declare a conflict (`:382-389`); `declares_predicted:253` and `basis_used:263` govern the predicted-evidence and basis-precedence rules.

- **Roll-up (`roll_up:565`)**: all cells not-assessed -> `unassessed` ("no assessed criteria");
  any hard `fail` -> `rejected`, naming the failed attributes; any hard unknown (`unknown_missing` /
  `unknown_conflicted` / `not_assessed`) -> `provisional`, naming the blocking attributes; hard
  rules pending an expert decision -> `provisional`; no hard rules at all -> `provisional` ("no
  confirmed hard rule; ranked on preferences only"); coverage below the floor -> `provisional`;
  otherwise `recommended`, except `recommended_requires_hd` with no `hd_` refs gives `provisional /
  awaiting_human_review` unless `machine_authority`, in which case `recommended` with a reason
  stating an agent decided and no person confirmed it (`:581-612`). The summary carries
  `hard_rule_coverage` (`None`, never 0, when there are no hard rules), `n_fail_hard`,
  `n_unknown_hard`, `n_preferences_evaluated`, `n_preferences`, `blocking_unknowns`,
  `determination_bases` and `gap_filled_criteria` (`:581-631`).

- **Records/artifacts it owns**: none — the `reason` and `assessment` artifacts are written by the
  controller (`controller.py:484-485`); this module returns the records.

- **Current state**: implemented; the why-comments are measurements, not rationale.
  - `mandated_coverage:715-773` records the 14 October board where mebendazole ranked 4th ahead of
    candidates measured on all five required receptors, and argues why a mandated hard exclusion is
    kept out of the floor's population (its `unknown_blocks_recommendation` already holds those
    candidates).
  - `:598-609` records the 9-cleared / 1,262-blocked ambiguity the machine-authority branch resolves.
  - `:425-433` records sorafenib ranked on a maximum over 125 curated VEGFR2 measurements against
    surufatinib's two, which is why the attribute's declared aggregation is honoured.

- **Handoff notes**: `ASSESSOR_VERSION` is baked into every cell's fingerprint
  (`controller.py:478-483`), so bumping it makes previously recorded cells non-reusable.
  `MIN_CALIBRATION_REFERENCE = 10` makes the guard abstain below ten reference candidates rather
  than demote a gate on one candidate's worth of evidence. `coverage` and `mandated_coverage`'s
  `coverage` are `None` — not 0 — where nothing is measurable, and every consumer must read absent
  as unknown (`:773`); the same rule is stated again on the board (`leaderboard.py:158`).

### `leaderboard` — `src/mas/core/leaderboard.py`

- **What it is**: Task-scoped, versioned board snapshots. A snapshot reports the result kind, one
  entry per candidate (state, verdicts, gate answers, mandated coverage, change records against
  the parent), an optional ranking, and a reporting tuple with coverage and abstention. Its
  docstring: "Precision is never shown without coverage and abstention" (`leaderboard.py:1-7`).

- **Entry points**: `STATE_ORDER:19`; `member_set_hash:22`; `leaderboard_record:31`;
  `snapshots:64`; `_changes:73`; `_review_summary:99`; `build_snapshot:115`.

- **Records/artifacts it owns**:
  - Event `leaderboard.current_set` on the task stream (`:57`).
  - The snapshot itself is written by the controller as a `leaderboard_snapshot` artifact
    (`controller.py:618`) and published with `leaderboard.snapshot_published` (`controller.py:620`).
  - Vocabulary domains `result_kind` (`:132`, `:235`) and `abstention_reason` (`:236`).

- **How the board ranks** (`:206-213`):
  - Eligible for a position: `state in ("recommended", "provisional")` AND `preference_score is not
    None` AND `preference_coverage >= ranking_coverage_floor` AND
    `clears_mandated_criteria is not False` (`:206-207`).
  - Sort: score descending, then `STATE_ORDER` (recommended before provisional), then preference
    coverage, then hard-rule coverage, then candidate ref (`:208-209`).
  - Positions are assigned only when the rule set has preferences (`:210-212`); with no
    preferences the board is an all-pass set.
  - A candidate below either floor keeps its entry, its state and its cells and gains a
    `rank_note` naming the numbers — it is not dropped, "because 'nobody has measured this
    compound at four of the five required receptors' is a finding about the evidence and the one
    thing a silent drop would hide" (`:167-169`, `:192-202`).
  - `None` is not a failure: `clears_mandated_criteria` is `None` where the task mandates nothing
    or the candidate has no mandated cell — "Absent counts read unknown, never pass" (`:158`,
    `:170-172`) — which is why the filter is `is not False` and not a truth test (`:204-205`).
  - Abstention: nothing ranked and nothing admitted is reported as `result_kind =
    no_recommendation` with one of `all_candidates_excluded` / `evidence_unavailable` /
    `unresolved_conflicts` / `insufficient_coverage` (`:224-236`).
  - Two floors are applied: the ranking coverage floor over *preference* cells (`:198`), and the
    mandated coverage floor over the task's own criteria (`:194-197`). Mandated *gates* are
    deliberately outside that floor and counted separately, so a ranked candidate can still carry
    `mandated_gates_unanswered` (`:175-180`, `:268-274`).
  - `result_kind` is `both_reported` / `ranked_under_score` / `all_pass_set` (`:132-133`), and the
    demoted kinds come from the cells, not from the rule registry, because the calibration guard
    demotes for this run only (`:124-129`).

- **Current state**: implemented.
  - `review_status` is hard-coded `"none"` on every entry (`:190`) and `precision_among_admitted`
    is `None` (`:249`) — precision depends on the sealed historical list, which only `recovery`
    can fill.
  - `_review_summary:99` carries the human-review answer onto the board, naming
    machine-adjudicated rules rather than counting them away (`:104-112`).

- **Handoff notes**:
  - The comparability key includes `member_set_hash`, because a percentile-style score is
    set-dependent; two snapshots over different member sets must not share a leaderboard or
    exchange change records (`:22-48`).
  - Adding an entry field that changes with the evidence is safe; changing the sort keys or the
    eligibility predicate changes published positions and should be treated as a new comparability
    question.

### `controller` — `src/mas/core/controller.py`

- **What it is**: The run controller: one run binds an adapter, rule set, budget envelope and
  settings, then executes the stages `identity` -> `assess` -> `snapshot` (`RUN_STAGES:30`) under
  strategy `strat@v1` (`:29`), journaling every step on the run stream. The database rules sweep
  first, the literature pass last (`DATABASE_FIRST` / `LITERATURE_LAST:31-32`).

- **Entry points**:
  - `RunController:106` (`start:127`, `_load:188`, `current_state:219`, `execute:226`,
    `_restore:255`, `_run:265`, `_literature_pass:334`, `_assess:421`, `_cell_refs_hash:467`,
    `_record_cell:477`, `_calibration_guard:499`, `_finish:554`, `resume:643`).
  - `CONTROLLER:28`; `RunError:48`; `_PassBudget:54`; `RunState:90`; `_emit:117`.

- **Records/artifacts it owns**:
  - Run-stream events through `_emit:117` — `run.continued:181`, `progress.estimate_revised:121`,
    `step.started` / `step.completed` / `checkpoint.written` (`:310`, `:319`, `:321` for the
    database sweep; `:370`, `:402`, `:407` for the literature pass), `candidate.assessed:489`,
    `stage.closed:619`, `leaderboard.snapshot_published:620`, `projection.hash:626`,
    `round.closed:634`, `attempt.finalized:637`, and the terminal `run.unresolved` /
    `run.completed` emit at `:638`.
  - Artifacts `config_layers:147`, `run_binding:173`, `plan:246`, `reason:484`, `assessment:485`,
    `calibration_guard:546`, `leaderboard_snapshot:618`.
  - Vocabulary domains `policy_arm`, `memory_mode`, `continuation_kind` (`:135-137`),
    `approval_kind` (`:544`).

- **Current state**: implemented.
  - `_finish` reads both floors from registered constants (`const_ranking_coverage_floor`,
    `const_mandated_coverage_floor` at `:610-615`), so the board a run published is reproducible
    from the board plus the constants.
  - `projection.hash:626` pins a hash over the replayed run range.
  - `_record_cell:477` stamps each cell with a `fingerprint` over candidate, rule, attribute,
    strategy, `assessor.ASSESSOR_VERSION`, the value-source claim refs, tool ids/versions, host
    platform and a `recall_set_hash`, plus `reuse={"decision": "recomputed"}`.
  - The literature pass assesses candidates concurrently with `workers` (default 1, `:108`, pooled
    at `:416-417`), which is why `_cell_refs_hash:467` takes a lock: iterating the cell dict while
    another worker inserts "raises RuntimeError ... rather than returning a wrong hash"
    (`:468-475`).

- **Handoff notes**:
  - Only one of the three `assess_cell` calls in `_assess` scores claims; the other two carry none
    and are refusals already (`:460-465`) — do not give them claims.
  - The calibration guard demotes a hard exclusion for this one run and the demotion is carried on
    the board, not written back into the rule registry (`leaderboard.py:124-129`).
  - A cell whose verdict is `not_assessed` with reason `budget_exhausted` sets `budget_cut` and the
    run ends `unresolved` rather than completed (`:317-318`, `:628-638`), with the unswept cells
    listed in the `round.closed` manifest (`:632-634`); resume must not silently score those
    cells, so treat the budget cut as a result.

### `staging` — `src/mas/core/staging.py`

- **What it is**: Registered shortlist stages (design §6.6): when a full sweep is infeasible, the
  operator registers a shortlist rule — the top K candidates of a published snapshot, ties at the
  boundary included — and the shortlist becomes a derived task that carries the source snapshot,
  the rule, and copies of the registered criteria with links to their source versions
  (`staging.py:1-8`).

- **Entry points**: `shortlist_members:20`; `shortlist_task:29` (its only caller is the CLI,
  `cli/main.py:277`).

- **Records/artifacts it owns**: none of its own.
  - It writes a task version via `task_mod.record_version` (`:48`) and each copied rule via
    `criteria.propose` (`:64`).
  - The shortlist rule is carried on the derived task's `candidate_universe.shortlist_rule`, with
    `kind: top_k_by_position`, `k`, `ties_at_boundary: included`, the source snapshot id and the
    source rule set ref (`:44-48`), plus `derived_from_task_id` (`:47`).

- **Current state**: implemented, 67 lines, and deliberately candidate-blind: "Nothing about the
  shortlist rule refers to any particular candidate" (`:6`).
  - `shortlist_members` includes every entry whose `preference_score` equals the K-th ranked
    entry's score, not just its position (`:25-28`).
  - `shortlist_task` takes the *latest* snapshot unconditionally (`:30`).
  - It strips the `cand_<scheme>-` prefix from each candidate ref so the new universe is an
    `enumerated_set` of raw identifiers (`:34-41`).
  - It copies each latest rule and its attribute with a `copied_from` link and without
    id/version/status (`:56-64`), and re-raises a source dispute on the copy by passing the
    dispute's inspection bundle into `criteria.propose` (`:52-55`, `:65-66`).

- **Handoff notes**:
  - A shortlist is a new task, not a filter — everything downstream (identity resolution, rule
    confirmation, running) treats it as a fresh task, and the identifiers in its universe are the
    adapter identifiers, not candidate ids.
  - Ties are decided on `preference_score` equality alone, so a re-scored source board can change
    the shortlist's membership even at the same K.
  - The dispute carry-over only matches review items whose `why_expert_required` starts with
    "proposer and critic" (`:53-54`) — a differently-worded dispute will not be copied.

### `freeze` — `src/mas/core/freeze.py`

- **What it is**: Pre-registration: a prospective policy is registered before results with a
  digest over the declared fields; `verify` compares what ran against what was registered and
  returns the drift; `bind_artifacts` records the artifact manifest a run actually used, which
  cannot exist at registration time.

- **Entry points**: `POLICY_FIELDS:29` (14 fields); `REQUIRED:46`; `FreezeError:49`;
  `register:53`; `registrations:82`; `verify:92`; `bind_artifacts:112`.

- **Records/artifacts it owns**:
  - Artifacts `preregistration` (`:74`) and `freeze_binding` (`:124`); ids `proto` (`new_id` at
    `:68`) and `bind` (`:122`).
  - Both write the *same* event type, `preregistration.recorded`, on the task stream (`:75`,
    `:125`), the binding distinguished only by `kind: "binding"` in its payload (`:125`).

- **Registration**: `register:53` refuses unknown policy fields — "registering a field nothing
  reads is a claim nobody can check" (`:60-62`) — and refuses a policy missing any `REQUIRED`
  field — "a registration without [...] does not fix what the result is" (`:63-66`). The digest
  covers the policy alone "so re-registering identical policy is detectable and a timestamp
  cannot make two different policies look like two of the same" (`:70-72`).

- **Verification**: `verify:92` resolves the registration artifact, compares each field the caller
  supplies in `actual` against the registered policy by canonical text, and returns
  `{conforms, drift, fields_not_registered, checked_fields}` — it returns drift rather than
  raising, because "a deviation is a result to report, and a run that quietly conformed because
  the checker refused to look is the failure this prevents" (`:93-97`).

- **Binding**: `bind_artifacts:112` refuses to bind when no registration exists on the task
  (`:119-120`) and stores its own artifact pointing at the registration "rather than amending it"
  (`:114-118`). Its captured digest is over `captured` alone (`:123`).

- **Current state**: implemented and tested, but with **no production caller**.
  - `freeze` is imported only by its own test (`tests/test_freeze.py:5`); there is no `freeze` CLI
    subcommand, and `criteria.confirm_rule_set` accepts `preregistration_ref=None`
    (`criteria.py:646`), only flagging a fitted-after-results ordering method with no reference
    (`criteria.py:894`, `registration_missing` validation at `:882-895`).
  - Nothing in `register` can check that the registration preceded the results; "prospective" is a
    contract stated in the docstring, not an enforced ordering.
  - **Gap (observed defect candidate)**: `registrations:82-89` selects every
    `preregistration.recorded` event and returns the payload's artifact record, so a
    `bind_artifacts` binding is returned as if it were a registration (the payload differs only by
    `kind: "binding"`, `:125`). A binding record has neither `policy` nor `preregistration_id`
    (`:122`), so a caller that enumerates `registrations()` and calls `verify` on each would raise
    `KeyError` at `freeze.py:104` (`record["policy"]`) or `:107` (`record["preregistration_id"]`).
    `tests/test_freeze.py` pins only the single-registration case (`:45`), so the conflation is
    untested. The fix is a one-line filter on `payload.get("kind")`, but the current accessor
    makes no distinction.

- **Handoff notes**:
  - `POLICY_FIELDS` and `REQUIRED` are the definition of what "prospective" means here; changing
    either changes the digest of future registrations and cannot change past ones.
  - `verify` never raises on deviation — the caller owns what drift means (report, refuse,
    re-register).
  - A binding may resolve a prospective reference but must not carry scientific policy
    (`:114-118`); if a future binding needs to, that is a design change, not a field addition.

### `recovery` — `src/mas/core/recovery.py`

- **What it is**: The primary acceptance measurement. The derivation is compared against a sealed
  historical criteria list that arrives once, after the criteria are frozen, is visible only to
  the isolated evaluator, and is reported as coverage over its items rather than as agreement with
  the system. All of it is on the case stream, separated from the run streams.

- **Entry points**:
  - `SCHEMA_VERSION:49`; `INTAKE_KIND` / `COMPARISON_KIND` / `REPORT_KIND:54-56`;
    `EVALUATOR_ROLE = "evaluator_judge":60`; `DERIVING_ROLES:63`; `CATEGORIES:69`; `FACETS:70`;
    `_DIFFERENCE_OF_FACET:75`; `RESTATEMENT_STRATA` / `INDEPENDENT_STRATA:81-82`;
    `EVALUATOR_ONLY_FILES:95`; `PUBLISHED_DIRECTORIES:96`; `RecoveryError:99`; `GateRefusal:105`.
  - `case_stream:116`; `frozen_snapshots:140`; `record_intake:186`; `intake_reference:257`;
    `read_intake:270`; `access_log:292`; `derived_set:323`; `check_mapping:440`;
    `check_isolated_evaluator:591`; `propose_mapping:661`; `exposure_declaration:693`;
    `compare:746`; `latest_comparison:796`; `_counts:805`; `_origin_view:844`; `report:892`;
    `public_counts:974`; `render_markdown:1053`; `render_counts:1124`; `manifest:1165`; `write:1194`.

- **Records/artifacts it owns**:
  - Artifacts `historical_criteria_intake`, `recovery_comparison`, `recovery_report`.
  - Events `case.version_recorded` (`:242`), `evaluator_only.read` (`:282`), `evaluation.recorded`
    (`:783`), all on the case stream (`case_stream:116`).
  - Files `recovery_report.json`, `recovery_report.md`, `recovery_counts.json`,
    `recovery_counts.md`, `recovery_manifest.json` (`:86-90`).
  - Vocabulary domains `intake_provenance_form`, `completeness_attestation`, `field_visibility`,
    `recovery_mapping_shape`, `recovery_match_basis`, `recovery_difference_kind`,
    `recovery_category`, `recovery_view`.

- **The comparison against the sealed list**:
  - Intake: `record_intake:186` requires a `provenance_form` and a `completeness_attestation` (defaults supplied where absent, `:206-207`), marks the record `field_visibility: evaluator_only` (`:225`), stores the artifact and journals `case.version_recorded` (`:237-242`).
  - Isolation: only the `evaluator_judge` role may open it (`EVALUATOR_ROLE:60`); `check_isolated_evaluator:591` plus `DERIVING_ROLES:63` (planner, proposer, critic, adjudicator, retriever, reader, summarizer, reflector, operator, coordinator) bar every deriving role, and every read is logged through `access_log:292` as `evaluator_only.read`.
  - The mapping: `propose_mapping:661` obtains a mapping (model or caller-supplied) and `check_mapping:440` gates it deterministically — each row's shape, match basis and difference kind are validated against the vocabularies (`:485-518`), a row with no differences is `exact` and anything else `near_equivalent` (`:518`), and the comparison's `recovery_view` flips to `assisted` if the mapping shows taint or assisted refs (`:740`); a mapping that fails the gate raises `GateRefusal:105`.
  - `compare:746` pins the derived criteria at the intake's freeze sequence (`intake["freeze"]["frozen_at_seq"]`), builds the derived set there, and records the comparison artifact and `evaluation.recorded` (`:782-783`); the gate and the route that produced the mapping ride on the comparison record.
  - The partition: `CATEGORIES:69` is `exact`, `near_equivalent`, `missed` — "exactly these three, exclusive and exhaustive over the historical items, so the counts sum to the number of items supplied" (`:68-71`); `extra` labels the derived side only and is never a historical item's category, and `_DIFFERENCE_OF_FACET:75` fixes the vocabulary so a near-equivalent must name whether it rests on expression, scope or threshold.
  - Exposure: `exposure_declaration:693` computes isolation as a finding from the access log and the exposure declarations on the confirming decisions — "where a declaration and the log disagree, the log prevails" (`:700`); `undeclared` is treated as exposed, which is why both the assisted and the independent view are always reported (`:718-724`).
  - `report:892` refuses a second mapping over an already-compared list (`comparison_already_recorded`, `:894-903`) — "a second mapping over a list that has been opened cannot be reported as another independent recovery" — and refuses a report whose intake content hash differs from the one compared (`intake_changed`, `:905-908`); a derived-set payload digest drift is reported with a note, not refused, because claims admitted after the pin live outside the pinned sequence (`:910-919`).
  - `_origin_view:844` stratifies by origin (`task_mandated`, `adapter_template`, `literature_derived`): an item matched only by a restatement is "counted here as supplied rather than derived" and keeps its category in the primary counts (`:874-888`).
  - `public_counts:974` builds the published slice (`field_visibility: agent_visible`, `:985`); `write:1194` writes the evaluator-only files and the counts, refusing any destination inside `PUBLISHED_DIRECTORIES` = `design_audit` because "the one directory a reviewer is told to read is the one place this content must not land" (`:95-96`, `:1199-1203`).

- **Current state**: implemented; two evaluator-role CLI actions expose it (`cli/main.py:1030-1056`,
  subparser at `:1204-1216`, actions `intake` and `report`).

- **Handoff notes**:
  - The real list must not enter the repository — `tests/test_recovery.py:1-6` says so in its own
    words: every historical item in that file is synthetic and says so in its label; the real list
    is sealed, arrives once through `recovery.record_intake` after the criteria are frozen, and
    "appears in no fixture, default or literal here".
  - The counts mean what they mean only relative to the frozen sequence and the intake content
    hash, so a re-import that changes either must not be reported as the same measurement.
  - Nothing in the deriving path may call `compare` or `report`; the isolation check is what
    enforces that, and the access log is the record a reviewer reads, not the declaration.

### `sr_stage` — `src/mas/core/sr_stage.py`

- **What it is**: The symbolic-regression stage: it turns a run's own resolved rows into a dataset
  with declared features, proposes expressions through a proposer/critic loop, fits them, makes one
  holdout check, and — when a winner is adopted — installs it as the rule set's ordering method
  and asks an expert to confirm it. Off unless settings say otherwise (`enabled:663`, mode from
  `sr.mode`, `MODES_BY_SETTING:52`).

- **Entry points**:
  - `SR_VERSION = "sr-stage-1":41`; `STEP = "symbolic_regression":43`; `FEATURE_CAPABILITIES:48`;
    `RESERVED_FEATURE_REFS:51`; `BUFFER = 3:54`; `HonestyViolation:58`; `Feature:113`;
    `Dataset:132`; `potency_target_rules:173`; `build_dataset:186`; `refuse_leaking_features:270`;
    `summary_for_proposer:293`; `assert_blind:318`; `refused_feature_requests:335`;
    `hinge_problems:347`; `grounding_labels:363`; `ScoringContext:381`; `_critique:419`;
    `_attempt:473`; `adoption_check:604`; `rationale:635`; `rationales`; `enabled:663`;
    `_knobs:667`; `reference_outcomes:686`; `fit_and_install:699`; `_winner:790`; `_install:799`;
    `rationale_of:848`; `record_of:860`.

- **Records/artifacts it owns**:
  - Artifacts `symbolic_regression` (`:780`), `scoring_expression`, `scoring_rationale`
    (`_install:805-845`); id `expr:804`.
  - Run events `run.annotated:726`, `step.started:737`, `decision.recorded:775`,
    `step.completed:781`.

- **Current state**: implemented; the honesty guards are the substance.
  - `refuse_leaking_features:270` rejects a proposed feature that is not one of the declared
    `FEATURE_CAPABILITIES` or that leaks the target.
  - `assert_blind:318` keeps the proposer from seeing outcomes, and `reference_outcomes:686`
    returns the candidates excluded from every split plus the labels the proposer may never see
    (the task's declared reference outcomes).
  - `RESERVED_FEATURE_REFS:51` bars a feature from being the preference score, coverage, position
    or rank it is meant to produce.
  - `_knobs:667` reads every number from registered constants (`const_sr_*`, defaults in
    `constants.py:28-39`).
  - Adoption is one look at the holdout: `adoption_check:604` compares Kendall tau against the
    weighted-preference baseline *recomputed over the holdout members alone* (because "a
    percentile score depends on the set it is computed in"), adopts when the margin is at least
    `const_sr_min_improvement`, and names its refusal reason (`holdout_too_small` /
    `did_not_beat_the_baseline_on_the_holdout`, `:604-632`).
  - `_winner:790` picks among adopted attempts by margin, then fewest terms, then canonical text.
  - `_install:799` registers the expression artifact, builds the `ordering_method`
    (`kind: "symbolic_expression"`), re-confirms the rule set through `criteria.confirm_rule_set`
    carrying the run's own deferral forward (why-comment `:826-830`), and opens a review request
    requiring an expert to confirm an ordering method fitted on the run's own results
    (`:832-837`).

- **Handoff notes**:
  - Adoption is decided on the holdout against the recomputed baseline, never on the fitting or
    selection metric; the three splits come from `symbolic.split_candidates` and reference outcomes
    are excluded outright.
  - Installing an expression changes what the board ranks on, so the `confirm_rule_set` ordering
    method and the review request are the audit pair — a change to `_install` that skips either
    breaks the only path by which a fitted score becomes authoritative.
  - `rationale_of:848` / `record_of:860` are the read-back pair the CLI uses; they depend on the
    `step.completed` payload's `step` and `artifact_id` staying as they are.

### `symbolic` — `src/mas/core/symbolic.py`

- **What it is**: The fitting engine behind `sr_stage`: a small term grammar, OLS solutions on
  standardised columns shrunk to a declared prior, a condition-number guard, sign checking against
  declared term directions, deterministic hashed three-way splits, and a deterministic total order
  for selecting between candidates. No model calls, no I/O, no journal writes (0 in 630 lines).

- **Entry points**:
  - `FITTER_VERSION` / `GRAMMAR_VERSION:29-30`; `FORMS:33`; `CONSTANT_FORMS:34`;
    `TERM_DIRECTIONS:37`; `MODES:38`; `PROVENANCES:39`; `GROUNDINGS:40`; `SPLIT_NAMES:41`;
    `SELECTION_METRICS:43`; `ADOPTION_METRIC:44`; `GrammarError:49`; `FitRefused:57`.
  - `Term:67`; `parse_term:156`; `parse_terms:191`; `Expression:208`; `solve:273`;
    `condition_estimate:294`; `fit:354`; `sign_violations:433`; `evaluate:470`; `kendall_tau:524`;
    `metric_on_rows:549`; `selection_score:565`; `better:573`; `Split:586`; `split_candidates:611`.

- **Records/artifacts it owns**: none; it defines the vocabularies (`MODES`, `PROVENANCES`,
  `GROUNDINGS`, `SPLIT_NAMES`, `TERM_DIRECTIONS`) that `sr_stage` records on the expression
  artifact, and the version strings that ride on it.

- **Current state**: implemented.
  - Hinge terms take their knee from a grid the proposer is shown (`const_sr_hinge_grid`,
    `constants.py:37-39`); a constant anywhere else must come from a claim the term cites — that
    constraint is enforced by `sr_stage.hinge_problems:347`, not here.
  - `fit:354` refuses a design it cannot solve within the condition limit (`FitRefused:57`,
    `const_sr_max_condition`), and `sign_violations:433` checks fitted signs against
    `TERM_DIRECTIONS`.

- **Handoff notes**:
  - `FITTER_VERSION` / `GRAMMAR_VERSION` ride on every installed expression, so bumping either
    invalidates the provenance of previously installed ones — treat it as a new fitter, not a
    patch.
  - Splits are hashed and deterministic; do not introduce a random source, because the split is
    part of the record a reviewer reproduces.
  - `SELECTION_METRICS` / `ADOPTION_METRIC:43-44` name what selection and adoption are measured
    on; changing them changes both the winner and the honest reading of it.

### `mechanism` — `src/mas/core/mechanism.py`

- **What it is**: The mechanism-of-action narrative: a separate artifact generated on demand from
  admitted, span-verified claims, gated so a sentence survives only if it cites a claim that names
  the candidate. Its record fields state the separation: it is not evidence and enters no score,
  verdict, ranking or coverage figure (`mechanism.py:322-326`).

- **Entry points**:
  - `MECHANISM_VERSION:46`; `STEP = "mechanism_narrative":47`; `MAX_CLAIMS` / `MAX_SENTENCES:49-50`;
    `FORBIDDEN_KEYS:54`; `SeparationViolation:59`.
  - Scaffolding `MECHANISM_STEMS:91`, `SCORING_WORDS:101`, `CONDITION_FIELDS:108`;
    `grounding_text:127`; `names_candidate:151`; `eligible_claims:168`; `citation:174`;
    `gate:192`; `check_separate:249`; `labels_for:260`; `narrative_of:273`; `narratives_of:283`;
    `explain:293`; `explain_shortlist:357`.

- **Records/artifacts it owns**:
  - Artifact `mechanism_narrative` (`:343`); run events `step.started:311` and
    `step.completed:344` with `step`, `candidate_ref`, `artifact_id`, `explanation_status`,
    sentence counts and `is_evidence: False` in the payload.
  - The record's own fields: `explanation_status` (`evidence_linked` / `unexplained`),
    `unexplained_reason`, `claims_offered`, `sentences`, `dropped_sentences`, `model_id`.

- **Current state**: implemented; on demand only, called from the CLI (`cli/main.py:781`, `:794`
  for `candidate explain` / `explain_shortlist`).
  - `explain:293` is idempotent: a narrative already recorded for the candidate is returned
    unchanged, with no model call and no new event, so a resumed or repeated shortlist costs
    nothing (`:301-305`).
  - It reads the claims itself, never accepting them as arguments: "only admitted claims with a
    verified span can reach the summarizer" (`:299-300`).
  - If there are no eligible claims, or no model bound to the `summarizer` role, it records an
    `unexplained_reason` instead of a narrative (`:330-334`).

- **Handoff notes**:
  - `FORBIDDEN_KEYS:54` and `check_separate:249` are the enforcement of "never an input to a
    score" — a record carrying a scoring key is refused with `SeparationViolation:59`, and
    `is_evidence: False` plus the note are written on the record itself (`:323-325`) so the
    separation is readable without reading this module.
  - The grounding gate drops any sentence that does not cite an eligible claim naming the
    candidate; weakening it would let the summarizer introduce unsupported mechanism.
  - The step id embeds run, step and candidate, so idempotence depends on `narrative_of` and the
    step id staying aligned.

### Module map (dependency order)

1. `ledger` + `identity` — record-level foundations: sources and claims with admission state; candidate ids. Everything downstream reads what `ledger.claims` returns.
2. `reading` -> `evidence` — retrieval and admission; what `evidence.gather` unions is exactly what a cell may be scored on.
3. `assessor` -> `symbolic` -> `sr_stage` — verdicts and roll-ups; the fitting engine; the stage that installs a fitted ordering method and asks for it to be confirmed.
4. `leaderboard` -> `controller` -> `staging` — the board, the run that publishes it, the shortlist task derived from the latest board.
5. `freeze`, `mechanism`, `recovery` — prospective policy record, the on-demand narrative, and the evaluator-only historical comparison; leaf modules, none of them on the core scoring path.

### Module section D — model adapters, domain/literature/prediction adapters, CLI, bridge, UI

### `core/models.py` — `src/mas/core/models.py`
- **What it is**: Provider-agnostic model adapters plus role→adapter resolution ("Model adapters and role resolution", `models.py:1`). Every agent role is bound at run start to one adapter.
  - Four adapter kinds: `anthropic` (Messages API), `openai_compatible` (any OpenAI-style chat-completions endpoint — DeepSeek, vLLM, a user's own provider, `models.py:7`), `exchange` (a file bridge answered by an outside agent, e.g. Claude subagents, `models.py:8-9`), and `scripted` (deterministic, tests only, `models.py:10`).
- **Entry points**:
  - Schemas: `CapabilityRecord` (`models.py:39`), `ModelRequest` (`models.py:54`), `ModelResponse` (`models.py:66`, `reasoning` kept in the trace only, `models.py:76`; `truncated` marks a token-limit stop, `models.py:77`), `ModelAdapter` Protocol (`models.py:80`).
  - Structured output: `extract_json` (`models.py:91`, tolerates code fences and prose), `validate` (`models.py:109`, JSON-schema subset: type/required/properties/items/enum), `schema_instruction` (`models.py:133`).
  - `AnthropicAdapter.complete` (`models.py:181`) POSTs `{base_url}/v1/messages` with `x-api-key` and `anthropic-version: 2023-06-01` (`models.py:186-189`).
  - `OpenAICompatibleAdapter`: `decoding` (`models.py:225`), `payload` (`models.py:236`), `complete` (`models.py:256`).
  - `ExchangeAdapter`: `post` (`models.py:316`), `wait` (`models.py:326`), `complete` (`models.py:338`).
  - `ScriptedAdapter` (`models.py:343`); `adapter_from_config` (`models.py:364`).
  - `ModelRoster` (`models.py:392`) with `from_toml` (`405`), `from_tables` (`411`), `adapter` (`416`), `role_bindings` (`421`).
  - `call_role` (`models.py:429`) — journal, budget charge and schema enforcement in one place.
- **Records/artifacts it owns**: journal events `agent.started`/`agent.finished` per call (`models.py:454`, `489`) and `run.annotated` budget-threshold events (`models.py:499-504`).
- One `trace` artifact per call with raw request, final text, schema problems and reasoning (`models.py:484`). Role names are fixed in `ROLES` (nine: planner, proposer, critic, adjudicator, retriever, reader, summarizer, reflector, evaluator_judge; `models.py:361`).
- **Current state**: implemented. `adapter_from_config` builds only anthropic/openai_compatible/exchange — the `scripted` kind exists but is not constructible from config (`models.py:364-389`). `ExchangeAdapter.wait` uses `text` if present, else `json.dumps(data)`, so a response with neither yields the literal `null` (`models.py:334`).
- For OpenAI-compatible providers, `thinking=True` sends no thinking field and omits temperature (`models.py:225-234`, `246-249`); a `finish_reason == "length"` reply is retried with doubled `max_tokens` up to `max_token_ceiling` and returned with `truncated=True` (`models.py:285-290`, `297`); `reasoning_content` is captured (`models.py:296`).
- **Handoff notes**:
  - Keys are read at call time from env var or key file and must never enter a record, trace or error message (ADR-40, `models.py:12-13`, `140-151`, `redact` at `162`).
  - `call_role` re-asks a reply that fails the schema with the listed problems; the default `max_repairs=2` is measured, not chosen: one repair was insufficient against DeepSeek `deepseek-v4-flash` on 2026-10-14 and cost three derivation runs (`models.py:439-443`); exhausting them raises `parse_failed` (`models.py:506`).
  - Budget contract: `llm_turns` is charged before the call and again per repair (`models.py:450`, `475`), USD is accumulated and threshold-annotated (`models.py:495-504`).
  - `role_bindings` go into the Run Binding and include the decoded parameters (`models.py:393`, `421-426`); an exchange dir given as a relative path resolves against the config file's directory (`models.py:384-385`).

### `adapters/drug/*` — `chembl.py`, `gtopdb.py`, `pubchem.py`, `registration.py`, `universe.py`
- **What it is**: Drug-prioritization adapter v1 (`registration.py:1`). Provider classes speak three remote curator families — ChEMBL web services, PubChem PUG REST, IUPHAR/BPS Guide to Pharmacology open bulk files — plus a local documented universe file. `registration.py` is the composition root: a CLI or script calls `register(broker)` and passes `ADAPTER` to the run controller; the core never imports this module (`registration.py:3-5`).
- **Entry points**:
  - `register(broker, *, literature, universe_file, cache_dir, upload_dir, predict, predict_python)` (`registration.py:43`); `ADAPTER` and `CAPABILITY_BINDINGS` (`registration.py:17`, `20-28`).
  - Universe (no network): `UniverseIdentity.invoke` (`universe.py:34`, resolve_name), `UniverseRecordField.invoke` (`universe.py:71`, record_field).
  - PubChem: `PubChemIdentity.invoke` (`pubchem.py:37`), `PubChemProperty.invoke` (`pubchem.py:95`) served by `PropertyCache.row` (`pubchem.py:77`).
  - ChEMBL: `ChEMBLBioactivity.invoke` (`chembl.py:129`, pchembl_values), `ChEMBLMechanism.invoke` (`chembl.py:179`, mechanism_records), `TargetCache.activities/mechanisms` (`chembl.py:104`, `110`).
  - GtoPdb: `GtoPdbAffinity.invoke` (`gtopdb.py:112`) over `GtoPdbData.load/uniprot_for` (`gtopdb.py:60`, `76`).
  - Proposer-facing catalog: `EVIDENCE_CATALOG` (`registration.py:98`), `_panel_entries` built from the predictor panel itself (`registration.py:79-94`), `DIMENSIONS` (`registration.py:196`), `objective_templates` (`registration.py:204`).
- **Records/artifacts it owns**: tool contracts `tool_drug_universe_identity` (`universe.py:18`), `tool_drug_universe_record_field` (`universe.py:60`), `tool_drug_pubchem_identity` (`pubchem.py:31`), `tool_drug_pubchem_property` (`pubchem.py:86`).
- `tool_drug_chembl_bioactivity` (`chembl.py:119`), `tool_drug_chembl_mechanism` (`chembl.py:169`), `tool_drug_gtopdb_affinity` (`gtopdb.py:101`).
- **External hosts**: `ebi.ac.uk/chembl/api/data` (`chembl.py:10`), `pubchem.ncbi.nlm.nih.gov/rest/pug` (`pubchem.py:12`), `guidetopharmacology.org/DATA` (`gtopdb.py:26`) plus the ChEMBL target endpoint for UniProt accessions (`gtopdb.py:29`, `81`).
- **Value stamps**: pChEMBL rows are `pchembl_value`, `value_kind: curated` (`chembl.py:147`); PubChem descriptors are `derived` (`pubchem.py:102`).
- A mechanism row is the categorical `target_engagement=True` with `determination_basis: curated` and its references in conditions (`chembl.py:192-211`).
- **Current state**: implemented. The salt/parent handling is deliberate: every per-compound ChEMBL query asks both `molecule_chembl_id` and `parent_molecule_chembl_id` and unions by row id, because measured 2026-10-13 imatinib at ABL1 has 106 rows under `molecule_chembl_id=CHEMBL941` vs 108 under `parent_molecule_chembl_id=CHEMBL941` (`chembl.py:33-41`, `69-90`). Censored relations (">", "<") are skipped as non-point measurements (`chembl.py:145-146`); GtoPdb keeps only Human rows with relation `""`/`"="`/None (`gtopdb.py:120`). `UniverseRecordField` maps a False route/warning flag to no value when no `first_approval` exists, because ChEMBL derives those flags from approved-product records (`universe.py:81-85`).
- **Handoff notes**:
  - `register`'s `predict` tri-state: `None` registers the ADMET panel only when an interpreter with `admet_ai` is found; `True` makes a missing environment refuse loudly once per cell (`environment_missing`); `False` leaves it out (`registration.py:47-60`, `72-74`).
  - Registration order is load-bearing: Europe PMC and PubMed come before Bookshelf/MediaWiki so an unnamed source search reaches the first answering tool (`registration.py:75-76`, `tools.py:20`).
  - `objective_templates`' why-comments are the design record and must be read before editing (`registration.py:216-247`): one required-target potency attribute carries three routes (ChEMBL pChEMBL + GtoPdb + literature) so one quantity is not registered twice; predicted affinity is deliberately not a route on measured potency, because percentile-ranking a shrinkage prediction against measurements would rank study coverage (`registration.py:240-247`).
  - The oral-route criterion no longer says "approved" (1,262 of 3,177 candidates have no approval record, `registration.py:283-294`), and it accepts `peer_reviewed`, not `peer_reviewed_primary`, which names no registry kind (`registration.py:322-330`).
  - `EVIDENCE_KINDS` is declared empty and computed after the catalog so it cannot drift from the entries and the literature registry (`registration.py:34-40`, `192-193`).

### `adapters/literature/*` — `http`, `registry`, `jats`, `textparse`, `europepmc`, `pubmed`, `bookshelf`, `mediawiki`, `uploads`, `tools`
- **What it is**: Six evidence sources behind one broker registration (`tools.py:19-28`): Europe PMC (search + full-text reading), PubMed (search only), NCBI Bookshelf (synced open-access books), Wikipedia and Wikibooks (MediaWiki), and a user-supplied uploads folder. `registry.py` is the policy gate: every source declares its licence and whether a language model may read its text, and a refused or unknown source is never queried (`registry.py:1-10`).
- **Entry points**:
  - Transport: `http.get` (`http.py:31`) with the error-class map — 404→None, 429→rate_limited, 401/403→ToolAbsent, ≥500→upstream_server_error, other 4xx→input_invalid non-retryable (`http.py:39-48`); per-host politeness intervals (`http.py:16-28`).
  - Registry: `Source` (`registry.py:17`), `SOURCES` (`registry.py:37-69`; europepmc, pubmed, bookshelf, wikipedia, wikibooks, uploads, and openstax refused), `permitted` (`registry.py:78`), `resolve` (`registry.py:89`), `for_hit` (`registry.py:97`).
  - Europe PMC: `EuropePMCSearch.invoke` (`europepmc.py:49`), `EuropePMCReader.invoke` (`europepmc.py:77`), `normalize_hit` (`europepmc.py:19`).
  - PubMed: `PubMedSearch.invoke` (`pubmed.py:27`); documents are read through the Europe PMC reader, as the registry declares (`registry.py:43-46`).
  - Bookshelf: `BookshelfLibrary.sync/index/file_list/locate` (`bookshelf.py:232`, `178`, `113`, `147`), `relaxation_plan` (`bookshelf.py:405`), `BookshelfSearch.invoke` (`bookshelf.py:490`), `BookshelfReader.invoke` (`bookshelf.py:580`).
  - MediaWiki: `MediaWikiSearch` (`mediawiki.py:29`), `MediaWikiReader` with revision-pinned reading (`mediawiki.py:71-79`).
  - Uploads: `UploadLibrary.check/documents/passages/hit` (`uploads.py:77`, `96`, `100`, `107`), `parse_file` (`uploads.py:43`), `UploadsSearch`/`UploadsReader` (`uploads.py:128`, `159`).
  - Parsers: `jats.parse` (`jats.py:66`), `jats.parse_bits` (`jats.py:142`), `abstract_passages` (`jats.py:121`), `textparse.html_passages`/`text_passages` (`textparse.py:102`, `116`); `tools.register` (`tools.py:19`).
- **Records/artifacts it owns**: tool ids `tool_literature_europepmc_search/reader`, `tool_literature_pubmed_search`, `tool_literature_bookshelf_search/reader`, `tool_literature_wikipedia_*`, `tool_literature_wikibooks_*`, `tool_literature_uploads_search/reader` (declared per source in the registry's `search_tool`/`reader_tool`, `registry.py:37-68`; contracts live on each class). Hits keep their `source` id so the reader, ledger and leaderboard can say where a claim came from (`registry.py:8-10`).
- **Passage identities**: stable locators in the shape `abstract.p1`, `sec2.p3`, `article-20545.s3.p1` (`jats.py:3-5`, `142-147`); paragraph and lead extraction feed the same shape from HTML/plain text (`textparse.py:3-5`).
- **External services**: Europe PMC REST (`europepmc.py:11`), NCBI E-utilities and the LitArch FTP (`bookshelf.py:49-50`, `pubmed.py:12`), MediaWiki APIs (`mediawiki.py:16-19`).
- Locally, `pdftotext` for PDF uploads (`uploads.py:46-55`).
- **Current state**: implemented. Bookshelf must be synced per book first (`bookshelf.py:232-277`) and its search refuses with `not_configured` until then (`bookshelf.py:491-493`); uploads need a `manifest.toml` declaring a licence and `llm_ingestion_permitted = true` (`uploads.py:77-94`); OpenStax is registered as refused (`registry.py:66-68`). Bookshelf search relaxes long boolean queries progressively and records every attempt (`bookshelf.py:13-18`, `405-428`), ranking by query-dependent title match with genre only as a tie-break (`bookshelf.py:554-556`). Uploads identity is the full 64-char sha256 and the reader re-checks it against the bytes on disk before reading (`uploads.py:109-114`, `175-176`).
- **Handoff notes**:
  - `registry.permitted` is checked before any search (`registry.py:8-9`); adding a source means declaring `automated_access`, `license` and `llm_ingestion`, or `resolve` refuses the whole list (`registry.py:89-91`).
  - MediaWiki reads are pinned to the latest revision at or before the evidence cutoff so a run never reads text written after it, and the citation (`oldid`) is a permalink (`mediawiki.py:3-5`, `71-79`).
  - Bookshelf sync streams the whole tarball and keeps only chapter XML (StatPearls is ~2 GB once images are dropped) (`bookshelf.py:4-8`, `246-258`); its term/title index is rebuilt when a book is re-synced, keyed by an accession@updated stamp (`bookshelf.py:81-84`, `178-208`).
  - `html_passages` stamps the pre-heading lead with `kind: "abstract"` so passage selection always keeps it, the same rule as a paper's abstract (`textparse.py:3-5`); JATS reference lists and known back-matter sections are skipped (`jats.py:37-39`).

### `adapters/predict/*` — `admet.py`, `_admet_worker.py`
- **What it is**: Predicted molecular properties from a local ADMET-AI panel: 41 endpoints predicted by a Chemprop-RDKit ensemble trained on a TDC dataset plus 11 physicochemical descriptors computed by RDKit (`admet.py:28-31`, table at `92-240`).
- The predictor lives in its own interpreter and is reached by a subprocess running `_admet_worker.py`, which imports only the standard library and `admet_ai`, so the core's install stays `requests`-only (`admet.py:18-23`, `_admet_worker.py:1-6`).
- **Entry points**:
  - `AdmetPrediction.invoke` (`admet.py:625`, question kind `admet_prediction`), `provenance` (`admet.py:663`), `warm_universe` (`admet.py:682`), `check` (`admet.py:701`).
  - Environment discovery: `candidates` (`admet.py:266`), `has_package` (`admet.py:307`), `interpreter` (`admet.py:314`), `available` (`admet.py:319`).
  - Structures: `structure_file_for` (`admet.py:335`) and `StructureIndex` (`admet.py:340`, InChIKey→SMILES from `universe_smiles.json` beside the universe file).
  - Cache: `PanelCache` (`admet.py:407`) with `stored/path/_run/row/warm` (`admet.py:449`, `445`, `495`, `567`, `582`).
  - Worker protocol: stdin SMILES lines; stdout JSON lines `meta`/`panel`/`row`/`done` (`_admet_worker.py:8-15`, `82-107`).
- **Records/artifacts it owns**: one contract `tool_predict_admet_panel` (`admet.py:611`) producing `model_prediction` values stamped `value_kind: predicted` and `determination_basis: predicted` (`admet.py:654-655`).
- On-disk cache rows under `cache_dir/admet/admet-ai-2-panel-1/<2-char>/<sha256>.json` (`admet.py:61`, `436`, `445-447`) plus `worker.log` (`admet.py:501-509`). External services: none — only the local predictor process.
- `PANEL_VERSION` keys both the recorded table and the cache so a package or table change serves new values (`admet.py:59-61`).
- **Current state**: implemented and availability-gated. A missing interpreter or package refuses non-retryably with `environment_missing` and the interpreters tried (`admet.py:324-330`); a missing structure file refuses the same way (`admet.py:364-368`).
- A compound with no structure in the universe returns no value with a warning — unknown, never a failure (`admet.py:634-640`).
- The installed panel is verified on every batch against the recorded table (name/category/task_type/package_units) and refused with `schema_violation` on drift (`admet.py:472-493`).
- **Determinism caveat**: ensembles run in inference mode so nothing is sampled, but values are not bit-exact across batches (measured up to 2.8e-6 relative between a batch of 3 and batches of 256; `admet.py:414-424`), so two cached predictions must never be compared for equality.
- **Handoff notes**:
  - The capability boundary is the invariant: a prediction never stands in for a measurement, and `criteria.check_attribute` refuses `predicted` alongside any other basis (`admet.py:11-16`). The 11 descriptors are RDKit calculations stamped `predicted` with the rest — the conservative single-basis reading — and PubChem `computed_property` remains the `derived` route (`admet.py:29-33`).
  - `_check_panel` must stay on every batch: a package that moved an endpoint would otherwise have values labelled by the old table (`admet.py:476-479`).
  - Worker plumbing invariants: stdout is duplicated and fd 1 pointed at stderr before `admet_ai` imports, because the library prints warnings and progress bars on stdout (`_admet_worker.py:17-22`, `31-35`); worker stderr goes to a file rather than an undrained pipe to avoid deadlock (`admet.py:505-508`).
  - The encoding is explicit utf-8 because one unit carries the Angstrom sign (`admet.py:508-509`); a SMILES the model drops is emitted as an explicit error row, never silence (`_admet_worker.py:96-99`).
  - `mas predict warm` opens no store and may run beside a sweep, because the panel is a function of a structure alone (`main.py:974-981`).

### `cli/main.py` — `src/mas/cli/main.py`
- **What it is**: The `mas` terminal client and composition root (`main.py:1`). It resolves store, settings, model roster and broker, then dispatches one of 15 subcommands; `bridge` is intercepted before the argparse parser and delegated to `mas.cli.bridge` (`main.py:1084-1086`).
- Expert decisions are confirmed on the terminal itself, never from a script (`main.py:67`, `246-254`).
- **Entry points — subcommand map** (parsers at `main.py:1094-1222`):
  - `init` (`cmd_init`, `main.py:259`); `task new|list|show|shortlist` (`cmd_task`, `269`); the shortlist action cuts a top-K follow-up task (`275-280`).
  - `criteria propose|derive|reduce|mandated|pool|dedupe|export` (`cmd_criteria`, `288`).
  - Criteria helpers: `_reduce_pool` (`363`), `_dedupe` (`393`), `_export_criteria` (`444`), `_show_pool` (`501`), `_show_trajectory` (`486`).
  - `rules confirm|show` (`cmd_rules`, `529`); `review list|decide|adjudicate|reopen` (`cmd_review`, `563`; `cmd_review_adjudicate`, `604`).
  - `run start|show|resume` (`cmd_run`, `637`); `board show` (`cmd_board`, `678`).
  - `candidate show|explain` (`cmd_candidate`, `763`); `score show` (`cmd_score`, `821`).
  - `config show|validate|save|estimate` (`cmd_config`, `876`); `sources list|check|sync|template` (`cmd_sources`, `921`); `predict check|warm` (`cmd_predict`, `974`); `models show` (`cmd_models`, `1009`); `recovery intake|report` (`cmd_recovery`, `1014`); `ui serve` (`cmd_ui`, `1067`).
  - Global options `--store --models --config --preset --profile --set` (`main.py:1088-1093`); helpers `_person` (`146`), `_open` (`155`), `_implementation` (`162`), `_broker` (`190`), `_settings` (`220`), `_roster` (`229`).
- **Records/artifacts it owns**: no direct writes — every effect goes through core functions. It binds `_implementation()` (package version, git commit, dirty flag) into runs and exports (`main.py:162-174`).
- It writes two templates at face value: the example `models.toml` at init (`EXAMPLE_MODELS`, `main.py:89-143`) and the uploads manifest template (`UPLOAD_TEMPLATE`, `main.py:908-918`).
- **Current state**: implemented. `criteria derive` runs the iterative pool workflow and prints one round (`main.py:329-340`); `criteria reduce` requires `--continues RUN` and deliberately takes no broker so a merge strategy can be re-run against the same pool (`main.py:363-372`).
- `criteria export` opens the store read-only so it can run while a sweep holds the lock (`main.py:448-452`); `run resume` refuses on a config-hash drift unless `--allow-config-drift` (`main.py:660-664`).
- `review adjudicate` refuses unless `interaction.autonomous_adjudication` is on (`main.py:611-615`).
- **Handoff notes**:
  - `_roster` resolves providers/roles from the settings file when it has providers and no `--models` was given, otherwise it requires `models.toml` or exits (`main.py:229-239`). `_broker` passes the task's universe file, cache dir, upload dir and `predict.python` into the drug registration (`main.py:190-196`).
  - The confirmation invariant: `_confirm_on_terminal` reads from `/dev/tty`, so piping stdin cannot fake an expert decision (`main.py:246-254`), and the entry is recorded `interactive` vs `scripted` (`main.py:593-595`).
  - `_print_round` is shared by derive and reduce so the two outputs read alike (`main.py:342-344`); keep it shared when either command grows output.

### `cli/bridge.py` — `src/mas/cli/bridge.py`
- **What it is**: The outside-agent side of the exchange bridge (`bridge.py:1-10`). `mas bridge next` prints the oldest unanswered request in an exchange dir, `answer` writes a response file, `status` counts.
  - A response body is either a JSON value matching the request's `response_schema` (written as `"data"`) or `{"text": "..."}` for free-text requests, and the command adds `request_id`, `model_id` and `answered_by` (`bridge.py:8-9`, `86-90`).
- **Entry points**:
  - `cmd_next` (`bridge.py:64`), `cmd_answer` (`bridge.py:80`), `cmd_status` (`bridge.py:99`), `main` (`bridge.py:107`).
  - Helpers: `_pending` (oldest unanswered, `bridge.py:25-28`), `_finished` (DONE marker freshness, `31-42`).
  - `_claim` — the atomic claim marker (`bridge.py:45-61`).
  - Defaults: `--wait 600` (`bridge.py:112`), `--model-id "claude-opus (subagent)"` and `--answered-by "claude-subagent"` (`114-115`).
  - Claim takeover after `CLAIM_TIMEOUT_S = 1800` (`bridge.py:22`).
  - Exit codes: 0 a request was printed, 2 no pending request after the wait, 3 done (`bridge.py:64-77`).
- **Records/artifacts it owns**: files inside the exchange dir — `requests/*.json` and `responses/*.json` (written atomically via `.tmp` + `os.replace`, `bridge.py:92-94`) and `claims/<id>.claim` (`bridge.py:49-60`).
- It reads, never writes, the run-side `DONE` marker (`bridge.py:38-42`).
- The other side of the same protocol is `ExchangeAdapter` (`core/models.py:300-340`) and the `kind = "exchange"` provider block in the example config (`main.py:96-100`).
- **Current state**: implemented. `next` claims a request with an `O_EXCL` marker so two agents cannot answer the same request (`bridge.py:45-61`).
- A claim older than 30 minutes may be taken over, and re-delivery to the same agent is allowed after a failed answer (`bridge.py:45-61`).
- `answer` refuses a request id with no matching request file (`bridge.py:81-83`).
- **Handoff notes**:
  - The stale-`DONE`-marker hazard is a why-comment: a marker left by an earlier run makes `next --wait` return at once, so a polling agent concludes the work is over and stops answering while the waiting run blocks to its own timeout (`bridge.py:32-36`).
  - `_finished` therefore compares the marker's mtime against the newest request (`bridge.py:40-42`).
  - Response files must keep the exact shape `cmd_answer` builds (`request_id` plus `text` or `data`, plus `model_id`/`answered_by`), because `ExchangeAdapter.wait` reads `text` first and falls back to `data`; the two identity fields are informational and not read by the adapter (`models.py:303-305`, `333-336`).
  - Timing contract with the adapter: default timeout 3600 s, poll 1 s (`models.py:308-314`, `326-332`); a bridge session that exits without answering leaves the request pending until that timeout.

### `ui/server.py` — `src/mas/ui/server.py`
- **What it is**: The browser workbench: the read surfaces of one store root over loopback, written in the standard library (`server.py:1`).
  - One dictionary from `views` is rendered twice — as a page at `/leaderboard` and as its JSON twin at `/api/leaderboard` — so the two cannot disagree (`server.py:3-5`, `175-191`).
- **Entry points**:
  - `Workbench.open/view/handle` (`server.py:172`, `175`, `193`).
  - `make_server` (binds but does not serve, `261`), `serve` (`279`), `address` (`274`), `non_loopback_reason` (`246`).
  - Rendering: `_page` (`server.py:114`), `_json` (`125`), `_problem` (`129`).
  - All values pass through `html.escape` (`server.py:66-99`).
  - Page set: `PAGES = ("/", "/leaderboard", "/candidate", "/run", "/review", "/pool", "/settings")` (`server.py:37`).
  - Query helpers `_one`/`_maybe`/`_rows` (`server.py:141`, `148`, `153`).
- **Records/artifacts it owns**: none. It writes no journal event and no artifact: the store root is opened read-only for the length of one request (`server.py:172-173`, `179`).
- Request logging is silenced because "the journal records what happened; a request log would record only who looked" (`server.py:242-243`).
- **Current state**: implemented. Three properties are structural rather than promised: the store is opened `read_only=True` (`server.py:173`).
- Every method but GET and HEAD is refused with 405 and an `Allow: GET, HEAD` header (`server.py:198-202`, `228-229`).
- The bind address is checked before binding and a non-loopback host is refused with its reason (`server.py:246-258`, `265-267`).
- `views.NotFound`→404, `BadRequest`→400, `StoreError`→503 (`server.py:209-216`).
- **Handoff notes**:
  - The parity rule is the invariant: a new surface is a new view dictionary, never new rendering in this file (`server.py:3-5`).
  - `views.MAX_ROWS` (200) caps `?top=` unless the query names a count (`server.py:153-159`, `views.py:34`).
  - Loopback-only is a decision, not a default: the workbench has no authentication, so `mas ui serve` binds 127.0.0.1/::1/localhost only (`main.py:1221`, `server.py:246-258`).
  - `Workbench.__init__` opens and closes the root once so a bad root fails at startup rather than at the first request (`server.py:170`).

### `ui/views.py` — `src/mas/ui/views.py`
- **What it is**: One dictionary per screen, folded from the journal by the same core functions the terminal client calls — `leaderboard.snapshots`, `projection.progress`, `review.items`, `pool.fold`, `sr_stage.rationale_of`, `mechanism.narrative_of`, `Config.layer_record`.
  - Everything is labelled only through registered vocabularies, so neither surface carries a label, state or count of its own (parity rule, `views.py:1-8`). Nothing here writes.
- **Entry points**:
  - Screens: `tasks_and_runs` (`views.py:122`), `board` (`153`), `run` (`318`).
  - `candidate` (`views.py:291`), `review_queue` (`355`), `criteria_pool` (`392`), `settings` (`436`).
  - Helpers: `run_states` (`views.py:82`), `_binding` (`99`), `_run_row` (`107`), `_cells` per-criterion rows (`270`).
  - `_mechanism_block` (`views.py:232`), `_rationale_block` (`256`), `_claim_row` (`221`), `link` (`44`), `_frame` (`48`).
  - Source resolution: `_task` (`views.py:56`), `_snapshots` (`63`), `_rule_set` (`75`).
- **Records/artifacts it owns**: none. It reads journal events (`RUN_STATE_KINDS`, `views.py:36-37`, folded by `run_states` `82-96`) and artifacts (run binding payload `99-104`, per-candidate cells `270-288`, narratives and rationales).
- Every label is resolved via `vocab.label` (`views.py:52-53`); `READ_ONLY` and `FRESHNESS` are constants stated on every page (`views.py:28-29`, `48-49`).
- **Current state**: implemented. Boards and candidates carry the newer mandated-criteria fields with `.get`, so a board published before those existed reads as unknown rather than as nothing-excluded (`views.py:171-178`, `205-212`).
- A machine-adjudicated review item is listed apart from expert-decided ones with `confirmed_by_a_person: False` and an explicit note that no person confirmed it (`views.py:31`, `375-389`).
- A view that cannot find its record raises `NotFound` rather than rendering an empty screen that reads like an answer (`views.py:10-13`, `40`).
- **Handoff notes**:
  - `redact` is the secret invariant (ADR-40): a setting whose key contains `api_key` shows the environment variable name or key file basename, never a value (`views.py:33`, `425-433`).
  - `settings` applies it to settings, providers and role bindings (`views.py:448-456`).
  - Every page is one fold with `as_of`/`freshness` and does not follow a running run (`views.py:12-13`, `48-49`).
  - State labels come from `vocab`, so a new screen must not invent one (`views.py:5-8`).
  - `_snapshots` pins a named snapshot or takes the latest published one and raises `NotFound` otherwise (`views.py:63-72`).
  - This pinning is what makes `/candidate?snapshot=` deterministic.

### Module map (dependency order)
1. `core/models.py` and `cli/bridge.py` share the exchange protocol: the adapter writes requests and waits; the bridge claims, answers, and reads the run's DONE marker.
2. `adapters/literature/*` bottom layer: `http` + `registry` + parsers (`jats`, `textparse`), then the six sources, then `tools.register`.
3. `adapters/drug/*`: `universe` (no network) and the ChEMBL/GtoPdb/PubChem providers, assembled by `registration.register`, which also calls the literature and prediction registrations.
4. `adapters/predict/*`: `admet.py` + `_admet_worker.py`, reached only through `drug/registration.register` when an interpreter with `admet_ai` is found or predict is forced.
5. `cli/main.py` composes store + config + roster + broker for every command (and `bridge`); `ui/server.py` serves `ui/views.py` folds read-only over the same root.

### Section E — Tests, design_audit/, repository root & live state, scripts

All paths are relative to the repo root `/home/yiwei3_duke/anny/mas`. Facts below were read off the checkout on 2026-10-15; nothing in the repository was modified.

## E.1 Tests (`tests/`)

26 test files, 454 `def test_` functions total: 440 offline + 14 live (3 files). Factories/doubles live in `tests/fakes.py`; shared fixtures in `tests/conftest.py`.

| file | covers (from docstring / test names) | tests | marker |
|---|---|---|---|
| `tests/conftest.py` | `store` and `core` fixtures, each opening `Store.open(tmp_path/"root")` / `Core.open(...)` | — | — |
| `tests/fakes.py` | `FakeIdentity`, `FakeProperty` — in-memory identity/property provider doubles used by the end-to-end tests | — | — |
| `tests/fixtures/admet_worker_output.jsonl` (21,868 B) | recorded predictor worker stdout replayed by `test_predict_admet.py` | — | — |
| `tests/fixtures/article.xml` (1,440 B), `chapter.nxml` (1,296 B) | JATS article and Bookshelf BITS chapter parse fixtures | — | — |
| `tests/test_adjudication.py` | machine adjudication (`core/adjudication.py`): an agent can never make an expert decision; task-restated cutoffs; expert-set cutoffs stop scoring; hard exclusions demoted; disputes resolved by a third model family or left open; revision may only weaken a rule; transform bounds must be traceable | 45 | — |
| `tests/test_bound_support.py` | bound support (`core/bound_support.py`), findings F2–F4: a cited claim must carry *this* number; `needs_expert` reads transform bounds; `>= 30 -> >= 90` revision refusals | 26 | — |
| `tests/test_bridge_and_parallel.py` | `mas bridge` request/response split between agents; stale `DONE` markers; parallel literature cells give the same board; configured read-worker count | 4 | — |
| `tests/test_calibration_guard.py` | `assessor.calibration_guard`: a well-sourced hard exclusion that removes nearly all of the mandated-criteria reference set is demoted; guard cannot see individual candidates | 9 | — |
| `tests/test_config_and_providers.py` | layered settings (`core/config.py`), spend accounting (`core/budget.py`), OpenAI-compatible adapter key-file/thinking/JSON-mode behaviour | 18 | — |
| `tests/test_criteria_export.py` | the criteria review package (`core/criteria_export.py`): what it must say; nothing moves between two exports | 16 | — |
| `tests/test_criteria_pool.py` | pool workflow (`core/pool.py`, `derivation_stages.py`, `derivation_run.py`): propose, filter, distill, merge, refine, promotion, stall stop, budget stop, continuation into round 2. Scripted models, no network | 62 | — |
| `tests/test_derivation.py` | proposal screening/queueing; percentile scoring of ordering preferences; declared transforms and aggregations applied; task-mandated criteria from scope+constraints; range claims straddling a cutoff as conflicts | 11 | — |
| `tests/test_drug_adapter.py` | drug adapter (`adapters/drug/chembl.py`, `universe.py`, `registration.py`): identity resolution, target/mechanism/activity caches, salt-vs-parent lookup, paging, receptor potency from two curations + literature, evidence-kind registration invariants | 22 | — |
| `tests/test_evidence.py` | broker retry/outcome taxonomy; identity ambiguity queueing; claim locations and snapshots; determination bases; concurrent reading equals sequential reading; budget refusal stops the run; journal hash chain under concurrent appends | 18 | — |
| `tests/test_firewall.py` | evidence firewall (`core.reading.is_case_source`): no case-source document enters the system's own evidence, including retitled copies; uses the live case-source title/sha256 | 11 | — |
| `tests/test_foundation.py` | canonical bytes (key order, NFC, non-finite refusal), id/ULID/version prefixes, vocabulary closure, store locking (second host refused, sync folders unsupported), journal append-only + contiguous seq, content-addressed artifacts | 16 | — |
| `tests/test_freeze.py` | registering an experiment before it runs (`core/freeze.py`) and detecting it did not run as registered | 7 | — |
| `tests/test_literature_sweep.py` | literature cell end to end through the candidate sweep: query build, fetch under `read.max_papers_per_candidate`, quote-checked claims, per-run `LiteratureCache`, reader unit/determination-basis filters | 29 | — |
| `tests/test_live_drug.py` | live checks against PubChem and ChEMBL (real network calls) | 4 | **live** |
| `tests/test_live_literature.py` | live checks against Europe PMC and PubMed (real network calls) | 6 | **live** |
| `tests/test_live_predict.py` | live checks of the predicted-property panel; no network, but needs the predictor's own interpreter (torch, chemprop, rdkit outside `mas`), ~15 s per test | 4 | **live** |
| `tests/test_mechanism.py` | mechanism-of-action narrative (`core/mechanism.py`): deterministic gate drops sentences it cannot stand behind; curated ChEMBL mechanism records ground sentences; nothing in scoring can read it; second pass free | 11 | — |
| `tests/test_models_and_reading.py` | JSON extraction from model replies, schema validation, `call_role` repair-once, roster TOML, secret redaction, exchange adapter, JATS/abstract passages, quote matching, summary citation checks, case-source matching | 15 | — |
| `tests/test_predict_admet.py` | predicted-property panel reached by subprocess with a replayed worker: pipe, JSON lines, panel check, cache files; nothing needs torch/rdkit/chemprop | 24 | — |
| `tests/test_records.py` | task context versioning; constants defaults; registry invariants (no unitless/arbitrary cutoffs); rule sets need expert decisions; pending items block unless allowed; snapshot gate reporting | 9 | — |
| `tests/test_recovery.py` | recovery of the sealed historical criteria (`core/recovery.py`, handoff §12.2): intake once after freeze, exact/near-equivalent/missed/extra accounting; fixtures are synthetic labelled items only | 13 | — |
| `tests/test_run_end_to_end.py` | full sweep publishes a ranked snapshot; no short-circuit after hard fail; crash-then-resume reuses finished cells; budget exhaustion leaves run unresolved; coverage-floor ranking; shortlist stage; mandated-receptor floor (registered number) | 11 | — |
| `tests/test_sources.py` | evidence sources: licence gate, BITS/HTML/text parsing, Bookshelf, MediaWiki, uploads, GtoPdb affinities, multi-source search, breadth×depth enumeration. No network | 19 | — |
| `tests/test_symbolic.py` | symbolic-regression scoring (`core/symbolic.py`, `core/sr_stage.py`): solver vs known answer, ill-conditioned/constant-column refusals, deterministic three-way split, holdout adoption/fallback, `expert_prior` route | 24 | — |
| `tests/test_ui.py` | browser workbench (`ui/server.py`, `ui/views.py`): endpoints via `Workbench.handle`, quote escaping, loopback-only bind, 405 for non-GET/HEAD, no UI write path, read-only core; one real socket request | 20 | — |

**How the live marker is declared and used.** `pyproject.toml` §`[tool.pytest.ini_options]` (lines 21–24) sets `testpaths = ["tests"]`, `markers = ["live: needs something the offline suite does not have: network access to PubChem, ChEMBL and Europe PMC, or the local predictor environment"]` and `addopts = "-m 'not live'"`. Exactly three files set `pytestmark = pytest.mark.live` (`tests/test_live_drug.py:8`, `tests/test_live_literature.py:11`, `tests/test_live_predict.py:14`); each docstring says "Run with: pytest -m live". No `skipif`/`xfail`/`importorskip` anywhere; the only other marker is `parametrize`.

**Exact commands** (README.md "Running the system"):
- `pip install -e ".[dev]"` — install (Python ≥3.11; runtime dep is `requests` only).
- `pytest` — offline suite (440 tests); live tests are deselected by `addopts`.
- `pytest -m live` — only the 14 live tests (overrides `addopts`); the two literature/drug files need network, `test_live_predict.py` needs the predictor environment instead.
- `pytest -m "live or not live"` — everything in one run.

## E.2 `design_audit/`

Status judged by content date and last commit: **live** = written/extended during the build phase (13–14 Oct 2026, commits after `aec82a6`); **historical** = the 12–13 Oct design-phase audit record.

| file | what it is | status |
|---|---|---|
| `optimized_design.md` (186 KB) | canonical design document (architecture, interfaces, states, persistence; §0 glossary governs all names) | historical design-phase; still cited by README as canonical |
| `architecture_decisions.md` (53 KB) | ADR log with context/alternatives/evidence/tradeoffs; extended during the build to at least ADR-49 (config layering, pool, SR scoring, licence gate, mechanism separation, provider measurement, …) | **live** (last commit dadbaf2, 13 Oct) |
| `collaboration_log.md` (42 KB) | actual multi-agent work record (who was assigned what, disagreements/resolutions); carries build records from §7.9 on | **live** (dadbaf2, 13 Oct) |
| `audit_report.md` (26 KB) | design-audit findings A-01… prioritised, evidence, recommended changes | historical |
| `suggestions.md` (16 KB) | gaps/weaknesses of the original concept, prioritised improvements | historical |
| `resources.md` (18 KB) | data/services/compute/expert-input inventory and missing case inputs | historical |
| `tools.md` (32 KB) | researched packages/data sources at the interface level (capabilities, licences, limits) | historical |
| `literature_review.md` (63 KB) | integrated literature review from workstreams 6a/6b | historical |
| `module.md` (37 KB) | module map: responsibilities, interfaces, persistence, failure behaviour | historical |
| `task.md` (36 KB) | implementation task list M0–M8 with acceptance criteria | historical |
| `leaderboard_spec.md` (27 KB) | leaderboard specification (task-scoped ranking, states, provenance) | historical |
| `evaluation_plan.md` (41 KB) | evaluation plan: process vs domain validity, matched-budget policy comparison, registration | historical |
| `iteration_and_provenance_spec.md` (40 KB) | how every run/round/revision is recorded so provenance questions are answerable | historical |
| `case_study_protocol.md` (43 KB) | protocol for the primary acceptance case (baseline, targets, sensitivity) | historical; baseline still referenced |
| `rebuttal_alignment.md` (41 KB) | maps each rebuttal-draft claim to the capability/evidence/records that would substantiate it | historical |
| `v1_scope.md` (11 KB) | v1 build order (what is in, what waits) | historical; still cited by README as build order |
| `post_handoff_decisions.md` (34 KB) | the nine post-handoff user discussions and decisions (ADR-30…-39), 13 Oct | historical design record |
| `ui_ux_spec.md` (67 KB) | UI/UX specification for browser workbench + terminal client (wireframes, states); updated during the build (last commit 9d72220) | live reference spec |
| `ui_backlog.md` (3 KB) | what the built workbench deliberately does not do, with reasons (ADR-35/12/31); known rough edges | **live** (4990d76, 13 Oct) |
| `situation_report.md` (23 KB) | iteration-2 report for a reviewer: what works, never worked, defects that reached a board, §7 rejected change, current numbers, decisions needed | **live** (da8a5ee, 14 Oct) |
| `improvement_plan.md` (13 KB) | post-audit plan: F1–F9 confirmed and closed, what blocks each measurement, work sequence, honest expectations, corrections to earlier claims | **live** (2783c13, 14 Oct) |
| `registered_endpoint_decision.md` (4 KB) | pre-registrations: primary rank endpoint = reference compound's position among *rankable* candidates (coverage floor 0.5), eligibility reported separately, target top 5 | **live** (5764d88, 14 Oct) |
| `predicted_evidence_and_the_receptor_gate.md` (10 KB) | what the ADMET panel / DTI receptor models and the receptor gate are worth, measured; the sparse-coverage ranking defect; literature-potency limit | **live** (e87c04c, 14 Oct) |
| `criteria_count_reconciliation.md` (4 KB) | reconciles every quoted criteria count (72/34/40/13/9/26/5) with its population and version | **live** (7b93fd6, 14 Oct) |
| `derived_criteria_review.md` (846 KB, 5,605 lines) | human-readable review export of the derived criteria, labelled `historical_baseline_pre_repair`, pinned at journal seq 516 | **live** export artifact (7b93fd6) |
| `derived_criteria_review.json` (1.3 MB, 1 line) | the exact records behind every card (adjudications, items…) | **live** export artifact |
| `derived_criteria_manifest.json` (12 KB) | baseline label, board refs/hashes (run, snapshot `lb_..._4`, `rules@v3`), counts, export provenance | **live** export artifact |
| `run_configs/models_deepseek.toml` (3 KB) | committed model roster for the clean derivation (round 2): two adapters over one DeepSeek model (reasoning on/off per role), key path redacted, measured model-id notes, exact CLI invocation | **live** run config (aa3668d, 14 Oct) |
| `agent_reports/` (14 files, 12–13 Oct) | design-audit workstream reports and independent reviews (below) | historical |

`agent_reports/` contents: `00_coordinator_brief.md` (brief all workstream subagents read); `evidence_and_policy.md` (WS1); `mas_architecture.md` (WS2); `tools_and_data.md` (WS3); `human_review_and_ui.md` (WS4); `evaluation_and_improvement.md` (WS5); `current_agent_literature_a.md`/`_b.md` (WS6a/6b); `reference_harness_inspection.md` (WS7); `final_integrated_review.md` (independent verdict: "ready with fixes"); `post_handoff_review.md` (review of ADR-30…-34 revisions); `chains_groups_memory_review.md` (D7–D9 review, "not ready"); `surfaces_review.md` (operator surfaces + Windows host, "not ready"); `consolidated_review.md` (post-revision consistency review, "not consistent").

## E.3 Repository root & live state

| path | what it is |
|---|---|
| `README.md` (22 KB) | user-facing entry: what the system claims, install, CLI workflow (task → criteria derive → review decide/adjudicate → rules confirm → run → board), autonomous adjudication routes, shortlist/defer-capability procedure, browser workbench, settings layers, pool workflow, SR scoring, mechanism notes, evidence sources, model roster/bridge |
| `MAS_System_Revision_Master_Handoff_EN_20261014.md` (94 KB, 1,023 lines) | external review + implementation specification handed to the build: FINAL GOAL section, findings F1–F8 (§6), evidence policy (§7), ranking/uncertainty (§8), work packages (§9), owner decisions (§10), criteria export (§11), freeze and one-shot evaluation protocol (§12), regression acceptance checks (§13), execution sequence (§14). Names remote `YWDDLiang03/mas`, reviewed commit `aec82a6` |
| `mas_audit.md` (15 KB, 125 lines) | external audit/remediation blueprint: north-star goal and two one-shot measurements, firewall/falsification conditions, diagnosis of four gaps (uncommitted criteria, zero-merge loop, fail-open authority, post-ranking defects), remediation steps. **Note:** its header classifies Sections 1–5 + Appendix as distributable and declares Section 6 sealed (the 11 CQAs); those sections are *not present* in this file — it stops mid-Step 3 in an unclosed code block |
| `pyproject.toml` (673 B) | packaging (`mas` console script → `mas.cli.main:main`, dependency `requests>=2.31`, dev extra `pytest>=8`) and the pytest config quoted in E.1 |
| `.gitignore` | ignores `__pycache__/`, caches, `build/`, `var/` (line 8, "local store roots used during development"), and `CELL1.pdf` ("case-source documents supplied by the user (not redistributable)") |
| `CELL1.pdf` (10.3 MB) | the reference manuscript (case source), git-ignored but present on disk |
| `MAS_MultiAgent_Design_Audit_EN_20261012/` | the originally supplied design-audit package: prompts (`START_HERE_...`), `Project_Brief_EN.md`, numbered concept/reference notes 01–07, `ARTIFACT_MANIFEST.json`, `MANIFEST.sha256`, plus `agentic_doping_reference/` excerpts, `references/`, `supporting_data/` |
| `src/mas/` | the implementation (`core/`, `adapters/`, `cli/`, `ui/`); `tests/` and `scripts/` beside it |
| `.pytest_cache/` | leftovers from earlier pytest runs (also `__pycache__/`) |

**`var/` layout** (git-ignored, not committed; sizes from the filesystem listing; the big `store.db` was not opened):

- `var/primary/` — the live manuscript-case root:
  - `store/` — the live store: `store.db` 2,134,335,488 B (~2.0 GiB) plus `store.db-wal` 4,120,032 B and `store.db-shm` 32,768 B (open/WAL state), `store.lock` 0 B; run configs `models.toml` 1,154 B, `models_deepseek.toml` 2,305 B, `models_round3.toml` 1,308 B; exchange queues `llm_exchange/`, `llm_exchange_critic/`, `llm_exchange_adjudicator/` and `llm_exchange_r3{,_critic,_adjudicator}/`, each with `requests/`+`responses/` (some with `claims/`; `llm_exchange/` also `orphaned/`), `DONE` markers incl. `DONE.stale-1130`
  - prediction caches: `admet_panel.json` 16,942,873 B; `dti_predictions.json` 2,112,949 B; `dti_training/` per receptor — `CSF1R.json` 982,963, `FGFR1.json` 1,725,074, `VEGFR1.json` 470,219, `VEGFR2.json` 3,675,862, `VEGFR3.json` 255,845
  - universe: `universe_chembl.json` 1,828,395 B, `universe_smiles.json` 232,187 B
  - run inputs/outputs: `task.json` 2,530 B, `derive.json` 80,413 B, `derive.err` 7 B, `run.log` 357 B
  - a stray **empty** `var/primary/store.db` (0 B) beside the `store/` directory — purpose unclear
- `var/pilot2/` (store.db 7,438,336 B) and `var/pilot/` (store.db 2,678,784 B) — earlier pilot roots, each with `task.json`, `derive.json`, `models.toml`, `llm_exchange{,_critic}/`
- `var/demo/` — demo root: `store/` (store.db 573,440 B), `demo.log` 7,704 B, `llm_exchange/` with five `brief_*.json` request/response pairs
- `var/clitest/` — small CLI-test root: store.db 45,056 B, `models.toml` 948 B, empty `llm_exchange/`

## E.4 `scripts/` (no `tools/` directory exists)

There is no `tools/` directory anywhere in the repository (checked with `find`); only `scripts/` with two files.

| file | what it does |
|---|---|
| `scripts/build_universe_chembl.py` | reconstructs the candidate universe from the ChEMBL web API: small molecules with `max_phase >= 3`, salts collapsed to parents, flags merged; writes a documented JSON record (source, query, date, counts, `universe`) so the universe is a `named_library`, never mistaken for the authors' list. Usage: `python scripts/build_universe_chembl.py OUT.json [--min-phase 3]`. Its note says "the authors' 3,171-compound list was not available". Likely produced `var/primary/universe_chembl.json` |
| `scripts/demo_literature.py` | demo of the literature pipeline with LLM roles answered through the subagent bridge: plan queries → search (Europe PMC + PubMed) → read → summarize → extract checked claims, printing a JSON report and writing `DONE` into the exchange dir. Requires the package importable (`from mas...`) and a `mas` store. Usage: `python scripts/demo_literature.py STORE_DIR EXCHANGE_DIR` |

## Unclear / caveats

- `mas_audit.md` is truncated in this checkout (ends mid-code-block; the announced Sections 4–5, Appendix and sealed Section 6 are absent).
- The empty `var/primary/store.db` beside `var/primary/store/` has no evident purpose.
- "Live" vs "historical" in E.2 is my judgement from content dates and commit activity, not an in-repo label (the only formal label found is `historical_baseline_pre_repair` in the `derived_criteria_*` export).


## 5. Pointers

- **Iteration log (today)**: `design_audit/iteration_log_2026-10-15.md` — the bridge stall, the
  takeover, rounds 5–11, every deviation recorded, the test log, and the development log.
- **Development log**: `git log dbb0394..HEAD` on `main`; each commit message carries its WHY.
- **Test log**: iteration log §5 (full suite 2026-10-15: **442 passed, 15 live deselected, 104.9 s**).
- **Design documents**: `design_audit/situation_report.md` (iteration-2 state),
  `improvement_plan.md` (WP0–WP10 sequence), `registered_endpoint_decision.md` (what counts as the
  result), `architecture_decisions.md` (ADR-01…ADR-46), `audit_report.md`,
  `case_study_protocol.md`, `ui_ux_spec.md`, `post_handoff_decisions.md`, and the root-level
  `MAS_System_Revision_Master_Handoff_EN_20261014.md`.
- **Live state**: `var/primary/store/` (git-ignored) — the journal store, rosters, caches, and the
  `llm_exchange_r3*` bridge queues whose 05:39–09:40 unserved requests are an honest record of the
  stall.
