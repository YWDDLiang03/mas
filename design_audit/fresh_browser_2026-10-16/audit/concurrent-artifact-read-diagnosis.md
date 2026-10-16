# Concurrent artifact lookup diagnosis

The failing four-worker literature test was reproduced without modifying its fixture. On the 25th repeated execution, `ArtifactStore.get()` raised `KeyError('art_5d0b377fa5be')` for a search-coverage record. An independent read-only connection immediately found that exact artifact, with its expected kind and hash. This evidence does not indicate a missing persisted artifact or a lost write transaction.

The shared connection is opened with `check_same_thread=False`. Writer transactions already hold `store.write_lock`; simultaneous read cursors use the same Python SQLite connection. This is consistent with the concurrent statement-cache inconsistency described in the [CPython issue #118172](https://github.com/python/cpython/issues/118172), which also documents `cached_statements=0` as a workaround. The application reproduction used CPython 3.14 and SQLite 3.50.4; this report does not generalize the finding to all SQLite threading.

Evidence retained:

- `concurrent-artifact-read-reproduction.json`: original four-worker fixture, failure at iteration 25, complete traceback, retained temporary database path, and independent proof that the artifact exists.
- `concurrent-artifact-read-uncached-control.json`: the same fixture with only connection statement caching disabled; 100 executions, zero failures, 17.18 seconds.
- A smaller component check, before and after the same connection option, used four workers reading 16 distinct stored artifacts. With the default statement cache it observed a wrong payload (requested index 1, received index 4), a missing-row `KeyError`, and `InterfaceError('bad parameter or other API misuse')`. With caching disabled it reported no errors. No primary store or model was used in either experiment.

The fix sets `cached_statements=0` on both writable and read-only `Store` connections. It leaves the existing writer lock and transaction boundaries intact. It does not serialize document retrieval or model calls. This is a connection-safety correction; no scientific observation, rule, or snapshot is rewritten.

After the source fix, targeted literature sweep, terminal-tool-fact and broker replay checks passed: **56 passed in 3.52 seconds**. The initial broader command named a nonexistent test file and ran no tests; the corrected command completed successfully. The parent is responsible for the final full offline suite. No further repeated stress was performed after the accepted control experiment.
