# Foundation: records, vocabularies and storage

[Components](README.md) · [Architecture](../architecture.md)

The foundation makes a saved research result inspectable after the process that produced it has ended. It supplies a single record identity, serialization rule and write discipline for the rest of MAS. This is the implementation of C1–C3; it also supplies the record identifiers used by the identity service and every later component.

## Purpose and design rationale

Scientific state changes over time: a criterion can be revised, a source can fail, and a candidate can move after new evidence arrives. Overwriting a final JSON document would erase the basis for those changes. MAS therefore records events in order and stores immutable artifact payloads referenced by those events. Projections can recover the relevant state while the previous state stays available.

Content hashes need a stable byte representation. Platform line endings and dictionary insertion order must not change an artifact's identity. [`canonical.py`](../../src/mas/core/canonical.py) normalizes Unicode to NFC, normalizes string line endings, sorts object keys and serializes compact UTF-8 JSON. Supplied files use their original bytes for `content_hash`; canonical text hashes are a separate duplicate-detection tool.

## Contract

| Input | Output / persistent record |
|---|---|
| Store root and `read_only` mode | `Core` containing `Store`, `Journal`, `ArtifactStore` |
| Stream ID, registered event kind, actor and event fields | `Event` with contiguous stream-local `seq`, event ID, timestamps and hashes |
| Artifact kind, JSON-compatible payload and schema version | `art_…` ID for a canonical envelope |
| Registered vocabulary domain and value | Accepted value or `VocabularyViolation` |
| Identifier prefix or versioned reference | Typed identifier / `@vN` reference |

There are run, task, group, case and evaluation streams. Sequence numbers are meaningful within one stream. They are not a global chronological counter across all tasks.

## Implementation

[`Core.open()`](../../src/mas/core/runtime.py) opens a root and constructs the journal and artifact store. [`Store.open()`](../../src/mas/core/store.py) creates or opens `store.db`, enables SQLite pragmas, installs append-only triggers, and holds an operating-system lock for a writer. An in-process reentrant lock serializes writes from worker threads. A read-only open takes no writer lock and uses a connection that refuses writes, allowing the UI to inspect a running host.

[`Journal.append()`](../../src/mas/core/journal.py) validates the stream, event kind, actor kind, visibility, execution states and termination reason. In a `BEGIN IMMEDIATE` transaction it assigns the next sequence number and stores both canonical event body and hash. `replay()` reads an inclusive sequence interval; `last_seq()`, `streams()` and `of_type()` support reconstruction and inspection.

[`ArtifactStore.put()`](../../src/mas/core/artifacts.py) wraps the payload in `kind`, `schema_version` and `vocabulary_version`, hashes the envelope, and uses the first 12 digest characters for the artifact ID. Identical envelopes reuse an ID; a truncated-ID collision with a different full digest is refused. `get()` returns the envelope and `payload()` returns its contents.

Payload semantics belong to the component that writes them. The generic artifact store does not implement a universal JSON-schema registry. For example, task validation lives in `task.validate`, attribute/rule invariants live in `criteria`, and tool outputs are checked in the broker and evidence path. This division keeps storage generic while allowing each scientific contract to express its own constraints.

[`vocab.py`](../../src/mas/core/vocab.py) owns closed values and display labels for execution, candidate and verdict states, evidence kinds, tool outcomes and other shared domains. [`ids.py`](../../src/mas/core/ids.py) supplies ULID-based IDs, registered prefixes and version parsing. [`constants.py`](../../src/mas/core/constants.py) registers values that affect verdicts, giving downstream records an explicit numerical basis.

## Failure semantics

- A second writer on a root fails with `store_locked`. Recognized network or synchronized roots are refused with `store_root_unsupported` unless explicitly overridden.
- Invalid vocabulary, unsupported canonical values, non-finite numbers and normalized-key collisions are refused before a record is committed.
- A failed event transaction rolls back. Previously committed events and artifacts remain readable.
- Read-only writes fail with `StoreError("read_only", ...)`.
- Append-only SQL triggers block updates/deletes through ordinary database operations. Administrative maintenance and direct filesystem access remain outside the scientific API's trust boundary.

The event journal and artifact table are authoritative scientific records. Workflow state, uploads, display annotations and workbench materialized caches are separate stores described in [workbench and CLI](workbench-and-cli.md).

## Worked example: stable content and a versioned event

**Illustrative executable fragment** for a writable local temporary directory:

```python
from tempfile import TemporaryDirectory
from mas.core.runtime import Core
from mas.core.journal import actor

with TemporaryDirectory() as root, Core.open(root) as core:
    first = core.artifacts.put("example", {"b": 2, "a": "line\r\n"})
    same = core.artifacts.put("example", {"a": "line\n", "b": 2})
    assert first == same
    event = core.journal.append(
        "task_example", "task.version_recorded",
        actor=actor("system", "example"),
        payload={"version": 1, "artifact_id": first},
    )
    assert event.seq == 1
```

The envelope's canonical content explains the reused artifact ID. This low-level example writes a registered event kind; a real task should be created through `task.record_version` so the task contract is checked.

## Existing verification

[`test_foundation.py`](../../tests/test_foundation.py) covers canonical equality, Unicode, non-finite refusal, raw-file hashes, ID parsing, vocabulary refusal, exclusive writers, contiguous sequences and append-only artifacts/events. Read-only behavior is also exercised in [`test_ui.py`](../../tests/test_ui.py). These checks concern local storage mechanics; they do not validate the truth of a claim stored in an otherwise valid artifact.
