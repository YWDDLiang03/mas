"""Snapshot isolation, provenance and model-boundary checks for saved predictions."""
import copy
import csv
import io
import json
import zipfile

import pytest

from mas.adapters.predict.cdes import PairRequest, SavedResultScorer, digest, install_dataset
from mas.ui.structure_results import StructureResults


@pytest.fixture
def imported(tmp_path):
    source = b"id,score\nEXAMPLE-A,0.75\n"
    manifest = {"integration_id": "cdes_" + "a" * 64, "task_id": "task_example", "snapshot_id": "snapshot-example",
                "candidate_count": 1, "prediction_count": 1, "matched_candidates": 1, "targets": ["Example target"],
                "source_files": [{"file": "example.csv", "sha256": digest(source)}]}
    row = {"id": "EXAMPLE-A", "name": "Example A", "candidate_ref": "candidate-a", "smiles": "CC",
           "match_status": "identifier_and_structure", "evaluation": {"classification": "Eligible", "rank": 1, "score": .8},
           "predictions": {"Example target": {"value": .75, "raw_value": "0.75", "rank": 1, "population": 1,
                                             "file": "example.csv", "row": 2}}, "measurements": {}}
    data = {"manifest": manifest, "targets": {"Example target": {"uniprot": "EXAMPLE-T", "sequence": "ABC",
              "sequence_sha256": digest(b"ABC"), "label": "Example target"}}, "candidates": [row],
            "admet": [], "original_candidates_without_prediction": []}
    root = install_dataset(data, {"example.csv": source}, tmp_path)
    return data, root, StructureResults(tmp_path)


def test_saved_provider_preserves_good_rows_and_reports_identity_failures(imported):
    data, _, _ = imported
    provider = SavedResultScorer(data)
    result = provider.predict_pairs([PairRequest("candidate-a", "CC", "EXAMPLE-T", "ABC"),
        PairRequest("EXAMPLE-A", "CCC", "EXAMPLE-T", "ABC"),
        PairRequest("EXAMPLE-A", "CC", "EXAMPLE-T", "ABD"),
        PairRequest("MISSING", "CC", "EXAMPLE-T", "ABC")])
    assert result["results"][0]["value"] == .75
    assert result["results"][0]["source"]["row"] == 2
    assert [row["error_code"] for row in result["errors"]] == ["structure_mismatch", "sequence_mismatch", "saved_result_missing"]
    assert data["candidates"][0]["evaluation"]["score"] == .8


def test_query_is_bound_to_task_and_snapshot(imported):
    _, _, service = imported
    assert service.get("task_other")["available"] is False
    assert service.get("task_example", snapshot="another")["reason"] == "different_evaluation"
    assert service.get("task_example", wanted="candidate-a")["item"]["id"] == "EXAMPLE-A"
    page = service.get("task_example", cohort="all", q="example", page=99, page_size=1)
    assert page["total"] == 1 and page["page"] == 1 and not page["has_more"]
    with pytest.raises(ValueError):
        service.get("../../task_example")


def test_full_export_preserves_values_and_source_bytes(imported):
    _, _, service = imported
    _, content = service.export("task_example", "zip")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read("predictions.csv").decode("utf-8-sig"))))
        assert rows[0]["interaction_score"] == "0.75"
        assert rows[0]["saved_score"] == "0.8"
        assert archive.read("sources/example.csv") == b"id,score\nEXAMPLE-A,0.75\n"
        assert json.loads(archive.read("results.json"))["manifest"]["snapshot_id"] == "snapshot-example"
    with pytest.raises(ValueError):
        service.export("task_example", "csv", snapshot="another")


def test_changed_contents_cannot_reuse_an_integration_identity(imported, tmp_path):
    data, root, _ = imported
    changed = copy.deepcopy(data)
    changed["candidates"][0]["predictions"]["Example target"]["value"] = .95
    with pytest.raises(ValueError):
        install_dataset(changed, {}, tmp_path)
    (root / "dataset.json.gz").write_bytes(b"modified")
    with pytest.raises(ValueError, match="checksum"):
        StructureResults(tmp_path).load("task_example")


def test_study_switch_persists_without_changing_saved_results(imported, tmp_path):
    _, root, service = imported
    before = (root / 'dataset.json.gz').read_bytes()
    service.set_enabled('task_example', False)
    reopened = StructureResults(tmp_path)
    assert reopened.get('task_example')['reason'] == 'module_disabled'
    reopened.set_enabled('task_example', True)
    assert reopened.get('task_example')['items'][0]['evaluation']['score'] == .8
    assert (root / 'dataset.json.gz').read_bytes() == before


