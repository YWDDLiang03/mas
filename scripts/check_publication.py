"""Check release links, versions and frozen example integrity without model calls."""
from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def heading_ids(text: str) -> set[str]:
    ids = set(re.findall(r'<a\s+(?:id|name)=["\x27]([^"\x27]+)["\x27]', text))
    counts = {}
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\-\s]', '', title.lower()).replace(' ', '-')
        number = counts.get(slug, 0)
        counts[slug] = number + 1
        ids.add(slug + (f'-{number}' if number else ''))
    return ids


def main() -> int:
    errors = []
    public_paths = [ROOT / p for p in subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT
    ).decode('utf-8').split('\0') if p and (ROOT / p).is_file()]
    documents = [p for p in public_paths if p.suffix == '.md' and
        (p.parent == ROOT or p.relative_to(ROOT).parts[0] in ('docs', 'config', 'examples'))]
    public_set = {p.resolve() for p in public_paths}
    links = 0
    for document in documents:
        if not document.exists():
            errors.append(f'Missing document: {document.relative_to(ROOT)}')
            continue
        text = document.read_text(encoding='utf-8-sig')
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', prose):
            target = target.strip().split(' "')[0].strip('<>')
            parts = urlsplit(target)
            if parts.scheme or target.startswith('//'):
                continue
            path = (document.parent / unquote(parts.path)).resolve() if parts.path else document
            links += 1
            if not path.exists():
                errors.append(f'{document.relative_to(ROOT)}: missing {target}')
            elif path.is_relative_to(ROOT) and path.is_file() and path not in public_set:
                errors.append(f'{document.relative_to(ROOT)}: link points to local-only file {target}')
            elif parts.fragment and path.suffix.lower() == '.md':
                if unquote(parts.fragment) not in heading_ids(path.read_text(encoding='utf-8-sig')):
                    errors.append(f'{document.relative_to(ROOT)}: missing anchor {target}')

    package = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    source = re.search(r'__version__ = "([^"]+)"', (ROOT / 'src/mas/__init__.py').read_text(encoding='utf-8')).group(1)
    client = json.loads((ROOT / 'web/client/package.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'web/client/package-lock.json').read_text(encoding='utf-8'))
    if len({package, source, client['version'], lock['version'], lock['packages']['']['version']}) != 1:
        errors.append('Package versions differ')

    case = ROOT / 'examples/oral-multitarget'
    verified_files = 0
    for manifest_path in case.glob('*/results/manifest.json'):
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        for name, entry in manifest['files'].items():
            path = manifest_path.parent / name
            if not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
                errors.append(f'Frozen result mismatch: {path.relative_to(ROOT)}')
            verified_files += 1
    if verified_files != 14:
        errors.append(f'Expected 14 manifest-bound result files, found {verified_files}')
    supplementary = json.loads((case / 'latest/supplementary-manifest.json').read_text(encoding='utf-8'))
    for name, entry in supplementary['files'].items():
        path = case / 'latest' / name
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            errors.append('Supplementary research input mismatch: ' + name)

    portable = json.loads((case / 'latest/reproduction/manifest.json').read_text(encoding='utf-8'))
    replay = json.loads((case / 'latest/reproduction/verification.json').read_text(encoding='utf-8'))
    if portable.get('format') != 'mas-portable-reproduction-v1':
        errors.append('Unknown portable reproduction format')
    capsule = portable['capsule']
    projection = portable.get('public_metadata_projection')
    if not isinstance(capsule.get('bytes'), int) or capsule['bytes'] <= 0 or not re.fullmatch(r'[0-9a-f]{64}', capsule.get('sha256', '')):
        errors.append('Invalid published capsule identity')
    verified_capsule = (projection or {}).get('source_capsule_sha256', capsule['sha256'])
    if projection and projection.get('source_capsule_sha256'):
        receipt = json.loads((case / 'latest/reproduction/public-metadata-verification.json').read_text(encoding='utf-8'))
        if (receipt.get('status') != 'pass' or receipt.get('public_capsule_sha256') != capsule['sha256']
                or receipt.get('source_capsule_sha256') != verified_capsule
                or receipt.get('unexpected_changed_records') != 0):
            errors.append('Public metadata projection verification differs')
    verified = replay['recorded_replay']
    if (replay['capsule_sha256'] != verified_capsule or verified['status'] != 'pass'
            or verified['candidate_count'] != 3177 or verified['assessment_count'] != 98487
            or verified['difference_count'] != 0
            or verified['saved_entries_sha256'] != verified['replayed_entries_sha256']):
        errors.append('Published capsule replay verification differs')

    comparison = json.loads((ROOT / 'config/examples/criterion-comparison.synthetic.json').read_text(encoding='utf-8'))
    if comparison.get('fixture_type') != 'synthetic' or len(comparison.get('rows', [])) != 3:
        errors.append('Public criterion comparison must be the declared synthetic fixture')
    task_export = json.loads((case / 'latest/results/task.json').read_text(encoding='utf-8'))
    if any(s.get('title') != 'Private source document' for s in task_export.get('case_source_documents') or []):
        errors.append('Excluded private source descriptions remain in the public task export')
    for path in public_paths:
        relative = path.relative_to(ROOT).as_posix()
        if ('manuscript' in path.name.lower() or relative.startswith(('docs/figures/original-layout/', 'docs/figures/current/'))
                or relative in ('examples/oral-multitarget/cqa-comparison.csv', 'examples/oral-multitarget/cqa-comparison.json')):
            errors.append('Private working material in public file set: ' + relative)
        if path.suffix.lower() in ('.md', '.toml', '.json', '.py', '.yml', '.yaml', '.csv'):
            content = path.read_text(encoding='utf-8-sig', errors='replace')
            if re.search(r'\bsk-[A-Za-z0-9]{24,}\b', content):
                errors.append('Credential-shaped value in public file: ' + relative)

    presentation = ROOT / 'docs/presentation'
    validation = json.loads((presentation / 'validation.json').read_text(encoding='utf-8'))
    if digest(presentation / 'MAS-system-and-case.pptx') != validation['pptx_sha256']:
        errors.append('Presentation changed after its visual/data verification')

    captures = json.loads((ROOT / 'docs/assets/current/manifest.json').read_text(encoding='utf-8'))
    for entry in captures['images']:
        path = ROOT / 'docs/assets/current' / entry['file']
        if not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            errors.append('Current screenshot differs from capture manifest: ' + entry['file'])
    current = json.loads((ROOT / 'docs/reference/current-ui-validation.json').read_text(encoding='utf-8'))
    current_csv = ROOT / current['csv']['file']
    if digest(current_csv) != current['csv']['sha256']:
        errors.append('Current browser export differs from its verification record')
    with current_csv.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    counts = dict(Counter(row['selection_decision'] for row in rows))
    if len(rows) != current['csv']['rows'] or counts != current['csv']['selection_counts']:
        errors.append('Current browser export selection counts differ')
    if counts != validation['current_ui_refresh']['candidate_groups']:
        errors.append('Presentation and current browser export groups differ')
    print(json.dumps({'version': package, 'documents': len(documents), 'local_links_checked': links,
                      'frozen_result_files_checked': verified_files, 'synthetic_comparison_rows': len(comparison['rows']),
                      'current_screenshots_checked': len(captures['images']), 'current_candidate_rows_checked': len(rows),
                      'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
