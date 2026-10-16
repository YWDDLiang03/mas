"""Preserve the exact local implementation and built UI before a real run."""
from __future__ import annotations

import hashlib
import json
import shutil
import os
from pathlib import Path

from mas.cli.main import _implementation
from mas.core.clock import utc_now


def main():
    root = Path(__file__).resolve().parents[1]
    implementation = _implementation()
    destination = root / 'var/provenance/workbench-v2' / implementation['source_sha256'][:16]
    for relative in ('src', 'tests', 'web/client/src'):
        shutil.copytree(root / relative, destination / relative,
                        ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=True)
    assets = Path(os.environ.get('MAS_WORKBENCH_ASSET_DIR') or root / 'web/client/dist').resolve()
    shutil.copytree(assets, destination / 'web/client/dist', dirs_exist_ok=True)
    for relative in ('AGENTS.md', 'pyproject.toml', 'web/client/package.json', 'web/client/package-lock.json',
                     'web/client/index.html', 'web/client/tsconfig.json', 'web/client/vite.config.ts'):
        source = root / relative
        if source.exists():
            shutil.copy2(source, destination / relative)
    files = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(destination.rglob('*')) if p.is_file() and p.name not in ('manifest.json', 'hashes.json')}
    manifest = {'implementation': implementation, 'created_at': utc_now(), 'path': str(destination),
                'built_asset_source_directory': str(assets), 'files': files}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'implementation': implementation, 'archive': str(destination), 'files': len(files)}))


if __name__ == '__main__':
    main()
