"""Portable inputs retain facts and source identity without inherited decisions."""
import gzip
import hashlib
import json

import pytest

from mas.core import existing_research, reproduction, task
from mas.core.canonical import canonical_text, sha256_hex
from mas.core.journal import actor
from mas.core.reproduction import FORMAT, import_bundle
from mas.core.runtime import Core


def test_pinned_evidence_does_not_need_ancestor_proposal_streams(core):
    source = {'source_id': 'src_fixture', 'title': 'Published source metadata'}
    source_ref = core.artifacts.put('source', source)
    claim = {'claim_id': 'claim_fixture', 'admission_state': 'admitted', 'source_ref': source['source_id'],
             'normalized_statement': 'A factual observation with no screening threshold.'}
    claim_ref = core.artifacts.put('claim', claim)
    manifest = {'source_task_id': 'task_ancestor_not_packaged', 'source_runs': [{'run_id': 'run_ancestor_not_packaged'}],
                'claims': [{'claim_id': claim['claim_id'], 'artifact_id': claim_ref, 'sha256': sha256_hex(claim)}],
                'source_records': {source['source_id']: {'artifact_id': source_ref, 'sha256': sha256_hex(source)}}}
    ref = core.artifacts.put('existing_fact_manifest', manifest)
    tid, _ = task.record_version(core, {'objective_text': 'Generate independent criteria from facts', 'mode': 'exploratory',
        'evaluation_scope': 'fixture', 'candidate_universe': {'members': ['K1']}, 'evidence_fact_manifest_ref': ref},
        by=actor('tool', 'portable-fixture'))
    pinned, claims = existing_research.pin_evidence(core, tid)
    assert pinned == manifest and claims == [claim]
    assert not any(e.event_type == 'criterion.version_proposed' for e in core.journal.replay(tid))


