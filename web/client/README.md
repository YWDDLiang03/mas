# MAS research workbench

React 18 / TypeScript / Vite 5 client for the real `/api/workbench` service.
Production assets use `/workbench/`; page selection is held in `view`, `task`,
`item`, `snapshot` and `lang` query parameters, so links open directly and survive
refresh. The Python host serves `dist/` after a build.

```powershell
npm ci
npm run build
```

`npm run check` checks strict TypeScript. `npm run dev` is optional and proxies
API requests to the local backend on port 8769. The client does not
launch its own API service.

`npm run verify:api -- http://127.0.0.1:8769` runs a small, read-only check using
the actual API client. It covers record pages, global search, details, the full
CSV and production assets. It does not submit settings, drafts or workflows.

## Interface direction

Quiet research notebook: pale blue ink, white paper, compact evidence tables and
a persistent workflow strip. Agentic Doping informed the clear task selector,
working panels and continuous run feedback. The three-count criterion journey
and the phase strip carry the visual identity. Display type uses Palatino;
body type uses Aptos with local fallbacks. Spacing follows an 8 px rhythm, and
motion is limited to connection/activity and drawer transitions, respecting
reduced motion.

## Data and interaction

- `src/api/types.ts` follows the shared v2 API contract; `client.ts` is the only
  request boundary. It handles local operation tokens and structured errors.
- `useWorkflowStream` reconnects using native EventSource and keeps a two-second
  read fallback while disconnected. Unknown denominators never become progress
  percentages. Commands preserve recorded failures and unknown costs.
- Research objectives, criteria, quotes, model content and existing user input
  stay verbatim. Only UI labels switch language. English is the default.
- Drafts are separate from scientific tasks. Start sends one idempotency key and
  follows only the workflow started on that page. Old completed workflows never
  change the selected task.
- Server filters run before 50-item pagination. CSV always requests the complete
  selected snapshot, independently of the current search or group.
- A criterion edit requests a new version; the client does not mutate a frozen
  result. References and raw provenance live in expandable record details.
- No demo research data, locally generated scores or browser automation are
  included. Empty, loading and unavailable states reflect the API response.

See the [installation guide](../../docs/installation.md) to start the backend,
the [component reference](../../docs/components/workbench-and-cli.md) for routes
and records, and the [tutorial](../../docs/tutorial.md) for the saved case.
