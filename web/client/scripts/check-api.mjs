/** Read-only integration check: no browser, settings writes, workflows or model calls. */
import assert from 'node:assert/strict';
import { build, stop } from 'esbuild';

const origin = process.argv[2] || 'http://127.0.0.1:8769';
const nativeFetch = globalThis.fetch;
globalThis.fetch = (url, init) => nativeFetch(new URL(String(url), origin), init);
const compiled = await build({ entryPoints: ['src/api/client.ts'], bundle: true, write: false, format: 'esm', platform: 'node' });
stop();
const { api } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString('base64')}`);
const bootstrap = await api.bootstrap();
assert.ok(Array.isArray(bootstrap.tasks) && Array.isArray(bootstrap.workflows));
const settings = await api.settings();
assert.ok(Array.isArray(settings.fields));
const task = bootstrap.current_task_id || bootstrap.tasks[0]?.task_id;
if (task) {
  const [overview, criteria, candidates, sources, snapshots] = await Promise.all([
    api.overview(task), api.criteria(task, { page: 1 }), api.candidates(task, { status: 'all', page: 1 }),
    api.evidence(task, { page: 1 }), api.snapshots(task),
  ]);
  assert.equal(overview.task.task_id, task);
  for (const page of [criteria, candidates, sources]) {
    assert.equal(page.page_size, 50); assert.ok(page.items.length <= 50);
    assert.ok(Number.isFinite(page.total) && typeof page.has_more === 'boolean');
  }
  if (criteria.items[0]) {
    const detail = await api.criterion(task, criteria.items[0].criterion_id);
    assert.ok(Array.isArray(detail.history) && Array.isArray(detail.sources));
  }
  if (candidates.items[0]) {
    const detail = await api.candidate(task, candidates.items[0].candidate_ref, candidates.snapshot_id || undefined);
    assert.ok(Array.isArray(detail.assessments) && Array.isArray(detail.evidence));
    const search = await api.candidates(task, { status: 'all', q: candidates.items[0].label, snapshot: candidates.snapshot_id || undefined, page: 1 });
    assert.ok(search.items.some(item => item.candidate_ref === candidates.items[0].candidate_ref));
  }
  const csvUrl = api.csvUrl(task, candidates.snapshot_id);
  assert.ok(!/[?&](q|status|page)=/.test(csvUrl));
  const csvResponse = await fetch(csvUrl);
  assert.ok(csvResponse.ok);
  const csv = await csvResponse.text();
  let quoted = false, rows = 0;
  for (let index = 0; index < csv.length; index++) {
    if (csv[index] === '"') { if (quoted && csv[index + 1] === '"') index++; else quoted = !quoted; }
    else if (csv[index] === '\n' && !quoted) rows++;
  }
  assert.ok(!quoted);
  const dataRows = rows - 1 + (csv.endsWith('\n') ? 0 : 1);
  assert.equal(dataRows, candidates.counts.total);
  assert.ok(csv.slice(0, csv.indexOf('\n')).includes('qualification'));
  console.log(`Real API: task overview, ${criteria.total} criterion records, ${candidates.total} candidates, ${sources.total} evidence records, ${snapshots.items.length} snapshots, search/detail and complete CSV passed.`);
} else console.log('Real API: bootstrap/settings passed; no recorded task is available for data-page checks.');

const indexResponse = await fetch('/workbench/');
assert.ok(indexResponse.ok);
const html = await indexResponse.text();
const assetPaths = [...html.matchAll(/(?:src|href)="(\/workbench\/assets\/[^\"]+)"/g)].map(match => match[1]);
assert.ok(assetPaths.length >= 2);
for (const path of assetPaths) { const response = await fetch(path); assert.ok(response.ok); await response.arrayBuffer(); }
console.log('Production index and compiled JS/CSS assets are served successfully.');
