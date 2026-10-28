"""Shared task metadata removes private descriptions while retaining exclusions."""
from copy import deepcopy

from mas.core.canonical import sha256_hex
from mas.core.reproduction import public_metadata_copy


def test_private_source_labels_are_projected_without_mutating_science():
    original = {'kind': 'task_context', 'payload': {'objective_text': 'Compare candidates',
        'scope_entities': ['target A'], 'case_source_documents': [{'title': 'Synthetic private draft',
        'note': 'Private descriptive notes', 'identifiers': [{'scheme': 'sha256', 'value': 'a' * 64}]}]}}
    saved = deepcopy(original)
    public, changed = public_metadata_copy(original)
    assert original == saved
    assert public['payload']['objective_text'] == original['payload']['objective_text']
    assert public['payload']['scope_entities'] == ['target A']
    assert public['payload']['case_source_documents'][0]['identifiers'] == saved['payload']['case_source_documents'][0]['identifiers']
    assert public['payload']['case_source_documents'][0]['title'] == 'Private source document'
    assert len(changed) == 2 and sha256_hex(public) != sha256_hex(original)
    assert public_metadata_copy(public) == (public, [])


def test_observations_and_tasks_without_private_source_descriptions_are_unchanged():
    for record in ({'kind': 'assessment', 'payload': {'value': 12.5, 'unit': 'nM'}},
                   {'kind': 'task_context', 'payload': {'objective_text': 'Compare candidates'}}):
        assert public_metadata_copy(record) == (record, [])


def test_projected_task_import_retains_task_identity_and_exclusion_fingerprint(core, tmp_path):
    import gzip
    import hashlib
    import json
    from mas.core import reproduction, task
    from mas.core.canonical import canonical_text
    from mas.core.journal import actor
    from mas.core.runtime import Core

    tid, _ = task.record_version(core, {'objective_text': 'Compare synthetic candidates',
        'mode': 'exploratory', 'evaluation_scope': 'fixture', 'candidate_universe': {'members': ['A']},
        'case_source_documents': [{'title': 'Synthetic private source', 'note': 'Private description',
            'identifiers': [{'scheme': 'sha256', 'value': 'b' * 64}]}]}, by=actor('tool', 'fixture'))
    event = core.journal.replay(tid)[0].to_record()
    aid = event['payload']['artifact_id']
    original = core.artifacts.get(aid)
    public, _ = public_metadata_copy(original)
    created = core.store.db.execute('SELECT created_at FROM artifacts WHERE artifact_id=?', (aid,)).fetchone()[0]
    bundle = tmp_path / 'bundle'; bundle.mkdir()
    archive = bundle / 'records.jsonl.gz'
    with gzip.open(archive, 'wt', encoding='utf-8') as f:
        for row in [{'record_type': 'event', 'body': event, 'sha256': sha256_hex(event)},
                    {'record_type': 'artifact', 'artifact_id': aid, 'body': public,
                     'source_sha256': sha256_hex(original), 'sha256': sha256_hex(public), 'created_at': created}]:
            f.write(canonical_text(row) + '\n')
    (bundle / 'manifest.json').write_text(json.dumps({'format': reproduction.FORMAT,
        'task_id': tid, 'run_id': 'run_fixture', 'snapshot_id': 'snapshot_fixture',
        'capsule': {'path': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()},
        'counts': {'events': 1, 'artifacts': 1}}), encoding='utf-8')
    restored = reproduction.import_bundle(bundle, tmp_path / 'restored')
    with Core.open(restored['store'], read_only=True) as imported:
        value = task.get(imported, tid)
        assert value['objective_text'] == 'Compare synthetic candidates'
        assert value['case_source_documents'][0]['title'] == 'Private source document'
        assert value['case_source_documents'][0]['identifiers'][0]['value'] == 'b' * 64