def capsule(directory, records):
    directory.mkdir()
    path = directory / 'records.jsonl.gz'
    with gzip.open(path, 'wt', encoding='utf-8') as handle:
        for row in records:
            handle.write(canonical_text(row) + '\n')
    manifest = {'format': FORMAT, 'task_id': 'task_fixture', 'run_id': 'run_fixture', 'snapshot_id': 'snapshot_fixture',
                'capsule': {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
                'counts': {'events': 0, 'artifacts': 0}}
    (directory / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return path


def test_import_refuses_file_escape_even_for_an_integrity_checked_capsule(tmp_path):
    import base64
    data = b'outside workspace'
    bundle = tmp_path / 'capsule'
    capsule(bundle, [{'record_type': 'file', 'path': '../escaped.txt',
                      'sha256': hashlib.sha256(data).hexdigest(), 'content_base64': base64.b64encode(data).decode()}])
    with pytest.raises(ValueError, match='escapes'):
        import_bundle(bundle, tmp_path / 'new-workspace')
    assert not (tmp_path / 'escaped.txt').exists()


def test_import_checks_compressed_bytes_before_creating_workspace(tmp_path):
    bundle = tmp_path / 'capsule'
    path = capsule(bundle, [])
    with path.open('ab') as handle:
        handle.write(b'changed after manifest')
    workspace = tmp_path / 'new-workspace'
    with pytest.raises(ValueError, match='part hash differs'):
        import_bundle(bundle, workspace)
    assert not workspace.exists()


def test_import_preserves_projection_order_across_export_sections(core, tmp_path):
    by = actor('tool', 'ordered-capsule-fixture')
    first = core.journal.append('task_fixture', 'run.annotated', actor=by, payload={'ordinal': 1}).to_record()
    second = core.journal.append('task_fixture', 'run.annotated', actor=by, payload={'ordinal': 2}).to_record()
    bundle = tmp_path / 'ordered-capsule'
    capsule(bundle, [{'record_type': 'event', 'source_rowid': rowid, 'body': body, 'sha256': sha256_hex(body)}
                     for rowid, body in ((200, second), (100, first))])
    manifest_path = bundle / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['counts']['events'] = 2
    manifest['dependency_policy'] = {'source_rowids_required': True}
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    restored = import_bundle(bundle, tmp_path / 'ordered-workspace')
    with Core.open(restored['store'], read_only=True) as imported:
        rows = imported.store.db.execute('SELECT rowid,body FROM events ORDER BY rowid').fetchall()
        assert [row[0] for row in rows] == [100, 200]
        assert [json.loads(row[1])['payload']['ordinal'] for row in rows] == [1, 2]


@pytest.mark.parametrize('phase', ['stream', 'metadata'])
def test_interrupted_owned_import_resumes_without_duplicates_or_overwriting_other_work(core, tmp_path, monkeypatch, phase):
    import base64
    event = core.journal.append('task_fixture', 'run.annotated', actor=actor('tool', 'resume-fixture'),
                                payload={'recorded': True}).to_record()
    artifact_id = core.artifacts.put('source', {'source_id': 'src_resume_fixture'})
    envelope = core.artifacts.get(artifact_id)
    created_at = core.store.db.execute('SELECT created_at FROM artifacts WHERE artifact_id=?', (artifact_id,)).fetchone()[0]
    data = b'{"universe": []}'
    bundle = tmp_path / 'resume-capsule'
    capsule(bundle, [
        {'record_type': 'event', 'source_rowid': 100, 'body': event, 'sha256': sha256_hex(event)},
        {'record_type': 'artifact', 'artifact_id': artifact_id, 'body': envelope,
         'sha256': sha256_hex(envelope), 'created_at': created_at},
        {'record_type': 'file', 'path': 'universe_chembl.json', 'content_base64': base64.b64encode(data).decode(),
         'sha256': hashlib.sha256(data).hexdigest()},
        {'record_type': 'workflow', 'body': {'workflow_id': 'wf_resume_fixture', 'state': 'completed'}},
    ])
    manifest_path = bundle / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['counts'].update(events=1, artifacts=1)
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

    other = tmp_path / 'unrelated-workspace'
    other.mkdir()
    (other / 'notes.txt').write_text('Keep unrelated work', encoding='utf-8')
    with pytest.raises(ValueError, match='existing work is preserved'):
        import_bundle(bundle, other)
    assert not (other / 'store').exists()

    workspace = tmp_path / 'resumable-workspace'
    helper = '_write_import_file' if phase == 'stream' else '_write_import_json'
    original = getattr(reproduction, helper)
    stop_at = 'universe_chembl.json' if phase == 'stream' else 'workbench-state.json'

    def stop_after_write(path, value):
        original(path, value)
        if path.name == stop_at:
            raise KeyboardInterrupt('Interrupted capsule import')

    with monkeypatch.context() as interruption:
        interruption.setattr(reproduction, helper, stop_after_write)
        with pytest.raises(KeyboardInterrupt, match='Interrupted capsule import'):
            import_bundle(bundle, workspace)
    assert not (workspace / 'reproduction-import.json').exists()
    assert (workspace / 'universe_chembl.json').read_bytes() == data
    (workspace / 'universe_chembl.json').write_bytes(b'Conflicting user data')
    with pytest.raises(ValueError, match='existing workspace file differs'):
        import_bundle(bundle, workspace)
    assert (workspace / 'universe_chembl.json').read_bytes() == b'Conflicting user data'
    (workspace / 'universe_chembl.json').write_bytes(data)  # Operator resolves the conflict explicitly.
    # New unrelated files remain outside the capsule's claimed paths.
    (workspace / 'notes.txt').write_text('Keep notes added after interruption', encoding='utf-8')
    result = import_bundle(bundle, workspace)
    assert result['workspace'] == str(workspace.resolve())
    assert result['store'] == str((workspace / 'store').resolve())
    assert json.loads((workspace / 'reproduction-import.json').read_text()) == result
    assert import_bundle(bundle, workspace) == result
    assert (workspace / 'notes.txt').read_text() == 'Keep notes added after interruption'
    with Core.open(result['store'], read_only=True) as restored:
        assert restored.store.db.execute('SELECT count(*) FROM events').fetchone()[0] == 1
        assert restored.store.db.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 1
        assert restored.store.db.execute('SELECT rowid FROM events').fetchone()[0] == 100
    import sqlite3
    with sqlite3.connect(workspace / 'workbench-workflows.db') as db:
        assert db.execute('SELECT count(*) FROM workflows').fetchone()[0] == 1
