# Operator surface backlog

What the first browser workbench (`src/mas/ui/`, slice S6) does **not** do, with the reason each
item was left out. Nothing here is a defect: the surface is deliberately a read surface over the
journal, and everything that changes state stays on the terminal, where an expert decision can be
entered interactively (ADR-35).

## Deliberately out of this iteration

| Item | Why not now |
|---|---|
| Live updates (server-sent events or a socket) | Every page is one fold of the journal, taken when the page is rendered, and says so; a push channel needs a subscription model with role-filtered, redacted frames (ADR-35) and is not worth that until someone watches a run in a browser. Reload folds again. |
| Starting, pausing or resuming a run from the browser | A command surface needs the durable command record, the at-most-once application and the per-stream basis check ADR-35 specifies. Until that exists, a button would be a second write path into the store. |
| Deciding a review item | An `hd_` requires interactive entry on the terminal (ADR-12, ADR-35). The review page shows the queue and states where the decision is made; it must not become a place where an approval can be clicked. |
| Editing settings | The resolved configuration is hashed into each run binding; editing it from a page without the layer provenance and the drift refusal would make a run's settings unreproducible. The page shows the layer every value came from instead. |
| Authentication, and serving to another machine | The host binds a loopback address and refuses anything else, because the surface is unauthenticated. Reaching it from another machine is the operator's own SSH port forward (U-15), not a listener on a routable address. |
| Windows and Chrome packaging | The workbench is stdlib `http.server` and runs wherever the host runs; what is untested is the Windows service-host path as a whole (U-14), not the pages. |
| Charts and trend views | A snapshot's comparability depends on its member set (ADR-43); a chart across snapshots with different member sets would imply a comparison the records do not support. Needs the member-set hash surfaced first. |
| Evaluator-only content | Reads of evaluator-only artifacts are confirmed, logged commands shown on screen only (ADR-31). The workbench has no path to them, and that is the intended state. |

## Known rough edges in what was built

| Edge | Note |
|---|---|
| A page is a full fold on every request | Fine for a store of this size; a long chain will want a cursor. Measured cost is in the test suite, not guessed. |
| `/pool` renders every lineage | At 72 lineages the page is around 100 KB. It needs paging before a pool of thousands. |
| No candidate search | Candidates are reached from the leaderboard or by id in the query string. |
| Tested headlessly only | Every endpoint is asserted as JSON and as rendered HTML, including escaping of claim text and refusal of non-GET methods, and a smoke test walks a real store. No human has looked at the pages, by design in this iteration. |