def test_optional_workflow_uses_explicit_target_input_and_pins_its_source(imported, tmp_path):
    from types import SimpleNamespace
    from mas.core.config import resolve
    from mas.ui.workflows import WorkflowManager
    manager = WorkflowManager(SimpleNamespace(store_root=tmp_path/'store', saved_overrides={},
        settings=resolve(project_file=None, environ={})), SimpleNamespace())
    manager._launch = lambda workflow_id: None
    try:
        off = manager.start({'idempotency_key': 'off', 'input': {'targets': ['EXAMPLE-T'], 'constraints': 'Intravenous use',
                            'cdes_enabled': False}})
        assert 'cdes' not in [row['id'] for row in off['phases']]
        supplied = manager._read(off['workflow_id'])['input']
        assert supplied['objective_source'] == 'targets_and_requirements'
        assert supplied['targets'] == ['EXAMPLE-T'] and supplied['original_objective'] == ''
        on = manager.start({'idempotency_key': 'on', 'input': {'objective': 'Synthetic target comparison',
                            'targets': ['EXAMPLE-T'], 'cdes_enabled': True}})
        assert [row['id'] for row in on['phases']][-3:] == ['screen', 'cdes', 'results']
        stored = manager._read(on['workflow_id'])['input']
        assert stored['_cdes_source']['dataset_sha256']
        with pytest.raises(ValueError, match='on or off'):
            manager.start({'idempotency_key': 'bad', 'input': {'objective': 'Example', 'cdes_enabled': 'false'}})
    finally:
        manager.close()


def test_new_study_links_only_its_targets_and_uses_its_own_measurements(imported, tmp_path):
    from mas.adapters.predict.cdes_workflow import run_saved_analysis, selected_targets
    from mas.core.runtime import Core
    from mas.core import criteria, task
    from mas.core.journal import actor
    source, _, service = imported
    who = actor('tool', 'synthetic-module-test')
    with Core.open(tmp_path/'store') as core:
        spec = {'objective_text': 'Synthetic intravenous target study', 'mode': 'conditional',
            'evaluation_scope': 'synthetic', 'candidate_universe': {'members': ['candidate-a']},
            'scope_entities': [{'entity_kind': 'target', 'label': 'Example target', 'identifier': 'EXAMPLE-T',
                                'identifier_scheme': 'uniprot', 'role': 'required'}],
            'constraints': [{'kind': 'route', 'text': 'Intravenous administration', 'hardness': 'hard'}]}
        tid, _ = task.record_version(core, spec, by=who)
        context = task.get(core, tid)
        attr = {'name': 'Synthetic activity', 'unit': 'nM', 'evidence_request': {'capability': 'interaction_evidence_lookup',
                'question_kind': 'pchembl_values', 'parameters': {'target_uniprot': 'EXAMPLE-T'}}}
        attr_ref = criteria.record_version(core, tid, 'attribute', 'attr_example@v0', attr, by=who, summary='Synthetic')
        rule = {'attribute_ref': attr_ref, 'rule_kind': 'preference'}
        rule_ref = criteria.record_version(core, tid, 'rule', 'rule_example@v0', rule, by=who, summary='Synthetic')
        frozen = core.artifacts.put('rule_set', {'entries': [{'attribute_ref': attr_ref, 'rule_ref': rule_ref}]})
        core.journal.append(tid, 'criterion.version_approved', actor=who,
                            payload={'rule_set_ref': 'rules@v1', 'artifact_id': frozen})
        cell = {'assessment_id': 'asm_example', 'value': 42.0, 'unit': 'nM', 'verdict': 'available',
                'value_kind': 'measured', 'determination_basis': 'measured', 'value_source_claim_refs': ['claim_synthetic']}
        artifact = core.artifacts.put('assessment', cell)
        core.journal.append('run_example', 'candidate.assessed', actor=who,
            payload={'artifact_id': artifact, 'candidate_ref': 'candidate-a', 'attribute_ref': attr_ref, 'rule_ref': rule_ref})
        snapshot = {'snapshot_id': 'snapshot-new', 'run_id': 'run_example', 'rules@v': 'rules@v1', 'candidate_entries': [
            {'candidate_ref': 'candidate-a', 'identity_labels': ['Example A'], 'selection': {'decision': 'eligible'},
             'qualification': {'hard_passed': 0, 'required_direct_answered': 1}, 'position': 1, 'preference_score': .42,
             'per_criterion_refs': ['asm_example']}]}
        pin = service.pin(service.collections()[0]['id'])
        result = run_saved_analysis(core, tmp_path, context, snapshot, pin)
        assert result['status'] == 'completed' and result['predicted_pairs'] == 1
        fresh = StructureResults(tmp_path).get(tid)['items'][0]
        assert fresh['evaluation']['score'] == .42
        assert fresh['measurements']['Example target']['value'] == 42
        assert fresh['measurements']['Example target']['unit'] == 'nM'
        assert fresh['predictions']['Example target']['value'] == .75
        assert len(service.collections()) == 1  # Derived results are not advertised as new model collections.
        selected, missing = selected_targets({'scope_entities': [{'identifier': 'ANOTHER-T', 'label': 'Another target'}]}, source)
        assert selected == [] and missing == ['Another target']
        selected, missing = selected_targets({'scope_entities': [{'identifier': 'DIFFERENT-ACCESSION',
            'identifier_scheme': 'uniprot', 'label': 'Example target'}]}, source)
        assert selected == [] and missing == ['Example target']
        selected, missing = selected_targets({'scope_entities': [{'identifier': 'EXAMPLE-T',
            'identifier_scheme': 'uniprot', 'label': 'Example target mutant', 'conditions': {'mutation': 'A1V'}}]}, source)
        assert selected == [] and missing == ['Example target mutant']
