"""Check release links, versions and frozen example integrity without model calls."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def heading_ids(text: str) -> set[str]:
    ids, counts = set(), {}
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\-\s]', '', title.lower()).replace(' ', '-')
        number = counts.get(slug, 0)
        counts[slug] = number + 1
        ids.add(slug + (f'-{number}' if number else ''))
    return ids


def main() -> int:
    errors = []
    documents = [ROOT / p for p in ('README.md', 'README.zh-CN.md', 'CONTRIBUTING.md', 'CHANGELOG.md')]
    documents += list((ROOT / 'docs').rglob('*.md'))
    documents += list((ROOT / 'config').rglob('*.md'))
    documents += [ROOT / 'examples/oral-multitarget/README.md']
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
    if verified_files != 28:
        errors.append(f'Expected 28 manifest-bound result files, found {verified_files}')
    supplementary = json.loads((case / 'latest/supplementary-manifest.json').read_text(encoding='utf-8'))
    for name, entry in supplementary['files'].items():
        path = case / 'latest' / name
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            errors.append('Supplementary research input mismatch: ' + name)

    comparison = json.loads((case / 'cqa-comparison.json').read_text(encoding='utf-8'))
    with (case / 'cqa-comparison.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(comparison['rows']) != 11 or len(rows) != 11:
        errors.append('CQA comparison must contain 11 original rows')
    for entry in comparison['latest']['files']:
        if digest(case / entry['path']) != entry['sha256']:
            errors.append('Comparison input hash mismatch: ' + entry['path'])
    if len(comparison['latest_enabled_core']) != 18 or len(comparison['latest_enabled_context']) != 13:
        errors.append('CQA enabled-set counts differ')

    presentation = ROOT / 'docs/presentation'
    validation = json.loads((presentation / 'validation.json').read_text(encoding='utf-8'))
    if digest(presentation / 'MAS-system-and-case.pptx') != validation['pptx_sha256']:
        errors.append('Presentation changed after its visual/data verification')
    print(json.dumps({'version': package, 'documents': len(documents), 'local_links_checked': links,
                      'frozen_result_files_checked': verified_files, 'comparison_rows': len(rows),
                      'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
