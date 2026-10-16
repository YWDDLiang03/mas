/** Type-check virtual proposed files without writing active source or dist. */
import { createRequire } from 'node:module';
import { readFileSync, existsSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const out = dirname(fileURLToPath(import.meta.url)), root = resolve(out, '../../..');
const project = resolve(root, 'web/client');
const require = createRequire(resolve(project, 'package.json'));
const ts = require('typescript');
const manifest = JSON.parse(readFileSync(resolve(out, 'patch_manifest.json'), 'utf8'));
const normalize = path => resolve(path).replaceAll('\\', '/');
const overrides = new Map(Object.keys(manifest.files).filter(path => /^web\/client\/.*\.tsx?$/.test(path))
  .map(path => [normalize(resolve(root, path)), readFileSync(resolve(out, 'proposed', path), 'utf8')]));
const configFile = ts.readConfigFile(resolve(project, 'tsconfig.json'), ts.sys.readFile);
const config = ts.parseJsonConfigFileContent(configFile.config, ts.sys, project);
const host = ts.createCompilerHost(config.options), read = host.readFile.bind(host), exists = host.fileExists.bind(host);
host.readFile = path => overrides.get(normalize(path)) ?? read(path);
host.fileExists = path => overrides.has(normalize(path)) || exists(path);
const program = ts.createProgram([...new Set([...config.fileNames, ...overrides.keys()])], { ...config.options, noEmit: true }, host);
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length) throw new Error(ts.formatDiagnosticsWithColorAndContext(diagnostics, {
  getCanonicalFileName: path => path, getCurrentDirectory: () => root, getNewLine: () => '\n',
}));
for (const [path, entry] of Object.entries(manifest.files)) {
  const active = resolve(root, path);
  const hash = existsSync(active) ? createHash('sha256').update(readFileSync(active)).digest('hex') : null;
  if (hash !== entry.before_sha256) throw new Error('Active source changed: ' + path);
}
writeFileSync(resolve(out, 'frontend-validation.json'), JSON.stringify({ status: 'prepared_not_applied', strict_typescript: 'passed',
  virtual_files: overrides.size, live_source_unchanged: true, dist_build: 'not run' }, null, 2) + '\n');
console.log('Prepared virtual frontend: strict TypeScript passed; active source and dist were not written.');
