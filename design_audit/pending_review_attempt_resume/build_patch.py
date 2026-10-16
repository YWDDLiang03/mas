"""Prepare an isolated patch; never edit active source or the primary store."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
preview = HERE / 'preview'
path = 'src/mas/core/investigation.py'
original = (ROOT/path).read_text(encoding='utf-8')
updated = original.replace('from . import adjudication, config, criteria, evidence, existing_research, ledger, measurement, review, task',
    'from . import adjudication, config, criteria, evidence, existing_research, ledger, measurement, review, review_attempts, task')
before = '                        adjudication.adjudicate(core, item, roster=roster, budget=budget, settings=settings.values)'
assert updated.count(before) == 1
updated = updated.replace(before,
    '                        review_attempts.review_once(core, item, roster=roster, budget=budget, settings=settings.values)')
changes = {path:(original,updated),
    'src/mas/core/review_attempts.py':('',(HERE/'review_attempts.py').read_text(encoding='utf-8')),
    'tests/test_review_attempt_resume.py':('',(HERE/'test_review_attempt_resume.py').read_text(encoding='utf-8'))}
patch=[]
manifest=[]
for path,(before,after) in changes.items():
    patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
        fromfile='a/'+path if before else '/dev/null',tofile='b/'+path))
    target=preview/path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(after,encoding='utf-8',newline='\n')
    manifest.append({'path':path,'base_sha256':hashlib.sha256(before.encode()).hexdigest() if before else None,
                     'patched_sha256':hashlib.sha256(after.encode()).hexdigest()})
(preview/'tests/conftest.py').write_bytes((ROOT/'tests/conftest.py').read_bytes())
(HERE/'review_attempt_resume.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
(HERE/'patch_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(HERE/'review_attempt_resume.patch')
