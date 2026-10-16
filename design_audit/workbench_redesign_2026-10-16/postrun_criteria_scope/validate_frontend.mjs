/** Virtual source overlay; no writes to web/client or the served dist. */
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const out = dirname(fileURLToPath(import.meta.url));
const root = resolve(out, '../../..');
const require = createRequire(resolve(root, 'web/client/package.json'));
const ts = require('typescript');
const esbuild = require('esbuild');
const original = resolve(root, 'web/client');
const manifest = JSON.parse(readFileSync(resolve(out, 'patch_manifest.json'), 'utf8'));
function digest(path) { return createHash('sha256').update(readFileSync(path)).digest('hex'); }
function servedFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory()
    ? servedFiles(resolve(directory, entry.name)) : [resolve(directory, entry.name)]);
}
const servedBefore = new Map(servedFiles(resolve(original, 'dist')).map(path => [path, digest(path)]));
const overrides = new Map(['src/pages/CriteriaPage.tsx', 'src/i18n.tsx', 'src/api/types.ts'].map(path => [
  resolve(original, path).replaceAll('\\', '/'), readFileSync(resolve(out, 'proposed/web/client', path), 'utf8'),
]));
const file = ts.readConfigFile(resolve(original, 'tsconfig.json'), ts.sys.readFile);
const config = ts.parseJsonConfigFileContent(file.config, ts.sys, original);
const host = ts.createCompilerHost(config.options);
const read = host.readFile.bind(host);
host.readFile = path => overrides.get(resolve(path).replaceAll('\\', '/')) ?? read(path);
const program = ts.createProgram(config.fileNames, { ...config.options, noEmit: true }, host);
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length) throw new Error(ts.formatDiagnosticsWithColorAndContext(diagnostics, {
  getCanonicalFileName: value => value, getCurrentDirectory: () => root, getNewLine: () => '\n',
}));
const bundle = await esbuild.build({ entryPoints: [resolve(original, 'src/main.tsx')], bundle: true,
  format: 'esm', platform: 'browser', write: false, outdir: resolve(out, 'not-written'),
  plugins: [{ name: 'prepared-patch', setup(build) {
    build.onLoad({ filter: /(?:CriteriaPage|i18n)\.tsx$/ }, args => {
      const contents = overrides.get(resolve(args.path).replaceAll('\\', '/'));
      return contents === undefined ? undefined : { contents, loader: 'tsx', resolveDir: dirname(args.path) };
    });
  } }],
});
esbuild.stop();
for (const [path, entry] of Object.entries(manifest.files)) {
  if (digest(resolve(root, path)) !== entry.before_sha256) throw new Error('Live source changed: ' + path);
}
const servedAfter = servedFiles(resolve(original, 'dist'));
if (servedAfter.length !== servedBefore.size || servedAfter.some(path => digest(path) !== servedBefore.get(path))) throw new Error('Served dist changed.');
writeFileSync(resolve(out, 'frontend-validation.json'), JSON.stringify({ status: 'prepared_not_applied',
  strict_typescript: 'passed', browser_bundle_in_memory: 'passed', outputs: bundle.outputFiles.map(file => ({ name: file.path.split(/[\\/]/).at(-1), bytes: file.contents.length })),
  live_source_and_dist_unchanged: true }, null, 2) + '\n');
console.log('Prepared frontend overlay: strict TypeScript and in-memory browser bundle passed; live files untouched.');
